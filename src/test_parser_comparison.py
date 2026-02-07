#!/usr/bin/env python3
"""
CTRK Parser Comparison Suite

A validation tool that compares Python parser output against native library output
by aligning records on GPS position (latitude, longitude), which uniquely identifies
each GPRMC sentence in the binary file.

This module provides functionality to:
- Load and compare matched pairs of Python/Native CSV outputs
- Align records using GPS coordinates with sub-meter tolerance
- Compute per-channel match rates with configurable tolerances
- Generate summary reports and detailed JSON results

The comparison methodology is designed to handle the inherent differences between
the two parsers (emission timing, state handling) while accurately measuring
parsing correctness.

Usage:
    python test_parser_comparison.py <output_dir>

    The output_dir should contain matching pairs:
        *_python.csv and *_native.csv

Example:
    $ python test_parser_comparison.py output/comparison/
    ================================================================================
    PARSER COMPARISON RESULTS (GPS-position aligned)
    ================================================================================
    Files compared: 42
    Total aligned records: 420,123
    ...

Output:
    - Console summary with per-channel match rates
    - comparison_results.json with detailed per-file statistics

See Also:
    - docs/COMPARISON.md for interpretation of results
    - src/ctrk_parser.py for the Python parser being validated
"""

import csv
import json
import sys
import time
from pathlib import Path
from collections import defaultdict
from typing import List, Dict, Optional, Tuple


# =============================================================================
# CONFIGURATION
# =============================================================================

# Channel comparison tolerances
# These values account for floating-point formatting differences and minor
# timing offsets while still detecting meaningful parsing errors.
TOLERANCES = {
    'rpm': 2,                  # Integer RPM, allow rounding
    'throttle_grip': 0.5,      # Percentage, tight tolerance
    'throttle': 0.5,           # Percentage, tight tolerance
    'front_speed_kmh': 0.5,    # km/h, sub-1 km/h precision
    'rear_speed_kmh': 0.5,     # km/h, sub-1 km/h precision
    'gear': 0,                 # Integer gear, must be exact
    'acc_x_g': 0.02,           # G-force, ~0.02G noise floor
    'acc_y_g': 0.02,           # G-force, ~0.02G noise floor
    'lean_deg': 0.5,           # Degrees, sub-degree precision
    'pitch_deg_s': 0.5,        # deg/s, sub-degree precision
    'water_temp': 0.5,         # Celsius, sub-degree precision
    'intake_temp': 0.5,        # Celsius, sub-degree precision
    'fuel_cc': 0.05,           # cc, tight tolerance
    'front_brake_bar': 0.1,    # bar, tight tolerance
    'rear_brake_bar': 0.1,     # bar, tight tolerance
    'gps_speed_kmh': 0.5,      # km/h, sub-1 km/h precision
}

# Boolean channels use exact matching (string comparison)
BOOL_CHANNELS = {'f_abs', 'r_abs', 'tcs', 'scs', 'lif', 'launch'}

# All channels for iteration
NUMERIC_CHANNELS = list(TOLERANCES.keys())
ALL_CHANNELS = NUMERIC_CHANNELS + list(BOOL_CHANNELS)


# =============================================================================
# DATA LOADING
# =============================================================================

def load_csv(path: str) -> List[dict]:
    """
    Load a CSV file into a list of dictionaries.

    Each row becomes a dictionary with column headers as keys and
    cell values as string values.

    Args:
        path: Path to the CSV file.

    Returns:
        List of dictionaries, one per row (excluding header).

    Raises:
        FileNotFoundError: If the file does not exist.
        csv.Error: If the file is not valid CSV.

    Example:
        >>> rows = load_csv("session_python.csv")
        >>> print(rows[0]['rpm'])
        '5234'
    """
    with open(path) as f:
        return list(csv.DictReader(f))


# =============================================================================
# RECORD ALIGNMENT
# =============================================================================

