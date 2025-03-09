# Mining System Tests

This directory contains tests for the keystroke mining system.

## Running Tests

To run all tests:

```
cd /path/to/mining
python -m unittest discover tests
```

To run a specific test file:

```
python -m unittest tests/test_keystroke_sanitizer.py
```

To run a specific test case:

```
python -m unittest tests.test_keystroke_sanitizer.TestKeystrokeSanitizer.test_with_password
```

## Test Files

### test_keystroke_sanitizer.py

Tests for the `keystroke_sanitizer.py` module, including:
- Password detection in simple and complex text
- Sanitization of password data in keystrokes
- Handling of backspaces and editing
- Detection of multiple passwords

### test_fuzzy_matcher.py

Tests for the `utils/fuzzy_matcher.py` module, including:
- Exact and fuzzy matching algorithms
- Handling of overlapping matches
- Buffer state analysis

### test_text_buffer.py

Tests for the `utils/text_buffer.py` module, including:
- Keystroke-to-text conversion
- Cursor movement
- Text editing operations

### test_password_manager.py

Tests for the `utils/password_manager.py` module, including:
- Secure password storage
- Password encryption and decryption
- Password management operations

### test_sanitizer.py

Legacy test file that contains manual testing functionality (interactive).

## Test Data

The test output is stored in the `test_output` directory at the project root.
This includes JSON output files showing sanitized keystroke data.

## Dependencies

Make sure to install all dependencies before running tests:

```
pip install -r requirements.txt
```