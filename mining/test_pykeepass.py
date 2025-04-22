#!/usr/bin/env python3
"""
Test script for PyKeePass integration.
Demonstrates basic functionality of creating, loading, and manipulating KeePass databases.
"""

import os
import sys
from pykeepass import PyKeePass, create_database
from pykeepass.exceptions import CredentialsError

def create_keepass_db(filepath, password, keyfile=None):
    """Create a new KeePass database with the given password and optional keyfile"""
    print(f"Creating new KeePass database at {filepath}")
    
    # Check if file already exists
    if os.path.exists(filepath):
        print(f"File {filepath} already exists. Aborting creation.")
        return None
    
    try:
        # Create a new KeePass database
        kp = create_database(filepath, password=password, keyfile=keyfile)
        
        # Save the database
        kp.save()
        print(f"Successfully created KeePass database at {filepath}")
        return kp
    except Exception as e:
        print(f"Error creating KeePass database: {e}")
        return None

def open_keepass_db(filepath, password, keyfile=None):
    """Open an existing KeePass database with the given password and optional keyfile"""
    print(f"Opening KeePass database at {filepath}")
    
    if not os.path.exists(filepath):
        print(f"File {filepath} does not exist.")
        return None
    
    try:
        # Open the existing KeePass database
        kp = PyKeePass(filepath, password=password, keyfile=keyfile)
        print("Successfully opened KeePass database")
        return kp
    except CredentialsError:
        print("Incorrect password or keyfile")
        return None
    except Exception as e:
        print(f"Error opening KeePass database: {e}")
        return None

def add_password_entry(kp, title, username, password, url=None, notes=None):
    """Add a password entry to the KeePass database"""
    if not kp:
        print("No open KeePass database")
        return False
    
    try:
        # Get the root group
        root_group = kp.root_group
        
        # Create a new entry
        entry = kp.add_entry(root_group, title, username, password, url=url, notes=notes)
        
        # Save the database
        kp.save()
        print(f"Added password entry: {title}")
        return True
    except Exception as e:
        print(f"Error adding password entry: {e}")
        return False

def list_passwords(kp):
    """List all passwords in the KeePass database"""
    if not kp:
        print("No open KeePass database")
        return []
    
    try:
        # Get all entries
        entries = kp.entries
        
        # Create a list of passwords
        passwords = []
        print("\nPassword entries:")
        for entry in entries:
            print(f"Title: {entry.title}, Username: {entry.username}, Password: {entry.password}")
            passwords.append(entry.password)
        
        return passwords
    except Exception as e:
        print(f"Error listing passwords: {e}")
        return []

def find_entry(kp, title=None, username=None):
    """Find entries matching the given criteria"""
    if not kp:
        print("No open KeePass database")
        return None
    
    try:
        # Find entries
        entries = kp.find_entries(title=title, username=username)
        
        if not entries:
            print(f"No entries found matching title='{title}', username='{username}'")
            return None
        
        print(f"Found {len(entries)} matching entries:")
        for i, entry in enumerate(entries):
            print(f"{i+1}. Title: {entry.title}, Username: {entry.username}, Password: {entry.password}")
        
        return entries
    except Exception as e:
        print(f"Error finding entries: {e}")
        return None

def remove_entry(kp, entry):
    """Remove an entry from the KeePass database"""
    if not kp or not entry:
        print("No open KeePass database or no entry provided")
        return False
    
    try:
        # Remove the entry
        kp.delete_entry(entry)
        
        # Save the database
        kp.save()
        print(f"Removed entry: {entry.title}")
        return True
    except Exception as e:
        print(f"Error removing entry: {e}")
        return False

def get_all_passwords(kp):
    """Extract just the password strings from all entries"""
    if not kp:
        return []
    
    try:
        return [entry.password for entry in kp.entries]
    except Exception as e:
        print(f"Error getting passwords: {e}")
        return []

def main():
    """Main function for testing PyKeePass functionality"""
    # Database file path
    db_path = "passwords.kdbx"
    
    # Master password
    master_password = "master_password"
    
    # Check if database exists, create if not
    if not os.path.exists(db_path):
        kp = create_keepass_db(db_path, master_password)
        if not kp:
            sys.exit(1)
        
        # Add some test passwords
        add_password_entry(kp, "Sample Login", "user1", "password123")
        add_password_entry(kp, "Email", "user@example.com", "email_password")
        add_password_entry(kp, "Banking", "bank_user", "secure_bank_password")
    else:
        # Open existing database
        kp = open_keepass_db(db_path, master_password)
        if not kp:
            sys.exit(1)
    
    # List all passwords
    passwords = list_passwords(kp)
    
    # Find a specific entry
    entries = find_entry(kp, title="Email")
    
    # Remove an entry (if any were found)
    if entries:
        remove_entry(kp, entries[0])
        print("\nAfter removal:")
        list_passwords(kp)
    
    # Get just the password strings
    password_strings = get_all_passwords(kp)
    print(f"\nPassword strings for sanitization: {password_strings}")
    
    print("\nTest completed successfully")

if __name__ == "__main__":
    main()