import tkinter as tk
import tkinter.messagebox as messagebox
import tkinter.simpledialog as simpledialog
import subprocess as sp
import os
import glob
import threading
import time

from simple_collector import SimpleCollector

class DisplayWidget:
    def __init__(self, master, collector=None):
        self.master = master
        self.master.title("Data Collection Control")
        
        # Create a separate top-level window for the dot indicator
        self.dot_window = tk.Toplevel(master)
        self.dot_window.title("Indicator")
        self.dot_window.overrideredirect(True)
        self.dot_window.attributes('-topmost', True)
        
        # Dark background color for the dot window
        self.dot_window.configure(bg="#2C2C2C")
        
        # Position the dot window at bottom-right corner
        screen_width = self.dot_window.winfo_screenwidth()
        screen_height = self.dot_window.winfo_screenheight()
        window_width, window_height = 50, 50
        x = screen_width - window_width - 10
        y = screen_height - window_height - 50
        self.dot_window.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # Data collector integration
        self.collector = collector
        
        # Track states
        self.is_running = False
        self.is_loading = False
        
        # Create a canvas to hold the circle (in the dot window)
        self.canvas = tk.Canvas(
            self.dot_window, 
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
        self.dot_window.bind("<ButtonPress-1>", self.start_move)
        self.dot_window.bind("<B1-Motion>", self.do_move)
        
        # Connect the windows - closing main window will close dot window
        self.master.protocol("WM_DELETE_WINDOW", self.on_master_close)

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
                    # Update UI on main thread
                    self.master.after(0, lambda: self.canvas.itemconfig(self.circle_id, fill="red"))
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
            # Use main window as parent for the dialog, not the dot window
            password = simpledialog.askstring("Password", 
                                            "Enter encryption password:", 
                                            show='*',
                                            parent=self.master)  # Main control window
            
            if not password:
                self.canvas.itemconfig(self.circle_id, fill="red")
                self.is_loading = False
                print("Password entry cancelled")
                return

            print("Initializing collector with password...")
            self.collector = SimpleCollector(password)
            
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
        x0 = self.dot_window.winfo_x() + dx
        y0 = self.dot_window.winfo_y() + dy
        self.dot_window.geometry(f"+{x0}+{y0}")
        
    def on_master_close(self):
        """Handle main window closing - ensure both windows close."""
        try:
            # Stop data collection if running
            if self.collector and self.is_running:
                self.collector.stop()
            # Shutdown completely
            if self.collector:
                self.collector.shutdown()
            # Destroy both windows
            self.dot_window.destroy()
            self.master.destroy()
        except Exception as e:
            print(f"Error during shutdown: {e}")
            # Force destroy if there's an error
            try:
                self.dot_window.destroy()
                self.master.destroy()
            except:
                pass

def run_app():
    # Create the main window with a title bar that can be minimized
    root = tk.Tk()
    root.title("Visual Data Mining Control")
    root.geometry("300x220+100+100")
    root.configure(bg="#2C2C2C")
    
    # Initialize the display widget with our pre-initialized but inactive collector
    global collector  # Use the collector we started before the UI
    app = DisplayWidget(root)
    app.collector = collector  # Connect the pre-initialized collector
    app.is_running = False  # Start in inactive state
    
    # Configure grid layout for main window
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)
    root.rowconfigure(1, weight=1)
    root.rowconfigure(2, weight=1)
    root.rowconfigure(3, weight=1)

    # App title
    title_label = tk.Label(
        root,
        text="Visual Data Mining",
        font=("Helvetica", 14, "bold"),
        fg="white",
        bg="#2C2C2C"
    )
    title_label.grid(row=0, column=0, padx=10, pady=5, sticky="ew")

    # Status label
    status_label = tk.Label(
        root,
        text="Status: Not Running",  # Start with inactive status
        font=("Helvetica", 10),
        fg="white",
        bg="#2C2C2C"
    )
    status_label.grid(row=1, column=0, padx=10, pady=5, sticky="ew")

    # Sync button
    sync_button = tk.Button(
        root,
        text="Sync Data",
        font=("Helvetica", 12, "bold"),
        fg="white",
        bg="#444444",
        relief="flat",
        command=lambda: sync_files(sync_button, app)
    )
    sync_button.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")

    # Add password button
    add_pwd_button = tk.Button(
        root,
        text="Add Password",
        font=("Helvetica", 12, "bold"),
        fg="white",
        bg="#444444",
        relief="flat",
        command=lambda: add_password(app)
    )
    add_pwd_button.grid(row=3, column=0, padx=10, pady=10, sticky="nsew")

    # Set the initial state to not running (red)
    app.canvas.itemconfig(app.circle_id, fill="red")

    # Update status periodically
    def update_status():
        try:
            if app.is_running:
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
    
    # Set up additional window close handler for the main window
    # (DisplayWidget already has a handler for the root window)
    def on_dot_close():
        try:
            print("Dot window closed, shutting down application...")
            if app.collector:
                print("Performing full shutdown of data collectors...")
                if app.is_running:
                    # Stop recording first if it's running
                    app.collector.stop()
                # Then do a full shutdown of listeners
                app.collector.shutdown()
            root.destroy()
        except Exception as e:
            print(f"Error during shutdown: {e}")
            root.destroy()
    
    # Set close handler for the dot window
    app.dot_window.protocol("WM_DELETE_WINDOW", on_dot_close)
    
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
    """Add a password to the collector for sanitization"""
    if app.collector is None:
        messagebox.showerror("Error", "Data collector not initialized. Start collection first.")
        return

    # Use the main window as parent for the dialog
    password = simpledialog.askstring("Add Password", 
                                     "Enter password to sanitize:", 
                                     show='*',
                                     parent=app.master)  # master is the main control window
    if password:
        try:
            app.collector.add_password(password)
            messagebox.showinfo("Success", "Password added successfully")
            print(f"Added password for sanitization (length: {len(password)})")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to add password: {e}")
            print(f"Error adding password: {e}")

