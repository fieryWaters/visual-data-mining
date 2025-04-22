"""
Password Manager Tests - Tests the PasswordManager utility for secure password storage.
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
        """Set up test environment with temporary files and manager instance"""
        # Create a temporary file for password storage
        self.temp_dir = tempfile.TemporaryDirectory()
        self.password_file = Path(self.temp_dir.name) / "test_passwords.keys"
        
        # Create a new password manager
        self.manager = PasswordManager(str(self.password_file))
        self.manager.setup_encryption("test_password")
    
    def tearDown(self):
        """Clean up temporary files"""
        self.temp_dir.cleanup()
    
    def test_add_password(self):
        """Test adding passwords and duplicate prevention"""
        # Add a password
        self.manager.add_password("test_password_1")
        passwords = self.manager.get_passwords()
        self.assertIn("test_password_1", passwords, "Added password should be in the list")
        
        # Test duplicate prevention
        self.manager.add_password("test_password_1")
        count = self.manager.get_passwords().count("test_password_1")
        self.assertEqual(count, 1, "Duplicate passwords should not be added")
    
    def test_remove_password(self):
        """Test removing a password while keeping others"""
        # Add two passwords
        self.manager.add_password("test_password_1")
        self.manager.add_password("test_password_2")
        
        # Remove one password
        self.manager.remove_password("test_password_1")
        remaining_passwords = self.manager.get_passwords()
        
        self.assertNotIn("test_password_1", remaining_passwords, 
                        "Removed password should not be in the list")
        self.assertIn("test_password_2", remaining_passwords, 
                     "Other passwords should remain in the list")
    
    def test_save_load_passwords(self):
        """Test saving and loading passwords from file"""
        # Add and save passwords
        self.manager.add_password("test_password1")
        self.manager.add_password("test_password2")
        success = self.manager.save_passwords()
        
        self.assertTrue(success, "Saving passwords should succeed")
        self.assertTrue(self.password_file.exists(), "Password file should be created")
        
        # Create a new manager and load passwords
        new_manager = PasswordManager(str(self.password_file))
        new_manager.setup_encryption("test_password")
        load_success = new_manager.load_passwords()
        
        self.assertTrue(load_success, "Loading passwords should succeed")
        
        # Check loaded passwords
        loaded_passwords = new_manager.get_passwords()
        expected = ["test_password1", "test_password2"]
        self.assertEqual(loaded_passwords, expected, 
                        "Loaded passwords should match saved passwords")
    
    def test_encryption(self):
        """Test that passwords are actually encrypted"""
        # Add a password and save
        test_password = "secret_data"
        self.manager.add_password(test_password)
        self.manager.save_passwords()
        
        # Verify password isn't stored as plaintext
        with open(self.password_file, "rb") as f:
            content = f.read()
        
        self.assertNotIn(test_password.encode(), content, 
                        "Password should not be stored as plaintext")
    
    def test_wrong_password(self):
        """Test that loading with wrong master password fails"""
        # Add and save a password
        self.manager.add_password("test_password")
        self.manager.save_passwords()
        
        # Try to load with wrong password
        new_manager = PasswordManager(str(self.password_file))
        new_manager.setup_encryption("wrong_password")  # Incorrect password
        load_success = new_manager.load_passwords()
        
        self.assertFalse(load_success, "Loading with wrong password should fail")
        self.assertEqual(new_manager.get_passwords(), [], 
                         "No passwords should be loaded with wrong master password")
    
    def test_get_passwords(self):
        """Test that get_passwords returns a copy of the list"""
        # Add passwords
        self.manager.add_password("password1")
        self.manager.add_password("password2")
        
        # Get and modify the returned list
        passwords = self.manager.get_passwords()
        passwords.append("password3")
        
        # Check that the original list is not modified
        manager_passwords = self.manager.get_passwords()
        self.assertNotIn("password3", manager_passwords, 
                        "get_passwords should return a copy, not the original list")
    
    def test_no_passwords_file(self):
        """Test behavior with non-existent password file"""
        # Create a path to a non-existent file
        nonexistent_file = Path(self.temp_dir.name) / "nonexistent.keys"
        
        # Create a manager with a non-existent file
        manager = PasswordManager(str(nonexistent_file))
        manager.setup_encryption("test_password")
        
        # Loading should succeed but return an empty list
        success = manager.load_passwords()
        self.assertTrue(success, "Loading a non-existent file should succeed")
        self.assertEqual(manager.get_passwords(), [], "No passwords should be loaded")
        
        # Verify manager is still functional
        manager.add_password("new_password")
        self.assertIn("new_password", manager.get_passwords(),
                     "Manager should be functional after loading non-existent file")


if __name__ == "__main__":
    unittest.main(verbosity=2)