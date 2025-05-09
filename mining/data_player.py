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
import queue
from threading import Lock
from utils.text_buffer import TextBuffer


class SharedState:
    """
    Thread-safe container for sharing state between GUI and worker threads.
    """
    
    def __init__(self):
        self.lock = Lock()
        self.version = 0
        
        # Timeline information (set once at initialization)
        self.timeline_start = None  # ISO timestamp
        self.timeline_end = None    # ISO timestamp
        self.timeline_duration = 0  # seconds
        
        # Control variables (modified by GUI thread)
        self.elapsed_time = 0.0     # Current position in timeline (seconds)
        self.is_playing = False     # Whether playback is active
        
        # Display state (modified by worker thread)
        self.screenshot_path = None
        self.text_content = ""
        self.modifier_states = {}   # key -> is_pressed
        
    def gui_update(self, **kwargs):
        """Update values that GUI thread controls."""
        with self.lock:
            for key, value in kwargs.items():
                if key in ['elapsed_time', 'is_playing']:
                    setattr(self, key, value)
    
    def worker_update(self, **kwargs):
        """Update values from the worker thread, incrementing version."""
        with self.lock:
            for key, value in kwargs.items():
                if key in ['screenshot_path', 'text_content', 'modifier_states']:
                    setattr(self, key, value)
            self.version += 1
    
    def init_timeline(self, start_time, end_time, duration):
        """Initialize timeline information."""
        with self.lock:
            self.timeline_start = start_time
            self.timeline_end = end_time
            self.timeline_duration = duration
    
    def get_timing_info(self):
        """Get timing information for GUI thread."""
        with self.lock:
            return {
                'timeline_start': self.timeline_start,
                'timeline_end': self.timeline_end,
                'timeline_duration': self.timeline_duration,
                'elapsed_time': self.elapsed_time,
                'is_playing': self.is_playing
            }
    
    def get_display_state(self):
        """Get display state information (with version)."""
        with self.lock:
            return {
                'version': self.version,
                'screenshot_path': self.screenshot_path,
                'text_content': self.text_content,
                'modifier_states': self.modifier_states.copy(),
            }


