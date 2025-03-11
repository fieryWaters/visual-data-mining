"""
Manual Test Framework for Keystroke Sanitizer
============================================

This script provides a manual testing framework for the keystroke sanitizer.
It simulates typing and generates mock keystroke events to test the sanitizer's
ability to detect and redact passwords in various scenarios.

Unlike the unittest framework in test_keystroke_sanitizer.py, this script:
1. Doesn't use assertion-based testing
2. Focuses on generating realistic keystroke data
3. Creates visual output for manual inspection
4. Saves test results to JSON files for further analysis

This is useful for:
- Manual verification of sanitizer behavior
- Generating test data for debugging
- Visualizing the sanitization process
"""

import time
import json
import os
from datetime import datetime
from pathlib import Path

# Create mock keystroke events
def generate_mock_keystrokes(test_case):
    """
    Generate mock keystroke events for testing
    
    Creates realistic keystroke events with timestamps, simulating
    a user typing text, possibly including a password and special keys.
    
    Args:
        test_case: Dictionary with test case parameters:
            - text: Base text to type
            - include_password: Whether to add a password
            - special_sequence: Optional list of special key actions
            - custom_password: Optional custom password to use instead of default
    
    Returns:
        List of keystroke events as dictionaries
    """
    events = []
    text = test_case["text"]
    include_password = test_case.get("include_password", False)
    special_sequence = test_case.get("special_sequence", None)
    custom_password = test_case.get("custom_password", None)
    
    print(f"  Generating keystrokes for: '{text}'")
    
    # Add a timestamp for each character with small time increments
    for i, char in enumerate(text):
        # Simulate a realistic typing delay
        timestamp = datetime.now().isoformat()
        
        # Create key press event
        events.append({
            "event": "KEY_PRESS",
            "key": char,
            "timestamp": timestamp
        })
        
        # Add short delay for key release
        time.sleep(0.01)
        timestamp = datetime.now().isoformat()
        
        # Create key release event
        events.append({
            "event": "KEY_RELEASE",
            "key": char,
            "timestamp": timestamp
        })
    
    # Add special sequence if provided (for backspace testing, etc.)
    if special_sequence:
        print(f"  Adding special sequence of {len(special_sequence)} actions")
        for action in special_sequence:
            timestamp = datetime.now().isoformat()
            
            # Create event based on action type
            if action["type"] == "press":
                events.append({
                    "event": "KEY_PRESS",
                    "key": action["key"],
                    "timestamp": timestamp
                })
            elif action["type"] == "release":
                events.append({
                    "event": "KEY_RELEASE",
                    "key": action["key"],
                    "timestamp": timestamp
                })
            
            # Add short delay between actions
            time.sleep(0.01)
    
    # Add password if requested
    if include_password:
        # Use custom password if provided, otherwise default
        password = custom_password if custom_password else "secret123"
        print(f"  Adding password: '{password}'")
        
        # Add space before password
        events.append({
            "event": "KEY_PRESS",
            "key": " ",
            "timestamp": datetime.now().isoformat()
        })
        
        # Type the password
        for char in password:
            timestamp = datetime.now().isoformat()
            events.append({
                "event": "KEY_PRESS",
                "key": char,
                "timestamp": timestamp
            })
            
            # Add key release events too
            time.sleep(0.01)
            timestamp = datetime.now().isoformat()
            events.append({
                "event": "KEY_RELEASE",
                "key": char,
                "timestamp": timestamp
            })
    
    print(f"  ✓ Generated {len(events)} keystroke events")
    return events

def visualize_password_detection(text, locations):
    """Create a visual representation of password detection in text"""
    if not locations:
        return text + "\n" + " " * len(text)
    
    # Create a marker line showing where passwords are detected
    marker = [" "] * len(text)
    for start, end in locations:
        for i in range(start, min(end, len(text))):
            marker[i] = "^"
    
    # Return text with marker line below
    return text + "\n" + "".join(marker)

