"""
Tests for the FuzzyMatcher utility class
"""

import unittest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.fuzzy_matcher import FuzzyMatcher, Match


class TestFuzzyMatcher(unittest.TestCase):
    """Tests for the FuzzyMatcher utility"""
    
    def test_exact_matches(self):
        """Test finding exact matches"""
        text = "The password is secret123 and another password is secret456"
        password = "secret123"
        
        matches = FuzzyMatcher.find_exact_matches(text, password)
        
        self.assertEqual(len(matches), 1, "Should find exactly one match")
        self.assertEqual(matches[0].start, 16, "Match should start at position 16")
        self.assertEqual(matches[0].end, 25, "Match should end at position 25")
        self.assertEqual(matches[0].similarity, 1.0, "Exact match should have similarity 1.0")
        self.assertEqual(matches[0].source, "exact", "Source should be 'exact'")
    
    def test_word_boundary_matches(self):
        """Test finding word boundary matches"""
        text = "Password: secret123. Another password: secret123test"
        password = "secret123"
        
        matches = FuzzyMatcher.find_word_boundary_matches(text, password)
        
        self.assertEqual(len(matches), 1, "Should find exactly one word boundary match")
        self.assertEqual(matches[0].start, 10, "Match should start at position 10")
        self.assertEqual(matches[0].end, 19, "Match should end at position 19")
    
    def test_fuzzy_matches(self):
        """Test finding fuzzy matches"""
        text = "My password is secrett1234"
        password = "secret123"
        
        matches = FuzzyMatcher.find_fuzzy_matches(text, password)
        
        self.assertGreater(len(matches), 0, "Should find at least one fuzzy match")
        self.assertGreater(matches[0].similarity, 0.7, "Similarity should be above threshold")
    
    def test_overlapping_matches(self):
        """Test handling of overlapping matches"""
        text = "secret123secret123"  # Overlapping matches
        password = "secret123"
        
        # First test that we find two matches with exact matching
        exact_matches = FuzzyMatcher.find_exact_matches(text, password)
        self.assertEqual(len(exact_matches), 2, "Should find two exact matches")
        
        # Now test with fuzzy matching which should filter overlaps
        fuzzy_matches = FuzzyMatcher.find_fuzzy_matches(text, password)
        
        # The filtered results should have non-overlapping matches
        for i in range(len(fuzzy_matches)):
            for j in range(i+1, len(fuzzy_matches)):
                self.assertFalse(
                    fuzzy_matches[i].start < fuzzy_matches[j].end and 
                    fuzzy_matches[i].end > fuzzy_matches[j].start,
                    "Matches should not overlap"
                )
    
    def test_find_all_matches(self):
        """Test finding all matches with different strategies"""
        text = "My first password is secret123 and my second is secret456"
        passwords = ["secret123", "secret456"]
        
        matches = FuzzyMatcher.find_all_matches(text, passwords)
        
        # We might find multiple matches including potential fuzzy matches
        # Just verify we have at least the two passwords we specified
        found_passwords = set(match.password for match in matches)
        self.assertTrue(len(found_passwords) >= 2, "Should find at least both passwords")
        
        # Verify the matches are for different passwords
        found_passwords = [match.password for match in matches]
        self.assertIn("secret123", found_passwords, "Should find first password")
        self.assertIn("secret456", found_passwords, "Should find second password")
    
    def test_find_matches_in_buffer_states(self):
        """Test finding matches in buffer states"""
        buffer_states = [
            "Type your password: s",
            "Type your password: se",
            "Type your password: sec",
            "Type your password: secr",
            "Type your password: secre",
            "Type your password: secret",
            "Type your password: secret1",
            "Type your password: secret12",
            "Type your password: secret123",
            "Type your password: ",  # Password deleted
            "Type your password: different"  # Different text
        ]
        passwords = ["secret123"]
        
        matches = FuzzyMatcher.find_matches_in_buffer_states(buffer_states, passwords)
        
        # Should find the complete password in one of the buffer states
        self.assertGreater(len(matches), 0, "Should find password in buffer states")
        
        # The last buffer state with the password should be the one with the complete password
        complete_match = False
        for match in matches:
            if match.source.endswith("exact") and buffer_states[int(match.source.split("_")[2])][match.start:match.end] == "secret123":
                complete_match = True
                
        self.assertTrue(complete_match, "Should find complete password match in buffer states")
    
    def test_merge_adjacent_matches(self):
        """Test merging adjacent matches"""
        # Create a list of matches that are adjacent
        matches = [
            Match(start=10, end=15, password="secret", similarity=0.9, source="fuzzy"),
            Match(start=16, end=19, password="secret", similarity=0.8, source="fuzzy")
        ]
        
        merged = FuzzyMatcher.merge_adjacent_matches(matches, max_gap=1)
        
        self.assertEqual(len(merged), 1, "Adjacent matches should be merged")
        self.assertEqual(merged[0].start, 10, "Merged match should start at first match's start")
        self.assertEqual(merged[0].end, 19, "Merged match should end at last match's end")
        
        # Test with non-adjacent matches
        matches = [
            Match(start=10, end=15, password="secret", similarity=0.9, source="fuzzy"),
            Match(start=20, end=25, password="secret", similarity=0.8, source="fuzzy")
        ]
        
        merged = FuzzyMatcher.merge_adjacent_matches(matches, max_gap=1)
        
        self.assertEqual(len(merged), 2, "Non-adjacent matches should not be merged")
    
    def test_convert_matches_to_locations(self):
        """Test converting Match objects to location tuples"""
        matches = [
            Match(start=10, end=15, password="secret", similarity=0.9, source="fuzzy"),
            Match(start=20, end=25, password="secret", similarity=0.8, source="fuzzy")
        ]
        
        locations = FuzzyMatcher.convert_matches_to_locations(matches)
        
        self.assertEqual(len(locations), 2, "Should have the same number of locations as matches")
        self.assertEqual(locations[0], (10, 15), "First location should match first match")
        self.assertEqual(locations[1], (20, 25), "Second location should match second match")


if __name__ == "__main__":
    unittest.main()