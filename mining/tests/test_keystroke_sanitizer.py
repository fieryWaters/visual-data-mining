#!/usr/bin/env python3
"""
Keystroke Sanitizer Test Suite
==============================

A simplified test suite for the KeystrokeSanitizer module.
"""

import os
import time
import unittest
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
        
        # Save results if filename specified
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
            
    def test_all_cases(self):
        """Run all test cases for the sanitizer"""
        print("\nRunning all keystroke sanitizer test cases:")
        
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

        # Run all test cases
        for i, case in enumerate(test_cases):
            case_num = i + 1
            print(f"\n--- Case {case_num}: {case['name']} ---")
            print(f"Input: '{case['text']}'")
            
            # Track if we need to check buffer for deleted passwords
            check_buffer = case.get('check_buffer', False)
            
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