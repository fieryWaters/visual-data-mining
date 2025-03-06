# Computer Interaction Mining Tools

This subproject contains tools for collecting and processing computer interaction data, which can be used for machine learning research and analysis of human-computer interaction patterns.

## Components

- **keystroke_recorder.py**: Real-time keystroke capture module
- **keystroke_sanitizer.py**: Password detection and sanitization 
- **screen_recorder.py**: Rolling video capture (InMemoryScreenRecorder)
- **data_collector.py**: Main controller integrating all modules

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

# Test password sanitization (detects and sanitizes passwords from keystroke data)
python3 keystroke_sanitizer.py --json
```

## Privacy and Security

- All data collection occurs only on your own device with your consent
- Passwords are detected using fuzzy matching and sanitized from logs
- Raw keystroke data is never written directly to disk
- The system is designed with privacy-preserving features

See PROJECT_PURPOSE.md for more information about the project's ethical considerations.