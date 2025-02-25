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
    
    def __init__(self, max_frames=300):
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
        """Main recording loop optimized for maximum speed"""
        try:
            # Variables for tracking performance
            frame_count = 0
            start_time = time.time()
            last_report_time = start_time
            
            # Main recording loop - capture as fast as possible
            while not self.stop_event.is_set():
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
                
                # Report stats periodically (every 5 seconds)
                if elapsed >= 5:
                    self.actual_fps = frame_count / elapsed
                    logger.info(f"Screen recording at {self.actual_fps:.2f} FPS, buffer: {len(self.frames)} frames, memory: {self.get_memory_usage_mb():.1f} MB")
                    frame_count = 0
                    last_report_time = current_time
                
        except Exception as e:
            logger.error(f"Error in recording thread: {e}")
    
    def start(self):
        """Start recording the screen to memory"""
        if self.running:
            return
        
        # Clear any existing frames
        with self.lock:
            self.frames = []
            self.frame_times = []
        
        self.running = True
        self.stop_event.clear()
        
        # Start recording thread
        self.recording_thread = threading.Thread(
            target=self._recording_loop,
            daemon=True
        )
        self.recording_thread.start()
        
        logger.info("In-memory screen recording started (maximum speed)")
    
    def stop(self):
        """Stop recording the screen"""
        if not self.running:
            return
        
        # Signal thread to stop
        self.stop_event.set()
        
        # Wait for recording thread to finish
        if self.recording_thread:
            self.recording_thread.join(timeout=2)
            self.recording_thread = None
        
        self.running = False
        logger.info(f"Screen recording stopped. Stored {len(self.frames)} frames ({self.get_memory_usage_mb():.1f} MB)")
    
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
    
    def save_frames_to_disk(self, output_dir, count=None, format='png'):
        """
        Save captured frames to disk.
        
        Args:
            output_dir: Directory to save images
            count: Number of recent frames to save (None = all)
            format: Image format ('png' or 'jpg')
        
        Returns:
            List of saved file paths
        """
        os.makedirs(output_dir, exist_ok=True)
        
        # Get frames to save
        frames_to_save = self.get_recent_frames(count=count)
        
        saved_files = []
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
            
        logger.info(f"Saved {len(saved_files)} frames to {output_dir}")
        return saved_files



# Test function 
def test():
    """Test the in-memory screen recorder"""
    # Configuration
    max_frames = 300    # Keep up to 300 frames in memory
    duration = 10       # Run for 10 seconds
    
    print("\n=== TESTING SCREEN RECORDER (MAXIMUM SPEED) ===")
    print(f"Settings: max_frames={max_frames}, duration={duration}s")
    
    # Create and start recorder
    recorder = InMemoryScreenRecorder(max_frames=max_frames)
    recorder.start()
    
    # Show progress
    for i in range(duration):
        if i % 5 == 0:
            # Every 5 seconds, show buffer stats
            buffer_size = len(recorder.frames) if hasattr(recorder, 'frames') else 0
            memory_usage = recorder.get_memory_usage_mb() if buffer_size > 0 else 0
            print(f"Status: Recording for {i} seconds, buffer size: {buffer_size} frames, memory: {memory_usage:.2f} MB")
        time.sleep(1)
    
    # Stop recording
    recorder.stop()
    
    # Show stats
    buffer_size = len(recorder.frames)
    memory_usage = recorder.get_memory_usage_mb()
    print(f"\nRecording stopped after {duration} seconds")
    print(f"Final buffer: {buffer_size} frames, memory usage: {memory_usage:.2f} MB")
    print(f"Actual FPS: {buffer_size/duration:.2f}")
    
    # Save captured frames
    output_dir = os.path.join(os.getcwd(), 'memory_captures')
    print(f"\nSaving frames to {output_dir}...")
    saved_files = recorder.save_frames_to_disk(output_dir, format='jpg')
    print(f"Saved {len(saved_files)} frames")
    
    print("\nTest complete.")

if __name__ == "__main__":
    test()