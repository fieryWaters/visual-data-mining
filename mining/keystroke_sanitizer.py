
import os
import json
import glob
from datetime import datetime
from typing import Dict, List, Tuple, Any, Optional

from utils.keepass_manager import KeePassManager
from utils.text_buffer import TextBuffer
from utils.fuzzy_matcher import FuzzyMatcher


class KeystrokeSanitizer:
    
    def __init__(self, password=None, keyfile=None, logs_dir="logs/sanitized_json"):
        self.logs_dir = logs_dir
        self.password_manager = KeePassManager.get_instance()
        
        if password:
            self.setup_encryption(password, keyfile)
    
    def setup_encryption(self, password=None, keyfile=None) -> bool:
        result = self.password_manager.setup_encryption(password, keyfile)
        if result:
            self.password_manager.load_passwords()
        return result
    def is_initialized(self) -> bool:
        return self.password_manager.is_initialized
    
    def load_passwords(self) -> bool:
        return self.password_manager.load_passwords()
    
    def save_passwords(self) -> bool:
        return self.password_manager.save_passwords()
    
    def add_password(self, password, title=None, username=None) -> bool:
        return self.password_manager.add_password(password, title, username)
    
    def remove_password(self, password) -> bool:
        return self.password_manager.remove_password(password)
        
    def _sanitize_text(self, text: str, password_locations: List[Tuple[int, int]]) -> str:
        if not password_locations or not text:
            return text
        
        sorted_locations = sorted(password_locations, key=lambda x: x[0])
        result = ""
        last_end = 0
        
        for start, end in sorted_locations:
            if start < last_end:
                continue
                
            if start > last_end:
                result += text[last_end:start]
            result += "[REDACTED]"
            last_end = end
            
        if last_end < len(text):
            result += text[last_end:]
            
        return result
    
    def _detect_passwords(self, text: str, buffer_states: List[str]) -> List[Tuple[int, int, int]]:
        passwords = self.password_manager.get_passwords()
        if not passwords or (not text and not buffer_states):
            return []
        
        all_locations = []
        if text:
            matches = FuzzyMatcher.find_matches(text, passwords)
            for match in matches:
                all_locations.append((match.start, match.end, -1))
        for buffer_idx, state in enumerate(buffer_states):
            if not state:
                continue
                
            for password in passwords:
                password_lower = password.lower()
                if password_lower in state.lower():
                    start_idx = state.lower().find(password_lower)
                    end_idx = start_idx + len(password)
                    all_locations.append((start_idx, end_idx, buffer_idx))
        
        unique_locations = []
        seen_positions = set()
        for start, end, buffer_idx in sorted(all_locations, key=lambda x: (x[2] != -1, x[0])):
            pos_key = (start, end)
            if pos_key not in seen_positions:
                unique_locations.append((start, end, buffer_idx))
                seen_positions.add(pos_key)
        
        return unique_locations

    def process_events(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        extracted_text, buffer_states, position_to_event_ids, related_events, buffer_state_mappings = TextBuffer.events_to_text(events)
        
        password_locations = self._detect_passwords(extracted_text, buffer_states)
        
        events_to_remove = set()
        
        for start, end, buffer_idx in password_locations:
            if buffer_idx == -1:
                for pos in range(start, end):
                    pos_str = str(pos)
                    if pos_str in position_to_event_ids:
                        for event_id_str in position_to_event_ids[pos_str]:
                            event_id = int(event_id_str)
                            events_to_remove.add(event_id)
                            
                            if event_id in related_events:
                                for related_id in related_events[event_id]:
                                    events_to_remove.add(related_id)
            else:
                for mapping in buffer_state_mappings:
                    if mapping.get("buffer_state_idx") == buffer_idx:
                        state_position_mapping = mapping.get("position_mapping", {})
                        for pos in range(start, end):
                            pos_str = str(pos)
                            if pos_str in state_position_mapping:
                                for event_id_str in state_position_mapping[pos_str]:
                                    event_id = int(event_id_str)
                                    events_to_remove.add(event_id)
                                    
                                    if event_id in related_events:
                                        for related_id in related_events[event_id]:
                                            events_to_remove.add(related_id)
        
        event_timestamps = {}
        event_to_index = {}
        for i, event in enumerate(events):
            event_id = id(event)
            event_timestamps[event_id] = event.get("timestamp", datetime.now().isoformat())
            event_to_index[event_id] = i
        
        sanitized_events = [event.copy() for event in events if id(event) not in events_to_remove]
        for start, end, buffer_idx in password_locations:
            timestamp = datetime.now().isoformat()
            
            if buffer_idx == -1:
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
                for mapping in buffer_state_mappings:
                    if mapping.get("buffer_state_idx") == buffer_idx and "event_id" in mapping:
                        event_id = mapping["event_id"]
                        if event_id in event_timestamps:
                            timestamp = event_timestamps[event_id]
            
            sanitized_events.append({
                "event": "PASSWORD_FOUND",
                "timestamp": timestamp,
                "start_index": start,
                "end_index": end,
                "buffer_state_idx": buffer_idx
            })
        
        sanitized_events.sort(key=lambda e: e.get("timestamp", ""))
        
        sanitized_text = self._sanitize_text(extracted_text, [(start, end) for start, end, _ in password_locations])
        return {
            "events": sanitized_events,
            "text": extracted_text,
            "sanitized_text": sanitized_text,
            "password_locations": password_locations,
            "buffer_states": buffer_states
        }
    
    def save_sanitized_json(self, sanitized_data: Dict[str, Any], output_file: str) -> bool:
        try:
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            
            output_data = {
                "timestamp": datetime.now().isoformat(),
                "events": sanitized_data["events"]
            }
            
            with open(output_file, "w") as f:
                json.dump(output_data, f, indent=2)
                
            return True
            
        except Exception:
            print("Error saving sanitized JSON")
            return False
    
    def find_occurrences(self, custom_strings=None, logs_dir=None) -> Dict[str, int]:
        search_dir = logs_dir or self.logs_dir
        
        log_files = self._get_log_files(search_dir)
        if not log_files:
            return {}
            
        occurrences = {}
        
        original_passwords = []
        if custom_strings:
            original_passwords = self.password_manager.get_passwords()
            strings_to_add = [custom_strings] if isinstance(custom_strings, str) else custom_strings
            for string in strings_to_add:
                self.password_manager.add_password(string, f"Temp: {string[:10]}")
        
        for file_path in log_files:
            try:
                events = self._extract_events_from_log(file_path)
                if not events:
                    continue
                
                sanitized_data = self.process_events(events)
                if sanitized_data["password_locations"]:
                    filename = os.path.basename(file_path)
                    occurrences[filename] = len(sanitized_data["password_locations"])
            
            except Exception as e:
                print(f"Error processing file {file_path}: {e}")
        
        if custom_strings and original_passwords:
            for pwd in self.password_manager.get_passwords():
                self.password_manager.remove_password(pwd)
            for pwd in original_passwords:
                self.password_manager.add_password(pwd)
                
        return occurrences
    
    def sanitize_logs(self, custom_strings=None, logs_dir=None) -> Dict[str, int]:
        search_dir = logs_dir or self.logs_dir
        
        log_files = self._get_log_files(search_dir)
        if not log_files:
            return {}
            
        replacements = {}
        
        original_passwords = []
        if custom_strings:
            original_passwords = self.password_manager.get_passwords()
            strings_to_add = [custom_strings] if isinstance(custom_strings, str) else custom_strings
            for string in strings_to_add:
                self.password_manager.add_password(string, f"Temp: {string[:10]}")
        
        for file_path in log_files:
            try:
                events = self._extract_events_from_log(file_path)
                if not events:
                    continue
                
                sanitized_data = self.process_events(events)
                
                if sanitized_data["password_locations"]:
                    self._save_sanitized_data(file_path, sanitized_data)
                    filename = os.path.basename(file_path)
                    replacements[filename] = len(sanitized_data["password_locations"])
            
            except Exception as e:
                print(f"Error sanitizing file {file_path}: {e}")
        
        if custom_strings and original_passwords:
            for pwd in self.password_manager.get_passwords():
                self.password_manager.remove_password(pwd)
            for pwd in original_passwords:
                self.password_manager.add_password(pwd)
                
        return replacements
    
    def _get_log_files(self, logs_dir) -> List[str]:
        if not os.path.exists(logs_dir):
            return []
            
        return glob.glob(os.path.join(logs_dir, "*.json"))
    
    def _extract_events_from_log(self, file_path: str) -> List[Dict[str, Any]]:
        try:
            with open(file_path, 'r') as f:
                log_data = json.load(f)
                
            if 'events' in log_data:
                return log_data['events']
            
            return []
            
        except Exception as e:
            print(f"Error extracting events from {file_path}: {e}")
            return []
    
    def _save_sanitized_data(self, file_path: str, sanitized_data: Dict[str, Any]) -> bool:
        try:
            output_data = {
                "timestamp": datetime.now().isoformat(),
                "events": sanitized_data["events"]
            }
            
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
        recorder.stop()
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