# Computer Use Training Dataset Implementation Plan

## Overview
Transform existing filtered computer use data into a pre-training dataset for vision language models, focusing on sequential computer actions with visual context.

## Current Data Structure Analysis

### Input Data
- **Location**: `data/filtered/filtered_*` folders
- **JSON Format**: Sanitized keystroke/mouse events with normalized coordinates (0-1)
- **Screenshots**: 3 screenshots/second, matched to events by timestamp
- **Sessions**: 15-minute gaps used to identify distinct usage sessions
- **Validation**: Coordinates validated, invalid sessions filtered out

### Existing Processing Pipeline
1. **normalize_logs.py**: Cleans raw data, filters invalid sessions, normalizes coordinates
2. **five_features_processing_deprecated.ipynb**: Creates click-screenshot pairs with historical context
3. **Data Quality**: Out-of-range coordinates filtered, timestamp matching validated

## Target Training Format

### Training Data Approach
- **Autoregressive**: Predict next action given all previous actions (like language modeling)
- **Multiple Data Points per Session**: Each action in a session becomes a training target
- **Image Context**: 3 recent screenshots + LLM summaries of older screenshots
- **Format**: Pure tool-use sequences without human instructions

### Data Point Structure
```
Given: [action1, action2, action3, ..., actionN, screenshot_summary1, screenshot_summary2, image1, image2, image3]
Predict: actionN+1
```

### Sequence Generation Strategy  
- **Session-based**: 15-minute sessions become training sequences
- **Sliding Window**: Each action in session creates a data point
- **Image + Summary Context**: Recent images + summarized older screens
- **Streaming Processing**: Handle large datasets without loading everything in memory

## Implementation Phases

### Phase 1: Unified Data Structure
- Convert JSON-L files into single event list + image list
- Implement streaming processing for large datasets
- Transform from raw event space to action space via two-stage derivative pipeline

**Raw Events**: [click, double click, scroll, keypresses]

**Stage 1: Primary Derived Events (Serialization)**
- Multiple scroll events (accumulate dx/dy pixels) → `pagedown` event (configurable pixel threshold)
- Consecutive keypresses → segmented `typed_text` events (split around special keys: Enter, Tab, Escape, modifier combos)
- Key combinations → `keyboard_combo` event objects with descriptive data
- All serialized as JSONL objects with new timestamps (beginning or end of sequence)

**Stage 2: Secondary Derived Events (Screenshot Triggers)**  
- `pagedown` event → insert `get_screenshot`
- `click` event → insert `get_screenshot`
- `keyboard_combo` events (CMD+tab, CMD+q, CMD+space) → insert `get_screenshot`

**Configuration**: Pixel thresholds, special key lists, combo patterns all configurable

**Edge Case**: Complex modifier sessions (CMD+hold → tab+tab+tab → CMD+release) require state machine tracking. Future enhancement for Windows data collection. 

### Phase 2: Context Window + Summarization  
- Generate LLM summaries of older screenshots
- Implement 3-image + summary context system
- Create training data points with sliding window approach

### Phase 3: Training Format Generation
- Convert to LlamaFactory-compatible format
- Format in tool-use format

### Phase 4: MCP Alignment & Extensions
- Research MCP tool calling standards
- Implement MCP Client
- Implement/Download MCP server for computer automation (selenium/playwrite MCP download)

## Open Questions & Technical Challenges

### MCP Integration Questions
- **Function Call Standards**: Are there competing formats or is tool calling standardized?
- **MCP Compatibility**: Does training data format need to match MCP schemas exactly?
- **Tool Definition**: How to align our training tools with Playwright MCP server tools?

### Data Processing Challenges  
- Persistent storage on cluster
- **Streaming Architecture**: Process 100GB-scale datasets without full memory load
- **Screenshot Summarization**: Which LLM to use for generating older screenshot summaries? (probably the one we will be using for inference, so it can summarize screenshots itself while going)
- **Keystroke Pattern Detection**: Build tools for command combinations (cmd+tab, cmd+q, etc.) (this should be generic for detecting any keystroke combo (input combo and it will return a list of them across the whole list))
- **Context Window Design**: Balance 3 images + summaries + action history

### Training Format Questions
- **Autoregressive Structure**: How to properly format sliding window predictions? Each one is its own conversation.
- **Session Boundaries**: How to handle context reset between sessions? Each one is its own conversation.
- **Action Representation**: Standardize click coordinates, keystroke sequences, timing

### Output Specifications
- **Dataset Size**: Combine all filtered folders into single training dataset
- **File Structure**: LlamaFactory-compatible directory structure
- **Image Paths**: Relative paths that work with LlamaFactory's image loading
- **Metadata Tracking**: Maintain source file and session information

## Success Metrics

3. **Format Compliance**: LlamaFactory format compatibility
4. **Training Readiness**: Dataset loads successfully in LlamaFactory

## Dependencies
- **Input Data**: All `data/filtered/filtered_*` folders
- **LlamaFactory**: Existing installation under `training/LLaMA-Factory/`

## Future Integration Points
- **MCP Server Integration**: Playwright browser automation (not decided yet)
- **Fine-tuning Pipeline**: Human-instructed task completion
- **Evaluation Framework**: Agent performance benchmarking

