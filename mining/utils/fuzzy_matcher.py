"""
Fuzzy matching utility for password detection.
Provides multiple methods for finding password matches in text.
"""

import re
from difflib import SequenceMatcher
from dataclasses import dataclass
from typing import List, Tuple, Set


@dataclass
class Match:
    """Represents a password match in text"""
    start: int        # Start position in text
    end: int          # End position in text
    password: str     # The matched password
    similarity: float # Similarity score (0.0-1.0)
    source: str       # Match type (exact, word_boundary, fuzzy)


class FuzzyMatcher:
    """
    Provides fuzzy matching capabilities for password detection with
    different matching strategies and scoring.
    """
    
    @staticmethod
    def find_exact_matches(text, password):
        """
        Find exact matches of a password in text
        
        Args:
            text: Text to search in
            password: Password to find
            
        Returns:
            list: List of Match objects
        """
        matches = []
        # Add case insensitive option, but give it a slightly lower similarity score
        for match in re.finditer(re.escape(password), text, re.IGNORECASE):
            exact_match = password.lower() == text[match.start():match.end()].lower()
            similarity = 1.0 if exact_match else 0.95
            source = "exact" if exact_match else "exact_case_insensitive"
            
            # Trim leading/trailing whitespace
            start, end = match.start(), match.end()
            while start < end and text[start].isspace():
                start += 1
            while end > start and text[end-1].isspace():
                end -= 1
                
            if start < end:  # Only add if we have a non-whitespace match
                matches.append(Match(
                    start=start,
                    end=end,
                    password=password,
                    similarity=similarity,
                    source=source
                ))
        return matches
        
    @staticmethod
    def find_word_boundary_matches(text, password):
        """
        Find word boundary matches of a password in text
        
        Args:
            text: Text to search in
            password: Password to find
            
        Returns:
            list: List of Match objects
        """
        matches = []
        # Add case insensitive search with word boundaries
        pattern = r'\b' + re.escape(password) + r'\b'
        for match in re.finditer(pattern, text, re.IGNORECASE):
            exact_match = password.lower() == text[match.start():match.end()].lower()
            similarity = 1.0 if exact_match else 0.95
            source = "word_boundary" if exact_match else "word_boundary_case_insensitive"
            
            # Trim leading/trailing whitespace
            start, end = match.start(), match.end()
            while start < end and text[start].isspace():
                start += 1
            while end > start and text[end-1].isspace():
                end -= 1
                
            if start < end:  # Only add if we have a non-whitespace match
                matches.append(Match(
                    start=start,
                    end=end,
                    password=password,
                    similarity=similarity,
                    source=source
                ))
        return matches
    
    @staticmethod
    def find_fuzzy_matches(text, password, min_similarity=0.75):
        """
        Find fuzzy matches of a password in text using variable window sizes
        
        Args:
            text: Text to search in
            password: Password to find
            min_similarity: Minimum similarity threshold (0.0-1.0)
            
        Returns:
            list: List of Match objects
        """
        if len(password) < 4:  # Skip very short passwords for fuzzy matching
            return []
            
        matches = []
        
        # Try different window sizes based on password length
        min_window = max(len(password) - 2, 4)
        max_window = min(len(password) + 4, len(text))
        
        for window_size in range(min_window, max_window + 1):
            # Slide window through text
            for i in range(len(text) - window_size + 1):
                chunk = text[i:i + window_size]
                
                # Both case-sensitive and case-insensitive comparison
                similarity_case_sensitive = SequenceMatcher(None, password, chunk).ratio()
                similarity_case_insensitive = SequenceMatcher(None, password.lower(), chunk.lower()).ratio()
                
                # Use the higher of the two scores, but cap case-insensitive at 0.98
                similarity = similarity_case_sensitive
                source = "fuzzy"
                
                if similarity_case_insensitive > similarity_case_sensitive:
                    similarity = min(similarity_case_insensitive, 0.98)  # Cap at 0.98 to give preference to case-sensitive
                    source = "fuzzy_case_insensitive"
                
                if similarity >= min_similarity:
                    # Trim leading/trailing whitespace
                    start, end = i, i + window_size
                    while start < end and text[start].isspace():
                        start += 1
                    while end > start and text[end-1].isspace():
                        end -= 1
                    
                    if start < end:  # Only add if we have a non-whitespace match
                        matches.append(Match(
                            start=start,
                            end=end,
                            password=password,
                            similarity=similarity,
                            source=source
                        ))
        
        # Sort by similarity (highest first)
        matches.sort(key=lambda x: x.similarity, reverse=True)
        
        # Remove overlapping matches (keeping the ones with higher similarity)
        filtered_matches = []
        for match in matches:
            overlap = False
            for existing in filtered_matches:
                # Check for overlap
                if (match.start < existing.end and match.end > existing.start):
                    overlap = True
                    break
            
            if not overlap:
                filtered_matches.append(match)
        
        return filtered_matches
    
    @classmethod
    def find_all_matches(cls, text, passwords, buffer_states=None):
        """
        Find all matches using multiple strategies
        
        Args:
            text: Text to search in
            passwords: List of passwords to find
            buffer_states: Optional list of buffer states for additional detection
            
        Returns:
            list: List of Match objects
        """
        all_matches = []
        
        # First, look for similar/fuzzy matches in chunks
        if text:
            chunk_matches = cls.find_fuzzy_matches_by_chunking(text, passwords)
            all_matches.extend(chunk_matches)
            
        # Search for each password
        for password in passwords:
            # 1. First try exact matches (highest priority)
            exact_matches = cls.find_exact_matches(text, password)
            all_matches.extend(exact_matches)
            
            # 2. Try word boundary matches
            word_matches = cls.find_word_boundary_matches(text, password)
            all_matches.extend(word_matches)
            
            # 3. Try fuzzy matches if no exact or word boundary matches found
            if not exact_matches and not word_matches and len(password) >= 6:
                fuzzy_matches = cls.find_fuzzy_matches(text, password)
                all_matches.extend(fuzzy_matches)
        
        # 4. If we have buffer states, search those too
        if buffer_states:
            buffer_matches = cls.find_matches_in_buffer_states(buffer_states, passwords)
            
            # Convert buffer matches to text positions and add to all_matches
            for match in buffer_matches:
                # Check if this match overlaps with existing ones in the final text
                overlap = False
                for existing in all_matches:
                    if (match.start < existing.end and match.end > existing.start):
                        overlap = True
                        break
                        
                if not overlap:
                    all_matches.append(match)
        
        # 5. Handle empty text case (when all content was deleted)
        if not text and buffer_states and buffer_states[-1]:
            # If the final buffer state is empty but we have earlier buffer states
            # with content, add matches from buffer states
            for state in buffer_states:
                if state:  # If this buffer state has content
                    # Search for passwords in this state
                    for password in passwords:
                        if password.lower() in state.lower():
                            all_matches.append(Match(
                                start=0,
                                end=0,  # Zero-length match since the final text is empty
                                password=password,
                                similarity=1.0,
                                source="deleted_password"
                            ))
                            break  # Only add one match for the empty text
        
        # Sort by starting position
        all_matches.sort(key=lambda x: x.start)
        
        return all_matches
        
    @classmethod
    def find_fuzzy_matches_by_chunking(cls, text, passwords, chunk_size=20, overlap=10):
        """
        Find potential matches by breaking text into overlapping chunks
        
        Args:
            text: Text to search in
            passwords: List of passwords to find
            chunk_size: Size of each chunk
            overlap: How much chunks should overlap
            
        Returns:
            list: List of Match objects
        """
        matches = []
        text_len = len(text)
        
        # Process the text in chunks to avoid performance issues with long text
        for chunk_start in range(0, text_len, chunk_size - overlap):
            chunk_end = min(chunk_start + chunk_size, text_len)
            chunk = text[chunk_start:chunk_end]
            
            # For each password, look for fuzzy matches in this chunk
            for password in passwords:
                # Skip short passwords for chunking
                if len(password) < 6:
                    continue
                    
                # Calculate similarity of this chunk to the password
                similarity = SequenceMatcher(None, password.lower(), chunk.lower()).ratio()
                
                # If this chunk might contain a password
                if similarity > 0.7:
                    # Look for misspelled variations in this chunk
                    for i in range(max(0, chunk_start - 2), min(text_len, chunk_end + 2) - len(password) + 1):
                        potential_match = text[i:i+len(password)]
                        match_similarity = SequenceMatcher(None, password.lower(), potential_match.lower()).ratio()
                        
                        if match_similarity > 0.75:
                            # Found a potential misspelled match
                            matches.append(Match(
                                start=i,
                                end=i+len(password),
                                password=password,
                                similarity=match_similarity,
                                source="fuzzy_chunked"
                            ))
        
        # Remove duplicates and overlaps
        if matches:
            # Sort by similarity
            matches.sort(key=lambda x: x.similarity, reverse=True)
            
            # Filter overlapping matches (keep higher similarity ones)
            filtered_matches = []
            for match in matches:
                overlap = False
                for existing in filtered_matches:
                    if (match.start < existing.end and match.end > existing.start):
                        overlap = True
                        break
                
                if not overlap:
                    filtered_matches.append(match)
                    
            return filtered_matches
            
        return matches
    
    @classmethod
    def find_matches_in_buffer_states(cls, buffer_states, passwords):
        """
        Find password matches in all buffer states
        
        Args:
            buffer_states: List of buffer states
            passwords: List of passwords to find
            
        Returns:
            list: List of Match objects
        """
        all_matches = []
        
        # Group matches by buffer state to handle overlaps properly
        for idx, buffer in enumerate(buffer_states):
            if not buffer:  # Skip empty buffer states
                continue
                
            buffer_matches = []
            
            for password in passwords:
                # Try exact matches first (case insensitive)
                for match in re.finditer(re.escape(password), buffer, re.IGNORECASE):
                    # Trim leading/trailing whitespace
                    start, end = match.start(), match.end()
                    while start < end and buffer[start].isspace():
                        start += 1
                    while end > start and buffer[end-1].isspace():
                        end -= 1
                    
                    if start < end:  # Only add if we have a non-whitespace match
                        exact_match = password.lower() == buffer[start:end].lower()
                        similarity = 1.0 if exact_match else 0.95
                        source = f"buffer_state_{idx}_exact" if exact_match else f"buffer_state_{idx}_exact_case_insensitive"
                        
                        buffer_matches.append(Match(
                            start=start,
                            end=end,
                            password=password,
                            similarity=similarity,
                            source=source
                        ))
                
                # Try fuzzy matches for substantial passwords
                if len(password) >= 6:
                    # Check if there's an approximate match
                    is_potential_match = password.lower() in buffer.lower() or buffer.lower() in password.lower()
                    has_exact_match = any(match.password.lower() == password.lower() for match in buffer_matches)
                    
                    if (is_potential_match or not has_exact_match) and len(buffer) >= 4:
                        for match in cls.find_fuzzy_matches(buffer, password, min_similarity=0.7):
                            buffer_matches.append(Match(
                                start=match.start,
                                end=match.end,
                                password=match.password,
                                similarity=match.similarity,
                                source=f"buffer_state_{idx}_{match.source}"
                            ))
            
            # Filter overlapping matches within this buffer state
            filtered_buffer_matches = []
            buffer_matches.sort(key=lambda x: x.similarity, reverse=True)
            
            for match in buffer_matches:
                overlap = False
                for existing in filtered_buffer_matches:
                    if (match.start < existing.end and match.end > existing.start):
                        overlap = True
                        break
                
                if not overlap:
                    filtered_buffer_matches.append(match)
            
            all_matches.extend(filtered_buffer_matches)
        
        return all_matches
        
    @staticmethod
    def convert_matches_to_locations(matches):
        """
        Convert Match objects to simple (start, end) tuples
        
        Args:
            matches: List of Match objects
            
        Returns:
            list: List of (start, end) tuples
        """
        return [(match.start, match.end) for match in matches]
        
    @staticmethod
    def merge_adjacent_matches(matches, max_gap=2):
        """
        Merge adjacent matches with small gaps between them.
        Now more conservative about merging to prevent identifying multiple passwords as one.
        
        Args:
            matches: List of Match objects
            max_gap: Maximum gap size to merge
            
        Returns:
            list: List of merged Match objects
        """
        if not matches:
            return []
            
        # Sort matches by start position
        sorted_matches = sorted(matches, key=lambda x: x.start)
        
        # Group matches by password to prevent merging different passwords
        password_groups = {}
        for match in sorted_matches:
            password_key = match.password.lower()  # Group case-insensitive
            if password_key not in password_groups:
                password_groups[password_key] = []
            password_groups[password_key].append(match)
        
        merged_results = []
        
        # Process each password group separately
        for password, password_matches in password_groups.items():
            if not password_matches:
                continue
                
            merged = [password_matches[0]]
            
            for current in password_matches[1:]:
                previous = merged[-1]
                
                # Only merge if:
                # 1. They're the same password
                # 2. The gap is small
                # 3. The resulting merged match isn't way longer than the original password
                if (current.start - previous.end <= max_gap and 
                        (current.end - previous.start) < len(previous.password) * 2):
                    # Merge the matches
                    merged[-1] = Match(
                        start=previous.start,
                        end=current.end,
                        password=previous.password,
                        similarity=max(previous.similarity, current.similarity),
                        source=f"merged_{previous.source}_{current.source}"
                    )
                else:
                    # Add as separate match
                    merged.append(current)
            
            merged_results.extend(merged)
        
        # Sort final results by start position
        merged_results.sort(key=lambda x: x.start)
        return merged_results
        
    @staticmethod
    def find_adjacent_distinct_passwords(text, passwords, min_gap=0, max_gap=10):
        """
        Find adjacent but distinct passwords in text that haven't been merged.
        This is a new method to address the adjacent password detection issue.
        
        Args:
            text: Text to search in
            passwords: List of passwords to find
            min_gap: Minimum gap between passwords
            max_gap: Maximum gap between passwords to consider adjacent
            
        Returns:
            list: List of Match objects
        """
        matches = []
        
        # Find all strict exact matches first with case insensitivity
        for password in passwords:
            for match in re.finditer(re.escape(password), text, re.IGNORECASE):
                # Trim whitespace
                start, end = match.start(), match.end()
                while start < end and text[start].isspace():
                    start += 1
                while end > start and text[end-1].isspace():
                    end -= 1
                
                if start < end:
                    matches.append(Match(
                        start=start,
                        end=end,
                        password=password,
                        similarity=1.0,
                        source="exact_adjacent_check"
                    ))
        
        # Sort by position
        matches.sort(key=lambda x: x.start)
        
        # Look for adjacent distinct passwords that meet our criteria
        distinct_adjacent = []
        seen_positions = set()  # Keep track of positions we've already covered
        
        for i in range(len(matches)):
            current = matches[i]
            current_pos = (current.start, current.end)
            
            # Skip if we've already processed this position
            if current_pos in seen_positions:
                continue
                
            seen_positions.add(current_pos)
            found_adjacent = False
            
            # Check adjacent matches
            for j in range(len(matches)):
                if i == j:
                    continue
                    
                next_match = matches[j]
                next_pos = (next_match.start, next_match.end)
                
                # Skip if we've already processed this position
                if next_pos in seen_positions:
                    continue
                    
                # Check if they're adjacent with a reasonable gap
                gap = abs(next_match.start - current.end)
                
                if min_gap <= gap <= max_gap:
                    # These are adjacent distinct passwords
                    if current.password.lower() != next_match.password.lower():
                        if not any(m.start == current.start and m.end == current.end for m in distinct_adjacent):
                            distinct_adjacent.append(current)
                        if not any(m.start == next_match.start and m.end == next_match.end for m in distinct_adjacent):
                            distinct_adjacent.append(next_match)
                        seen_positions.add(next_pos)
                        found_adjacent = True
            
            # If no adjacents were found, still add the current match
            if not found_adjacent and not any(m.start == current.start and m.end == current.end for m in distinct_adjacent):
                distinct_adjacent.append(current)
        
        return distinct_adjacent
        
    @staticmethod
    def find_consecutive_matches(text, password, min_count=2):
        """
        Find consecutive occurrences of the same password
        
        Args:
            text: Text to search in
            password: Password to find consecutive occurrences of
            min_count: Minimum number of consecutive occurrences to look for
            
        Returns:
            list: List of Match objects for each individual consecutive match
        """
        matches = []
        if not text or len(text) < len(password) * min_count:
            return matches
            
        # Look for exact repeating patterns of the password
        pattern = f"({re.escape(password)}){{{min_count},}}"
        
        for match in re.finditer(pattern, text, re.IGNORECASE):
            full_match = match.group(0)
            match_start = match.start()
            
            # Calculate how many times the password appears consecutively
            password_len = len(password)
            count = len(full_match) // password_len
            
            # Create a separate match for each occurrence in the consecutive run
            for i in range(count):
                start = match_start + (i * password_len)
                end = start + password_len
                
                matches.append(Match(
                    start=start,
                    end=end,
                    password=password,
                    similarity=1.0,
                    source="consecutive_exact"
                ))
        
        return matches