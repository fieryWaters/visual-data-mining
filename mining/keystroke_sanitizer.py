"""
Keystroke sanitizer module.
Processes raw keystroke data to sanitize passwords and sensitive information.
"""

import os
import json
import getpass
import base64
from datetime import datetime
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import re
from difflib import SequenceMatcher

class KeystrokeSanitizer:
    """
    Processes raw keystroke data to sanitize passwords and sensitive information
    """
    
    def __init__(self, passwords_file="secret.keys", salt=None):
        """
        Initialize the sanitizer with password file path
        
        Args:
            passwords_file: Path to the encrypted passwords file
            salt: Salt for encryption (if None, a random salt is generated)
        """
        self.passwords_file = passwords_file
        self.passwords = []
        self.key = None
        self.salt = salt if salt else os.urandom(16)  # Generate random salt if not provided
        
    def _derive_key(self, password):
        """Derive encryption key from password using PBKDF2"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self.salt,
            iterations=100000,
        )
        return base64.urlsafe_b64encode(kdf.derive(password.encode()))
    
    def setup_encryption(self, password=None):
        """
        Setup encryption with password (prompt if not provided)
        
        Args:
            password: User password for encryption (optional)
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not password:
                password = getpass.getpass("Enter encryption password: ")
            
            self.key = self._derive_key(password)
            return True
        except Exception as e:
            print(f"Error setting up encryption: {e}")
            return False
    
    def load_passwords(self):
        """
        Load passwords from encrypted file
        
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.key:
            print("Encryption not set up. Call setup_encryption() first.")
            return False
            
        try:
            if not os.path.exists(self.passwords_file):
                # No passwords file yet, create empty list
                self.passwords = []
                return True
                
            cipher = Fernet(self.key)
            with open(self.passwords_file, 'rb') as f:
                encrypted_data = f.read()
                
            # Decrypt the data
            decrypted_data = cipher.decrypt(encrypted_data)
            
            # Load JSON data
            self.passwords = json.loads(decrypted_data.decode())
            return True
            
        except Exception as e:
            print(f"Error loading passwords: {e}")
            return False
    
    def save_passwords(self):
        """
        Save passwords to encrypted file
        
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.key:
            print("Encryption not set up. Call setup_encryption() first.")
            return False
            
        try:
            # Convert passwords to JSON
            data = json.dumps(self.passwords).encode()
            
            # Encrypt the data
            cipher = Fernet(self.key)
            encrypted_data = cipher.encrypt(data)
            
            # Write to file
            with open(self.passwords_file, 'wb') as f:
                f.write(encrypted_data)
                
            return True
            
        except Exception as e:
            print(f"Error saving passwords: {e}")
            return False
    
    def add_password(self, password):
        """
        Add a password to the list
        
        Args:
            password: Password string to add
        """
        if password and password not in self.passwords:
            self.passwords.append(password)
    
    def remove_password(self, password):
        """
        Remove a password from the list
        
        Args:
            password: Password string to remove
        """
        if password in self.passwords:
            self.passwords.remove(password)
    
    def _key_to_char(self, key_event):
        """
        Convert a key event to a character
        
        Args:
            key_event: Key event from the recorder
        
        Returns:
            str: Character representation or special key name
        """
        key = key_event.get("key", "")
        
        # Special keys
        if key.startswith("Key."):
            return key
            
        # Normal character
        return key
    
    def _process_backspace(self, buffer):
        """
        Process backspace in text buffer
        
        Args:
            buffer: Text buffer
        
        Returns:
            str: Updated buffer
        """
        if buffer and len(buffer) > 0:
            return buffer[:-1]
        return buffer
    
    def _process_delete(self, buffer, cursor_pos):
        """
        Process delete in text buffer
        
        Args:
            buffer: Text buffer
            cursor_pos: Cursor position
        
        Returns:
            tuple: (updated buffer, updated cursor position)
        """
        if cursor_pos < len(buffer):
            buffer = buffer[:cursor_pos] + buffer[cursor_pos+1:]
        return buffer, cursor_pos
    
    def _process_arrow_keys(self, cursor_pos, key, buffer_len):
        """
        Process arrow keys to update cursor position
        
        Args:
            cursor_pos: Current cursor position
            key: Key pressed
            buffer_len: Length of text buffer
        
        Returns:
            int: Updated cursor position
        """
        if key == "Key.left":
            return max(0, cursor_pos - 1)
        elif key == "Key.right":
            return min(buffer_len, cursor_pos + 1)
        elif key == "Key.home":
            return 0
        elif key == "Key.end":
            return buffer_len
        return cursor_pos
    
    def _events_to_text(self, events):
        """
        Convert keystroke events to text with cursor tracking
        
        Args:
            events: List of keystroke events
        
        Returns:
            str: Reconstructed text
        """
        buffer = ""
        cursor_pos = 0
        
        # New list to store buffer state history for password detection
        buffer_states = []
        
        for event in events:
            if event["event"] != "KEY_PRESS":
                continue
                
            key = event.get("key", "")
            
            # Handle special keys
            if key == "Key.space":
                # Insert space at cursor position
                buffer = buffer[:cursor_pos] + " " + buffer[cursor_pos:]
                cursor_pos += 1
            elif key == "Key.enter":
                # Insert newline at cursor position
                buffer = buffer[:cursor_pos] + "\n" + buffer[cursor_pos:]
                cursor_pos += 1
            elif key == "Key.backspace":
                # Handle backspace
                if cursor_pos > 0:
                    buffer = buffer[:cursor_pos-1] + buffer[cursor_pos:]
                    cursor_pos -= 1
            elif key == "Key.delete":
                # Handle delete
                buffer, cursor_pos = self._process_delete(buffer, cursor_pos)
            elif key in ["Key.left", "Key.right", "Key.home", "Key.end"]:
                # Update cursor position
                cursor_pos = self._process_arrow_keys(cursor_pos, key, len(buffer))
            elif key.startswith("Key."):
                # Ignore other special keys
                pass
            else:
                # Regular character - insert at cursor position
                buffer = buffer[:cursor_pos] + key + buffer[cursor_pos:]
                cursor_pos += 1
            
            # After each keystroke, add the current buffer state to our history
            # This captures the text even if it's later deleted
            if buffer:  # Only add non-empty states
                buffer_states.append(buffer)
                
        # Return both the final buffer and the history of buffer states
        return buffer, buffer_states
    
    def _find_password_in_buffer_states(self, buffer_states):
        """
        Find passwords in all buffer states (text snapshots after each keystroke)
        
        Args:
            buffer_states: List of buffer states from keystroke processing
            
        Returns:
            list: List of (buffer_idx, start, end, similarity) tuples marking password locations
        """
        password_matches = []
        
        # Process each buffer state
        for idx, buffer in enumerate(buffer_states):
            for password in self.passwords:
                # Exact match
                for match in re.finditer(re.escape(password), buffer):
                    password_matches.append((idx, match.start(), match.end(), 1.0))
                
                # Fuzzy matching for each buffer state
                for i in range(len(buffer) - len(password)//2 + 1):
                    # Use window size based on password length
                    window_size = min(len(password) + 5, len(buffer) - i)
                    if window_size < len(password) // 2:
                        continue
                        
                    chunk = buffer[i:i + window_size]
                    similarity = SequenceMatcher(None, password, chunk).ratio()
                    
                    # Check if similarity is high enough
                    if similarity > 0.75:
                        # Find best window size for this match
                        best_window = window_size
                        best_sim = similarity
                        
                        for w in range(max(len(password) - 2, 3), min(len(password) + 5, len(buffer) - i + 1)):
                            test_chunk = buffer[i:i + w]
                            test_sim = SequenceMatcher(None, password, test_chunk).ratio()
                            
                            if test_sim > best_sim:
                                best_sim = test_sim
                                best_window = w
                        
                        # Record this match
                        password_matches.append((idx, i, i + best_window, best_sim))
        
        # Remove overlapping matches in the same buffer state
        # (keeping the ones with higher similarity)
        filtered_matches = []
        
        # Group matches by buffer index
        matches_by_buffer = {}
        for match in password_matches:
            buffer_idx = match[0]
            if buffer_idx not in matches_by_buffer:
                matches_by_buffer[buffer_idx] = []
            matches_by_buffer[buffer_idx].append(match)
        
        # Filter overlaps within each buffer
        for buffer_idx, matches in matches_by_buffer.items():
            # Sort by similarity (descending)
            matches.sort(key=lambda x: x[3], reverse=True)
            
            filtered_buffer_matches = []
            for match in matches:
                overlap = False
                for existing in filtered_buffer_matches:
                    # Check for overlap
                    if (match[1] <= existing[2] and match[2] >= existing[1]):
                        overlap = True
                        break
                
                if not overlap:
                    filtered_buffer_matches.append(match)
            
            filtered_matches.extend(filtered_buffer_matches)
        
        return filtered_matches
    
    def _find_password_locations(self, text, buffer_states=None):
        """
        Find password locations in text using fuzzy matching
        
        Args:
            text: Processed text from keystrokes
            buffer_states: List of buffer states from keystroke history (optional)
        
        Returns:
            list: List of (start, end) tuples marking password locations
        """
        password_locations = []
        
        # First check the final text
        for password in self.passwords:
            # Simple search first
            for match in re.finditer(re.escape(password), text):
                password_locations.append((match.start(), match.end()))
                
            # Improved fuzzy search with lower threshold and sliding window approach
            for i in range(len(text)):
                # Use larger window for longer passwords to handle insertions/deletions
                window_size = min(len(password) + 5, len(text) - i)
                if window_size < len(password) // 2:
                    continue  # Skip if the remaining text is too short
                    
                chunk = text[i:i + window_size]
                similarity = SequenceMatcher(None, password, chunk).ratio()
                
                # Use a lower threshold for initial match detection
                if similarity > 0.7:
                    # Expand the match to find best boundaries
                    best_start, best_end = i, i + window_size
                    best_sim = similarity
                    
                    # Try different window sizes to find optimal match
                    for window in range(max(len(password) - 2, 3), len(password) + 5):
                        if i + window > len(text):
                            break
                            
                        test_chunk = text[i:i + window]
                        test_sim = SequenceMatcher(None, password, test_chunk).ratio()
                        
                        if test_sim > best_sim:
                            best_sim = test_sim
                            best_start, best_end = i, i + window
                    
                    # Only consider as match if similarity is sufficiently high
                    if best_sim > 0.75:
                        # Check if this overlaps with existing matches
                        overlap = False
                        for s, e in password_locations:
                            if (best_start <= s <= best_end) or (best_start <= e <= best_end) or \
                               (s <= best_start <= e) or (s <= best_end <= e):
                                overlap = True
                                break
                        
                        if not overlap:
                            password_locations.append((best_start, best_end))
                            # Skip ahead to avoid finding the same match multiple times
                            i = best_end - 1
                            
        # If we have buffer states, check those too
        if buffer_states:
            buffer_password_matches = self._find_password_in_buffer_states(buffer_states)
            
            # Convert buffer matches to text positions if they don't exist in the final text
            for _, start, end, _ in buffer_password_matches:
                # Check if this match overlaps with existing ones
                overlap = False
                for s, e in password_locations:
                    if (start <= s <= end) or (start <= e <= end) or \
                       (s <= start <= e) or (s <= end <= e):
                        overlap = True
                        break
                
                if not overlap:
                    password_locations.append((start, end))
        
        # Sort by starting position
        return sorted(password_locations)
    
    def _sanitize_text(self, text, password_locations):
        """
        Sanitize text by replacing password locations
        
        Args:
            text: Original text
            password_locations: List of (start, end) tuples marking password locations
        
        Returns:
            str: Sanitized text
        """
        # Handle the case with no passwords
        if not password_locations:
            return text
            
        # Ensure password locations are within text bounds
        valid_locations = [(start, end) for start, end in password_locations if start < len(text) and end <= len(text)]
        
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
    
    def process_events(self, events):
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
        extracted_text, buffer_states = self._events_to_text(events)
        
        # 2. Find password locations in both final text and buffer states
        password_locations = self._find_password_locations(extracted_text, buffer_states)
        
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
            "buffer_states": buffer_states  # Include buffer history for debugging
        }
    
    def save_to_log(self, sanitized_data, log_file):
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