def sync_files(button, app=None):
    """Sync collected data files to remote server"""
    was_running = False
    
    # If collection is running and app is provided, stop collection first
    if app and app.is_running:
        print("Pausing data collection for sync...")
        was_running = True
        # Store original button appearance
        original_fill = app.canvas.itemcget(app.circle_id, "fill")
        
        # Stop the collector
        if app.collector:
            app.collector.stop()
            app.is_running = False
    
    # Paths based on SimpleCollector's defaults
    source_dir = os.path.join(os.getcwd(), 'logs')
    if not os.path.exists(source_dir):
        print(f"Creating directory: {source_dir}")
        os.makedirs(source_dir, exist_ok=True)
        
    # Define remote destination with username-specific folder
    # Get current username for personalized upload folder
    try:
        username = sp.check_output(['whoami'], text=True).strip()
        remote_destination = f'data_uploader:/data/uploads/{username}'
        print(f"Using upload destination: {remote_destination}")
    except Exception as e:
        print(f"Error getting username: {e}")
        # Fallback to generic name if username can't be determined
        remote_destination = 'data_uploader:/data/uploads/unknown_user'
    
    # Update UI to show syncing state
    button.config(text="Syncing...", state="disabled")
    if app:
        app.canvas.itemconfig(app.circle_id, fill="orange")  # Orange during sync
    
    command = [
        'rsync',
        '-avz',
        '--checksum',
        '--remove-source-files',
        '--partial-dir=.rsync-partial',
        '--compress-level=9',
        '--timeout=5',
        source_dir,
        remote_destination
    ]

    try:
        print(f"Running sync command: {' '.join(command)}")
        process = sp.Popen(command, stdout=sp.PIPE, stderr=sp.PIPE, text=True)

        # Real-time output
        for line in iter(process.stdout.readline, ''):
            line = line.strip()
            if line:
                print(f"Syncing: {line}")
                button.config(text=f"{line[:20]}...")

        process.stdout.close()
        return_code = process.wait()

        if return_code == 0:
            button.config(text="Sync Successful")
            print("Data sync completed successfully")
        else:
            stderr_output = process.stderr.read().strip()
            print(f"Error during sync: {stderr_output}")
            button.config(text="Sync Failed")
            
            # Show error in message box if critical
            if stderr_output and 'error' in stderr_output.lower():
                messagebox.showerror("Sync Error", f"Failed to sync: {stderr_output[:100]}")

    except Exception as e:
        print(f"Unexpected error during sync: {e}")
        button.config(text="Error!")
        messagebox.showerror("Sync Error", f"Failed to sync: {str(e)}")

    finally:
        # Reset button after delay
        button.after(3000, lambda: button.config(text="Sync Data", state="normal"))
        
        # Restart collection if it was running before
        if app and was_running:
            def restart_collection():
                # Reset circle to appropriate state based on collection status
                if app.is_running:
                    app.canvas.itemconfig(app.circle_id, fill="green")
                else:
                    # Need to restart collection
                    app.toggle_state(None)
                    
            # Schedule restart after button reset
            button.after(3500, restart_collection)

def run_tkinter_in_thread():
    """Run the Tkinter main loop in its own dedicated thread."""
    try:
        print("Starting Tkinter in dedicated thread...")
        # Create and configure the main GUI window with standard decorations
        root = tk.Tk()
        root.title("Visual Data Mining Control")
        root.geometry("300x220+100+100")
        root.configure(bg="#2C2C2C")
        
        # Create the display widget with separate dot indicator
        app = DisplayWidget(root)
        
        # Configure grid layout for main window
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        root.rowconfigure(1, weight=1)
        root.rowconfigure(2, weight=1)
        root.rowconfigure(3, weight=1)
        
        # App title
        title_label = tk.Label(
            root,
            text="Visual Data Mining",
            font=("Helvetica", 14, "bold"),
            fg="white",
            bg="#2C2C2C"
        )
        title_label.grid(row=0, column=0, padx=10, pady=5, sticky="ew")
        
        # Status label
        status_label = tk.Label(
            root,
            text="Status: Not Running",
            font=("Helvetica", 10),
            fg="white",
            bg="#2C2C2C"
        )
        status_label.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        
        # Sync button
        sync_button = tk.Button(
            root,
            text="Sync Data",
            font=("Helvetica", 12, "bold"),
            fg="white",
            bg="#444444",
            relief="flat",
            command=lambda: sync_files(sync_button, app)
        )
        sync_button.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")
        
        # Add password button
        add_pwd_button = tk.Button(
            root,
            text="Add Password",
            font=("Helvetica", 12, "bold"),
            fg="white",
            bg="#444444",
            relief="flat",
            command=lambda: add_password(app)
        )
        add_pwd_button.grid(row=3, column=0, padx=10, pady=10, sticky="nsew")
        
        # Update status periodically
        def update_status():
            try:
                if app.is_running:
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
        
        # Set up additional window close handler for the dot window
        def on_dot_close():
            try:
                print("Dot window closed, shutting down application...")
                if app.collector and app.is_running:
                    app.collector.stop()
                root.destroy()
            except Exception as e:
                print(f"Error during shutdown: {e}")
                root.destroy()
        
        # Set handlers for window closing
        app.dot_window.protocol("WM_DELETE_WINDOW", on_dot_close)
        
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
