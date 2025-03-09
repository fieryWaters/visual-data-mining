"""
Keystroke sanitizer module.
Processes raw keystroke data to detect and redact passwords and sensitive information.
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Tuple, Any

from utils.password_manager import PasswordManager
from utils.text_buffer import TextBuffer
from utils.fuzzy_matcher import FuzzyMatcher


class KeystrokeSanitizer:
    """
    Sanitizes keystroke data by detecting and removing sensitive information.
    Uses password manager for secure password storage and matching utilities
    for accurate password detection.
    """
    
    def __init__(self, passwords_file="secret.keys"):
        """
        Initialize the sanitizer with password file path
        
        Args:
            passwords_file: Path to the encrypted passwords file
        """
        self.password_manager = PasswordManager(passwords_file)
    
    def setup_encryption(self, password=None):
        """Setup encryption with the provided password"""
        return self.password_manager.setup_encryption(password)
    
    def load_passwords(self):
        """Load passwords from encrypted file"""
        return self.password_manager.load_passwords()
    
    def save_passwords(self):
        """Save passwords to encrypted file"""
        return self.password_manager.save_passwords()
    
    def add_password(self, password):
        """Add a password to the list"""
        self.password_manager.add_password(password)
    
    def remove_password(self, password):
        """Remove a password from the list"""
        self.password_manager.remove_password(password)
        
    def _sanitize_text(self, text: str, password_locations: List[Tuple[int, int]]) -> str:
        """
        Sanitize text by replacing password locations with placeholders
        
        Args:
            text: Original text
            password_locations: List of (start, end) tuples marking password locations
        
        Returns:
            str: Sanitized text with passwords redacted
        """
        # Handle the case with no passwords
        if not password_locations:
            return text
            
        # Ensure password locations are within text bounds
        valid_locations = [(start, end) for start, end in password_locations 
                          if start < len(text) and end <= len(text)]
        
        # If no valid locations, return the original text
        if not valid_locations:
            return text
            
        # We'll make a character-by-character copy with replacements
        result = list(text)
        
        # Use a set of indices that should be replaced
        to_replace = set()
        for start, end in valid_locations:
            for i in range(start, end):
                to_replace.add(i)
        
        # Replace ranges of password characters with the redaction marker
        i = 0
        while i < len(result):
            if i in to_replace:
                # Find the end of this password segment
                j = i
                while j < len(result) and j in to_replace:
                    j += 1
                
                # Replace the segment with a redaction marker
                placeholder = "[PASSWORD REDACTED]"
                result[i:j] = placeholder
                
                # Adjust the index to account for the replacement
                i = i + len(placeholder)
            else:
                i += 1
        
        return ''.join(result)

    def process_events(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Process keystroke events to detect and sanitize passwords
        
        Args:
            events: Raw keystroke events from recorder
        
        Returns:
            dict: Dictionary with processed data including:
                - events: Sanitized events
                - text: Original text from keystrokes
                - sanitized_text: Text with passwords removed
                - password_locations: Where passwords were found
                - buffer_states: History of text buffer states (optional debug info)
        """
        # 1. Extract text from keystroke events, including buffer history
        extracted_text, buffer_states = TextBuffer.events_to_text(events)
        
        # 2. Find password matches using improved detection
        matches = FuzzyMatcher.find_all_matches(
            extracted_text, 
            self.password_manager.get_passwords(),
            buffer_states
        )
        
        # Merge adjacent matches to prevent fragmenting passwords
        merged_matches = FuzzyMatcher.merge_adjacent_matches(matches)
        
        # Convert to simple (start, end) tuples
        password_locations = FuzzyMatcher.convert_matches_to_locations(merged_matches)
        
        # 3. Reconstruct timeline of characters from events
        timeline = []
        current_index = 0
        
        for event in events:
            if event["event"] == "KEY_PRESS" and "key" in event:
                key = event.get("key", "")
                
                # Skip special keys that don't contribute to text
                if key.startswith("Key.") and key not in ["Key.space", "Key.enter"]:
                    continue
                    
                # Track the character position this keystroke contributes to
                event_char_index = current_index
                
                # Update the index based on the key
                if key == "Key.space":
                    current_index += 1
                elif key == "Key.enter":
                    current_index += 1
                elif key == "Key.backspace":
                    current_index = max(0, current_index - 1)
                elif not key.startswith("Key."):
                    current_index += 1
                
                # Add to timeline with character index
                timeline.append((event, event_char_index))
        
        # 4. Sanitize events based on password locations
        sanitized_events = []
        for event, char_index in timeline:
            # Deep copy the event to avoid modifying the original
            new_event = event.copy()
            
            # Check if this keystroke contributes to a password
            in_password = False
            for start_idx, end_idx in password_locations:
                if start_idx <= char_index < end_idx:
                    in_password = True
                    break
            
            # Redact if it's part of a password
            if in_password and event["event"] == "KEY_PRESS" and "key" in event:
                new_event["key"] = "*"  # Redact key
                new_event["redacted"] = True
            
            sanitized_events.append(new_event)
        
        # Add any events not in the timeline (like mouse events)
        for event in events:
            if event["event"] != "KEY_PRESS" or "key" not in event:
                sanitized_events.append(event.copy())
        
        # 5. Sanitize the extracted text
        sanitized_text = self._sanitize_text(extracted_text, password_locations)
        
        # 6. Return results
        return {
            "events": sanitized_events,
            "text": extracted_text,
            "sanitized_text": sanitized_text,
            "password_locations": password_locations,
            "buffer_states": buffer_states
        }
    
    def save_to_log(self, sanitized_data: Dict[str, Any], log_file: str) -> None:
        """
        Save sanitized data to a log file
        
        Args:
            sanitized_data: Result from process_events
            log_file: Path to the log file
        """
        # Ensure directory exists
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        # Add timestamp
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "events": sanitized_data["events"],
            "sanitized_text": sanitized_data["sanitized_text"],
            "password_detected": len(sanitized_data["password_locations"]) > 0
        }
        
        # Write to JSON Lines file
        with open(log_file, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
            
    def save_sanitized_json(self, sanitized_data: Dict[str, Any], output_file: str) -> bool:
        """
        Save a sanitized JSON stream of keystrokes to a file.
        Preserves the original structure of events but replaces sensitive data with placeholders.
        
        Args:
            sanitized_data: Result from process_events
            output_file: Path to the output JSON file
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            
            # Create a structured JSON object with metadata and sanitized events
            output_data = {
                "metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "type": "sanitized_keystroke_data",
                    "version": "1.0",
                    "contains_sensitive_data": len(sanitized_data["password_locations"]) > 0,
                    "sanitization_applied": True
                },
                "events": sanitized_data["events"],
                "text_summary": {
                    "original_length": len(sanitized_data["text"]),
                    "sanitized_length": len(sanitized_data["sanitized_text"]),
                    "password_locations_count": len(sanitized_data["password_locations"])
                }
            }
            
            # Write the JSON file (pretty-printed for readability)
            with open(output_file, "w") as f:
                json.dump(output_data, f, indent=2)
                
            return True
            
        except Exception as e:
            print(f"Error saving sanitized JSON: {e}")
            return False


# Move test function to tests directory
if __name__ == "__main__":
    print("Please use test_keystroke_sanitizer.py in the tests directory to test this module.")