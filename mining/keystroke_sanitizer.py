"""
Keystroke sanitizer module.
Processes raw keystroke data to detect and remove passwords, replacing them
with PASSWORD_FOUND events in the output stream.
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
    """
    
    def __init__(self, passwords_file="secret.keys"):
        """Initialize with password file path"""
        self.password_manager = PasswordManager(passwords_file)
    
    # Direct password manager access methods
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
        Replace password locations with [REDACTED] placeholders.
        """
        if not password_locations or not text:
            return text
            
        # Ensure password locations are within text bounds
        valid_locations = [(start, end) for start, end in password_locations 
                          if start < len(text) and end <= len(text)]
        
        if not valid_locations:
            return text
        
        # Sort by start position
        sorted_locations = sorted(valid_locations, key=lambda x: x[0])
        
        # Build sanitized text
        result = ""
        last_end = 0
        
        for start, end in sorted_locations:
            if start < last_end:
                continue
                
            # Add text between passwords
            if start > last_end:
                result += text[last_end:start]
                
            # Add redaction marker
            result += "[REDACTED]"
            last_end = end
            
        # Add any remaining text
        if last_end < len(text):
            result += text[last_end:]
            
        return result
    
    def _detect_passwords(self, text: str, buffer_states: List[str]) -> List[Tuple[int, int]]:
        """
        Detect passwords in text using fuzzy matching.
        """
        # Get passwords to detect
        passwords = self.password_manager.get_passwords()
        if not passwords or (not text and not buffer_states):
            return []
        
        # Use fuzzy matcher to find potential matches
        matches = FuzzyMatcher.find_matches(text, passwords)
        
        # Convert matches to location tuples
        locations = [(match.start, match.end) for match in matches]
        
        # Check if password was in buffer states but deleted
        if not locations and buffer_states and any(state for state in buffer_states):
            for password in passwords:
                password_lower = password.lower()
                for state in buffer_states:
                    if state and password_lower in state.lower():
                        # Password was typed then deleted
                        locations.append((0, 0))
                        break
        
        return sorted(locations)

    def process_events(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Process keystroke events to detect and sanitize passwords.
        """
        # Convert events to text with tracking information
        extracted_text, buffer_states, position_to_event_ids, related_events = TextBuffer.events_to_text(events)
        
        # Detect password locations
        password_locations = self._detect_passwords(extracted_text, buffer_states)
        
        # Track events to remove (password-related events)
        events_to_remove = set()
        
        # Find all events that contributed to passwords
        for start, end in password_locations:
            if 0 <= start < end <= len(extracted_text):
                for pos in range(start, end):
                    pos_str = str(pos)
                    if pos_str in position_to_event_ids:
                        for event_id_str in position_to_event_ids[pos_str]:
                            event_id = int(event_id_str)
                            events_to_remove.add(event_id)
                            
                            # Also remove related events
                            if event_id in related_events:
                                for related_id in related_events[event_id]:
                                    events_to_remove.add(related_id)
        
        # Create timestamp lookup
        event_timestamps = {}
        event_to_index = {}
        for i, event in enumerate(events):
            event_id = id(event)
            event_timestamps[event_id] = event.get("timestamp", datetime.now().isoformat())
            event_to_index[event_id] = i
        
        # Create sanitized event stream
        sanitized_events = [event.copy() for event in events if id(event) not in events_to_remove]
        
        # Add PASSWORD_FOUND events
        for start, end in password_locations:
            timestamp = datetime.now().isoformat()
            
            # Try to use timestamp from last event in password
            if 0 <= start < end <= len(extracted_text):
                last_pos = end - 1
                pos_str = str(last_pos)
                
                if pos_str in position_to_event_ids and position_to_event_ids[pos_str]:
                    event_ids = [int(eid) for eid in position_to_event_ids[pos_str]]
                    if event_ids:
                        last_event_id = max(event_ids, 
                                            key=lambda eid: event_to_index.get(eid, 0) if eid in event_to_index else 0)
                        if last_event_id in event_timestamps:
                            timestamp = event_timestamps[last_event_id]
            
            # Add the password found event
            sanitized_events.append({
                "event": "PASSWORD_FOUND",
                "timestamp": timestamp,
                "start_index": start,
                "end_index": end
            })
        
        # Create sanitized text
        sanitized_text = self._sanitize_text(extracted_text, password_locations)
        
        # Return results
        return {
            "events": sanitized_events,
            "text": extracted_text,
            "sanitized_text": sanitized_text,
            "password_locations": password_locations,
            "buffer_states": buffer_states
        }
    
    def save_to_log(self, sanitized_data: Dict[str, Any], log_file: str) -> None:
        """Save sanitized data to a log file"""
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "events": sanitized_data["events"],
            "sanitized_text": sanitized_data["sanitized_text"],
            "password_detected": len(sanitized_data["password_locations"]) > 0
        }
        
        with open(log_file, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
            
    def save_sanitized_json(self, sanitized_data: Dict[str, Any], output_file: str) -> bool:
        """Save sanitized keystroke data to a JSON file"""
        try:
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            
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
            
            with open(output_file, "w") as f:
                json.dump(output_data, f, indent=2)
                
            return True
            
        except Exception as e:
            print(f"Error saving sanitized JSON: {e}")
            return False


# Run tests from the tests directory
if __name__ == "__main__":
    print("Please use test_keystroke_sanitizer.py in the tests directory to test this module.")