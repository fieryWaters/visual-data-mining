#!/usr/bin/env python3
"""
Data Player - A movie player for visualizing screen recordings with keystroke data.
"""

import os
import json
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk
import time
from datetime import datetime
import threading
import glob
import re
from utils.text_buffer import TextBuffer


class ModifierKeysWidget(ttk.Frame):
    """
    Widget to display the state of modifier keys.
    """
    
    def __init__(self, master, **kwargs):
        """Initialize the modifier keys widget."""
        super().__init__(master, **kwargs)
        
        # Define modifier keys to track - all variants map to a single display name
        self.modifiers = {
            'Key.shift': 'SHIFT',
            'Key.shift_l': 'SHIFT',
            'Key.shift_r': 'SHIFT',
            
            'Key.ctrl': 'CTRL',
            'Key.ctrl_l': 'CTRL',
            'Key.ctrl_r': 'CTRL',
            
            'Key.alt': 'ALT',
            'Key.alt_l': 'ALT',
            'Key.alt_r': 'ALT',
            
            'Key.cmd': 'CMD',
            'Key.cmd_l': 'CMD',
            'Key.cmd_r': 'CMD',
            
            'Key.caps_lock': 'CAPS',
            'Key.tab': 'TAB',
        }
        
        # List of unique modifier display names
        display_names = ['SHIFT', 'CTRL', 'ALT', 'CMD', 'CAPS', 'TAB']
        
        # Create indicator labels
        self.indicators = {}
        
        # Use a horizontal layout
        for i, display_name in enumerate(display_names):
            # Create indicator frame with border
            indicator = ttk.Frame(self, borderwidth=2, relief=tk.GROOVE, width=50, height=30)
            indicator.grid(row=0, column=i, padx=5, pady=5)
            indicator.grid_propagate(False)  # Keep fixed size
            
            # Add label inside frame
            label = ttk.Label(
                indicator, 
                text=display_name,
                anchor=tk.CENTER,
                background="#d3d3d3"  # Light gray (inactive state)
            )
            label.pack(fill=tk.BOTH, expand=True)
            
            # Store the label reference
            self.indicators[display_name] = label
        
        # Current state of modifiers (counts for each modifier)
        self.active_counts = {name: 0 for name in display_names}
    
    def update_modifier(self, key, is_pressed):
        """Update the state of a modifier key."""
        if key in self.modifiers:
            display_name = self.modifiers[key]
            
            if is_pressed:
                # Increment counter for this modifier
                self.active_counts[display_name] += 1
                # Activate the indicator if count is positive
                if self.active_counts[display_name] > 0:
                    self.indicators[display_name].configure(background="#4caf50")  # Green for active
            else:
                # Decrement counter, but don't go below zero
                if self.active_counts[display_name] > 0:
                    self.active_counts[display_name] -= 1
                # Deactivate if count reaches zero
                if self.active_counts[display_name] == 0:
                    self.indicators[display_name].configure(background="#d3d3d3")  # Gray for inactive
    
    def clear_all(self):
        """Reset all modifiers to inactive state."""
        for display_name in self.active_counts:
            self.active_counts[display_name] = 0
            self.indicators[display_name].configure(background="#d3d3d3")  # Gray for inactive


