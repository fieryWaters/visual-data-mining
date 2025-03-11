"""
FuzzyMatcher Tests
==================

This module tests the FuzzyMatcher utility which is responsible for identifying
sensitive information (passwords) in text using various matching strategies:

1. Exact matching - For precise password detection
2. Word boundary matching - For passwords surrounded by non-alphanumeric characters
3. Fuzzy matching - For detecting password variants or typos
4. Buffer state matching - For detecting passwords across keystroke history

The tests verify that the matcher correctly identifies and processes sensitive 
information with proper handling of edge cases like overlapping matches.
"""

import unittest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.fuzzy_matcher import FuzzyMatcher, Match


class TestFuzzyMatcher(unittest.TestCase):
    """Tests for the FuzzyMatcher utility"""
    
    def setUp(self):
        """Set up the test environment"""
        print("\n" + "="*80)
        
    def test_exact_matches(self):
        """
        TEST 1: Exact Matching
        ----------------------
        Tests the ability to find exact occurrences of passwords in text.
        
        Expected outcome:
        - Finds exactly one match at the correct position
        - Match has similarity 1.0 and source "exact"
        """
        print("TEST 1: Exact Matching")
        print("="*80)
        
        text = "The password is secret123 and another password is secret456"
        password = "secret123"
        
        print(f"Input text: '{text}'")
        print(f"Password to find: '{password}'")
        
        print("Finding exact matches...")
        matches = FuzzyMatcher.find_exact_matches(text, password)
        
        # Output results
        if len(matches) == 0:
            print("  No matches found")
        else:
            print(f"  Found {len(matches)} matches:")
            for i, match in enumerate(matches):
                print(f"    Match {i+1}: '{text[match.start:match.end]}' at positions {match.start}-{match.end}")
                print(f"      Similarity: {match.similarity}, Source: {match.source}")
        
        # Assertions
        self.assertEqual(len(matches), 1, "Should find exactly one match")
        
        if len(matches) > 0:
            self.assertEqual(matches[0].start, 16, "Match should start at position 16")
            self.assertEqual(matches[0].end, 25, "Match should end at position 25")
            self.assertEqual(matches[0].similarity, 1.0, "Exact match should have similarity 1.0")
            self.assertEqual(matches[0].source, "exact", "Source should be 'exact'")
            print("  ✓ All assertions passed")
    
    def test_word_boundary_matches(self):
        """
        TEST 2: Word Boundary Matching
        -----------------------------
        Tests finding passwords at word boundaries (surrounded by non-alphanumeric chars).
        This is useful for detecting passwords in contexts like:
        "Password: secret123." but not in "secret123test"
        
        Expected outcome:
        - Finds one match that's at a word boundary
        - Does not match when password is part of a larger word
        """
        print("TEST 2: Word Boundary Matching")
        print("="*80)
        
        text = "Password: secret123. Another password: secret123test"
        password = "secret123"
        
        print(f"Input text: '{text}'")
        print(f"Password to find: '{password}'")
        
        print("Finding word boundary matches...")
        matches = FuzzyMatcher.find_word_boundary_matches(text, password)
        
        # Output results
        if len(matches) == 0:
            print("  No matches found")
        else:
            print(f"  Found {len(matches)} matches:")
            for i, match in enumerate(matches):
                print(f"    Match {i+1}: '{text[match.start:match.end]}' at positions {match.start}-{match.end}")
                print(f"      Similarity: {match.similarity}, Source: {match.source}")
                
        # Check if the non-boundary match was correctly excluded
        if "secret123test" not in [text[match.start:match.end] for match in matches]:
            print("  ✓ Correctly excluded 'secret123test' (not at word boundary)")
        
        # Assertions
        self.assertEqual(len(matches), 1, "Should find exactly one word boundary match")
        
        if len(matches) > 0:
            self.assertEqual(matches[0].start, 10, "Match should start at position 10")
            self.assertEqual(matches[0].end, 19, "Match should end at position 19")
            print("  ✓ All assertions passed")
    
    def test_fuzzy_matches(self):
        """
        TEST 3: Fuzzy Matching
        ---------------------
        Tests finding passwords with small variations using fuzzy matching.
        This is useful for detecting typos or slightly modified passwords.
        
        Expected outcome:
        - Finds at least one fuzzy match for a similar password
        - Match has similarity above threshold (typically 0.7)
        """
        print("TEST 3: Fuzzy Matching")
        print("="*80)
        
        text = "My password is secrett1234"
        password = "secret123"
        
        print(f"Input text: '{text}'")
        print(f"Password to find: '{password}'")
        print(f"Looking for fuzzy matches (variants of the password)...")
        
        matches = FuzzyMatcher.find_fuzzy_matches(text, password)
        
        # Output results
        if len(matches) == 0:
            print("  No fuzzy matches found")
        else:
            print(f"  Found {len(matches)} fuzzy matches:")
            for i, match in enumerate(matches):
                print(f"    Match {i+1}: '{text[match.start:match.end]}' at positions {match.start}-{match.end}")
                print(f"      Similarity: {match.similarity}, Source: {match.source}")
        
        # Assertions
        self.assertGreater(len(matches), 0, "Should find at least one fuzzy match")
        
        if len(matches) > 0:
            self.assertGreater(matches[0].similarity, 0.7, "Similarity should be above threshold")
            print(f"  ✓ Found fuzzy match with similarity {matches[0].similarity}")
            print("  ✓ All assertions passed")
    
    def test_overlapping_matches(self):
        """
        TEST 4: Overlapping Matches
        --------------------------
        Tests handling of overlapping password matches.
        The matcher should properly handle cases where passwords overlap.
        
        Expected outcome:
        - Exact matching finds all overlapping instances
        - Fuzzy matching properly filters overlapping matches
        """
        print("TEST 4: Overlapping Matches")
        print("="*80)
        
        text = "secret123secret123"  # Overlapping matches
        password = "secret123"
        
        print(f"Input text: '{text}' (contains overlapping instances)")
        print(f"Password to find: '{password}'")
        
        # First test that we find two matches with exact matching
        print("Finding exact matches (should find all instances)...")
        exact_matches = FuzzyMatcher.find_exact_matches(text, password)
        
        # Output exact matches
        if len(exact_matches) == 0:
            print("  No exact matches found")
        else:
            print(f"  Found {len(exact_matches)} exact matches:")
            for i, match in enumerate(exact_matches):
                print(f"    Match {i+1}: '{text[match.start:match.end]}' at positions {match.start}-{match.end}")
        
        self.assertEqual(len(exact_matches), 2, "Should find two exact matches")
        print("  ✓ Exact matching correctly found 2 overlapping instances")
        
        # Now test with fuzzy matching which should filter overlaps
        print("Finding fuzzy matches (should handle overlaps)...")
        fuzzy_matches = FuzzyMatcher.find_fuzzy_matches(text, password)
        
        # Output fuzzy matches
        if len(fuzzy_matches) == 0:
            print("  No fuzzy matches found")
        else:
            print(f"  Found {len(fuzzy_matches)} fuzzy matches:")
            for i, match in enumerate(fuzzy_matches):
                print(f"    Match {i+1}: '{text[match.start:match.end]}' at positions {match.start}-{match.end}")
        
        # Check for overlaps
        overlap_found = False
        for i in range(len(fuzzy_matches)):
            for j in range(i+1, len(fuzzy_matches)):
                if (fuzzy_matches[i].start < fuzzy_matches[j].end and 
                    fuzzy_matches[i].end > fuzzy_matches[j].start):
                    overlap_found = True
                    print(f"  ✗ Found overlapping matches: {fuzzy_matches[i]} and {fuzzy_matches[j]}")
        
        if not overlap_found:
            print("  ✓ No overlapping matches found in fuzzy results")
        
        # The filtered results should have non-overlapping matches
        for i in range(len(fuzzy_matches)):
            for j in range(i+1, len(fuzzy_matches)):
                self.assertFalse(
                    fuzzy_matches[i].start < fuzzy_matches[j].end and 
                    fuzzy_matches[i].end > fuzzy_matches[j].start,
                    "Matches should not overlap"
                )
        print("  ✓ All assertions passed")
    
    def test_find_all_matches(self):
        """
        TEST 5: Finding All Matches
        --------------------------
        Tests the comprehensive search for multiple passwords in text.
        Uses all matching strategies to find all instances of multiple passwords.
        
        Expected outcome:
        - Finds multiple passwords in the same text
        - Returns matches for different passwords
        """
        print("TEST 5: Finding All Matches")
        print("="*80)
        
        text = "My first password is secret123 and my second is secret456"
        passwords = ["secret123", "secret456"]
        
        print(f"Input text: '{text}'")
        print(f"Passwords to find: {passwords}")
        
        print("Finding all matches with all strategies...")
        matches = FuzzyMatcher.find_all_matches(text, passwords)
        
        # Output results
        if len(matches) == 0:
            print("  No matches found")
        else:
            print(f"  Found {len(matches)} matches:")
            for i, match in enumerate(matches):
                print(f"    Match {i+1}: '{text[match.start:match.end]}' (password: '{match.password}')")
                print(f"      Positions: {match.start}-{match.end}, Similarity: {match.similarity}, Source: {match.source}")
        
        # We might find multiple matches including potential fuzzy matches
        # Just verify we have at least the two passwords we specified
        found_passwords = set(match.password for match in matches)
        print(f"  Found passwords: {found_passwords}")
        
        self.assertTrue(len(found_passwords) >= 2, "Should find at least both passwords")
        
        # Verify the matches are for different passwords
        found_passwords = [match.password for match in matches]
        self.assertIn("secret123", found_passwords, "Should find first password")
        self.assertIn("secret456", found_passwords, "Should find second password")
        print("  ✓ All assertions passed")
    
    def test_find_matches_in_buffer_states(self):
        """
        TEST 6: Matches in Buffer States
        -------------------------------
        Tests finding passwords across buffer states (keystroke history).
        This simulates detecting passwords as they're being typed.
        
        Expected outcome:
        - Finds password as it's being typed across buffer states
        - Identifies complete password in appropriate buffer state
        """
        print("TEST 6: Matches in Buffer States")
        print("="*80)
        
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
        
        print("Buffer states (representing keystroke history):")
        for i, state in enumerate(buffer_states):
            print(f"  State {i}: '{state}'")
        
        print(f"Password to find: '{passwords[0]}'")
        print("Finding matches across buffer states...")
        
        matches = FuzzyMatcher.find_matches_in_buffer_states(buffer_states, passwords)
        
        # Output results
        if len(matches) == 0:
            print("  No matches found in buffer states")
        else:
            print(f"  Found {len(matches)} matches:")
            for i, match in enumerate(matches):
                state_index = int(match.source.split("_")[2]) if "_" in match.source else "unknown"
                if state_index != "unknown" and state_index < len(buffer_states):
                    matched_text = buffer_states[state_index][match.start:match.end]
                    print(f"    Match {i+1}: '{matched_text}' in state {state_index}")
                    print(f"      Positions: {match.start}-{match.end}, Similarity: {match.similarity}, Source: {match.source}")
                else:
                    print(f"    Match {i+1}: Unknown text at positions {match.start}-{match.end}")
                    print(f"      Similarity: {match.similarity}, Source: {match.source}")
        
        # Should find the complete password in one of the buffer states
        self.assertGreater(len(matches), 0, "Should find password in buffer states")
        
        # The last buffer state with the password should be the one with the complete password
        complete_match = False
        for match in matches:
            if (match.source.endswith("exact") and 
                "_" in match.source and 
                int(match.source.split("_")[2]) < len(buffer_states) and
                buffer_states[int(match.source.split("_")[2])][match.start:match.end] == "secret123"):
                complete_match = True
                print(f"  ✓ Found complete password match in buffer state {match.source.split('_')[2]}")
                
        self.assertTrue(complete_match, "Should find complete password match in buffer states")
        print("  ✓ All assertions passed")
    
    def test_merge_adjacent_matches(self):
        """
        TEST 7: Merge Adjacent Matches
        -----------------------------
        Tests merging of adjacent or nearly adjacent matches.
        This helps combine fragments of the same password.
        
        Expected outcomes:
        - Adjacent matches are merged into a single match
        - Non-adjacent matches remain separate
        """
        print("TEST 7: Merge Adjacent Matches")
        print("="*80)
        
        # Create a list of matches that are adjacent
        print("Test Case 1: Adjacent matches")
        matches = [
            Match(start=10, end=15, password="secret", similarity=0.9, source="fuzzy"),
            Match(start=16, end=19, password="secret", similarity=0.8, source="fuzzy")
        ]
        
        print("Original matches:")
        for i, match in enumerate(matches):
            print(f"  Match {i+1}: positions {match.start}-{match.end}, similarity {match.similarity}")
            
        print("Merging adjacent matches (max gap = 1)...")
        merged = FuzzyMatcher.merge_adjacent_matches(matches, max_gap=1)
        
        print("Merged matches:")
        for i, match in enumerate(merged):
            print(f"  Match {i+1}: positions {match.start}-{match.end}, similarity {match.similarity}")
        
        self.assertEqual(len(merged), 1, "Adjacent matches should be merged")
        
        if len(merged) > 0:
            self.assertEqual(merged[0].start, 10, "Merged match should start at first match's start")
            self.assertEqual(merged[0].end, 19, "Merged match should end at last match's end")
            print("  ✓ Adjacent matches successfully merged")
        
        # Test with non-adjacent matches
        print("\nTest Case 2: Non-adjacent matches")
        matches = [
            Match(start=10, end=15, password="secret", similarity=0.9, source="fuzzy"),
            Match(start=20, end=25, password="secret", similarity=0.8, source="fuzzy")
        ]
        
        print("Original matches:")
        for i, match in enumerate(matches):
            print(f"  Match {i+1}: positions {match.start}-{match.end}, similarity {match.similarity}")
            
        print("Attempting to merge non-adjacent matches (max gap = 1)...")
        merged = FuzzyMatcher.merge_adjacent_matches(matches, max_gap=1)
        
        print("Result after merge attempt:")
        for i, match in enumerate(merged):
            print(f"  Match {i+1}: positions {match.start}-{match.end}, similarity {match.similarity}")
        
        self.assertEqual(len(merged), 2, "Non-adjacent matches should not be merged")
        print("  ✓ Non-adjacent matches correctly remain separate")
        print("  ✓ All assertions passed")
    
    def test_convert_matches_to_locations(self):
        """
        TEST 8: Convert Matches to Locations
        -----------------------------------
        Tests conversion of Match objects to simple location tuples.
        This is used to simplify the match data structure for consumers.
        
        Expected outcome:
        - Each Match is converted to a (start, end) tuple
        - All matches are preserved in the conversion
        """
        print("TEST 8: Convert Matches to Locations")
        print("="*80)
        
        matches = [
            Match(start=10, end=15, password="secret", similarity=0.9, source="fuzzy"),
            Match(start=20, end=25, password="secret", similarity=0.8, source="fuzzy")
        ]
        
        print("Original matches:")
        for i, match in enumerate(matches):
            print(f"  Match {i+1}: positions {match.start}-{match.end}")
            print(f"    Password: '{match.password}', Similarity: {match.similarity}, Source: {match.source}")
            
        print("Converting to location tuples...")
        locations = FuzzyMatcher.convert_matches_to_locations(matches)
        
        print("Resulting locations:")
        for i, location in enumerate(locations):
            print(f"  Location {i+1}: positions {location[0]}-{location[1]}")
        
        self.assertEqual(len(locations), 2, "Should have the same number of locations as matches")
        self.assertEqual(locations[0], (10, 15), "First location should match first match")
        self.assertEqual(locations[1], (20, 25), "Second location should match second match")
        print("  ✓ All matches successfully converted to location tuples")
        print("  ✓ All assertions passed")


if __name__ == "__main__":
    print("\n" + "="*80)
    print("FUZZY MATCHER TEST SUITE")
    print("="*80)
    print("PLEASE USE THE run_tests.py SCRIPT TO RUN TESTS")
    print("Example: python run_tests.py fuzzy_matcher")
    print("="*80)
    sys.exit(1)