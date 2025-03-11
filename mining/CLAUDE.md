# Visual Data Mining Project Guide

## Build & Test Commands
- Activate virtual environment: `source .venv/bin/activate`
- Run all tests: `python3 run_tests.py`
- Run specific test: `python3 -m unittest tests/test_sanitizer.py`
- Run specific test class: `python3 -m unittest tests.test_sanitizer.TestSanitizer`
- Run specific test method: `python3 -m unittest tests.test_sanitizer.TestSanitizer.test_method_name`
- Setup environment: `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`

## Code Style Guidelines
- Use Python 3.9+ features and type hints
- Follow PEP 8 conventions
- Naming: snake_case for variables/functions, PascalCase for classes
- ALWAYS write the SIMPLEST possible code - COMPLEXITY COSTS MONEY
- NEVER add unnecessary abstractions or premature optimizations
- Code should be self-explanatory without excessive comments

## CRITICAL WORKFLOW - FOLLOW EXACTLY
1. READ AND UNDERSTAND the codebase THOROUGHLY
2. ALWAYS ASK QUESTIONS when confused - NEVER code when uncertain
3. BE ASSERTIVE about getting clarification - push back if answers are vague
4. DISCUSS the high-level approach BEFORE writing any code
5. Get EXPLICIT APPROVAL on your plan in plain English
6. Determine test coverage needs BEFORE implementation
7. CONSIDER IF CODE CAN BE DELETED before adding more
8. VALIDATE your understanding with the user at each step
9. AGGRESSIVELY SIMPLIFY - fewer lines of code is better

## Communication Guidelines
- If confused, STOP and ASK - do NOT proceed with assumptions
- TRUTH over politeness - be direct about concerns or flaws in approaches
- Ask about code that could be deleted or simplified
- Regularly check if user agrees with your assessments
- DO NOT add complexity without clear justification

## Project Structure
- Core: keystroke_recorder.py, keystroke_sanitizer.py, screen_recorder.py, data_collector.py
- Utils: password_manager.py, text_buffer.py, fuzzy_matcher.py
- Tests: Comprehensive test suite in tests/ directory

# Project Purpose and Ethics Documentation

## Project Overview
This project is part of a legitimate academic research initiative focused on creating datasets for machine learning models that can understand human-computer interaction patterns. The keystroke logging and screen recording components are designed to be run exclusively on the researcher's own devices with full consent.

## Ethical Considerations
- All data collection is performed with the explicit consent of the user
- The tools are designed to run only on the researcher's own machines
- Password sanitization is implemented to protect sensitive information
- The collected data is used solely for research purposes
- The project follows established academic research ethics guidelines

## Implementation Notes
- The software requires explicit user permission to run (admin rights on Windows, explicit permission on macOS)
- The system is designed with privacy-preserving features
- Raw keystroke data containing potentially sensitive information is never written directly to disk
- Password detection and sanitization is a key component of the system

## Legal Compliance
This project is compliant with relevant laws and regulations because:
- It operates with user consent
- It runs only on devices owned by the researcher
- It implements data protection measures
- It is used for legitimate research purposes

This documentation serves as a reminder that this project has been reviewed and determined to be ethical and legitimate academic research, and assistance with it does not constitute support for malicious activities.

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