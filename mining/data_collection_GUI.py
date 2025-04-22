import tkinter as tk
import tkinter.messagebox as messagebox
import tkinter.simpledialog as simpledialog
import subprocess as sp
import os
import glob
import threading
import time

from simple_collector import SimpleCollector
from pykeepass_gui import KeePassDialog
from password_viewer import PasswordViewer
from retroactive_sanitizer import RetroactiveSanitizer

class DisplayWidget:
    def __init__(self, master, collector=None):
        # The master window is now the dot indicator window
        self.master = master
        self.master.title("Indicator")
        self.master.overrideredirect(True)
        self.master.attributes('-topmost', True)
        
        # Dark background color
        self.master.configure(bg="#2C2C2C")
        
        # Position at bottom-right corner
        screen_width = self.master.winfo_screenwidth()
        screen_height = self.master.winfo_screenheight()
        window_width, window_height = 50, 50
        x = screen_width - window_width - 10
        y = screen_height - window_height - 50
        self.master.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # Create a separate control window that is a child of the dot indicator
        self.control_window = tk.Toplevel(master)
        self.control_window.title("Data Collection Control")
        self.control_window.configure(bg="#2C2C2C")
        self.control_window.geometry("300x400+100+100")

        # Default Prompt For session
        self.session_prompt = ""   # will hold whatever the user typed
        
        # Data collector integration
        self.collector = collector
        
        # PyKeePass integration
        self.keepass_dialog = KeePassDialog(master)
        
        # Track states
        self.is_running = False
        self.is_loading = False
        self.is_saving_prompt = False 
        
        # Create a canvas to hold the circle (in the master window, which is the dot indicator)
        self.canvas = tk.Canvas(
            self.master, 
            width=40, 
            height=40, 
            highlightthickness=0, 
            bd=0, 
            bg="#2C2C2C"
        )
        self.canvas.pack(expand=True, fill="both")
        
        # Draw the circle (initially red)
        self.circle_id = self.canvas.create_oval(5, 5, 40, 40, fill="red", outline="")
        
        # Bind a mouse click on the canvas to toggle the state
        self.canvas.bind("<Button-1>", self.toggle_state)
        
        # Make the dot window draggable (since it has no border)
        self.master.bind("<ButtonPress-1>", self.start_move)
        self.master.bind("<B1-Motion>", self.do_move)
        
        # Connect the windows - closing dot window will close control window
        self.master.protocol("WM_DELETE_WINDOW", self.on_master_close)
        self.control_window.protocol("WM_DELETE_WINDOW", self.on_master_close)

    def toggle_state(self, event=None):
        """
        Toggle between running (green circle) and not running (red circle).
        Controls the data collection process.
        """
        # If we were loading, exit the loading state first.
        if self.is_loading:
            self.is_loading = False
            return

        # If clicking on the circle for dragging, ignore
        if hasattr(event, 'widget') and event.widget != self.canvas:
            return

        # Update UI immediately to show loading state
        self.set_loading_state()  # Show blue during state transition
        self.master.update_idletasks()  # Force UI update

        # Start a separate thread to handle collector operations
        # to avoid freezing the UI
        def toggle_collector():
            try:
                if not self.is_running:
                    # Check if we have a collector, create one if not
                    if self.collector is None:
                        # Make sure to run dialog on main thread
                        self.master.after(0, self._prompt_for_password)
                        return
                    
                    # 1) grab the prompt
                    raw_prompt = self.prompt_widget.get("1.0", "end-1c")
                    if not raw_prompt.strip():
                        self.is_loading = False
                        self.master.after(0, lambda: self.canvas.itemconfig(self.circle_id, fill="red"))
                        messagebox.showerror("Missing prompt", "Please describe what you’re doing first.")
                        return

                    self.session_prompt = raw_prompt        # store it
                    self.prompt_widget.config(state="disabled")  # lock editing

                    self.prompt_widget.config(
                        bg="#555555",      # lighter grey
                        fg="#888888",
                        insertbackground="#888888")
                    
                    # Start collector in a dedicated thread completely separate from the UI
                    print("Starting data collector in dedicated thread...")
                    
                    # Create a completely separate thread for the collector
                    collector_thread = threading.Thread(
                        target=self._start_collector_in_thread,
                        daemon=True
                    )
                    collector_thread.start()
                    
                    # Wait a moment for startup to begin
                    time.sleep(0.5)
                    
                    self.is_running = True
                    self.is_loading = False
                    # Update UI on main thread
                    self.master.after(0, lambda: self.canvas.itemconfig(self.circle_id, fill="green"))
                else:
                                # Deactivate collector (but don't fully stop listeners)
                    if self.collector:
                        print("Deactivating data collector...")
                        self.collector.stop()  # This now just deactivates the recorder

                    self.is_running = False
                    self.is_loading = False
                    self.is_saving_prompt = True
                    self.master.after(0, lambda: self.canvas.itemconfig(self.circle_id, fill="blue"))

                    self._save_prompt_to_log(self.session_prompt)


                    def finish_saving():
                        self.prompt_widget.config(state="normal")
                        self.prompt_widget.delete("1.0", "end")
                        self.prompt_widget.config(
                            bg="#3A3A3A",     # original dark grey
                            fg="white",
                            insertbackground="white")
                        self.is_saving_prompt = False
                        self.is_running = False
                        self.is_loading = False
                        self.canvas.itemconfig(self.circle_id, fill="red")
                    
                    self.session_prompt = ""   

                    self.master.after(2000, finish_saving) 
            except Exception as e:
                print(f"Error toggling collector: {e}")
                self.is_loading = False
                # Update UI on main thread
                self.master.after(0, lambda: self.canvas.itemconfig(self.circle_id, fill="red"))

        threading.Thread(target=toggle_collector, daemon=True).start()
        
    def _start_collector_in_thread(self):
        """Run the collector.start() method in a completely isolated thread"""
        try:
            print("Collector thread starting with process ID:", os.getpid())
            # This runs in its own dedicated thread, isolated from the UI thread
            self.collector.start()
            print("Collector thread completed initialization")
        except Exception as e:
            print(f"Error in collector thread: {e}")
            # Signal back to the UI thread that we had an error
            self.master.after(0, lambda: self.canvas.itemconfig(self.circle_id, fill="red"))
    
    def _prompt_for_password(self):
        """Prompt for password on the main thread and initialize collector"""
        try:
            # Initialize KeePass database first
            keepass_initialized = self.keepass_dialog.init_database()
            
            if not keepass_initialized:
                # User may have cancelled, but we can still proceed with simple password
                password = simpledialog.askstring("Password", 
                                                "Enter encryption password:", 
                                                show='*',
                                                parent=self.master)  # Main control window
                
                if not password:
                    self.canvas.itemconfig(self.circle_id, fill="red")
                    self.is_loading = False
                    print("Password entry cancelled")
                    return
            else:
                # Use master password from KeePass as encryption password
                # This is a convenience so users only need to remember one password
                password = simpledialog.askstring("Confirm", 
                                                "Re-enter your master password for data encryption:", 
                                                show='*',
                                                parent=self.master)
                
                if not password:
                    self.canvas.itemconfig(self.circle_id, fill="red")
                    self.is_loading = False
                    print("Password confirmation cancelled")
                    return

            print("Initializing collector with password...")
            self.collector = SimpleCollector(password)
            
            # If KeePass is initialized, add all passwords to sanitization
            if keepass_initialized:
                passwords = self.keepass_dialog.get_all_passwords()
                for pwd in passwords:
                    self.collector.add_password(pwd)
                print(f"Added {len(passwords)} passwords for sanitization")
            
            # Now toggle again to start the collection
            self.toggle_state(None)
        except Exception as e:
            print(f"Error in password prompt: {e}")
            self.canvas.itemconfig(self.circle_id, fill="red")
            self.is_loading = False

    def set_loading_state(self):
        """
        Force the circle to appear blue to indicate a 'loading' or 'pending' state.
        This does not toggle self.is_running, but sets a separate flag 'is_loading'.
        """
        self.is_loading = True
        self.canvas.itemconfig(self.circle_id, fill="blue")

    def start_move(self, event):
        """Remember the click position so we can move the dot window."""
        self._x = event.x
        self._y = event.y

    def do_move(self, event):
        """Reposition the dot window based on mouse movement."""
        dx = event.x - self._x
        dy = event.y - self._y
        x0 = self.master.winfo_x() + dx
        y0 = self.master.winfo_y() + dy
        self.master.geometry(f"+{x0}+{y0}")
        
    def on_master_close(self):
        """Handle window closing - ensure both windows close."""
        try:
            # Stop data collection if running
            if self.collector and self.is_running:
                self.collector.stop()
            # Shutdown completely
            if self.collector:
                self.collector.shutdown()
            # Destroy both windows
            self.control_window.destroy()
            self.master.destroy()
        except Exception as e:
            print(f"Error during shutdown: {e}")
            # Force destroy if there's an error
            try:
                self.control_window.destroy()
                self.master.destroy()
            except:
                pass

    def _save_prompt_to_log(self, prompt_txt):
        ts = time.strftime("%Y‑%m‑%d %H:%M:%S")
        with open("session_prompts.log", "a", encoding="utf‑8") as f:
            f.write(f"{ts}  {prompt_txt}\n")


