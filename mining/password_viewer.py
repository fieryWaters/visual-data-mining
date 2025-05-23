#!/usr/bin/env python3
"""
Password viewer for the PyKeePass integration.
Provides a simple interface to view, add, and delete passwords.
"""

import os
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from utils.keepass_manager import KeePassManager

class PasswordViewer:
    """Password viewer dialog"""
    
    def __init__(self, parent, keepass_manager=None, db_path="passwords.kdbx"):
        """Initialize with parent window and optional KeePass manager"""
        self.parent = parent
        
        # Use provided manager or get singleton instance
        if keepass_manager:
            self.keepass_manager = keepass_manager
        else:
            self.keepass_manager = KeePassManager.get_instance(db_path)
            
        # Password entries
        self.password_entries = []
        self.showing_passwords = {}  # Track which passwords are shown
        
    def show_dialog(self):
        """Show the password viewer dialog"""
        # Create a new top level window
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Password Viewer")
        self.dialog.geometry("400x400")
        self.dialog.configure(bg="#2C2C2C")
        self.dialog.resizable(False, False)
        
        # Make dialog modal
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        
        # Check if database is locked
        if not self.keepass_manager.is_unlocked():
            # Offer to unlock but don't force it
            if messagebox.askyesno(
                "Database Locked",
                "Password database is locked. Would you like to unlock it now?",
                parent=self.dialog
            ):
                # User chose to unlock, prompt for password
                master_password = simpledialog.askstring(
                    "Master Password",
                    "Enter master password to view passwords:",
                    show='*',
                    parent=self.dialog
                )
                
                if master_password:
                    # Try to unlock with the provided password
                    success = self.keepass_manager.unlock(master_password)
                    if success:
                        # Load the passwords if unlocked successfully
                        self.keepass_manager.load_passwords()
                    else:
                        # Show error but don't close dialog
                        messagebox.showerror(
                            "Error", 
                            "Failed to unlock password database. Check your password and try again.",
                            parent=self.dialog
                        )
                # If user cancels password prompt, just continue with locked state
            # If user doesn't want to unlock, just continue with locked state
        
        # Create frame for the password list
        self.password_frame = tk.Frame(self.dialog, bg="#2C2C2C")
        self.password_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Create buttons
        button_frame = tk.Frame(self.dialog, bg="#2C2C2C")
        button_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        add_button = tk.Button(
            button_frame,
            text="Add Password",
            font=("Helvetica", 12, "bold"),
            command=self.add_password
        )
        add_button.pack(side="left", padx=5, pady=5, fill="x", expand=True)
        
        close_button = tk.Button(
            button_frame,
            text="Close",
            font=("Helvetica", 12, "bold"),
            command=self.dialog.destroy
        )
        close_button.pack(side="left", padx=5, pady=5, fill="x", expand=True)
        
        # Add database management buttons
        db_frame = tk.Frame(self.dialog, bg="#2C2C2C")
        db_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        # Change password button - disable if locked
        self.change_pw_button = tk.Button(
            db_frame,
            text="Change Keyring Password",
            font=("Helvetica", 12, "bold"),
            command=self._change_master_password
        )
        self.change_pw_button.pack(side="left", padx=5, pady=5, fill="x", expand=True)
        
        # Create new keyring button - always enabled
        new_keyring_button = tk.Button(
            db_frame,
            text="Create New Keyring",
            font=("Helvetica", 12, "bold"),
            command=self._create_new_keyring
        )
        new_keyring_button.pack(side="left", padx=5, pady=5, fill="x", expand=True)
        
        # Update button states based on lock state
        self._update_button_states()
        
        # Load and display passwords
        self.load_passwords()
        
        # Wait for dialog to close
        self.parent.wait_window(self.dialog)
    
    def load_passwords(self):
        """Load and display passwords from the database"""
        # Clear existing entries
        for widget in self.password_frame.winfo_children():
            widget.destroy()
        
        # Reset tracking
        self.password_entries = []
        self.showing_passwords = {}
        
        # Update button states
        self._update_button_states()
        
        # Check if locked
        if not self.keepass_manager.is_unlocked():
            # Show locked message
            label = tk.Label(
                self.password_frame,
                text="Password database is locked",
                font=("Helvetica", 10),
                fg="white",
                bg="#2C2C2C"
            )
            label.pack(pady=50)
            return
            
        # Get passwords from the database
        password_entries = self.keepass_manager.kp.entries if hasattr(self.keepass_manager, 'kp') and self.keepass_manager.kp else []
        
        if not password_entries:
            label = tk.Label(
                self.password_frame,
                text="No passwords found in the database",
                font=("Helvetica", 10),
                fg="white",
                bg="#2C2C2C"
            )
            label.pack(pady=50)
            return
        
        # Create header
        header_frame = tk.Frame(self.password_frame, bg="#2C2C2C")
        header_frame.pack(fill="x", pady=(0, 5))
        
        tk.Label(
            header_frame,
            text="Title",
            font=("Helvetica", 10, "bold"),
            fg="white",
            bg="#2C2C2C",
            width=20,
            anchor="w"
        ).pack(side="left", padx=5)
        
        tk.Label(
            header_frame,
            text="Password",
            font=("Helvetica", 10, "bold"),
            fg="white",
            bg="#2C2C2C",
            width=20,
            anchor="w"
        ).pack(side="left", padx=5)
        
        tk.Label(
            header_frame,
            text="Show",
            font=("Helvetica", 10, "bold"),
            fg="white",
            bg="#2C2C2C",
            width=5,
            anchor="w"
        ).pack(side="left", padx=5)
        
        tk.Label(
            header_frame,
            text="Delete",
            font=("Helvetica", 10, "bold"),
            fg="white",
            bg="#2C2C2C",
            width=5,
            anchor="w"
        ).pack(side="left", padx=5)
        
        # Create scrollable container
        canvas = tk.Canvas(self.password_frame, bg="#2C2C2C", highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.password_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg="#2C2C2C")
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Add password entries
        for i, entry in enumerate(password_entries):
            entry_id = id(entry)
            self.showing_passwords[entry_id] = False
            
            entry_frame = tk.Frame(scrollable_frame, bg="#333333")
            entry_frame.pack(fill="x", pady=1)
            
            # Title
            title_label = tk.Label(
                entry_frame,
                text=entry.title or f"Password {i+1}",
                font=("Helvetica", 10),
                fg="white",
                bg="#333333",
                width=20,
                anchor="w"
            )
            title_label.pack(side="left", padx=5, pady=5)
            
            # Password (masked by default)
            password_label = tk.Label(
                entry_frame,
                text="*" * 8,
                font=("Helvetica", 10),
                fg="white",
                bg="#333333",
                width=20,
                anchor="w"
            )
            password_label.pack(side="left", padx=5, pady=5)
            
            # Show/hide checkbox
            show_var = tk.BooleanVar(value=False)
            show_checkbox = tk.Checkbutton(
                entry_frame,
                variable=show_var,
                bg="#333333",
                activebackground="#444444",
                fg="white",
                selectcolor="#222222",  # Darker color when selected for better contrast
                highlightthickness=0,   # Remove highlight border
                command=lambda e=entry, pl=password_label, sv=show_var, eid=entry_id: self.toggle_password(e, pl, sv, eid)
            )
            show_checkbox.pack(side="left", padx=5, pady=5)
            
            # Delete button
            delete_button = tk.Button(
                entry_frame,
                text="X",
                font=("Helvetica", 8, "bold"),
                width=2,
                command=lambda e=entry, ef=entry_frame: self.delete_password(e, ef)
            )
            delete_button.pack(side="left", padx=5, pady=5)
            
            self.password_entries.append({
                "entry": entry,
                "frame": entry_frame,
                "password_label": password_label,
                "show_var": show_var
            })
    
    def toggle_password(self, entry, label, show_var, entry_id):
        """Toggle password visibility"""
        if show_var.get():
            # Show password
            label.config(text=entry.password)
            self.showing_passwords[entry_id] = True
        else:
            # Hide password
            label.config(text="*" * 8)
            self.showing_passwords[entry_id] = False
    
    def delete_password(self, entry, entry_frame):
        """Delete a password with confirmation"""
        # Check if database is locked
        if not self.keepass_manager.is_unlocked():
            messagebox.showerror(
                "Error", 
                "Database is locked. Cannot delete passwords.",
                parent=self.dialog
            )
            return
            
        title = entry.title or "this password"
        confirm = messagebox.askyesno(
            "Confirm Deletion",
            f"Are you sure you want to delete {title}?",
            parent=self.dialog
        )
        
        if confirm:
            # Delete from the database
            try:
                # Use our remove_password method that checks lock state
                password = entry.password
                success = self.keepass_manager.remove_password(password)
                
                if not success:
                    messagebox.showerror(
                        "Error",
                        "Failed to delete password. Database might be locked.",
                        parent=self.dialog
                    )
                    return
                
                # Remove from the UI
                entry_frame.destroy()
                
                # Check if we need to update the UI
                entries = []
                if self.keepass_manager.is_unlocked() and hasattr(self.keepass_manager, 'kp') and self.keepass_manager.kp:
                    entries = self.keepass_manager.kp.entries
                    
                if not entries:
                    self.load_passwords()  # Reload to show "No passwords" message
                    
                messagebox.showinfo(
                    "Success",
                    f"Password {title} deleted successfully",
                    parent=self.dialog
                )
                
            except Exception as e:
                messagebox.showerror(
                    "Error",
                    f"Failed to delete password: {e}",
                    parent=self.dialog
                )
    
    def add_password(self):
        """Add a new password"""
        # Check if database is locked
        if not self.keepass_manager.is_unlocked():
            # Prompt for password
            master_password = simpledialog.askstring(
                "Unlock Database",
                "Database is locked. Enter master password to unlock:",
                show='*',
                parent=self.dialog
            )
            
            if not master_password:
                return
                
            success = self.keepass_manager.unlock(master_password)
            if not success:
                messagebox.showerror(
                    "Error", 
                    "Failed to unlock database. Incorrect password.",
                    parent=self.dialog
                )
                return
        
        # Password entry dialog
        password = simpledialog.askstring(
            "Add Password",
            "Enter new password to protect:",
            show='*',
            parent=self.dialog
        )
        
        if not password:
            return
            
        # Optional title
        title = simpledialog.askstring(
            "Password Title",
            "Enter a title for this password (optional):",
            parent=self.dialog
        )
        
        try:
            # Add to the database
            self.keepass_manager.add_password(password, title=title)
            
            # Reload the password list
            self.load_passwords()
            
            messagebox.showinfo(
                "Success",
                "Password added successfully",
                parent=self.dialog
            )
            
        except Exception as e:
            messagebox.showerror(
                "Error",
                "Failed to add password",
                parent=self.dialog
            )
            
    def _update_button_states(self):
        """Update button states based on lock status"""
        is_unlocked = self.keepass_manager.is_unlocked()
        
        # Change password button - only enabled if unlocked
        if is_unlocked:
            self.change_pw_button.config(state="normal")
        else:
            self.change_pw_button.config(state="disabled")
            
    def _change_master_password(self):
        """Delegate to KeePassDialog's change master password method"""
        # This should only be callable when the database is already unlocked
        # But double-check anyway
        if not self.keepass_manager.is_unlocked():
            messagebox.showerror(
                "Error",
                "Database must be unlocked first to change password.",
                parent=self.dialog
            )
            return
            
        from pykeepass_gui import KeePassDialog
        dialog = KeePassDialog(self.dialog, self.keepass_manager.passwords_file)
        result = dialog.change_master_password()
        
        # Refresh the password list after changing master password
        if result:
            self.load_passwords()
    
    def _create_new_keyring(self):
        """Delegate to KeePassDialog's create new keyring method"""
        from pykeepass_gui import KeePassDialog
        dialog = KeePassDialog(self.dialog, self.keepass_manager.passwords_file)
        result = dialog.create_new_keyring()
        
        # Refresh the password list after creating new keyring
        if result:
            self.load_passwords()
            
    def prompt_unlock(self):
        """Prompt for master password to unlock the database"""
        master_password = simpledialog.askstring(
            "Master Password",
            "Enter master password to unlock database:",
            show='*',
            parent=self.dialog
        )
        
        if not master_password:
            return False
            
        # Try to unlock with the provided password
        return self.keepass_manager.unlock(master_password)


if __name__ == "__main__":
    # Test the password viewer
    root = tk.Tk()
    root.title("Password Viewer Test")
    root.geometry("200x100")
    
    def show_viewer():
        viewer = PasswordViewer(root)
        viewer.show_dialog()
    
    button = tk.Button(root, text="Show Password Viewer", command=show_viewer)
    button.pack(padx=20, pady=30)
    
    root.mainloop()