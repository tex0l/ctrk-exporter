#!/usr/bin/env python3
"""
Comprehensive Test Suite for CTRK Parser Validation

Compares Python parser output against native library output (reference).
Generates detailed statistical analysis and identifies root causes of discrepancies.

Usage:
    python test_parser_comparison.py <input_dir> <output_dir> [--single FILE]

Requirements:
    - Python CSV files in output_dir with pattern *_python.csv
    - Native CSV files in output_dir with pattern *_native.csv
"""

import csv
import json
import sys
import os
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Tuple, Any
from collections import defaultdict
import statistics


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class ChannelStats:
    """Statistics for a single channel comparison."""
    channel: str
    tolerance: float
    total_compared: int = 0
    exact_matches: int = 0
    within_tolerance: int = 0
    mismatches: int = 0

    # Value differences
    differences: List[float] = field(default_factory=list)
    avg_diff: float = 0.0
    max_diff: float = 0.0
    std_diff: float = 0.0

    # Value ranges
    python_min: float = float('inf')
    python_max: float = float('-inf')
    native_min: float = float('inf')
    native_max: float = float('-inf')

    # Position of max difference (for debugging)
    max_diff_index: int = -1
    max_diff_timestamp: int = 0

    def match_rate(self) -> float:
        if self.total_compared == 0:
            return 0.0
        return (self.within_tolerance / self.total_compared) * 100

    def exact_match_rate(self) -> float:
        if self.total_compared == 0:
            return 0.0
        return (self.exact_matches / self.total_compared) * 100

    def finalize(self):
        """Calculate final statistics."""
        if self.differences:
            self.avg_diff = statistics.mean(self.differences)
            self.max_diff = max(abs(d) for d in self.differences)
            if len(self.differences) > 1:
                self.std_diff = statistics.stdev(self.differences)


@dataclass
class TimestampAnalysis:
    """Analysis of timestamp patterns."""
    total_records: int = 0

    # Native patterns
    native_intervals: List[int] = field(default_factory=list)
    native_avg_interval: float = 0.0
    native_std_interval: float = 0.0
    native_min_interval: int = 0
    native_max_interval: int = 0
    native_100ms_count: int = 0
    native_100ms_rate: float = 0.0

    # Python patterns
    python_intervals: List[int] = field(default_factory=list)
    python_avg_interval: float = 0.0
    python_std_interval: float = 0.0
    python_min_interval: int = 0
    python_max_interval: int = 0
    python_100ms_count: int = 0
    python_100ms_rate: float = 0.0

    # Alignment
    aligned_count: int = 0
    timestamp_drift_avg: float = 0.0
    timestamp_drift_max: int = 0

    # Issues detected
    python_time_reversals: int = 0
    native_time_reversals: int = 0

    def finalize(self):
        """Calculate final statistics."""
        if self.native_intervals:
            self.native_avg_interval = statistics.mean(self.native_intervals)
            self.native_min_interval = min(self.native_intervals)
            self.native_max_interval = max(self.native_intervals)
            if len(self.native_intervals) > 1:
                self.native_std_interval = statistics.stdev(self.native_intervals)
            # Count 100ms intervals (95-105ms tolerance)
            self.native_100ms_count = sum(1 for i in self.native_intervals if 95 <= i <= 105)
            self.native_100ms_rate = (self.native_100ms_count / len(self.native_intervals)) * 100

        if self.python_intervals:
            self.python_avg_interval = statistics.mean(self.python_intervals)
            self.python_min_interval = min(self.python_intervals)
            self.python_max_interval = max(self.python_intervals)
            if len(self.python_intervals) > 1:
                self.python_std_interval = statistics.stdev(self.python_intervals)
            self.python_100ms_count = sum(1 for i in self.python_intervals if 95 <= i <= 105)
            self.python_100ms_rate = (self.python_100ms_count / len(self.python_intervals)) * 100


