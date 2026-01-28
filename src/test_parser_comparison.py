#!/usr/bin/env python3
"""
CTRK Parser Comparison Suite

Compares Python parser output against native library output by aligning
records on GPS position (latitude, longitude), which uniquely identifies
each GPRMC sentence in the binary file.

Usage:
    python test_parser_comparison.py <output_dir>

The output_dir should contain matching pairs:
    *_python.csv and *_native.csv
"""

import csv
import json
import sys
import time
from pathlib import Path
from collections import defaultdict
from typing import List, Dict, Tuple, Optional


# Channel comparison tolerances
TOLERANCES = {
    'rpm': 2,
    'throttle_grip': 0.5,
    'throttle': 0.5,
    'front_speed_kmh': 0.5,
    'rear_speed_kmh': 0.5,
    'gear': 0,
    'acc_x_g': 0.02,
    'acc_y_g': 0.02,
    'lean_deg': 0.5,
    'pitch_deg_s': 0.5,
    'water_temp': 0.5,
    'intake_temp': 0.5,
    'fuel_cc': 0.05,
    'front_brake_bar': 0.1,
    'rear_brake_bar': 0.1,
    'gps_speed_kmh': 0.5,
}

BOOL_CHANNELS = {'f_abs', 'r_abs', 'tcs', 'scs', 'lif', 'launch'}
NUMERIC_CHANNELS = list(TOLERANCES.keys())
ALL_CHANNELS = NUMERIC_CHANNELS + list(BOOL_CHANNELS)


def load_csv(path: str) -> List[dict]:
    """Load CSV file into list of dicts."""
    with open(path) as f:
        return list(csv.DictReader(f))


def pos_match(row1: dict, row2: dict, epsilon: float = 0.000005) -> bool:
    """Check if two rows have matching GPS positions within tolerance.

    Uses tight numeric tolerance (≈0.5m) to handle ±0.000002 lat/lon differences
    between Python and Native float formatting of the same NMEA sentence,
    while avoiding false matches between consecutive GPRMC sentences (~2.8m apart
    at 100 km/h, or ~0.000025 degrees).
    """
    lat1, lon1 = float(row1['latitude']), float(row1['longitude'])
    lat2, lon2 = float(row2['latitude']), float(row2['longitude'])
    return abs(lat1 - lat2) < epsilon and abs(lon1 - lon2) < epsilon


def align_records(python_rows: List[dict], native_rows: List[dict]) -> dict:
    """Align Python and Native records by GPS position using sequence matching.

    Both parsers process the same GPRMC sentences, so records should appear
    in the same order with the same (lat, lon) pairs. We use a simple
    two-pointer approach to align them, handling insertions/deletions.

    Returns dict with:
        - aligned: list of (python_row, native_row) tuples
        - python_orphans: list of python rows with no match
        - native_orphans: list of native rows with no match
    """
    aligned = []
    python_orphans = []
    native_orphans = []

    pi = 0
    ni = 0

    while pi < len(python_rows) and ni < len(native_rows):
        if pos_match(python_rows[pi], native_rows[ni]):
            aligned.append((python_rows[pi], native_rows[ni]))
            pi += 1
            ni += 1
        else:
            # Look ahead in both sequences to find best match
            # Check if python has an extra row (skip python)
            found_p_ahead = False
            for look in range(1, 4):
                if pi + look < len(python_rows) and pos_match(python_rows[pi + look], native_rows[ni]):
                    # Python has 'look' extra rows before matching
                    for j in range(look):
                        python_orphans.append(python_rows[pi + j])
                    pi += look
                    found_p_ahead = True
                    break

            if found_p_ahead:
                continue

            # Check if native has an extra row (skip native)
            found_n_ahead = False
            for look in range(1, 4):
                if ni + look < len(native_rows) and pos_match(native_rows[ni + look], python_rows[pi]):
                    for j in range(look):
                        native_orphans.append(native_rows[ni + j])
                    ni += look
                    found_n_ahead = True
                    break

            if found_n_ahead:
                continue

            # No match within lookahead - skip the row that's behind in time
            pts = int(python_rows[pi].get('time_ms', 0))
            nts = int(native_rows[ni].get('time_ms', 0))
            if pts <= nts:
                python_orphans.append(python_rows[pi])
                pi += 1
            else:
                native_orphans.append(native_rows[ni])
                ni += 1

    # Remaining rows are orphans
    while pi < len(python_rows):
        python_orphans.append(python_rows[pi])
        pi += 1
    while ni < len(native_rows):
        native_orphans.append(native_rows[ni])
        ni += 1

    return {
        'aligned': aligned,
        'python_orphans': python_orphans,
        'native_orphans': native_orphans,
    }