def run_app():
    # Create the small dot indicator as the main window
    root = tk.Tk()
    root.overrideredirect(True)
    root.attributes('-topmost', True)
    root.configure(bg="#2C2C2C")
    root.geometry("50x50+0+0")  # Position will be adjusted by DisplayWidget
    
    # Initialize our display widget which will create the control window
    global collector  # Use the collector we started before the UI
    app = DisplayWidget(root)
    app.collector = collector  # Connect the pre-initialized collector
    app.is_running = False  # Start in inactive state
    
    # Configure control window layout
    for idx, weight in ((0,0),   # title row
                        (1,0),   # status row
                        (2,0),   # "Describe this session:" label
                        (3,1),   # text area – can stretch
                        (4,0),   # Manage Passwords button
                        (5,0),   # Find Sensitive Data button
                        (6,0)):  # Sanitize Logs button
        app.control_window.rowconfigure(idx, weight=weight)
    
    # Configure grid layout for control window
    app.control_window.columnconfigure(0, weight=1)

    # App title
    title_label = tk.Label(
        app.control_window,
        text="Visual Data Mining",
        font=("Helvetica", 14, "bold"),
        fg="white",
        bg="#2C2C2C"
    )
    title_label.grid(row=0, column=0, padx=10, pady=5, sticky="ew")

    # Status label
    status_label = tk.Label(
        app.control_window,
        text="Status: Not Running",  # Start with inactive status
        font=("Helvetica", 10),
        fg="white",
        bg="#2C2C2C"
    )
    status_label.grid(row=1, column=0, padx=10, pady=5, sticky="ew")

    # Sync button
    # sync_button = tk.Button(
    #     root,
    #     text="Sync Data",
    #     font=("Helvetica", 12, "bold"),
    #     fg="white",
    #     bg="#444444",
    #     relief="flat",
    #     command=lambda: sync_files(sync_button, app)
    # )
    # sync_button.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")

    # --- Session‑prompt label ---
    prompt_label = tk.Label(
        app.control_window,
        text="Describe this session:",
        font=("Helvetica", 10, "bold"),
        fg="white",
        bg="#2C2C2C"
    )
    prompt_label.grid(row=2, column=0, padx=10, pady=(10, 1), sticky="w")

    # --- Text area ---------------------------------------------------
    prompt_text = tk.Text(
        app.control_window,
        font=("Helvetica", 10),
        bg="#3A3A3A",
        fg="white",
        insertbackground="white",   # caret visible on dark bg
        relief="flat",
        height=4,                   # roughly 4 lines tall
        wrap="word"                 # wrap at word boundaries
    )
    prompt_text.grid(row=3, column=0, padx=10, pady=6, sticky="nsew")

    app.prompt_widget = prompt_text

    # Manage Passwords button
    manage_pwd_button = tk.Button(
        app.control_window,
        text="Manage Passwords",
        font=("Helvetica", 12, "bold"),
        command=lambda: view_passwords(app)
    )
    manage_pwd_button.grid(row=4, column=0, padx=10, pady=(10, 5), sticky="nsew")
    
    # Find Sensitive Data button (find only)
    find_button = tk.Button(
        app.control_window,
        text="Find Sensitive Data",
        font=("Helvetica", 12, "bold"),
        command=lambda: find_sensitive_data(app)
    )
    find_button.grid(row=5, column=0, padx=10, pady=5, sticky="nsew")
    
    # Sanitize Logs button (find and replace)
    sanitize_button = tk.Button(
        app.control_window,
        text="Sanitize Logs",
        font=("Helvetica", 12, "bold"),
        command=lambda: sanitize_sensitive_data(app)
    )
    sanitize_button.grid(row=6, column=0, padx=10, pady=(5, 10), sticky="nsew")

    # Set the initial state to not running (red)
    app.canvas.itemconfig(app.circle_id, fill="red")

    # Update status periodically
    def update_status():
        try:
            if app.is_saving_prompt:
                status_label.config(text="Status: Saving Prompt...")
            elif app.is_running:
                status_label.config(text="Status: Running")
            elif app.is_loading:
                status_label.config(text="Status: Loading...")
            else:
                status_label.config(text="Status: Not Running")
            
            # Set up the next update if not destroyed
            if root.winfo_exists():
                root.after(500, update_status)
        except Exception as e:
            print(f"Error updating status: {e}")
    
    # The DisplayWidget class now handles window closing via on_master_close
    
    # Initial status update and start event loop
    update_status()
    
    # Start the application
    print("GUI initialized and ready")
    try:
        root.mainloop()
    except Exception as e:
        print(f"Error in main loop: {e}")
        # Try to clean up if an error occurs
        if app.collector:
            try:
                app.collector.stop()
            except:
                pass

