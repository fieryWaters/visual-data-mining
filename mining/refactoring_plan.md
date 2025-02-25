# Keystroke Logger Refactoring Plan

## Module Structure

We'll split the current keystroke_logger.py into three distinct modules:

1. **keystroke_recorder.py**: Real-time keystroke capture module
2. **keystroke_sanitizer.py**: Password detection and sanitization 
3. **screen_recorder.py**: Rolling video capture

## Module Details

### 1. keystroke_recorder.py
- Core functionality: Capture all keystrokes in real-time
- Store data in memory buffer (not to file)
- Capture metadata (timestamp, key state)
- Light and fast for real-time performance
- Include mouse clicks and scroll events
- Export buffer data on demand to sanitizer

### 2. keystroke_sanitizer.py
- Password management:
  - Store passwords in encrypted JSON file
  - Decrypt using user-provided password
  - Use proper encryption (AES)
- Text processing:
  - Convert raw keystrokes to text (handling backspaces, etc.)
  - Run fuzzy matching against password list
  - Sanitize detected passwords in output
- Create sanitized log files (JSONL format)
- Mark password locations with special event type
- Preserve all other data for ML purposes

### 3. screen_recorder.py
- Rolling screen capture (24/7)
- Configurable window size (default 10 minutes)
- Zero time gap between captures
- Filename format includes timestamp
- Proper resource management

## Implementation Approach
1. Create the three modules with basic interfaces
2. Implement keystroke_recorder.py first (memory buffer)
3. Implement screen_recorder.py (video capture)
4. Implement keystroke_sanitizer.py (password handling)
5. Create a main controller script to connect all modules

## Security Considerations
- Never write raw keystroke buffer to disk
- Proper encryption for password storage
- Sanitize all sensitive data
- Allow user to control what is captured