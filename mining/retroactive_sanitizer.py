#!/usr/bin/env python3
"""
Retroactive sanitization for keystroke logs.
Scans existing keystroke logs for sensitive information and sanitizes them.
Uses the KeystrokeSanitizer to ensure consistent sanitization across real-time and retroactive processes.
"""

import os
import json
import glob
from typing import Dict, List, Any
from datetime import datetime

from keystroke_sanitizer import KeystrokeSanitizer
from utils.text_buffer import TextBuffer


class RetroactiveSanitizer:
    """
    Scan and sanitize keystroke logs for sensitive information.
    Reuses the KeystrokeSanitizer to maintain consistent sanitization logic.
    """
    
    def __init__(self, keepass_manager, logs_dir="logs/sanitized_json"):
        """Initialize with KeePass manager and logs directory"""
        self.keepass_manager = keepass_manager
        self.logs_dir = logs_dir
        # Create a KeystrokeSanitizer instance that uses the same KeePass manager
        self.sanitizer = KeystrokeSanitizer(passwords_file="passwords.kdbx")
        self.sanitizer.password_manager = keepass_manager  # Share the KeePass manager
        
    def find_occurrences(self, custom_strings=None) -> Dict[str, int]:
        """
        Find occurrences of sensitive data in log files without modifying them.
        
        Args:
            custom_strings: Optional list of custom strings to search for
                           (will be added temporarily to the sanitizer)
        
        Returns:
            Dict mapping filenames to the number of occurrences found
        """
        # Get all log files
        log_files = self._get_log_files()
        if not log_files:
            return {}
            
        # Track occurrences per file
        occurrences = {}
        
        # Add custom strings temporarily if provided
        original_passwords = []
        if custom_strings:
            # Store original passwords
            original_passwords = self.keepass_manager.get_passwords()
            # Add custom strings as temporary passwords
            strings_to_add = [custom_strings] if isinstance(custom_strings, str) else custom_strings
            for string in strings_to_add:
                self.keepass_manager.add_password(string, f"Temp: {string[:10]}")
        
        # Process each file
        for file_path in log_files:
            try:
                # Load the events from the log file
                events = self._extract_events_from_log(file_path)
                if not events:
                    continue
                
                # Use the KeystrokeSanitizer to process events (without modifying the file)
                sanitized_data = self.sanitizer.process_events(events)
                
                # Check if any passwords were found
                if sanitized_data["password_locations"]:
                    filename = os.path.basename(file_path)
                    occurrences[filename] = len(sanitized_data["password_locations"])
            
            except Exception as e:
                print(f"Error processing file {file_path}: {e}")
        
        # Restore original passwords if we added custom strings
        if custom_strings and original_passwords:
            # Remove all passwords (including our temporary ones)
            for pwd in self.keepass_manager.get_passwords():
                self.keepass_manager.remove_password(pwd)
            # Add back original passwords
            for pwd in original_passwords:
                self.keepass_manager.add_password(pwd)
                
        return occurrences
    
    def sanitize_logs(self, custom_strings=None) -> Dict[str, int]:
        """
        Sanitize all log files by replacing sensitive data with [REDACTED].
        
        Args:
            custom_strings: Optional custom strings to search for and sanitize
        
        Returns:
            Dict mapping filenames to the number of replacements made
        """
        # Get all log files
        log_files = self._get_log_files()
        if not log_files:
            return {}
            
        # Track replacements per file
        replacements = {}
        
        # Add custom strings temporarily if provided
        original_passwords = []
        if custom_strings:
            # Store original passwords
            original_passwords = self.keepass_manager.get_passwords()
            # Add custom strings as temporary passwords
            strings_to_add = [custom_strings] if isinstance(custom_strings, str) else custom_strings
            for string in strings_to_add:
                self.keepass_manager.add_password(string, f"Temp: {string[:10]}")
        
        # Process each file
        for file_path in log_files:
            try:
                # Load the events from the log file
                events = self._extract_events_from_log(file_path)
                if not events:
                    continue
                
                # Use the KeystrokeSanitizer to process events
                sanitized_data = self.sanitizer.process_events(events)
                
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
            for pwd in self.keepass_manager.get_passwords():
                self.keepass_manager.remove_password(pwd)
            # Add back original passwords
            for pwd in original_passwords:
                self.keepass_manager.add_password(pwd)
                
        return replacements
    
    def _get_log_files(self) -> List[str]:
        """Get all keystroke log files in the logs directory"""
        if not os.path.exists(self.logs_dir):
            return []
            
        # Search for all JSON files
        return glob.glob(os.path.join(self.logs_dir, "*.json"))
    
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
    # Simple test
    import getpass
    from utils.keepass_manager import KeePassManager
    
    # Initialize KeePass manager
    manager = KeePassManager()
    
    password = getpass.getpass("Enter master password: ")
    if manager.setup_encryption(password):
        manager.load_passwords()
        
        # Create sanitizer
        sanitizer = RetroactiveSanitizer(manager)
        
        # Ask for search method
        print("\nHow would you like to search?")
        print("1. Use all stored passwords")
        print("2. Enter a custom search term")
        choice = input("Choose option (1/2): ")
        
        if choice == "2":
            search_term = input("Enter text to search for: ")
            print(f"\nFinding occurrences of '{search_term}'...")
            occurrences = sanitizer.find_occurrences(search_term)
        else:
            print("\nFinding occurrences of all stored passwords...")
            occurrences = sanitizer.find_occurrences()
        
        if occurrences:
            print(f"\nFound {sum(occurrences.values())} potential password occurrences in {len(occurrences)} files")
            for file, count in occurrences.items():
                print(f"  {file}: {count} occurrences")
                
            # Ask for confirmation
            confirm = input("\nDo you want to sanitize these files? (y/n): ")
            if confirm.lower() == 'y':
                # Sanitize logs
                if choice == "2":
                    replacements = sanitizer.sanitize_logs(search_term)
                else:
                    replacements = sanitizer.sanitize_logs()
                    
                print(f"\nSanitized {sum(replacements.values())} occurrences in {len(replacements)} files")
        else:
            print("\nNo password occurrences found")
    else:
        print("\nFailed to initialize KeePass database")