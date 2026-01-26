#!/usr/bin/env python3
"""Compare native app output with Y-Trac reference data."""

import json
import csv
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
ASSETS_DIR = PROJECT_ROOT / "assets" / "exports"

def load_ytrac_reference():
    """Load Y-Trac reference JSON."""
    with open(ASSETS_DIR / "ytrac_reference.json", "r") as f:
        return json.load(f)

def load_native_csv():
    """Load native CSV and return rows by lap."""
    rows_by_lap = {}
    with open(ASSETS_DIR / "20250729-170818_native.csv", "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            lap = int(row["lap"])
            if lap not in rows_by_lap:
                rows_by_lap[lap] = []
            rows_by_lap[lap].append(row)
    return rows_by_lap

def timestamp_to_ms(timestamp_str):
    """Convert HH:MM:SS.mmm to milliseconds."""
    parts = timestamp_str.split(":")
    hours = int(parts[0])
    minutes = int(parts[1])
    seconds = float(parts[2])
    return int((hours * 3600 + minutes * 60 + seconds) * 1000)

def find_closest_row(rows, target_ms, lap_start_ms):
    """Find the row closest to target time offset."""
    target_absolute = lap_start_ms + target_ms
    closest = None
    min_diff = float('inf')
    for row in rows:
        row_ms = int(row["time_ms"])
        diff = abs(row_ms - target_absolute)
        if diff < min_diff:
            min_diff = diff
            closest = row
    return closest, min_diff

# Channel mapping: Y-Trac name -> CSV column name
CHANNEL_MAP = {
    "rpm": "rpm",
    "throttle_grip": "throttle_grip",
    "throttle": "throttle",
    "r_speed": "rear_speed_kmh",
    "f_speed": "front_speed_kmh",
    "gear": "gear",
    "lean": "lean_deg",
    "pitch": "pitch_deg_s",
    "r_brake": "rear_brake_bar",
    "f_brake": "front_brake_bar",
    "water_temp": "water_temp",
    "air_temp": "intake_temp",
    "fuel": "fuel_cc",
    "acc_x": "acc_x_g",
    "acc_y": "acc_y_g",
}

def parse_value(v):
    """Parse a value string to float."""
    if v == "--" or v == "":
        return None
    try:
        return float(v)
    except:
        return None

def main():
    print("=" * 70)
    print("COMPARISON: Y-Trac vs App Minimale (formulas corrected)")
    print("=" * 70)

    # Load data
    ytrac = load_ytrac_reference()
    native_by_lap = load_native_csv()

    lap_number = ytrac["metadata"]["lap_number"]
    print(f"\nLap: {lap_number}")
    print(f"Y-Trac samples: {len(ytrac['samples'])}")

    if lap_number not in native_by_lap:
        print(f"ERROR: Lap {lap_number} not found in native CSV")
        return

    native_rows = native_by_lap[lap_number]
    lap_start_ms = int(native_rows[0]["time_ms"])
    print(f"Native rows for lap {lap_number}: {len(native_rows)}")
    print(f"Lap start timestamp: {lap_start_ms}")

    # Compare each sample
    all_errors = {}

    for sample in ytrac["samples"]:
        target_ts = sample["actual_timestamp"]
        target_ms = timestamp_to_ms(target_ts)

        native_row, time_diff = find_closest_row(native_rows, target_ms, lap_start_ms)

        print(f"\n--- Timestamp: {target_ts} (offset: {target_ms}ms, match diff: {time_diff}ms) ---")

        ytrac_channels = sample["channels"]

        for ytrac_name, csv_col in CHANNEL_MAP.items():
            ytrac_val = parse_value(ytrac_channels.get(ytrac_name, "--"))
            native_val = parse_value(native_row.get(csv_col, ""))

            if ytrac_val is None:
                print(f"  {ytrac_name:15}: Y-Trac=-- (skipped)")
                continue

            if native_val is None:
                print(f"  {ytrac_name:15}: Native missing")
                continue

            # Calculate error
            if abs(ytrac_val) > 0.01:
                error_pct = ((native_val - ytrac_val) / ytrac_val) * 100
            else:
                error_pct = native_val - ytrac_val  # Absolute error for near-zero values

            # Track errors
            if ytrac_name not in all_errors:
                all_errors[ytrac_name] = []
            all_errors[ytrac_name].append({
                "ytrac": ytrac_val,
                "native": native_val,
                "error_pct": error_pct
            })

            # Status indicator
            if abs(error_pct) < 2:
                status = "✓"
            elif abs(error_pct) < 10:
                status = "~"
            else:
                status = "✗"

            print(f"  {ytrac_name:15}: Y-Trac={ytrac_val:>10}, Native={native_val:>10.2f}, Err={error_pct:>7.1f}% {status}")

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY BY CHANNEL")
    print("=" * 70)

    channels_ok = []
    channels_minor = []
    channels_major = []

    for channel, errors in sorted(all_errors.items()):
        # Filter out near-zero comparisons (unreliable)
        valid_errors = [e for e in errors if abs(e["ytrac"]) > 0.5]

        if not valid_errors:
            avg_err = 0
            status = "⚪ (near-zero values)"
        else:
            avg_err = sum(e["error_pct"] for e in valid_errors) / len(valid_errors)
            if abs(avg_err) < 2:
                status = "✓ OK"
                channels_ok.append(channel)
            elif abs(avg_err) < 10:
                status = "~ Minor"
                channels_minor.append(channel)
            else:
                status = "✗ MAJOR"
                channels_major.append(channel)

        print(f"  {channel:15}: avg error = {avg_err:>7.1f}%  {status}")

    print("\n" + "-" * 70)
    print(f"Channels OK (<2% error):     {len(channels_ok):2} - {', '.join(channels_ok) or 'none'}")
    print(f"Channels Minor (2-10% error): {len(channels_minor):2} - {', '.join(channels_minor) or 'none'}")
    print(f"Channels Major (>10% error):  {len(channels_major):2} - {', '.join(channels_major) or 'none'}")

    return all_errors

if __name__ == "__main__":
    main()
