import os
import json
import threading
from datetime import datetime
from pynput import keyboard, mouse
from PIL import ImageGrab

# Create directories if they don't exist.
os.makedirs("screenshots", exist_ok=True)
os.makedirs("logs", exist_ok=True)
LOG_FILE = os.path.join("logs", "interaction_log.jsonl")  # JSON Lines file

def write_log(record):
    record["timestamp"] = datetime.now().isoformat()
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(record) + "\n")

class ClickTracker:
    def __init__(self, threshold=0.3):
        self.pending_click = None  # Store details of the first click
        self.pending_timer = None  # Timer for double-click detection
        self.threshold = threshold  # Double-click detection threshold in seconds

    def clear_pending(self):
        """Clear the pending click after the double-click threshold expires."""
        self.pending_click = None
        self.pending_timer = None

    def on_click(self, x, y, button, pressed):
        if not pressed:
            return  # Only process press events

        xi = int(x)
        yi = int(y)

        if self.pending_click is None:
            # First click: take screenshot and log it
            self.pending_click = (xi, yi, button)
            screenshot_path = f"screenshots/screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            ImageGrab.grab().save(screenshot_path)
            write_log({
                "event": "CLICK",
                "button": str(button),
                "x": xi,
                "y": yi,
                "screenshot": screenshot_path
            })
            # Start a timer to wait for a potential second click
            self.pending_timer = threading.Timer(self.threshold, self.clear_pending)
            self.pending_timer.start()
        else:
            # Second click within the threshold: log it without taking a screenshot
            write_log({
                "event": "CLICK",
                "button": str(button),
                "x": xi,
                "y": yi,
                "note": "Second click within double-click threshold"
            })
            # Cancel the pending timer and clear pending state
            if self.pending_timer:
                self.pending_timer.cancel()
            self.clear_pending()

def on_key_press(key):
    try:
        key_val = key.char
    except AttributeError:
        key_val = str(key)
    write_log({
        "event": "KEY_PRESS",
        "key": key_val
    })

def on_scroll(x, y, dx, dy):
    xi = int(x)
    yi = int(y)
    write_log({
        "event": "SCROLL",
        "x": xi,
        "y": yi,
        "dx": int(dx),
        "dy": int(dy),
        "direction": "up" if dy > 0 else "down"
    })

def main():
    tracker = ClickTracker(threshold=0.3)
    mouse_listener = mouse.Listener(on_click=tracker.on_click, on_scroll=on_scroll)
    keyboard_listener = keyboard.Listener(on_press=on_key_press)
    mouse_listener.start()
    keyboard_listener.start()
    mouse_listener.join()
    keyboard_listener.join()

if __name__ == "__main__":
    main()