def test_sanitizer(output_dir="test_output"):
    """
    Run manual tests on the keystroke sanitizer with mock data
    
    Creates several test cases to verify the sanitizer's behavior with:
    - Simple text without passwords
    - Text with an explicit password
    - Text with backspaces (simulating typos)
    - Text with multiple passwords
    - Mixed content (like a login form)
    - Adjacent identical passwords
    - Passwords with mixed casing
    - Passwords with leading/trailing whitespace
    
    Args:
        output_dir: Directory to save test output files
        
    Returns:
        True if all tests completed
    """
    from keystroke_sanitizer import KeystrokeSanitizer
    
    print("\n" + "="*80)
    print("KEYSTROKE SANITIZER MANUAL TEST SUITE")
    print("="*80)
    
    # Create output directory
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)
    print(f"Test output will be saved to: {output_dir.absolute()}")
    
    # Create test cases
    test_cases = [
        {
            "name": "simple_text",
            "description": "Simple text without passwords",
            "text": "This is some normal text without secrets",
            "include_password": False
        },
        {
            "name": "with_password",
            "description": "Text with an explicit password",
            "text": "Here is my password:",
            "include_password": True
        },
        {
            "name": "with_backspace",
            "description": "Text with backspaces (simulating typos)",
            "text": "Password with typo: secrett",  # We'll add and delete characters manually
            "include_password": False,
            "special_sequence": [
                {"key": "1", "type": "press"},
                {"key": "2", "type": "press"},
                {"key": "3", "type": "press"},
                {"key": "Key.backspace", "type": "press"},
                {"key": "Key.backspace", "type": "press"},
                {"key": "1", "type": "press"},
                {"key": "2", "type": "press"},
                {"key": "3", "type": "press"}
            ]
        },
        {
            "name": "multiple_passwords",
            "description": "Text with multiple passwords",
            "text": "First password: secret123 Second password: secret456",
            "include_password": False
        },
        {
            "name": "mixed_content",
            "description": "Mixed content like a login form",
            "text": "Username: user@example.com\nPassword: ",
            "include_password": True,
            "special_sequence": [
                {"key": "Key.enter", "type": "press"},
                {"key": "L", "type": "press"},
                {"key": "o", "type": "press"},
                {"key": "g", "type": "press"},
                {"key": "i", "type": "press"},
                {"key": "n", "type": "press"},
                {"key": " ", "type": "press"},
                {"key": "s", "type": "press"},
                {"key": "u", "type": "press"},
                {"key": "c", "type": "press"},
                {"key": "c", "type": "press"},
                {"key": "e", "type": "press"},
                {"key": "s", "type": "press"},
                {"key": "s", "type": "press"},
                {"key": "f", "type": "press"},
                {"key": "u", "type": "press"},
                {"key": "l", "type": "press"},
                {"key": "!", "type": "press"}
            ]
        },
        # New test cases for the improved sanitizer
        {
            "name": "adjacent_passwords",
            "description": "Adjacent identical passwords",
            "text": "Look at these passwords: secret123secret123secret123",
            "include_password": False
        },
        {
            "name": "mixed_case_passwords",
            "description": "Passwords with mixed casing",
            "text": "These are variations: Secret123 SECRET123 sEcReT123",
            "include_password": False
        },
        {
            "name": "whitespace_passwords",
            "description": "Passwords with leading/trailing whitespace",
            "text": "Space before:  secret123 and space after: secret123  end",
            "include_password": False
        },
        {
            "name": "different_adjacent_passwords",
            "description": "Different adjacent passwords",
            "text": "Adjacent different: secret123secret456",
            "include_password": False
        },
        {
            "name": "very_similar_passwords",
            "description": "Very similar but distinct passwords",
            "text": "Similar passwords: secret123 secret1234 secrett123",
            "include_password": False
        }
    ]
    
    # Initialize sanitizer
    print("\nInitializing keystroke sanitizer...")
    sanitizer = KeystrokeSanitizer()
    sanitizer.setup_encryption("test_password")  # Use a fixed test password
    
    # Add test passwords to sanitize
    print("Adding passwords to detect: 'secret123', 'secret456', 'secret1234'")
    sanitizer.add_password("secret123")
    sanitizer.add_password("secret456")
    sanitizer.save_passwords()
    
    print(f"\nRunning {len(test_cases)} test cases...")
    
    # Process each test case
    for i, test_case in enumerate(test_cases):
        print("\n" + "="*80)
        print(f"TEST CASE {i+1}: {test_case['name']}")
        print("-"*80)
        print(f"Description: {test_case['description']}")
        print("="*80)
        
        # Generate mock events
        print("STEP 1: Generating mock keystroke events")
        events = generate_mock_keystrokes(test_case)
        
        # Process the events
        print("STEP 2: Processing events through sanitizer")
        sanitized_data = sanitizer.process_events(events)
        
        # Check for password detection
        password_count = len(sanitized_data["password_locations"])
        print(f"STEP 3: Analyzing results")
        
        if password_count > 0:
            print(f"  ✓ Detected {password_count} potential password(s)")
        else:
            print(f"  ⚠ No passwords detected")
        
        # Check if text was modified
        if sanitized_data["text"] != sanitized_data["sanitized_text"]:
            print(f"  ✓ Text was modified (passwords redacted)")
        else:
            print(f"  ⚠ Text was not modified")
        
        # Save results to JSON
        print("STEP 4: Saving results to file")
        output_file = output_dir / f"test_{test_case['name']}.json"
        sanitizer.save_sanitized_json(sanitized_data, output_file)
        print(f"  ✓ Saved sanitized JSON to {output_file}")
        
        # Print the sanitized text
        print("\nOriginal text:")
        print("-"*40)
        print(sanitized_data["text"])
        
        print("\nSanitized text:")
        print("-"*40)
        print(sanitized_data["sanitized_text"])
        
        # Visual representation of password detection
        print("\nPassword detection (^ marks detected characters):")
        print("-"*40)
        print(visualize_password_detection(sanitized_data["text"], sanitized_data["password_locations"]))
        
        if password_count > 0:
            print("\nPassword locations:")
            print("-"*40)
            for start, end in sanitized_data["password_locations"]:
                detected_text = sanitized_data["text"][start:end]
                print(f"  Position {start}-{end}: '{detected_text}'")
                
                # Highlight which password matches
                if detected_text.lower() == "secret123":
                    print(f"  → Matches 'secret123' (case insensitive)")
                elif detected_text.lower() == "secret456":
                    print(f"  → Matches 'secret456' (case insensitive)")
                elif detected_text.lower() == "secret1234":
                    print(f"  → Matches 'secret1234' (case insensitive)")
                else:
                    print(f"  → Fuzzy match (similarity to stored passwords)")
    
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"✓ All {len(test_cases)} test cases completed")
    print(f"✓ Test output saved to {output_dir.absolute()}")
    print(f"✓ Review the JSON files for detailed results")
    print("="*80)
    
    return True

if __name__ == "__main__":
    test_sanitizer()