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
from datetime import datetime, timedelta
import threading
import glob
import re
from utils.text_buffer import TextBuffer


class ModifierKeysWidget(ttk.Frame):
    """Compact widget to display modifier key states."""
    
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        # Define modifier keys directly for clarity
        self.key_map = {
            # Command/Meta keys
            "Key.cmd": "CMD", 
            "Key.cmd_l": "CMD", 
            "Key.cmd_r": "CMD",
            "Key.meta": "CMD",  # Some systems use meta instead of cmd
            
            # Control keys
            "Key.ctrl": "CTRL", 
            "Key.ctrl_l": "CTRL", 
            "Key.ctrl_r": "CTRL",
            
            # Shift keys
            "Key.shift": "SHIFT", 
            "Key.shift_l": "SHIFT", 
            "Key.shift_r": "SHIFT",
            
            # Alt keys
            "Key.alt": "ALT", 
            "Key.alt_l": "ALT", 
            "Key.alt_r": "ALT",
            "Key.alt_gr": "ALT",
            
            # Arrow keys
            "Key.up": "UP",
            "Key.down": "DOWN",
            "Key.left": "LEFT",
            "Key.right": "RIGHT",
            
            # Other special keys
            "Key.caps_lock": "CAPS",
            "Key.tab": "TAB",
            "Key.esc": "ESC"
        }
        
        # Define the display order
        display_order = [
            "SHIFT", "CTRL", "ALT", "CMD",   # Modifiers
            "UP", "DOWN", "LEFT", "RIGHT",   # Arrows
            "CAPS", "TAB", "ESC"             # Special keys
        ]
        
        # Create indicators all at once
        self.labels = {}
        for i, name in enumerate(display_order):
            lbl = ttk.Label(self, text=name, width=6, anchor=tk.CENTER, relief=tk.GROOVE, background="#d3d3d3")
            lbl.grid(row=0, column=i, padx=2, pady=2)
            self.labels[name] = lbl
        
        # Track active counts
        self.counts = {name: 0 for name in self.labels}
    
    def update_modifier(self, key, is_pressed):
        """Toggle a modifier key state."""
        if key in self.key_map:
            name = self.key_map[key]
            self.counts[name] += 1 if is_pressed else -1
            self.labels[name].configure(background="#4caf50" if self.counts[name] > 0 else "#d3d3d3")
    
    def clear_all(self):
        """Reset all modifier states."""
        for name in self.labels:
            self.counts[name] = 0
            self.labels[name].configure(background="#d3d3d3")


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
        
        # Simple state machine
        self.playing = False
        self.start_time = None  # Reference point (in system time)
        self.elapsed_time = 0.0  # Position in timeline (in seconds)
        self.play_thread = None
        self.stop_playback = threading.Event()
        
        # Data containers
        self.screenshots = {}  # Dictionary of timestamp -> filepath
        self.screenshot_times = []  # Ordered list of timestamps
        self.keystroke_data = []  # List of (timestamp, event) tuples
        self.timeline_start = None  # First timestamp in dataset (ISO)
        self.timeline_end = None    # Last timestamp in dataset (ISO)
        self.timeline_duration = 0  # Total duration in seconds
        
        # Create UI
        self.create_ui()
        
        # Text buffer for processing keystrokes
        self.text_buffer = TextBuffer()
        
        # Update display timer
        self.update_timer_id = None
        
        # Load data if directories exist
        if os.path.exists(self.screenshots_dir) and os.path.exists(self.sanitized_dir):
            self.load_data()
        else:
            self.text_display.insert(tk.END, "Data directories not found. Please select a logs directory.")
    
    def create_ui(self):
        """Create the user interface."""
        # Main layout frame
        f = ttk.Frame(self.master, padding=10)
        f.pack(fill=tk.BOTH, expand=True)
        
        # Directory controls (top)
        ctrl = ttk.Frame(f)
        ctrl.pack(fill=tk.X)
        
        ttk.Label(ctrl, text="Logs Directory:").pack(side=tk.LEFT, padx=5)
        self.dir_entry = ttk.Entry(ctrl, width=50)
        self.dir_entry.insert(0, self.logs_dir)
        self.dir_entry.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(ctrl, text="Browse", command=self.browse_directory).pack(side=tk.LEFT, padx=2)
        ttk.Button(ctrl, text="Load", command=self.load_data).pack(side=tk.LEFT, padx=2)
        
        # Main display area (middle)
        mid = ttk.Frame(f)
        mid.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Image display
        self.image_frame = ttk.Frame(mid, borderwidth=2, relief=tk.GROOVE)
        self.image_frame.pack(fill=tk.BOTH, expand=True, side=tk.TOP)
        self.canvas = tk.Canvas(self.image_frame, bg="black")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Text display area
        self.text_frame = ttk.Frame(mid, height=150)
        self.text_frame.pack(fill=tk.X, side=tk.BOTTOM)
        self.text_frame.pack_propagate(False)
        
        # Modifier keys display
        self.modifier_keys = ModifierKeysWidget(self.text_frame)
        self.modifier_keys.pack(fill=tk.X, side=tk.TOP, pady=3)
        
        # Keystroke text display
        self.text_display = tk.Text(self.text_frame, height=7, wrap=tk.WORD, 
                                   bg="#f0f0f0", font=("Courier", 12))
        self.text_scrollbar = ttk.Scrollbar(self.text_frame, command=self.text_display.yview)
        self.text_display.configure(yscrollcommand=self.text_scrollbar.set)
        self.text_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.text_display.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Playback controls (bottom)
        btm = ttk.Frame(f)
        btm.pack(fill=tk.X, side=tk.BOTTOM, pady=5)
        
        # Time control
        time_frame = ttk.Frame(btm)
        time_frame.pack(fill=tk.X, pady=5)
        
        # Time and playback controls
        self.time_var = tk.StringVar(value="00:00:00.000")
        ttk.Label(time_frame, textvariable=self.time_var, font=("Courier", 12)).pack(side=tk.LEFT, padx=5)
        self.play_btn = ttk.Button(time_frame, text="Play", command=self.toggle_playback)
        self.play_btn.pack(side=tk.LEFT, padx=5)
        
        # Timeline scrubbing bar
        timeline_frame = ttk.Frame(btm)
        timeline_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(timeline_frame, text="Timeline:").pack(side=tk.LEFT, padx=5)
        self.scrub_var = tk.DoubleVar(value=0)
        self.scrub_bar = ttk.Scale(
            timeline_frame, 
            orient=tk.HORIZONTAL, 
            variable=self.scrub_var,
            from_=0, to=100,
            command=self.on_scrub
        )
        self.scrub_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        self.status_bar = ttk.Label(btm, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM, pady=3)
        
        # Window resize handler
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
            
    def extract_timestamp_from_filename(self, filepath):
        """
        Extract ISO timestamp from screenshot filename.
        Example filename: screen_20250402_141928_296876.jpg
        Returns ISO format: 2025-04-02T14:19:28.296876
        """
        match = re.search(r'screen_(\d{8})_(\d{6})_(\d+)\.jpg', os.path.basename(filepath))
        if not match:
            return None
            
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
        
        return f"{year}-{month}-{day}T{hour}:{minute}:{second}.{ms}"
    
    def load_data(self):
        """Load screenshots and keystroke data."""
        self.status_var.set("Loading data...")
        self.master.update_idletasks()
        
        # Reset data
        self.screenshots = {}
        self.screenshot_times = []
        self.keystroke_data = []
        self.text_buffer = TextBuffer()
        self.elapsed_time = 0.0
        
        # Update directories from entry field
        self.logs_dir = self.dir_entry.get()
        self.screenshots_dir = os.path.join(self.logs_dir, 'screenshots')
        self.sanitized_dir = os.path.join(self.logs_dir, 'sanitized_json')
        
        try:
            # Load screenshots
            screenshot_files = glob.glob(os.path.join(self.screenshots_dir, "*.jpg"))
            for filepath in screenshot_files:
                # Extract timestamp from filename
                timestamp = self.extract_timestamp_from_filename(filepath)
                if timestamp:
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
            
            # Calculate timeline range
            if self.screenshot_times:
                self.timeline_start = self.screenshot_times[0]
                self.timeline_end = self.screenshot_times[-1]
                
                # Calculate total duration in seconds
                start_dt = datetime.fromisoformat(self.timeline_start)
                end_dt = datetime.fromisoformat(self.timeline_end)
                self.timeline_duration = (end_dt - start_dt).total_seconds()
                
                # Initialize display at the beginning (0 elapsed time)
                self.update_display_for_elapsed_time()
                
                self.status_var.set(
                    f"Loaded {len(self.screenshots)} screenshots and {len(self.keystroke_data)} keystroke events"
                )
            else:
                self.status_var.set("No data found in selected directories")
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load data: {e}")
            self.status_var.set(f"Error: {e}")
    
                
    def update_display_for_elapsed_time(self):
        """Update the display based on the current elapsed time."""
        if not self.timeline_start or not self.screenshot_times:
            return
            
        try:
            # Convert elapsed time to absolute timeline position
            start_dt = datetime.fromisoformat(self.timeline_start)
            target_dt = start_dt + timedelta(seconds=self.elapsed_time)
            target_iso = target_dt.isoformat()
            
            # Find the closest screenshot timestamp
            closest_time = self.screenshot_times[0]
            for ts in self.screenshot_times:
                if ts <= target_iso:
                    closest_time = ts
                else:
                    break
            
            # Update the text buffer for this position
            self.text_buffer = TextBuffer()
            events_up_to = [(ts, event) for ts, event in self.keystroke_data if ts <= target_iso]
            self.update_text_display(events_up_to)
            
            # Update the visual display
            if closest_time in self.screenshots:
                img = Image.open(self.screenshots[closest_time])
                self.display_image(img)
                
                # Format timestamp for display
                display_dt = start_dt + timedelta(seconds=self.elapsed_time)
                formatted_time = display_dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                self.time_var.set(formatted_time)
                
                # Update scrub bar position (we handle this in the scrubber)
                # Not updating the scrub bar here to avoid infinite loop
                
                # Update status bar
                if not self.playing:
                    percentage_int = int((self.elapsed_time / self.timeline_duration) * 100)
                    self.status_var.set(f"Timeline position: {percentage_int}%")
        except Exception as e:
            self.status_var.set(f"Display error: {str(e)[:50]}...")
    
    def on_scrub(self, value):
        """Handle timeline scrubbing."""
        if self.screenshot_times:
            try:
                # Convert percentage to elapsed time in seconds
                percentage = float(value)
                new_elapsed_time = (percentage / 100) * self.timeline_duration
                
                # Update elapsed time
                self.elapsed_time = new_elapsed_time
                
                # If playing, adjust start time to maintain continuity
                if self.playing:
                    self.start_time = time.time() - self.elapsed_time
                
                # Update status
                percentage_str = f"{int(percentage)}%"
                self.status_var.set(f"Timeline position: {percentage_str}")
                
                # Manually trigger a single update after a slight delay
                self.master.after(10, self.update_display_for_elapsed_time)
            except Exception as e:
                self.status_var.set(f"Error during scrubbing: {str(e)[:50]}...")
    
    def display_image(self, img):
        """Resize and display an image on the canvas."""
        # Get canvas size and retry if not ready
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        if w <= 1 or h <= 1:
            self.master.after(100, lambda: self.display_image(img))
            return
            
        # Resize image to fit canvas
        img_w, img_h = img.size
        scale = min(w/img_w, h/img_h)
        new_size = (int(img_w*scale), int(img_h*scale))
        
        # Create PhotoImage and display
        photo = ImageTk.PhotoImage(img.resize(new_size, Image.Resampling.LANCZOS))
        self.canvas.delete("all")
        self.canvas.create_image(w//2, h//2, image=photo, anchor=tk.CENTER)
        self.canvas.image = photo  # Prevent garbage collection
    
    def on_resize(self, event=None):
        """Redisplay current image when window resizes."""
        # Just update the display using current elapsed time
        self.update_display_for_elapsed_time()
    
    def process_keystroke_event(self, event, update_ui=False):
        """Process a keystroke event and update the UI if requested."""
        if not event:
            return
        
        event_type = event.get('event', '')
        
        # Handle different event types
        if event_type == 'KEY_PRESS':
            key = event.get('key', '')
            if not key:
                return
                
            # Update modifier keys if it's a special key
            if key.startswith('Key.') and update_ui:
                # Process immediately for better responsiveness
                self.modifier_keys.update_modifier(key, True)
            
            # Process the keystroke
            self.text_buffer.process_keystroke(key, id(event))
            
        elif event_type == 'KEY_RELEASE' and update_ui:
            # Only update modifier keys state for KEY_RELEASE
            key = event.get('key', '')
            if key and key.startswith('Key.'):
                # Process immediately for better responsiveness
                self.modifier_keys.update_modifier(key, False)
                
        elif event_type == 'PASSWORD_FOUND':
            # Insert [REDACTED] text
            for char in "[REDACTED]":
                self.text_buffer.process_keystroke(char, id(event))
        
        # Update text display if requested
        if update_ui:
            self.master.after(0, lambda: (
                self.text_display.delete("1.0", tk.END),
                self.text_display.insert(tk.END, self.text_buffer.get_text()),
                self.text_display.see(tk.END)
            ))
    
    def update_text_display(self, events):
        """Process keystroke events and update the text display."""
        self.text_display.delete("1.0", tk.END)
        self.modifier_keys.clear_all()
        
        # Process all events in sequence
        for timestamp, event in events:
            # Process the keystroke for text
            self.process_keystroke_event(event, update_ui=False)
            
            # Update modifier keys for special keys
            event_type = event.get('event', '')
            key = event.get('key', '')
            
            if event_type == 'KEY_PRESS' and key and key.startswith('Key.'):
                self.modifier_keys.update_modifier(key, True)
            elif event_type == 'KEY_RELEASE' and key and key.startswith('Key.'):
                self.modifier_keys.update_modifier(key, False)
            
        # Show the result
        self.text_display.insert(tk.END, self.text_buffer.get_text())
        self.text_display.see(tk.END)
    
    def toggle_playback(self):
        """Toggle between play and pause."""
        if not self.timeline_start:
            messagebox.showinfo("No Data", "No data loaded to play. Please select a logs directory.")
            return
            
        if self.playing:
            # PAUSE: Just flag we're no longer playing
            self.playing = False
            self.play_btn.configure(text="Play")
            self.status_var.set("Paused")
            
            # Stop update timer
            if self.update_timer_id:
                self.master.after_cancel(self.update_timer_id)
                self.update_timer_id = None
        else:
            # PLAY: Set playing flag and start the update loop
            self.playing = True
            self.play_btn.configure(text="Pause")
            self.status_var.set("Playing")
            
            # If we're at the end, restart from beginning
            if self.elapsed_time >= self.timeline_duration:
                self.elapsed_time = 0
                self.update_display_for_elapsed_time()
            
            # Set start_time based on current elapsed time
            self.start_time = time.time() - self.elapsed_time
            
            # Start update timer
            self.update_playback_display()
    
    def update_playback_display(self):
        """Update display during playback using timer-based approach."""
        if not self.playing:
            return
            
        try:
            # Calculate current elapsed time based on start time
            current_time = time.time()
            self.elapsed_time = current_time - self.start_time
            
            # Check if we've reached the end
            if self.elapsed_time >= self.timeline_duration:
                # We're at the end, stop playback
                self.playing = False
                self.play_btn.configure(text="Play")
                self.status_var.set("Playback complete - press Play to restart")
                self.modifier_keys.clear_all()
                
                # Set to end for restart detection
                self.elapsed_time = self.timeline_duration
                self.update_display_for_elapsed_time()
                
                # Update scrubber to end position
                self.scrub_bar.set(100)
                return
                
            # Update display based on current elapsed time
            self.update_display_for_elapsed_time()
            
            # Update scrubber position during playback (won't cause recursion during playback)
            if self.timeline_duration > 0:
                percentage = (self.elapsed_time / self.timeline_duration) * 100
                self.scrub_bar.set(percentage)
            
            # Schedule next update (roughly 30 fps for smooth playback)
            self.update_timer_id = self.master.after(33, self.update_playback_display)
        
        except Exception as e:
            self.status_var.set(f"Playback error: {str(e)[:50]}...")
            self.playing = False
            self.play_btn.configure(text="Play")


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
    
    # Bring window to foreground
    root.lift()
    root.attributes('-topmost', True)
    root.after_idle(root.attributes, '-topmost', False)
    
    # Run the application
    root.mainloop()


if __name__ == "__main__":
    main()