"""
Text buffer utility for handling keystroke-to-text conversion.
Manages cursor position, editing operations, and maintains buffer state history.
Provides precise mapping between text positions and keystroke events.
"""

from typing import List, Dict, Tuple, Any, Set


class TextBuffer:
    """
    A text buffer that handles keystroke-to-text conversion with cursor tracking
    and precise mapping between text positions and keystroke events
    """
    
    def __init__(self):
        """Initialize an empty text buffer with cursor at position 0"""
        self.buffer = ""
        self.cursor_pos = 0
        self.buffer_states = []
        
        # Track which events created which positions in the text
        # For each position in the buffer, store the event IDs that contributed to it
        self.position_to_events = {}
        
        # Track deleted positions (by backspace/delete) and their events
        self.deleted_positions = {}
        
    def process_keystroke(self, key, event_id=None):
        """
        Process a keystroke and update the buffer
        
        Args:
            key: Key pressed (string representation)
            event_id: Unique identifier for this event (for tracking)
            
        Returns:
            bool: True if buffer was modified, False otherwise
        """
        modified = False
        
        # Keep track of the previous state for event tracking
        prev_buffer = self.buffer
        prev_cursor = self.cursor_pos
        
        if key == "Key.space":
            # Insert space at cursor position
            self.buffer = self.buffer[:self.cursor_pos] + " " + self.buffer[self.cursor_pos:]
            self.cursor_pos += 1
            modified = True
            
            # Track which event created this position
            if event_id is not None:
                # Shift all positions after the cursor
                self._shift_positions(prev_cursor)
                # Add this event to the current position
                self._add_event_to_position(prev_cursor, event_id)
                
        elif key == "Key.enter":
            # Insert newline at cursor position
            self.buffer = self.buffer[:self.cursor_pos] + "\n" + self.buffer[self.cursor_pos:]
            self.cursor_pos += 1
            modified = True
            
            # Track which event created this position
            if event_id is not None:
                # Shift all positions after the cursor
                self._shift_positions(prev_cursor)
                # Add this event to the current position
                self._add_event_to_position(prev_cursor, event_id)
                
        elif key == "Key.backspace":
            # Handle backspace
            if self.cursor_pos > 0:
                # Track the deleted character and its events
                if event_id is not None:
                    deleted_pos = self.cursor_pos - 1
                    if deleted_pos in self.position_to_events:
                        deleted_events = self.position_to_events.pop(deleted_pos)
                        # Store the deleted position and its events
                        self.deleted_positions[len(self.buffer_states)] = {
                            "position": deleted_pos,
                            "character": self.buffer[deleted_pos:deleted_pos+1],
                            "events": deleted_events,
                            "deletion_event": event_id
                        }
                
                self.buffer = self.buffer[:self.cursor_pos-1] + self.buffer[self.cursor_pos:]
                self.cursor_pos -= 1
                modified = True
                
                # Update positions after deletion
                if event_id is not None:
                    self._shift_positions(self.cursor_pos, shift_by=-1)
                
        elif key == "Key.delete":
            # Handle delete
            if self.cursor_pos < len(self.buffer):
                # Track the deleted character and its events
                if event_id is not None:
                    deleted_pos = self.cursor_pos
                    if deleted_pos in self.position_to_events:
                        deleted_events = self.position_to_events.pop(deleted_pos)
                        # Store the deleted position and its events
                        self.deleted_positions[len(self.buffer_states)] = {
                            "position": deleted_pos,
                            "character": self.buffer[deleted_pos:deleted_pos+1],
                            "events": deleted_events,
                            "deletion_event": event_id
                        }
                
                self.buffer = self.buffer[:self.cursor_pos] + self.buffer[self.cursor_pos+1:]
                modified = True
                
                # Update positions after deletion
                if event_id is not None:
                    self._shift_positions(self.cursor_pos, shift_by=-1)
                
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
            
            # Track which event created this position
            if event_id is not None:
                # Shift all positions after the cursor
                self._shift_positions(prev_cursor)
                # Add this event to the current position
                self._add_event_to_position(prev_cursor, event_id)
            
        # If buffer was modified, save the state
        if modified and self.buffer:
            self.buffer_states.append(self.buffer)
            
        return modified
    
    def _shift_positions(self, from_position, shift_by=1):
        """
        Shift position-to-event mappings when text is inserted or deleted
        
        Args:
            from_position: Position in buffer where the shift starts
            shift_by: Amount to shift by (positive for insertion, negative for deletion)
        """
        # Get all positions that need to be shifted (>= from_position)
        positions_to_shift = [pos for pos in self.position_to_events.keys() 
                             if pos >= from_position]
        positions_to_shift.sort(reverse=(shift_by < 0))  # Sort to avoid overlap issues
        
        # Create new mappings
        new_position_to_events = {}
        
        # Copy unchanged positions
        for pos in self.position_to_events:
            if pos < from_position:
                new_position_to_events[pos] = self.position_to_events[pos]
        
        # Shift positions
        for pos in positions_to_shift:
            if shift_by < 0 and pos >= from_position and pos < from_position + abs(shift_by):
                # Skip positions that will be deleted
                continue
                
            new_pos = pos + shift_by
            if new_pos >= 0:  # Avoid negative positions
                new_position_to_events[new_pos] = self.position_to_events[pos]
        
        # Update the mapping
        self.position_to_events = new_position_to_events
        
    def _add_event_to_position(self, position, event_id):
        """
        Add an event ID to a position in the position-to-events mapping
        
        Args:
            position: Position in the buffer
            event_id: Event ID to add
        """
        if position not in self.position_to_events:
            self.position_to_events[position] = set()
            
        self.position_to_events[position].add(event_id)
        
    def get_text(self):
        """Get the current text in the buffer"""
        return self.buffer
        
    def get_buffer_states(self):
        """Get the history of buffer states"""
        return self.buffer_states
        
    def get_events_for_position(self, position):
        """
        Get all events that contributed to a specific position
        
        Args:
            position: Position in the buffer
            
        Returns:
            set: Set of event IDs
        """
        return self.position_to_events.get(position, set())
        
    def get_events_for_range(self, start, end):
        """
        Get all events that contributed to a range of positions
        
        Args:
            start: Start position (inclusive)
            end: End position (exclusive)
            
        Returns:
            set: Set of event IDs
        """
        events = set()
        for pos in range(start, end):
            events.update(self.get_events_for_position(pos))
            
        return events
        
    def get_deleted_positions(self):
        """Get history of deleted positions and their events"""
        return self.deleted_positions
        
    def clear(self):
        """Clear the buffer, history, and event tracking"""
        self.buffer = ""
        self.cursor_pos = 0
        self.buffer_states = []
        self.position_to_events = {}
        self.deleted_positions = {}

    def get_cursor_position(self):
        """Get the current cursor position"""
        return self.cursor_pos
        
    @staticmethod
    def events_to_text(events):
        """
        Convert keystroke events to text using the buffer,
        tracking which events contributed to which positions
        
        Args:
            events: List of keystroke events
            
        Returns:
            tuple: (final_text, buffer_states, position_to_event_ids, related_event_ids)
                - final_text: The reconstructed text
                - buffer_states: History of buffer states
                - position_to_event_ids: Dict mapping text positions to event IDs
                - related_event_ids: Dict mapping original press event IDs to related release event IDs
        """
        buffer = TextBuffer()
        
        # Track related events (press-release pairs)
        related_events = {}
        event_ids = {}  # Map event IDs to actual events for timestamp retrieval
        
        # First, find all press-release pairs
        press_events = {}
        for i, event in enumerate(events):
            event_id = id(event)
            event_ids[event_id] = event  # Store the event for later reference
            
            if event["event"] == "KEY_PRESS" and "key" in event:
                key = event.get("key", "")
                # Store this press event
                if key in press_events:
                    # If we already have this key in press_events, it might be a repeated key
                    # We'll handle this by using a compound key
                    compound_key = f"{key}_{i}"
                    press_events[compound_key] = (event_id, i)
                else:
                    press_events[key] = (event_id, i)
            elif event["event"] == "KEY_RELEASE" and "key" in event:
                key = event.get("key", "")
                # If we found a matching press event
                if key in press_events:
                    press_id, press_idx = press_events[key]
                    release_id = event_id
                    # Link press and release events
                    if press_id not in related_events:
                        related_events[press_id] = []
                    related_events[press_id].append(release_id)
                    # Remove from active press events
                    press_events.pop(key, None)
        
        # Now process events to build text, tracking position-to-event mapping
        for i, event in enumerate(events):
            if event["event"] == "KEY_PRESS" and "key" in event:
                key = event.get("key", "")
                event_id = id(event)
                buffer.process_keystroke(key, event_id)
        
        # Convert position_to_events sets to lists for JSON compatibility
        position_to_event_ids = {}
        for pos, event_set in buffer.position_to_events.items():
            position_to_event_ids[str(pos)] = list(event_set)  # Convert to string key for JSON compatibility
        
        return (buffer.get_text(), 
                buffer.get_buffer_states(), 
                position_to_event_ids, 
                related_events)