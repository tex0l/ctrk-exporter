#!/usr/bin/env python3
"""
Generate comparison visualizations between native library output and parser v6.
Creates:
1. Individual graphs for v6 parser (same style as native)
2. Overlay graphs showing both native and v6 superimposed
"""

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
import numpy as np
from pathlib import Path
import sys
from datetime import datetime

# Dark theme styling
plt.style.use('dark_background')
plt.rcParams['figure.facecolor'] = '#1a1a2e'
plt.rcParams['axes.facecolor'] = '#1a1a2e'
plt.rcParams['axes.edgecolor'] = '#404060'
plt.rcParams['axes.labelcolor'] = 'white'
plt.rcParams['xtick.color'] = 'white'
plt.rcParams['ytick.color'] = 'white'
plt.rcParams['grid.color'] = '#404060'
plt.rcParams['text.color'] = 'white'
plt.rcParams['legend.facecolor'] = '#2a2a4e'


def load_data(csv_path: Path) -> pd.DataFrame:
    """Load and prepare CSV data."""
    df = pd.read_csv(csv_path)
    start_time = df['time_ms'].iloc[0]
    df['time_s'] = (df['time_ms'] - start_time) / 1000.0
    # Convert boolean columns
    for col in ['f_abs', 'r_abs']:
        if col in df.columns:
            df[col] = df[col].map({'true': 1, 'false': 0, True: 1, False: 0}).fillna(0).astype(int)
    return df


def create_ytrac_style_graph(df: pd.DataFrame, output_path: Path, title_prefix: str = ""):
    """Create Y-Trac style graph for a single dataset."""

    fig = plt.figure(figsize=(16, 12))
    gs = GridSpec(6, 1, height_ratios=[1, 1, 1, 1, 1, 1], hspace=0.1)

    channels = [
        {'col': 'rpm', 'label': 'E/G-RPM', 'unit': 'r/min', 'color': '#ff6b6b'},
        {'col': 'rear_speed_kmh', 'label': 'R-Speed', 'unit': 'km/h', 'color': '#4ecdc4'},
        {'col': 'throttle', 'label': 'Throttle', 'unit': '%', 'color': '#ffe66d'},
        {'col': 'lean_deg', 'label': 'Lean', 'unit': 'deg', 'color': '#ff9ff3'},
        {'col': 'acc_x_g', 'label': 'Acc-X', 'unit': 'g', 'color': '#54a0ff'},
        {'col': 'front_brake_bar', 'label': 'F-Brake', 'unit': 'bar', 'color': '#ff6348'},
    ]

    time_data = df['time_s']

    for i, ch in enumerate(channels):
        ax = fig.add_subplot(gs[i])
        data = df[ch['col']]
        ax.plot(time_data, data, color=ch['color'], linewidth=0.8, alpha=0.9)
        ax.fill_between(time_data, data, alpha=0.2, color=ch['color'])

        ax.set_ylabel(f"{ch['label']}\n({ch['unit']})", fontsize=9, rotation=0, ha='right', va='center')
        ax.yaxis.set_label_coords(-0.08, 0.5)
        ax.grid(True, alpha=0.3)
        ax.set_xlim(time_data.iloc[0], time_data.iloc[-1])

        if i < len(channels) - 1:
            ax.set_xticklabels([])
        else:
            ax.set_xlabel('Time (s)', fontsize=10)

    fig.suptitle(f"{title_prefix} Telemetry - Full Session", fontsize=14, y=0.98)
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()
    print(f"Saved: {output_path}")


