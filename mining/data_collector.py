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
from screen_recorder import InMemoryScreenRecorder

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
                 passwords_file=None,  # Will default to output_dir/secret.keys if None
                 screen_record=True,
                 screen_window_minutes=10,
                 screen_fps=5,
                 process_interval=10,  # Process buffer every 10 seconds
                 buffer_size=10000,
                 save_sanitized_json=True): # Whether to save sanitized JSON stream
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
            save_sanitized_json: Whether to save sanitized JSON stream
        """
        self.output_dir = output_dir
        self.process_interval = process_interval
        self.save_sanitized_json = save_sanitized_json
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Set passwords file path (default to output_dir/secret.keys if not specified)
        if passwords_file is None:
            self.passwords_file = os.path.join(output_dir, 'secret.keys')
        else:
            self.passwords_file = passwords_file
        
        # Initialize components
        self.keystroke_recorder = KeystrokeRecorder(buffer_size=buffer_size)
        self.keystroke_sanitizer = KeystrokeSanitizer(passwords_file=self.passwords_file)
        
        # Initialize screen recorder if enabled
        self.screen_recorder = None
        if screen_record:
            # Calculate max frames based on fps and window minutes
            max_frames = screen_fps * 60 * screen_window_minutes
            self.screen_recorder = InMemoryScreenRecorder(
                max_frames=max_frames
            )
        
        # Internal state
        self.running = False
        self.processing_thread = None
        self.stop_event = threading.Event()
        
        # Log files
        self.log_file = os.path.join(output_dir, 'interaction_log.jsonl')
        self.json_output_dir = os.path.join(output_dir, 'sanitized_json')
    
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
        try:
            if not self.keystroke_sanitizer.load_passwords():
                logger.error("Failed to load passwords - password might be incorrect")
                return False
        except Exception as e:
            logger.error(f"Error loading passwords: {e}")
            logger.error("If this is your first run, you can use --add-password to initialize the password file")
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
        # Create the sanitized JSON directory if needed
        if self.save_sanitized_json:
            os.makedirs(self.json_output_dir, exist_ok=True)
            
        # Initialize session timestamp for filenames
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        buffer_count = 0
        
        while not self.stop_event.is_set():
            try:
                # Get current events from buffer and clear it
                events = self.keystroke_recorder.get_buffer_contents(clear=True)
                
                if events:
                    # Process events to sanitize passwords
                    sanitized_data = self.keystroke_sanitizer.process_events(events)
                    
                    # Save sanitized data to log file (using existing method)
                    self.keystroke_sanitizer.save_to_log(sanitized_data, self.log_file)
                    
                    # Save sanitized data as JSON if enabled
                    if self.save_sanitized_json:
                        # Create a timestamped filename
                        buffer_count += 1
                        json_filename = f"sanitized_{session_id}_{buffer_count:04d}.json"
                        json_path = os.path.join(self.json_output_dir, json_filename)
                        
                        # Save the sanitized JSON
                        if self.keystroke_sanitizer.save_sanitized_json(sanitized_data, json_path):
                            logger.debug(f"Saved sanitized JSON to {json_path}")
                    
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
            
            # Save captured frames to disk
            screen_output_dir = os.path.join(self.output_dir, 'screen_recordings')
            os.makedirs(screen_output_dir, exist_ok=True)
            self.screen_recorder.save_frames_to_disk(screen_output_dir, format='jpg')
            logger.info(f"Saved screen recordings to {screen_output_dir}")
        
        # Process any remaining events
        events = self.keystroke_recorder.get_buffer_contents()
        if events:
            # Process events to sanitize passwords
            sanitized_data = self.keystroke_sanitizer.process_events(events)
            
            # Save sanitized data to log file
            self.keystroke_sanitizer.save_to_log(sanitized_data, self.log_file)
            
            # Save sanitized data as JSON if enabled
            if self.save_sanitized_json:
                # Create a timestamped filename for final buffer
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                json_filename = f"sanitized_{timestamp}_final.json"
                json_path = os.path.join(self.json_output_dir, json_filename)
                
                # Save the sanitized JSON
                if self.keystroke_sanitizer.save_sanitized_json(sanitized_data, json_path):
                    logger.debug(f"Saved final sanitized JSON to {json_path}")
        
        self.running = False
        logger.info("Data collection stopped")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Data collection for ML research")
    parser.add_argument("--no-screen", action="store_true", help="Disable screen recording")
    parser.add_argument("--screen-minutes", type=int, default=10, help="Minutes to keep in rolling screen recording")
    parser.add_argument("--screen-fps", type=int, default=5, help="Target frames per second for screen recording")
    parser.add_argument("--output-dir", type=str, default="logs", help="Output directory for logs")
    parser.add_argument("--process-interval", type=int, default=10, help="Seconds between processing buffer")
    parser.add_argument("--add-password", type=str, help="Add a password to sanitize")
    parser.add_argument("--no-json", action="store_true", help="Disable sanitized JSON output")
    parser.add_argument("--test-mode", action="store_true", help="Run in test mode with simulated data")
    parser.add_argument("--password", type=str, help="Encryption password (use only for testing)")
    parser.add_argument("--duration", type=int, default=30, help="Test duration in seconds")
    args = parser.parse_args()
    
    # Create data collector
    collector = DataCollector(
        output_dir=args.output_dir,
        screen_record=not args.no_screen,
        screen_window_minutes=args.screen_minutes,
        screen_fps=args.screen_fps,
        process_interval=args.process_interval,
        save_sanitized_json=not args.no_json
    )
    
    # Set up encryption
    if args.password:
        password = args.password
    else:
        password = input("Enter encryption password: ")
        
    if not collector.setup(password):
        print("Failed to set up data collector")
        return
    
    # Add password if provided
    if args.add_password:
        collector.add_password(args.add_password)
    
    # Add some test passwords for development
    if args.test_mode:
        collector.add_password("secret123")
        collector.add_password("password123")
        collector.add_password("topsecret")
    
    # Start collection
    collector.start()
    
    print("Data collection started. Press Ctrl+C to stop...")
    try:
        # For test mode, simulate typing including passwords
        if args.test_mode:
            print("RUNNING IN TEST MODE WITH SIMULATED INPUT")
            
            # Import test framework for simulated keystrokes
            from test_sanitizer import generate_mock_keystrokes
            
            # Create test data
            test_cases = [
                {
                    "name": "login_form",
                    "text": "username: testuser\npassword: ",
                    "include_password": True
                },
                {
                    "name": "document_with_password",
                    "text": "Here are some notes about the project.\nDO NOT SHARE!\nWebsite login: admin/",
                    "include_password": True
                }
            ]
            
            # Process each test case (simulate typing)
            for test_case in test_cases:
                print(f"Simulating typing: {test_case['name']}")
                
                # Generate events
                events = generate_mock_keystrokes(test_case)
                
                # Add to recorder buffer directly (bypassing actual keyboard recording)
                for event in events:
                    if event["event"] == "KEY_PRESS":
                        collector.keystroke_recorder.buffer.add_event(event)
                
                # Sleep to allow processing
                time.sleep(2)
            
            # Run for specified duration
            print(f"Test running for {args.duration} seconds...")
            for i in range(args.duration):
                if i % 5 == 0:
                    print(f"{args.duration - i} seconds remaining...")
                time.sleep(1)
        else:
            # Keep the main thread running
            while True:
                time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping data collection...")
    finally:
        collector.stop()
        print("Data collection stopped")


if __name__ == "__main__":
    main()