#!/usr/bin/env python3
"""
Compare RAW values between Python parser and Native library exports.

Usage:
    python scripts/compare_raw_values.py <native_raw.csv> <parser_gps.csv> <parser_can.csv>

This script compares the raw (uncalibrated) values to identify exactly where
the parser differs from the native library at the byte level.
"""

import csv
import sys
from pathlib import Path
from collections import defaultdict


def load_native_raw(filepath):
    """Load native raw export."""
    rows = []
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def load_parser_gps(filepath):
    """Load parser GPS export."""
    rows = []
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def main():
    if len(sys.argv) < 4:
        print("Usage: python scripts/compare_raw_values.py <native_raw.csv> <parser_gps.csv> <parser_can.csv>")
        print("\nExample:")
        print("  python scripts/compare_raw_values.py \\")
        print("    assets/exports/20250729-170818_native_raw.csv \\")
        print("    assets/exports/20250729-170818_gps.csv \\")
        print("    assets/exports/20250729-170818_can.csv")
        sys.exit(1)

    native_path = sys.argv[1]
    parser_gps_path = sys.argv[2]
    parser_can_path = sys.argv[3]

    print("=" * 80)
    print("RAW VALUES COMPARISON")
    print("=" * 80)

    native_rows = load_native_raw(native_path)
    parser_gps = load_parser_gps(parser_gps_path)

    print(f"\nNative rows: {len(native_rows)}")
    print(f"Parser GPS rows: {len(parser_gps)}")

    # Show column headers
    if native_rows:
        print(f"\nNative columns: {list(native_rows[0].keys())}")
    if parser_gps:
        print(f"Parser GPS columns: {list(parser_gps[0].keys())}")

    # Compare first few rows by timestamp
    print("\n" + "=" * 80)
    print("FIRST 10 ROWS COMPARISON")
    print("=" * 80)

    # Build parser index by file_millis
    parser_by_ms = {}
    for row in parser_gps:
        ms = int(row.get('file_millis', 0))
        if ms not in parser_by_ms:
            parser_by_ms[ms] = row

    for i, native in enumerate(native_rows[:10]):
        time_ms = int(native['time_ms'])
        native_ms = time_ms % 1000

        print(f"\n--- Native row {i+1} ---")
        print(f"  time_ms: {time_ms} (ms={native_ms})")
        print(f"  rpm_raw: {native.get('rpm_raw', '?')}")
        print(f"  lean_raw: {native.get('lean_raw', '?')}")
        print(f"  pitch_raw: {native.get('pitch_raw', '?')}")
        print(f"  accx_raw: {native.get('accx_raw', '?')}")
        print(f"  accy_raw: {native.get('accy_raw', '?')}")

        # Find matching parser row
        parser_row = parser_by_ms.get(native_ms)
        if parser_row:
            print(f"  --> Parser match (file_millis={native_ms}):")
            print(f"      file_pos: {parser_row.get('file_pos', '?')}")
            print(f"      gprmc_time: {parser_row.get('gprmc_time', '?')}")
        else:
            print(f"  --> No parser match for ms={native_ms}")

    # Summary stats
    print("\n" + "=" * 80)
    print("RAW VALUE PATTERNS")
    print("=" * 80)

    # Show first few unique lean_raw values from native
    lean_values = set()
    pitch_values = set()
    for row in native_rows[:100]:
        lean_values.add(int(row.get('lean_raw', 0)))
        pitch_values.add(int(row.get('pitch_raw', 0)))

    print(f"\nFirst 100 native rows:")
    print(f"  Unique lean_raw values: {sorted(lean_values)[:10]}...")
    print(f"  Unique pitch_raw values: {sorted(pitch_values)[:10]}...")

    print("\n" + "=" * 80)
    print("NEXT STEPS")
    print("=" * 80)
    print("""
To do a full comparison:

1. Run the modified Android app to generate:
   - <name>_native.csv (calibrated values)
   - <name>_native_raw.csv (raw values from native library)

2. Run the Python parser to generate:
   - <name>_gps.csv (GPS records with file_millis)
   - <name>_can.csv (CAN records)

3. Compare the raw values to identify byte-level differences.
""")


if __name__ == '__main__':
    main()