def create_overlay_comparison(df_native: pd.DataFrame, df_v6: pd.DataFrame, output_path: Path):
    """Create overlay comparison graph with native and v6 superimposed."""

    fig = plt.figure(figsize=(18, 14))
    gs = GridSpec(6, 1, height_ratios=[1, 1, 1, 1, 1, 1], hspace=0.1)

    channels = [
        {'col': 'rpm', 'label': 'E/G-RPM', 'unit': 'r/min'},
        {'col': 'rear_speed_kmh', 'label': 'R-Speed', 'unit': 'km/h'},
        {'col': 'throttle', 'label': 'Throttle', 'unit': '%'},
        {'col': 'lean_deg', 'label': 'Lean', 'unit': 'deg'},
        {'col': 'acc_x_g', 'label': 'Acc-X', 'unit': 'g'},
        {'col': 'front_brake_bar', 'label': 'F-Brake', 'unit': 'bar'},
    ]

    time_native = df_native['time_s']
    time_v6 = df_v6['time_s']

    for i, ch in enumerate(channels):
        ax = fig.add_subplot(gs[i])

        data_native = df_native[ch['col']]
        data_v6 = df_v6[ch['col']]

        # Plot native (solid line)
        ax.plot(time_native, data_native, color='#4ecdc4', linewidth=1.0, alpha=0.8, label='Native')
        # Plot v6 (dashed line)
        ax.plot(time_v6, data_v6, color='#ff6b6b', linewidth=1.0, alpha=0.8, linestyle='--', label='Parser v6')

        ax.set_ylabel(f"{ch['label']}\n({ch['unit']})", fontsize=9, rotation=0, ha='right', va='center')
        ax.yaxis.set_label_coords(-0.08, 0.5)
        ax.grid(True, alpha=0.3)

        # Use common x range
        x_min = min(time_native.iloc[0], time_v6.iloc[0])
        x_max = max(time_native.iloc[-1], time_v6.iloc[-1])
        ax.set_xlim(x_min, x_max)

        if i == 0:
            ax.legend(loc='upper right', fontsize=8)

        if i < len(channels) - 1:
            ax.set_xticklabels([])
        else:
            ax.set_xlabel('Time (s)', fontsize=10)

    fig.suptitle("Comparison: Native vs Parser v6 - Full Session", fontsize=14, y=0.98)
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()
    print(f"Saved: {output_path}")


def create_overlay_all_channels(df_native: pd.DataFrame, df_v6: pd.DataFrame, output_path: Path):
    """Create overlay comparison for ALL channels."""

    channel_groups = {
        'Engine': [
            {'col': 'rpm', 'label': 'RPM', 'unit': 'r/min'},
            {'col': 'throttle_grip', 'label': 'Throttle Grip', 'unit': '%'},
            {'col': 'throttle', 'label': 'Throttle', 'unit': '%'},
            {'col': 'gear', 'label': 'Gear', 'unit': ''},
        ],
        'Speed': [
            {'col': 'rear_speed_kmh', 'label': 'R-Speed', 'unit': 'km/h'},
            {'col': 'front_speed_kmh', 'label': 'F-Speed', 'unit': 'km/h'},
            {'col': 'gps_speed_kmh', 'label': 'GPS Speed', 'unit': 'km/h'},
        ],
        'Chassis': [
            {'col': 'lean_deg', 'label': 'Lean', 'unit': 'deg'},
            {'col': 'pitch_deg_s', 'label': 'Pitch', 'unit': 'deg/s'},
        ],
        'Acceleration': [
            {'col': 'acc_x_g', 'label': 'Acc-X', 'unit': 'g'},
            {'col': 'acc_y_g', 'label': 'Acc-Y', 'unit': 'g'},
        ],
        'Brakes': [
            {'col': 'front_brake_bar', 'label': 'F-Brake', 'unit': 'bar'},
            {'col': 'rear_brake_bar', 'label': 'R-Brake', 'unit': 'bar'},
        ],
        'Temperature': [
            {'col': 'water_temp', 'label': 'Water Temp', 'unit': 'C'},
            {'col': 'intake_temp', 'label': 'Intake Temp', 'unit': 'C'},
        ],
        'Fuel': [
            {'col': 'fuel_cc', 'label': 'Fuel', 'unit': 'cc'},
        ],
    }

    total_channels = sum(len(channels) for channels in channel_groups.values())

    fig = plt.figure(figsize=(20, total_channels * 1.5))
    gs = GridSpec(total_channels, 1, hspace=0.05)

    time_native = df_native['time_s']
    time_v6 = df_v6['time_s']
    row_idx = 0

    for group_name, channels in channel_groups.items():
        for ch in channels:
            ax = fig.add_subplot(gs[row_idx])

            data_native = df_native[ch['col']]
            data_v6 = df_v6[ch['col']]

            # Plot both
            ax.plot(time_native, data_native, color='#4ecdc4', linewidth=0.8, alpha=0.9, label='Native')
            ax.plot(time_v6, data_v6, color='#ff6b6b', linewidth=0.8, alpha=0.7, linestyle='--', label='v6')

            unit_str = f" ({ch['unit']})" if ch['unit'] else ""
            ax.set_ylabel(f"{ch['label']}{unit_str}", fontsize=8, rotation=0, ha='right', va='center')
            ax.yaxis.set_label_coords(-0.06, 0.5)

            # Calculate error stats
            # Match by time (approximate)
            min_len = min(len(data_native), len(data_v6))
            if min_len > 0:
                diff = np.abs(data_native.iloc[:min_len].values - data_v6.iloc[:min_len].values)
                max_diff = np.max(diff)
                mean_diff = np.mean(diff)
                ax.text(1.01, 0.7, f'maxErr:{max_diff:.2f}', transform=ax.transAxes, fontsize=6, color='#ff6b6b')
                ax.text(1.01, 0.3, f'avgErr:{mean_diff:.2f}', transform=ax.transAxes, fontsize=6, color='#888')

            ax.grid(True, alpha=0.2)
            x_min = min(time_native.iloc[0], time_v6.iloc[0])
            x_max = max(time_native.iloc[-1], time_v6.iloc[-1])
            ax.set_xlim(x_min, x_max)

            if row_idx == 0:
                ax.legend(loc='upper right', fontsize=7)

            if row_idx < total_channels - 1:
                ax.set_xticklabels([])
            else:
                ax.set_xlabel('Time (s)', fontsize=10)

            ax.tick_params(axis='y', labelsize=7)
            ax.tick_params(axis='x', labelsize=8)

            row_idx += 1

    fig.suptitle("All Channels Comparison: Native (cyan) vs Parser v6 (red dashed)", fontsize=14, y=0.995)
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()
    print(f"Saved: {output_path}")


