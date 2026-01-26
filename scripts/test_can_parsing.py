#!/usr/bin/env python3
"""
Test CAN message parsing against native library output.

This script extracts CAN messages from a CTRK file and compares the parsed
values with the native library output to verify the parsing formulas.

Usage:
    python scripts/test_can_parsing.py
"""

import struct
import csv
from pathlib import Path
from collections import defaultdict
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional

PROJECT_ROOT = Path(__file__).parent.parent
CTRK_FILE = PROJECT_ROOT / "assets" / "original" / "20250729-170818.CTRK"
NATIVE_RAW_CSV = PROJECT_ROOT / "artifacts" / "minimal-android-app-2026-01-25T21:44:32" / "exports" / "20250729-170818_native_raw.csv"


# =============================================================================
# CAN PARSING FUNCTIONS (from reverse engineering)
# =============================================================================

def parse_can_0x0209(data: bytes) -> dict:
    """Engine: RPM & Gear"""
    rpm = (data[0] << 8) | data[1]
    gear = data[4] & 0x07
    if gear == 7:
        gear = None  # Invalid
    return {'rpm': rpm, 'gear': gear}


def parse_can_0x0215(data: bytes) -> dict:
    """Throttle: TPS, APS, electronic controls"""
    tps = (data[0] << 8) | data[1]
    aps = (data[2] << 8) | data[3]
    launch = 1 if (data[6] & 0x60) else 0
    tcs = (data[7] >> 5) & 1
    scs = (data[7] >> 4) & 1
    lif = (data[7] >> 3) & 1
    return {'tps': tps, 'aps': aps, 'launch': launch, 'tcs': tcs, 'scs': scs, 'lif': lif}


def parse_can_0x023e(data: bytes) -> dict:
    """Temperature & Fuel"""
    water_temp = data[0]  # Single byte!
    intake_temp = data[1]  # Single byte!
    fuel_delta = (data[2] << 8) | data[3]
    return {'water_temp': water_temp, 'intake_temp': intake_temp, 'fuel_delta': fuel_delta}


def parse_can_0x0250(data: bytes) -> dict:
    """Motion: Acceleration X/Y"""
    acc_x = (data[0] << 8) | data[1]
    acc_y = (data[2] << 8) | data[3]
    return {'acc_x': acc_x, 'acc_y': acc_y}


def parse_can_0x0258_simple(data: bytes) -> dict:
    """IMU: Lean & Pitch (simple formula - sum only)"""
    b0, b1, b2, b3 = data[0], data[1], data[2], data[3]
    val1_part = (b0 << 4) | (b2 & 0x0f)
    val1 = val1_part << 8
    val2 = ((b1 & 0x0f) << 4) | (b3 >> 4)
    lean_sum = (val1 + val2) & 0xFFFF
    pitch = (data[6] << 8) | data[7]
    return {'lean_sum': lean_sum, 'pitch': pitch}


def parse_can_0x0258_native(data: bytes) -> dict:
    """IMU: Lean & Pitch (native formula with deadband)"""
    b0, b1, b2, b3 = data[0], data[1], data[2], data[3]

    # Step 1: Extract values from packed bytes
    val1_part = (b0 << 4) | (b2 & 0x0f)
    val1 = val1_part << 8
    val2 = ((b1 & 0x0f) << 4) | (b3 >> 4)

    # Step 2: Compute sum
    sum_val = (val1 + val2) & 0xFFFF

    # Step 3: Transform to deviation from center (9000)
    if sum_val < 9000:
        deviation = 9000 - sum_val
    else:
        deviation = (sum_val - 9000) & 0xFFFF

    # Step 4: Deadband - if within ±5° (~499 raw), return upright
    if deviation <= 499:
        lean = 9000  # Upright
    else:
        # Step 5: Round to nearest degree
        deviation_rounded = deviation - (deviation % 100)
        lean = 9000 + deviation_rounded

    lean = lean & 0xFFFF
    pitch = (data[6] << 8) | data[7]
    return {'lean': lean, 'pitch': pitch, 'lean_sum': sum_val}


def parse_can_0x0260(data: bytes) -> dict:
    """Brake pressure"""
    front = (data[0] << 8) | data[1]
    rear = (data[2] << 8) | data[3]
    return {'front_brake': front, 'rear_brake': rear}


def parse_can_0x0264(data: bytes) -> dict:
    """Wheel speed"""
    front = (data[0] << 8) | data[1]
    rear = (data[2] << 8) | data[3]
    return {'front_speed': front, 'rear_speed': rear}