# Test function
def test():
    """Test the keystroke sanitizer"""
    from keystroke_recorder import KeystrokeRecorder
    import time
    
    # Create a sanitizer and add test passwords
    sanitizer = KeystrokeSanitizer()
    sanitizer.setup_encryption("test_password")
    sanitizer.add_password("secret123")
    sanitizer.save_passwords()
    
    # Create a recorder
    recorder = KeystrokeRecorder()
    
    try:
        # Start recording
        recorder.start()
        print("Type some text including variations of 'secret123'. Press Ctrl+C to stop...")
        print("Try different variations like: secret123, secrett123, secret1234, secret12, etc.")
        print("You can also type it and then delete it with backspace - it will still be detected!")
        
        # Wait for user input
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nStopping recording...")
    except Exception as e:
        print(f"Error during recording: {e}")
    finally:
        # Ensure recorder is stopped
        try:
            recorder.stop()
            
            # Process the keystrokes
            events = recorder.get_buffer_contents()
            print(f"Captured {len(events)} events")
            
            sanitizer.load_passwords()
            processed = sanitizer.process_events(events)
            
            print("\nExtracted text (final state):")
            print(processed["text"])
            
            print("\nSanitized text:")
            print(processed["sanitized_text"])
            
            print(f"\nFound {len(processed['password_locations'])} password instances")
            
            # Show password locations for debugging
            if processed["password_locations"]:
                print("\nPassword matches found at:")
                for start, end in processed["password_locations"]:
                    match_text = processed["text"][start:end]
                    print(f"  Position {start}-{end}: '{match_text}' (similarity: {SequenceMatcher(None, 'secret123', match_text).ratio():.2f})")
            
            # Show buffer history to demonstrate detection even when deleted
            if processed["buffer_states"]:
                print("\nBuffer state history (shows all intermediate states):")
                print("-------------------------------------------------------")
                
                # Remove duplicates while preserving order
                seen = set()
                unique_states = []
                for state in processed["buffer_states"]:
                    if state not in seen:
                        seen.add(state)
                        unique_states.append(state)
                
                # Track which passwords have been detected in previous states
                previously_shown_locations = set()

                # Print all unique states in chronological order
                for i, state in enumerate(unique_states):
                    # Get password detection status with position information
                    contains_password = False
                    password_matches = []
                    
                    for password in sanitizer.passwords:
                        # Check for exact match with word boundaries
                        for match in re.finditer(r'\b' + re.escape(password) + r'\b', state):
                            contains_password = True
                            start, end = match.span()
                            password_matches.append((start, end, password, 1.0))
                        
                        # If no word boundary match, check for exact match anywhere
                        if not any(m[2] == password for m in password_matches) and len(password) >= 6:
                            for match in re.finditer(re.escape(password), state):
                                start, end = match.span()
                                password_matches.append((start, end, password, 1.0))
                        
                        # Check for fuzzy match only with substantial passwords
                        if len(password) >= 6:
                            for j in range(len(state) - len(password)//2 + 1):
                                if j + len(password) <= len(state):
                                    chunk = state[j:j+len(password)]
                                    similarity = SequenceMatcher(None, password, chunk).ratio()
                                    if similarity > 0.85 and not any(j >= m[0] and j < m[1] for m in password_matches):
                                        password_matches.append((j, j+len(password), password, similarity))
                    
                    # Filter out matches that persist from previous states unless new content was added
                    new_matches = []
                    for start, end, password, similarity in password_matches:
                        # Create a unique key for this match
                        match_content = state[start:end]
                        match_key = (match_content, password, similarity)
                        
                        # Only include this match if:
                        # 1. We haven't seen it in previous states, OR
                        # 2. This state has significant new content beyond the previous state
                        if match_key not in previously_shown_locations or (
                           i > 0 and len(state) > len(unique_states[i-1]) + 5):
                            new_matches.append((start, end, password, similarity))
                            previously_shown_locations.add(match_key)
                    
                    # Sort matches by position
                    new_matches.sort(key=lambda x: x[0])
                    
                    # Format and highlight the state
                    formatted_state = state
                    if len(formatted_state) > 70:
                        formatted_state = formatted_state[:67] + "..."
                    
                    # Show password indicator with position
                    password_indicator = ""
                    if new_matches:
                        match_details = []
                        for start, end, password, similarity in new_matches:
                            # Show context around the match
                            context = f"'{state[max(0, start-10):start]}[{state[start:end]}]{state[end:min(len(state), end+10)]}'"
                            if similarity < 1.0:
                                match_details.append(f"NEW MATCH at pos {start}-{end}: {context} (similar to {password}, {similarity:.2f})")
                            else:
                                match_details.append(f"NEW MATCH at pos {start}-{end}: {context}")
                        
                        password_indicator = " ← NEW PASSWORD MATCH\n    " + "\n    ".join(match_details)
                    
                    # Print with state number and a line break between states
                    print(f"  State {i:3d}: '{formatted_state}'{password_indicator}\n")
                
                print("-------------------------------------------------------")
                
                # Summary statistics - use same password detection logic for consistency
                password_states = 0
                for state in unique_states:
                    for password in sanitizer.passwords:
                        if (re.search(r'\b' + re.escape(password) + r'\b', state) or 
                            (password in state and len(password) >= 6)):
                            password_states += 1
                            break
                print(f"Total unique states: {len(unique_states)}")
                print(f"States containing exact passwords: {password_states}")
                
                # Find first and last states where passwords appeared
                first_password_state = None
                last_password_state = None
                
                for i, state in enumerate(unique_states):
                    for password in sanitizer.passwords:
                        # Use same detection logic as above for consistency
                        if (re.search(r'\b' + re.escape(password) + r'\b', state) or 
                            (password in state and len(password) >= 6)):
                            if first_password_state is None:
                                first_password_state = i
                            last_password_state = i
                
                if first_password_state is not None:
                    print(f"Passwords first appeared in state {first_password_state} and last appeared in state {last_password_state}")
                    if first_password_state != last_password_state:
                        print(f"Password was typed and then deleted/modified")
        except Exception as e:
            print(f"Error processing results: {e}")
    

if __name__ == "__main__":
    test()