def add_password(app):
    """Add a password to sanitization using PyKeePass"""
    try:
        # Use the KeePass dialog to add a password
        if app.keepass_dialog.add_password():
            # If a collector is active, also add all passwords from KeePass to it
            if app.collector is not None:
                passwords = app.keepass_dialog.get_all_passwords()
                for pwd in passwords:
                    app.collector.add_password(pwd)
                print(f"Added {len(passwords)} passwords for sanitization")
            return True
        return False
    except Exception as e:
        messagebox.showerror("Error", f"Failed to add password: {e}")
        print(f"Error adding password: {e}")
        return False

def view_passwords(app):
    """Show the password viewer dialog"""
    try:
        # Create a password viewer with the app's KeePass manager
        viewer = PasswordViewer(app.master, app.keepass_dialog.keepass_manager)
        viewer.show_dialog()
        
        # If collection is active, update with any new passwords
        if app.collector is not None:
            passwords = app.keepass_dialog.get_all_passwords()
            for pwd in passwords:
                app.collector.add_password(pwd)
            print(f"Updated collector with {len(passwords)} passwords")
            
    except Exception as e:
        messagebox.showerror("Error", f"Failed to open password viewer: {e}")
        print(f"Error opening password viewer: {e}")

def find_sensitive_data(app):
    """Find sensitive data in log files without modifying them"""
    try:
        # Initialize KeePass database if needed
        if not app.keepass_dialog.keepass_manager.kp:
            result = app.keepass_dialog.init_database()
            if not result:
                messagebox.showerror(
                    "Error", 
                    "Cannot find sensitive data without access to password database", 
                    parent=app.master
                )
                return
        
        # Create retroactive sanitizer
        sanitizer = RetroactiveSanitizer(app.keepass_dialog.keepass_manager)
        
        # Find occurrences
        app.master.config(cursor="watch")  # Show busy cursor
        app.master.update()
        
        occurrences = sanitizer.find_occurrences()
        
        app.master.config(cursor="")  # Reset cursor
        
        if not occurrences:
            messagebox.showinfo(
                "Find Result",
                "No sensitive data found in log files",
                parent=app.master
            )
            return
        
        # Show results
        total_matches = sum(occurrences.values())
        result_message = f"Found {total_matches} potential password occurrences in {len(occurrences)} files:\n\n"
        
        for file, count in occurrences.items():
            result_message += f"{file}: {count} occurrences\n"
        
        messagebox.showinfo(
            "Find Result",
            result_message,
            parent=app.master
        )
        
    except Exception as e:
        app.master.config(cursor="")  # Reset cursor if error
        messagebox.showerror("Error", f"Failed to find sensitive data: {e}")
        print(f"Error finding sensitive data: {e}")