def compare_channels(python_row: dict, native_row: dict) -> Dict[str, dict]:
    """Compare all channels between aligned rows.

    Returns dict mapping channel name to:
        - match: bool
        - python_val: original value
        - native_val: original value
        - diff: absolute difference (numeric channels only)
    """
    results = {}

    for ch in NUMERIC_CHANNELS:
        try:
            pval = float(python_row[ch])
            nval = float(native_row[ch])
            diff = abs(pval - nval)
            tol = TOLERANCES[ch]
            results[ch] = {
                'match': diff <= tol,
                'python_val': pval,
                'native_val': nval,
                'diff': diff,
            }
        except (ValueError, KeyError):
            pass

    for ch in BOOL_CHANNELS:
        try:
            pval = str(python_row[ch]).lower()
            nval = str(native_row[ch]).lower()
            results[ch] = {
                'match': pval == nval,
                'python_val': pval,
                'native_val': nval,
                'diff': 0 if pval == nval else 1,
            }
        except KeyError:
            pass

    return results


def compare_file_pair(python_path: str, native_path: str) -> dict:
    """Compare a single Python/Native CSV pair."""
    python_rows = load_csv(python_path)
    native_rows = load_csv(native_path)

    if not python_rows or not native_rows:
        return None

    # Align records
    alignment = align_records(python_rows, native_rows)
    aligned = alignment['aligned']

    # Compare channels
    channel_stats = defaultdict(lambda: {'matches': 0, 'total': 0, 'diffs': []})

    for prow, nrow in aligned:
        results = compare_channels(prow, nrow)
        for ch, result in results.items():
            channel_stats[ch]['total'] += 1
            if result['match']:
                channel_stats[ch]['matches'] += 1
            channel_stats[ch]['diffs'].append(result['diff'])

    # Compute rates
    channel_rates = {}
    for ch in ALL_CHANNELS:
        stats = channel_stats[ch]
        if stats['total'] > 0:
            channel_rates[ch] = {
                'match_rate': 100.0 * stats['matches'] / stats['total'],
                'matches': stats['matches'],
                'total': stats['total'],
                'avg_diff': sum(stats['diffs']) / len(stats['diffs']) if stats['diffs'] else 0,
                'max_diff': max(stats['diffs']) if stats['diffs'] else 0,
            }

    # Overall match rate
    total_matches = sum(channel_stats[ch]['matches'] for ch in ALL_CHANNELS)
    total_compared = sum(channel_stats[ch]['total'] for ch in ALL_CHANNELS)
    overall_rate = 100.0 * total_matches / total_compared if total_compared > 0 else 0.0

    # Timestamp analysis
    ts_diffs = []
    for prow, nrow in aligned:
        pts = int(prow['time_ms'])
        nts = int(nrow['time_ms'])
        ts_diffs.append(pts - nts)

    return {
        'python_records': len(python_rows),
        'native_records': len(native_rows),
        'aligned': len(aligned),
        'python_orphans': len(alignment['python_orphans']),
        'native_orphans': len(alignment['native_orphans']),
        'channel_rates': channel_rates,
        'overall_rate': overall_rate,
        'total_matches': total_matches,
        'total_compared': total_compared,
        'ts_drift_start': ts_diffs[0] if ts_diffs else 0,
        'ts_drift_end': ts_diffs[-1] if ts_diffs else 0,
        'ts_drift_mean': sum(ts_diffs) / len(ts_diffs) if ts_diffs else 0,
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python test_parser_comparison.py <output_dir>")
        sys.exit(1)

    output_dir = Path(sys.argv[1])
    start_time = time.time()

    # Find matching pairs
    python_files = sorted(output_dir.glob('*_python.csv'))
    native_map = {}
    for f in output_dir.glob('*_native.csv'):
        basename = f.name.replace('_native.csv', '')
        native_map[basename] = f

    # Compare each pair
    file_results = {}
    global_channels = defaultdict(lambda: {'matches': 0, 'total': 0})
    total_aligned = 0
    total_python_orphans = 0
    total_native_orphans = 0

    for pf in python_files:
        basename = pf.name.replace('_python.csv', '')
        if basename not in native_map:
            continue

        nf = native_map[basename]
        result = compare_file_pair(str(pf), str(nf))
        if result is None:
            continue

        file_results[basename] = result
        total_aligned += result['aligned']
        total_python_orphans += result['python_orphans']
        total_native_orphans += result['native_orphans']

        for ch in ALL_CHANNELS:
            if ch in result['channel_rates']:
                cr = result['channel_rates'][ch]
                global_channels[ch]['matches'] += cr['matches']
                global_channels[ch]['total'] += cr['total']

    elapsed = time.time() - start_time

    # Print results
    print("=" * 80)
    print("PARSER COMPARISON RESULTS (GPS-position aligned)")
    print("=" * 80)
    print(f"\nFiles compared: {len(file_results)}")
    print(f"Total aligned records: {total_aligned:,}")
    print(f"Python orphans: {total_python_orphans:,}")
    print(f"Native orphans: {total_native_orphans:,}")
    print(f"Elapsed: {elapsed:.1f}s")

    print(f"\n{'Channel':<20} {'Match Rate':>10} {'Matches':>10} {'Total':>10}")
    print("-" * 55)

    total_all_matches = 0
    total_all_compared = 0

    for ch in NUMERIC_CHANNELS + sorted(BOOL_CHANNELS):
        stats = global_channels[ch]
        if stats['total'] > 0:
            rate = 100.0 * stats['matches'] / stats['total']
            print(f"{ch:<20} {rate:>9.1f}% {stats['matches']:>10,} {stats['total']:>10,}")
            total_all_matches += stats['matches']
            total_all_compared += stats['total']

    print("-" * 55)
    overall = 100.0 * total_all_matches / total_all_compared if total_all_compared > 0 else 0
    print(f"{'OVERALL':<20} {overall:>9.2f}% {total_all_matches:>10,} {total_all_compared:>10,}")

    # Per-file summary
    print(f"\n{'File':<30} {'Rate':>7} {'Aligned':>8} {'P.Orph':>7} {'N.Orph':>7} {'TS drift':>10}")
    print("-" * 75)
    for basename in sorted(file_results, key=lambda b: file_results[b]['overall_rate']):
        r = file_results[basename]
        print(f"{basename:<30} {r['overall_rate']:>6.1f}% {r['aligned']:>8,} "
              f"{r['python_orphans']:>7} {r['native_orphans']:>7} "
              f"{r['ts_drift_end']:>+8}ms")

    # Save JSON
    json_path = output_dir / 'comparison_results.json'
    json_data = {
        'summary': {
            'files': len(file_results),
            'total_aligned': total_aligned,
            'python_orphans': total_python_orphans,
            'native_orphans': total_native_orphans,
            'overall_rate': overall,
        },
        'channel_rates': {
            ch: {'rate': 100.0 * s['matches'] / s['total'] if s['total'] > 0 else 0,
                 'matches': s['matches'], 'total': s['total']}
            for ch, s in global_channels.items()
        },
        'files': {
            k: {key: val for key, val in v.items() if key != 'channel_rates'}
            for k, v in file_results.items()
        },
    }
    with open(json_path, 'w') as f:
        json.dump(json_data, f, indent=2)
    print(f"\nDetailed results saved to {json_path}")


if __name__ == '__main__':
    main()
