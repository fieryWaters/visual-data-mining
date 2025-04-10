#!/usr/bin/env python3
"""
Build script for packaging the Visual Data Mining application with PyInstaller.
Creates a standalone executable with all dependencies included.
"""

import os
import sys
import shutil
import subprocess
import glob
from pathlib import Path

def check_pyinstaller():
    """Check if PyInstaller is installed, install if not."""
    try:
        import PyInstaller
        print("PyInstaller is already installed.")
        return True
    except ImportError:
        print("PyInstaller not found. Installing...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error installing PyInstaller: {e}")
            return False

def create_build_directories():
    """Create and clean build directories."""
    build_dir = Path("build")
    dist_dir = Path("dist")
    
    # Clean existing build artifacts
    if build_dir.exists():
        print(f"Cleaning {build_dir}...")
        shutil.rmtree(build_dir)
    
    if dist_dir.exists():
        print(f"Cleaning {dist_dir}...")
        shutil.rmtree(dist_dir)
    
    # Create directories
    build_dir.mkdir(exist_ok=True)
    dist_dir.mkdir(exist_ok=True)
    
    return True

def cleanup_build_artifacts(source_path, executable_name, onefile=True):
    """
    Clean up PyInstaller build artifacts and move executable to main directory.
    
    Args:
        source_path: Path to the generated executable
        executable_name: Name of the executable file
        onefile: Whether the build was a single file or directory
    
    Returns:
        bool: True if cleanup was successful, False otherwise
    """
    try:
        # Move the executable to the main directory
        if os.path.exists(source_path):
            print(f"Moving executable to main directory...")
            shutil.copy2(source_path, executable_name)
            print(f"Executable copied to {executable_name}")
        else:
            print(f"Warning: Could not find executable at {source_path}")
            return False
        
        # Remove .spec file(s)
        for spec_file in glob.glob("*.spec"):
            print(f"Removing spec file: {spec_file}")
            os.remove(spec_file)
        
        # Remove build directory
        if os.path.exists("build"):
            print("Removing build directory...")
            shutil.rmtree("build")
        
        # Remove dist directory
        if os.path.exists("dist"):
            print("Removing dist directory...")
            shutil.rmtree("dist")
        
        # Check if everything worked
        cleanup_success = (
            not os.path.exists("build") and
            not os.path.exists("dist") and
            len(glob.glob("*.spec")) == 0 and
            os.path.exists(executable_name)
        )
        
        return cleanup_success
    
    except Exception as e:
        print(f"Error during cleanup: {e}")
        return False

def build_application(onefile=True, debug=False, clean_after=True):
    """
    Build the application using PyInstaller with all necessary options.
    
    Args:
        onefile: If True, create a single executable file instead of a directory
        debug: If True, add debug options for troubleshooting
        clean_after: If True, clean up build artifacts and move executable to main directory
    """
    # Entry point file (the main script to execute)
    entry_point = "data_collection_GUI.py"
    
    # Check if the entry point exists
    if not os.path.exists(entry_point):
        print(f"Error: Entry point {entry_point} not found.")
        return False
        
    # If you change the class name inside data_collection_GUI.py, 
    # you don't need to modify anything here - PyInstaller will handle it
    
    # Application name for the output
    app_name = "data_collection_GUI"
    
    # Basic command with required options
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--clean",
        "--name", app_name
    ]
    
    # Add packaging mode (--onefile or --onedir)
    if onefile:
        cmd.append("--onefile")
    else:
        cmd.append("--onedir")
    
    # Add hidden imports for our dependencies
    hidden_imports = [
        # Pynput dependencies
        "pynput.keyboard", "pynput.keyboard._win32", "pynput.keyboard._darwin", "pynput.keyboard._xorg",
        "pynput.mouse", "pynput.mouse._win32", "pynput.mouse._darwin", "pynput.mouse._xorg",
        
        # Tkinter dependencies
        "tkinter", "tkinter.ttk", "tkinter.messagebox", "tkinter.simpledialog", "tkinter.filedialog",
        
        # Other potential hidden imports
        "PIL", "PIL._tkinter_finder", "cv2", "numpy", "cryptography.hazmat.backends.openssl",
        
        # Project modules
        "utils.text_buffer", "utils.password_manager", "utils.fuzzy_matcher"
    ]
    
    for imp in hidden_imports:
        cmd.extend(["--hidden-import", imp])
    
    # Add data files and directories
    data_files = [
        # Add logs directory as a data directory
        ("logs", "logs"),
        
        # Add screenshots directory as a data directory
        ("screenshots", "screenshots"),
        
        # Specify any other resource files your app needs
        # ("path/to/resource", "resource")
    ]
    
    for src, dst in data_files:
        if os.path.exists(src):
            cmd.extend(["--add-data", f"{src}{os.pathsep}{dst}"])
    
    # Add debug options if requested
    if debug:
        cmd.append("--debug=all")
    
    # No console window for GUI application unless in debug mode
    if not debug:
        cmd.append("--noconsole")
    
    # Add icon if available
    # if os.path.exists("path/to/icon.ico"):
    #     cmd.extend(["--icon", "path/to/icon.ico"])
    
    # Add entry point
    cmd.append(entry_point)
    
    # Run PyInstaller
    print("\nRunning PyInstaller with the following command:")
    print(" ".join(cmd))
    print("\nThis may take several minutes...\n")
    
    try:
        subprocess.check_call(cmd)
        print("\nBuild completed successfully!")
        
        # Show output location
        executable_ext = '.exe' if sys.platform == 'win32' else ''
        executable_name = f"{app_name}{executable_ext}"
        
        if onefile:
            source_path = f"dist/{executable_name}"
            print(f"\nExecutable created at: {source_path}")
        else:
            source_path = f"dist/{app_name}/{executable_name}"
            print(f"\nApplication directory created at: dist/{app_name}/")
            print(f"Run with: {source_path}")
        
        # Clean up build artifacts if requested
        if clean_after:
            success = cleanup_build_artifacts(source_path, executable_name, onefile)
            if success:
                print(f"\nCleanup completed. Executable is now in the main directory: {executable_name}")
            else:
                print("\nWarning: Cleanup failed. Build artifacts remain.")
        
        return True
    
    except subprocess.CalledProcessError as e:
        print(f"\nError during build: {e}")
        return False

def main():
    """Main function to build the application."""
    print("=== Data Collection GUI Builder ===\n")
    print("Building a standalone executable...\n")
    
    if not check_pyinstaller():
        return 1
    
    if not create_build_directories():
        return 1
    
    # Build a single file executable and clean up afterwards
    if not build_application(onefile=True, debug=False, clean_after=True):
        return 1
    
    print("\nBuild process completed.")
    return 0

if __name__ == "__main__":
    sys.exit(main())