def sanitize_sensitive_data(app):
    """Sanitize sensitive data in log files by replacing with [REDACTED]"""
    try:
        # Initialize KeePass database if needed
        if not app.keepass_dialog.keepass_manager.kp:
            result = app.keepass_dialog.init_database()
            if not result:
                messagebox.showerror(
                    "Error", 
                    "Cannot sanitize logs without access to password database", 
                    parent=app.master
                )
                return
        
        # Create retroactive sanitizer
        sanitizer = RetroactiveSanitizer(app.keepass_dialog.keepass_manager)
        
        # Find occurrences first
        app.master.config(cursor="watch")  # Show busy cursor
        app.master.update()
        
        occurrences = sanitizer.find_occurrences()
        
        if not occurrences:
            app.master.config(cursor="")  # Reset cursor
            messagebox.showinfo(
                "Sanitize Result",
                "No sensitive data found in log files",
                parent=app.master
            )
            return
        
        # Show results and ask for confirmation
        total_matches = sum(occurrences.values())
        confirm_message = f"Found {total_matches} potential password occurrences in {len(occurrences)} files:\n\n"
        
        for file, count in occurrences.items():
            confirm_message += f"{file}: {count} occurrences\n"
            
        confirm_message += "\nDo you want to sanitize these files?"
        
        confirm = messagebox.askyesno(
            "Confirm Sanitization",
            confirm_message,
            parent=app.master
        )
        
        if not confirm:
            app.master.config(cursor="")  # Reset cursor
            return
        
        # Perform sanitization
        replacements = sanitizer.sanitize_logs()
        
        app.master.config(cursor="")  # Reset cursor
        
        # Show results
        total_replaced = sum(replacements.values())
        result_message = f"Sanitized {total_replaced} occurrences in {len(replacements)} files"
        
        messagebox.showinfo(
            "Sanitize Result",
            result_message,
            parent=app.master
        )
        
    except Exception as e:
        app.master.config(cursor="")  # Reset cursor if error
        messagebox.showerror("Error", f"Failed to sanitize logs: {e}")
        print(f"Error sanitizing logs: {e}")

