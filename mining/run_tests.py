#!/usr/bin/env python3
"""
Keystroke Sanitizer Test Suite Runner
=====================================

This script runs all the tests for the keystroke sanitizer module and its components.
It provides a unified way to run all tests or specific test modules.

Usage:
    python run_tests.py [module_name]
    
    - If no module_name is provided, runs all tests
    - If module_name is provided, runs only that test module
    
Available modules:
    - sanitizer (tests for the main KeystrokeSanitizer class)
    - fuzzy_matcher (tests for the FuzzyMatcher utility)
    - password_manager (tests for the PasswordManager utility)
    - text_buffer (tests for the TextBuffer utility)
    - edge_cases (edge case tests for the sanitizer)
    - manual (manual test script with visual output)
    - all (runs all tests)
"""

import sys
import unittest
import os
import importlib.util
from pathlib import Path

def run_all_tests():
    """Run all test modules and display a summary"""
    print("\n" + "="*80)
    print("RUNNING ALL KEYSTROKE SANITIZER TESTS")
    print("="*80)
    
    # Get all test modules
    test_dir = Path(__file__).parent / 'tests'
    test_files = [f for f in os.listdir(test_dir) if f.startswith('test_') and f.endswith('.py')]
    unittest_files = []
    special_test_files = []
    
    # Separate unittest files from special test scripts
    for test_file in test_files:
        if test_file in ['test_sanitizer.py', 'test_edge_cases.py']:
            special_test_files.append(test_file)
        else:
            unittest_files.append(test_file)
    
    # First run unittest-based tests
    success = run_unittest_tests(unittest_files)
    
    # Then run special test scripts
    special_success = run_special_tests(special_test_files)
    
    return success and special_success

def run_unittest_tests(test_files):
    """Run unittest-based test modules"""
    print("\n" + "="*80)
    print("RUNNING UNITTEST-BASED TESTS")
    print("="*80)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    test_dir = Path(__file__).parent / 'tests'
    
    # Add test modules to the suite
    for test_file in test_files:
        module_name = test_file[:-3]  # Remove .py extension
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
    print("UNITTEST RESULTS")
    print("="*80)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "="*80)
    print("UNITTEST SUMMARY")
    print("="*80)
    print(f"Ran {result.testsRun} tests")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if not result.failures and not result.errors:
        print("\n✅ ALL UNITTEST TESTS PASSED")
        return True
    else:
        print("\n❌ SOME UNITTEST TESTS FAILED")
        return False

def run_special_tests(test_files):
    """Run special test scripts that don't use unittest"""
    print("\n" + "="*80)
    print("RUNNING SPECIAL TEST SCRIPTS")
    print("="*80)
    
    test_dir = Path(__file__).parent / 'tests'
    all_passed = True
    
    for test_file in test_files:
        print(f"\nRunning special test: {test_file}")
        
        # Import and run the module
        module_path = test_dir / test_file
        module_name = test_file[:-3]  # Remove .py extension
        
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Run the appropriate test function
        if hasattr(module, 'test_sanitizer'):
            try:
                result = module.test_sanitizer()
                if not result:
                    all_passed = False
            except Exception as e:
                print(f"Error running {test_file}: {e}")
                all_passed = False
        elif hasattr(module, 'run_edge_case_tests'):
            try:
                passed, total = module.run_edge_case_tests()
                if passed < total:
                    all_passed = False
            except Exception as e:
                print(f"Error running {test_file}: {e}")
                all_passed = False
        else:
            print(f"Warning: No test function found in {test_file}")
    
    # Print summary
    print("\n" + "="*80)
    print("SPECIAL TESTS SUMMARY")
    print("="*80)
    
    if all_passed:
        print("\n✅ ALL SPECIAL TESTS PASSED")
    else:
        print("\n❌ SOME SPECIAL TESTS FAILED")
    
    return all_passed

def run_specific_module(module_name):
    """Run tests for a specific module"""
    print("\n" + "="*80)
    print(f"RUNNING TESTS FOR: {module_name}")
    print("="*80)
    
    # Map module names to test file names
    module_map = {
        'sanitizer': 'test_keystroke_sanitizer.py',
        'fuzzy_matcher': 'test_fuzzy_matcher.py',
        'password_manager': 'test_password_manager.py',
        'text_buffer': 'test_text_buffer.py',
        'edge_cases': 'test_edge_cases.py',
        'manual': 'test_sanitizer.py'
    }
    
    if module_name not in module_map:
        print(f"Error: Unknown module '{module_name}'")
        print(f"Available modules: {', '.join(module_map.keys())}")
        return False
    
    # Get the test file for the module
    test_file = module_map[module_name]
    test_path = Path(__file__).parent / 'tests' / test_file
    
    if not test_path.exists():
        print(f"Error: Test file {test_path} does not exist")
        return False
    
    # Special handling for non-unittest modules
    if module_name in ['edge_cases', 'manual']:
        return run_special_tests([test_file])
    
    # For unittest modules
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Import the module and add its tests to the suite
    sys.path.insert(0, str(test_path.parent))
    try:
        module_name_no_ext = test_file[:-3]  # Remove .py extension
        module = __import__(module_name_no_ext)
        suite.addTest(loader.loadTestsFromModule(module))
    except ImportError as e:
        print(f"Error importing {module_name_no_ext}: {e}")
        sys.path.pop(0)
        return False
    finally:
        sys.path.pop(0)
    
    # Run the tests
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
        print("\n❌ TESTS FAILED")
        return False

def print_help():
    """Print usage information"""
    print("\nKeystroke Sanitizer Test Runner")
    print("==============================")
    print("Usage:")
    print("  python run_tests.py [module_name]")
    print("")
    print("Available modules:")
    print("  sanitizer        - Tests for the main KeystrokeSanitizer class")
    print("  fuzzy_matcher    - Tests for the FuzzyMatcher utility")
    print("  password_manager - Tests for the PasswordManager utility")
    print("  text_buffer      - Tests for the TextBuffer utility")
    print("  edge_cases       - Edge case tests for the sanitizer")
    print("  manual           - Manual test script with visual output")
    print("  all              - Runs all tests (default)")
    print("")

if __name__ == "__main__":
    # Check if the user wants to run a specific module
    if len(sys.argv) > 1:
        module_name = sys.argv[1].lower()
        
        if module_name in ('-h', '--help', 'help'):
            print_help()
            sys.exit(0)
        elif module_name == 'all':
            success = run_all_tests()
        else:
            success = run_specific_module(module_name)
    else:
        # Default: run all tests
        success = run_all_tests()
    
    # Set exit code based on test results
    sys.exit(0 if success else 1)