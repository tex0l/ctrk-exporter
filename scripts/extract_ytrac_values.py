#!/usr/bin/env python3
"""
Extract telemetry values from Y-Trac official app via UI Automator.

This script automates the extraction of channel values from the Y-Trac app
running in an Android emulator. It uses adb and UI Automator to:
1. Navigate to the telemetry view
2. Scroll through all channels
3. Capture values at different timestamps
4. Save results to a reference JSON file

Usage:
    python scripts/extract_ytrac_values.py [--timestamps 0,10,30,60]

Requirements:
    - Android emulator running with Y-Trac app installed
    - adb in PATH
    - Y-Trac app open with a CTRK file loaded
"""

import subprocess
import xml.etree.ElementTree as ET
import json
import time
import re
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Project root
PROJECT_ROOT = Path(__file__).parent.parent
ASSETS_DIR = PROJECT_ROOT / "assets"

# Channel mapping: Y-Trac name -> normalized name
# Note: Temperature uses Unicode ℃ (U+2103) not °C
CHANNEL_MAP = {
    "E/G-RPM (r/min)": "rpm",
    "Throttle-Grip (％)": "throttle_grip",
    "Throttle-Grip (%)": "throttle_grip",
    "Throttle (％)": "throttle",
    "Throttle (%)": "throttle",
    "R-Speed (km/h)": "r_speed",
    "F-Speed (km/h)": "f_speed",
    "GPS-Speed (km/h)": "gps_speed",
    "Gear": "gear",
    "Lean (°)": "lean",
    "Pitch (°/s)": "pitch",
    "R-Brake (bar)": "r_brake",
    "F-Brake (bar)": "f_brake",
    "Water-Temp (°C)": "water_temp",
    "Water-Temp (℃)": "water_temp",  # Unicode DEGREE CELSIUS
    "Air-Temp (°C)": "air_temp",
    "Air-Temp (℃)": "air_temp",  # Unicode DEGREE CELSIUS
    "Fuel (cc)": "fuel",
    "Acc-X (g)": "acc_x",
    "Acc-Y (g)": "acc_y",
    "AIN-1": "ain_1",
    "AIN-2": "ain_2",
}

# Required channels (from user specification)
REQUIRED_CHANNELS = [
    "throttle", "throttle_grip", "rpm", "r_speed", "f_speed",
    "gear", "lean", "pitch", "r_brake", "f_brake",
    "water_temp", "air_temp", "fuel", "acc_x", "acc_y"
]


def run_adb(args: List[str], timeout: int = 30) -> str:
    """Run an adb command and return output."""
    cmd = ["adb"] + args
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0 and "error" in result.stderr.lower():
        raise RuntimeError(f"adb command failed: {result.stderr}")
    return result.stdout


def check_emulator() -> bool:
    """Check if emulator is connected."""
    output = run_adb(["devices"])
    return "emulator" in output and "device" in output


def dump_ui() -> ET.Element:
    """Dump UI hierarchy and parse XML."""
    run_adb(["shell", "uiautomator", "dump", "/sdcard/ui_dump.xml"])
    xml_content = run_adb(["shell", "cat", "/sdcard/ui_dump.xml"])
    return ET.fromstring(xml_content)


def find_nodes_by_resource_id(root: ET.Element, resource_id: str) -> List[ET.Element]:
    """Find all nodes with a specific resource-id."""
    return root.findall(f".//*[@resource-id='{resource_id}']")


def find_node_by_text(root: ET.Element, text: str) -> Optional[ET.Element]:
    """Find a node by its text content."""
    for node in root.iter("node"):
        if node.get("text") == text:
            return node
    return None


def get_bounds(node: ET.Element) -> Tuple[int, int, int, int]:
    """Parse bounds string '[x1,y1][x2,y2]' into tuple."""
    bounds = node.get("bounds", "[0,0][0,0]")
    match = re.match(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds)
    if match:
        return tuple(map(int, match.groups()))
    return (0, 0, 0, 0)


def tap(x: int, y: int):
    """Tap at coordinates."""
    run_adb(["shell", "input", "tap", str(x), str(y)])
    time.sleep(0.3)


def swipe(x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300):
    """Swipe from (x1,y1) to (x2,y2)."""
    run_adb(["shell", "input", "swipe", str(x1), str(y1), str(x2), str(y2), str(duration_ms)])
    time.sleep(0.3)


