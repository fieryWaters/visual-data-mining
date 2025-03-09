"""
Fuzzy matching utility for password detection.
Provides multiple methods for finding password matches in text.
"""

import re
from difflib import SequenceMatcher
from dataclasses import dataclass
from typing import List, Tuple


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
        for match in re.finditer(re.escape(password), text):
            matches.append(Match(
                start=match.start(),
                end=match.end(),
                password=password,
                similarity=1.0,
                source="exact"
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
        for match in re.finditer(r'\b' + re.escape(password) + r'\b', text):
            matches.append(Match(
                start=match.start(),
                end=match.end(),
                password=password,
                similarity=1.0,
                source="word_boundary"
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
                similarity = SequenceMatcher(None, password, chunk).ratio()
                
                if similarity >= min_similarity:
                    # Found potential match
                    matches.append(Match(
                        start=i,
                        end=i + window_size,
                        password=password,
                        similarity=similarity,
                        source="fuzzy"
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
        
        # Sort by starting position
        all_matches.sort(key=lambda x: x.start)
        
        return all_matches
    
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
            buffer_matches = []
            
            for password in passwords:
                # Try exact matches first
                for match in re.finditer(re.escape(password), buffer):
                    buffer_matches.append(Match(
                        start=match.start(),
                        end=match.end(),
                        password=password,
                        similarity=1.0,
                        source=f"buffer_state_{idx}_exact"
                    ))
                
                # Try fuzzy matches for substantial passwords
                if len(password) >= 6 and not any(match.password == password for match in buffer_matches):
                    for match in cls.find_fuzzy_matches(buffer, password):
                        buffer_matches.append(Match(
                            start=match.start,
                            end=match.end,
                            password=match.password,
                            similarity=match.similarity,
                            source=f"buffer_state_{idx}_fuzzy"
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
    def merge_adjacent_matches(matches, max_gap=3):
        """
        Merge adjacent matches with small gaps between them
        
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
        
        merged = [sorted_matches[0]]
        
        for current in sorted_matches[1:]:
            previous = merged[-1]
            
            # Check if current match is adjacent to previous match
            if current.start - previous.end <= max_gap:
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
                
        return merged