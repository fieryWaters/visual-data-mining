"""
Screen recording module that captures continuous screen video
with a rolling buffer window.
"""

import os
import cv2
import time
import numpy as np
import threading
from datetime import datetime, timedelta
import pyautogui
from queue import Queue
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


# Original class kept for compatibility
class ScreenRecorder:
    """
    Records the screen continuously with a rolling window of video files.
    """
    
    def __init__(self, output_dir='screen_recordings', 
                 window_minutes=10, fps=5, 
                 codec='mp4v', extension='.mp4'):
        """
        Initialize the screen recorder.
        
        Args:
            output_dir: Directory to save recording files
            window_minutes: Length of rolling window in minutes
            fps: Frames per second to capture
            codec: Video codec (FOURCC code)
            extension: Video file extension
        """
        self.output_dir = output_dir
        self.window_minutes = window_minutes
        self.fps = fps
        self.codec = codec
        self.extension = extension
        
        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Internal state
        self.running = False
        self.recording_thread = None
        self.stop_event = threading.Event()
        self.current_writer = None
        self.current_file = None
        self.start_time = None
        
        # Cleanup old files after window_minutes
        self.cleanup_thread = None
    
    def _create_writer(self):
        """Create a new video writer"""
        # Close existing writer if there is one
        if self.current_writer is not None:
            self.current_writer.release()
        
        # Get screen size
        screen_size = pyautogui.size()
        
        # Create new file and writer
        self.current_file = self._generate_filename()
        fourcc = cv2.VideoWriter_fourcc(*self.codec)
        
        # Create the writer
        self.current_writer = cv2.VideoWriter(
            self.current_file, 
            fourcc, 
            self.fps, 
            (screen_size.width, screen_size.height)
        )
        
        logger.info(f"Started new recording: {self.current_file}")
        self.start_time = time.time()
    
    def _cleanup_old_files(self):
        """Clean up old video files outside the rolling window"""
        while not self.stop_event.is_set():
            try:
                current_time = time.time()
                cutoff_time = current_time - (self.window_minutes * 60)
                
                # Find all video files
                video_files = [
                    os.path.join(self.output_dir, f) 
                    for f in os.listdir(self.output_dir) 
                    if f.endswith(self.extension)
                ]
                
                # Remove files older than the cutoff
                for video_file in video_files:
                    # Skip the current file
                    if video_file == self.current_file:
                        continue
                        
                    # Check file modification time
                    file_time = os.path.getmtime(video_file)
                    if file_time < cutoff_time:
                        logger.info(f"Removing old recording: {os.path.basename(video_file)}")
                        os.remove(video_file)
            
            except Exception as e:
                logger.error(f"Error in cleanup thread: {e}")
            
            # Sleep for a while before checking again
            time.sleep(60)  # Check every minute
    
    def _recording_loop(self):
        """Main recording loop"""
        try:
            self._create_writer()
            
            # Track frame timing to maintain consistent FPS
            frame_time = 1.0 / self.fps
            next_frame_time = time.time()
            
            while not self.stop_event.is_set():
                current_time = time.time()
                
                # Check if we need to start a new file (every 10 seconds for testing)
                elapsed = current_time - self.start_time
                if elapsed >= 10:  # Create a new file every 10 seconds
                    self._create_writer()
                
                # Sleep until next frame time
                if current_time < next_frame_time:
                    time.sleep(next_frame_time - current_time)
                
                # Capture screen and write frame
                screenshot = pyautogui.screenshot()
                frame = np.array(screenshot)
                # Convert RGB to BGR (for OpenCV)
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                
                # Write the frame
                self.current_writer.write(frame)
                
                # Calculate next frame time
                next_frame_time = time.time() + frame_time
        
        except Exception as e:
            logger.error(f"Error in recording thread: {e}")
        
        finally:
            # Clean up resources
            if self.current_writer is not None:
                self.current_writer.release()
                self.current_writer = None
    
    def start(self):
        """Start recording the screen"""
        if self.running:
            return
        
        self.running = True
        self.stop_event.clear()
        
        # Start recording thread
        self.recording_thread = threading.Thread(
            target=self._recording_loop,
            daemon=True
        )
        self.recording_thread.start()
        
        # Start cleanup thread
        self.cleanup_thread = threading.Thread(
            target=self._cleanup_old_files,
            daemon=True
        )
        self.cleanup_thread.start()
        
        logger.info(f"Screen recording started (window: {self.window_minutes} minutes, FPS: {self.fps})")
    
    def stop(self):
        """Stop recording the screen"""
        if not self.running:
            return
        
        # Signal threads to stop
        self.stop_event.set()
        
        # Wait for recording thread to finish
        if self.recording_thread:
            self.recording_thread.join(timeout=5)
            self.recording_thread = None
        
        # Cleanup resources
        if self.current_writer:
            self.current_writer.release()
            self.current_writer = None
        
        self.running = False
        logger.info("Screen recording stopped")

