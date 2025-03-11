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
from utils.fuzzy_matcher import FuzzyMatcher, Match


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
        Preserves non-password characters between adjacent password matches.
        
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
                between_text = text[last_end:start]
                result += between_text
                
            # Add the redaction marker - NO asterisks or padding
            result += "[REDACTED]"
            
            # Update the last endpoint
            last_end = end
            
        # Add any remaining text after the last region
        if last_end < len(text):
            remaining_text = text[last_end:]
            result += remaining_text
            
        return result
        
    def _find_optimal_length(self, test_string, reference_password):
        """
        Find the optimal length for a password match by analyzing the similarity curve.
        Identifies the point where adding more characters consistently decreases similarity.
        
        Args:
            test_string: The string to analyze
            reference_password: The password to compare against
            
        Returns:
            int: The optimal length (0 if no clear breakpoint found)
        """
        # Too short to analyze
        if len(test_string) < 5:
            return 0
            
        # Track similarity at each length
        similarities = []
        for i in range(1, len(test_string) + 1):
            substring = test_string[:i]
            similarity = FuzzyMatcher.calculate_similarity(substring, reference_password)
            similarities.append(similarity)
        
        # Find the peak followed by consistent decreases
        optimal_length = 0
        max_similarity = 0
        decreasing_count = 0
        
        for i in range(1, len(similarities)):
            current = similarities[i]
            previous = similarities[i-1]
            
            # If increasing, update max values and reset decreasing counter
            if current > previous:
                max_similarity = current
                optimal_length = i + 1  # Convert to 1-based index
                decreasing_count = 0
            # If decreasing significantly from the peak
            elif current < previous - 0.01:
                decreasing_count += 1
                # Break point after 3 consecutive decreases
                if decreasing_count >= 3 and optimal_length > 0:
                    # Return the position before decreases started
                    return optimal_length
            # If basically flat, don't count as decreasing
            else:
                decreasing_count = 0
                
        # If we found a reasonable peak but didn't hit 3 consecutive decreases
        # (might happen at the end of the string)
        if optimal_length > 0 and max_similarity > 0.7:
            # Find the last increasing point
            for i in range(len(similarities) - 1, 0, -1):
                if similarities[i] > similarities[i-1]:
                    final_optimal = i + 1  # Convert to 1-based index
                    return final_optimal
        
        return optimal_length
    
    def _detect_passwords(self, text: str, buffer_states: List[str]) -> List[Tuple[int, int]]:
        """
        Simplified approach to password detection using sliding window similarity matching.
        Handles adjacent passwords, exact matches, and variations naturally through
        a single unified algorithm.
        
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
        
        # Helper function to remove overlapping regions
        def remove_overlapping(candidates, selected_region):
            """Remove candidates that overlap with the selected region"""
            start, end = selected_region
            return [c for c in candidates if not (c[0] < end and c[1] > start)]
        
        # Step 1: Generate all potential matches using sliding windows
        match_candidates = []
        
        for password in all_passwords:
            password_len = len(password)
            min_window = max(password_len - 2, 4)  # Allow for slight variations
            max_window = min(password_len + 4, len(text))
            
            # For each possible window size
            for window_size in range(min_window, max_window + 1):
                # Slide window through text
                for i in range(len(text) - window_size + 1):
                    window_text = text[i:i + window_size]
                    
                    # Calculate similarity (case insensitive)
                    similarity = FuzzyMatcher.calculate_similarity(window_text.lower(), password.lower())
                    
                    # Keep matches above threshold
                    if similarity >= 0.75:
                        match_candidates.append((i, i + window_size, window_text, password, similarity))
        
        # Step 2: For each candidate, optimize the length by probing nearby lengths
        optimized_candidates = []
        
        for start, end, match_text, ref_password, similarity in match_candidates:
            # If it's a perfect match, keep as is
            if similarity >= 0.99:
                optimized_candidates.append((start, end, match_text, ref_password, similarity))
                continue
            
            # Find optimal length by analyzing similarity curve
            optimal_length = self._find_optimal_length(match_text, ref_password)
            
            if optimal_length > 0 and optimal_length != len(match_text):
                # Create optimized match
                new_text = match_text[:optimal_length]
                new_end = start + optimal_length
                new_similarity = FuzzyMatcher.calculate_similarity(new_text.lower(), ref_password.lower())
                
                optimized_candidates.append((start, new_end, new_text, ref_password, new_similarity))
            else:
                # Keep original if optimization didn't improve
                optimized_candidates.append((start, end, match_text, ref_password, similarity))
        
        # Step 3: Sort by similarity (highest first)
        optimized_candidates.sort(key=lambda x: x[4], reverse=True)
        
        # Step 4: Greedily select non-overlapping matches in order of similarity
        selected_regions = []
        remaining_candidates = optimized_candidates.copy()
        
        # First process perfect or near-perfect matches (similarity >= 0.9)
        high_confidence = [c for c in remaining_candidates if c[4] >= 0.9]
        
        for start, end, match_text, ref_password, similarity in high_confidence:
            # Check if this overlaps with already selected regions
            overlaps = any(s < end and e > start for s, e in selected_regions)
            
            if not overlaps:
                selected_regions.append((start, end))
                # Remove overlapping candidates
                remaining_candidates = remove_overlapping(remaining_candidates, (start, end))
        
        # Then process good matches (similarity >= 0.85)
        good_matches = [c for c in remaining_candidates if c[4] >= 0.85]
        
        for start, end, match_text, ref_password, similarity in good_matches:
            # Check if this overlaps with already selected regions
            overlaps = any(s < end and e > start for s, e in selected_regions)
            
            if not overlaps:
                selected_regions.append((start, end))
                # Remove overlapping candidates
                remaining_candidates = remove_overlapping(remaining_candidates, (start, end))
        
        # Step 5: Handle buffer states for deleted passwords
        if not text and buffer_states and any(state for state in buffer_states):
            for password in all_passwords:
                password_lower = password.lower()
                for state in buffer_states:
                    if state and password_lower in state.lower():
                        # This password was in a buffer state but was deleted
                        selected_regions.append((0, 0))
                        break
        
        # Return the final password regions, sorted by position
        return sorted(selected_regions)

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