def pos_match(row1: dict, row2: dict, epsilon: float = 0.000005) -> bool:
    """
    Check if two records have matching GPS positions within tolerance.

    Uses tight numeric tolerance (~0.5m at equator) to handle small differences
    in float formatting between Python and Native parsers processing the same
    NMEA sentence, while avoiding false matches between consecutive GPRMC
    sentences (typically ~2.8m apart at 100 km/h).

    Args:
        row1: First record dictionary with 'latitude' and 'longitude' keys.
        row2: Second record dictionary with 'latitude' and 'longitude' keys.
        epsilon: Maximum coordinate difference in degrees (default: 0.000005°).

    Returns:
        True if both latitude and longitude differ by less than epsilon.

    Note:
        At the equator, 0.000005° ≈ 0.55 meters. This is tight enough to
        distinguish unique GPRMC sentences while tolerating float formatting.
    """
    lat1, lon1 = float(row1['latitude']), float(row1['longitude'])
    lat2, lon2 = float(row2['latitude']), float(row2['longitude'])
    return abs(lat1 - lat2) < epsilon and abs(lon1 - lon2) < epsilon


def align_records(python_rows: List[dict], native_rows: List[dict]) -> dict:
    """
    Align Python and Native records by GPS position using sequence matching.

    Both parsers process the same GPRMC sentences from the CTRK file, so records
    should appear in the same order with matching (lat, lon) pairs. This function
    uses a two-pointer approach with limited lookahead to align them, handling
    insertions/deletions gracefully.

    The algorithm handles:
    - Perfect alignment (most common case)
    - Extra records on either side (orphans)
    - Small timing differences in emission

    Args:
        python_rows: List of record dictionaries from Python parser CSV.
        native_rows: List of record dictionaries from Native parser CSV.

    Returns:
        Dictionary with:
        - 'aligned': List of (python_row, native_row) tuples for matched records
        - 'python_orphans': List of python rows with no match in native
        - 'native_orphans': List of native rows with no match in python

    Example:
        >>> alignment = align_records(python_rows, native_rows)
        >>> print(f"Aligned: {len(alignment['aligned'])}")
        >>> print(f"Python orphans: {len(alignment['python_orphans'])}")
    """
    aligned = []
    python_orphans = []
    native_orphans = []

    pi = 0  # Python index
    ni = 0  # Native index

    while pi < len(python_rows) and ni < len(native_rows):
        if pos_match(python_rows[pi], native_rows[ni]):
            # Direct match - most common case
            aligned.append((python_rows[pi], native_rows[ni]))
            pi += 1
            ni += 1
        else:
            # Look ahead in both sequences to find best match
            # Check if python has extra rows (skip python)
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

            # Check if native has extra rows (skip native)
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


# =============================================================================
# CHANNEL COMPARISON
# =============================================================================

def compare_channels(python_row: dict, native_row: dict) -> Dict[str, dict]:
    """
    Compare all telemetry channels between two aligned records.

    For numeric channels, computes absolute difference and checks against
    the configured tolerance. For boolean channels, performs exact string
    comparison (case-insensitive).

    Args:
        python_row: Record dictionary from Python parser.
        native_row: Record dictionary from Native parser.

    Returns:
        Dictionary mapping channel name to result dict with:
        - 'match': bool indicating if values are within tolerance
        - 'python_val': Value from Python parser
        - 'native_val': Value from Native parser
        - 'diff': Absolute difference (numeric) or 0/1 (boolean)

    Example:
        >>> results = compare_channels(prow, nrow)
        >>> if not results['rpm']['match']:
        ...     print(f"RPM mismatch: {results['rpm']['diff']}")
    """
    results = {}

    # Compare numeric channels
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
            pass  # Skip if channel missing or invalid

    # Compare boolean channels (exact string match)
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
            pass  # Skip if channel missing

    return results


# =============================================================================
# FILE PAIR COMPARISON
# =============================================================================

