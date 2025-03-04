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
                
        return buffer
    
    def _find_password_locations(self, text):
        """
        Find password locations in text using fuzzy matching
        
        Args:
            text: Processed text from keystrokes
        
        Returns:
            list: List of (start, end) tuples marking password locations
        """
        password_locations = []
        
        for password in self.passwords:
            # Simple search first
            for match in re.finditer(re.escape(password), text):
                password_locations.append((match.start(), match.end()))
                
            # Fuzzy search
            for i in range(len(text) - len(password) // 2):
                chunk = text[i:i + len(password) + 10]  # Check a slightly larger chunk
                similarity = SequenceMatcher(None, password, chunk).ratio()
                
                # If similarity is high, consider it a match
                if similarity > 0.8:
                    # Find the best match within the chunk
                    highest_sim = 0
                    best_pos = 0
                    
                    for j in range(min(10, len(chunk) - len(password) + 1)):
                        sub_chunk = chunk[j:j + len(password)]
                        sub_sim = SequenceMatcher(None, password, sub_chunk).ratio()
                        if sub_sim > highest_sim:
                            highest_sim = sub_sim
                            best_pos = j
                            
                    if highest_sim > 0.8:
                        start = i + best_pos
                        end = start + len(password)
                        # Check if this overlaps with existing matches
                        overlap = False
                        for s, e in password_locations:
                            if (start <= s <= end) or (start <= e <= end) or (s <= start <= e) or (s <= end <= e):
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
        # Handle overlapping ranges by working backwards
        result = list(text)
        
        for start, end in reversed(password_locations):
            placeholder = "[PASSWORD REDACTED]"
            result[start:end] = placeholder
            
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
        """
        # 1. Extract text from keystroke events
        extracted_text = self._events_to_text(events)
        
        # 2. Find password locations
        password_locations = self._find_password_locations(extracted_text)
        
        # 3. Sanitize original events
        sanitized_events = []
        for event in events:
            # For KEY_PRESS events, check if we need to redact the key
            if event["event"] == "KEY_PRESS" and "key" in event:
                # Deep copy the event to avoid modifying the original
                new_event = event.copy()
                
                # Check if the current keystroke is part of a password
                # This is a simplified check that marks special regions
                for start_idx, end_idx in password_locations:
                    timestamp = datetime.fromisoformat(event["timestamp"])
                    event_time = timestamp.timestamp()
                    
                    # If this appears to be a password keystroke, mark it
                    if event_time >= start_idx and event_time <= end_idx:
                        new_event["key"] = "*"  # Redact key
                        new_event["redacted"] = True
                        break
                        
                sanitized_events.append(new_event)
            else:
                sanitized_events.append(event.copy())
        
        # 4. Sanitize the extracted text
        sanitized_text = self._sanitize_text(extracted_text, password_locations)
        
        # 5. Return results
        return {
            "events": sanitized_events,
            "text": extracted_text,
            "sanitized_text": sanitized_text,
            "password_locations": password_locations
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
    
    # Create a sanitizer and add a test password
    sanitizer = KeystrokeSanitizer()
    sanitizer.setup_encryption("test_password")
    sanitizer.add_password("secret123")
    sanitizer.save_passwords()
    
    # Create a recorder
    recorder = KeystrokeRecorder()
    
    try:
        # Start recording
        recorder.start()
        print("Type some text including 'secret123'. Press Ctrl+C to stop...")
        
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
            
            print("\nExtracted text:")
            print(processed["text"])
            
            print("\nSanitized text:")
            print(processed["sanitized_text"])
            
            print(f"\nFound {len(processed['password_locations'])} password instances")
        except Exception as e:
            print(f"Error processing results: {e}")
    

if __name__ == "__main__":
    test()