def create_difference_graph(df_native: pd.DataFrame, df_v6: pd.DataFrame, output_path: Path):
    """Create a graph showing the difference (error) between native and v6."""

    fig = plt.figure(figsize=(18, 14))
    gs = GridSpec(6, 1, height_ratios=[1, 1, 1, 1, 1, 1], hspace=0.1)

    channels = [
        {'col': 'rpm', 'label': 'RPM Error', 'unit': 'r/min'},
        {'col': 'rear_speed_kmh', 'label': 'R-Speed Error', 'unit': 'km/h'},
        {'col': 'throttle', 'label': 'Throttle Error', 'unit': '%'},
        {'col': 'lean_deg', 'label': 'Lean Error', 'unit': 'deg'},
        {'col': 'acc_x_g', 'label': 'Acc-X Error', 'unit': 'g'},
        {'col': 'front_brake_bar', 'label': 'F-Brake Error', 'unit': 'bar'},
    ]

    # Match data by index (same length assumption for visualization)
    min_len = min(len(df_native), len(df_v6))
    time_data = df_native['time_s'].iloc[:min_len]

    for i, ch in enumerate(channels):
        ax = fig.add_subplot(gs[i])

        data_native = df_native[ch['col']].iloc[:min_len].values
        data_v6 = df_v6[ch['col']].iloc[:min_len].values
        diff = data_native - data_v6

        # Plot difference
        ax.plot(time_data, diff, color='#ff6b6b', linewidth=0.8, alpha=0.9)
        ax.fill_between(time_data, diff, alpha=0.2, color='#ff6b6b')
        ax.axhline(y=0, color='#4ecdc4', linestyle='-', linewidth=0.5, alpha=0.5)

        ax.set_ylabel(f"{ch['label']}\n({ch['unit']})", fontsize=9, rotation=0, ha='right', va='center')
        ax.yaxis.set_label_coords(-0.08, 0.5)
        ax.grid(True, alpha=0.3)
        ax.set_xlim(time_data.iloc[0], time_data.iloc[-1])

        # Add stats
        max_err = np.max(np.abs(diff))
        mean_err = np.mean(np.abs(diff))
        ax.text(0.99, 0.95, f'Max: {max_err:.2f} | Mean: {mean_err:.2f}',
                transform=ax.transAxes, fontsize=8, ha='right', va='top', color='#888')

        if i < len(channels) - 1:
            ax.set_xticklabels([])
        else:
            ax.set_xlabel('Time (s)', fontsize=10)

    fig.suptitle("Error: Native - Parser v6 (positive = native higher)", fontsize=14, y=0.98)
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()
    print(f"Saved: {output_path}")


