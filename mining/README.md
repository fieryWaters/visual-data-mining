# Computer Interaction Mining Tools

This subproject contains tools for collecting and processing computer interaction data, which can be used for machine learning research and analysis of human-computer interaction patterns.

## Components

- **keystroke_recorder.py**: Real-time keystroke capture module
- **keystroke_sanitizer.py**: Password detection and sanitization 
- **screen_recorder.py**: Rolling video capture
- **data_collector.py**: Main controller integrating all modules

## Setup

1. Create a virtual environment:
```
python -m venv mining-venv
source mining-venv/bin/activate  # On Windows: mining-venv\Scripts\activate
```

2. Install dependencies:
```
pip install -r requirements.txt
```

## Usage

### Data Collection

Run the main data collector:
```
python data_collector.py
```

Command-line options:
- `--no-screen`: Disable screen recording
- `--screen-minutes`: Minutes to keep in rolling screen recording (default: 10)
- `--screen-fps`: Frames per second for screen recording (default: 5)
- `--output-dir`: Output directory for logs (default: "logs")
- `--add-password`: Add a password to sanitize

### Individual Components

You can also run each component separately for testing:

```
python keystroke_recorder.py  # Test keystroke recording
python screen_recorder.py     # Test screen recording
```

## Privacy and Security

- All data collection occurs only on your own device with your consent
- Passwords are detected using fuzzy matching and sanitized from logs
- Raw keystroke data is never written directly to disk
- The system is designed with privacy-preserving features

See PROJECT_PURPOSE.md for more information about the project's ethical considerations.