def parse_can_0x0268(data: bytes) -> dict:
    """ABS status"""
    f_abs = data[4] & 1
    r_abs = (data[4] >> 1) & 1
    return {'f_abs': bool(f_abs), 'r_abs': bool(r_abs)}


# =============================================================================
# CTRK FILE PARSING
# =============================================================================

def extract_can_messages(ctrk_path: Path) -> Dict[int, List[Tuple[int, bytes]]]:
    """Extract all CAN messages from CTRK file grouped by CAN ID."""
    with open(ctrk_path, 'rb') as f:
        data = f.read()

    valid_can_ids = {
        0x0209, 0x0215, 0x0226, 0x0227, 0x023E, 0x0250,
        0x0257, 0x0258, 0x0260, 0x0264, 0x0267, 0x0268,
        0x0511, 0x051B
    }

    messages = defaultdict(list)
    pos = 0

    while pos < len(data) - 20:
        # Look for CAN marker: 07 E9 07
        if (data[pos] == 0x07 and
            data[pos+1] == 0xE9 and
            data[pos+2] == 0x07):

            can_id = struct.unpack('<H', data[pos+3:pos+5])[0]

            if can_id in valid_can_ids:
                can_data = data[pos+8:pos+16]
                messages[can_id].append((pos, can_data))
                pos += 16
                continue

        pos += 1

    return messages


def load_native_raw_csv(csv_path: Path) -> List[dict]:
    """Load native raw values from CSV."""
    rows = []
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


# =============================================================================
# TESTS
# =============================================================================

def test_lean_formula():
    """Test the LEAN formula against native values."""
    print("=" * 80)
    print("TEST: LEAN Formula Verification")
    print("=" * 80)

    messages = extract_can_messages(CTRK_FILE)
    native_rows = load_native_raw_csv(NATIVE_RAW_CSV)

    can_0x0258 = messages[0x0258]
    print(f"Found {len(can_0x0258)} CAN 0x0258 messages")
    print(f"Native rows: {len(native_rows)}")

    # Test first 100 messages
    print("\n### Sample CAN 0x0258 parsing:")
    print(f"{'Idx':>5} | {'Raw bytes':^24} | {'sum':>6} | {'Native':>6} | {'Calc':>6} | {'Match':^5}")
    print("-" * 70)

    match_count = 0
    mismatch_samples = []

    # We can't directly match CAN messages to native rows by index
    # because native has GPS-aligned records, not raw CAN messages.
    # Instead, let's verify the formula produces valid values.

    lean_distribution = defaultdict(int)

    for i, (pos, data) in enumerate(can_0x0258[:50]):
        result = parse_can_0x0258_native(data)
        lean_calculated = result['lean']
        lean_sum = result['lean_sum']

        lean_distribution[lean_calculated] += 1

        if i < 20:
            print(f"{i:5} | {data.hex(' '):24} | {lean_sum:6} | {'?':>6} | {lean_calculated:6} |")

    print(f"\n### Calculated LEAN distribution (first 50 messages):")
    for lean_val, count in sorted(lean_distribution.items()):
        deg = (lean_val / 100) - 90
        print(f"  lean_raw={lean_val:5} → {deg:+6.1f}° : {count} occurrences")

    print(f"\n### Native LEAN distribution (all rows):")
    native_lean_dist = defaultdict(int)
    for row in native_rows:
        lean = int(row['lean_raw'])
        native_lean_dist[lean] += 1

    for lean_val, count in sorted(native_lean_dist.items())[:15]:
        deg = (lean_val / 100) - 90
        print(f"  lean_raw={lean_val:5} → {deg:+6.1f}° : {count} occurrences")

    # Check if values are in same range
    calc_min = min(lean_distribution.keys())
    calc_max = max(lean_distribution.keys())
    native_min = min(native_lean_dist.keys())
    native_max = max(native_lean_dist.keys())

    print(f"\n### Value range comparison:")
    print(f"  Calculated: {calc_min} to {calc_max}")
    print(f"  Native:     {native_min} to {native_max}")