def create_zoomed_comparison(df_native: pd.DataFrame, df_v6: pd.DataFrame, output_path: Path,
                             start_s: float, end_s: float, title: str = ""):
    """Create zoomed overlay comparison for a specific time range."""

    # Filter to time range
    df_n = df_native[(df_native['time_s'] >= start_s) & (df_native['time_s'] <= end_s)].copy()
    df_p = df_v6[(df_v6['time_s'] >= start_s) & (df_v6['time_s'] <= end_s)].copy()

    if len(df_n) == 0 or len(df_p) == 0:
        print(f"Warning: No data in range {start_s}-{end_s}s")
        return

    fig = plt.figure(figsize=(16, 10))
    gs = GridSpec(4, 1, height_ratios=[1, 1, 1, 1], hspace=0.1)

    channels = [
        {'col': 'rpm', 'label': 'RPM', 'unit': 'r/min'},
        {'col': 'throttle', 'label': 'Throttle', 'unit': '%'},
        {'col': 'lean_deg', 'label': 'Lean', 'unit': 'deg'},
        {'col': 'rear_speed_kmh', 'label': 'R-Speed', 'unit': 'km/h'},
    ]

    for i, ch in enumerate(channels):
        ax = fig.add_subplot(gs[i])

        ax.plot(df_n['time_s'], df_n[ch['col']], color='#4ecdc4', linewidth=1.5, alpha=0.9, label='Native', marker='o', markersize=2)
        ax.plot(df_p['time_s'], df_p[ch['col']], color='#ff6b6b', linewidth=1.5, alpha=0.8, linestyle='--', label='v6', marker='x', markersize=2)

        ax.set_ylabel(f"{ch['label']} ({ch['unit']})", fontsize=10)
        ax.grid(True, alpha=0.3)
        ax.set_xlim(start_s, end_s)

        if i == 0:
            ax.legend(loc='upper right', fontsize=9)

        if i < len(channels) - 1:
            ax.set_xticklabels([])
        else:
            ax.set_xlabel('Time (s)', fontsize=10)

    title_str = title if title else f"Zoomed Comparison: {start_s:.1f}s - {end_s:.1f}s"
    fig.suptitle(title_str, fontsize=14, y=0.98)
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()
    print(f"Saved: {output_path}")


def main():
    # Paths
    base_dir = Path(__file__).parent.parent
    native_csv = base_dir / "artifacts/minimal-android-app-2026-01-25T21:44:32/exports/20250729-170818_native.csv"
    v6_csv = base_dir / "artifacts/parsed-2026-01-26T16:12:25/exports/20250729-170818_v6.csv"

    # Create output directories
    v6_graphs_dir = base_dir / "artifacts/parsed-2026-01-26T16:12:25/exports/graphs"
    compare_dir = base_dir / "artifacts/compare-native-v6"
    v6_graphs_dir.mkdir(parents=True, exist_ok=True)
    compare_dir.mkdir(parents=True, exist_ok=True)

    print("Loading data...")
    df_native = load_data(native_csv)
    df_v6 = load_data(v6_csv)
    print(f"Native: {len(df_native)} points, v6: {len(df_v6)} points")

    # 1. Generate v6 parser graphs (same style as native)
    print("\n=== Generating v6 Parser Graphs ===")
    create_ytrac_style_graph(df_v6, v6_graphs_dir / "telemetry_full.png", title_prefix="Parser v6")

    # 2. Generate overlay comparison graphs
    print("\n=== Generating Overlay Comparison Graphs ===")
    create_overlay_comparison(df_native, df_v6, compare_dir / "overlay_main_channels.png")
    create_overlay_all_channels(df_native, df_v6, compare_dir / "overlay_all_channels.png")
    create_difference_graph(df_native, df_v6, compare_dir / "difference_graph.png")

    # 3. Generate zoomed comparisons at interesting points
    print("\n=== Generating Zoomed Comparisons ===")
    # First 30 seconds (warmup)
    create_zoomed_comparison(df_native, df_v6, compare_dir / "zoom_0_30s.png", 0, 30, "First 30 seconds")
    # Mid-session sample
    mid_time = df_native['time_s'].median()
    create_zoomed_comparison(df_native, df_v6, compare_dir / f"zoom_{int(mid_time-15)}_{int(mid_time+15)}s.png",
                            mid_time - 15, mid_time + 15, f"Mid-session ({int(mid_time-15)}-{int(mid_time+15)}s)")
    # High action section (around 100-130s typically has good data)
    create_zoomed_comparison(df_native, df_v6, compare_dir / "zoom_100_130s.png", 100, 130, "Action segment (100-130s)")

    print(f"\n=== Done! ===")
    print(f"v6 graphs saved to: {v6_graphs_dir}")
    print(f"Comparison graphs saved to: {compare_dir}")


if __name__ == '__main__':
    main()