# def sync_files(button, app=None):
#     """Sync collected data files to remote server"""
#     was_running = False
    
#     # If collection is running and app is provided, stop collection first
#     if app and app.is_running:
#         print("Pausing data collection for sync...")
#         was_running = True
#         # Store original button appearance
#         original_fill = app.canvas.itemcget(app.circle_id, "fill")
        
#         # Stop the collector
#         if app.collector:
#             app.collector.stop()
#             app.is_running = False
    
#     # Paths based on SimpleCollector's defaults
#     source_dir = os.path.join(os.getcwd(), 'logs')
#     if not os.path.exists(source_dir):
#         print(f"Creating directory: {source_dir}")
#         os.makedirs(source_dir, exist_ok=True)
        
#     # Define remote destination with username-specific folder
#     # Get current username for personalized upload folder
#     try:
#         username = sp.check_output(['whoami'], text=True).strip()
#         remote_destination = f'data_uploader:/data/uploads/{username}'
#         print(f"Using upload destination: {remote_destination}")
#     except Exception as e:
#         print(f"Error getting username: {e}")
#         # Fallback to generic name if username can't be determined
#         remote_destination = 'data_uploader:/data/uploads/unknown_user'
    
#     # Update UI to show syncing state
#     button.config(text="Syncing...", state="disabled")
#     if app:
#         app.canvas.itemconfig(app.circle_id, fill="orange")  # Orange during sync
    
#     command = [
#         'rsync',
#         '-avz',
#         '--checksum',
#         '--remove-source-files',
#         '--partial-dir=.rsync-partial',
#         '--compress-level=9',
#         '--timeout=5',
#         source_dir,
#         remote_destination
#     ]

#     try:
#         print(f"Running sync command: {' '.join(command)}")
#         process = sp.Popen(command, stdout=sp.PIPE, stderr=sp.PIPE, text=True)

#         # Real-time output
#         for line in iter(process.stdout.readline, ''):
#             line = line.strip()
#             if line:
#                 print(f"Syncing: {line}")
#                 button.config(text=f"{line[:20]}...")

#         process.stdout.close()
#         return_code = process.wait()

#         if return_code == 0:
#             button.config(text="Sync Successful")
#             print("Data sync completed successfully")
#         else:
#             stderr_output = process.stderr.read().strip()
#             print(f"Error during sync: {stderr_output}")
#             button.config(text="Sync Failed")
            
#             # Show error in message box if critical
#             if stderr_output and 'error' in stderr_output.lower():
#                 messagebox.showerror("Sync Error", f"Failed to sync: {stderr_output[:100]}")

#     except Exception as e:
#         print(f"Unexpected error during sync: {e}")
#         button.config(text="Error!")
#         messagebox.showerror("Sync Error", f"Failed to sync: {str(e)}")

#     finally:
#         # Reset button after delay
#         button.after(3000, lambda: button.config(text="Sync Data", state="normal"))
        
#         # Restart collection if it was running before
#         if app and was_running:
#             def restart_collection():
#                 # Reset circle to appropriate state based on collection status
#                 if app.is_running:
#                     app.canvas.itemconfig(app.circle_id, fill="green")
#                 else:
#                     # Need to restart collection
#                     app.toggle_state(None)
                    
#             # Schedule restart after button reset
#             button.after(3500, restart_collection)

