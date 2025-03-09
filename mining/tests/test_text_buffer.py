"""
Tests for the TextBuffer utility class
"""

import unittest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.text_buffer import TextBuffer


class TestTextBuffer(unittest.TestCase):
    """Tests for the TextBuffer utility"""
    
    def setUp(self):
        """Set up a new TextBuffer for each test"""
        self.buffer = TextBuffer()
    
    def test_simple_typing(self):
        """Test typing simple text"""
        # Type "Hello"
        self.buffer.process_keystroke("H")
        self.buffer.process_keystroke("e")
        self.buffer.process_keystroke("l")
        self.buffer.process_keystroke("l")
        self.buffer.process_keystroke("o")
        
        self.assertEqual(self.buffer.get_text(), "Hello", "Buffer should contain the typed text")
        self.assertEqual(self.buffer.get_cursor_position(), 5, "Cursor should be at the end")
        
        # Check buffer states
        buffer_states = self.buffer.get_buffer_states()
        self.assertEqual(len(buffer_states), 5, "Should have 5 buffer states")
        self.assertEqual(buffer_states, ["H", "He", "Hel", "Hell", "Hello"], 
                        "Buffer states should track each keystroke")
    
    def test_backspace(self):
        """Test backspace functionality"""
        # Type "Hello" then backspace twice
        for char in "Hello":
            self.buffer.process_keystroke(char)
        
        self.buffer.process_keystroke("Key.backspace")
        self.buffer.process_keystroke("Key.backspace")
        
        self.assertEqual(self.buffer.get_text(), "Hel", "Backspace should remove characters")
        self.assertEqual(self.buffer.get_cursor_position(), 3, "Cursor should be at position 3")
        
        # Type more characters
        self.buffer.process_keystroke("p")
        
        self.assertEqual(self.buffer.get_text(), "Help", "Should be able to type after backspace")
    
    def test_cursor_movement(self):
        """Test cursor movement with arrow keys"""
        # Type "Hello"
        for char in "Hello":
            self.buffer.process_keystroke(char)
        
        # Move cursor to beginning
        self.buffer.process_keystroke("Key.home")
        self.assertEqual(self.buffer.get_cursor_position(), 0, "Home key should move cursor to start")
        
        # Type at beginning
        self.buffer.process_keystroke("X")
        self.assertEqual(self.buffer.get_text(), "XHello", "Should insert at cursor position")
        
        # Move right twice
        self.buffer.process_keystroke("Key.right")
        self.buffer.process_keystroke("Key.right")
        self.assertEqual(self.buffer.get_cursor_position(), 3, "Right arrow should move cursor right")
        
        # Insert in middle
        self.buffer.process_keystroke("Y")
        self.assertEqual(self.buffer.get_text(), "XHeYllo", "Should insert at cursor position")
        
        # Move to end
        self.buffer.process_keystroke("Key.end")
        self.assertEqual(self.buffer.get_cursor_position(), 7, "End key should move cursor to end")
    
    def test_special_keys(self):
        """Test handling of special keys"""
        # Test space
        self.buffer.process_keystroke("H")
        self.buffer.process_keystroke("i")
        self.buffer.process_keystroke("Key.space")
        self.buffer.process_keystroke("t")
        self.buffer.process_keystroke("h")
        self.buffer.process_keystroke("e")
        self.buffer.process_keystroke("r")
        self.buffer.process_keystroke("e")
        
        self.assertEqual(self.buffer.get_text(), "Hi there", "Space should insert a space")
        
        # Test enter
        self.buffer.process_keystroke("Key.enter")
        self.buffer.process_keystroke("W")
        self.buffer.process_keystroke("o")
        self.buffer.process_keystroke("r")
        self.buffer.process_keystroke("l")
        self.buffer.process_keystroke("d")
        
        self.assertEqual(self.buffer.get_text(), "Hi there\nWorld", "Enter should insert a newline")
        
        # Test delete
        self.buffer.process_keystroke("Key.home")  # Go to beginning
        self.buffer.process_keystroke("Key.delete")  # Delete 'H'
        
        self.assertEqual(self.buffer.get_text(), "i there\nWorld", "Delete should remove character at cursor")
    
    def test_clear(self):
        """Test clearing the buffer"""
        for char in "Hello World":
            self.buffer.process_keystroke(char)
        
        self.buffer.clear()
        
        self.assertEqual(self.buffer.get_text(), "", "Buffer should be empty after clear")
        self.assertEqual(self.buffer.get_cursor_position(), 0, "Cursor should be at start after clear")
        self.assertEqual(self.buffer.get_buffer_states(), [], "Buffer states should be empty after clear")
    
    def test_events_to_text(self):
        """Test converting keystroke events to text"""
        events = [
            {"event": "KEY_PRESS", "key": "H"},
            {"event": "KEY_RELEASE", "key": "H"},
            {"event": "KEY_PRESS", "key": "e"},
            {"event": "KEY_RELEASE", "key": "e"},
            {"event": "KEY_PRESS", "key": "l"},
            {"event": "KEY_RELEASE", "key": "l"},
            {"event": "KEY_PRESS", "key": "l"},
            {"event": "KEY_RELEASE", "key": "l"},
            {"event": "KEY_PRESS", "key": "o"},
            {"event": "KEY_RELEASE", "key": "o"},
            {"event": "KEY_PRESS", "key": "Key.space"},
            {"event": "KEY_RELEASE", "key": "Key.space"},
            {"event": "KEY_PRESS", "key": "W"},
            {"event": "KEY_RELEASE", "key": "W"},
            {"event": "KEY_PRESS", "key": "o"},
            {"event": "KEY_RELEASE", "key": "o"},
            {"event": "KEY_PRESS", "key": "r"},
            {"event": "KEY_RELEASE", "key": "r"},
            {"event": "KEY_PRESS", "key": "l"},
            {"event": "KEY_RELEASE", "key": "l"},
            {"event": "KEY_PRESS", "key": "d"},
            {"event": "KEY_RELEASE", "key": "d"}
        ]
        
        text, buffer_states = TextBuffer.events_to_text(events)
        
        self.assertEqual(text, "Hello World", "Should convert events to correct text")
        self.assertEqual(len(buffer_states), 11, "Should have the correct number of buffer states")


if __name__ == "__main__":
    unittest.main()