# Computer Interaction Mining Tools

This subproject contains tools for collecting and processing computer interaction data, which can be used for machine learning research and analysis of human-computer interaction patterns.

## Components

- **keystroke_recorder.py**: Real-time keystroke capture module
- **keystroke_sanitizer.py**: Password detection and sanitization 
- **screen_recorder.py**: Rolling video capture (InMemoryScreenRecorder)
- **data_collector.py**: Main controller integrating all modules
- **utils/**: Utility modules:
  - **password_manager.py**: Secure password storage and management
  - **text_buffer.py**: Keystroke-to-text conversion with buffer tracking
  - **fuzzy_matcher.py**: Advanced password detection algorithms
- **tests/**: Comprehensive test suite for all components

## Setup

1. Create a virtual environment:
```bash
# Create a virtual environment (.venv is the standard for this project)
python3 -m venv .venv

# On macOS/Linux:
source .venv/bin/activate

# On Windows:
# .venv\Scripts\activate
```

2. Install dependencies:
```bash
pip3 install -r requirements.txt
```

Alternatively, use the automated setup script:
```bash
# Run the setup script which creates the venv and installs dependencies
bash setup.sh
```

## Usage

### Data Collection

Run the main data collector (always use python3 explicitly):
```bash
# Make sure your virtual environment is activated
python3 data_collector.py
```

Command-line options:
- `--no-screen`: Disable screen recording
- `--screen-minutes`: Minutes to keep in rolling screen recording (default: 10)
- `--screen-fps`: Target frames per second for screen recording (default: 5)
- `--output-dir`: Output directory for logs (default: "logs")
- `--add-password`: Add a password to sanitize
- `--no-json`: Disable sanitized JSON output
- `--process-interval`: Seconds between processing buffer (default: 10)

### Individual Components

You can also run each component separately for testing:

```bash
# Test keystroke recording (records keystrokes and shows events in real-time)
python3 keystroke_recorder.py

# Test screen recording (captures screenshots in memory and saves them to disk)
python3 screen_recorder.py

# Run tests for the sanitizer (includes automated test cases)
python3 -m unittest discover tests
```

### Code Structure

The system has been refactored for improved modularity and maintainability:

1. **Core Components**:
   - `keystroke_sanitizer.py`: Main sanitization module
   - `keystroke_recorder.py`: Captures keystrokes in real-time
   - `screen_recorder.py`: In-memory screenshot capture

2. **Utility Modules** (in `utils/`):
   - `password_manager.py`: Handles secure password storage
   - `text_buffer.py`: Converts keystrokes to text with editing capabilities
   - `fuzzy_matcher.py`: Provides advanced password detection algorithms

3. **Test Suite** (in `tests/`):
   - Comprehensive tests for all modules
   - Includes test cases for different input scenarios
   - Automated test runner with assertions

## Privacy and Security

- All data collection occurs only on your own device with your consent
- Passwords are detected using fuzzy matching and sanitized from logs
- Raw keystroke data is never written directly to disk
- The system is designed with privacy-preserving features

See PROJECT_PURPOSE.md for more information about the project's ethical considerations.

## Keystroke Sanitizer Architecture

The keystroke sanitizer consists of several modular components:

1. **KeystrokeSanitizer Class** (`keystroke_sanitizer.py`):
   - Core sanitization functionality
   - Integrates utility modules for text processing and password detection
   - Public API for sanitizing keystroke data
   - Handles sanitized data output formats

2. **Password Management** (`utils/password_manager.py`):
   - Secure storage of sensitive passwords
   - Encryption using industry-standard algorithms
   - Password list management functionality

3. **Text Buffer** (`utils/text_buffer.py`):
   - Converts raw keystroke events to readable text
   - Handles text editing operations (backspace, cursor movement)
   - Maintains buffer state history for enhanced detection

4. **Fuzzy Matching** (`utils/fuzzy_matcher.py`):
   - Advanced password detection algorithms
   - Multiple matching strategies (exact, word boundary, fuzzy)
   - Handles overlapping matches and false positives

### Password Detection Process

1. Raw keystroke events are converted to text using the TextBuffer
2. The FuzzyMatcher module analyzes both:
   - The final text after all editing operations
   - Intermediate buffer states to catch passwords that were typed and deleted
3. Multiple matching strategies are applied with varying thresholds
4. Detected passwords are marked with location data for sanitization
5. Sanitized output replaces sensitive data with placeholders

### Testing

The system includes a comprehensive test suite to verify functionality:

```bash
# Run all tests
python -m unittest discover tests

# Run a specific test module
python -m unittest tests.test_keystroke_sanitizer

# Run a specific test case
python -m unittest tests.test_keystroke_sanitizer.TestKeystrokeSanitizer.test_with_password
```

Test output files are saved to the `test_output` directory for inspection.

## Development

This codebase follows these principles:

- **Modularity**: Components are separated with clear responsibilities
- **Testability**: Every module has comprehensive unit tests 
- **Privacy-first**: Sensitive data is handled securely throughout
- **Usability**: The API is designed to be straightforward for integration