# Test function for in-memory recorder
def test_memory_recorder():
    """Test the in-memory screen recorder"""
    # Configuration
    max_frames = 300    # Keep up to 300 frames in memory
    duration = 10       # Run for 10 seconds
    
    print("\n=== TESTING IN-MEMORY SCREEN RECORDER (MAXIMUM SPEED) ===")
    print(f"Settings: max_frames={max_frames}")
    
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

# Performance diagnostics test function 
def test_screenshots():
    """Test screen capture performance by isolating bottlenecks"""
    # Use current directory for output
    output_dir = os.path.join(os.getcwd(), 'screen_captures')
    os.makedirs(output_dir, exist_ok=True)
    print(f"Saving screenshots to: {output_dir}")
    
    # Test parameters
    capture_count = 20
    test_modes = [
        "capture_only",            # Just take screenshots without saving
        "capture_and_save",        # Take screenshots and save to disk
        "capture_save_compressed", # Take screenshots and save with compression
        "capture_memory_only"      # Take screenshots and keep in memory
    ]
    
    print("\n=== PERFORMANCE DIAGNOSTICS ===")
    
    for mode in test_modes:
        print(f"\nTesting mode: {mode}")
        
        mode_dir = os.path.join(output_dir, mode)
        os.makedirs(mode_dir, exist_ok=True)
        
        # Warm-up
        _ = pyautogui.screenshot()
        
        screenshots = []
        start_time = time.time()
        frame_count = 0
        
        # Time each operation precisely
        capture_time = 0
        processing_time = 0
        save_time = 0
        
        for i in range(capture_count):
            # Measure screenshot capture time
            capture_start = time.time()
            screenshot = pyautogui.screenshot()
            capture_end = time.time()
            capture_time += (capture_end - capture_start)
            
            # Process differently based on test mode
            processing_start = time.time()
            
            if mode == "capture_only":
                # Just capture, don't save
                pass
                
            elif mode == "capture_and_save":
                # Save with default settings
                filename = os.path.join(mode_dir, f"screen_{i}.png")
                save_start = time.time()
                screenshot.save(filename)
                save_end = time.time()
                save_time += (save_end - save_start)
                
            elif mode == "capture_save_compressed":
                # Save with compression - convert RGBA to RGB for JPEG
                filename = os.path.join(mode_dir, f"screen_{i}.jpg")
                save_start = time.time()
                rgb_image = screenshot.convert('RGB')
                rgb_image.save(filename, quality=85, optimize=True)
                save_end = time.time()
                save_time += (save_end - save_start)
                
            elif mode == "capture_memory_only":
                # Keep in memory
                screenshots.append(screenshot)
            
            processing_end = time.time()
            processing_time += (processing_end - processing_start)
            
            frame_count += 1
            
            # Report progress for longer tests
            if i % 5 == 0:
                print(f"Progress: {i}/{capture_count}")
        
        # Report detailed timing
        elapsed = time.time() - start_time
        fps = frame_count / elapsed
        
        print(f"\nDetailed timing:")
        print(f"- Total time: {elapsed:.4f} sec for {frame_count} frames (FPS: {fps:.2f})")
        print(f"- Average capture time: {(capture_time/frame_count)*1000:.2f} ms")
        print(f"- Average processing time: {(processing_time/frame_count)*1000:.2f} ms")
        if mode in ["capture_and_save", "capture_save_compressed"]:
            print(f"- Average save time: {(save_time/frame_count)*1000:.2f} ms")
    
    print("\nTest complete. Screenshots saved to:", output_dir)
    
# Original test function for video recording
def test():
    """Test the screen recorder"""
    recorder = ScreenRecorder(window_minutes=1, fps=10)
    recorder.start()
    
    try:
        print("Recording screen. Press Ctrl+C to stop...")
        # Keep the main thread running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        recorder.stop()
        print("Recording stopped")

if __name__ == "__main__":
    test_memory_recorder()