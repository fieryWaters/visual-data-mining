#!/usr/bin/env python3
"""
Retroactive sanitization for keystroke logs.
Scans existing keystroke logs for sensitive information and sanitizes them.
"""

import os
import json
import glob
from typing import Dict, List, Tuple, Any

from utils.keepass_manager import KeePassManager
from utils.fuzzy_matcher import FuzzyMatcher


class RetroactiveSanitizer:
    """
    Scan and sanitize keystroke logs for sensitive information.
    """
    
    def __init__(self, keepass_manager, logs_dir="logs/sanitized_json"):
        """Initialize with KeePass manager and logs directory"""
        self.keepass_manager = keepass_manager
        self.logs_dir = logs_dir
        
    def find_occurrences(self) -> Dict[str, int]:
        """
        Find potential password occurrences in log files without modifying them.
        
        Returns:
            Dict mapping filenames to the number of occurrences found
        """
        if not self.keepass_manager.kp:
            return {}
            
        # Get passwords to search for
        passwords = self.keepass_manager.get_passwords()
        if not passwords:
            return {}
            
        # Get all log files
        log_files = self._get_log_files()
        if not log_files:
            return {}
            
        # Track occurrences per file
        occurrences = {}
        
        # Process each file
        for file_path in log_files:
            try:
                # Load the JSON file
                with open(file_path, 'r') as f:
                    log_data = json.load(f)
                    
                # Extract all text content from events
                text_content = self._extract_text_from_log(log_data)
                if not text_content:
                    continue
                    
                # Find matches
                matches = FuzzyMatcher.find_matches(text_content, passwords)
                
                # Store the count of occurrences
                if matches:
                    filename = os.path.basename(file_path)
                    occurrences[filename] = len(matches)
            
            except Exception as e:
                print(f"Error processing file {file_path}: {e}")
                
        return occurrences
    
    def sanitize_logs(self) -> Dict[str, int]:
        """
        Sanitize all log files by replacing passwords with [REDACTED].
        
        Returns:
            Dict mapping filenames to the number of replacements made
        """
        if not self.keepass_manager.kp:
            return {}
            
        # Get passwords to search for
        passwords = self.keepass_manager.get_passwords()
        if not passwords:
            return {}
            
        # Get all log files
        log_files = self._get_log_files()
        if not log_files:
            return {}
            
        # Track replacements per file
        replacements = {}
        
        # Process each file
        for file_path in log_files:
            try:
                # Load the JSON file
                with open(file_path, 'r') as f:
                    log_data = json.load(f)
                    
                # Check if we need to process this file
                text_content = self._extract_text_from_log(log_data)
                if not text_content:
                    continue
                    
                # Find matches
                matches = FuzzyMatcher.find_matches(text_content, passwords)
                if not matches:
                    continue
                    
                # Sanitize the text
                sanitized_text = self._sanitize_text(text_content, matches)
                
                # Update the log data with sanitized text
                sanitized_log = self._update_log_with_sanitized_text(log_data, sanitized_text)
                
                # Save the sanitized data back to the file
                with open(file_path, 'w') as f:
                    json.dump(sanitized_log, f, indent=2)
                    
                # Store the count of replacements
                filename = os.path.basename(file_path)
                replacements[filename] = len(matches)
            
            except Exception as e:
                print(f"Error sanitizing file {file_path}: {e}")
                
        return replacements
    
    def _get_log_files(self) -> List[str]:
        """Get all keystroke log files in the logs directory"""
        if not os.path.exists(self.logs_dir):
            return []
            
        # Search for all JSON files
        return glob.glob(os.path.join(self.logs_dir, "*.json"))
    
    def _extract_text_from_log(self, log_data: Dict[str, Any]) -> str:
        """Extract all text content from a log file"""
        # Most logs have a 'text_summary' field that might contain the text
        if 'text_summary' in log_data and 'original_text' in log_data['text_summary']:
            return log_data['text_summary']['original_text']
            
        # Some logs might store the text directly
        if 'text' in log_data:
            return log_data['text']
            
        # Reconstruct text from events if needed
        text = ""
        if 'events' in log_data:
            for event in log_data['events']:
                if event.get('event') == 'key_press' and 'character' in event:
                    text += event['character']
        
        return text
    
    def _sanitize_text(self, text: str, matches: List[Any]) -> str:
        """Replace password matches with [REDACTED]"""
        if not text or not matches:
            return text
            
        # Convert matches to (start, end) tuples
        password_locations = [(match.start, match.end) for match in matches]
        
        # Sort by start position
        sorted_locations = sorted(password_locations, key=lambda x: x[0])
        
        # Build sanitized text
        result = ""
        last_end = 0
        
        for start, end in sorted_locations:
            if start < last_end:
                continue  # Skip overlapping matches
                
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
    
    def _update_log_with_sanitized_text(self, log_data: Dict[str, Any], sanitized_text: str) -> Dict[str, Any]:
        """Update the log data with the sanitized text"""
        # Create a copy of the log data
        sanitized_log = log_data.copy()
        
        # Update text in text_summary if it exists
        if 'text_summary' in sanitized_log:
            if 'original_text' in sanitized_log['text_summary']:
                sanitized_log['text_summary']['original_text'] = sanitized_text
                
            if 'sanitized_text' in sanitized_log['text_summary']:
                sanitized_log['text_summary']['sanitized_text'] = sanitized_text
        
        # Update direct text field if it exists
        if 'text' in sanitized_log:
            sanitized_log['text'] = sanitized_text
            
        # Set sanitization flags
        if 'metadata' in sanitized_log:
            sanitized_log['metadata']['contains_sensitive_data'] = True
            sanitized_log['metadata']['sanitization_applied'] = True
            
        # Mark events that contain password data
        if 'events' in sanitized_log:
            # Add a sanitization event if none exists
            has_password_event = any(e.get('event') == 'PASSWORD_FOUND' for e in sanitized_log['events'])
            if not has_password_event:
                sanitized_log['events'].append({
                    'event': 'PASSWORD_FOUND',
                    'retroactive_sanitization': True,
                    'message': 'Retroactively sanitized sensitive data'
                })
        
        return sanitized_log


if __name__ == "__main__":
    # Simple test
    import getpass
    
    # Initialize KeePass manager
    manager = KeePassManager()
    
    password = getpass.getpass("Enter master password: ")
    if manager.setup_encryption(password):
        manager.load_passwords()
        
        # Create sanitizer
        sanitizer = RetroactiveSanitizer(manager)
        
        # Find occurrences
        print("Finding password occurrences...")
        occurrences = sanitizer.find_occurrences()
        
        if occurrences:
            print(f"Found {sum(occurrences.values())} potential password occurrences in {len(occurrences)} files")
            for file, count in occurrences.items():
                print(f"  {file}: {count} occurrences")
                
            # Ask for confirmation
            confirm = input("Do you want to sanitize these files? (y/n): ")
            if confirm.lower() == 'y':
                # Sanitize logs
                replacements = sanitizer.sanitize_logs()
                print(f"Sanitized {sum(replacements.values())} occurrences in {len(replacements)} files")
        else:
            print("No password occurrences found")