def get_current_timestamp(root: ET.Element) -> Optional[str]:
    """Get current timestamp from the UI."""
    nodes = find_nodes_by_resource_id(root, "com.yamaha.jp.dataviewer:id/textViewGraphCurrentTime")
    if nodes:
        return nodes[0].get("text")
    return None


def get_lap_info(root: ET.Element) -> Optional[str]:
    """Get current lap info from the UI."""
    nodes = find_nodes_by_resource_id(root, "com.yamaha.jp.dataviewer:id/curlap")
    if nodes:
        return nodes[0].get("text")
    return None


def extract_visible_channels(root: ET.Element) -> Dict[str, str]:
    """Extract channel names and values from visible list items."""
    channels = {}

    # Find all dataName and dataValue pairs
    data_names = find_nodes_by_resource_id(root, "com.yamaha.jp.dataviewer:id/dataName")
    data_values = find_nodes_by_resource_id(root, "com.yamaha.jp.dataviewer:id/dataValue")

    for name_node, value_node in zip(data_names, data_values):
        name = name_node.get("text", "").strip()
        value = value_node.get("text", "").strip()

        if name and name in CHANNEL_MAP:
            normalized_name = CHANNEL_MAP[name]
            channels[normalized_name] = value

    return channels


def scroll_channel_list(direction: str = "down"):
    """Scroll the channel list up or down."""
    # Channel list is on the left side, roughly x=222
    if direction == "down":
        swipe(222, 900, 222, 600, 300)
    else:
        swipe(222, 600, 222, 900, 300)


def extract_all_channels() -> Dict[str, str]:
    """Extract all channels by scrolling through the list."""
    all_channels = {}

    # First, scroll to top
    for _ in range(5):
        scroll_channel_list("up")
    time.sleep(0.5)

    # Now scroll down and collect all channels
    previous_count = 0
    no_change_count = 0

    for _ in range(10):  # Max 10 scroll iterations
        root = dump_ui()
        visible_channels = extract_visible_channels(root)
        all_channels.update(visible_channels)

        # Check if we've found new channels
        if len(all_channels) == previous_count:
            no_change_count += 1
            if no_change_count >= 2:
                break  # No new channels found after 2 scrolls
        else:
            no_change_count = 0
            previous_count = len(all_channels)

        scroll_channel_list("down")

    return all_channels


def get_play_button_bounds(root: ET.Element) -> Optional[Tuple[int, int, int, int]]:
    """Get the play/pause button bounds."""
    nodes = find_nodes_by_resource_id(root, "com.yamaha.jp.dataviewer:id/imageButtonPlayPause")
    if nodes:
        return get_bounds(nodes[0])
    return None


def get_rewind_button_bounds(root: ET.Element) -> Optional[Tuple[int, int, int, int]]:
    """Get the rewind button bounds."""
    nodes = find_nodes_by_resource_id(root, "com.yamaha.jp.dataviewer:id/imageButtonRewind")
    if nodes:
        return get_bounds(nodes[0])
    return None


def click_play_pause():
    """Click the play/pause button."""
    root = dump_ui()
    bounds = get_play_button_bounds(root)
    if bounds:
        x = (bounds[0] + bounds[2]) // 2
        y = (bounds[1] + bounds[3]) // 2
        tap(x, y)


def reset_to_start():
    """Reset timeline to the beginning by clicking rewind multiple times."""
    root = dump_ui()
    bounds = get_rewind_button_bounds(root)
    if bounds:
        x = (bounds[0] + bounds[2]) // 2
        y = (bounds[1] + bounds[3]) // 2
        # Go back to start (rewind goes to previous lap, so we need to be careful)
        # Actually, let's just make sure we're at the beginning of the current lap
        pass  # We'll handle this differently


def seek_to_timestamp(target_seconds: float):
    """
    Navigate to a specific timestamp using play/pause.

    Since Y-Trac doesn't have a seekbar that works via tap, we use play/pause:
    1. Check current position
    2. If target > current, play for the difference
    3. Pause
    """
    # Get current timestamp
    root = dump_ui()
    current = get_current_timestamp(root)
    current_seconds = timestamp_to_seconds(current) if current else 0.0

    # Calculate time to wait
    wait_time = target_seconds - current_seconds

    # Only play if we need to advance
    if wait_time > 0.5:  # Small threshold to avoid tiny waits
        # Start playback
        click_play_pause()

        # Wait for the desired duration (playback is 1x speed)
        time.sleep(wait_time)

        # Pause
        click_play_pause()
        time.sleep(0.3)
    elif wait_time < -0.5:
        # We've passed the target - this shouldn't happen with sorted timestamps
        print(f"    WARNING: Current time ({current_seconds:.1f}s) > target ({target_seconds:.1f}s)")


