"""
Text buffer utility for handling keystroke-to-text conversion.
Manages cursor position, editing operations, and maintains buffer state history.
"""

from typing import List, Dict, Tuple, Any, Set


class TextBuffer:
    """
    A text buffer that handles keystroke-to-text conversion with cursor tracking.
    """
    
    def __init__(self):
        """Initialize an empty text buffer"""
        self.buffer = ""
        self.cursor_pos = 0
        self.buffer_states = []
        self.position_to_events = {}
        
    def process_keystroke(self, key, event_id=None):
        """Process a keystroke and update the buffer"""
        modified = False
        prev_cursor = self.cursor_pos
        
        # Helper function for character insertion
        def insert_char(char):
            nonlocal modified
            self.buffer = self.buffer[:self.cursor_pos] + char + self.buffer[self.cursor_pos:]
            self.cursor_pos += 1
            modified = True
            
            if event_id is not None:
                self._shift_positions(prev_cursor)
                self._add_event_to_position(prev_cursor, event_id)
        
        # Process different key types
        if key == "Key.space":
            insert_char(" ")
        elif key == "Key.enter":
            insert_char("\n")
        elif key == "Key.backspace":
            if self.cursor_pos > 0:
                if event_id is not None and self.cursor_pos-1 in self.position_to_events:
                    self.position_to_events.pop(self.cursor_pos-1)
                
                self.buffer = self.buffer[:self.cursor_pos-1] + self.buffer[self.cursor_pos:]
                self.cursor_pos -= 1
                modified = True
                
                if event_id is not None:
                    self._shift_positions(self.cursor_pos, shift_by=-1)
        elif key == "Key.delete":
            if self.cursor_pos < len(self.buffer):
                if event_id is not None and self.cursor_pos in self.position_to_events:
                    self.position_to_events.pop(self.cursor_pos)
                
                self.buffer = self.buffer[:self.cursor_pos] + self.buffer[self.cursor_pos+1:]
                modified = True
                
                if event_id is not None:
                    self._shift_positions(self.cursor_pos, shift_by=-1)
        elif key == "Key.left":
            self.cursor_pos = max(0, self.cursor_pos - 1)
        elif key == "Key.right":
            self.cursor_pos = min(len(self.buffer), self.cursor_pos + 1)
        elif key == "Key.home":
            self.cursor_pos = 0
        elif key == "Key.end":
            self.cursor_pos = len(self.buffer)
        elif not key.startswith("Key."):
            insert_char(key)
        
        # Save state if buffer was modified
        if modified and self.buffer:
            self.buffer_states.append(self.buffer)
            
        return modified
    
    def _shift_positions(self, from_position, shift_by=1):
        """Shift position-to-event mappings when text is inserted or deleted"""
        positions_to_shift = [pos for pos in self.position_to_events.keys() 
                             if pos >= from_position]
        positions_to_shift.sort(reverse=(shift_by < 0))
        
        new_position_to_events = {}
        
        # Copy unchanged positions
        for pos in self.position_to_events:
            if pos < from_position:
                new_position_to_events[pos] = self.position_to_events[pos]
        
        # Shift positions
        for pos in positions_to_shift:
            if shift_by < 0 and pos >= from_position and pos < from_position + abs(shift_by):
                continue
                
            new_pos = pos + shift_by
            if new_pos >= 0:
                new_position_to_events[new_pos] = self.position_to_events[pos]
        
        self.position_to_events = new_position_to_events
        
    def _add_event_to_position(self, position, event_id):
        """Add an event ID to a position"""
        if position not in self.position_to_events:
            self.position_to_events[position] = set()
            
        self.position_to_events[position].add(event_id)
        
    def get_text(self):
        """Get current text"""
        return self.buffer
        
    def get_buffer_states(self):
        """Get history of buffer states"""
        return self.buffer_states
        
    def get_cursor_position(self):
        """Get cursor position"""
        return self.cursor_pos
        
    def clear(self):
        """Clear the buffer and history"""
        self.buffer = ""
        self.cursor_pos = 0
        self.buffer_states = []
        self.position_to_events = {}
        
    @staticmethod
    def events_to_text(events):
        """
        Convert keystroke events to text.
        
        Returns:
            tuple: (text, buffer_states, position_to_event_ids, related_events, buffer_state_mappings)
        """
        buffer = TextBuffer()
        related_events = {}
        buffer_state_mappings = []  # Will store position mappings for each buffer state
        
        # Find press-release pairs
        press_events = {}
        for i, event in enumerate(events):
            event_id = id(event)
            
            if event["event"] == "KEY_PRESS" and "key" in event:
                key = event.get("key", "")
                if key in press_events:
                    compound_key = f"{key}_{i}"
                    press_events[compound_key] = (event_id, i)
                else:
                    press_events[key] = (event_id, i)
            elif event["event"] == "KEY_RELEASE" and "key" in event:
                key = event.get("key", "")
                if key in press_events:
                    press_id, _ = press_events[key]
                    if press_id not in related_events:
                        related_events[press_id] = []
                    related_events[press_id].append(event_id)
                    press_events.pop(key, None)
        
        # Track all events seen so far for each buffer state
        events_seen = set()
        
        # Process events to build text
        for event in events:
            if event["event"] == "KEY_PRESS" and "key" in event:
                event_id = id(event)
                
                # Record this event as seen
                events_seen.add(event_id)
                
                # Add related events
                if event_id in related_events:
                    for related_id in related_events[event_id]:
                        events_seen.add(related_id)
                
                # Process the keystroke
                modified = buffer.process_keystroke(event.get("key", ""), event_id)
                
                # If buffer was modified, capture state snapshot
                if modified:
                    # Store mapping with both position info and all events seen
                    # This ensures we can map passwords in deleted text to keystroke events
                    current_mapping = {}
                    for pos, event_set in buffer.position_to_events.items():
                        current_mapping[str(pos)] = list(event_set)
                    
                    buffer_state_mappings.append({
                        "state": buffer.buffer,
                        "position_mapping": current_mapping,
                        "events_seen": list(events_seen),
                        "buffer_state_idx": len(buffer.buffer_states) - 1  # Index of corresponding buffer state
                    })
        
        # Convert position_to_events to JSON-compatible format for final state
        position_to_event_ids = {}
        for pos, event_set in buffer.position_to_events.items():
            position_to_event_ids[str(pos)] = list(event_set)
        
        return (buffer.get_text(), 
                buffer.get_buffer_states(), 
                position_to_event_ids, 
                related_events,
                buffer_state_mappings)