class DisplayProcessor:
    """
    Background processor that calculates display state based on timeline position.
    Reads the elapsed_time from shared state and updates the display output.
    """
    
    def __init__(self, shared_state, screenshot_data, keystroke_data):
        self.state = shared_state
        self.screenshots = screenshot_data.get('screenshots', {})  # timestamp -> path
        self.screenshot_times = screenshot_data.get('timestamps', [])
        self.keystroke_data = keystroke_data
        
        self.running = False
        self.thread = None
        
        # Timeline information
        if self.screenshot_times:
            duration = self._calculate_duration()
            self.state.init_timeline(
                self.screenshot_times[0],
                self.screenshot_times[-1],
                duration
            )
            print(f"Timeline initialized with duration: {duration} seconds")
            
    def _calculate_duration(self):
        """Calculate total duration in seconds."""
        if len(self.screenshot_times) < 2:
            return 0.0
            
        start = datetime.fromisoformat(self.screenshot_times[0])
        end = datetime.fromisoformat(self.screenshot_times[-1])
        return (end - start).total_seconds()
        
    def start(self):
        """Start the processor thread."""
        if self.running:
            return
            
        self.running = True
        self.thread = threading.Thread(target=self._process_loop, daemon=True)
        self.thread.start()
        
    def stop(self):
        """Stop the processor thread."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
            self.thread = None
            
    def _process_loop(self):
        """Main processing loop running in background thread."""
        last_elapsed_time = -1  # Force initial update
        update_interval = 1/30  # ~30 fps
        last_update_time = 0
        
        while self.running:
            now = time.time()
            
            # Only update at target frame rate
            if now - last_update_time >= update_interval:
                # Get current elapsed time (set by GUI thread)
                timing = self.state.get_timing_info()
                elapsed_time = timing['elapsed_time']
                
                # Only update if position has changed
                if abs(elapsed_time - last_elapsed_time) > 0.001:
                    self._update_display_for_position(elapsed_time)
                    last_elapsed_time = elapsed_time
                    
                last_update_time = now
            
            # Sleep briefly to avoid excessive CPU
            time.sleep(0.001)
            
    def _update_display_for_position(self, elapsed_time):
        """Update the display state for a specific position."""
        if not self.screenshot_times:
            return
            
        try:
            # Convert elapsed time to absolute timeline position
            timing = self.state.get_timing_info()
            start_dt = datetime.fromisoformat(timing['timeline_start'])
            target_dt = start_dt + timedelta(seconds=elapsed_time)
            target_iso = target_dt.isoformat()
            
            # Find the closest screenshot timestamp
            closest_time = self.screenshot_times[0]
            for ts in self.screenshot_times:
                if ts <= target_iso:
                    closest_time = ts
                else:
                    break
            
            # Get screenshot path
            screenshot_path = self.screenshots.get(closest_time)
            
            # Process relevant keystrokes
            text_buffer = TextBuffer()
            modifier_states = {}
            
            # Get all events up to this position
            events_up_to = [(ts, event) for ts, event in self.keystroke_data if ts <= target_iso]
            
            # Process each event
            for _, event in events_up_to:
                event_type = event.get('event', '')
                key = event.get('key', '')
                
                # Process based on event type
                if event_type == 'KEY_PRESS':
                    if key and key.startswith('Key.'):
                        modifier_states[key] = True
                        
                    if key:
                        text_buffer.process_keystroke(key, id(event))
                        
                elif event_type == 'KEY_RELEASE':
                    if key and key.startswith('Key.'):
                        modifier_states[key] = False
                        
                elif event_type == 'PASSWORD_FOUND':
                    for char in "[REDACTED]":
                        text_buffer.process_keystroke(char, id(event))
            
            # Update the state with processed data (this will increment state version)
            self.state.worker_update(
                screenshot_path=screenshot_path,
                text_content=text_buffer.get_text(),
                modifier_states=modifier_states
            )
            
        except Exception as e:
            print(f"Error updating display: {e}")


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
        # If logs_dir not specified, look for the most recent logs_* directory
        if not logs_dir:
            log_dirs = [d for d in glob.glob(os.path.join(os.getcwd(), 'logs_*')) if os.path.isdir(d)]
            if log_dirs:
                # Sort by modification time (newest first)
                log_dirs.sort(key=os.path.getmtime, reverse=True)
                logs_dir = log_dirs[0]
            else:
                # Fallback to old 'logs' directory if no logs_* found
                logs_dir = os.path.join(os.getcwd(), 'logs')

        self.logs_dir = logs_dir
        self.screenshots_dir = os.path.join(self.logs_dir, 'screenshots')
        self.sanitized_dir = os.path.join(self.logs_dir, 'sanitized_json')
        
        # Shared state between UI and worker threads
        self.shared_state = SharedState()
        self.processor = None
        
        # UI state
        self.last_seen_version = 0
        self.photo_image = None  # Keep a reference to prevent garbage collection
        self.update_ui_timer_id = None
        self.playback_timer_id = None
        self.ui_update_interval = 33  # ms (about 30 fps)
        self._scrubbing = False
        self._last_image_path = None
        
        # Playback reference time (when playing)
        self.reference_time = None
        
        # Data containers
        self.screenshots = {}  # Dictionary of timestamp -> filepath
        self.screenshot_times = []  # Ordered list of timestamps
        self.keystroke_data = []  # List of (timestamp, event) tuples
        
        # Create UI
        self.create_ui()
        
        # Load data if directories exist
        if os.path.exists(self.screenshots_dir) and os.path.exists(self.sanitized_dir):
            self.load_data()
        else:
            self.text_display.insert(tk.END, "Data directories not found. Please select a logs directory.")
            
        # Start the UI update timer
        self.start_ui_updates()
    
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
    
    def start_ui_updates(self):
        """Start the UI update timer."""
        self.update_ui()
        
    def update_ui(self):
        """Update UI based on the current state."""
        try:
            # Get the latest display state from the worker thread
            display = self.shared_state.get_display_state()
            
            # Only process if state has changed
            if display['version'] > self.last_seen_version:
                self.last_seen_version = display['version']
                
                # Update time display - calculated from elapsed time
                timing = self.shared_state.get_timing_info()
                if timing['timeline_start']:
                    # Format timestamp
                    start_dt = datetime.fromisoformat(timing['timeline_start'])
                    current_dt = start_dt + timedelta(seconds=timing['elapsed_time'])
                    formatted_time = current_dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                    self.time_var.set(formatted_time)
                
                # Calculate scrubber position
                if timing['timeline_duration'] > 0 and not self._scrubbing:
                    percentage = min(100, (timing['elapsed_time'] / timing['timeline_duration']) * 100)
                    self.scrub_var.set(percentage)
                
                # Update play/pause button
                self.play_btn.configure(text="Pause" if timing['is_playing'] else "Play")
                
                # Update text content
                self.text_display.delete("1.0", tk.END)
                self.text_display.insert(tk.END, display['text_content'])
                self.text_display.see(tk.END)
                
                # Update modifier keys
                self.modifier_keys.clear_all()
                for key, is_pressed in display['modifier_states'].items():
                    if is_pressed:
                        self.modifier_keys.update_modifier(key, True)
                
                # Update image if changed
                if display['screenshot_path'] and (not self._last_image_path or 
                                                 self._last_image_path != display['screenshot_path']):
                    self._last_image_path = display['screenshot_path']
                    self.display_image(Image.open(display['screenshot_path']))
        except Exception as e:
            self.status_var.set(f"UI update error: {str(e)[:50]}...")
        
        # Schedule next update
        self.update_ui_timer_id = self.master.after(self.ui_update_interval, self.update_ui)
        
    def update_playback_position(self):
        """Update position during playback."""
        if self.reference_time is not None:
            # Get timing info
            timing = self.shared_state.get_timing_info()
            
            # Calculate current elapsed time
            elapsed_time = time.time() - self.reference_time
            
            # Check for end of timeline
            if elapsed_time >= timing['timeline_duration']:
                # At the end, stop playback and set position to end
                self.stop_playback()
                # Set to exact end position
                self.shared_state.gui_update(elapsed_time=timing['timeline_duration'])
                self.status_var.set("Playback complete - press Play to restart")
            else:
                # Update elapsed time
                self.shared_state.gui_update(elapsed_time=elapsed_time)
                
                # Schedule next update
                self.playback_timer_id = self.master.after(33, self.update_playback_position)
    
    def load_data(self):
        """Load screenshots and keystroke data."""
        self.status_var.set("Loading data...")
        self.master.update_idletasks()
        
        # Stop any existing processor
        if self.processor:
            self.processor.stop()
            self.processor = None
        
        # Stop playback if active
        self.stop_playback()
        
        # Reset data
        self.screenshots = {}
        self.screenshot_times = []
        self.keystroke_data = []
        self._scrubbing = False
        self._last_image_path = None
        
        # Reset shared state
        self.shared_state = SharedState()
        
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
            
            # Create screenshot data for the processor
            screenshot_data = {
                'screenshots': self.screenshots,
                'timestamps': self.screenshot_times
            }
            
            # Create and start the display processor
            self.processor = DisplayProcessor(self.shared_state, screenshot_data, self.keystroke_data)
            self.processor.start()
            
            # Set initial position
            self.shared_state.gui_update(elapsed_time=0.0)
            
            # Wait briefly for processor to initialize
            self.master.after(100, lambda: self.status_var.set(
                f"Loaded {len(self.screenshots)} screenshots and {len(self.keystroke_data)} keystroke events"
            ))
            
            if not self.screenshot_times:
                self.status_var.set("No data found in selected directories")
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load data: {e}")
            self.status_var.set(f"Error: {e}")
            
    def stop_playback(self):
        """Stop active playback."""
        # Cancel any playback timer
        if self.playback_timer_id:
            self.master.after_cancel(self.playback_timer_id)
            self.playback_timer_id = None
            
        # Update shared state
        self.shared_state.gui_update(is_playing=False)
        
        # Clear reference time
        self.reference_time = None
    
    def on_scrub(self, value):
        """Handle timeline scrubbing - direct UI control of elapsed time."""
        if self.processor and self.screenshot_times:
            try:
                # Mark that we're scrubbing
                self._scrubbing = True
                
                # Convert percentage to elapsed time in seconds
                percentage = float(value)
                timing = self.shared_state.get_timing_info()
                timeline_duration = timing.get('timeline_duration', 0)
                is_playing = timing.get('is_playing', False)
                
                if timeline_duration > 0:
                    # Calculate new elapsed time
                    new_elapsed_time = (percentage / 100) * timeline_duration
                    
                    # Directly update shared state (no command queue)
                    self.shared_state.gui_update(elapsed_time=new_elapsed_time)
                    
                    # If we're playing, update the reference time so playback continues from new position
                    if is_playing:
                        self.reference_time = time.time() - new_elapsed_time
                    
                    # Update status bar
                    percentage_str = f"{int(percentage)}%"
                    self.status_var.set(f"Timeline position: {percentage_str}")
                
                # Clear scrubbing flag after a short delay
                self.master.after(200, self._clear_scrubbing_flag)
            except Exception as e:
                self.status_var.set(f"Error during scrubbing: {str(e)[:50]}...")
                self._clear_scrubbing_flag()
                
    def _clear_scrubbing_flag(self):
        """Clear the scrubbing flag after a delay."""
        self._scrubbing = False
    
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
        # Refresh the current image if available
        if hasattr(self, '_last_image_path') and self._last_image_path:
            try:
                img = Image.open(self._last_image_path)
                self.display_image(img)
            except Exception:
                pass
    
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
        if not self.processor:
            messagebox.showinfo("No Data", "No data loaded to play. Please select a logs directory.")
            return
            
        timing = self.shared_state.get_timing_info()
        if timing['is_playing']:
            # Pause playback
            self.stop_playback()
            self.status_var.set("Paused")
        else:
            # Start playback
            self.start_playback()
            self.status_var.set("Playing")
            
    def start_playback(self):
        """Start playback from current position."""
        # Get current timing info
        timing = self.shared_state.get_timing_info()
        
        # Check if we need to restart from beginning
        # This will happen if we're very close to the end (within 0.1 seconds)
        threshold = 0.1
        if timing['elapsed_time'] >= (timing['timeline_duration'] - threshold):
            # Reset to beginning
            self.shared_state.gui_update(elapsed_time=0.0)
            timing['elapsed_time'] = 0.0
        
        # Set reference time based on current elapsed time
        self.reference_time = time.time() - timing['elapsed_time']
        
        # Set playing state
        self.shared_state.gui_update(is_playing=True)
        
        # Start playback update timer
        self.update_playback_position()
            
    def __del__(self):
        """Clean up resources."""
        # Stop UI updates
        if hasattr(self, 'update_ui_timer_id') and self.update_ui_timer_id:
            try:
                self.master.after_cancel(self.update_ui_timer_id)
            except Exception:
                pass
        
        # Stop playback timer
        if hasattr(self, 'playback_timer_id') and self.playback_timer_id:
            try:
                self.master.after_cancel(self.playback_timer_id)
            except Exception:
                pass
        
        # Stop the processor
        if hasattr(self, 'processor') and self.processor:
            try:
                self.processor.stop()
            except Exception:
                pass
    


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