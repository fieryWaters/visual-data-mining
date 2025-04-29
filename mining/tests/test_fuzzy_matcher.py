#!/usr/bin/env python3
"""
FuzzyMatcher Test Suite
======================

Tests the simplified FuzzyMatcher utility used for password detection.
"""

import unittest
import sys
import os

# Add parent directory to path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.fuzzy_matcher import FuzzyMatcher, Match


class TestFuzzyMatcher(unittest.TestCase):
    """Tests for the simplified FuzzyMatcher utility"""
    
    def test_all_cases(self):
        """Test the core functionality of the fuzzy matcher"""
        print("\nRunning fuzzy matcher tests:")
        
        # Test 1: Similarity calculation
        print("\n--- 1. Similarity Calculation ---")
        self.assertEqual(FuzzyMatcher.calculate_similarity("secret123", "secret123"), 1.0)
        self.assertEqual(FuzzyMatcher.calculate_similarity("Secret123", "secret123"), 1.0)
        similarity = FuzzyMatcher.calculate_similarity("secret123", "secrett123")
        self.assertGreater(similarity, 0.8)
        print(f"✓ Similarity calculation works correctly (secret123/secrett123 = {similarity:.2f})")
        
        # Test 2: Basic match finding
        print("\n--- 2. Basic Match Finding ---")
        text = "The password is secret123"
        passwords = ["secret123"]
        
        matches = FuzzyMatcher.find_matches(text, passwords)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].start, 16)
        self.assertEqual(matches[0].end, 25)
        self.assertEqual(matches[0].source, "exact")
        print(f"✓ Found exact match at positions {matches[0].start}-{matches[0].end}")
        
        # Test 3: Multiple password finding
        print("\n--- 3. Finding Multiple Passwords ---")
        text = "First secret123 then secret456"
        passwords = ["secret123", "secret456"]
        
        matches = FuzzyMatcher.find_matches(text, passwords)
        self.assertEqual(len(matches), 2)
        found_passwords = {text[m.start:m.end] for m in matches}
        self.assertEqual(found_passwords, {"secret123", "secret456"})
        print(f"✓ Found both passwords: {found_passwords}")
        
        # Test 4: Fuzzy matching
        print("\n--- 4. Fuzzy Matching ---")
        text = "Used the password secrett1234 yesterday"
        passwords = ["secret123"]
        
        matches = FuzzyMatcher.find_matches(text, passwords)
        self.assertGreater(len(matches), 0)
        best_match = max(matches, key=lambda m: m.similarity)
        self.assertGreater(best_match.similarity, 0.75)
        print(f"✓ Fuzzy match found: '{text[best_match.start:best_match.end]}' with similarity {best_match.similarity:.2f}")
        
        # Test 5: Location conversion
        print("\n--- 5. Convert to Locations ---")
        matches = [
            Match(start=10, end=15, password="secret", similarity=0.9, source="fuzzy"),
            Match(start=20, end=30, password="secret", similarity=0.8, source="fuzzy")
        ]
        
        locations = FuzzyMatcher.convert_matches_to_locations(matches)
        self.assertEqual(locations, [(10, 15), (20, 30)])
        print(f"✓ Successfully converted to locations: {locations}")
        
        print("\nAll fuzzy matcher tests passed successfully!")


if __name__ == "__main__":
    print("Please use the run_tests.py script to run tests.")
    print("Example: python run_tests.py fuzzy_matcher")
    sys.exit(1)