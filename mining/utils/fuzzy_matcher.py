"""
Fuzzy matching utility for password detection.
Provides core methods for finding password matches in text.
"""

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
    source: str       # Match type (exact, fuzzy, etc.)


class FuzzyMatcher:
    """
    Provides fuzzy matching capabilities for password detection.
    """
    
    @staticmethod
    def calculate_similarity(str1, str2):
        """
        Calculate similarity between two strings.
        Handles case insensitivity and different string lengths.
        
        Args:
            str1: First string
            str2: Second string
            
        Returns:
            float: Similarity score (0.0-1.0)
        """
        # Convert to lowercase for case-insensitive comparison
        str1_lower = str1.lower()
        str2_lower = str2.lower()
        
        # Check for exact match after case normalization
        if str1_lower == str2_lower:
            return 1.0
            
        # Use SequenceMatcher for fuzzy matching
        return SequenceMatcher(None, str1_lower, str2_lower).ratio()
    
    @staticmethod
    def remove_overlapping_matches(matches: List[Match]) -> List[Match]:
        """
        Remove overlapping matches, keeping the ones with higher similarity.
        
        Args:
            matches: List of Match objects
            
        Returns:
            list: Filtered list of non-overlapping Match objects
        """
        if not matches:
            return []
            
        # Sort by similarity (highest first)
        sorted_matches = sorted(matches, key=lambda x: x.similarity, reverse=True)
        
        # Filter overlapping matches (keep higher similarity ones)
        filtered_matches = []
        for match in sorted_matches:
            overlap = False
            for existing in filtered_matches:
                if (match.start < existing.end and match.end > existing.start):
                    overlap = True
                    break
            
            if not overlap:
                filtered_matches.append(match)
                
        # Re-sort by position for consistency
        filtered_matches.sort(key=lambda x: x.start)
        return filtered_matches
    
    @classmethod
    def find_matches(cls, text: str, passwords: List[str], min_similarity: float = 0.75) -> List[Match]:
        """
        Find all password matches in text using a single unified algorithm.
        Combines exact, word boundary, and fuzzy matching in one method.
        
        Args:
            text: Text to search in
            passwords: List of passwords to find
            min_similarity: Minimum similarity threshold (0.0-1.0)
            
        Returns:
            list: List of Match objects
        """
        all_matches = []
        
        # Skip processing if there's no text or passwords
        if not text or not passwords:
            return []
        
        # Process each password
        for password in passwords:
            # Skip very short passwords for fuzzy matching
            if len(password) < 4:
                continue
                
            # Try different window sizes based on password length
            min_window = max(len(password) - 2, 4)
            max_window = min(len(password) + 4, len(text))
            
            for window_size in range(min_window, max_window + 1):
                # Slide window through text
                for i in range(len(text) - window_size + 1):
                    chunk = text[i:i + window_size]
                    
                    # Check similarity (case insensitive)
                    similarity = cls.calculate_similarity(password, chunk)
                    
                    # Is this a good match?
                    if similarity >= min_similarity:
                        # Determine the match type
                        source = "exact" if similarity >= 0.99 else "fuzzy"
                        
                        # Trim leading/trailing whitespace
                        start, end = i, i + window_size
                        while start < end and text[start].isspace():
                            start += 1
                        while end > start and text[end-1].isspace():
                            end -= 1
                        
                        if start < end:  # Only add if we have a non-whitespace match
                            all_matches.append(Match(
                                start=start,
                                end=end,
                                password=password,
                                similarity=similarity,
                                source=source
                            ))
        
        # Remove overlapping matches
        return cls.remove_overlapping_matches(all_matches)
    
    @staticmethod
    def convert_matches_to_locations(matches: List[Match]) -> List[Tuple[int, int]]:
        """
        Convert Match objects to simple (start, end) tuples
        
        Args:
            matches: List of Match objects
            
        Returns:
            list: List of (start, end) tuples
        """
        return [(match.start, match.end) for match in matches]