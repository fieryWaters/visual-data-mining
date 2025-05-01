"""
KeePass password manager module.
Handles secure storage and retrieval of passwords for the keystroke sanitizer
using the PyKeePass library.
"""

import os
import threading
from typing import List, Optional, Tuple, ClassVar
from pykeepass import PyKeePass, create_database
from pykeepass.exceptions import CredentialsError


class KeePassManager:
    """Manages secure storage and retrieval of passwords using KeePass"""
    
    _instance: ClassVar[Optional['KeePassManager']] = None
    _lock = threading.RLock()  # Reentrant lock for thread safety
    
    @classmethod
    def get_instance(cls, passwords_file="passwords.kdbx") -> 'KeePassManager':
        """Get or create the singleton instance"""
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls(passwords_file)
            return cls._instance
    
    def __init__(self, passwords_file="passwords.kdbx"):
        """Initialize with password file path"""
        # Protect singleton pattern
        with self._lock:
            if KeePassManager._instance is not None and self is not KeePassManager._instance:
                # Just return if someone tries to create a new instance
                return
            
            self.passwords_file = passwords_file
            self.kp = None
            self.passwords = []
            self.is_initialized = False
            self.is_locked = True  # Start in locked state
            
            # Make this the singleton instance if it's the first creation
            if KeePassManager._instance is None:
                KeePassManager._instance = self
    
    def setup_encryption(self, password=None, keyfile=None) -> bool:
        """Set up encryption with the provided password"""
        with self._lock:
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
                
                self.is_initialized = True
                self.is_locked = False  # Unlock the database
                return True
            except Exception as e:
                print(f"Error setting up encryption: {e}")
                self.is_initialized = False
                self.is_locked = True
                return False
                
    def unlock(self, password=None, keyfile=None) -> bool:
        """Unlock the database with provided credentials"""
        with self._lock:
            if not password:
                return False
                
            # Check if database exists
            if not os.path.exists(self.passwords_file):
                return False
                
            try:
                # Try to open the database
                self.kp = PyKeePass(self.passwords_file, password=password, keyfile=keyfile)
                self.is_initialized = True
                self.is_locked = False
                return True
            except Exception as e:
                print(f"Error unlocking database: {e}")
                self.is_locked = True
                return False
                
    def is_unlocked(self) -> bool:
        """Check if the database is currently unlocked"""
        return self.is_initialized and not self.is_locked
        
    def database_exists(self) -> bool:
        """Check if the database file exists"""
        return os.path.exists(self.passwords_file)
    
    def load_passwords(self) -> bool:
        """Load passwords from KeePass database"""
        with self._lock:
            try:
                if self.is_locked or not self.is_initialized or not self.kp:
                    print("Database is locked or not initialized.")
                    return False
                    
                self.passwords = self._extract_passwords()
                return True
            except Exception as e:
                print(f"Error loading passwords: {e}")
                return False
    
    def save_passwords(self) -> bool:
        """Save passwords to KeePass database"""
        with self._lock:
            try:
                if self.is_locked or not self.is_initialized or not self.kp:
                    print("Database is locked or not initialized.")
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
        with self._lock:
            if self.is_locked or not self.is_initialized or not self.kp:
                print("Database is locked or not initialized.")
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
        with self._lock:
            if self.is_locked or not self.is_initialized or not self.kp:
                print("Database is locked or not initialized.")
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
        with self._lock:
            if self.is_locked or not self.kp:
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
        with self._lock:
            if self.is_locked or not self.is_initialized or not self.kp:
                return []
                
            try:
                return [entry.password for entry in self.kp.entries 
                       if password_fragment.lower() in entry.password.lower()]
            except Exception as e:
                print(f"Error searching passwords: {e}")
                return []
                
    def change_master_password(self, current_password: str, new_password: str, keyfile: Optional[str] = None) -> bool:
        """Change the master password of the database"""
        with self._lock:
            if not os.path.exists(self.passwords_file):
                return False
                
            try:
                # Open the database with current credentials
                temp_kp = PyKeePass(self.passwords_file, password=current_password, keyfile=keyfile)
                
                # Change the password
                temp_kp.password = new_password
                
                # Save the database with new password
                temp_kp.save()
                
                # Update our instance to use the new credentials
                self.kp = temp_kp
                self.is_initialized = True
                self.is_locked = False
                
                return True
            except Exception as e:
                print(f"Error changing master password: {e}")
                return False
                
    def create_new_database(self, new_password: str, keyfile: Optional[str] = None, transfer_entries: bool = False) -> bool:
        """Create a new database, optionally transferring entries from the old one"""
        with self._lock:
            try:
                old_entries = []
                
                # If transferring entries and we have an unlocked database, save the entries
                if transfer_entries and self.is_unlocked() and self.kp:
                    old_entries = [(entry.title, entry.username, entry.password) for entry in self.kp.entries]
                
                # Create new database
                new_kp = create_database(self.passwords_file, password=new_password, keyfile=keyfile)
                
                # Transfer entries if requested
                if transfer_entries and old_entries:
                    root_group = new_kp.root_group
                    for title, username, password in old_entries:
                        new_kp.add_entry(root_group, title, username or "", password)
                
                # Save the new database
                new_kp.save()
                
                # Update our instance
                self.kp = new_kp
                self.is_initialized = True
                self.is_locked = False
                
                # Update the passwords list
                self.passwords = self._extract_passwords()
                
                return True
            except Exception as e:
                print(f"Error creating new database: {e}")
                return False


if __name__ == "__main__":
    # Simple test
    import getpass
    
    manager = KeePassManager.get_instance()
    
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