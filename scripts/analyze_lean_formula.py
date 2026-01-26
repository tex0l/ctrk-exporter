#!/usr/bin/env python3
"""
Deep analysis of LEAN formula - compare calculated vs native throughout file.
"""

import struct
import csv
from pathlib import Path
from collections import defaultdict

PROJECT_ROOT = Path(__file__).parent.parent
CTRK_FILE = PROJECT_ROOT / "assets" / "original" / "20250729-170818.CTRK"
NATIVE_RAW_CSV = PROJECT_ROOT / "artifacts" / "minimal-android-app-2026-01-25T21:44:32" / "exports" / "20250729-170818_native_raw.csv"


def compute_lean_native(data: bytes) -> dict:
    """Native formula with deadband."""
    b0, b1, b2, b3 = data[0], data[1], data[2], data[3]

    val1_part = (b0 << 4) | (b2 & 0x0f)
    val1 = val1_part << 8
    val2 = ((b1 & 0x0f) << 4) | (b3 >> 4)
    sum_val = (val1 + val2) & 0xFFFF

    if sum_val < 9000:
        deviation = 9000 - sum_val
    else:
        deviation = (sum_val - 9000) & 0xFFFF

    if deviation <= 499:
        lean = 9000
    else:
        deviation_rounded = deviation - (deviation % 100)
        lean = 9000 + deviation_rounded

    return {
        'sum': sum_val,
        'deviation': deviation,
        'lean': lean & 0xFFFF,
        'lean_deg': (lean / 100) - 90
    }


def extract_can_0x0258(ctrk_path: Path):
    """Extract all CAN 0x0258 messages."""
    with open(ctrk_path, 'rb') as f:
        data = f.read()

    messages = []
    pos = 0

    while pos < len(data) - 20:
        if (data[pos] == 0x07 and
            data[pos+1] == 0xE9 and
            data[pos+2] == 0x07):

            can_id = struct.unpack('<H', data[pos+3:pos+5])[0]

            if can_id == 0x0258:
                can_data = data[pos+8:pos+16]
                messages.append((pos, can_data))
                pos += 16
                continue
        pos += 1

    return messages


def main():
    print("LEAN Formula Deep Analysis")
    print("=" * 80)

    messages = extract_can_0x0258(CTRK_FILE)
    print(f"Total CAN 0x0258 messages: {len(messages)}")

    # Load native
    native_rows = []
    with open(NATIVE_RAW_CSV, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            native_rows.append(row)

    print(f"Total native rows: {len(native_rows)}")

    # Sample at different points in the file
    sample_indices = [0, 100, 1000, 5000, 8000, 10000, 12000, 14000, 16000]

    print("\n### Sampling CAN 0x0258 at different file positions:")
    print(f"{'Idx':>6} | {'Raw':^24} | {'sum':>6} | {'dev':>5} | {'calc':>6} | {'deg':>6}")
    print("-" * 70)

    for idx in sample_indices:
        if idx < len(messages):
            pos, data = messages[idx]
            result = compute_lean_native(data)
            print(f"{idx:6} | {data.hex(' '):24} | {result['sum']:6} | {result['deviation']:5} | {result['lean']:6} | {result['lean_deg']:+6.1f}")

    # Find messages with high deviation
    print("\n### Messages with deviation > 499 (lean != upright):")
    print(f"{'Idx':>6} | {'Raw':^24} | {'sum':>6} | {'dev':>5} | {'calc':>6} | {'deg':>6}")
    print("-" * 70)

    non_upright_count = 0
    for i, (pos, data) in enumerate(messages):
        result = compute_lean_native(data)
        if result['deviation'] > 499:
            non_upright_count += 1
            if non_upright_count <= 20:
                print(f"{i:6} | {data.hex(' '):24} | {result['sum']:6} | {result['deviation']:5} | {result['lean']:6} | {result['lean_deg']:+6.1f}")

    print(f"\nTotal messages with deviation > 499: {non_upright_count}")

    # Compare distribution
    print("\n### Distribution of calculated LEAN values:")
    calc_dist = defaultdict(int)
    for pos, data in messages:
        result = compute_lean_native(data)
        calc_dist[result['lean']] += 1

    for lean_val, count in sorted(calc_dist.items()):
        deg = (lean_val / 100) - 90
        print(f"  {lean_val:5} ({deg:+6.1f}°): {count:6}")

    # Native distribution
    print("\n### Distribution of native LEAN values:")
    native_dist = defaultdict(int)
    for row in native_rows:
        lean = int(row['lean_raw'])
        native_dist[lean] += 1

    for lean_val, count in sorted(native_dist.items()):
        deg = (lean_val / 100) - 90
        print(f"  {lean_val:5} ({deg:+6.1f}°): {count:6}")

    # Check for a match by looking at sum values that should give non-9000 lean
    print("\n### Analysis of sum value distribution:")
    sum_dist = defaultdict(int)
    for pos, data in messages:
        result = compute_lean_native(data)
        # Round to nearest 100
        sum_rounded = round(result['sum'] / 100) * 100
        sum_dist[sum_rounded] += 1

    for sum_val, count in sorted(sum_dist.items()):
        deviation = abs(sum_val - 9000)
        print(f"  sum~{sum_val:5}: {count:6} (deviation={deviation:4})")

    # The problem might be that the formula is correct but the transformation is different
    # Let me try without the deadband
    print("\n### Testing without deadband (just round deviation):")
    no_deadband_dist = defaultdict(int)
    for pos, data in messages:
        b0, b1, b2, b3 = data[0], data[1], data[2], data[3]
        val1_part = (b0 << 4) | (b2 & 0x0f)
        val1 = val1_part << 8
        val2 = ((b1 & 0x0f) << 4) | (b3 >> 4)
        sum_val = (val1 + val2) & 0xFFFF

        # Just use sum directly, rounded
        lean = round(sum_val / 100) * 100
        no_deadband_dist[lean] += 1

    for lean_val, count in list(sorted(no_deadband_dist.items()))[:15]:
        deg = (lean_val / 100) - 90
        print(f"  {lean_val:5} ({deg:+6.1f}°): {count:6}")


if __name__ == '__main__':
    main()
