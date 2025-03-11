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
- Imports: standard lib first, then third-party, then local modules
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