"""
KeePass password manager module.
Handles secure storage and retrieval of passwords for the keystroke sanitizer
using the PyKeePass library.
"""

import os
from typing import List, Optional, Tuple
from pykeepass import PyKeePass, create_database
from pykeepass.exceptions import CredentialsError


class KeePassManager:
    """Manages secure storage and retrieval of passwords using KeePass"""
    
    def __init__(self, passwords_file="passwords.kdbx"):
        """Initialize with password file path"""
        self.passwords_file = passwords_file
        self.kp = None
        self.passwords = []
        
    def setup_encryption(self, password=None, keyfile=None) -> bool:
        """Set up encryption with the provided password"""
        try:
            if not password:
                raise ValueError("Password is required")
                
            if os.path.exists(self.passwords_file):
                # Open existing database
                self.kp = PyKeePass(self.passwords_file, password=password, keyfile=keyfile)
            else:
                # Create new database
                self.kp = create_database(self.passwords_file, password=password, keyfile=keyfile)
                self.kp.save()
                
            return True
        except Exception as e:
            print(f"Error setting up encryption: {e}")
            return False
    
    def load_passwords(self) -> bool:
        """Load passwords from KeePass database"""
        try:
            if not self.kp:
                print("Encryption not set up. Call setup_encryption() first.")
                return False
                
            self.passwords = self._extract_passwords()
            return True
        except Exception as e:
            print(f"Error loading passwords: {e}")
            return False
    
    def save_passwords(self) -> bool:
        """Save passwords to KeePass database"""
        try:
            if not self.kp:
                print("Encryption not set up. Call setup_encryption() first.")
                return False
                
            self.kp.save()
            return True
        except Exception as e:
            print(f"Error saving passwords: {e}")
            return False
    
    def add_password(self, password: str, title: str = None, username: str = None) -> bool:
        """
        Add a password to the KeePass database
        
        Args:
            password: The password to add
            title: Optional title for the entry (defaults to "Password Entry")
            username: Optional username for the entry
        
        Returns:
            bool: Success or failure
        """
        if not self.kp:
            print("Encryption not set up. Call setup_encryption() first.")
            return False
            
        try:
            # Skip if password already exists
            if password in self._extract_passwords():
                return True
                
            # Generate a title if not provided
            if not title:
                existing_entries = len(self.kp.entries)
                title = f"Password Entry {existing_entries + 1}"
                
            # Add the entry to the root group
            root_group = self.kp.root_group
            self.kp.add_entry(root_group, title, username or "", password)
            
            # Save the database
            self.kp.save()
            
            # Update the passwords list
            self.passwords = self._extract_passwords()
            return True
        except Exception as e:
            print(f"Error adding password: {e}")
            return False
    
    def remove_password(self, password: str) -> bool:
        """Remove a password from the KeePass database"""
        if not self.kp:
            print("Encryption not set up. Call setup_encryption() first.")
            return False
            
        try:
            # Find entries with this password
            entries_to_remove = []
            for entry in self.kp.entries:
                if entry.password == password:
                    entries_to_remove.append(entry)
            
            if not entries_to_remove:
                return False
                
            # Remove the entries
            for entry in entries_to_remove:
                self.kp.delete_entry(entry)
                
            # Save the database
            self.kp.save()
            
            # Update the passwords list
            self.passwords = self._extract_passwords()
            return True
        except Exception as e:
            print(f"Error removing password: {e}")
            return False
    
    def get_passwords(self) -> List[str]:
        """Get a copy of the password list"""
        if not self.kp:
            return []
            
        # Refresh the passwords list
        self.passwords = self._extract_passwords()
        return self.passwords.copy()
    
    def _extract_passwords(self) -> List[str]:
        """Extract passwords from the KeePass database"""
        if not self.kp:
            return []
            
        try:
            return [entry.password for entry in self.kp.entries]
        except Exception as e:
            print(f"Error extracting passwords: {e}")
            return []
    
    def check_credentials(self, password: str, keyfile: Optional[str] = None) -> bool:
        """Check if the provided credentials can open the database"""
        if not os.path.exists(self.passwords_file):
            return False
            
        try:
            # Try to open the database
            PyKeePass(self.passwords_file, password=password, keyfile=keyfile)
            return True
        except CredentialsError:
            return False
        except Exception:
            return False
    
    def search_password(self, password_fragment: str) -> List[str]:
        """Search for passwords containing the given fragment"""
        if not self.kp:
            return []
            
        try:
            return [entry.password for entry in self.kp.entries 
                   if password_fragment.lower() in entry.password.lower()]
        except Exception as e:
            print(f"Error searching passwords: {e}")
            return []


if __name__ == "__main__":
    # Simple test
    import getpass
    
    manager = KeePassManager()
    
    if os.path.exists(manager.passwords_file):
        password = getpass.getpass("Enter your master password: ")
    else:
        password = getpass.getpass("Create a master password: ")
        
    if manager.setup_encryption(password):
        print("Encryption set up successfully")
        
        # Load or create passwords
        if not os.path.exists(manager.passwords_file) or not manager.load_passwords():
            print("Adding sample passwords")
            manager.add_password("samplePassword1", "Email", "user@example.com")
            manager.add_password("samplePassword2", "Banking", "user123")
            
        # Count passwords
        passwords = manager.get_passwords()
        print(f"Number of stored passwords: {len(passwords)}")
        
        # Test search
        search_term = "secret"
        found = manager.search_password(search_term)
        print(f"Found {len(found)} passwords containing '{search_term}'")
    else:
        print("Failed to set up encryption")