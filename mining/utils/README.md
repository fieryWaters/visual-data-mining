# Mining Utility Modules

This directory contains utility modules used by the keystroke mining system.

## Modules

### password_manager.py

A secure password management module that handles:
- Encrypted storage of passwords
- Loading and saving passwords to a secure file
- Password validation

### text_buffer.py

A text buffer implementation that:
- Converts keystroke events to text
- Tracks cursor position
- Handles text editing operations (insert, delete, backspace)
- Maintains buffer state history for analysis

### fuzzy_matcher.py

A fuzzy matching system for password detection:
- Multiple matching strategies (exact, word boundary, fuzzy)
- Handles overlapping matches
- Buffer state analysis for detecting passwords even if later deleted
- Match scoring and filtering

## Usage

These utilities are primarily used by the `keystroke_sanitizer.py` module but can be used independently.

Example:

```python
from utils.password_manager import PasswordManager
from utils.text_buffer import TextBuffer
from utils.fuzzy_matcher import FuzzyMatcher

# Process keystrokes
buffer = TextBuffer()
for keystroke in keystrokes:
    buffer.process_keystroke(keystroke)

# Detect passwords
password_manager = PasswordManager()
password_manager.setup_encryption("secure_password")
password_manager.add_password("secret123")

matches = FuzzyMatcher.find_all_matches(
    buffer.get_text(),
    password_manager.get_passwords(),
    buffer.get_buffer_states()
)
```

## Testing

Each utility has a corresponding test file in the `tests` directory.