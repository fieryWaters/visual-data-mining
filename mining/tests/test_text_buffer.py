"""
TextBuffer Tests
==============

This module tests the TextBuffer utility which is responsible for:
1. Converting keystrokes to text
2. Handling cursor positioning and editing operations
3. Tracking buffer state history for password detection
4. Processing special keys (backspace, arrows, etc.)

The tests verify that the buffer correctly converts keystroke events to text
while properly handling editing operations and special keys.
"""

import unittest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.text_buffer import TextBuffer


class TestTextBuffer(unittest.TestCase):
    """Tests for the TextBuffer utility"""
    
    def setUp(self):
        """
        Set up a new TextBuffer for each test
        
        Creates a fresh TextBuffer instance with empty state
        """
        print("\n" + "="*80)
        self.buffer = TextBuffer()
        print(f"Created new empty TextBuffer")
    
    def test_simple_typing(self):
        """
        TEST 1: Simple Typing
        -------------------
        Tests basic typing functionality to ensure keystrokes are properly
        converted to text and buffer states are tracked.
        
        Expected outcome:
        - Buffer contains the correct text
        - Cursor is positioned at the end
        - Buffer states history is correctly maintained
        """
        print("TEST 1: Simple Typing")
        print("="*80)
        
        print("Typing 'Hello' one character at a time...")
        # Type "Hello"
        self.buffer.process_keystroke("H")
        self.buffer.process_keystroke("e")
        self.buffer.process_keystroke("l")
        self.buffer.process_keystroke("l")
        self.buffer.process_keystroke("o")
        
        # Check buffer contents
        text = self.buffer.get_text()
        position = self.buffer.get_cursor_position()
        print(f"Buffer text: '{text}'")
        print(f"Cursor position: {position}")
        
        self.assertEqual(text, "Hello", "Buffer should contain the typed text")
        if text == "Hello":
            print("  ✓ Buffer contains correct text: 'Hello'")
        else:
            print(f"  ✗ FAIL: Buffer contains '{text}' instead of 'Hello'")
            
        self.assertEqual(position, 5, "Cursor should be at the end")
        if position == 5:
            print("  ✓ Cursor is at the end (position 5)")
        else:
            print(f"  ✗ FAIL: Cursor at position {position} instead of 5")
        
        # Check buffer states
        buffer_states = self.buffer.get_buffer_states()
        print(f"Buffer states history: {buffer_states}")
        
        self.assertEqual(len(buffer_states), 5, "Should have 5 buffer states")
        if len(buffer_states) == 5:
            print("  ✓ Buffer has 5 states (one per character)")
        else:
            print(f"  ✗ FAIL: Buffer has {len(buffer_states)} states instead of 5")
            
        expected_states = ["H", "He", "Hel", "Hell", "Hello"]
        self.assertEqual(buffer_states, expected_states, 
                        "Buffer states should track each keystroke")
        if buffer_states == expected_states:
            print("  ✓ Buffer states match expected progression")
        else:
            print(f"  ✗ FAIL: Buffer states do not match expected progression")
        print("  ✓ All assertions passed")
    
    def test_backspace(self):
        """
        TEST 2: Backspace Functionality
        -----------------------------
        Tests that backspace correctly removes characters and updates the cursor.
        Also verifies that typing can continue after using backspace.
        
        Expected outcome:
        - Characters are deleted when backspace is pressed
        - Cursor position is updated
        - Can continue typing after backspace
        """
        print("TEST 2: Backspace Functionality")
        print("="*80)
        
        # Type "Hello" then backspace twice
        print("Typing 'Hello'...")
        for char in "Hello":
            self.buffer.process_keystroke(char)
            
        print(f"Initial text: '{self.buffer.get_text()}'")
        print(f"Initial cursor position: {self.buffer.get_cursor_position()}")
        
        print("Pressing backspace twice...")
        self.buffer.process_keystroke("Key.backspace")
        self.buffer.process_keystroke("Key.backspace")
        
        # Check text after backspace
        text_after_backspace = self.buffer.get_text()
        position_after_backspace = self.buffer.get_cursor_position()
        print(f"Text after backspace: '{text_after_backspace}'")
        print(f"Cursor position after backspace: {position_after_backspace}")
        
        self.assertEqual(text_after_backspace, "Hel", "Backspace should remove characters")
        if text_after_backspace == "Hel":
            print("  ✓ Text correctly updated to 'Hel' after backspace")
        else:
            print(f"  ✗ FAIL: Text is '{text_after_backspace}' instead of 'Hel'")
            
        self.assertEqual(position_after_backspace, 3, "Cursor should be at position 3")
        if position_after_backspace == 3:
            print("  ✓ Cursor position correctly updated to 3")
        else:
            print(f"  ✗ FAIL: Cursor at position {position_after_backspace} instead of 3")
        
        # Type more characters
        print("Typing 'p' after backspace...")
        self.buffer.process_keystroke("p")
        
        final_text = self.buffer.get_text()
        print(f"Final text: '{final_text}'")
        
        self.assertEqual(final_text, "Help", "Should be able to type after backspace")
        if final_text == "Help":
            print("  ✓ Successfully continued typing after backspace")
        else:
            print(f"  ✗ FAIL: Text is '{final_text}' instead of 'Help'")
        print("  ✓ All assertions passed")
    
    def test_cursor_movement(self):
        """
        TEST 3: Cursor Movement
        ---------------------
        Tests that arrow keys, home, and end keys correctly position the cursor,
        and that text can be inserted at the cursor position.
        
        Expected outcome:
        - Home key moves cursor to start
        - Right arrow moves cursor right
        - End key moves cursor to end
        - Text is inserted at cursor position
        """
        print("TEST 3: Cursor Movement")
        print("="*80)
        
        # Type "Hello"
        print("Typing 'Hello'...")
        for char in "Hello":
            self.buffer.process_keystroke(char)
            
        print(f"Initial text: '{self.buffer.get_text()}'")
        print(f"Initial cursor position: {self.buffer.get_cursor_position()}")
        
        # Move cursor to beginning
        print("Pressing Home key...")
        self.buffer.process_keystroke("Key.home")
        home_position = self.buffer.get_cursor_position()
        print(f"Cursor position after Home: {home_position}")
        
        self.assertEqual(home_position, 0, "Home key should move cursor to start")
        if home_position == 0:
            print("  ✓ Home key correctly moved cursor to position 0")
        else:
            print(f"  ✗ FAIL: Home key moved cursor to {home_position} instead of 0")
        
        # Type at beginning
        print("Typing 'X' at beginning...")
        self.buffer.process_keystroke("X")
        text_after_x = self.buffer.get_text()
        print(f"Text after typing 'X': '{text_after_x}'")
        
        self.assertEqual(text_after_x, "XHello", "Should insert at cursor position")
        if text_after_x == "XHello":
            print("  ✓ Character inserted correctly at cursor position")
        else:
            print(f"  ✗ FAIL: Text is '{text_after_x}' instead of 'XHello'")
        
        # Move right twice
        print("Pressing Right arrow twice...")
        self.buffer.process_keystroke("Key.right")
        self.buffer.process_keystroke("Key.right")
        right_position = self.buffer.get_cursor_position()
        print(f"Cursor position after Right arrows: {right_position}")
        
        self.assertEqual(right_position, 3, "Right arrow should move cursor right")
        if right_position == 3:
            print("  ✓ Right arrows correctly moved cursor to position 3")
        else:
            print(f"  ✗ FAIL: Right arrows moved cursor to {right_position} instead of 3")
        
        # Insert in middle
        print("Typing 'Y' at current position...")
        self.buffer.process_keystroke("Y")
        text_after_y = self.buffer.get_text()
        print(f"Text after typing 'Y': '{text_after_y}'")
        
        self.assertEqual(text_after_y, "XHeYllo", "Should insert at cursor position")
        if text_after_y == "XHeYllo":
            print("  ✓ Character inserted correctly in the middle")
        else:
            print(f"  ✗ FAIL: Text is '{text_after_y}' instead of 'XHeYllo'")
        
        # Move to end
        print("Pressing End key...")
        self.buffer.process_keystroke("Key.end")
        end_position = self.buffer.get_cursor_position()
        print(f"Cursor position after End: {end_position}")
        
        self.assertEqual(end_position, 7, "End key should move cursor to end")
        if end_position == 7:
            print("  ✓ End key correctly moved cursor to end (position 7)")
        else:
            print(f"  ✗ FAIL: End key moved cursor to {end_position} instead of 7")
        print("  ✓ All assertions passed")
    
    def test_special_keys(self):
        """
        TEST 4: Special Keys Handling
        ---------------------------
        Tests handling of special keys like space, enter, and delete.
        
        Expected outcome:
        - Space key inserts a space
        - Enter key inserts a newline
        - Delete key removes character at cursor
        """
        print("TEST 4: Special Keys Handling")
        print("="*80)
        
        # Test space
        print("Testing space key...")
        print("Typing 'Hi'...")
        self.buffer.process_keystroke("H")
        self.buffer.process_keystroke("i")
        
        print("Pressing space key...")
        self.buffer.process_keystroke("Key.space")
        
        print("Typing 'there'...")
        self.buffer.process_keystroke("t")
        self.buffer.process_keystroke("h")
        self.buffer.process_keystroke("e")
        self.buffer.process_keystroke("r")
        self.buffer.process_keystroke("e")
        
        space_text = self.buffer.get_text()
        print(f"Text after space: '{space_text}'")
        
        self.assertEqual(space_text, "Hi there", "Space should insert a space")
        if space_text == "Hi there":
            print("  ✓ Space key correctly inserted a space")
        else:
            print(f"  ✗ FAIL: Text is '{space_text}' instead of 'Hi there'")
        
        # Test enter
        print("\nTesting enter key...")
        print("Pressing enter key...")
        self.buffer.process_keystroke("Key.enter")
        
        print("Typing 'World'...")
        self.buffer.process_keystroke("W")
        self.buffer.process_keystroke("o")
        self.buffer.process_keystroke("r")
        self.buffer.process_keystroke("l")
        self.buffer.process_keystroke("d")
        
        enter_text = self.buffer.get_text()
        print(f"Text after enter: '{enter_text}'")
        
        self.assertEqual(enter_text, "Hi there\nWorld", "Enter should insert a newline")
        if enter_text == "Hi there\nWorld":
            print("  ✓ Enter key correctly inserted a newline")
        else:
            print(f"  ✗ FAIL: Text is '{enter_text}' instead of 'Hi there\\nWorld'")
        
        # Test delete
        print("\nTesting delete key...")
        print("Moving cursor to beginning...")
        self.buffer.process_keystroke("Key.home")  # Go to beginning
        
        print("Pressing delete key...")
        self.buffer.process_keystroke("Key.delete")  # Delete 'H'
        
        delete_text = self.buffer.get_text()
        print(f"Text after delete: '{delete_text}'")
        
        self.assertEqual(delete_text, "i there\nWorld", "Delete should remove character at cursor")
        if delete_text == "i there\nWorld":
            print("  ✓ Delete key correctly removed character at cursor")
        else:
            print(f"  ✗ FAIL: Text is '{delete_text}' instead of 'i there\\nWorld'")
        print("  ✓ All assertions passed")
    
    def test_clear(self):
        """
        TEST 5: Clear Buffer
        -----------------
        Tests clearing the buffer to ensure all state is reset.
        
        Expected outcome:
        - Buffer text is empty
        - Cursor is at position 0
        - Buffer states are empty
        """
        print("TEST 5: Clear Buffer")
        print("="*80)
        
        print("Typing 'Hello World'...")
        for char in "Hello World":
            self.buffer.process_keystroke(char)
            
        print(f"Initial text: '{self.buffer.get_text()}'")
        print(f"Initial cursor position: {self.buffer.get_cursor_position()}")
        print(f"Initial buffer states count: {len(self.buffer.get_buffer_states())}")
        
        print("Clearing the buffer...")
        self.buffer.clear()
        
        # Check buffer after clear
        clear_text = self.buffer.get_text()
        clear_position = self.buffer.get_cursor_position()
        clear_states = self.buffer.get_buffer_states()
        
        print(f"Text after clear: '{clear_text}'")
        print(f"Cursor position after clear: {clear_position}")
        print(f"Buffer states after clear: {clear_states}")
        
        self.assertEqual(clear_text, "", "Buffer should be empty after clear")
        if clear_text == "":
            print("  ✓ Buffer text correctly emptied")
        else:
            print(f"  ✗ FAIL: Buffer text is '{clear_text}' instead of empty")
            
        self.assertEqual(clear_position, 0, "Cursor should be at start after clear")
        if clear_position == 0:
            print("  ✓ Cursor correctly reset to position 0")
        else:
            print(f"  ✗ FAIL: Cursor at position {clear_position} instead of 0")
            
        self.assertEqual(clear_states, [], "Buffer states should be empty after clear")
        if not clear_states:
            print("  ✓ Buffer states correctly emptied")
        else:
            print(f"  ✗ FAIL: Buffer states not empty: {clear_states}")
        print("  ✓ All assertions passed")
    
    def test_events_to_text(self):
        """
        TEST 6: Convert Events to Text
        ----------------------------
        Tests the static method for converting keystroke events to text.
        This simulates the sanitizer processing recorded keystroke events.
        
        Expected outcome:
        - Keystroke events are converted to correct text
        - Buffer states are correctly tracked
        """
        print("TEST 6: Convert Events to Text")
        print("="*80)
        
        print("Creating mock keystroke events for 'Hello World'...")
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
        
        print(f"Converting {len(events)} events to text...")
        text, buffer_states = TextBuffer.events_to_text(events)
        
        print(f"Resulting text: '{text}'")
        print(f"Number of buffer states: {len(buffer_states)}")
        if len(buffer_states) > 0:
            print(f"Final buffer state: '{buffer_states[-1]}'")
        
        self.assertEqual(text, "Hello World", "Should convert events to correct text")
        if text == "Hello World":
            print("  ✓ Events correctly converted to 'Hello World'")
        else:
            print(f"  ✗ FAIL: Text is '{text}' instead of 'Hello World'")
            
        self.assertEqual(len(buffer_states), 11, "Should have the correct number of buffer states")
        if len(buffer_states) == 11:
            print("  ✓ Correct number of buffer states (11)")
        else:
            print(f"  ✗ FAIL: Found {len(buffer_states)} buffer states instead of 11")
            
        # Verify final state
        if buffer_states and buffer_states[-1] == "Hello World":
            print("  ✓ Final buffer state is correct")
        elif buffer_states:
            print(f"  ✗ FAIL: Final buffer state is '{buffer_states[-1]}' instead of 'Hello World'")
        print("  ✓ All assertions passed")


if __name__ == "__main__":
    print("\n" + "="*80)
    print("TEXT BUFFER TEST SUITE")
    print("="*80)
    print("This test suite verifies the functionality of the TextBuffer utility")
    print("which is responsible for converting keystrokes to text and tracking")
    print("the state of the text as it's being edited.")
    print("\nEach test will show:")
    print("  ✓ - Passed assertions")
    print("  ✗ - Failed assertions")
    print("\nDetailed operation information is displayed for verification.")
    print("="*80)
    unittest.main(verbosity=2)