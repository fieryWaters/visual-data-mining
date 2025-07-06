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

## Open Issues

### Technical Challenges
- Stream 100GB datasets without full memory load
- Screenshot summarization model selection (probably the one we will be using for inference, so it can summarize screenshots itself while going)
- Generic keystroke combo detection
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