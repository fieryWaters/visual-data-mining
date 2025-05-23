#!/usr/bin/env python3
"""
Simplified data collector that integrates keystroke recording, sanitization, and screen recording.
"""

import os
import time
import threading
from datetime import datetime

from keystroke_recorder import KeystrokeRecorder
from keystroke_sanitizer import KeystrokeSanitizer
from screen_recorder import InMemoryScreenRecorder

class SimpleCollector:
    """Minimalist implementation of the data collection system"""
    
    def __init__(self, password, output_dir='logs'):
        # Create directories
        os.makedirs(output_dir, exist_ok=True)
        
        # Initialize components with shared password manager
        self.keystroke_recorder = KeystrokeRecorder(buffer_size=1000)
        self.keystroke_sanitizer = KeystrokeSanitizer(password)
        self.screen_recorder = InMemoryScreenRecorder(max_frames=300)
        
        # Initialize file paths
        self.output_dir = output_dir
        
        # Internal state
        self.running = False
        self.stop_event = threading.Event()
        self.process_thread = None
    
    def add_password(self, password):
        """Add a password to sanitize"""
        result = self.keystroke_sanitizer.add_password(password)
        if result:
            self.keystroke_sanitizer.save_passwords()
            print("Added password to sanitization list")
        return result
    
    def _process_buffer(self):
        """Process keystroke buffer and save screenshots every 5 seconds"""
        # Create required directories
        json_dir = os.path.join(self.output_dir, 'sanitized_json')
        screenshots_dir = os.path.join(self.output_dir, 'screenshots')
        os.makedirs(json_dir, exist_ok=True)
        os.makedirs(screenshots_dir, exist_ok=True)
        
        # Session ID for filenames
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        buffer_count = 0
        
        while not self.stop_event.is_set():
            try:
                # 1. Process keystrokes
                events = self.keystroke_recorder.get_buffer_contents(clear=True)
                if events:
                    # Sanitize events
                    sanitized = self.keystroke_sanitizer.process_events(events)
                    
                    # Save as JSON file
                    buffer_count += 1
                    json_filename = f"sanitized_{session_id}_{buffer_count:04d}.json"
                    json_path = os.path.join(json_dir, json_filename)
                    self.keystroke_sanitizer.save_sanitized_json(sanitized, json_path)
                    
                    print(f"Processed {len(events)} events, saved to {json_filename}")
                
                # 2. Save current screenshots to disk and clear buffer
                saved_files = self.screen_recorder.save_frames_to_disk(
                    screenshots_dir, 
                    format='jpg'
                )
                if saved_files:
                    print(f"Saved {len(saved_files)} screenshots")
            
            except Exception as e:
                print(f"Error in processing: {e}")
            
            # Wait before next processing
            time.sleep(120)
    
    def start(self):
        """Start all recording components"""
        import time
        
        if self.running:
            return
            
        print("\nStarting recording components sequentially with delays...")
        
        # Start keystroke recorder first in inactive state
        print("\n1. Starting keystroke recorder...")
        self.keystroke_recorder.start()
        # Activate it to start processing events
        self.keystroke_recorder.set_active(True)
        
        # Wait before starting next component
        time.sleep(2)
        
        # Start screen recorder next (also in inactive state)
        print("\n2. Starting screen recorder...")
        self.screen_recorder.start()
        # Activate it to start capturing screenshots
        self.screen_recorder.set_active(True)
        
        # Wait before starting processing thread
        time.sleep(2)
        
        # Start processing thread
        print("\n3. Starting processing thread...")
        self.stop_event.clear()
        self.process_thread = threading.Thread(target=self._process_buffer, daemon=True)
        self.process_thread.start()
        
        self.running = True
        print("\nAll recording components started successfully")
    
    def stop(self):
        """Stop all recording components"""
        if not self.running:
            return
            
        # Stop processing thread
        self.stop_event.set()
        if self.process_thread:
            self.process_thread.join(timeout=2)
        
        # Process any final events
        events = self.keystroke_recorder.get_buffer_contents()
        if events:
            # Create required directories
            json_dir = os.path.join(self.output_dir, 'sanitized_json')
            os.makedirs(json_dir, exist_ok=True)
            
            # Process and save
            sanitized = self.keystroke_sanitizer.process_events(events)
            
            # Save as final JSON
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            json_path = os.path.join(json_dir, f"sanitized_{timestamp}_final.json")
            self.keystroke_sanitizer.save_sanitized_json(sanitized, json_path)
            print(f"Processed final {len(events)} events")
        
        # Deactivate both recorders (but don't fully stop them)
        self.keystroke_recorder.set_active(False)
        self.screen_recorder.set_active(False)
        
        self.running = False
        print("Recording stopped")
        
    def shutdown(self):
        """Completely shut down all components and clean up (use on app exit)"""
        # Make sure to stop recording first if it's running
        if self.running:
            self.stop()
            
        # Now properly shut down both recorders
        print("Shutting down keystroke recorder completely...")
        self.keystroke_recorder.shutdown()
        
        print("Shutting down screen recorder completely...")
        self.screen_recorder.shutdown()
        
        print("Application shutdown complete")

if __name__ == "__main__":
    # Simple usage example
    password = input("Enter encryption password: ")
    collector = SimpleCollector(password)
    
    # Add test passwords
    collector.add_password("test_password1")
    collector.add_password("test_password2")
    
    # Start collection
    collector.start()
    
    try:
        print("Recording... (Press Ctrl+C to stop)")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        collector.stop()
        print("Done")