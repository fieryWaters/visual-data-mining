import os
import time
import threading
from datetime import datetime
from pynput import keyboard, mouse
from PIL import ImageGrab

# Ensure required directories exist
os.makedirs("screenshots", exist_ok=True)
os.makedirs("logs", exist_ok=True)
LOG_FILE = os.path.join("logs", "interaction_log.txt")

class ClickTracker:
    def __init__(self, threshold=0.3):
        self.pending_click = None
        self.pending_timer = None
        self.threshold = threshold

    def clear_pending(self):
        self.pending_click = None
        self.pending_timer = None

    def on_click(self, x, y, button, pressed):
        if not pressed:
            return  # Only process press events

        current_time = time.time()
        if self.pending_click is None:
            # First click: take screenshot and log a single click
            self.pending_click = (x, y, button, current_time)
            screenshot_path = f"screenshots/screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            ImageGrab.grab().save(screenshot_path)
            with open(LOG_FILE, "a") as f:
                f.write(f"SINGLE_CLICK: {datetime.now()} - {button} at ({x}, {y}), saved to {screenshot_path}\n")
            self.pending_timer = threading.Timer(self.threshold, self.clear_pending)
            self.pending_timer.start()
        else:
            # Second click within threshold? Log as double click without a new screenshot.
            if (current_time - self.pending_click[3]) <= self.threshold:
                if self.pending_timer:
                    self.pending_timer.cancel()
                with open(LOG_FILE, "a") as f:
                    f.write(f"DOUBLE_CLICK: {datetime.now()} - {button} at ({x}, {y})\n")
            self.clear_pending()

def on_key_press(key):
    try:
        k = key.char
    except AttributeError:
        k = str(key)
    with open(LOG_FILE, "a") as f:
        f.write(f"KEY_PRESS: {datetime.now()} - {k}\n")

def main():
    tracker = ClickTracker(threshold=0.3)
    mouse_listener = mouse.Listener(on_click=tracker.on_click)
    key_listener = keyboard.Listener(on_press=on_key_press)
    
    mouse_listener.start()
    key_listener.start()
    mouse_listener.join()
    key_listener.join()

if __name__ == "__main__":
    main()
