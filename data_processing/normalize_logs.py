#!/usr/bin/env python3
import os
import json
import glob
import re
import shutil
import socket
from datetime import datetime
from PIL import Image
import pyautogui
from tqdm import tqdm
from datasets import Dataset

def normalize_image_size(img, max_size=(1120, 1120)):
    original_width, original_height = img.size
    resize_ratio = min(max_size[0] / original_width, max_size[1] / original_height)
    return img.resize((int(original_width * resize_ratio), int(original_height * resize_ratio)), Image.Resampling.LANCZOS) if resize_ratio < 1 else img

def extract_activity_timestamps(filepath):
    with open(filepath, 'r') as f:
        data = json.load(f)
    return [datetime.fromisoformat(event['timestamp']).timestamp() for event in data.get('events', []) if 'timestamp' in event]

def merge_time_ranges(ranges):
    if not ranges:
        return []
    sorted_ranges = sorted(ranges)
    merged = [sorted_ranges[0]]
    for current in sorted_ranges[1:]:
        last = merged[-1]
        if current[0] <= last[1]:
            merged[-1] = (last[0], max(last[1], current[1]))
        else:
            merged.append(current)
    return merged

def identify_sessions(event_timestamps, gap_threshold=900):
    if not event_timestamps:
        return []
    sorted_timestamps = sorted(event_timestamps)
    sessions = []
    session_start = last_time = sorted_timestamps[0]

    for time in sorted_timestamps[1:]:
        if time - last_time > gap_threshold:
            sessions.append((session_start, last_time))
            session_start = time
        last_time = time

    sessions.append((session_start, last_time))
    return sessions

def check_session_coordinates(session_range, json_data_list, max_coordinate=1.0):
    session_start, session_end = session_range
    for json_data in json_data_list:
        for event in json_data.get('events', []):
            if event.get('event') == 'MOUSE' and 'timestamp' in event:
                ts = datetime.fromisoformat(event['timestamp']).timestamp()
                if session_start <= ts <= session_end:
                    x_val, y_val = event.get('x', 0), event.get('y', 0)
                    if isinstance(x_val, float) and x_val > max_coordinate:
                        return True
                    if isinstance(y_val, float) and y_val > max_coordinate:
                        return True
    return False

def extract_timestamp_from_filename(filename):
    match = re.search(r'screen_(\d{8})_(\d{6})_\d+\.jpg', filename)
    return datetime.strptime(f"{match.group(1)}_{match.group(2)}", "%Y%m%d_%H%M%S").timestamp() if match else None

def is_in_activity_range(timestamp, activity_ranges):
    """Check if a timestamp falls within any activity range using binary search."""
    import bisect
    idx = bisect.bisect_right(activity_ranges, (timestamp, float('inf'))) - 1
    return idx >= 0 and activity_ranges[idx][0] <= timestamp <= activity_ranges[idx][1]

def process_screenshot(filepath, output_dir):
    filename = os.path.basename(filepath)
    img = Image.open(filepath)
    normalize_image_size(img).save(os.path.join(output_dir, filename), quality=100)
    return {"status": "success", "filename": filename}

def process_json_file(filepath, output_dir, norm_width, norm_height):
    filename = os.path.basename(filepath)
    with open(filepath, 'r') as f:
        data = json.load(f)

    events_normalized = 0
    for event in data.get('events', []):
        if event.get('event') == 'MOUSE':
            for coord in ['x', 'y']:
                if coord in event and isinstance(event[coord], int):
                    events_normalized += 1
                    event[coord] = event[coord] / (norm_width if coord == 'x' else norm_height)

    with open(os.path.join(output_dir, filename), 'w') as f:
        json.dump(data, f, indent=2)

    return {
        "status": "success",
        "filename": filename,
        "normalized": events_normalized > 0,
        "events_normalized": events_normalized
    }