@dataclass
class FileComparison:
    """Complete comparison results for a single file."""
    filename: str
    python_records: int = 0
    native_records: int = 0
    aligned_records: int = 0

    channels: Dict[str, ChannelStats] = field(default_factory=dict)
    timestamp_analysis: TimestampAnalysis = field(default_factory=TimestampAnalysis)

    overall_match_rate: float = 0.0
    error: Optional[str] = None

    def finalize(self):
        """Calculate overall statistics."""
        for stats in self.channels.values():
            stats.finalize()
        self.timestamp_analysis.finalize()

        # Overall match rate across all channels
        total_matches = sum(s.within_tolerance for s in self.channels.values())
        total_compared = sum(s.total_compared for s in self.channels.values())
        if total_compared > 0:
            self.overall_match_rate = (total_matches / total_compared) * 100


@dataclass
class TestResults:
    """Aggregate results across all files."""
    summary: Dict[str, Any] = field(default_factory=dict)
    aggregate_channels: Dict[str, ChannelStats] = field(default_factory=dict)
    files: List[FileComparison] = field(default_factory=list)

    # Root cause analysis
    root_causes: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


# =============================================================================
# CHANNEL DEFINITIONS
# =============================================================================

# Channel tolerances for comparison
CHANNEL_TOLERANCES = {
    # Numeric channels
    'rpm': 10,              # RPM can vary slightly
    'throttle_grip': 0.5,   # Percentage
    'throttle': 0.5,        # Percentage
    'water_temp': 0.5,      # Celsius
    'intake_temp': 0.5,     # Celsius
    'front_speed_kmh': 0.5, # km/h
    'rear_speed_kmh': 0.5,  # km/h
    'gps_speed_kmh': 0.5,   # km/h
    'fuel_cc': 0.1,         # cc
    'lean_deg': 1.0,        # degrees
    'pitch_deg_s': 1.0,     # deg/s
    'acc_x_g': 0.01,        # G
    'acc_y_g': 0.01,        # G
    'front_brake_bar': 0.5, # bar
    'rear_brake_bar': 0.5,  # bar
    'gear': 0,              # Exact match

    # Boolean/discrete channels (exact match)
    'f_abs': 0,
    'r_abs': 0,
    'tcs': 0,
    'scs': 0,
    'lif': 0,
    'launch': 0,
}

# Channels to compare (in CSV order)
CHANNELS_TO_COMPARE = list(CHANNEL_TOLERANCES.keys())


# =============================================================================
# CSV PARSING
# =============================================================================

def load_csv(filepath: Path) -> List[Dict[str, Any]]:
    """Load CSV file and return list of records."""
    records = []
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            record = {}
            for key, value in row.items():
                # Convert types
                if key in ('lap', 'time_ms', 'gear', 'tcs', 'scs', 'lif', 'launch'):
                    record[key] = int(value) if value else 0
                elif key in ('f_abs', 'r_abs'):
                    record[key] = 1 if value.lower() == 'true' else 0
                elif key in ('latitude', 'longitude'):
                    record[key] = float(value) if value else 0.0
                else:
                    try:
                        record[key] = float(value) if value else 0.0
                    except ValueError:
                        record[key] = value
            records.append(record)
    return records


def parse_value(value: str, channel: str) -> float:
    """Parse a CSV value to float for comparison."""
    if channel in ('f_abs', 'r_abs'):
        return 1.0 if value.lower() == 'true' else 0.0
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0


# =============================================================================
# ALIGNMENT ALGORITHM
# =============================================================================

