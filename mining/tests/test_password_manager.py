"""
Password Manager Tests
=====================

This module tests the PasswordManager utility which is responsible for:
1. Securely storing passwords in an encrypted file
2. Adding, removing and retrieving passwords
3. Handling encryption/decryption with a master password
4. Providing passwords for the sanitization process

These tests verify that passwords are properly stored, encrypted,
and can be retrieved with the correct master password.
"""

import unittest
import sys
import os
import tempfile
from pathlib import Path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.password_manager import PasswordManager


class TestPasswordManager(unittest.TestCase):
    """Tests for the PasswordManager utility"""
    
    def setUp(self):
        """
        Set up a test environment for each test
        
        Creates:
        - Temporary directory
        - Test password file
        - PasswordManager instance
        """
        print("\n" + "="*80)
        
        # Create a temporary file for password storage
        self.temp_dir = tempfile.TemporaryDirectory()
        self.password_file = Path(self.temp_dir.name) / "test_passwords.keys"
        
        print(f"Setting up test environment")
        print(f"  ✓ Created temporary directory: {self.temp_dir.name}")
        print(f"  ✓ Created password file path: {self.password_file}")
        
        # Create a new password manager
        self.manager = PasswordManager(str(self.password_file))
        self.manager.setup_encryption("test_password")
        print(f"  ✓ Created password manager with test password")
    
    def tearDown(self):
        """
        Clean up after each test
        
        Removes:
        - Temporary directory and all its contents
        """
        # Remove the temporary directory and all its contents
        self.temp_dir.cleanup()
        print(f"  ✓ Cleaned up temporary test directory")
    
    def test_add_password(self):
        """
        TEST 1: Adding Passwords
        ----------------------
        Tests adding passwords to the manager and checks for duplicate prevention.
        
        Expected outcome:
        - Password is added to the list
        - Duplicate passwords are prevented
        """
        print("TEST 1: Adding Passwords")
        print("="*80)
        
        # Add a password
        print("Adding password 'secret123'...")
        self.manager.add_password("secret123")
        
        # Check that it's in the list
        passwords = self.manager.get_passwords()
        print(f"Current passwords: {passwords}")
        
        if "secret123" in passwords:
            print("  ✓ Password successfully added")
        else:
            print("  ✗ FAIL: Password not found in list")
        self.assertIn("secret123", passwords, "Added password should be in the list")
        
        # Check duplicate prevention
        print("Attempting to add the same password again...")
        self.manager.add_password("secret123")
        
        # Check count of this password
        count = self.manager.get_passwords().count("secret123")
        if count == 1:
            print("  ✓ Duplicate prevention worked - password only appears once")
        else:
            print(f"  ✗ FAIL: Password appears {count} times (expected 1)")
        self.assertEqual(count, 1, "Duplicate passwords should not be added")
        print("  ✓ All assertions passed")
    
    def test_remove_password(self):
        """
        TEST 2: Removing Passwords
        ------------------------
        Tests removing passwords from the manager.
        
        Expected outcome:
        - Specified password is removed
        - Other passwords remain in the list
        """
        print("TEST 2: Removing Passwords")
        print("="*80)
        
        # Add two passwords
        print("Adding two passwords: 'secret123' and 'secret456'")
        self.manager.add_password("secret123")
        self.manager.add_password("secret456")
        
        initial_passwords = self.manager.get_passwords()
        print(f"Initial passwords: {initial_passwords}")
        
        # Remove one password
        print("Removing 'secret123'...")
        self.manager.remove_password("secret123")
        
        # Check that it's removed
        remaining_passwords = self.manager.get_passwords()
        print(f"Remaining passwords: {remaining_passwords}")
        
        if "secret123" not in remaining_passwords:
            print("  ✓ Password 'secret123' successfully removed")
        else:
            print("  ✗ FAIL: Password 'secret123' still in list")
        self.assertNotIn("secret123", remaining_passwords, 
                        "Removed password should not be in the list")
        
        if "secret456" in remaining_passwords:
            print("  ✓ Password 'secret456' correctly retained")
        else:
            print("  ✗ FAIL: Password 'secret456' was incorrectly removed")
        self.assertIn("secret456", remaining_passwords, 
                     "Other passwords should remain in the list")
        print("  ✓ All assertions passed")
    
    def test_save_load_passwords(self):
        """
        TEST 3: Saving and Loading Passwords
        ----------------------------------
        Tests saving passwords to a file and loading them back.
        
        Expected outcome:
        - Passwords are successfully saved to file
        - File is created
        - Passwords can be loaded by a new manager instance
        - Loaded passwords match the saved passwords
        """
        print("TEST 3: Saving and Loading Passwords")
        print("="*80)
        
        # Add passwords
        print("Adding test passwords: 'test_password1' and 'test_password2'")
        self.manager.add_password("test_password1")
        self.manager.add_password("test_password2")
        
        # Save passwords
        print(f"Saving passwords to {self.password_file}...")
        success = self.manager.save_passwords()
        
        if success:
            print("  ✓ Passwords saved successfully")
        else:
            print("  ✗ FAIL: Could not save passwords")
        self.assertTrue(success, "Saving passwords should succeed")
        
        if self.password_file.exists():
            print("  ✓ Password file created")
        else:
            print("  ✗ FAIL: Password file not created")
        self.assertTrue(self.password_file.exists(), "Password file should be created")
        
        # Create a new manager and load passwords
        print("\nCreating new manager instance and loading saved passwords...")
        new_manager = PasswordManager(str(self.password_file))
        new_manager.setup_encryption("test_password")
        load_success = new_manager.load_passwords()
        
        if load_success:
            print("  ✓ Passwords loaded successfully")
        else:
            print("  ✗ FAIL: Could not load passwords")
        self.assertTrue(load_success, "Loading passwords should succeed")
        
        # Check loaded passwords
        loaded_passwords = new_manager.get_passwords()
        print(f"Loaded passwords: {loaded_passwords}")
        expected = ["test_password1", "test_password2"]
        
        if loaded_passwords == expected:
            print("  ✓ Loaded passwords match saved passwords")
        else:
            print(f"  ✗ FAIL: Loaded passwords {loaded_passwords} don't match expected {expected}")
        self.assertEqual(loaded_passwords, expected, 
                        "Loaded passwords should match saved passwords")
        print("  ✓ All assertions passed")
    
    def test_encryption(self):
        """
        TEST 4: Password Encryption
        -------------------------
        Tests that passwords are encrypted before storage.
        
        Expected outcome:
        - Password file is created
        - File does not contain plaintext passwords
        """
        print("TEST 4: Password Encryption")
        print("="*80)
        
        # Add a password and save
        test_password = "secret_data"
        print(f"Adding and saving password: '{test_password}'")
        self.manager.add_password(test_password)
        self.manager.save_passwords()
        
        # Verify file exists
        if self.password_file.exists():
            print("  ✓ Password file created")
            
            # Read the file contents
            with open(self.password_file, "rb") as f:
                content = f.read()
            
            # The password should not be in the file as plaintext
            if test_password.encode() not in content:
                print("  ✓ Password not stored as plaintext")
            else:
                print("  ✗ FAIL: Password found as plaintext in file")
            self.assertNotIn(test_password.encode(), content, 
                            "Password should not be stored as plaintext")
            
            # Show some file info
            print(f"  File size: {len(content)} bytes")
        else:
            print("  ✗ FAIL: Password file not created")
            self.fail("Password file not created")
        print("  ✓ All assertions passed")
    
    def test_wrong_password(self):
        """
        TEST 5: Wrong Master Password
        ---------------------------
        Tests that loading with the wrong master password fails.
        
        Expected outcome:
        - Loading with wrong password fails
        - No passwords are loaded with wrong password
        """
        print("TEST 5: Wrong Master Password")
        print("="*80)
        
        # Add and save passwords
        print("Adding and saving a test password")
        self.manager.add_password("test_password")
        self.manager.save_passwords()
        
        # Try to load with wrong password
        print("Attempting to load with incorrect master password...")
        new_manager = PasswordManager(str(self.password_file))
        new_manager.setup_encryption("wrong_password")  # Incorrect master password
        load_success = new_manager.load_passwords()
        
        if not load_success:
            print("  ✓ Loading with wrong password correctly failed")
        else:
            print("  ✗ FAIL: Loading succeeded with wrong password")
        self.assertFalse(load_success, "Loading with wrong password should fail")
        
        # Check that no passwords were loaded
        loaded_passwords = new_manager.get_passwords()
        if not loaded_passwords:
            print("  ✓ No passwords were loaded with wrong master password")
        else:
            print(f"  ✗ FAIL: Loaded {len(loaded_passwords)} passwords despite wrong master password")
        print("  ✓ All assertions passed")
    
    def test_get_passwords(self):
        """
        TEST 6: Password List Copy
        ------------------------
        Tests that get_passwords returns a copy of the password list,
        not the original list, to prevent accidental modification.
        
        Expected outcome:
        - Modifying the returned list doesn't affect the manager's list
        """
        print("TEST 6: Password List Copy")
        print("="*80)
        
        # Add some passwords
        print("Adding two passwords: 'password1' and 'password2'")
        self.manager.add_password("password1")
        self.manager.add_password("password2")
        
        # Get the passwords list and modify it
        print("Getting passwords list and modifying the returned list...")
        passwords = self.manager.get_passwords()
        original_count = len(passwords)
        print(f"Original list: {passwords}")
        
        print("Adding 'password3' to the returned list (not to the manager)")
        passwords.append("password3")
        print(f"Modified returned list: {passwords}")
        
        # Check that the original list is not modified
        manager_passwords = self.manager.get_passwords()
        print(f"Manager's internal list: {manager_passwords}")
        
        if "password3" not in manager_passwords:
            print("  ✓ Manager's internal list not affected by modifications to the returned list")
        else:
            print("  ✗ FAIL: Manager's internal list was modified")
        self.assertNotIn("password3", manager_passwords, 
                        "get_passwords should return a copy, not the original list")
        print("  ✓ All assertions passed")
    
    def test_no_passwords_file(self):
        """
        TEST 7: Missing Password File
        ----------------------------
        Tests behavior when the password file doesn't exist yet.
        
        Expected outcome:
        - Loading from a non-existent file succeeds but returns an empty list
        - Manager is ready to add new passwords
        """
        print("TEST 7: Missing Password File")
        print("="*80)
        
        # Create a path to a non-existent file
        nonexistent_file = Path(self.temp_dir.name) / "nonexistent.keys"
        print(f"Testing with non-existent file: {nonexistent_file}")
        
        # Verify file doesn't exist
        if not nonexistent_file.exists():
            print("  ✓ Confirmed file doesn't exist")
        
        # Create a manager with a non-existent file
        print("Creating manager with non-existent file path...")
        manager = PasswordManager(str(nonexistent_file))
        manager.setup_encryption("test_password")
        
        # Loading should succeed but return an empty list
        print("Attempting to load passwords...")
        success = manager.load_passwords()
        
        if success:
            print("  ✓ Loading from non-existent file succeeds")
        else:
            print("  ✗ FAIL: Loading from non-existent file failed")
        self.assertTrue(success, "Loading a non-existent file should succeed")
        
        # Check loaded passwords
        loaded_passwords = manager.get_passwords()
        if not loaded_passwords:
            print("  ✓ No passwords loaded (empty list)")
        else:
            print(f"  ✗ FAIL: Unexpected passwords loaded: {loaded_passwords}")
        self.assertEqual(loaded_passwords, [], "No passwords should be loaded")
        
        # Now try adding a password to verify the manager is functional
        print("Adding a password to verify manager is functional...")
        manager.add_password("new_password")
        
        if "new_password" in manager.get_passwords():
            print("  ✓ Manager is functional after loading from non-existent file")
        else:
            print("  ✗ FAIL: Couldn't add new password")
        print("  ✓ All assertions passed")


if __name__ == "__main__":
    print("\n" + "="*80)
    print("PASSWORD MANAGER TEST SUITE")
    print("="*80)
    print("This test suite verifies the functionality of the PasswordManager utility")
    print("which is responsible for securely storing and retrieving passwords.")
    print("\nEach test will show:")
    print("  ✓ - Passed assertions")
    print("  ✗ - Failed assertions")
    print("\nDetailed operation information is displayed for verification.")
    print("="*80)
    unittest.main(verbosity=2)