def seek_to_position(percentage: float):
    """Move timeline to a percentage position (0.0 to 1.0)."""
    # This function is kept for compatibility but now uses the play/pause method
    # We'll implement it based on lap duration
    pass  # Will be called differently now


def timestamp_to_seconds(timestamp: str) -> float:
    """Convert timestamp string 'HH:MM:SS.mmm' to seconds."""
    try:
        parts = timestamp.split(":")
        if len(parts) == 3:
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = float(parts[2])
            return hours * 3600 + minutes * 60 + seconds
    except:
        pass
    return 0.0


def extract_at_timestamp(target_seconds: float, lap_duration_seconds: float) -> Dict[str, any]:
    """Extract all channel values at a specific timestamp."""
    # Use play/pause to navigate to target timestamp
    seek_to_timestamp(target_seconds)

    # Small delay to ensure UI is updated
    time.sleep(0.3)

    # Get actual timestamp (we're now paused)
    root = dump_ui()
    actual_timestamp = get_current_timestamp(root)

    # Extract all channels (while paused)
    channels = extract_all_channels()

    # Get timestamp again after extraction (should be same since paused)
    root = dump_ui()
    final_timestamp = get_current_timestamp(root)

    return {
        "target_seconds": target_seconds,
        "actual_timestamp": actual_timestamp,
        "final_timestamp": final_timestamp,
        "channels": channels
    }


def ensure_telemetry_view() -> bool:
    """Ensure we're in the telemetry view, navigate there if needed."""
    root = dump_ui()

    # Check if we're in telemetry view (has seekbar and channel list)
    seekbar = find_nodes_by_resource_id(root, "com.yamaha.jp.dataviewer:id/seekBar")
    if seekbar:
        return True

    # Look for Viewer button
    for node in root.iter("node"):
        if node.get("content-desc") == "Viewer":
            bounds = get_bounds(node)
            x = (bounds[0] + bounds[2]) // 2
            y = (bounds[1] + bounds[3]) // 2
            tap(x, y)
            time.sleep(1)
            return True

    return False


