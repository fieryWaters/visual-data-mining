"""
Main controller for the data collection system.
Integrates keystroke recording, sanitization, and screen recording.
"""

import os
import time
import json
import argparse
import threading
import logging
from datetime import datetime

# Import our modules
from keystroke_recorder import KeystrokeRecorder
from keystroke_sanitizer import KeystrokeSanitizer
from screen_recorder import ScreenRecorder

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("data_collector.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('data_collector')

class DataCollector:
    """
    Main controller for collecting, processing, and storing interaction data
    """
    
    def __init__(self, output_dir='logs', 
                 passwords_file='secret.keys',
                 screen_record=True,
                 screen_window_minutes=10,
                 screen_fps=5,
                 process_interval=10,  # Process buffer every 10 seconds
                 buffer_size=10000):   # Max events in buffer
        """
        Initialize data collector with all components
        
        Args:
            output_dir: Directory for storing logs
            passwords_file: Encrypted file with passwords to sanitize
            screen_record: Whether to enable screen recording
            screen_window_minutes: Minutes to keep in rolling screen recording
            screen_fps: Frames per second for screen recording
            process_interval: Seconds between processing buffer
            buffer_size: Maximum events in keystroke buffer
        """
        self.output_dir = output_dir
        self.passwords_file = passwords_file
        self.process_interval = process_interval
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Initialize components
        self.keystroke_recorder = KeystrokeRecorder(buffer_size=buffer_size)
        self.keystroke_sanitizer = KeystrokeSanitizer(passwords_file=passwords_file)
        
        # Initialize screen recorder if enabled
        self.screen_recorder = None
        if screen_record:
            screen_output_dir = os.path.join(output_dir, 'screen_recordings')
            self.screen_recorder = ScreenRecorder(
                output_dir=screen_output_dir,
                window_minutes=screen_window_minutes,
                fps=screen_fps
            )
        
        # Internal state
        self.running = False
        self.processing_thread = None
        self.stop_event = threading.Event()
        
        # Log file
        self.log_file = os.path.join(output_dir, 'interaction_log.jsonl')
    
    def setup(self, password=None):
        """
        Set up the data collector, including password encryption
        
        Args:
            password: Password for encryption (optional)
        
        Returns:
            bool: True if setup successful, False otherwise
        """
        # Set up encryption for password sanitization
        if not self.keystroke_sanitizer.setup_encryption(password):
            logger.error("Failed to set up encryption")
            return False
        
        # Load existing passwords
        if not self.keystroke_sanitizer.load_passwords():
            logger.error("Failed to load passwords")
            return False
        
        logger.info("Data collector setup complete")
        return True
    
    def add_password(self, password):
        """Add a password to the sanitization list"""
        self.keystroke_sanitizer.add_password(password)
        self.keystroke_sanitizer.save_passwords()
        logger.info("Added password to sanitization list")
    
    def _process_buffer(self):
        """Process the keystroke buffer periodically"""
        while not self.stop_event.is_set():
            try:
                # Get current events from buffer and clear it
                events = self.keystroke_recorder.get_buffer_contents(clear=True)
                
                if events:
                    # Process events to sanitize passwords
                    sanitized_data = self.keystroke_sanitizer.process_events(events)
                    
                    # Save sanitized data to log file
                    self.keystroke_sanitizer.save_to_log(sanitized_data, self.log_file)
                    
                    logger.debug(f"Processed {len(events)} events, found {len(sanitized_data['password_locations'])} password instances")
            
            except Exception as e:
                logger.error(f"Error processing keystroke buffer: {e}")
            
            # Sleep until next processing interval
            time.sleep(self.process_interval)
    
    def start(self):
        """Start data collection"""
        if self.running:
            return
        
        self.running = True
        self.stop_event.clear()
        
        # Start keystroke recorder
        self.keystroke_recorder.start()
        logger.info("Keystroke recorder started")
        
        # Start screen recorder if enabled
        if self.screen_recorder:
            self.screen_recorder.start()
            logger.info("Screen recorder started")
        
        # Start processing thread
        self.processing_thread = threading.Thread(
            target=self._process_buffer,
            daemon=True
        )
        self.processing_thread.start()
        
        logger.info("Data collection started")
    
    def stop(self):
        """Stop data collection"""
        if not self.running:
            return
        
        # Signal processing thread to stop
        self.stop_event.set()
        
        # Stop keystroke recorder
        self.keystroke_recorder.stop()
        
        # Stop screen recorder if enabled
        if self.screen_recorder:
            self.screen_recorder.stop()
        
        # Process any remaining events
        events = self.keystroke_recorder.get_buffer_contents()
        if events:
            sanitized_data = self.keystroke_sanitizer.process_events(events)
            self.keystroke_sanitizer.save_to_log(sanitized_data, self.log_file)
        
        self.running = False
        logger.info("Data collection stopped")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Data collection for ML research")
    parser.add_argument("--no-screen", action="store_true", help="Disable screen recording")
    parser.add_argument("--screen-minutes", type=int, default=10, help="Minutes to keep in rolling screen recording")
    parser.add_argument("--screen-fps", type=int, default=5, help="Frames per second for screen recording")
    parser.add_argument("--output-dir", type=str, default="logs", help="Output directory for logs")
    parser.add_argument("--process-interval", type=int, default=10, help="Seconds between processing buffer")
    parser.add_argument("--add-password", type=str, help="Add a password to sanitize")
    args = parser.parse_args()
    
    # Create data collector
    collector = DataCollector(
        output_dir=args.output_dir,
        screen_record=not args.no_screen,
        screen_window_minutes=args.screen_minutes,
        screen_fps=args.screen_fps,
        process_interval=args.process_interval
    )
    
    # Set up encryption
    password = input("Enter encryption password: ")
    if not collector.setup(password):
        print("Failed to set up data collector")
        return
    
    # Add password if provided
    if args.add_password:
        collector.add_password(args.add_password)
    
    # Start collection
    collector.start()
    
    print("Data collection started. Press Ctrl+C to stop...")
    try:
        # Keep the main thread running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping data collection...")
        collector.stop()
        print("Data collection stopped")


if __name__ == "__main__":
    main()