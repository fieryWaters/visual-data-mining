# Computer Use Training Dataset Implementation Plan

## Input Data
- **Location**: `data/filtered/filtered_*` folders 
- **Format**: Sanitized JSON events + screenshots (3/second)
- **Processing**: Coordinates normalized, invalid sessions filtered
- **Sessions**: 15-minute gaps identify distinct usage periods
- **Existing Tools**: `normalize_logs.py`, `five_features_processing_deprecated.ipynb`

## Target Output
- **Training Style**: Autoregressive action prediction (like language modeling)
- **Data Points**: Each action in session becomes training target
- **Context**: 3 recent screenshots + LLM summaries of older screens
- **Format**: Pure tool-use sequences, no human instructions

**Data Point Structure:**
```
Given: [action1, action2, action3, ..., actionN, screenshot_summary1, screenshot_summary2, image1, image2, image3]
Predict: actionN+1
```

## Processing Pipeline

### Phase 1: Raw → Derived Events
**Raw Events**: [click, double click, scroll, keypresses]

**Stage 1: Primary Derived Events**
- Scroll accumulation (dx/dy pixels) → `pagedown` event
- Consecutive keypresses → segmented `typed_text` events (split on special keys)
- Key combinations → `keyboard_combo` objects
- All serialized as JSONL with new timestamps

**Stage 2: Screenshot Triggers**
- `pagedown`, `click`, `keyboard_combo` → insert `get_screenshot`

**Configuration**: Pixel thresholds, special key lists, combo patterns

### Phase 2: Context + Summarization
- Generate LLM summaries of older screenshots
- Implement 3-image + summary context system
- Create sliding window training data points

### Phase 3: Training Format
- Convert to LlamaFactory-compatible format (`training/LLaMA-Factory/`)
- Tool-use conversation structure
- Each sliding window = separate conversation

### Phase 4: MCP Integration
- Research MCP tool calling standards
- Implement MCP client
- Download Playwright/Selenium MCP server

## Implementation Status

### Phase 1 - Completed: Key Combination Detection ✅

**Implementation Details:**
- **File**: `preprocessing_scripts/key_combo_processor.py` 
- **Approach**: Tree-based detection using anytree library for nested modifier structures
- **Output**: Single file `data/derived_events/keyboard_combos.json` containing all meaningful combos

**Key Design Decisions:**
1. **Combo Starters**: Modifiers (`Key.cmd`, `Key.ctrl`, `Key.alt`, `Key.shift`) + Arrow keys (`Key.up/down/left/right`)
2. **Tree Structure**: Nested dictionaries preserving exact key press order
   - Example: `{"Key.cmd": {"Key.shift": {"z": {}}}}` for Cmd+Shift+Z
   - Repeated keys: `{"Key.cmd": {"Key.tab": [{}, {}]}}` for Cmd+Tab+Tab (array length = repetitions)
3. **Filtering Logic**:
   - **Shift Typing Filter**: Removes capitalization (`{"Key.shift": {"A": {}}}`) and extended typing sessions with spaces/backspace
   - **Empty Combo Filter**: Removes modifier-only presses (`{"Key.cmd": {}}`)
   - **Arrow Keys**: Captured as immediate standalone combos (`{"Key.down": {}}`)

**Results Achieved:**
- **2,494 total meaningful combos** from 349,130 events across all sessions
- **8 modifier-based combos**: Real shortcuts like Cmd+Space, Cmd+Tab, Cmd+C+V
- **2,486 arrow key actions**: Navigation events (up: 748, down: 800, left: 1,261, right: 854)
- **Filtered out**: 58 shift typing sessions, 2 empty modifier presses

**Technical Implementation:**
- Loads all JSON files simultaneously for chronological processing
- Uses anytree Node structure for tree building and navigation
- Converts trees to nested dictionaries for JSON serialization
- Handles repeated keys via array notation `[{}, {}]`

### Phase 1 - Next Enhancements Required:

**1. Arrow Key Aggregation**
- **Issue**: Multiple consecutive arrow presses create separate combo entries
- **Solution**: Aggregate consecutive identical arrows into count format
- **Example**: `{"Key.left": 3}` instead of `[{"Key.left": {}}, {"Key.left": {}}, {"Key.left": {}}]` (current format uses empty objects as counters)

**2. Comprehensive Special Key Capture**
- **Current**: Only captures arrow keys as standalone actions
- **Expand to**: All special keys when pressed outside modifier combos
- **Include**: Function keys (`Key.f1-f12`), navigation (`Key.tab`, `Key.esc`), editing (`Key.delete`), media keys, etc.

## Open Issues

### Technical Challenges
- Stream 100GB datasets without full memory load
- Screenshot summarization model selection (probably the one we will be using for inference, so it can summarize screenshots itself while going)
- Balance 3 images + summaries + action history
- Persistent storage on cluster

### Format Questions
- Function call standardization across MCP implementations
- Training data compatibility with MCP schemas
- Tool alignment with Playwright MCP server

### Edge Cases
- Complex modifier sessions (CMD+hold → tab+tab+tab → release)
- Session boundary handling in autoregressive format
- Coordinate/timing representation standards

---

**Goal**: Train VLM to predict next computer action given visual + action history context.