# Mining Tests

Tests for the keystroke sanitizer and related components.

## Usage

```bash
# Run all tests
python run_tests.py

# Run specific component tests
python run_tests.py sanitizer
python run_tests.py fuzzy_matcher
python run_tests.py password_manager
python run_tests.py text_buffer
```

## Test Structure

- **test_keystroke_sanitizer.py**: Sanitizer test cases (password detection, redaction)
- **test_fuzzy_matcher.py**: Matching algorithm tests
- **test_password_manager.py**: Password storage and encryption
- **test_text_buffer.py**: Keystroke-to-text conversion

Test output is saved to `test_output/` for inspection.