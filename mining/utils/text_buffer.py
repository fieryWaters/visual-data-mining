"""
Text buffer utility for handling keystroke-to-text conversion.
Manages cursor position, editing operations, and maintains buffer state history.
"""

class TextBuffer:
    """
    A text buffer that handles keystroke-to-text conversion with cursor tracking
    """
    
    def __init__(self):
        """Initialize an empty text buffer with cursor at position 0"""
        self.buffer = ""
        self.cursor_pos = 0
        self.buffer_states = []
        
    def process_keystroke(self, key):
        """
        Process a keystroke and update the buffer
        
        Args:
            key: Key pressed (string representation)
            
        Returns:
            bool: True if buffer was modified, False otherwise
        """
        modified = False
        
        if key == "Key.space":
            # Insert space at cursor position
            self.buffer = self.buffer[:self.cursor_pos] + " " + self.buffer[self.cursor_pos:]
            self.cursor_pos += 1
            modified = True
        elif key == "Key.enter":
            # Insert newline at cursor position
            self.buffer = self.buffer[:self.cursor_pos] + "\n" + self.buffer[self.cursor_pos:]
            self.cursor_pos += 1
            modified = True
        elif key == "Key.backspace":
            # Handle backspace
            if self.cursor_pos > 0:
                self.buffer = self.buffer[:self.cursor_pos-1] + self.buffer[self.cursor_pos:]
                self.cursor_pos -= 1
                modified = True
        elif key == "Key.delete":
            # Handle delete
            if self.cursor_pos < len(self.buffer):
                self.buffer = self.buffer[:self.cursor_pos] + self.buffer[self.cursor_pos+1:]
                modified = True
        elif key == "Key.left":
            # Move cursor left
            self.cursor_pos = max(0, self.cursor_pos - 1)
        elif key == "Key.right":
            # Move cursor right
            self.cursor_pos = min(len(self.buffer), self.cursor_pos + 1)
        elif key == "Key.home":
            # Move cursor to start
            self.cursor_pos = 0
        elif key == "Key.end":
            # Move cursor to end
            self.cursor_pos = len(self.buffer)
        elif not key.startswith("Key."):
            # Regular character - insert at cursor position
            self.buffer = self.buffer[:self.cursor_pos] + key + self.buffer[self.cursor_pos:]
            self.cursor_pos += 1
            modified = True
            
        # If buffer was modified, save the state
        if modified and self.buffer:
            self.buffer_states.append(self.buffer)
            
        return modified
    
    def get_text(self):
        """Get the current text in the buffer"""
        return self.buffer
        
    def get_buffer_states(self):
        """Get the history of buffer states"""
        return self.buffer_states
        
    def clear(self):
        """Clear the buffer and history"""
        self.buffer = ""
        self.cursor_pos = 0
        self.buffer_states = []

    def get_cursor_position(self):
        """Get the current cursor position"""
        return self.cursor_pos
        
    @staticmethod
    def events_to_text(events):
        """
        Convert keystroke events to text using the buffer
        
        Args:
            events: List of keystroke events
            
        Returns:
            tuple: (final_text, buffer_states)
        """
        buffer = TextBuffer()
        
        for event in events:
            if event["event"] != "KEY_PRESS":
                continue
                
            key = event.get("key", "")
            buffer.process_keystroke(key)
            
        return buffer.get_text(), buffer.get_buffer_states()