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
        self.keepass_manager = KeePassManager(db_path)
        
    def init_database(self):
        """Initialize the KeePass database, create if needed"""
        if os.path.exists(self.db_path):
            # Database exists, prompt for password
            return self._prompt_master_password()
        else:
            # No database, prompt to create
            return self._create_new_database()
    
    def _create_new_database(self):
        """Create a new KeePass database with master password"""
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
            messagebox.showerror(
                "Error",
                "Failed to create password database.",
                parent=self.parent
            )
            return False
    
    def _prompt_master_password(self, attempts=3):
        """Prompt for master password to open existing database"""
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
                # Password is correct
                self.keepass_manager.setup_encryption(password)
                self.keepass_manager.load_passwords()
                return True
            else:
                attempts_left = attempts - i - 1
                if attempts_left > 0:
                    messagebox.showerror(
                        "Error",
                        f"Incorrect password. {attempts_left} attempts remaining.",
                        parent=self.parent
                    )
                else:
                    messagebox.showerror(
                        "Error",
                        "Failed to unlock database after multiple attempts.",
                        parent=self.parent
                    )
        return False
    
    def add_password(self):
        """Add a new password to the database"""
        # Make sure database is initialized
        if not self.keepass_manager.kp:
            result = self.init_database()
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
        # Make sure database is initialized
        if not self.keepass_manager.kp:
            result = self.init_database()
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
        # Make sure database is initialized
        if not self.keepass_manager.kp:
            return []
            
        return self.keepass_manager.get_passwords()


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