def align_by_timestamp(python_records: List[Dict], native_records: List[Dict],
                       tolerance_ms: int = 50) -> List[Tuple[Dict, Dict, int]]:
    """
    Align Python and Native records by timestamp.

    Returns list of (python_record, native_record, time_diff) tuples.
    Uses nearest-neighbor matching within tolerance.
    """
    aligned = []

    if not python_records or not native_records:
        return aligned

    # Create timestamp index for native records
    native_by_time = {r['time_ms']: r for r in native_records}
    native_times = sorted(native_by_time.keys())

    for py_rec in python_records:
        py_time = py_rec['time_ms']

        # Binary search for nearest native timestamp
        best_match = None
        best_diff = float('inf')

        # Simple linear search for nearest (could optimize with bisect)
        for nat_time in native_times:
            diff = abs(nat_time - py_time)
            if diff < best_diff:
                best_diff = diff
                best_match = nat_time
            elif diff > best_diff:
                # Times are sorted, so we can stop
                break

        if best_match is not None and best_diff <= tolerance_ms:
            aligned.append((py_rec, native_by_time[best_match], best_diff))

    return aligned


def align_by_index(python_records: List[Dict], native_records: List[Dict]) -> List[Tuple[Dict, Dict]]:
    """
    Simple index-based alignment (1:1 comparison).
    Useful when record counts are similar.
    """
    min_len = min(len(python_records), len(native_records))
    return [(python_records[i], native_records[i]) for i in range(min_len)]


# =============================================================================
# COMPARISON LOGIC
# =============================================================================

def compare_channel(python_val: float, native_val: float,
                    tolerance: float) -> Tuple[bool, bool, float]:
    """
    Compare two values with tolerance.

    Returns:
        (exact_match, within_tolerance, difference)
    """
    diff = python_val - native_val
    exact = abs(diff) < 0.0001
    within = abs(diff) <= tolerance
    return exact, within, diff


def analyze_timestamps(python_records: List[Dict],
                       native_records: List[Dict]) -> TimestampAnalysis:
    """Analyze timestamp patterns in both datasets."""
    analysis = TimestampAnalysis()

    # Native timestamp intervals
    native_times = [r['time_ms'] for r in native_records]
    for i in range(1, len(native_times)):
        interval = native_times[i] - native_times[i-1]
        analysis.native_intervals.append(interval)
        if interval < 0:
            analysis.native_time_reversals += 1

    # Python timestamp intervals
    python_times = [r['time_ms'] for r in python_records]
    for i in range(1, len(python_times)):
        interval = python_times[i] - python_times[i-1]
        analysis.python_intervals.append(interval)
        if interval < 0:
            analysis.python_time_reversals += 1

    analysis.total_records = max(len(python_records), len(native_records))
    return analysis


def compare_file(python_csv: Path, native_csv: Path) -> FileComparison:
    """Compare Python and Native CSV outputs for a single file."""
    filename = python_csv.stem.replace('_python', '')
    comparison = FileComparison(filename=filename)

    try:
        python_records = load_csv(python_csv)
        native_records = load_csv(native_csv)
    except Exception as e:
        comparison.error = f"Failed to load CSVs: {e}"
        return comparison

    comparison.python_records = len(python_records)
    comparison.native_records = len(native_records)

    if not python_records or not native_records:
        comparison.error = "No records (empty file)"
        return comparison

    # Analyze timestamps
    comparison.timestamp_analysis = analyze_timestamps(python_records, native_records)

    # Align records by timestamp
    aligned = align_by_timestamp(python_records, native_records, tolerance_ms=60)
    comparison.aligned_records = len(aligned)
    comparison.timestamp_analysis.aligned_count = len(aligned)

    if not aligned:
        comparison.error = "No records could be aligned by timestamp"
        return comparison

    # Calculate timestamp drift
    drifts = [diff for _, _, diff in aligned]
    comparison.timestamp_analysis.timestamp_drift_avg = statistics.mean(drifts) if drifts else 0
    comparison.timestamp_analysis.timestamp_drift_max = max(drifts) if drifts else 0

    # Initialize channel stats
    for channel, tolerance in CHANNEL_TOLERANCES.items():
        comparison.channels[channel] = ChannelStats(channel=channel, tolerance=tolerance)

    # Compare each aligned record
    for idx, (py_rec, nat_rec, time_diff) in enumerate(aligned):
        for channel in CHANNELS_TO_COMPARE:
            if channel not in py_rec or channel not in nat_rec:
                continue

            py_val = py_rec[channel]
            nat_val = nat_rec[channel]

            # Handle boolean conversion
            if isinstance(py_val, str):
                py_val = 1.0 if py_val.lower() == 'true' else 0.0
            if isinstance(nat_val, str):
                nat_val = 1.0 if nat_val.lower() == 'true' else 0.0

            stats = comparison.channels[channel]
            tolerance = CHANNEL_TOLERANCES[channel]

            exact, within, diff = compare_channel(float(py_val), float(nat_val), tolerance)

            stats.total_compared += 1
            if exact:
                stats.exact_matches += 1
            if within:
                stats.within_tolerance += 1
            else:
                stats.mismatches += 1

            stats.differences.append(diff)

            # Track ranges
            stats.python_min = min(stats.python_min, float(py_val))
            stats.python_max = max(stats.python_max, float(py_val))
            stats.native_min = min(stats.native_min, float(nat_val))
            stats.native_max = max(stats.native_max, float(nat_val))

            # Track max diff location
            if abs(diff) > abs(stats.max_diff):
                stats.max_diff = diff
                stats.max_diff_index = idx
                stats.max_diff_timestamp = py_rec['time_ms']

    comparison.finalize()
    return comparison


