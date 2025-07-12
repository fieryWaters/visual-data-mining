#!/usr/bin/env python3
import json
import glob
from anytree import Node

def load_all_events():
    """Load and sort all events from all JSON files."""
    all_events = []
    for file_path in glob.glob("../data/filtered/*/sanitized_json/*.json"):
        with open(file_path) as f:
            data = json.load(f)
            all_events.extend(data.get('events', []))
    
    all_events.sort(key=lambda x: x.get('timestamp', ''))
    return all_events

def contains_non_modifier_keys(tree, modifiers):
    """Check if tree contains any non-modifier keys (letters, numbers, symbols)."""
    for key, subtree in tree.items():
        if key not in modifiers:
            return True
        if contains_non_modifier_keys(subtree, modifiers):
            return True
    return False

def is_shift_typing(combo_dict):
    """Check if this is just shift + printable characters (typing, not a combo)."""
    if len(combo_dict) != 1 or 'Key.shift' not in combo_dict:
        return False
    
    shift_children = combo_dict['Key.shift']
    if not isinstance(shift_children, dict):
        return False
    
    # Extended typing includes letters, space, and backspace
    typing_keys = {'Key.space', 'Key.backspace'}
    
    # If all children are printable chars or typing keys, it's typing
    for key in shift_children.keys():
        if key in typing_keys:
            continue  # space/backspace are typing
        elif len(key) == 1 and key.isprintable():
            continue  # single printable chars are typing
        else:
            return False  # found non-typing key
    
    return True

def node_to_dict(node):
    """Convert anytree Node to nested dictionary."""
    if not node.children:
        return {}
    result = {}
    for child in node.children:
        if child.name in result:
            # Handle multiple children with same name (e.g., Tab+Tab)
            if not isinstance(result[child.name], list):
                result[child.name] = [result[child.name]]
            result[child.name].append(node_to_dict(child))
        else:
            result[child.name] = node_to_dict(child)
    return result

def process_key_combos():
    """Core combo processing logic - build nested trees."""
    modifiers = {'Key.cmd', 'Key.cmd_r', 'Key.ctrl', 'Key.alt', 'Key.alt_r', 'Key.shift', 'Key.shift_r'}
    arrows = {'Key.up', 'Key.down', 'Key.left', 'Key.right'}
    
    all_events = load_all_events()
    print(f"Processing {len(all_events)} events...")
    
    combo_root = None
    current_node = None
    combo_start_time = None
    all_combos = []
    total_combos_evaluated = 0
    shift_typing_count = 0
    no_content_count = 0
    kept_count = 0
    
    for event in all_events:
        event_type = event.get('event')
        key = event.get('key')
        timestamp = event.get('timestamp')
        
        if event_type == 'KEY_PRESS':
            if key in modifiers:
                if combo_root is None:
                    # Start new combo
                    combo_root = Node("root")
                    combo_start_time = timestamp
                    current_node = Node(key, parent=combo_root)
                else:
                    # Add nested level
                    current_node = Node(key, parent=current_node)
            elif key in arrows:
                # Emit arrow combo immediately
                print(f"CAPTURED ARROW: {key}")
                all_combos.append({
                    "event": "KEYBOARD_COMBO",
                    "combo": {key: {}},
                    "timestamp": timestamp,
                    "end_timestamp": timestamp
                })
            else:
                # Add to current level
                if current_node is not None:
                    Node(key, parent=current_node)
                else:
                    # Normal typing - ignore
                    pass
        
        elif event_type == 'KEY_RELEASE' and key in modifiers:
            if current_node and current_node.name == key:
                # Go back up one level
                current_node = current_node.parent
                
                # If back at root, emit combo
                if current_node == combo_root:
                    combo_dict = node_to_dict(combo_root)
                    total_combos_evaluated += 1
                    
                    # Skip if it's just shift typing or has no meaningful content
                    if is_shift_typing(combo_dict):
                        shift_typing_count += 1
                       # print(f"DISCARDED (shift typing): {combo_dict}")
                    elif not contains_non_modifier_keys(combo_dict, modifiers):
                        no_content_count += 1
                        print(f"DISCARDED (no content): {combo_dict}")
                    else:
                        kept_count += 1
                        print(f"KEPT: {combo_dict}")
                        all_combos.append({
                            "event": "KEYBOARD_COMBO",
                            "combo": combo_dict,
                            "timestamp": combo_start_time,
                            "end_timestamp": timestamp
                        })
                    
                    # Reset for next combo
                    combo_root = None
                    current_node = None
                    combo_start_time = None
    
    print(f"\nSUMMARY:")
    print(f"Total combo trees evaluated: {total_combos_evaluated}")
    print(f"Shift typing discarded: {shift_typing_count}")
    print(f"No content discarded: {no_content_count}")
    print(f"Meaningful combos kept: {kept_count}")
    print(f"Length of all_combos: {len(all_combos)}")
    return all_combos

def main():
    combos = process_key_combos()
    
    if combos:
        import os
        output_dir = "../data/derived_events"
        os.makedirs(output_dir, exist_ok=True)
        
        with open(f"{output_dir}/keyboard_combos.json", 'w') as f:
            json.dump({"total_combos": len(combos), "derived_events": combos}, f, indent=2)
        
        print(f"Found {len(combos)} meaningful keyboard combos")
    else:
        print("No meaningful keyboard combos found")

if __name__ == "__main__":
    main()