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
    """Resize an image to a maximum size while preserving aspect ratio."""
    original_width, original_height = img.size
    resize_ratio = min(max_size[0] / original_width, max_size[1] / original_height)
    
    if resize_ratio < 1:
        new_width, new_height = int(original_width * resize_ratio), int(original_height * resize_ratio)
        return img.resize((new_width, new_height), Image.Resampling.LANCZOS)
    return img

def extract_activity_timestamps(filepath):
    """Extract timestamps of all user activity events from a JSON file."""
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        timestamps = []
        for event in data.get('events', []):
            ts = event.get('timestamp')
            if not ts:
                continue
                
            if isinstance(ts, str):
                try:
                    dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                    timestamps.append(dt.timestamp())
                except:
                    pass
            elif isinstance(ts, (int, float)):
                timestamps.append(ts / 1000 if ts > 1e10 else ts)
                
        return timestamps
    except Exception as e:
        print(f"Error extracting timestamps from {filepath}: {e}")
        return []

def merge_time_ranges(ranges):
    """Merge overlapping time ranges."""
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

def extract_timestamp_from_filename(filename):
    """Extract timestamp from screenshot filename."""
    match = re.search(r'screen_(\d{8})_(\d{6})_\d+\.jpg', filename)
    if match:
        dt = datetime.strptime(f"{match.group(1)}_{match.group(2)}", "%Y%m%d_%H%M%S")
        return dt.timestamp()
    return None

def is_in_activity_range(timestamp, activity_ranges):
    """Check if a timestamp falls within any activity range using binary search."""
    import bisect
    idx = bisect.bisect_right(activity_ranges, (timestamp, float('inf'))) - 1
    return idx >= 0 and activity_ranges[idx][0] <= timestamp <= activity_ranges[idx][1]

def process_screenshot(filepath, output_dir):
    """Process a single screenshot file and save it to the output directory."""
    try:
        filename = os.path.basename(filepath)
        output_path = os.path.join(output_dir, filename)
        
        img = Image.open(filepath)
        normalized_img = normalize_image_size(img)
        normalized_img.save(output_path, quality=100)
        
        return {"status": "success", "filename": filename}
    except Exception as e:
        return {"status": "error", "filename": os.path.basename(filepath), "error": str(e)}

