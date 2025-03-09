"""
Tests for the PasswordManager utility class
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
        """Set up a test environment for each test"""
        # Create a temporary file for password storage
        self.temp_dir = tempfile.TemporaryDirectory()
        self.password_file = Path(self.temp_dir.name) / "test_passwords.keys"
        
        # Create a new password manager
        self.manager = PasswordManager(str(self.password_file))
        self.manager.setup_encryption("test_password")
    
    def tearDown(self):
        """Clean up after each test"""
        # Remove the temporary directory and all its contents
        self.temp_dir.cleanup()
    
    def test_add_password(self):
        """Test adding passwords"""
        # Add a password
        self.manager.add_password("secret123")
        
        # Check that it's in the list
        self.assertIn("secret123", self.manager.get_passwords(), 
                     "Added password should be in the list")
        
        # Check duplicate prevention
        self.manager.add_password("secret123")
        self.assertEqual(self.manager.get_passwords().count("secret123"), 1, 
                        "Duplicate passwords should not be added")
    
    def test_remove_password(self):
        """Test removing passwords"""
        # Add and then remove a password
        self.manager.add_password("secret123")
        self.manager.add_password("secret456")
        
        self.manager.remove_password("secret123")
        
        # Check that it's removed
        self.assertNotIn("secret123", self.manager.get_passwords(), 
                        "Removed password should not be in the list")
        self.assertIn("secret456", self.manager.get_passwords(), 
                     "Other passwords should remain in the list")
    
    def test_save_load_passwords(self):
        """Test saving and loading passwords"""
        # Add passwords
        self.manager.add_password("test_password1")
        self.manager.add_password("test_password2")
        
        # Save passwords
        success = self.manager.save_passwords()
        self.assertTrue(success, "Saving passwords should succeed")
        self.assertTrue(self.password_file.exists(), "Password file should be created")
        
        # Create a new manager and load passwords
        new_manager = PasswordManager(str(self.password_file))
        new_manager.setup_encryption("test_password")
        success = new_manager.load_passwords()
        
        self.assertTrue(success, "Loading passwords should succeed")
        self.assertEqual(new_manager.get_passwords(), ["test_password1", "test_password2"], 
                        "Loaded passwords should match saved passwords")
    
    def test_encryption(self):
        """Test that passwords are actually encrypted"""
        # Add a password and save
        self.manager.add_password("secret_data")
        self.manager.save_passwords()
        
        # Read the file contents
        with open(self.password_file, "rb") as f:
            content = f.read()
        
        # The password should not be in the file as plaintext
        self.assertNotIn(b"secret_data", content, 
                        "Password should not be stored as plaintext")
    
    def test_wrong_password(self):
        """Test attempting to load with wrong password"""
        # Add and save passwords
        self.manager.add_password("test_password")
        self.manager.save_passwords()
        
        # Try to load with wrong password
        new_manager = PasswordManager(str(self.password_file))
        new_manager.setup_encryption("wrong_password")
        success = new_manager.load_passwords()
        
        self.assertFalse(success, "Loading with wrong password should fail")
    
    def test_get_passwords(self):
        """Test get_passwords returns a copy, not the original list"""
        # Add some passwords
        self.manager.add_password("password1")
        self.manager.add_password("password2")
        
        # Get the passwords list and modify it
        passwords = self.manager.get_passwords()
        passwords.append("password3")
        
        # Check that the original list is not modified
        self.assertNotIn("password3", self.manager.get_passwords(), 
                        "get_passwords should return a copy, not the original list")
    
    def test_no_passwords_file(self):
        """Test loading when no passwords file exists"""
        # Create a manager with a non-existent file
        manager = PasswordManager(str(Path(self.temp_dir.name) / "nonexistent.keys"))
        manager.setup_encryption("test_password")
        
        # Loading should succeed but return an empty list
        success = manager.load_passwords()
        self.assertTrue(success, "Loading a non-existent file should succeed")
        self.assertEqual(manager.get_passwords(), [], "No passwords should be loaded")


if __name__ == "__main__":
    unittest.main()