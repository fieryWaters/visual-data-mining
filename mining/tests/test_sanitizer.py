"""
Test framework for keystroke sanitizer that simulates keypresses
"""

import time
import json
import os
from datetime import datetime

# Create mock keystroke events
def generate_mock_keystrokes(test_case):
    """
    Generate mock keystroke events for testing
    
    Args:
        test_case: Dictionary with test case parameters
    
    Returns:
        List of keystroke events
    """
    events = []
    text = test_case["text"]
    include_password = test_case.get("include_password", False)
    special_sequence = test_case.get("special_sequence", None)
    
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
        # Add a simulated password (secret123)
        password = "secret123"
        
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
    
    return events

def test_sanitizer(output_dir="test_output"):
    """Run tests on the keystroke sanitizer with mock data"""
    from keystroke_sanitizer import KeystrokeSanitizer
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Create test cases
    test_cases = [
        {
            "name": "simple_text",
            "text": "This is some normal text without secrets",
            "include_password": False
        },
        {
            "name": "with_password",
            "text": "Here is my password:",
            "include_password": True
        },
        {
            "name": "with_backspace",
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
            "text": "First password: secret123 Second password: secret456",
            "include_password": False
        },
        {
            "name": "mixed_content",
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
        }
    ]
    
    # Initialize sanitizer
    sanitizer = KeystrokeSanitizer()
    sanitizer.setup_encryption("test_password")  # Use a fixed test password
    
    # Add test passwords to sanitize
    sanitizer.add_password("secret123")
    sanitizer.add_password("secret456")
    sanitizer.save_passwords()
    
    print(f"Testing keystroke sanitizer with {len(test_cases)} test cases...")
    
    # Process each test case
    for i, test_case in enumerate(test_cases):
        print(f"\nTest Case {i+1}: {test_case['name']}")
        
        # Generate mock events
        events = generate_mock_keystrokes(test_case)
        
        print(f"Generated {len(events)} mock keystroke events")
        
        # Process the events
        sanitized_data = sanitizer.process_events(events)
        
        # Check for password detection
        password_count = len(sanitized_data["password_locations"])
        print(f"Password detection: {password_count} instances found")
        
        # Save results to JSON
        output_file = os.path.join(output_dir, f"test_{test_case['name']}.json")
        sanitizer.save_sanitized_json(sanitized_data, output_file)
        print(f"Saved sanitized JSON to {output_file}")
        
        # Print the sanitized text
        print("\nOriginal text:")
        print(sanitized_data["text"])
        
        print("\nSanitized text:")
        print(sanitized_data["sanitized_text"])
        
        if password_count > 0:
            print("\nPassword locations:")
            for start, end in sanitized_data["password_locations"]:
                print(f"  Position {start}-{end}: '{sanitized_data['text'][start:end]}'")
    
    print("\nAll tests completed successfully!")
    return True

if __name__ == "__main__":
    test_sanitizer()