def process_json_file(filepath, output_dir, norm_width, norm_height):
    """Process a single JSON file and save it to the output directory."""
    try:
        filename = os.path.basename(filepath)
        output_path = os.path.join(output_dir, filename)
        
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        file_needed_normalization = False
        events_normalized = 0
        
        for event in data.get('events', []):
            if event.get('event') == 'MOUSE':
                for coord in ['x', 'y']:
                    if coord in event:
                        value = event[coord]
                        
                        # Only normalize if value is an integer
                        if isinstance(value, int):
                            file_needed_normalization = True
                            events_normalized += 1
                            
                            # Use provided dimensions
                            event[coord] = value / (norm_width if coord == 'x' else norm_height)
        
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        return {
            "status": "success", 
            "filename": filename, 
            "normalized": file_needed_normalization,
            "events_normalized": events_normalized
        }
    except Exception as e:
        return {"status": "error", "filename": os.path.basename(filepath), "error": str(e)}

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
    
    # Step 1: Filter files by date (after April 30, 2025)
    cutoff_date = datetime(2025, 4, 30, 23, 59, 59).timestamp()
    print(f"Filtering out data on or before: {datetime.fromtimestamp(cutoff_date)}")
    
    # Filter JSON files by date in filename
    all_json_files = glob.glob(os.path.join(JSON_DIR, "*.json"))
    json_files = []

    for filepath in tqdm(all_json_files, desc="Filtering JSON files by date"):
        filename = os.path.basename(filepath)
        # Extract date from sanitized_YYYYMMDD_* pattern
        date_match = re.search(r'sanitized_(\d{8})_', filename)
        if date_match:
            file_date = date_match.group(1)
            file_timestamp = datetime.strptime(file_date, "%Y%m%d").timestamp()
            if file_timestamp > cutoff_date:
                json_files.append(filepath)

    # Filter screenshot files by date in filename
    all_screenshot_files = glob.glob(os.path.join(SCREENSHOTS_DIR, "*.jpg"))
    screenshot_files = []

    for filepath in tqdm(all_screenshot_files, desc="Filtering screenshots by date"):
        filename = os.path.basename(filepath)
        # Extract date from screen_YYYYMMDD_* pattern
        date_match = re.search(r'screen_(\d{8})_', filename)
        if date_match:
            file_date = date_match.group(1)
            file_timestamp = datetime.strptime(file_date, "%Y%m%d").timestamp()
            if file_timestamp > cutoff_date:
                screenshot_files.append(filepath)
    
    print(f"Files after date filter:")
    print(f"- JSON files: {len(json_files)} out of {len(all_json_files)} ({len(json_files)/len(all_json_files)*100:.2f}%)")
    print(f"- Screenshots: {len(screenshot_files)} out of {len(all_screenshot_files)} ({len(screenshot_files)/len(all_screenshot_files)*100:.2f}%)")
    
    # Step 2: Scan for coordinate anomalies in filtered JSON files
    print("Scanning for coordinate anomalies in filtered JSON files...")
    
    max_x, max_y = 0, 0
    max_x_file, max_y_file = "", ""
    anomalous_files = []
    
    # Known screen dimensions
    expected_max_x = 2560  # MacBook Pro Retina 13.3" width
    expected_max_y = 1600  # MacBook Pro Retina 13.3" height
    
    for filepath in tqdm(json_files, desc="Scanning JSON files"):
        filename = os.path.basename(filepath)
        file_has_anomaly = False
        
        with open(filepath, 'r') as f:
            data = json.load(f)
            
        for event in data.get('events', []):
            if event.get('event') == 'MOUSE':
                # Track maximum X coordinate
                if 'x' in event:
                    x_val = event['x']
                    if x_val > max_x:
                        max_x = x_val
                        max_x_file = filename

                    # Check if X exceeds expected maximum
                    if x_val > expected_max_x:
                        file_has_anomaly = True

                # Track maximum Y coordinate
                if 'y' in event:
                    y_val = event['y']
                    if y_val > max_y:
                        max_y = y_val
                        max_y_file = filename

                    # Check if Y exceeds expected maximum
                    if y_val > expected_max_y:
                        file_has_anomaly = True
        
        if file_has_anomaly and filepath not in anomalous_files:
            anomalous_files.append(filepath)
    
    # Report findings
    print(f"Maximum coordinates found:")
    print(f"- Max X: {max_x} (in file {max_x_file})")
    print(f"- Max Y: {max_y} (in file {max_y_file})")
    print(f"- Expected maximum: {expected_max_x}x{expected_max_y}")
    
    if anomalous_files:
        print(f"\nFound {len(anomalous_files)} files with coordinates exceeding expected range:")
        for i, filepath in enumerate(anomalous_files[:5]):  # Show first 5
            filename = os.path.basename(filepath)
            print(f"  {i+1}. {filename}")
        
        if len(anomalous_files) > 5:
            print(f"  ... and {len(anomalous_files) - 5} more")
    else:
        print("\nNo coordinate anomalies found in filtered files")
    
    # Determine normalization dimensions (using screen dimensions if no anomalies)
    norm_width = screen_width
    norm_height = screen_height
    
    # Step 3: Identify activity ranges to filter screenshots
    print("Identifying activity ranges from filtered JSON files...")

    # Extract timestamps from all events
    all_activity_timestamps = []

    for filepath in tqdm(json_files, desc="Extracting activity timestamps"):
        with open(filepath, 'r') as f:
            data = json.load(f)

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

    print(f"Found {len(all_activity_timestamps)} activity events")
    
    # Create time ranges with buffer
    buffer_seconds = 15  # 15 seconds before and after each event
    activity_ranges = [(t - buffer_seconds, t + buffer_seconds) for t in all_activity_timestamps]
    
    # Merge overlapping ranges
    merged_ranges = merge_time_ranges(activity_ranges)
    print(f"Created {len(merged_ranges)} activity time ranges after merging")
    
    # Calculate total activity time
    total_activity_seconds = sum(end - start for start, end in merged_ranges)
    activity_hours = total_activity_seconds / 3600
    print(f"Total activity time: {activity_hours:.2f} hours")
    
    # Further filter screenshots by activity
    activity_filtered_screenshots = []
    
    for filepath in tqdm(screenshot_files, desc="Filtering screenshots by activity"):
        filename = os.path.basename(filepath)
        timestamp = extract_timestamp_from_filename(filename)
        
        if timestamp is not None and is_in_activity_range(timestamp, merged_ranges):
            activity_filtered_screenshots.append(filepath)
    
    print(f"Screenshots after activity filter: {len(activity_filtered_screenshots)} out of {len(screenshot_files)}")
    print(f"Final retention rate: {len(activity_filtered_screenshots)/len(all_screenshot_files)*100:.2f}% of all screenshots")
    
    # Step 4: Process JSON files - normalize coordinates
    print("Processing JSON files...")
    print(f"Using normalization dimensions: {norm_width}x{norm_height}")
    
    # Process JSON files
    num_cores = max(1, os.cpu_count() // 2)
    json_dataset = Dataset.from_dict({"filepath": json_files})
    
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
    
    # Step 5: Process filtered screenshots - resize and save
    print("Processing filtered screenshots...")
    # Create dataset for parallel processing
    screenshots_dataset = Dataset.from_dict({"filepath": activity_filtered_screenshots})
    
    # Process screenshots in parallel
    screenshot_results = screenshots_dataset.map(
        lambda example: process_screenshot(example["filepath"], OUTPUT_SCREENSHOTS_DIR),
        num_proc=num_cores,
        batched=False,
        desc="Processing screenshots"
    )
    
    # Extract statistics
    success_screenshots = sum(1 for result in screenshot_results if result["status"] == "success")
    error_screenshots = sum(1 for result in screenshot_results if result["status"] == "error")
    
    print(f"Screenshot processing complete:")
    print(f"- Screenshots processed successfully: {success_screenshots}")
    print(f"- Errors: {error_screenshots}")
    
    # Copy session_prompts.log if it exists
    session_prompts_path = os.path.join(LOGS_DIR, "session_prompts.log")
    if os.path.exists(session_prompts_path):
        shutil.copy2(session_prompts_path, os.path.join(OUTPUT_DIR, "session_prompts.log"))
        print("Copied session_prompts.log to output directory")
    
    # Step 6: Summary report
    print("\n===== Normalization Summary =====")
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"Date cutoff (after April 30, 2025 to exclude out-of-range coordinates): {datetime.fromtimestamp(cutoff_date)}")
    
    print("\nFiltering statistics:")
    print(f"- JSON files: {len(json_files)} out of {len(all_json_files)} ({len(json_files)/len(all_json_files)*100:.2f}%)")
    print(f"- Screenshots after date filter: {len(screenshot_files)} out of {len(all_screenshot_files)} ({len(screenshot_files)/len(all_screenshot_files)*100:.2f}%)")
    print(f"- Screenshots after activity filter: {len(activity_filtered_screenshots)} out of {len(all_screenshot_files)} ({len(activity_filtered_screenshots)/len(all_screenshot_files)*100:.2f}%)")
    
    print("\nCoordinate analysis:")
    print(f"- Maximum coordinates found: X={max_x}, Y={max_y}")
    print(f"- Normalization dimensions used: {norm_width}x{norm_height}")
    print(f"- Anomalous files found: {len(anomalous_files)}")
    
    print("\nProcessing results:")
    print(f"- JSON files processed: {success_json} (Errors: {error_json})")
    print(f"- Files with coordinates normalized: {files_with_nonnormalized_coords}")
    print(f"- Total events normalized: {total_events_normalized}")
    print(f"- Screenshots processed: {success_screenshots} (Errors: {error_screenshots})")
    
    print(f"\nTotal activity time: {activity_hours:.2f} hours")
    print("\nNormalization complete! The normalized data is ready for use.")

if __name__ == "__main__":
    main()