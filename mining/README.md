# Computer Interaction Mining

Privacy-preserving keystroke and screen recording with sanitization.

## Components

- **keystroke_recorder.py**: Captures keystrokes in real-time
- **keystroke_sanitizer.py**: Detects and redacts passwords
- **screen_recorder.py**: In-memory screenshot recorder
- **data_collector.py**: Main controller

**Utils:**
- **password_manager.py**: Secure password storage
- **text_buffer.py**: Keystroke-to-text conversion
- **fuzzy_matcher.py**: Password detection algorithms

## Setup

```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip3 install -r requirements.txt
```

## Usage

```bash
# Run data collector
python3 data_collector.py [options]

# Options:
# --no-screen          Disable screen recording
# --screen-minutes N   Minutes to keep in buffer (default: 10)
# --screen-fps N       Frames per second (default: 5)
# --output-dir DIR     Log directory (default: "logs")
# --add-password PWD   Add password to sanitize
# --process-interval N Process every N seconds (default: 10)
```

## Testing

```bash
# Run all tests
python run_tests.py

# Run specific tests
python run_tests.py sanitizer
python run_tests.py fuzzy_matcher
python run_tests.py password_manager
python run_tests.py text_buffer
```

## Privacy Features

- Detects and redacts passwords using fuzzy matching
- Handles text editing (backspace, deletion)
- Preserves non-sensitive information
- Raw keystroke data never written to disk

## Password Detection

1. Events → Text conversion via TextBuffer
2. FuzzyMatcher analyzes text and buffer history
3. Multiple detection strategies with thresholds
4. Detected passwords replaced with [REDACTED]