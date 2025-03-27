"""
Screen recording module that captures continuous screenshots
with an in-memory rolling buffer for maximum performance.
"""

import os
import time
import threading
from datetime import datetime, timedelta
import pyautogui
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('screen_recorder')

class InMemoryScreenRecorder:
    """
    Records the screen continuously with a rolling window in memory.
    Optimized for performance by keeping everything in RAM.
    """
    
    def __init__(self, max_frames=30):
        """
        Initialize the in-memory screen recorder.
        
        Args:
            max_frames: Maximum number of frames to keep in memory
        """
        # Configuration
        self.max_frames = max_frames
        
        # Memory buffer for screenshots
        self.frames = []
        self.frame_times = []
        self.lock = threading.Lock()
        
        # Internal state
        self.running = False
        self.active = False  # Whether to actually capture screenshots or not
        self.recording_thread = None
        self.stop_event = threading.Event()
        self.actual_fps = 0
        
    def get_memory_usage_mb(self):
        """Estimate memory usage of stored frames in MB"""
        if not self.frames:
            return 0
        
        # Sample first frame
        sample = self.frames[0]
        frame_size = sample.width * sample.height * 4  # RGBA = 4 bytes per pixel
        total_bytes = frame_size * len(self.frames)
        return total_bytes / (1024 * 1024)  # Convert to MB
    
    def _recording_loop(self):
        try:
            # Variables for tracking performance
            frame_count = 0
            start_time = time.time()
            last_report_time = start_time
            
            # Main recording loop - but only capture when active
            while not self.stop_event.is_set():
                # Only take screenshots if in active state
                if self.active:
                    # Take screenshot as fast as the system allows
                    screenshot = pyautogui.screenshot()
                    timestamp = datetime.now().isoformat()
                    
                    # Add to buffer with thread safety
                    with self.lock:
                        self.frames.append(screenshot)
                        self.frame_times.append(timestamp)
                        
                        # Maintain max size by removing oldest frames if needed
                        while len(self.frames) > self.max_frames:
                            self.frames.pop(0)
                            self.frame_times.pop(0)
                    
                    # Update metrics
                    frame_count += 1
                    current_time = time.time()
                    elapsed = current_time - last_report_time
                    
                    """
                    # Report stats periodically (every 5 seconds)
                    if elapsed >= 5:
                        self.actual_fps = frame_count / elapsed
                        logger.info(f"Screen recording at {self.actual_fps:.2f} FPS, buffer: {len(self.frames)} frames, memory: {self.get_memory_usage_mb():.1f} MB")
                        frame_count = 0
                        last_report_time = current_time
                    """
                else:
                    # When not active, just sleep to reduce CPU usage
                    time.sleep(0.1)
                
        except Exception as e:
            logger.error(f"Error in recording thread: {e}")
    
    def start(self):
        """Initialize the screen recorder (but don't start capturing yet)"""
        import time
        
        if self.running:
            return
            
        print("Initializing screen recorder...")
        
        # Clear any existing frames
        with self.lock:
            self.frames = []
            self.frame_times = []
        
        # Wait 1 second before starting
        time.sleep(1)
        
        self.running = True
        # Start with active=False so it doesn't actually capture screenshots yet
        self.active = False
        self.stop_event.clear()
        
        # Start recording thread
        self.recording_thread = threading.Thread(
            target=self._recording_loop,
            daemon=True
        )
        
        # Wait another second before actually starting the thread
        time.sleep(1)
        
        self.recording_thread.start()
        print("Screen recorder thread started successfully (but not capturing)")
    
    def set_active(self, active_state):
        """
        Set whether the recorder should capture screenshots or idle.
        
        Args:
            active_state: True to start capturing, False to pause
        """
        if not self.running:
            print("Warning: Can't activate screen recorder that isn't running")
            return False
            
        # Only log if there's an actual state change
        if self.active != active_state:
            self.active = active_state
            print(f"Screen recorder {'activated' if active_state else 'deactivated'}")
            if active_state:
                # Clear buffer when starting fresh capture
                with self.lock:
                    self.frames = []
                    self.frame_times = []
        
        return True
    
    def stop(self):
        """Pause recording (but keep thread running)"""
        if not self.running:
            return
        
        # Just set to inactive rather than stopping the thread
        self.active = False
        logger.info(f"Screen recording paused. Stored {len(self.frames)} frames ({self.get_memory_usage_mb():.1f} MB)")
    
    def shutdown(self):
        """Completely shut down the screen recorder (for app exit)"""
        if not self.running:
            return
        
        # Signal thread to stop
        self.stop_event.set()
        
        # Wait for recording thread to finish
        if self.recording_thread:
            self.recording_thread.join(timeout=2)
            self.recording_thread = None
        
        self.running = False
        self.active = False
        logger.info(f"Screen recorder shut down. Final buffer had {len(self.frames)} frames ({self.get_memory_usage_mb():.1f} MB)")
    
    def get_recent_frames(self, seconds=None, count=None):
        """
        Get recent frames from the buffer.
        
        Args:
            seconds: If provided, return frames from the last N seconds
            count: If provided, return the last N frames
            
        Returns:
            List of (timestamp, frame) tuples
        """
        with self.lock:
            if not self.frames:
                return []
                
            if seconds is not None:
                # Get frames from the last N seconds
                cutoff_time = datetime.fromisoformat(self.frame_times[-1]) - timedelta(seconds=seconds)
                cutoff_str = cutoff_time.isoformat()
                
                # Find the index of the first frame after the cutoff
                start_idx = 0
                for i, timestamp in enumerate(self.frame_times):
                    if timestamp >= cutoff_str:
                        start_idx = i
                        break
                
                result = list(zip(self.frame_times[start_idx:], self.frames[start_idx:]))
                
            elif count is not None:
                # Get the last N frames
                start_idx = max(0, len(self.frames) - count)
                result = list(zip(self.frame_times[start_idx:], self.frames[start_idx:]))
                
            else:
                # Get all frames
                result = list(zip(self.frame_times, self.frames))
                
            return result
    
    def save_frames_to_disk(self, output_dir, format='png'):
        """
        Save all captured frames to disk and clear the buffer.
        
        Args:
            output_dir: Directory to save images
            format: Image format ('png' or 'jpg')
        
        Returns:
            List of saved file paths
        """
        os.makedirs(output_dir, exist_ok=True)
        
        saved_files = []
        
        # Get all frames and clear the buffer
        with self.lock:
            frames_to_save = list(zip(self.frame_times, self.frames))
            self.frames = []
            self.frame_times = []
        
        for i, (timestamp, frame) in enumerate(frames_to_save):
            # Generate filename
            dt = datetime.fromisoformat(timestamp)
            filename = f"screen_{dt.strftime('%Y%m%d_%H%M%S_%f')}.{format}"
            filepath = os.path.join(output_dir, filename)
            
            # Save the image
            if format.lower() == 'jpg':
                # Convert RGBA to RGB for JPEG
                rgb_frame = frame.convert('RGB')
                rgb_frame.save(filepath, quality=85, optimize=True)
            else:
                frame.save(filepath)
                
            saved_files.append(filepath)
            
        return saved_files



def test2():
    output_dir = os.path.join(os.getcwd(), 'screenshots')
    recorder = InMemoryScreenRecorder(30)
    recorder.start()
    while(True):
        time.sleep(1)
        recorder.save_frames_to_disk(output_dir)

if __name__ == "__main__":
    test2()