def compare_file_pair(python_path: str, native_path: str) -> Optional[dict]:
    """
    Compare a single Python/Native CSV file pair.

    Loads both files, aligns records by GPS position, and computes
    per-channel match statistics.

    Args:
        python_path: Path to the Python parser output CSV.
        native_path: Path to the Native parser output CSV.

    Returns:
        Dictionary with comparison results:
        - 'python_records': Total records in Python output
        - 'native_records': Total records in Native output
        - 'aligned': Number of successfully aligned record pairs
        - 'python_orphans': Records unique to Python output
        - 'native_orphans': Records unique to Native output
        - 'channel_rates': Per-channel match rate and statistics
        - 'overall_rate': Weighted average match rate across all channels
        - 'total_matches': Sum of matching channel comparisons
        - 'total_compared': Sum of all channel comparisons
        - 'ts_drift_start': Timestamp difference at first aligned record
        - 'ts_drift_end': Timestamp difference at last aligned record
        - 'ts_drift_mean': Average timestamp difference

        Returns None if either file is empty.

    Example:
        >>> result = compare_file_pair("session_python.csv", "session_native.csv")
        >>> print(f"Overall match: {result['overall_rate']:.1f}%")
    """
    python_rows = load_csv(python_path)
    native_rows = load_csv(native_path)

    if not python_rows or not native_rows:
        return None

    # Align records by GPS position
    alignment = align_records(python_rows, native_rows)
    aligned = alignment['aligned']

    # Compare all channels for aligned records
    channel_stats = defaultdict(lambda: {'matches': 0, 'total': 0, 'diffs': []})

    for prow, nrow in aligned:
        results = compare_channels(prow, nrow)
        for ch, result in results.items():
            channel_stats[ch]['total'] += 1
            if result['match']:
                channel_stats[ch]['matches'] += 1
            channel_stats[ch]['diffs'].append(result['diff'])

    # Compute per-channel rates
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

    # Compute overall match rate (across all channel comparisons)
    total_matches = sum(channel_stats[ch]['matches'] for ch in ALL_CHANNELS)
    total_compared = sum(channel_stats[ch]['total'] for ch in ALL_CHANNELS)
    overall_rate = 100.0 * total_matches / total_compared if total_compared > 0 else 0.0

    # Analyze timestamp drift between parsers
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


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def main():
    """
    Main entry point for the comparison suite.

    Discovers Python/Native CSV pairs in the specified directory,
    runs comparisons, and outputs summary statistics to console and JSON.

    Usage:
        python test_parser_comparison.py <output_dir>

    The output_dir should contain files named:
        - *_python.csv (Python parser output)
        - *_native.csv (Native parser output)

    Matching pairs are identified by the prefix before _python/_native.

    Output:
        - Console: Summary table with per-channel and per-file statistics
        - JSON: Detailed results saved to comparison_results.json
    """
    if len(sys.argv) < 2:
        print("Usage: python test_parser_comparison.py <output_dir>")
        sys.exit(1)

    output_dir = Path(sys.argv[1])
    start_time = time.time()

    # Discover matching file pairs
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

        # Accumulate global channel statistics
        for ch in ALL_CHANNELS:
            if ch in result['channel_rates']:
                cr = result['channel_rates'][ch]
                global_channels[ch]['matches'] += cr['matches']
                global_channels[ch]['total'] += cr['total']

    elapsed = time.time() - start_time

    # Print results to console
    print("=" * 80)
    print("PARSER COMPARISON RESULTS (GPS-position aligned)")
    print("=" * 80)
    print(f"\nFiles compared: {len(file_results)}")
    print(f"Total aligned records: {total_aligned:,}")
    print(f"Python orphans: {total_python_orphans:,}")
    print(f"Native orphans: {total_native_orphans:,}")
    print(f"Elapsed: {elapsed:.1f}s")

    # Per-channel summary table
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

    # Per-file summary table
    print(f"\n{'File':<30} {'Rate':>7} {'Aligned':>8} {'P.Orph':>7} {'N.Orph':>7} {'TS drift':>10}")
    print("-" * 75)
    for basename in sorted(file_results, key=lambda b: file_results[b]['overall_rate']):
        r = file_results[basename]
        print(f"{basename:<30} {r['overall_rate']:>6.1f}% {r['aligned']:>8,} "
              f"{r['python_orphans']:>7} {r['native_orphans']:>7} "
              f"{r['ts_drift_end']:>+8}ms")

    # Save detailed JSON results
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