def run_tkinter_in_thread():
    """Run the Tkinter main loop in its own dedicated thread."""
    try:
        print("Starting Tkinter in dedicated thread...")
        # Create the small dot indicator as the main window
        root = tk.Tk()
        root.overrideredirect(True)
        root.attributes('-topmost', True)
        root.configure(bg="#2C2C2C")
        root.geometry("50x50+0+0")  # Position will be adjusted by DisplayWidget

        # Create the display widget which will create the control window
        app = DisplayWidget(root)
        
        # Configure grid layout for control window
        app.control_window.columnconfigure(0, weight=1)
        for idx, weight in ((0,0), (1,0), (2,0), (3,1), (4,0), (5,0), (6,0)):
            app.control_window.rowconfigure(idx, weight=weight)
        
        # App title
        title_label = tk.Label(
            app.control_window,
            text="Visual Data Mining",
            font=("Helvetica", 14, "bold"),
            fg="white",
            bg="#2C2C2C"
        )
        title_label.grid(row=0, column=0, padx=10, pady=5, sticky="ew")
        
        # Status label
        status_label = tk.Label(
            app.control_window,
            text="Status: Not Running",
            font=("Helvetica", 10),
            fg="white",
            bg="#2C2C2C"
        )
        status_label.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        
        # Sync button
        # sync_button = tk.Button(
        #     root,
        #     text="Sync Data",
        #     font=("Helvetica", 12, "bold"),
        #     fg="white",
        #     bg="#444444",
        #     relief="flat",
        #     command=lambda: sync_files(sync_button, app)
        # )
        # sync_button.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")

        # --- Session‑prompt label ---
        prompt_label = tk.Label(
            app.control_window,
            text="Describe this session:",
            font=("Helvetica", 10, "bold"),
            fg="white",
            bg="#2C2C2C"
        )
        prompt_label.grid(row=2, column=0, padx=10, pady=(10, 1), sticky="w")

        # --- Text area ---------------------------------------------------
        prompt_text = tk.Text(
            app.control_window,
            font=("Helvetica", 10),
            bg="#3A3A3A",
            fg="white",
            insertbackground="white",   # caret visible on dark bg
            relief="flat",
            height=4,                   # roughly 4 lines tall
            wrap="word"                 # wrap at word boundaries
        )
        prompt_text.grid(row=3, column=0, padx=10, pady=6, sticky="nsew")

        app.prompt_widget = prompt_text 
        
        # Add password button
        add_pwd_button = tk.Button(
            app.control_window,
            text="Add Password",
            font=("Helvetica", 12, "bold"),
            command=lambda: add_password(app)
        )
        add_pwd_button.grid(row=4, column=0, padx=10, pady=10, sticky="nsew")
        
        # Update status periodically
        def update_status():
            try:
                if app.is_saving_prompt:
                    status_label.config(text="Status: Saving Prompt...")
                elif app.is_running:
                    status_label.config(text="Status: Running")
                elif app.is_loading:
                    status_label.config(text="Status: Loading...")
                else:
                    status_label.config(text="Status: Not Running")
                
                # Set up the next update if not destroyed
                if root.winfo_exists():
                    root.after(500, update_status)
            except Exception as e:
                print(f"Error updating status: {e}")
        
        # The DisplayWidget class handles window closing via on_master_close
        
        # Initial status update
        update_status()
        
        print("Tkinter thread: GUI initialized and ready")
        root.mainloop()
        print("Tkinter main loop has exited")
    
    except Exception as e:
        print(f"Critical error in Tkinter thread: {e}")

if __name__ == "__main__":
    print("Main thread starting")
    
    # Initialize collector and listeners first, before Tkinter
    print("Setting up data collection components first...")
    
    # Create SimpleCollector with a fixed password for initial startup
    # This avoids needing a Tkinter dialog for password
    initial_password = "startup_password"
    collector = SimpleCollector(initial_password)
    
    # Start recording components but keep them inactive
    print("Initializing recording components in inactive state...")
    
    # Start all components in inactive state
    
    # Start the keystroke recorder but don't activate event processing
    collector.keystroke_recorder.start() 
    print("Keyboard listener initialized but not active")
    
    # Initialize screen recorder but don't start capturing
    collector.screen_recorder.start()
    print("Screen recorder initialized but not capturing")
    
    # Now start Tkinter with inactive collectors
    print("Now initializing Tkinter GUI...")
    run_app()  # This runs the Tkinter initialization with our pre-initialized collector
