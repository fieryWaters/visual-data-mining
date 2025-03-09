"""
Keystroke sanitizer module.
Processes raw keystroke data to detect and remove passwords, replacing them
with PASSWORD_FOUND events in the output stream.
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Tuple, Any, Set

from utils.password_manager import PasswordManager
from utils.text_buffer import TextBuffer
from utils.fuzzy_matcher import FuzzyMatcher


class KeystrokeSanitizer:
    """
    Sanitizes keystroke data by detecting and completely removing sensitive information.
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
        Sanitize text by replacing password locations with [REDACTED] placeholders.
        Does not use asterisks (*) at all, just clean [REDACTED] markers.
        
        Args:
            text: Original text
            password_locations: List of (start, end) tuples marking password locations
        
        Returns:
            str: Sanitized text with passwords replaced by [REDACTED]
        """
        # Handle the case with no passwords
        if not password_locations or not text:
            return text
            
        # Ensure password locations are within text bounds
        valid_locations = [(start, end) for start, end in password_locations 
                          if start < len(text) and end <= len(text)]
        
        # If no valid locations, return the original text
        if not valid_locations:
            return text
        
        # Sort the locations by start position
        sorted_locations = sorted(valid_locations, key=lambda x: x[0])
        
        # Rebuild the text with [REDACTED] markers instead of passwords
        result = ""
        last_end = 0
        
        for start, end in sorted_locations:
            # Only process if this is a new region (not contained in what we've processed)
            if start < last_end:
                continue
                
            # Add any text between the last region and this one
            if start > last_end:
                result += text[last_end:start]
                
            # Add the redaction marker - NO asterisks or padding
            result += "[REDACTED]"
            
            # Update the last endpoint
            last_end = end
            
        # Add any remaining text after the last region
        if last_end < len(text):
            result += text[last_end:]
            
        return result
        
    def _detect_passwords(self, text: str, buffer_states: List[str]) -> List[Tuple[int, int]]:
        """
        Quality-ranked greedy approach to password detection that handles:
        - Exact matches (case sensitive and insensitive)
        - Adjacent passwords (same or different)
        - Consecutive identical passwords
        - Passwords in buffer history (typed and deleted)
        
        Args:
            text: The text to search for passwords
            buffer_states: History of text buffer states
            
        Returns:
            List of (start, end) tuples indicating password regions
        """
        # Get all passwords to detect
        all_passwords = self.password_manager.get_passwords()
        if not all_passwords:
            return []
            
        if not text and not buffer_states:
            return []
            
        # Step 1: Collect ALL potential password matches
        all_matches = []
        
        # Use basic detection along with buffer states
        basic_matches = FuzzyMatcher.find_all_matches(text, all_passwords, buffer_states)
        all_matches.extend(basic_matches)
        
        # Look for adjacent distinct passwords
        adjacent_matches = FuzzyMatcher.find_adjacent_distinct_passwords(text, all_passwords)
        all_matches.extend(adjacent_matches)
        
        # Look for consecutive identical passwords
        for password in all_passwords:
            consecutive_matches = FuzzyMatcher.find_consecutive_matches(text, password, min_count=2)
            all_matches.extend(consecutive_matches)
        
        # Step 2: Score each match based on quality
        scored_matches = []
        for match in all_matches:
            # Calculate a quality score (higher is better)
            # Factors:
            # 1. Exact matches are better than fuzzy matches
            # 2. Longer matches are better than shorter
            # 3. Higher similarity is better
            # 4. Match source (some sources are more reliable)
            
            # Base score from similarity (0-100)
            score = match.similarity * 100
            
            # Bonus for exact matches
            if match.similarity >= 0.95:  # Close to exact match
                score += 25
                
            # Bonus for longer passwords (up to 20 points)
            pwd_len = len(match.password)
            length_bonus = min(20, pwd_len * 2)
            score += length_bonus
            
            # Bonus/penalty based on match source
            if "exact" in match.source:
                score += 15  # Strong bonus for exact matches
            elif "word_boundary" in match.source:
                score += 10  # Good bonus for word boundary matches
            elif "fuzzy" in match.source:
                score -= 5   # Slight penalty for fuzzy matches
                
            # Penalize matches that aren't in the known password list
            known_password = False
            for password in all_passwords:
                # Check if this is a known password (case insensitive)
                if match.password.lower() == password.lower():
                    known_password = True
                    break
                    
            if not known_password:
                # Big penalty for matches not in the password list
                score -= 30
                
            # Store the scored match
            scored_matches.append((match, score))
        
        # Step 3: Sort matches by score (highest first)
        scored_matches.sort(key=lambda x: x[1], reverse=True)
        
        # Step 4: Greedily select non-overlapping matches in order of score
        selected_matches = []
        claimed_regions = []  # Track regions already claimed by higher-scoring matches
        
        for match, score in scored_matches:
            # Check if this match significantly overlaps with any claimed region
            significant_overlap = False
            
            for start, end in claimed_regions:
                # Calculate overlap
                overlap_start = max(match.start, start)
                overlap_end = min(match.end, end)
                overlap_len = max(0, overlap_end - overlap_start)
                
                # If there's any significant overlap (>30%), reject this match
                if overlap_len > 0 and overlap_len > 0.3 * (match.end - match.start):
                    significant_overlap = True
                    break
                    
            # Only accept this match if it doesn't significantly overlap with claimed regions
            if not significant_overlap:
                selected_matches.append(match)
                # Mark this region as claimed
                claimed_regions.append((match.start, match.end))
        
        # Step 5: Convert selected matches to password regions
        password_regions = []
        for match in selected_matches:
            password_regions.append((match.start, match.end))
            
        # Step 6: Handle the special case of deleted passwords
        # (found in buffer states but not in final text)
        if not text and buffer_states and any(state for state in buffer_states):
            for password in all_passwords:
                password_lower = password.lower()
                for state in buffer_states:
                    if state and password_lower in state.lower():
                        # This password was in a buffer state but was deleted
                        # Add a zero-length region at position 0
                        password_regions.append((0, 0))
                        break
        
        # Step 7: Sort by start position and return
        return sorted(password_regions, key=lambda x: x[0])

    def process_events(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Process keystroke events to detect and sanitize passwords.
        Completely removes password-related events and replaces them with PASSWORD_FOUND events.
        
        Args:
            events: Raw keystroke events from recorder
        
        Returns:
            dict: Dictionary with processed data including:
                - events: Sanitized events with PASSWORD_FOUND events and no password events
                - text: Original text from keystrokes
                - sanitized_text: Text with passwords replaced by [REDACTED]
                - password_locations: Where passwords were found
                - buffer_states: History of text buffer states (optional debug info)
        """
        # 1. Extract text from keystroke events with enhanced event tracking
        extracted_text, buffer_states, position_to_event_ids, related_events = TextBuffer.events_to_text(events)
        
        # 2. Detect password locations in the text using unified detection
        password_locations = self._detect_passwords(extracted_text, buffer_states)
        
        # 3. Identify all keystroke events that contributed to passwords
        # First, create a set of event IDs to remove (both press and release)
        events_to_remove = set()
        
        # For each password location, collect all events that contributed to it
        for start, end in password_locations:
            if 0 <= start < end <= len(extracted_text):
                # For each position in this password region
                for pos in range(start, end):
                    # Get all events that contributed to this position
                    pos_str = str(pos)
                    if pos_str in position_to_event_ids:
                        # Add direct events for this position
                        for event_id_str in position_to_event_ids[pos_str]:
                            # Convert string ID back to int for comparison
                            event_id = int(event_id_str)
                            events_to_remove.add(event_id)
                            
                            # Also add any related release events
                            if event_id in related_events:
                                for related_id in related_events[event_id]:
                                    events_to_remove.add(related_id)
        
        # 4. Create a timestamp lookup for each event
        event_timestamps = {}
        event_to_index = {}
        for i, event in enumerate(events):
            event_id = id(event)
            event_timestamps[event_id] = event.get("timestamp", datetime.now().isoformat())
            event_to_index[event_id] = i
            
        # 5. Create a completely new sanitized event stream (without password events)
        sanitized_events = []
        
        # Only include events that are not password-related
        for event in events:
            if id(event) not in events_to_remove:
                sanitized_events.append(event.copy())
        
        # 6. Create PASSWORD_FOUND events (one for each password region)
        for start, end in password_locations:
            timestamp = datetime.now().isoformat()  # Default fallback
            
            # Find the last event that contributed to this password
            if 0 <= start < end <= len(extracted_text):
                # Look for events at the end position
                last_pos = end - 1
                pos_str = str(last_pos)
                
                if pos_str in position_to_event_ids and position_to_event_ids[pos_str]:
                    # Get the event with the latest timestamp
                    event_ids = [int(eid) for eid in position_to_event_ids[pos_str]]
                    if event_ids:
                        # Find the event with highest index (last chronologically)
                        last_event_id = max(event_ids, key=lambda eid: event_to_index.get(eid, 0) 
                                            if eid in event_to_index else 0)
                        if last_event_id in event_timestamps:
                            timestamp = event_timestamps[last_event_id]
            
            # Create PASSWORD_FOUND event
            password_found_event = {
                "event": "PASSWORD_FOUND",
                "timestamp": timestamp,
                "start_index": start,
                "end_index": end
            }
            
            # Add to sanitized events
            sanitized_events.append(password_found_event)
        
        # 7. Sanitize the extracted text (replacing passwords with [REDACTED])
        sanitized_text = self._sanitize_text(extracted_text, password_locations)
        
        # 8. Return results
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


# Run tests from the tests directory
if __name__ == "__main__":
    print("Please use test_keystroke_sanitizer.py in the tests directory to test this module.")