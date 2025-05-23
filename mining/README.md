# Visual Data Mining

Privacy-preserving keystroke and screen recording tool with password sanitization.

## Build Instructions

### Windows
```bash
# Open cmd.exe and ensure Python 3.11 is installed
py -3.11 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# Build data collection GUI (default)
python build_app.py

# Build data player
python build_app.py data_player.py
```
Executables will be created as `data_collection_GUI.exe` and/or `data_player.exe`

### Linux
```bash
# insall python3.12 using this link: https://www.python.org/downloads/release/python-3120/
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Build data collection GUI (default)
python build_app.py

# Build data player
python build_app.py data_player.py
```
Executables will be created as `data_collection_GUI` and/or `data_player`

## Running the Tool
Simply launch the executable file created above or run the GUI directly:
```bash
python3 data_collection_GUI.py
```

## Module Descriptions

- **data_collection_GUI.py**: Main GUI application with real-time recording controls
- **simple_collector.py**: Core controller integrating all recording components
- **keystroke_recorder.py**: Records keyboard and mouse inputs with event timestamps
- **screen_recorder.py**: In-memory screenshot recorder optimized for performance
- **keystroke_sanitizer.py**: Detects and removes passwords from keystroke data
- **data_player.py**: Tool to review and replay captured data

## Utils
- **password_manager.py**: Encrypted password storage with secure loading/saving
- **text_buffer.py**: Converts keystroke events to text with editing support
- **fuzzy_matcher.py**: Advanced algorithms for password detection

## Testing
```bash
python3 run_tests.py
```

## Privacy
- All sensitive data is sanitized before storage
- Passwords are detected and replaced with [REDACTED]
- Raw keystroke data is never written directly to disk