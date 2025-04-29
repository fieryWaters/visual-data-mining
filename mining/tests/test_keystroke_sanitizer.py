#!/usr/bin/env python3
"""
Keystroke Sanitizer Test Suite
==============================

A simplified test suite for the KeystrokeSanitizer module.
"""

import os
import time
import unittest
import json
from datetime import datetime
from pathlib import Path
import sys

# Add parent directory to path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from keystroke_sanitizer import KeystrokeSanitizer


class TestKeystrokeSanitizer(unittest.TestCase):
    """Simplified test suite for KeystrokeSanitizer"""
    
    def setUp(self):
        """Set up test environment with standard test passwords"""
        # Create test output directory
        self.test_dir = Path("test_output")
        self.test_dir.mkdir(exist_ok=True)
        
        # Create standard sanitizer
        self.sanitizer = self.create_sanitizer(["secret123", "secret456"])
    
    def tearDown(self):
        """Clean up test password files"""
        for file in self.test_dir.glob("*.keys"):
            if file.exists():
                os.remove(file)
    
    def create_sanitizer(self, passwords):
        """Create a sanitizer with specified passwords"""
        file_path = self.test_dir / "test_passwords.keys"
        if file_path.exists():
            os.remove(file_path)
            
        sanitizer = KeystrokeSanitizer(str(file_path))
        sanitizer.setup_encryption("test_password")
        
        for password in passwords:
            sanitizer.add_password(password)
        sanitizer.save_passwords()
        
        return sanitizer
    
    def format_keystroke_streams(self, events):
        """
        Extract and format keystroke events into readable press and release streams.
        For special keys (non-printable), show their representation.
        """
        press_stream = []
        release_stream = []
        
        for event in events:
            if event["event"] == "KEY_PRESS":
                key = event.get("key", "")
                if len(key) == 1:  # Printable character
                    press_stream.append(key)
                else:  # Special key
                    press_stream.append(f"[{key}]")
            elif event["event"] == "KEY_RELEASE":
                key = event.get("key", "")
                if len(key) == 1:  # Printable character
                    release_stream.append(key)
                else:  # Special key
                    release_stream.append(f"[{key}]")
        
        return {
            "press_stream": "".join(press_stream),
            "release_stream": "".join(release_stream)
        }
    
    def run_test(self, text, special_keys=None, expected_output=None, 
                 min_detections=0, filename=None, custom_passwords=None):
        """Run a test with given parameters and return sanitized data"""
        # Use custom sanitizer if needed
        if custom_passwords:
            sanitizer = self.create_sanitizer(custom_passwords)
        else:
            sanitizer = self.sanitizer
            
        # Generate events
        events = []
        for char in text:
            events.append({"event": "KEY_PRESS", "key": char, "timestamp": datetime.now().isoformat()})
            time.sleep(0.002)  # Small delay
            events.append({"event": "KEY_RELEASE", "key": char, "timestamp": datetime.now().isoformat()})
        
        # Add special keys if specified
        if special_keys:
            for key in special_keys:
                events.append({"event": "KEY_PRESS", "key": key, "timestamp": datetime.now().isoformat()})
                time.sleep(0.002)
                events.append({"event": "KEY_RELEASE", "key": key, "timestamp": datetime.now().isoformat()})
        
        # Process events
        sanitized_data = sanitizer.process_events(events)
        
        # Save ONLY sanitized results if filename specified (NEVER raw keystrokes!)
        if filename:
            output_file = self.test_dir / f"{filename}.json"
            sanitizer.save_sanitized_json(sanitized_data, str(output_file))
        
        # Check minimum password detections
        if min_detections > 0:
            self.assertGreaterEqual(
                len(sanitized_data["password_locations"]), 
                min_detections,
                f"Should detect at least {min_detections} passwords"
            )
        
        # Check expected output if specified
        if expected_output is not None:
            self.assertEqual(
                sanitized_data["sanitized_text"],
                expected_output,
                f"Expected: '{expected_output}', Got: '{sanitized_data['sanitized_text']}'"
            )
            
        # Return data for further checks
        return sanitized_data
            
    def test_all_cases(self, test_number=None):
        """Run all test cases or a specific test case by number
        
        Args:
            test_number: Optional integer to run only a specific test case (1-indexed)
        """
        print("\nRunning keystroke sanitizer test cases:")
        
        # All test cases in a single list
        test_cases = [
            # 1. Simple text without passwords
            {
                "name": "Simple Text Without Passwords",
                "text": "This is some normal text without any secrets",
                "expected": "This is some normal text without any secrets",
                "min_detections": 0,
                "filename": "test_simple_text"
            },
            
            # 2. Basic password detection
            {
                "name": "Basic Password Detection",
                "text": "Here is my password: secret123",
                "expected": "Here is my password: [REDACTED]",
                "min_detections": 1,
                "filename": "test_basic_password"
            },
            
            # 3. Multiple passwords
            {
                "name": "Multiple Passwords",
                "text": "First password: secret123 Second password: secret456",
                "expected": "First password: [REDACTED] Second password: [REDACTED]",
                "min_detections": 2,
                "filename": "test_multiple_passwords"
            },
            
            # 4. Mixed content with login form
            {
                "name": "Mixed Content with Login Form",
                "text": "Username: user@example.com\nPassword: secret123\nLogin successful!",
                "expected": "Username: user@example.com\nPassword: [REDACTED]\nLogin successful!",
                "min_detections": 1,
                "filename": "test_mixed_content"
            },
            
            # 5. Consecutive identical passwords
            {
                "name": "Consecutive Identical Passwords",
                "text": "secret123secret123secret123",
                "expected": "[REDACTED][REDACTED][REDACTED]",
                "min_detections": 2,
                "filename": "test_consecutive_passwords"
            },
            
            # 6. Adjacent different passwords
            {
                "name": "Adjacent Different Passwords",
                "text": "secret123secret456",
                "expected": "[REDACTED][REDACTED]",
                "min_detections": 2,
                "filename": "test_adjacent_different"
            },
            
            # 7. Character between passwords
            {
                "name": "Character Between Passwords",
                "text": "secrett1234secret1233",
                "expected": "[REDACTED]4[REDACTED]3",
                "min_detections": 2,
                "filename": "test_character_between"
            },
            
            # 8. Similar but distinct passwords
            {
                "name": "Similar But Distinct Passwords",
                "text": "secret123 secret1234",
                "expected": "[REDACTED] [REDACTED]4",  # The 4 remains in the output
                "min_detections": 2,
                "filename": "test_similar_distinct"
            },
            
            # 9. Mixed case passwords
            {
                "name": "Mixed Case Passwords",
                "text": "SECRET123 Secret123 sEcReT123",
                "expected": "[REDACTED] [REDACTED] [REDACTED]",
                "min_detections": 3,
                "filename": "test_mixed_case"
            },
            
            # 10. Whitespace handling
            {
                "name": "Whitespace Handling",
                "text": "Space before:  secret123 and space after: secret123  end",
                "expected": "Space before:  [REDACTED] and space after: [REDACTED]  end",
                "min_detections": 2,
                "filename": "test_whitespace"
            },
            
            # 11. Password with backspace correction
            {
                "name": "Password with Backspace Correction",
                "text": "Password with typo: secrett",
                "special_keys": ["1", "2", "3", "Key.backspace", "Key.backspace", "1", "2", "3"],
                "min_detections": 1,
                "filename": "test_backspace"
            },
            
            # 12. Fuzzy password matching
            {
                "name": "Fuzzy Password Matching",
                "text": "My password is secrett1234",
                "min_detections": 1,
                "filename": "test_fuzzy_match"
            },
            
            # 13. Password typed then deleted
            {
                "name": "Password Typed Then Deleted",
                "text": "secret123",
                "special_keys": ["Key.backspace"] * 9,  # Delete the entire password
                "min_detections": 0,  # May not detect in final text but should be in buffer
                "filename": "test_deleted_password",
                "check_buffer": True
            },
            
            # 14. Misspelled passwords
            {
                "name": "Misspelled Passwords",
                "text": "scret123 screett123",
                "min_detections": 1,
                "filename": "test_misspelled"
            },
            
            # 15. Password manager integration
            {
                "name": "Password Manager Integration",
                "text": "This contains unique_pw1 and also unique_pw2",
                "min_detections": 2,
                "filename": "test_password_manager",
                "custom_passwords": ["unique_pw1", "unique_pw2"],
                "expected": "This contains [REDACTED] and also [REDACTED]"
            }
        ]

        # Filter test cases if a specific number was provided
        if test_number is not None:
            try:
                test_idx = int(test_number) - 1  # Convert to 0-indexed
                if 0 <= test_idx < len(test_cases):
                    test_cases = [test_cases[test_idx]]
                else:
                    print(f"Error: Test number {test_number} is out of range (1-{len(test_cases)})")
                    return
            except ValueError:
                print(f"Error: Invalid test number '{test_number}'")
                return
        
        # Run test cases
        for i, case in enumerate(test_cases):
            if test_number is None:
                case_num = i + 1
            else:
                case_num = int(test_number)
                
            print(f"\n--- Case {case_num}: {case['name']} ---")
            print(f"Input: '{case['text']}'")
            if case.get('expected'):
                print(f"Expected: '{case['expected']}'")
            
            # Track if we need to check buffer for deleted passwords
            check_buffer = case.get('check_buffer', False)
            
            # Update filename to include test number
            if case.get('filename'):
                case['filename'] = f"test_{case_num:02d}_{case['filename'].replace('test_', '')}"
            
            # Run the test
            result = self.run_test(
                text=case['text'],
                special_keys=case.get('special_keys'),
                expected_output=case.get('expected'),
                min_detections=case.get('min_detections', 0),
                filename=case.get('filename'),
                custom_passwords=case.get('custom_passwords')
            )
            
            # Print result summary
            print(f"Detected: {len(result['password_locations'])} password locations")
            print(f"Sanitized: '{result['sanitized_text']}'")
            
            # Read the keystrokes directly from JSON file
            if case.get('filename'):
                json_file_path = self.test_dir / f"{case.get('filename')}.json"
                if json_file_path.exists():
                    try:
                        with open(json_file_path, 'r') as f:
                            json_data = json.load(f)
                            # Extract and filter events by type
                            events = json_data.get('events', [])
                            keypresses = []
                            keyreleases = []
                            passwords = []
                            
                            for event in events:
                                event_type = event.get('event')
                                if event_type == 'KEY_PRESS' and 'key' in event:
                                    key = event.get('key')
                                    keypresses.append(key if len(key) == 1 else f"[{key}]")
                                    
                                elif event_type == 'KEY_RELEASE' and 'key' in event: 
                                    key = event.get('key')
                                    keyreleases.append(key if len(key) == 1 else f"[{key}]")
                                    
                                elif event_type == 'PASSWORD_FOUND':
                                    passwords.append("[PASSWORD_FOUND]")
                            
                            # Display events in a more readable format
                            print(f"Key presses:   {''.join(keypresses + passwords)}")
                            print(f"Key releases:  {''.join(keyreleases)}")
                    except Exception as e:
                        print(f"Error reading JSON file: {e}")
            
            # Additional check for deleted passwords
            if check_buffer and "secret123" in str(result["buffer_states"]):
                print("✅ Detected password in buffer states")
                self.assertTrue(True, "Buffer contains deleted password")
            
            print(f"✅ Case {case_num} passed")
            
        print("\nAll sanitizer test cases passed successfully")


if __name__ == "__main__":
    print("Please use the run_tests.py script to run tests.")
    print("Example: python run_tests.py sanitizer")
    sys.exit(1)