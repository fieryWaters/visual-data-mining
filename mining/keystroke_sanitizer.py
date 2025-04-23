"""
Keystroke sanitizer module.
Processes raw keystroke data to detect and remove passwords, replacing them
with PASSWORD_FOUND events in the output stream.
"""

import os
import json
import glob
from datetime import datetime
from typing import Dict, List, Tuple, Any, Optional

from utils.keepass_manager import KeePassManager
from utils.text_buffer import TextBuffer
from utils.fuzzy_matcher import FuzzyMatcher


class KeystrokeSanitizer:
    """
    Sanitizes keystroke data by detecting and removing sensitive information.
    Includes both real-time and retroactive sanitization capabilities.
    """
    
    def __init__(self, password=None, keyfile=None, logs_dir="logs/sanitized_json"):
        """Initialize the sanitizer with optional password for immediate setup"""
        self.logs_dir = logs_dir
        self.password_manager = KeePassManager.get_instance()
        
        # Initialize password manager if credentials provided
        if password:
            self.setup_encryption(password, keyfile)
    
    def setup_encryption(self, password=None, keyfile=None) -> bool:
        """Setup encryption with the provided password"""
        result = self.password_manager.setup_encryption(password, keyfile)
        if result:
            self.password_manager.load_passwords()
        return result
    
    def is_initialized(self) -> bool:
        """Check if the password manager is properly initialized"""
        return self.password_manager.is_initialized
    
    def load_passwords(self) -> bool:
        """Load passwords from encrypted file"""
        return self.password_manager.load_passwords()
    
    def save_passwords(self) -> bool:
        """Save passwords to encrypted file"""
        return self.password_manager.save_passwords()
    
    def add_password(self, password, title=None, username=None) -> bool:
        """Add a password to the list"""
        return self.password_manager.add_password(password, title, username)
    
    def remove_password(self, password) -> bool:
        """Remove a password from the list"""
        return self.password_manager.remove_password(password)
        
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
    
    def _detect_passwords(self, text: str, buffer_states: List[str]) -> List[Tuple[int, int, int]]:
        """
        Detect passwords in text using fuzzy matching.
        
        Returns:
            List of tuples (start_pos, end_pos, buffer_state_idx)
            buffer_state_idx indicates which buffer state contained this password
        """
        # Get passwords to detect
        passwords = self.password_manager.get_passwords()
        if not passwords or (not text and not buffer_states):
            return []
        
        # Track all password locations with their buffer state indexes
        all_locations = []
        
        # Look for passwords in the final text
        if text:
            matches = FuzzyMatcher.find_matches(text, passwords)
            for match in matches:
                # For matches in the final text, use -1 to indicate final state
                all_locations.append((match.start, match.end, -1))
        
        # Look for passwords in all buffer states
        for buffer_idx, state in enumerate(buffer_states):
            if not state:
                continue
                
            # Skip if we've already found this password in the final text
            for password in passwords:
                password_lower = password.lower()
                if password_lower in state.lower():
                    # Check if this isn't already covered in the final text
                    start_idx = state.lower().find(password_lower)
                    end_idx = start_idx + len(password)
                    
                    # Add this location with its buffer state index
                    all_locations.append((start_idx, end_idx, buffer_idx))
        
        # Return all unique locations (sorted by start position)
        # If there are duplicates, prefer the ones from the final text
        unique_locations = []
        seen_positions = set()
        
        # First add locations from final text (buffer_idx = -1)
        for start, end, buffer_idx in sorted(all_locations, key=lambda x: (x[2] != -1, x[0])):
            pos_key = (start, end)
            if pos_key not in seen_positions:
                unique_locations.append((start, end, buffer_idx))
                seen_positions.add(pos_key)
        
        return unique_locations

    def process_events(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Process keystroke events to detect and sanitize passwords.
        """
        # Convert events to text with tracking information
        extracted_text, buffer_states, position_to_event_ids, related_events, buffer_state_mappings = TextBuffer.events_to_text(events)
        
        # Detect password locations
        password_locations = self._detect_passwords(extracted_text, buffer_states)
        
        # Track events to remove (password-related events)
        events_to_remove = set()
        
        # Find all events that contributed to passwords
        for start, end, buffer_idx in password_locations:
            # For passwords in the final text
            if buffer_idx == -1:
                # Use the current position_to_event_ids mapping
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
            # For passwords in intermediate buffer states
            else:
                # Find the corresponding buffer state mapping
                for mapping in buffer_state_mappings:
                    if mapping.get("buffer_state_idx") == buffer_idx:
                        # Get the position mapping for this state
                        state_position_mapping = mapping.get("position_mapping", {})
                        
                        # Get events for this password's character positions
                        for pos in range(start, end):
                            pos_str = str(pos)
                            if pos_str in state_position_mapping:
                                for event_id_str in state_position_mapping[pos_str]:
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
        for start, end, buffer_idx in password_locations:
            # Use timestamp from appropriate event
            timestamp = datetime.now().isoformat()
            
            if buffer_idx == -1:
                # For passwords in final text, use timestamp from the last character position
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
            else:
                # For buffer states, use timestamp from that state
                for mapping in buffer_state_mappings:
                    if mapping.get("buffer_state_idx") == buffer_idx and "event_id" in mapping:
                        event_id = mapping["event_id"]
                        if event_id in event_timestamps:
                            timestamp = event_timestamps[event_id]
            
            # Add the password found event
            sanitized_events.append({
                "event": "PASSWORD_FOUND",
                "timestamp": timestamp,
                "start_index": start,
                "end_index": end,
                "buffer_state_idx": buffer_idx
            })
        
        # Sort all events by timestamp
        sanitized_events.sort(key=lambda e: e.get("timestamp", ""))
        
        # Create sanitized text (convert password_locations to the format _sanitize_text expects)
        sanitized_text = self._sanitize_text(extracted_text, [(start, end) for start, end, _ in password_locations])
        
        # Return results
        return {
            "events": sanitized_events,
            "text": extracted_text,
            "sanitized_text": sanitized_text,
            "password_locations": password_locations,
            "buffer_states": buffer_states
        }
    
            
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
    
    # Retroactive sanitization capabilities (moved from RetroactiveSanitizer)
    def find_occurrences(self, custom_strings=None, logs_dir=None) -> Dict[str, int]:
        """
        Find occurrences of sensitive data in log files without modifying them.
        
        Args:
            custom_strings: Optional list of custom strings to search for
            logs_dir: Optional override for logs directory
            
        Returns:
            Dict mapping filenames to the number of occurrences found
        """
        search_dir = logs_dir or self.logs_dir
        
        # Get all log files
        log_files = self._get_log_files(search_dir)
        if not log_files:
            return {}
            
        # Track occurrences per file
        occurrences = {}
        
        # Add custom strings temporarily if provided
        original_passwords = []
        if custom_strings:
            # Store original passwords
            original_passwords = self.password_manager.get_passwords()
            # Add custom strings as temporary passwords
            strings_to_add = [custom_strings] if isinstance(custom_strings, str) else custom_strings
            for string in strings_to_add:
                self.password_manager.add_password(string, f"Temp: {string[:10]}")
        
        # Process each file
        for file_path in log_files:
            try:
                # Load the events from the log file
                events = self._extract_events_from_log(file_path)
                if not events:
                    continue
                
                # Process events to find sensitive data
                sanitized_data = self.process_events(events)
                
                # Check if any passwords were found
                if sanitized_data["password_locations"]:
                    filename = os.path.basename(file_path)
                    occurrences[filename] = len(sanitized_data["password_locations"])
            
            except Exception as e:
                print(f"Error processing file {file_path}: {e}")
        
        # Restore original passwords if we added custom strings
        if custom_strings and original_passwords:
            # Remove all passwords (including our temporary ones)
            for pwd in self.password_manager.get_passwords():
                self.password_manager.remove_password(pwd)
            # Add back original passwords
            for pwd in original_passwords:
                self.password_manager.add_password(pwd)
                
        return occurrences
    
    def sanitize_logs(self, custom_strings=None, logs_dir=None) -> Dict[str, int]:
        """
        Sanitize all log files by replacing sensitive data with [REDACTED].
        
        Args:
            custom_strings: Optional custom strings to search for and sanitize
            logs_dir: Optional override for logs directory
            
        Returns:
            Dict mapping filenames to the number of replacements made
        """
        search_dir = logs_dir or self.logs_dir
        
        # Get all log files
        log_files = self._get_log_files(search_dir)
        if not log_files:
            return {}
            
        # Track replacements per file
        replacements = {}
        
        # Add custom strings temporarily if provided
        original_passwords = []
        if custom_strings:
            # Store original passwords
            original_passwords = self.password_manager.get_passwords()
            # Add custom strings as temporary passwords
            strings_to_add = [custom_strings] if isinstance(custom_strings, str) else custom_strings
            for string in strings_to_add:
                self.password_manager.add_password(string, f"Temp: {string[:10]}")
        
        # Process each file
        for file_path in log_files:
            try:
                # Load the events from the log file
                events = self._extract_events_from_log(file_path)
                if not events:
                    continue
                
                # Process events
                sanitized_data = self.process_events(events)
                
                # Check if any passwords were found
                if sanitized_data["password_locations"]:
                    # Update the file with sanitized data
                    self._save_sanitized_data(file_path, sanitized_data)
                    
                    # Store the count of replacements
                    filename = os.path.basename(file_path)
                    replacements[filename] = len(sanitized_data["password_locations"])
            
            except Exception as e:
                print(f"Error sanitizing file {file_path}: {e}")
        
        # Restore original passwords if we added custom strings
        if custom_strings and original_passwords:
            # Remove all passwords (including our temporary ones)
            for pwd in self.password_manager.get_passwords():
                self.password_manager.remove_password(pwd)
            # Add back original passwords
            for pwd in original_passwords:
                self.password_manager.add_password(pwd)
                
        return replacements
    
    def _get_log_files(self, logs_dir) -> List[str]:
        """Get all keystroke log files in the specified logs directory"""
        if not os.path.exists(logs_dir):
            return []
            
        # Search for all JSON files
        return glob.glob(os.path.join(logs_dir, "*.json"))
    
    def _extract_events_from_log(self, file_path: str) -> List[Dict[str, Any]]:
        """Extract keystroke events from a log file"""
        try:
            with open(file_path, 'r') as f:
                log_data = json.load(f)
                
            # Most log files have events in an 'events' field
            if 'events' in log_data:
                return log_data['events']
            
            return []
            
        except Exception as e:
            print(f"Error extracting events from {file_path}: {e}")
            return []
    
    def _save_sanitized_data(self, file_path: str, sanitized_data: Dict[str, Any]) -> bool:
        """Save sanitized data back to the file"""
        try:
            # Create output data format
            output_data = {
                "metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "type": "sanitized_keystroke_data",
                    "version": "1.0",
                    "contains_sensitive_data": len(sanitized_data["password_locations"]) > 0,
                    "sanitization_applied": True,
                    "retroactive_sanitization": True
                },
                "events": sanitized_data["events"],
                "text_summary": {
                    "original_length": len(sanitized_data["text"]),
                    "sanitized_length": len(sanitized_data["sanitized_text"]),
                    "password_locations_count": len(sanitized_data["password_locations"])
                }
            }
            
            # Write back to the file
            with open(file_path, 'w') as f:
                json.dump(output_data, f, indent=2)
                
            return True
            
        except Exception as e:
            print(f"Error saving sanitized data to {file_path}: {e}")
            return False


if __name__ == "__main__":
    import time
    import sys
    import getpass
    from keystroke_recorder import KeystrokeRecorder
    
    # Initialize sanitizer
    sanitizer = KeystrokeSanitizer()
    try:
        print("Setting up KeePass database...")
        password = getpass.getpass("Enter master password for KeePass database: ")
        sanitizer.setup_encryption(password)
        sanitizer.load_passwords()
        print("KeePass database set up successfully")
    except Exception as e:
        print(f"Error setting up KeePass database: {e}")
        sys.exit(1)
    
    # Initialize the keystroke recorder
    recorder = KeystrokeRecorder()
    
    print("Recording keystrokes... Type sensitive information to test sanitization.")
    print("Press Ctrl+C to stop recording and process the results.")
    
    try:
        # Start recording
        recorder.start()
        
        # Keep the main thread running
        while True:
            time.sleep(0.5)
            
    except KeyboardInterrupt:
        print("\nStopping keystroke capture...")
        # Stop the recorder
        recorder.stop()
        
        # Process the captured events
        events = recorder.get_buffer_contents()
        if events:
            print(f"Processing {len(events)} events...")
            result = sanitizer.process_events(events)
            print(f"\nOriginal text: {result['text']}")
            print(f"Sanitized text: {result['sanitized_text']}")
            if result['password_locations']:
                print(f"Password locations: {result['password_locations']}")
            else:
                print("No passwords detected")
    
    except Exception as e:
        print(f"Error: {e}")