def go_to_lap(lap_number: int) -> bool:
    """Navigate to a specific lap using rewind/forward buttons."""
    max_attempts = 20

    for _ in range(max_attempts):
        root = dump_ui()
        lap_info = get_lap_info(root)

        if lap_info:
            # Parse current lap number from "LAP X / Y"
            match = re.match(r'LAP\s+(\d+)\s*/\s*(\d+)', lap_info)
            if match:
                current_lap = int(match.group(1))

                if current_lap == lap_number:
                    return True
                elif current_lap < lap_number:
                    # Need to go forward
                    bounds = find_nodes_by_resource_id(root, "com.yamaha.jp.dataviewer:id/imageButtonForward")
                    if bounds:
                        b = get_bounds(bounds[0])
                        tap((b[0] + b[2]) // 2, (b[1] + b[3]) // 2)
                        time.sleep(0.3)
                else:
                    # Need to go backward
                    bounds = find_nodes_by_resource_id(root, "com.yamaha.jp.dataviewer:id/imageButtonRewind")
                    if bounds:
                        b = get_bounds(bounds[0])
                        tap((b[0] + b[2]) // 2, (b[1] + b[3]) // 2)
                        time.sleep(0.3)

    return False


def ensure_paused():
    """Ensure playback is paused by checking timestamp stability."""
    # Take two timestamp readings 0.5s apart
    root1 = dump_ui()
    ts1 = get_current_timestamp(root1)

    time.sleep(0.5)

    root2 = dump_ui()
    ts2 = get_current_timestamp(root2)

    # If timestamps differ, we're playing - click pause
    if ts1 != ts2:
        click_play_pause()
        time.sleep(0.3)


def ensure_at_start() -> bool:
    """Ensure we're at the start of the current lap (timestamp 00:00:00)."""
    # First ensure we're paused
    ensure_paused()

    root = dump_ui()
    current = get_current_timestamp(root)

    if current and timestamp_to_seconds(current) < 0.5:
        return True  # Already at start

    # We need to restart. Go back one lap and forward again to reset
    lap_info = get_lap_info(root)
    if lap_info:
        match = re.match(r'LAP\s+(\d+)\s*/\s*(\d+)', lap_info)
        if match:
            current_lap = int(match.group(1))
            total_laps = int(match.group(2))

            # Go back one lap and forward to reset position
            if current_lap > 1:
                go_to_lap(current_lap - 1)
                time.sleep(0.3)
                go_to_lap(current_lap)
                time.sleep(0.3)
                return True

    return False


def main():
    parser = argparse.ArgumentParser(description="Extract Y-Trac telemetry values")
    parser.add_argument("--timestamps", type=str, default="0,5,10,20,30",
                        help="Comma-separated list of timestamps in seconds (default: 0,5,10,20,30)")
    parser.add_argument("--output", type=str, default=None,
                        help="Output JSON file path (default: assets/exports/ytrac_reference.json)")
    parser.add_argument("--lap", type=int, default=2,
                        help="Lap number to extract (default: 2)")
    parser.add_argument("--lap-duration", type=float, default=112.8,
                        help="Lap duration in seconds (default: 112.8 for Lap 2)")
    args = parser.parse_args()

    # Parse timestamps (must be sorted ascending for play/pause navigation)
    timestamps = sorted([float(t.strip()) for t in args.timestamps.split(",")])

    # Output path
    output_path = Path(args.output) if args.output else ASSETS_DIR / "exports" / "ytrac_reference.json"

    print("=" * 60)
    print("Y-Trac Value Extraction Tool")
    print("=" * 60)

    # Check emulator
    print("\n[1/6] Checking emulator connection...")
    if not check_emulator():
        print("ERROR: No emulator connected. Please start the emulator first.")
        return 1
    print("  -> Emulator connected")

    # Ensure telemetry view
    print("\n[2/6] Navigating to telemetry view...")
    if not ensure_telemetry_view():
        print("ERROR: Could not navigate to telemetry view.")
        print("       Please open a CTRK file in Y-Trac and select a lap.")
        return 1
    print("  -> In telemetry view")

    # Navigate to the correct lap
    print(f"\n[3/6] Navigating to Lap {args.lap}...")
    if not go_to_lap(args.lap):
        print(f"WARNING: Could not navigate to lap {args.lap}")
    time.sleep(0.5)

    # Reset to start of lap
    print("\n[4/6] Resetting to start of lap...")
    ensure_at_start()
    time.sleep(0.5)

    # Get lap info
    root = dump_ui()
    lap_info = get_lap_info(root)
    print(f"  -> Current lap: {lap_info}")

    # Extract data at each timestamp
    print(f"\n[5/6] Extracting values at {len(timestamps)} timestamps...")
    print("       (Using play/pause - timestamps are approximate)")
    results = {
        "metadata": {
            "extraction_date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "lap_info": lap_info,
            "lap_number": args.lap,
            "lap_duration_seconds": args.lap_duration,
            "timestamps_requested": timestamps,
            "note": "Timestamps are approximate due to play/pause navigation"
        },
        "samples": []
    }

    for i, ts in enumerate(timestamps):
        print(f"  -> Extracting at t={ts}s ({i+1}/{len(timestamps)})...")
        sample = extract_at_timestamp(ts, args.lap_duration)
        results["samples"].append(sample)
        print(f"     Actual: {sample['actual_timestamp']}, Channels: {len(sample['channels'])}")

    # Verify all required channels
    print("\n[6/6] Verifying required channels...")
    all_extracted = set()
    for sample in results["samples"]:
        all_extracted.update(sample["channels"].keys())

    missing = set(REQUIRED_CHANNELS) - all_extracted
    if missing:
        print(f"  WARNING: Missing channels: {missing}")
    else:
        print(f"  -> All {len(REQUIRED_CHANNELS)} required channels extracted")

    results["metadata"]["channels_extracted"] = sorted(list(all_extracted))
    results["metadata"]["required_channels"] = REQUIRED_CHANNELS
    results["metadata"]["missing_channels"] = sorted(list(missing))

    # Save results
    print(f"\nSaving results to {output_path}...")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print("  -> Done!")

    # Summary
    print("\n" + "=" * 60)
    print("EXTRACTION SUMMARY")
    print("=" * 60)
    print(f"Lap: {lap_info}")
    print(f"Timestamps: {timestamps}")
    print(f"Channels extracted: {len(all_extracted)}")
    print(f"Required channels: {len(REQUIRED_CHANNELS)}")
    if missing:
        print(f"Missing: {missing}")
    else:
        print("Status: ALL REQUIRED CHANNELS PRESENT")
    print(f"\nOutput: {output_path}")

    return 0


if __name__ == "__main__":
    exit(main())
