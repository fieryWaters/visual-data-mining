"""
Real-time keystroke recording module.
Captures keystrokes, mouse clicks and scrolls in memory buffer.
"""

import threading
from datetime import datetime
from pynput import keyboard, mouse
from collections import deque
import queue

class KeystrokeBuffer:
    """Thread-safe buffer for storing keystroke and mouse events"""
    
    def __init__(self, max_size=10000):
        """Initialize buffer with maximum size limit"""
        self.buffer = deque(maxlen=max_size)
        self.lock = threading.Lock()
    
    def add_event(self, event):
        """Add an event to the buffer with timestamp"""
        event["timestamp"] = datetime.now().isoformat()
        with self.lock:
            self.buffer.append(event)
    
    def get_events(self, clear=False):
        """Get all events, optionally clearing the buffer"""
        with self.lock:
            events = list(self.buffer)
            if clear:
                self.buffer.clear()
        return events

class KeystrokeRecorder:
    """Records keystrokes and mouse actions in real-time"""
    
    def __init__(self, buffer_size=10000):
        """
        Initialize recorder with event buffer
        
        Args:
            buffer_size: Maximum number of events to store in the buffer
        """
        self.buffer = KeystrokeBuffer(max_size=buffer_size)
        self.keyboard_listener = None
        self.mouse_listener = None
        self.running = False
        self.pending_click = None
        self.pending_timer = None
        self.dbl_click_threshold = 0.3  # seconds
        self._setup_complete = False

    def on_key_press(self, key):
        """Handle key press events"""
        try:
            # Handle normal characters
            if hasattr(key, 'char'):
                key_val = key.char
            # Handle special keys
            else:
                key_val = f"Key.{key.name}" if hasattr(key, 'name') else str(key)
            
            self.buffer.add_event({
                "event": "KEY_PRESS",
                "key": key_val
            })
        except Exception as e:
            print(f"Error processing key press: {e}")
        
    def on_key_release(self, key):
        """Handle key release events"""
        try:
            # Handle normal characters
            if hasattr(key, 'char'):
                key_val = key.char
            # Handle special keys
            else:
                key_val = f"Key.{key.name}" if hasattr(key, 'name') else str(key)
                
            self.buffer.add_event({
                "event": "KEY_RELEASE",
                "key": key_val
            })
        except Exception as e:
            print(f"Error processing key release: {e}")
        
    def clear_pending(self):
        """Clear the pending click after the double-click threshold expires"""
        self.pending_click = None
        self.pending_timer = None
        
    def on_click(self, x, y, button, pressed):
        """Handle mouse click events"""
        xi, yi = int(x), int(y)
        
        if pressed:
            # Check for double clicks
            if self.pending_click is None:
                self.pending_click = (xi, yi, button)
                
                # Start a timer to wait for potential second click
                self.pending_timer = threading.Timer(
                    self.dbl_click_threshold, 
                    self.clear_pending
                )
                self.pending_timer.start()
                
                # Record single click event
                event = {
                    "event": "MOUSE",
                    "event_type": "SINGLE_CLICK",
                    "button": str(button),
                    "x": xi,
                    "y": yi
                }
            else:
                # Second click within threshold - record as double click
                event = {
                    "event": "MOUSE",
                    "event_type": "DOUBLE_CLICK",
                    "button": str(button),
                    "x": xi,
                    "y": yi
                }
                
                # Cancel the pending timer and clear state
                if self.pending_timer:
                    self.pending_timer.cancel()
                self.clear_pending()
                
            self.buffer.add_event(event)
            
    def on_scroll(self, x, y, dx, dy):
        """Handle mouse scroll events"""
        xi, yi = int(x), int(y)
        
        self.buffer.add_event({
            "event": "MOUSE",
            "event_type": "SCROLL",
            "x": xi,
            "y": yi,
            "dx": int(dx),
            "dy": int(dy),
            "direction": "up" if dy > 0 else "down"
        })
    def start(self):
        """Start recording keystrokes and mouse actions"""
        if self.running:
            return
            
        self.keyboard_listener = keyboard.Listener(
            on_press=self.on_key_press,
            on_release=self.on_key_release
        )
        
        self.mouse_listener = mouse.Listener(
            on_click=self.on_click,
            on_scroll=self.on_scroll
        )
        
        self.keyboard_listener.start()
        self.mouse_listener.start()
        self.running = True
        
    def stop(self):
        """Stop recording keystrokes and mouse actions"""
        if not self.running:
            return
            
        if self.keyboard_listener:
            self.keyboard_listener.stop()
            
        if self.mouse_listener:
            self.mouse_listener.stop()
            
        self.running = False
        
    def get_buffer_contents(self, clear=False):
        """Get the contents of the buffer"""
        return self.buffer.get_events(clear)


# Stand-alone test function
def test():
    """Test the keystroke recorder with real-time output"""
    recorder = KeystrokeRecorder()
    
    # Create a custom event handler to print events in real-time
    def event_printer():
        last_count = 0
        try:
            while recorder.running:
                events = recorder.get_buffer_contents()
                if len(events) > last_count:
                    for event in events[last_count:]:
                        print(event)
                    last_count = len(events)
                import time
                time.sleep(0.1)  # Check for new events every 100ms
        except Exception as e:
            print(f"Printer error: {e}")
    
    recorder.start()
    print("Recording started. Press Ctrl+C to stop...")
    
    # Start the printer in a separate thread
    import threading
    printer_thread = threading.Thread(target=event_printer)
    printer_thread.daemon = True
    printer_thread.start()
    
    try:
        # Keep the main thread running
        while True:
            import time
            time.sleep(0.5)
    except KeyboardInterrupt:
        recorder.stop()
        events = recorder.get_buffer_contents()
        print(f"\nRecording stopped. Total events: {len(events)}")


if __name__ == "__main__":
    test()