def main():
    # Configuration
    screen_width, screen_height = pyautogui.size()
    
    # Define paths
    ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    MINING_DIR = os.path.join(ROOT_DIR, 'mining')
    LOGS_DIR = os.path.join(MINING_DIR, 'logs_jacob_may_6_2025')
    SCREENSHOTS_DIR = os.path.join(LOGS_DIR, 'screenshots')
    JSON_DIR = os.path.join(LOGS_DIR, 'sanitized_json')
    
    # Generate distinctive output folder name
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    hostname = socket.gethostname().replace(".", "_")
    OUTPUT_DIR = os.path.join(ROOT_DIR, 'data', f"normalized_{hostname}_{timestamp}")
    OUTPUT_SCREENSHOTS_DIR = os.path.join(OUTPUT_DIR, 'screenshots')
    OUTPUT_JSON_DIR = os.path.join(OUTPUT_DIR, 'sanitized_json')
    
    # Create output directories
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(OUTPUT_SCREENSHOTS_DIR, exist_ok=True)
    os.makedirs(OUTPUT_JSON_DIR, exist_ok=True)
    
    print("Loading list of keystroke")
    all_json_files = glob.glob(os.path.join(JSON_DIR, "*.json"))
    json_files = all_json_files  # No date filtering

    print("Loading list of screenshots files")
    all_screenshot_files = glob.glob(os.path.join(SCREENSHOTS_DIR, "*.jpg"))
    screenshot_files = all_screenshot_files  # No date filtering
    
    print(f"Found files:")
    print(f"- JSON files: {len(json_files)}")
    print(f"- Screenshots: {len(screenshot_files)}")

    # Determine normalization dimensions using screen dimensions
    norm_width = screen_width
    norm_height = screen_height
    
    # Step 3: Identify all activity events and their timestamps
    print("Extracting all activity events and their timestamps...")
    
    json_data_list = []
    all_activity_timestamps = []
    
    for filepath in tqdm(json_files, desc="Loading JSON data"):
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                json_data_list.append(data)
                
                # Extract timestamps from each event
                for event in data.get('events', []):
                    ts = event.get('timestamp')
                    if ts:
                        if isinstance(ts, str):
                            try:
                                dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                                all_activity_timestamps.append(dt.timestamp())
                            except:
                                pass
                        elif isinstance(ts, (int, float)):
                            timestamp = ts / 1000 if ts > 1e10 else ts
                            all_activity_timestamps.append(timestamp)
        except Exception as e:
            print(f"Error loading {filepath}: {e}")
    
    print(f"Found {len(all_activity_timestamps)} activity events")
    
    # Step 4: Identify sessions (15-minute gap threshold)
    print("Identifying sessions based on 15-minute gaps...")
    sessions = identify_sessions(all_activity_timestamps)
    print(f"Identified {len(sessions)} distinct sessions")
    
    # Step 5: Filter out sessions with coordinates > 1.0
    print("Filtering out sessions with out-of-range coordinates...")
    valid_sessions = []
    invalid_sessions = []
    
    for session in tqdm(sessions, desc="Validating sessions"):
        if check_session_coordinates(session, json_data_list):
            invalid_sessions.append(session)
        else:
            valid_sessions.append(session)
    
    print(f"Sessions with valid coordinates: {len(valid_sessions)} out of {len(sessions)}")
    print(f"Sessions with out-of-range coordinates: {len(invalid_sessions)}")
    
    # Display session information
    if invalid_sessions:
        total_invalid_time = sum(end - start for start, end in invalid_sessions) / 3600  # hours
        print(f"Total time in invalid sessions: {total_invalid_time:.2f} hours")
        
        print("\nInvalid session periods:")
        for i, (start, end) in enumerate(invalid_sessions[:5]):  # Show first 5
            start_dt = datetime.fromtimestamp(start)
            end_dt = datetime.fromtimestamp(end)
            duration_mins = (end - start) / 60
            print(f"  {i+1}. {start_dt} to {end_dt} ({duration_mins:.2f} minutes)")
        
        if len(invalid_sessions) > 5:
            print(f"  ... and {len(invalid_sessions) - 5} more")
    
    # Step 6: Create time ranges for valid activity (for screenshot filtering)
    print("Creating activity time ranges for valid sessions...")
    
    # Create time ranges with buffer (15 seconds before and after each event)
    buffer_seconds = 15
    activity_ranges = []
    
    # Only include timestamps from valid sessions
    valid_timestamps = []
    for filepath in json_files:
        timestamps = extract_activity_timestamps(filepath)
        for ts in timestamps:
            # Check if timestamp is in any valid session
            for start, end in valid_sessions:
                if start <= ts <= end:
                    valid_timestamps.append(ts)
                    break
    
    # Create buffered ranges around valid timestamps
    activity_ranges = [(t - buffer_seconds, t + buffer_seconds) for t in valid_timestamps]
    
    # Merge overlapping ranges
    merged_ranges = merge_time_ranges(activity_ranges)
    print(f"Created {len(merged_ranges)} activity time ranges after filtering and merging")
    
    # Calculate total activity time
    total_activity_seconds = sum(end - start for start, end in merged_ranges)
    activity_hours = total_activity_seconds / 3600
    print(f"Total valid activity time: {activity_hours:.2f} hours")
    
    # Filter screenshots by valid activity ranges
    activity_filtered_screenshots = []
    
    for filepath in tqdm(screenshot_files, desc="Filtering screenshots by valid activity"):
        filename = os.path.basename(filepath)
        timestamp = extract_timestamp_from_filename(filename)
        
        if timestamp is not None and is_in_activity_range(timestamp, merged_ranges):
            activity_filtered_screenshots.append(filepath)
    
    print(f"Screenshots after valid activity filter: {len(activity_filtered_screenshots)} out of {len(screenshot_files)}")
    print(f"Final retention rate: {len(activity_filtered_screenshots)/len(all_screenshot_files)*100:.2f}% of all screenshots")
    
    # Step 7: Filter JSON files to only those in valid sessions
    print("Filtering JSON files to only include those in valid sessions...")
    valid_json_files = []
    
    # For each JSON file, check if its events are within valid sessions
    for filepath in tqdm(json_files, desc="Filtering JSON files by valid sessions"):
        timestamps = extract_activity_timestamps(filepath)
        has_valid_events = False
        
        for ts in timestamps:
            # Check if timestamp is in any valid session
            for start, end in valid_sessions:
                if start <= ts <= end:
                    has_valid_events = True
                    break
            
            if has_valid_events:
                break
        
        if has_valid_events:
            valid_json_files.append(filepath)
    
    print(f"JSON files with valid sessions: {len(valid_json_files)} out of {len(json_files)}")
    
    # Step 8: Process JSON files - normalize coordinates
    print("Processing JSON files...")
    print(f"Using normalization dimensions: {norm_width}x{norm_height}")
    
    # Process JSON files
    num_cores = max(1, os.cpu_count() // 2)
    json_dataset = Dataset.from_dict({"filepath": valid_json_files})
    
    json_results = json_dataset.map(
        lambda example: process_json_file(example["filepath"], OUTPUT_JSON_DIR, norm_width, norm_height),
        num_proc=num_cores,
        batched=False,
        desc="Processing JSON files"
    )
    
    # Extract statistics
    success_json = sum(1 for result in json_results if result["status"] == "success")
    error_json = sum(1 for result in json_results if result["status"] == "error")
    files_with_nonnormalized_coords = sum(1 for result in json_results if result.get("normalized", False))
    total_events_normalized = sum(result.get("events_normalized", 0) for result in json_results)
    
    # Scan sanitized files for max X/Y values and out-of-range coordinates
    max_norm_x, max_norm_y = 0, 0
    total_events = 0
    out_of_range_events = 0
    latest_out_of_range_timestamp = 0
    latest_out_of_range_file = ""

    for filepath in tqdm(glob.glob(os.path.join(OUTPUT_JSON_DIR, "*.json")), desc="Analyzing normalized coordinates"):
        with open(filepath, 'r') as f:
            data = json.load(f)

        for event in data.get('events', []):
            if event.get('event') == 'MOUSE':
                total_events += 1
                x_val = event.get('x', 0)
                y_val = event.get('y', 0)

                max_norm_x = max(max_norm_x, x_val)
                max_norm_y = max(max_norm_y, y_val)

                # Check if coordinates exceed normalized range (0-1)
                if x_val > 1.0 or y_val > 1.0:
                    out_of_range_events += 1
                    if 'timestamp' in event:
                        ts = event['timestamp']
                        if isinstance(ts, str):
                            try:
                                dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                                timestamp = dt.timestamp()
                            except:
                                continue
                        else:
                            timestamp = ts / 1000 if ts > 1e10 else ts

                        if timestamp > latest_out_of_range_timestamp:
                            latest_out_of_range_timestamp = timestamp
                            latest_out_of_range_file = filepath

    print(f"JSON processing complete:")
    print(f"- Files processed successfully: {success_json}")
    print(f"- Errors: {error_json}")
    print(f"- Files with coordinates normalized: {files_with_nonnormalized_coords}")
    print(f"- Total events normalized: {total_events_normalized}")
    print(f"- Max normalized X: {max_norm_x:.6f}, Max normalized Y: {max_norm_y:.6f}")

    # Report out-of-range coordinates
    print(f"\nOut-of-range coordinate analysis:")
    percentage = (out_of_range_events/total_events*100) if total_events > 0 else 0
    print(f"- Events with coordinates > 1.0: {out_of_range_events} out of {total_events} ({percentage:.2f}%)")

    if latest_out_of_range_timestamp > 0:
        latest_date = datetime.fromtimestamp(latest_out_of_range_timestamp)
        latest_file = os.path.basename(latest_out_of_range_file)
        print(f"- Latest out-of-range event: {latest_date} in file {latest_file}")
    
    # Step 9: Process filtered screenshots - resize and save
    print("\nProcessing filtered screenshots...")
    print(f"- Screenshots to process: {len(activity_filtered_screenshots)}")
    print(f"- Output directory: {OUTPUT_DIR}")

    # Create dataset for parallel processing
    screenshots_dataset = Dataset.from_dict({"filepath": activity_filtered_screenshots})

    # Process screenshots in parallel
    screenshot_results = screenshots_dataset.map(
        lambda example: process_screenshot(example["filepath"], OUTPUT_SCREENSHOTS_DIR),
        num_proc=num_cores,
        batched=False,
        desc="Processing screenshots"
    )

    # Copy session_prompts.log if it exists
    session_prompts_path = os.path.join(LOGS_DIR, "session_prompts.log")
    if os.path.exists(session_prompts_path):
        shutil.copy2(session_prompts_path, os.path.join(OUTPUT_DIR, "session_prompts.log"))

if __name__ == "__main__":
    main()