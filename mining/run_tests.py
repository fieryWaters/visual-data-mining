#!/usr/bin/env python3
"""
Keystroke Sanitizer Test Suite Runner
====================================

The official test runner for the keystroke sanitizer and related utilities.
This is the PREFERRED way to run all tests in this project.

Usage:
    python run_tests.py [module_name]
    
    - If no module_name is provided, runs all tests
    - If module_name is provided, runs only that test module
    
Available modules:
    - sanitizer     - Tests for the KeystrokeSanitizer (refactored version)
    - fuzzy_matcher - Tests for the FuzzyMatcher utility
    - keepass_manager - Tests for the KeePassManager utility
    - text_buffer   - Tests for the TextBuffer utility
    - all           - Runs all tests (default)

Note: Do NOT use unittest commands directly - always use this script
for consistent test execution and reporting.
"""

import sys
import unittest
import os
from pathlib import Path

def run_all_tests():
    """Run all test modules and display a summary"""
    print("\n" + "="*80)
    print("RUNNING ALL KEYSTROKE SANITIZER TESTS")
    print("="*80)
    
    # Define the core test files we want to run
    core_test_files = [
        'test_keystroke_sanitizer.py',
        'test_fuzzy_matcher.py',
        'test_keepass_manager.py',
        'test_text_buffer.py'
    ]
    
    # Run tests
    return run_unittest_tests(core_test_files)

def run_unittest_tests(test_files):
    """Run unittest-based test modules"""
    print("\n" + "="*80)
    print("RUNNING UNITTEST TESTS")
    print("="*80)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    test_dir = Path(__file__).parent / 'tests'
    
    # Add test modules to the suite
    for test_file in test_files:
        module_name = test_file[:-3]  # Remove .py extension
        test_path = test_dir / test_file
        
        if not test_path.exists():
            print(f"Warning: Test file {test_path} does not exist, skipping")
            continue
            
        print(f"Loading tests from: {module_name}")
        
        # Import the module and add its tests to the suite
        sys.path.insert(0, str(test_dir))
        try:
            module = __import__(module_name)
            suite.addTest(loader.loadTestsFromModule(module))
        except ImportError as e:
            print(f"Error importing {module_name}: {e}")
        finally:
            sys.path.pop(0)
    
    # Run the tests
    print("\n" + "="*80)
    print("TEST RESULTS")
    print("="*80)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"Ran {result.testsRun} tests")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if not result.failures and not result.errors:
        print("\n✅ ALL TESTS PASSED")
        return True
    else:
        print("\n❌ SOME TESTS FAILED")
        return False

def run_specific_module(module_name, test_number=None):
    """Run tests for a specific module, optionally a specific test number"""
    print("\n" + "="*80)
    print(f"RUNNING TESTS FOR: {module_name}" + (f" TEST #{test_number}" if test_number else ""))
    print("="*80)
    
    # Map module names to test file names
    module_map = {
        'sanitizer': 'test_keystroke_sanitizer.py',
        'fuzzy_matcher': 'test_fuzzy_matcher.py',
        'keepass_manager': 'test_keepass_manager.py',
        'text_buffer': 'test_text_buffer.py'
    }
    
    if module_name not in module_map:
        print(f"Error: Unknown module '{module_name}'")
        print(f"Available modules: {', '.join(module_map.keys())}")
        return False
    
    # For sanitizer with test number, run just that specific test
    if module_name == 'sanitizer' and test_number:
        try:
            # Just run the specified test directly
            import unittest
            from tests.test_keystroke_sanitizer import TestKeystrokeSanitizer
            
            # Create and configure test instance
            test_case = TestKeystrokeSanitizer('test_all_cases')
            test_case.setUp()
            
            # Run the specific test
            test_case.test_all_cases(test_number)
            
            # Clean up
            test_case.tearDown()
            return True
        except Exception as e:
            print(f"Error running test: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    # Run the unittest for that module
    return run_unittest_tests([module_map[module_name]])

def print_help():
    """Print usage information"""
    print("\nKeystroke Sanitizer Test Runner")
    print("==============================")
    print("Usage:")
    print("  python run_tests.py [module_name] [test_number]")
    print("")
    print("Available modules:")
    print("  sanitizer        - Tests for the KeystrokeSanitizer (refactored version)")
    print("  fuzzy_matcher    - Tests for the FuzzyMatcher utility")
    print("  password_manager - Tests for the PasswordManager utility")
    print("  text_buffer      - Tests for the TextBuffer utility")
    print("  all              - Runs all tests (default)")
    print("")
    print("Examples:")
    print("  python run_tests.py sanitizer     - Run all sanitizer tests")
    print("  python run_tests.py sanitizer 10  - Run just test case #10 (Whitespace Handling)")
    print("")

if __name__ == "__main__":
    # Check if the user wants to run a specific module
    if len(sys.argv) > 1:
        module_name = sys.argv[1].lower()
        
        # Check for test number (optional)
        test_number = None
        if len(sys.argv) > 2:
            test_number = sys.argv[2]
        
        if module_name in ('-h', '--help', 'help'):
            print_help()
            sys.exit(0)
        elif module_name == 'all':
            success = run_all_tests()
        else:
            success = run_specific_module(module_name, test_number)
    else:
        # Default: run all tests
        success = run_all_tests()
    
    # Set exit code based on test results
    sys.exit(0 if success else 1)