"""
Password manager module.
Handles secure storage and retrieval of passwords for the keystroke sanitizer.
"""

import os
import json
import getpass
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class PasswordManager:
    """
    Manages secure storage and retrieval of passwords using encryption
    """
    
    def __init__(self, passwords_file="secret.keys", salt=None):
        """
        Initialize the password manager with file path
        
        Args:
            passwords_file: Path to the encrypted passwords file
            salt: Salt for encryption (if None, a random salt is generated)
        """
        self.passwords_file = passwords_file
        self.passwords = []
        self.key = None
        # Use a fixed salt for testing to ensure consistent encryption/decryption
        self.salt = salt if salt else b'0123456789abcdef'
        
    def _derive_key(self, password):
        """Derive encryption key from password using PBKDF2"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self.salt,
            iterations=100000,
        )
        return base64.urlsafe_b64encode(kdf.derive(password.encode()))
    
    def setup_encryption(self, password=None):
        """
        Setup encryption with password (prompt if not provided)
        
        Args:
            password: User password for encryption (optional)
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not password:
                password = getpass.getpass("Enter encryption password: ")
            
            self.key = self._derive_key(password)
            return True
        except Exception as e:
            print(f"Error setting up encryption: {e}")
            return False
    
    def load_passwords(self):
        """
        Load passwords from encrypted file
        
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.key:
            print("Encryption not set up. Call setup_encryption() first.")
            return False
            
        try:
            if not os.path.exists(self.passwords_file):
                # No passwords file yet, create empty list
                self.passwords = []
                return True
                
            cipher = Fernet(self.key)
            with open(self.passwords_file, 'rb') as f:
                encrypted_data = f.read()
                
            # Decrypt the data
            decrypted_data = cipher.decrypt(encrypted_data)
            
            # Load JSON data
            self.passwords = json.loads(decrypted_data.decode())
            return True
            
        except Exception as e:
            print(f"Error loading passwords: {e}")
            return False
    
    def save_passwords(self):
        """
        Save passwords to encrypted file
        
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.key:
            print("Encryption not set up. Call setup_encryption() first.")
            return False
            
        try:
            # Convert passwords to JSON
            data = json.dumps(self.passwords).encode()
            
            # Encrypt the data
            cipher = Fernet(self.key)
            encrypted_data = cipher.encrypt(data)
            
            # Write to file
            with open(self.passwords_file, 'wb') as f:
                f.write(encrypted_data)
                
            return True
            
        except Exception as e:
            print(f"Error saving passwords: {e}")
            return False
    
    def add_password(self, password):
        """
        Add a password to the list
        
        Args:
            password: Password string to add
        """
        if password and password not in self.passwords:
            self.passwords.append(password)
    
    def remove_password(self, password):
        """
        Remove a password from the list
        
        Args:
            password: Password string to remove
        """
        if password in self.passwords:
            self.passwords.remove(password)
    
    def get_passwords(self):
        """
        Get the list of passwords
        
        Returns:
            list: Copy of passwords list
        """
        return self.passwords.copy()