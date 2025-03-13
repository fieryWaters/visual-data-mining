"""
TextBuffer Tests - Tests the TextBuffer utility for keystroke processing and text editing.
"""

import unittest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.text_buffer import TextBuffer


class TestTextBuffer(unittest.TestCase):
    """Tests for the TextBuffer utility"""
    
    def setUp(self):
        """Create a fresh TextBuffer for each test"""
        self.buffer = TextBuffer()
    
    def type_string(self, text):
        """Helper to type a string of characters"""
        for char in text:
            self.buffer.process_keystroke(char)
        return self.buffer.get_text()
            
    def test_simple_typing(self):
        """Test basic typing and buffer state tracking"""
        # Type "Hello"
        self.buffer.process_keystroke("H")
        self.buffer.process_keystroke("e")
        self.buffer.process_keystroke("l")
        self.buffer.process_keystroke("l")
        self.buffer.process_keystroke("o")
        
        # Verify text, cursor, and state history
        self.assertEqual(self.buffer.get_text(), "Hello", "Buffer should contain the typed text")
        self.assertEqual(self.buffer.get_cursor_position(), 5, "Cursor should be at the end")
        
        # Check buffer states
        expected_states = ["H", "He", "Hel", "Hell", "Hello"]
        self.assertEqual(self.buffer.get_buffer_states(), expected_states, 
                         "Buffer states should track each keystroke")
    
    def test_backspace(self):
        """Test backspace functionality"""
        # Type "Hello", then backspace twice
        self.type_string("Hello")
        self.buffer.process_keystroke("Key.backspace")
        self.buffer.process_keystroke("Key.backspace")
        
        # Verify text and cursor after backspace
        self.assertEqual(self.buffer.get_text(), "Hel", "Backspace should remove characters")
        self.assertEqual(self.buffer.get_cursor_position(), 3, "Cursor should be at position 3")
        
        # Type more after backspace
        self.buffer.process_keystroke("p")
        self.assertEqual(self.buffer.get_text(), "Help", "Should be able to type after backspace")
    
    def test_cursor_movement(self):
        """Test cursor movement and text insertion at cursor position"""
        # Type "Hello"
        self.type_string("Hello")
        
        # Move cursor to beginning with Home key
        self.buffer.process_keystroke("Key.home")
        self.assertEqual(self.buffer.get_cursor_position(), 0, "Home key should move cursor to start")
        
        # Type at beginning of text
        self.buffer.process_keystroke("X")
        self.assertEqual(self.buffer.get_text(), "XHello", "Should insert at cursor position")
        
        # Move right twice and insert in middle
        self.buffer.process_keystroke("Key.right")
        self.buffer.process_keystroke("Key.right")
        self.assertEqual(self.buffer.get_cursor_position(), 3, "Right arrow should move cursor right")
        
        self.buffer.process_keystroke("Y")
        self.assertEqual(self.buffer.get_text(), "XHeYllo", "Should insert at cursor position")
        
        # Move to end
        self.buffer.process_keystroke("Key.end")
        self.assertEqual(self.buffer.get_cursor_position(), 7, "End key should move cursor to end")
    
    def test_special_keys(self):
        """Test space, enter, and delete keys"""
        # Test space key
        self.type_string("Hi")
        self.buffer.process_keystroke("Key.space")
        self.type_string("there")
        self.assertEqual(self.buffer.get_text(), "Hi there", "Space should insert a space")
        
        # Test enter key
        self.buffer.process_keystroke("Key.enter")
        self.type_string("World")
        self.assertEqual(self.buffer.get_text(), "Hi there\nWorld", 
                         "Enter should insert a newline")
        
        # Test delete key
        self.buffer.process_keystroke("Key.home")  # Go to beginning
        self.buffer.process_keystroke("Key.delete")  # Delete 'H'
        self.assertEqual(self.buffer.get_text(), "i there\nWorld", 
                         "Delete should remove character at cursor")
    
    def test_clear(self):
        """Test clearing the buffer"""
        # Type some text
        self.type_string("Hello World")
        
        # Clear the buffer
        self.buffer.clear()
        
        # Verify everything is reset
        self.assertEqual(self.buffer.get_text(), "", "Buffer should be empty after clear")
        self.assertEqual(self.buffer.get_cursor_position(), 0, "Cursor should be at start after clear")
        self.assertEqual(self.buffer.get_buffer_states(), [], "Buffer states should be empty after clear")
    
    def test_events_to_text(self):
        """Test converting keystroke events to text"""
        # Create mock keystroke events
        events = []
        for char in "Hello World":
            events.append({"event": "KEY_PRESS", "key": char if char != ' ' else "Key.space"})
            events.append({"event": "KEY_RELEASE", "key": char if char != ' ' else "Key.space"})
        
        # Convert events to text
        text, buffer_states, positions_map, related_events = TextBuffer.events_to_text(events)
        
        # Verify results
        self.assertEqual(text, "Hello World", "Should convert events to correct text")
        self.assertEqual(len(buffer_states), 11, "Should have the correct number of buffer states")
        self.assertEqual(buffer_states[-1], "Hello World", "Final buffer state should be correct")


if __name__ == "__main__":
    unittest.main(verbosity=2)