def test_other_can_messages():
    """Test other CAN message parsing."""
    print("\n" + "=" * 80)
    print("TEST: Other CAN Message Parsing")
    print("=" * 80)

    messages = extract_can_messages(CTRK_FILE)
    native_rows = load_native_raw_csv(NATIVE_RAW_CSV)

    # Test CAN 0x0209 (Engine)
    print("\n### CAN 0x0209 (Engine) - First 5 messages:")
    for i, (pos, data) in enumerate(messages[0x0209][:5]):
        result = parse_can_0x0209(data)
        print(f"  {i}: {data.hex(' ')} → RPM={result['rpm']}, Gear={result['gear']}")

    # Compare with native
    print(f"\n  Native first 5 rows: RPM={[int(r['rpm_raw']) for r in native_rows[1:6]]}")

    # Test CAN 0x0215 (Throttle)
    print("\n### CAN 0x0215 (Throttle) - First 5 messages:")
    for i, (pos, data) in enumerate(messages[0x0215][:5]):
        result = parse_can_0x0215(data)
        print(f"  {i}: {data.hex(' ')} → TPS={result['tps']}, APS={result['aps']}")

    print(f"\n  Native first 5 rows: TPS={[int(r['tps_raw']) for r in native_rows[1:6]]}")
    print(f"  Native first 5 rows: APS={[int(r['aps_raw']) for r in native_rows[1:6]]}")

    # Test CAN 0x023E (Temperature)
    print("\n### CAN 0x023E (Temperature) - First 5 messages:")
    for i, (pos, data) in enumerate(messages[0x023E][:5]):
        result = parse_can_0x023e(data)
        print(f"  {i}: {data.hex(' ')} → WT={result['water_temp']}, INTT={result['intake_temp']}, Fuel_delta={result['fuel_delta']}")

    print(f"\n  Native first 10 rows: WT={[int(r['wt_raw']) for r in native_rows[1:11]]}")

    # Test CAN 0x0250 (Acceleration)
    print("\n### CAN 0x0250 (Acceleration) - First 5 messages:")
    for i, (pos, data) in enumerate(messages[0x0250][:5]):
        result = parse_can_0x0250(data)
        print(f"  {i}: {data.hex(' ')} → ACC_X={result['acc_x']}, ACC_Y={result['acc_y']}")

    print(f"\n  Native first 5 rows: ACCX={[int(r['accx_raw']) for r in native_rows[1:6]]}")
    print(f"  Native first 5 rows: ACCY={[int(r['accy_raw']) for r in native_rows[1:6]]}")

    # Test CAN 0x0264 (Speed)
    print("\n### CAN 0x0264 (Speed) - First 5 messages:")
    for i, (pos, data) in enumerate(messages[0x0264][:5]):
        result = parse_can_0x0264(data)
        print(f"  {i}: {data.hex(' ')} → Front={result['front_speed']}, Rear={result['rear_speed']}")

    print(f"\n  Native first 5 rows: FSPEED={[int(r['fspeed_raw']) for r in native_rows[1:6]]}")
    print(f"  Native first 5 rows: RSPEED={[int(r['rspeed_raw']) for r in native_rows[1:6]]}")


def print_summary():
    """Print summary of CAN message counts."""
    print("\n" + "=" * 80)
    print("SUMMARY: CAN Message Counts in CTRK File")
    print("=" * 80)

    messages = extract_can_messages(CTRK_FILE)

    can_names = {
        0x0209: "Engine (RPM, Gear)",
        0x0215: "Throttle (TPS, APS)",
        0x023E: "Temperature & Fuel",
        0x0250: "Acceleration (X, Y)",
        0x0258: "IMU (Lean, Pitch)",
        0x0260: "Brake Pressure",
        0x0264: "Wheel Speed",
        0x0268: "ABS Status",
        0x0226: "Raw CAN 1",
        0x0227: "Raw CAN 2",
        0x0511: "Raw CAN 3",
        0x051B: "Raw CAN 4",
    }

    total = 0
    for can_id in sorted(messages.keys()):
        count = len(messages[can_id])
        name = can_names.get(can_id, "Unknown")
        print(f"  0x{can_id:04X}: {count:6} messages - {name}")
        total += count

    print(f"\n  Total: {total} CAN messages")


def main():
    print("CTRK CAN Parsing Test Suite")
    print("=" * 80)
    print(f"CTRK File: {CTRK_FILE}")
    print(f"Native CSV: {NATIVE_RAW_CSV}")
    print()

    if not CTRK_FILE.exists():
        print(f"ERROR: CTRK file not found: {CTRK_FILE}")
        return

    if not NATIVE_RAW_CSV.exists():
        print(f"ERROR: Native CSV not found: {NATIVE_RAW_CSV}")
        return

    print_summary()
    test_lean_formula()
    test_other_can_messages()

    print("\n" + "=" * 80)
    print("Test suite completed.")
    print("=" * 80)


if __name__ == '__main__':
    main()