# =============================================================================
# AGGREGATE ANALYSIS
# =============================================================================

def aggregate_results(file_comparisons: List[FileComparison]) -> TestResults:
    """Aggregate results across all files."""
    results = TestResults()
    results.files = file_comparisons

    # Count files with various statuses
    total_files = len(file_comparisons)
    files_with_native = sum(1 for f in file_comparisons if f.native_records > 0)
    files_with_errors = sum(1 for f in file_comparisons if f.error)

    results.summary = {
        'total_files': total_files,
        'files_with_native': files_with_native,
        'files_with_errors': files_with_errors,
    }

    # Aggregate channel statistics
    for channel in CHANNELS_TO_COMPARE:
        agg_stats = ChannelStats(channel=channel, tolerance=CHANNEL_TOLERANCES[channel])

        for fc in file_comparisons:
            if channel in fc.channels:
                stats = fc.channels[channel]
                agg_stats.total_compared += stats.total_compared
                agg_stats.exact_matches += stats.exact_matches
                agg_stats.within_tolerance += stats.within_tolerance
                agg_stats.mismatches += stats.mismatches
                agg_stats.differences.extend(stats.differences)

                if stats.python_min < agg_stats.python_min:
                    agg_stats.python_min = stats.python_min
                if stats.python_max > agg_stats.python_max:
                    agg_stats.python_max = stats.python_max
                if stats.native_min < agg_stats.native_min:
                    agg_stats.native_min = stats.native_min
                if stats.native_max > agg_stats.native_max:
                    agg_stats.native_max = stats.native_max

        agg_stats.finalize()
        results.aggregate_channels[channel] = agg_stats

    # Root cause analysis
    results.root_causes = analyze_root_causes(file_comparisons, results.aggregate_channels)
    results.recommendations = generate_recommendations(results.root_causes)

    return results


