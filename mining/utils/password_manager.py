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
    """Manages secure storage and retrieval of passwords"""
    
    def __init__(self, passwords_file="secret.keys", salt=None):
        """Initialize with password file path and optional salt"""
        self.passwords_file = passwords_file
        self.passwords = []
        self.key = None
        self.salt = salt if salt else b'0123456789abcdef'
        
    def _derive_key(self, password):
        """Derive encryption key from password"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self.salt,
            iterations=100000,
        )
        return base64.urlsafe_b64encode(kdf.derive(password.encode()))
    
    def _handle_error(self, operation, error):
        """Centralized error handling"""
        print(f"Error during {operation}: {error}")
        return False
    
    def setup_encryption(self, password=None):
        """Setup encryption with password"""
        try:
            if not password:
                password = getpass.getpass("Enter encryption password: ")
            
            self.key = self._derive_key(password)
            return True
        except Exception as e:
            return self._handle_error("encryption setup", e)
    
    def load_passwords(self):
        """Load passwords from encrypted file"""
        if not self.key:
            print("Encryption not set up. Call setup_encryption() first.")
            return False
            
        try:
            if not os.path.exists(self.passwords_file):
                self.passwords = []
                return True
                
            with open(self.passwords_file, 'rb') as f:
                encrypted_data = f.read()
                
            cipher = Fernet(self.key)
            decrypted_data = cipher.decrypt(encrypted_data)
            
            self.passwords = json.loads(decrypted_data.decode())
            return True
            
        except Exception as e:
            return self._handle_error("password loading", e)
    
    def save_passwords(self):
        """Save passwords to encrypted file"""
        if not self.key:
            print("Encryption not set up. Call setup_encryption() first.")
            return False
            
        try:
            data = json.dumps(self.passwords).encode()
            
            cipher = Fernet(self.key)
            encrypted_data = cipher.encrypt(data)
            
            with open(self.passwords_file, 'wb') as f:
                f.write(encrypted_data)
                
            return True
            
        except Exception as e:
            return self._handle_error("password saving", e)
    
    def add_password(self, password):
        """Add a password to the list"""
        if password and password not in self.passwords:
            self.passwords.append(password)
    
    def remove_password(self, password):
        """Remove a password from the list"""
        if password in self.passwords:
            self.passwords.remove(password)
    
    def get_passwords(self):
        """Get a copy of the password list"""
        return self.passwords.copy()