class DataPlayer:
    """
    Movie player for visualizing screen recordings with keystroke data.
    """

    def __init__(self, master, logs_dir=None):
        """
        Initialize the data player.
        
        Args:
            master: The Tkinter root window
            logs_dir: Directory containing logs (screenshots and sanitized keystrokes)
        """
        self.master = master
        self.master.title("Data Mining Player")
        self.master.geometry("1200x800")
        self.master.minsize(800, 600)
        
        # Set data directory
        self.logs_dir = logs_dir or os.path.join(os.getcwd(), 'logs')
        self.screenshots_dir = os.path.join(self.logs_dir, 'screenshots')
        self.sanitized_dir = os.path.join(self.logs_dir, 'sanitized_json')
        
        # Player state
        self.playing = False
        self.current_time = None
        self.play_thread = None
        self.stop_playback = threading.Event()
        
        # Data containers
        self.screenshots = {}  # Dictionary of timestamp -> filepath
        self.screenshot_times = []  # Ordered list of timestamps
        self.keystroke_data = []  # List of (timestamp, event) tuples
        
        # Create UI
        self.create_ui()
        
        # Text buffer for processing keystrokes
        self.text_buffer = TextBuffer()
        
        # Load data if directories exist
        if os.path.exists(self.screenshots_dir) and os.path.exists(self.sanitized_dir):
            self.load_data()
        else:
            self.text_display.insert(tk.END, "Data directories not found. Please select a logs directory.")
    
    def create_ui(self):
        """Create the user interface."""
        # Main frame
        main_frame = ttk.Frame(self.master)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Top controls section
        controls_frame = ttk.Frame(main_frame)
        controls_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Directory selection
        ttk.Label(controls_frame, text="Logs Directory:").pack(side=tk.LEFT, padx=5)
        self.dir_entry = ttk.Entry(controls_frame, width=50)
        self.dir_entry.insert(0, self.logs_dir)
        self.dir_entry.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            controls_frame, 
            text="Browse", 
            command=self.browse_directory
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            controls_frame, 
            text="Load", 
            command=self.load_data
        ).pack(side=tk.LEFT, padx=5)
        
        # Middle section - split between image and status
        middle_frame = ttk.Frame(main_frame)
        middle_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Image display (largest component)
        self.image_frame = ttk.Frame(middle_frame, borderwidth=2, relief=tk.GROOVE)
        self.image_frame.pack(fill=tk.BOTH, expand=True, side=tk.TOP, padx=5, pady=5)
        
        # Canvas for image display
        self.canvas = tk.Canvas(self.image_frame, bg="black")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Keystroke display
        self.text_frame = ttk.Frame(middle_frame, height=150)
        self.text_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=5, pady=5)
        self.text_frame.pack_propagate(False)  # Prevent frame from shrinking
        
        # Create a sub-frame for modifier keys display
        modifier_frame = ttk.Frame(self.text_frame)
        modifier_frame.pack(fill=tk.X, side=tk.TOP, padx=5, pady=5)
        
        # Add modifier keys widget
        self.modifier_keys = ModifierKeysWidget(modifier_frame)
        self.modifier_keys.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        # Scrolled text widget for keystroke display
        self.text_display = tk.Text(
            self.text_frame, 
            height=7,  # Reduced height to make room for modifier keys
            wrap=tk.WORD, 
            bg="#f0f0f0",
            font=("Courier", 12)
        )
        self.text_scrollbar = ttk.Scrollbar(self.text_frame, command=self.text_display.yview)
        self.text_display.configure(yscrollcommand=self.text_scrollbar.set)
        
        self.text_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.text_display.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Bottom controls
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=5, pady=5)
        
        # Current time display
        self.time_var = tk.StringVar(value="00:00:00.000")
        time_label = ttk.Label(
            bottom_frame,
            textvariable=self.time_var,
            font=("Courier", 12)
        )
        time_label.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Playback controls
        self.play_btn = ttk.Button(
            bottom_frame, 
            text="Play", 
            command=self.toggle_playback
        )
        self.play_btn.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        self.status_bar = ttk.Label(
            bottom_frame, 
            textvariable=self.status_var, 
            relief=tk.SUNKEN, 
            anchor=tk.W
        )
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM, padx=5, pady=5)
        
        # Bind window resize event to redraw the canvas image
        self.master.bind("<Configure>", self.on_resize)
    
    def browse_directory(self):
        """Open file dialog to select logs directory."""
        directory = filedialog.askdirectory(
            initialdir=os.path.dirname(self.logs_dir),
            title="Select Logs Directory"
        )
        if directory:
            self.logs_dir = directory
            self.screenshots_dir = os.path.join(directory, 'screenshots')
            self.sanitized_dir = os.path.join(directory, 'sanitized_json')
            self.dir_entry.delete(0, tk.END)
            self.dir_entry.insert(0, directory)
    
    def load_data(self):
        """Load screenshots and keystroke data."""
        self.status_var.set("Loading data...")
        self.master.update_idletasks()
        
        # Reset data
        self.screenshots = {}
        self.screenshot_times = []
        self.keystroke_data = []
        self.text_buffer = TextBuffer()
        
        # Update directories from entry field
        self.logs_dir = self.dir_entry.get()
        self.screenshots_dir = os.path.join(self.logs_dir, 'screenshots')
        self.sanitized_dir = os.path.join(self.logs_dir, 'sanitized_json')
        
        try:
            # Load screenshots
            screenshot_files = glob.glob(os.path.join(self.screenshots_dir, "*.jpg"))
            for filepath in screenshot_files:
                # Extract timestamp from filename
                # Example filename: screen_20250402_141928_296876.jpg
                match = re.search(r'screen_(\d{8})_(\d{6})_(\d+)\.jpg', os.path.basename(filepath))
                if match:
                    date_str = match.group(1)
                    time_str = match.group(2)
                    ms_str = match.group(3)
                    
                    # Format for ISO timestamp
                    year = date_str[:4]
                    month = date_str[4:6]
                    day = date_str[6:8]
                    hour = time_str[:2]
                    minute = time_str[2:4]
                    second = time_str[4:6]
                    ms = ms_str[:6].ljust(6, '0')
                    
                    timestamp = f"{year}-{month}-{day}T{hour}:{minute}:{second}.{ms}"
                    self.screenshots[timestamp] = filepath
            
            # Create sorted list of screenshot timestamps
            self.screenshot_times = sorted(self.screenshots.keys())
            
            # Load keystroke data
            json_files = glob.glob(os.path.join(self.sanitized_dir, "*.json"))
            for filepath in json_files:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                    for event in data.get('events', []):
                        timestamp = event.get('timestamp')
                        if timestamp:
                            self.keystroke_data.append((timestamp, event))
            
            # Sort keystrokes by timestamp
            self.keystroke_data.sort(key=lambda x: x[0])
            
            # Reset UI
            self.text_display.delete("1.0", tk.END)
            
            # Set current time to first screenshot if available
            if self.screenshot_times:
                self.current_time = self.screenshot_times[0]
                self.update_display(self.current_time)
                self.status_var.set(
                    f"Loaded {len(self.screenshots)} screenshots and {len(self.keystroke_data)} keystroke events"
                )
            else:
                self.status_var.set("No data found in selected directories")
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load data: {e}")
            self.status_var.set(f"Error: {e}")
    
    def update_display(self, current_time):
        """Update display to show content at the given timestamp."""
        if not current_time:
            return
        
        self.current_time = current_time
        
        # Find the most recent screenshot before current_time
        latest_screenshot = None
        for timestamp in self.screenshot_times:
            if timestamp <= current_time:
                latest_screenshot = self.screenshots[timestamp]
            else:
                break
        
        # Display the screenshot if found
        if latest_screenshot:
            try:
                img = Image.open(latest_screenshot)
                self.display_image(img)
                
                # Format timestamp as human-readable
                dt = datetime.fromisoformat(current_time)
                formatted_time = dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                self.time_var.set(formatted_time)
            except Exception as e:
                self.status_var.set(f"Error displaying image: {e}")
    
    def display_image(self, img):
        """Resize and display an image on the canvas."""
        # Get canvas size
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        # Skip if canvas not yet sized
        if canvas_width <= 1 or canvas_height <= 1:
            self.master.after(100, lambda: self.display_image(img))
            return
        
        # Calculate scaling to fit canvas while preserving aspect ratio
        img_width, img_height = img.size
        scale_width = canvas_width / img_width
        scale_height = canvas_height / img_height
        scale = min(scale_width, scale_height)
        
        # New dimensions
        new_width = int(img_width * scale)
        new_height = int(img_height * scale)
        
        # Resize image
        resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Convert to PhotoImage
        photo = ImageTk.PhotoImage(resized_img)
        
        # Clear canvas and display new image
        self.canvas.delete("all")
        self.canvas.create_image(
            canvas_width // 2, 
            canvas_height // 2,
            image=photo, 
            anchor=tk.CENTER
        )
        
        # Keep a reference to prevent garbage collection
        self.canvas.image = photo
    
    def on_resize(self, event=None):
        """Handle window resize events by redisplaying the current image."""
        # Only resize if we have a current timestamp
        if self.current_time:
            # Find most recent screenshot
            latest_screenshot = None
            for timestamp in self.screenshot_times:
                if timestamp <= self.current_time:
                    latest_screenshot = self.screenshots[timestamp]
                else:
                    break
            
            if latest_screenshot:
                img = Image.open(latest_screenshot)
                self.display_image(img)
    
    def update_text_display(self, events):
        """Update text display with processed keystroke events."""
        # Clear the text display
        self.text_display.delete("1.0", tk.END)
        
        # Reset all modifier keys
        self.modifier_keys.clear_all()
        
        # Process events to generate text
        for _, event in events:
            event_type = event.get('event')
            
            if event_type == 'KEY_PRESS':
                key = event.get('key', '')
                
                # Update modifier keys display for special keys
                if key.startswith('Key.'):
                    self.modifier_keys.update_modifier(key, True)
                
                # Process the key using TextBuffer's process_keystroke method
                self.text_buffer.process_keystroke(key, id(event))
            
            elif event_type == 'KEY_RELEASE':
                key = event.get('key', '')
                
                # Update modifier keys display for special keys
                if key.startswith('Key.'):
                    self.modifier_keys.update_modifier(key, False)
            
            # Handle password found events
            elif event_type == 'PASSWORD_FOUND':
                # Insert [REDACTED] text for password events
                self.text_buffer.process_keystroke('[', id(event))
                self.text_buffer.process_keystroke('R', id(event))
                self.text_buffer.process_keystroke('E', id(event))
                self.text_buffer.process_keystroke('D', id(event))
                self.text_buffer.process_keystroke('A', id(event))
                self.text_buffer.process_keystroke('C', id(event))
                self.text_buffer.process_keystroke('T', id(event))
                self.text_buffer.process_keystroke('E', id(event))
                self.text_buffer.process_keystroke('D', id(event))
                self.text_buffer.process_keystroke(']', id(event))
        
        # Display the current buffer text
        self.text_display.insert(tk.END, self.text_buffer.get_text())
        self.text_display.see(tk.END)
    
    def toggle_playback(self):
        """Toggle between play and pause."""
        if self.playing:
            self.stop_playback.set()
            self.playing = False
            self.play_btn.configure(text="Play")
            self.status_var.set("Paused")
        else:
            self.start_playback()
    
    def start_playback(self):
        """Start playback from current position."""
        if not self.screenshot_times:
            messagebox.showinfo("No Data", "No data loaded to play. Please select a logs directory.")
            return
        
        # Stop any existing playback
        self.stop_playback.set()
        if self.play_thread and self.play_thread.is_alive():
            self.play_thread.join(timeout=0.5)
        
        # Reset stop event
        self.stop_playback.clear()
        
        # Update UI
        self.playing = True
        self.play_btn.configure(text="Pause")
        
        # Set starting time if not already set
        if not self.current_time:
            self.current_time = self.screenshot_times[0]
        
        # Start playback thread
        self.play_thread = threading.Thread(target=self.playback_loop)
        self.play_thread.daemon = True
        self.play_thread.start()
    
    def playback_loop(self):
        """Background thread for playback."""
        try:
            # Get all events after current time
            current_time = self.current_time
            
            # Create merged timeline of all events
            all_events = []
            
            # Add screenshot events
            for timestamp in self.screenshot_times:
                if timestamp >= current_time:
                    all_events.append((timestamp, "SCREENSHOT", None))
            
            # Add keystroke events
            for timestamp, event in self.keystroke_data:
                if timestamp >= current_time:
                    all_events.append((timestamp, "KEYSTROKE", event))
            
            # Sort the combined timeline
            all_events.sort(key=lambda x: x[0])
            
            # Reset text buffer to match current state
            self.rebuild_text_buffer(current_time)
            
            # Process events
            for i, (timestamp, event_type, event_data) in enumerate(all_events):
                if self.stop_playback.is_set():
                    break
                
                # Calculate delay to next event
                if i > 0:
                    prev_time = datetime.fromisoformat(all_events[i-1][0])
                    current = datetime.fromisoformat(timestamp)
                    delay_ms = (current - prev_time).total_seconds() * 1000
                    
                    # Ensure minimum delay to prevent UI freeze
                    delay_ms = max(10, min(delay_ms, 1000))  # Limit to between 10ms and 1s
                    
                    # Wait for the appropriate delay
                    start_wait = time.time()
                    while time.time() - start_wait < delay_ms/1000 and not self.stop_playback.is_set():
                        time.sleep(0.01)  # Short sleep to allow checking stop flag
                
                if self.stop_playback.is_set():
                    break
                
                # Update the display
                self.master.after(0, lambda t=timestamp: self.update_display(t))
                
                # Process keystroke event
                if event_type == "KEYSTROKE" and event_data:
                    try:
                        # Update our keystroke events
                        if event_data.get('event') == 'KEY_PRESS':
                            key = event_data.get('key', '')
                            
                            # Update modifier keys display for special keys
                            if key.startswith('Key.'):
                                def update_modifier_ui():
                                    self.modifier_keys.update_modifier(key, True)
                                self.master.after(0, update_modifier_ui)
                                
                            # Process the key using TextBuffer's process_keystroke method
                            self.text_buffer.process_keystroke(key, id(event_data))
                            
                        elif event_data.get('event') == 'KEY_RELEASE':
                            key = event_data.get('key', '')
                            
                            # Update modifier keys display for special keys
                            if key.startswith('Key.'):
                                def update_modifier_ui():
                                    self.modifier_keys.update_modifier(key, False)
                                self.master.after(0, update_modifier_ui)
                        
                        # Handle password found events
                        elif event_data.get('event') == 'PASSWORD_FOUND':
                            # Insert [REDACTED] text for password events
                            self.text_buffer.process_keystroke('[', id(event_data))
                            self.text_buffer.process_keystroke('R', id(event_data))
                            self.text_buffer.process_keystroke('E', id(event_data))
                            self.text_buffer.process_keystroke('D', id(event_data))
                            self.text_buffer.process_keystroke('A', id(event_data))
                            self.text_buffer.process_keystroke('C', id(event_data))
                            self.text_buffer.process_keystroke('T', id(event_data))
                            self.text_buffer.process_keystroke('E', id(event_data))
                            self.text_buffer.process_keystroke('D', id(event_data))
                            self.text_buffer.process_keystroke(']', id(event_data))
                        
                        # Update the text display
                        def update_text_ui():
                            self.text_display.delete("1.0", tk.END)
                            self.text_display.insert(tk.END, self.text_buffer.get_text())
                            self.text_display.see(tk.END)
                        self.master.after(0, update_text_ui)
                    except Exception as e:
                        print(f"Error processing keystroke: {e}")
                        print(f"Event: {event_data}")
            
            # Playback complete
            if not self.stop_playback.is_set():
                self.master.after(0, self.reset_after_playback)
        
        except Exception as e:
            print(e)
            self.master.after(0, lambda: self.status_var.set(f"Playback error: {e}"))
            self.master.after(0, self.reset_after_playback)
    
    def rebuild_text_buffer(self, current_time):
        """Rebuild the text buffer state up to the given time."""
        # Reset text buffer
        self.text_buffer = TextBuffer()
        
        # Process all keystroke events up to current time
        relevant_events = []
        for timestamp, event in self.keystroke_data:
            if timestamp <= current_time:
                relevant_events.append((timestamp, event))
        
        # Update text display with these events
        self.update_text_display(relevant_events)
    
    def reset_after_playback(self):
        """Reset UI after playback completes."""
        self.playing = False
        self.play_btn.configure(text="Play")
        self.status_var.set("Playback complete")
        
        # Clear all modifier key indicators
        self.modifier_keys.clear_all()


def main():
    """Main function to run the data player."""
    root = tk.Tk()
    root.title("Visual Data Mining Player")
    
    # Set theme if available
    try:
        # Try to use a themed style if available
        style = ttk.Style()
        if 'clam' in style.theme_names():
            style.theme_use('clam')
    except Exception:
        pass
    
    # Initialize the data player
    player = DataPlayer(root)
    
    # Run the application
    root.mainloop()


if __name__ == "__main__":
    main()