def analyze_root_causes(comparisons: List[FileComparison],
                        agg_channels: Dict[str, ChannelStats]) -> List[str]:
    """Identify root causes of discrepancies."""
    causes = []

    # Check for timestamp issues
    total_reversals = sum(c.timestamp_analysis.python_time_reversals for c in comparisons)
    if total_reversals > 0:
        causes.append(f"TIMESTAMP_REVERSAL: Python has {total_reversals} time reversals (timestamps going backwards)")

    # Check timestamp interval patterns
    for c in comparisons:
        if c.timestamp_analysis.python_100ms_rate > 99 and c.timestamp_analysis.native_100ms_rate < 99:
            if "TIMESTAMP_ROUNDING" not in str(causes):
                causes.append("TIMESTAMP_ROUNDING: Python rounds to exact 100ms intervals, native has natural GPS drift")
            break

    # Check record count differences
    total_py = sum(c.python_records for c in comparisons)
    total_nat = sum(c.native_records for c in comparisons)
    diff_pct = abs(total_py - total_nat) / max(total_nat, 1) * 100
    if diff_pct > 0.05:
        causes.append(f"RECORD_COUNT_DIFF: Python has {diff_pct:.2f}% {'more' if total_py > total_nat else 'fewer'} records")

    # Check high-frequency channels for interpolation issues
    for channel in ['rpm', 'front_speed_kmh', 'rear_speed_kmh', 'acc_x_g', 'acc_y_g']:
        if channel in agg_channels:
            stats = agg_channels[channel]
            if stats.match_rate() < 85:
                causes.append(f"INTERPOLATION_{channel.upper()}: Low match rate ({stats.match_rate():.1f}%) suggests native interpolation differs")

    # Check for systematic offset
    for channel, stats in agg_channels.items():
        if stats.total_compared > 1000:
            if abs(stats.avg_diff) > stats.tolerance * 0.5:
                causes.append(f"SYSTEMATIC_OFFSET_{channel.upper()}: Average diff {stats.avg_diff:.4f} (tolerance {stats.tolerance})")

    return causes


def generate_recommendations(root_causes: List[str]) -> List[str]:
    """Generate recommendations based on root causes."""
    recs = []

    cause_str = ' '.join(root_causes)

    if 'TIMESTAMP_REVERSAL' in cause_str:
        recs.append("FIX: Correct _create_initial_record() to not produce timestamps before subsequent records")

    if 'TIMESTAMP_ROUNDING' in cause_str:
        recs.append("IMPLEMENT: Use native GPS timestamps with sub-100ms precision instead of rounding")

    if 'RECORD_COUNT_DIFF' in cause_str:
        recs.append("INVESTIGATE: Compare first/last GPS sentences to understand record count differences")

    if 'INTERPOLATION' in cause_str:
        recs.append("IMPLEMENT: Add linear interpolation of CAN values between GPS timestamps (like native)")

    return recs


# =============================================================================
# REPORTING
# =============================================================================

def print_summary(results: TestResults):
    """Print human-readable summary."""
    print("\n" + "=" * 80)
    print("CTRK PARSER COMPARISON TEST RESULTS")
    print("=" * 80)

    print(f"\nFiles: {results.summary['total_files']} total, "
          f"{results.summary['files_with_native']} with native output, "
          f"{results.summary['files_with_errors']} errors")

    print("\n" + "-" * 80)
    print("CHANNEL MATCH RATES (within tolerance)")
    print("-" * 80)
    print(f"{'Channel':<20} {'Match %':>10} {'Exact %':>10} {'Avg Diff':>12} {'Max Diff':>12} {'Compared':>10}")
    print("-" * 80)

    for channel in CHANNELS_TO_COMPARE:
        if channel in results.aggregate_channels:
            s = results.aggregate_channels[channel]
            print(f"{channel:<20} {s.match_rate():>9.2f}% {s.exact_match_rate():>9.2f}% "
                  f"{s.avg_diff:>12.4f} {s.max_diff:>12.4f} {s.total_compared:>10}")

    print("\n" + "-" * 80)
    print("ROOT CAUSES IDENTIFIED")
    print("-" * 80)
    for cause in results.root_causes:
        print(f"  - {cause}")

    print("\n" + "-" * 80)
    print("RECOMMENDATIONS")
    print("-" * 80)
    for rec in results.recommendations:
        print(f"  - {rec}")


def save_results(results: TestResults, output_path: Path):
    """Save results to JSON file."""

    def make_serializable(obj):
        """Convert dataclass to dict, removing large lists."""
        if hasattr(obj, '__dataclass_fields__'):
            d = {}
            for k, v in asdict(obj).items():
                if k == 'differences':
                    continue  # Skip large diff lists
                if k in ('native_intervals', 'python_intervals'):
                    continue  # Skip large interval lists
                d[k] = make_serializable(v)
            return d
        elif isinstance(obj, dict):
            return {k: make_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [make_serializable(i) for i in obj]
        elif isinstance(obj, float):
            if obj == float('inf'):
                return "inf"
            elif obj == float('-inf'):
                return "-inf"
            return round(obj, 4)
        return obj

    data = make_serializable(results)

    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"\nResults saved to: {output_path}")


