#!/usr/bin/env python3
"""
PyKeePass integration for the data collection GUI.
Provides dialog boxes for creating and accessing KeePass databases.
"""

import os
import tkinter as tk
from tkinter import simpledialog, messagebox
from utils.keepass_manager import KeePassManager


class KeePassDialog:
    """Handles PyKeePass interactions for the GUI"""
    
    def __init__(self, parent, db_path="passwords.kdbx"):
        """Initialize with parent window and database path"""
        self.parent = parent
        self.db_path = db_path
        self.keepass_manager = KeePassManager.get_instance(db_path)
        self.status_var = None
        
    def init_database(self, silent=False):
        """
        Initialize the KeePass database, create if needed
        
        Args:
            silent: If True, don't show error messages for cancellations
            
        Returns:
            bool: True if database was successfully initialized
        """
        if os.path.exists(self.db_path):
            # Database exists, prompt for password
            return self._prompt_master_password(attempts=3, silent=silent)
        else:
            # No database, prompt to create
            return self._create_new_database(silent=silent)
    
    def _create_new_database(self, silent=False):
        """
        Create a new KeePass database with master password
        
        Args:
            silent: If True, don't show error messages for cancellations
        """
        
        # Show a dialog explaining what's happening
        messagebox.showinfo(
            "Create Password Database",
            "No password database found. You'll need to create a new database with a master password.\n\n"
            "This master password will protect all your passwords. Make sure to remember it!",
            parent=self.parent
        )
        
        # Prompt for new master password
        password = simpledialog.askstring(
            "Create Master Password",
            "Enter new master password:",
            show='*',
            parent=self.parent
        )
        
        if not password:
            if not silent:
                messagebox.showinfo("Cancelled", "Database creation cancelled.", parent=self.parent)
            return False
            
        # Confirm password
        confirm = simpledialog.askstring(
            "Confirm Master Password",
            "Confirm master password:",
            show='*',
            parent=self.parent
        )
        
        if password != confirm:
            if not silent:
                messagebox.showerror("Error", "Passwords do not match!", parent=self.parent)
            return False
            
        # Create the database
        if self.keepass_manager.setup_encryption(password):
            messagebox.showinfo(
                "Success", 
                f"Password database created successfully at {self.db_path}",
                parent=self.parent
            )
            return True
        else:
            if not silent:
                messagebox.showerror(
                    "Error",
                    "Failed to create password database.",
                    parent=self.parent
                )
            return False
    
    def _prompt_master_password(self, attempts=3, silent=False):
        """
        Prompt for master password to open existing database
        
        Args:
            attempts: Number of password attempts allowed
            silent: If True, don't show error messages for cancellations
        """
        
        for i in range(attempts):
            password = simpledialog.askstring(
                "Master Password",
                f"Enter master password for {self.db_path}:",
                show='*',
                parent=self.parent
            )
            
            if password is None:  # User cancelled
                return False
                
            if self.keepass_manager.check_credentials(password):
                # Password is correct - use unlock instead of setup_encryption
                if self.keepass_manager.unlock(password):
                    self.keepass_manager.load_passwords()
                    return True
            else:
                attempts_left = attempts - i - 1
                if attempts_left > 0:
                    if not silent:
                        messagebox.showerror(
                            "Error",
                            f"Incorrect password. {attempts_left} attempts remaining.",
                            parent=self.parent
                        )
                else:
                    if not silent:
                        messagebox.showerror(
                            "Error",
                            "Failed to unlock database after multiple attempts.",
                            parent=self.parent
                        )
        return False
        
    def check_unlock_state(self):
        """Update UI based on lock state"""
        is_unlocked = self.keepass_manager.is_unlocked()
        
        # Return the state for other components to use
        return is_unlocked
        
    def prompt_unlock(self):
        """Explicitly prompt for unlock"""
        if self.keepass_manager.is_unlocked():
            # Already unlocked
            return True
            
        return self._prompt_master_password(attempts=3, silent=False)
    
    def add_password(self):
        """Add a new password to the database"""
        # Check if database is locked
        if not self.keepass_manager.is_unlocked():
            # Try to unlock
            result = self.prompt_unlock()
            if not result:
                return False
                
        # Prompt for the password to add
        password = simpledialog.askstring(
            "Add Password", 
            "Enter password to sanitize:", 
            show='*',
            parent=self.parent
        )
        
        if not password:
            return False
            
        # Add the password
        title = simpledialog.askstring(
            "Add Password",
            "Enter a title for this password (optional):",
            parent=self.parent
        )
        
        success = self.keepass_manager.add_password(password, title=title or None)
        
        if success:
            messagebox.showinfo("Success", "Password added successfully", parent=self.parent)
            return True
        else:
            messagebox.showerror("Error", "Failed to add password", parent=self.parent)
            return False
    
    def search_for_password(self):
        """Search for a password in the database"""
        # Check if database is locked
        if not self.keepass_manager.is_unlocked():
            # Try to unlock
            result = self.prompt_unlock()
            if not result:
                return []
                
        # Prompt for search term
        search_term = simpledialog.askstring(
            "Search Password", 
            "Enter text to search for:", 
            parent=self.parent
        )
        
        if not search_term:
            return []
            
        # Search for the password
        return self.keepass_manager.search_password(search_term)
    
    def get_all_passwords(self):
        """Get all passwords for sanitization"""
        # Check if locked - if so, just return empty list
        if not self.keepass_manager.is_unlocked():
            return []
            
        return self.keepass_manager.get_passwords()
        
    def retroactive_sanitize(self, custom_strings=None):
        """Perform retroactive sanitization with optional custom strings"""
        from keystroke_sanitizer import KeystrokeSanitizer
        
        # Check if database is locked
        if not self.keepass_manager.is_unlocked():
            # Try to unlock
            result = self.prompt_unlock()
            if not result:
                return False
        
        # Create sanitizer that uses our KeePass manager
        sanitizer = KeystrokeSanitizer()
        
        # If custom strings provided, use them, otherwise use all passwords
        strings_to_sanitize = custom_strings if custom_strings else None
        
        # Find occurrences
        occurrences = sanitizer.find_occurrences(strings_to_sanitize)
        
        if not occurrences:
            messagebox.showinfo(
                "No Matches", 
                "No password occurrences found in log files.",
                parent=self.parent
            )
            return False
            
        # Show found occurrences and ask for confirmation
        files_text = "\n".join([f"• {file}: {count} occurrences" for file, count in list(occurrences.items())[:10]])
        if len(occurrences) > 10:
            files_text += f"\n• ... and {len(occurrences) - 10} more files"
            
        confirm = messagebox.askyesno(
            "Confirm Sanitization",
            f"Found {sum(occurrences.values())} potential password occurrences in {len(occurrences)} files:\n\n{files_text}\n\n"
            "Do you want to sanitize these files?",
            parent=self.parent
        )
        
        if not confirm:
            return False
        
        # Perform sanitization
        replacements = sanitizer.sanitize_logs(strings_to_sanitize)
        
        if replacements:
            messagebox.showinfo(
                "Sanitization Complete",
                f"Sanitized {sum(replacements.values())} occurrences in {len(replacements)} files.",
                parent=self.parent
            )
            return True
        else:
            messagebox.showinfo(
                "No Changes",
                "No changes were made to log files.",
                parent=self.parent
            )
            return False
            
    def retroactive_sanitize_with_search(self):
        """Search for passwords and retroactively sanitize them"""
        # Check if database is locked
        if not self.keepass_manager.is_unlocked():
            # Try to unlock
            result = self.prompt_unlock()
            if not result:
                return False
        
        # Prompt for search term
        search_term = simpledialog.askstring(
            "Search for Sanitization", 
            "Enter text to search for in passwords:", 
            parent=self.parent
        )
        
        if not search_term:
            return False
        
        # Search for matching passwords
        matching_passwords = self.keepass_manager.search_password(search_term)
        
        if not matching_passwords:
            messagebox.showinfo(
                "No Matches", 
                f"No passwords found containing '{search_term}'.",
                parent=self.parent
            )
            return False
            
        # Show found passwords and ask for confirmation
        passwords_text = "\n".join([f"• {pw}" for pw in matching_passwords[:5]])
        if len(matching_passwords) > 5:
            passwords_text += f"\n• ... and {len(matching_passwords) - 5} more"
            
        confirm = messagebox.askyesno(
            "Confirm Search",
            f"Found {len(matching_passwords)} password(s) containing '{search_term}':\n\n{passwords_text}\n\n"
            "Do you want to search logs for these passwords?",
            parent=self.parent
        )
        
        if not confirm:
            return False
            
        # Perform retroactive sanitization with these passwords
        return self.retroactive_sanitize(matching_passwords)


# For testing independently
if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()  # Hide main window
    dialog = KeePassDialog(root)
    
    if dialog.init_database():
        print("Database initialized successfully")
        
        # Add a password
        if dialog.add_password():
            print("Password added successfully")
            
        # Get all passwords
        passwords = dialog.get_all_passwords()
        print(f"All passwords: {passwords}")
        
        # Search for a password
        search_results = dialog.search_for_password()
        print(f"Search results: {search_results}")
    else:
        print("Failed to initialize database")
        
    root.destroy()