# =============================================================================
# DETAILED TIMESTAMP ANALYSIS
# =============================================================================

def analyze_first_timestamps(python_csv: Path, native_csv: Path, n: int = 10):
    """Detailed analysis of first N timestamps."""
    print(f"\n{'='*60}")
    print(f"FIRST {n} TIMESTAMPS COMPARISON")
    print(f"{'='*60}")

    py_records = load_csv(python_csv)[:n]
    nat_records = load_csv(native_csv)[:n]

    print(f"\n{'Row':<5} {'Python time_ms':<18} {'Native time_ms':<18} {'Diff':>8}")
    print("-" * 55)

    for i in range(min(n, len(py_records), len(nat_records))):
        py_ts = py_records[i]['time_ms']
        nat_ts = nat_records[i]['time_ms']
        diff = py_ts - nat_ts
        print(f"{i+1:<5} {py_ts:<18} {nat_ts:<18} {diff:>+8}")

    # Interval analysis
    print(f"\n{'Row':<5} {'Py Interval':<15} {'Nat Interval':<15}")
    print("-" * 40)

    for i in range(1, min(n, len(py_records), len(nat_records))):
        py_int = py_records[i]['time_ms'] - py_records[i-1]['time_ms']
        nat_int = nat_records[i]['time_ms'] - nat_records[i-1]['time_ms']
        py_flag = "REVERSAL!" if py_int < 0 else ""
        print(f"{i+1:<5} {py_int:<15} {nat_int:<15} {py_flag}")


# =============================================================================
# MAIN
# =============================================================================

def main():
    if len(sys.argv) < 3:
        print("Usage: python test_parser_comparison.py <input_dir> <output_dir> [--single FILE]")
        print("\nExpects:")
        print("  - output_dir/*_python.csv (Python parser output)")
        print("  - output_dir/*_native.csv (Native library output)")
        sys.exit(1)

    input_dir = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])

    single_file = None
    if len(sys.argv) > 3 and sys.argv[3] == '--single':
        single_file = sys.argv[4] if len(sys.argv) > 4 else None

    if not output_dir.exists():
        print(f"Output directory not found: {output_dir}")
        sys.exit(1)

    # Find file pairs
    python_files = sorted(output_dir.glob('*_python.csv'))

    if single_file:
        python_files = [f for f in python_files if single_file in f.stem]

    if not python_files:
        print("No Python CSV files found")
        sys.exit(1)

    print(f"Found {len(python_files)} Python CSV files")

    # Compare each file
    comparisons = []
    for py_csv in python_files:
        base_name = py_csv.stem.replace('_python', '')
        nat_csv = output_dir / f"{base_name}_native.csv"

        if not nat_csv.exists():
            print(f"  Skipping {base_name}: no native CSV")
            fc = FileComparison(filename=base_name, error="No native CSV found")
            comparisons.append(fc)
            continue

        print(f"  Comparing: {base_name}")
        fc = compare_file(py_csv, nat_csv)
        comparisons.append(fc)

        # Detailed first timestamp analysis for first file
        if len(comparisons) == 1 and fc.timestamp_analysis.python_time_reversals > 0:
            analyze_first_timestamps(py_csv, nat_csv)

    # Aggregate and report
    results = aggregate_results(comparisons)
    print_summary(results)

    # Save detailed results
    results_path = output_dir / 'test_results_detailed.json'
    save_results(results, results_path)

    # Return exit code based on match rate
    overall_match = sum(s.match_rate() for s in results.aggregate_channels.values()) / len(results.aggregate_channels)
    print(f"\nOverall match rate: {overall_match:.2f}%")

    return 0 if overall_match >= 95 else 1


if __name__ == '__main__':
    sys.exit(main())
