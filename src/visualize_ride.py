#!/usr/bin/env python3
"""
Visualize CTRK ride data similar to Y-Trac app.
Creates interactive graphs showing telemetry channels over time.
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.gridspec import GridSpec
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
import sys

# Configure matplotlib for better rendering
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


def load_ride_data(csv_path: Path) -> pd.DataFrame:
    """Load ride data from CSV."""
    df = pd.read_csv(csv_path)

    # Convert timestamp to datetime for better plotting
    # time_ms is unix timestamp in milliseconds
    df['datetime'] = pd.to_datetime(df['time_ms'], unit='ms')

    # Calculate relative time from start (in seconds)
    start_time = df['time_ms'].iloc[0]
    df['time_s'] = (df['time_ms'] - start_time) / 1000.0

    return df


def create_ytrac_style_graph(df: pd.DataFrame, output_path: Path, lap: int = None):
    """
    Create a Y-Trac style graph with multiple channels.

    Similar to Y-Trac viewer showing:
    - Timeline with track position
    - Multiple telemetry channels stacked
    - Color-coded lines for each channel
    """

    # Filter by lap if specified
    if lap is not None:
        df = df[df['lap'] == lap].copy()
        title_suffix = f" - Lap {lap}"
    else:
        title_suffix = " - All Laps"

    # Create figure with GridSpec for Y-Trac-like layout
    fig = plt.figure(figsize=(16, 12))
    gs = GridSpec(6, 1, height_ratios=[1, 1, 1, 1, 1, 1], hspace=0.1)

    # Define channels to plot with their colors and units
    channels = [
        {'col': 'rpm', 'label': 'E/G-RPM', 'unit': 'r/min', 'color': '#ff6b6b', 'scale': 1},
        {'col': 'rear_speed_kmh', 'label': 'R-Speed', 'unit': 'km/h', 'color': '#4ecdc4', 'scale': 1},
        {'col': 'throttle', 'label': 'Throttle', 'unit': '%', 'color': '#ffe66d', 'scale': 1},
        {'col': 'lean_deg', 'label': 'Lean', 'unit': '°', 'color': '#ff9ff3', 'scale': 1},
        {'col': 'acc_x_g', 'label': 'Acc-X', 'unit': 'g', 'color': '#54a0ff', 'scale': 1},
        {'col': 'front_brake_bar', 'label': 'F-Brake', 'unit': 'bar', 'color': '#ff6348', 'scale': 1},
    ]

    axes = []
    time_data = df['time_s']

    for i, ch in enumerate(channels):
        ax = fig.add_subplot(gs[i])
        axes.append(ax)

        # Plot the channel data
        data = df[ch['col']] * ch['scale']
        ax.plot(time_data, data, color=ch['color'], linewidth=0.8, alpha=0.9)
        ax.fill_between(time_data, data, alpha=0.2, color=ch['color'])

        # Configure axis
        ax.set_ylabel(f"{ch['label']}\n({ch['unit']})", fontsize=9, rotation=0, ha='right', va='center')
        ax.yaxis.set_label_coords(-0.08, 0.5)

        # Grid
        ax.grid(True, alpha=0.3)
        ax.set_xlim(time_data.iloc[0], time_data.iloc[-1])

        # Add current value annotation at the end
        last_val = data.iloc[-1]
        ax.annotate(f'{last_val:.1f}', xy=(time_data.iloc[-1], last_val),
                    xytext=(5, 0), textcoords='offset points',
                    fontsize=8, color=ch['color'])

        # Hide x-axis labels except for bottom plot
        if i < len(channels) - 1:
            ax.set_xticklabels([])
        else:
            ax.set_xlabel('Time (s)', fontsize=10)

    # Title
    fig.suptitle(f"Ride Telemetry{title_suffix}", fontsize=14, y=0.98)

    # Save
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()
    print(f"Saved: {output_path}")


def create_map_view(df: pd.DataFrame, output_path: Path, lap: int = None):
    """Create a track map view colored by speed."""

    if lap is not None:
        df = df[df['lap'] == lap].copy()
        title_suffix = f" - Lap {lap}"
    else:
        title_suffix = " - All Laps"

    fig, ax = plt.subplots(figsize=(10, 10))

    # Plot track colored by speed
    scatter = ax.scatter(df['longitude'], df['latitude'],
                        c=df['rear_speed_kmh'], cmap='plasma',
                        s=2, alpha=0.6)

    # Colorbar
    cbar = plt.colorbar(scatter, ax=ax, label='Speed (km/h)')

    # Mark start/finish
    ax.scatter(df['longitude'].iloc[0], df['latitude'].iloc[0],
              color='green', s=100, marker='o', label='Start', zorder=5)
    ax.scatter(df['longitude'].iloc[-1], df['latitude'].iloc[-1],
              color='red', s=100, marker='s', label='Finish', zorder=5)

    ax.set_xlabel('Longitude')
    ax.set_ylabel('Latitude')
    ax.set_title(f"Track Map{title_suffix}")
    ax.legend()
    ax.set_aspect('equal')
    ax.grid(True, alpha=0.3)

    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()
    print(f"Saved: {output_path}")


def create_lap_comparison(df: pd.DataFrame, output_path: Path):
    """Create lap time comparison chart."""

    # Calculate lap times
    lap_times = []
    for lap_num in df['lap'].unique():
        lap_data = df[df['lap'] == lap_num]
        duration = (lap_data['time_ms'].iloc[-1] - lap_data['time_ms'].iloc[0]) / 1000.0
        lap_times.append({'lap': lap_num, 'time_s': duration})

    lap_df = pd.DataFrame(lap_times)

    fig, ax = plt.subplots(figsize=(12, 6))

    # Color bars by performance (fastest = green, slowest = red)
    sorted_indices = lap_df['time_s'].argsort().values
    bar_colors = ['#2ecc71' if i == sorted_indices[0] else
                  '#e74c3c' if i == sorted_indices[-1] else '#3498db'
                  for i in range(len(lap_df))]

    bars = ax.bar(lap_df['lap'], lap_df['time_s'], color=bar_colors, edgecolor='white', linewidth=0.5)

    # Add time labels on bars
    for bar, time in zip(bars, lap_df['time_s']):
        minutes = int(time // 60)
        seconds = time % 60
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2,
               f'{minutes}:{seconds:05.2f}', ha='center', va='bottom', fontsize=9)

    ax.set_xlabel('Lap')
    ax.set_ylabel('Time (seconds)')
    ax.set_title('Lap Times Comparison')
    ax.grid(True, alpha=0.3, axis='y')

    # Highlight best lap
    best_lap = lap_df.loc[lap_df['time_s'].idxmin()]
    ax.axhline(y=best_lap['time_s'], color='#2ecc71', linestyle='--', alpha=0.5, label=f"Best: Lap {int(best_lap['lap'])}")
    ax.legend()

    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()
    print(f"Saved: {output_path}")


def create_channel_histogram(df: pd.DataFrame, output_path: Path):
    """Create histogram distribution of key channels."""

    fig, axes = plt.subplots(2, 3, figsize=(14, 8))
    axes = axes.flatten()

    channels = [
        ('rpm', 'RPM Distribution', 'r/min', '#ff6b6b'),
        ('rear_speed_kmh', 'Speed Distribution', 'km/h', '#4ecdc4'),
        ('lean_deg', 'Lean Angle Distribution', '°', '#ff9ff3'),
        ('throttle', 'Throttle Distribution', '%', '#ffe66d'),
        ('acc_x_g', 'Longitudinal Accel', 'g', '#54a0ff'),
        ('acc_y_g', 'Lateral Accel', 'g', '#ff6348'),
    ]

    for ax, (col, title, unit, color) in zip(axes, channels):
        data = df[col].dropna()
        ax.hist(data, bins=50, color=color, alpha=0.7, edgecolor='white', linewidth=0.3)
        ax.set_title(title, fontsize=10)
        ax.set_xlabel(unit)
        ax.set_ylabel('Count')
        ax.grid(True, alpha=0.3)

        # Add statistics
        mean_val = data.mean()
        max_val = data.max()
        ax.axvline(mean_val, color='white', linestyle='--', alpha=0.7, label=f'Mean: {mean_val:.1f}')
        ax.legend(fontsize=8)

    fig.suptitle('Channel Distributions', fontsize=14, y=1.02)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()
    print(f"Saved: {output_path}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python visualize_ride.py <csv_file> [output_dir]")
        print("\nExample:")
        print("  python visualize_ride.py artifacts/minimal-android-app-2026-01-25T21:44:32/exports/20250729-170818_native.csv")
        sys.exit(1)

    csv_path = Path(sys.argv[1])
    if not csv_path.exists():
        print(f"Error: File not found: {csv_path}")
        sys.exit(1)

    # Output directory
    if len(sys.argv) > 2:
        output_dir = Path(sys.argv[2])
    else:
        output_dir = csv_path.parent / "graphs"

    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading data from: {csv_path}")
    df = load_ride_data(csv_path)
    print(f"Loaded {len(df)} data points, {df['lap'].nunique()} laps")

    # Generate all visualizations
    print("\nGenerating visualizations...")

    # Full ride telemetry
    create_ytrac_style_graph(df, output_dir / "telemetry_full.png")

    # Best lap (lap 4 based on earlier analysis)
    create_ytrac_style_graph(df, output_dir / "telemetry_lap4.png", lap=4)

    # Track map
    create_map_view(df, output_dir / "track_map.png")
    create_map_view(df, output_dir / "track_map_lap4.png", lap=4)

    # Lap comparison
    create_lap_comparison(df, output_dir / "lap_comparison.png")

    # Channel distributions
    create_channel_histogram(df, output_dir / "channel_distributions.png")

    print(f"\nAll visualizations saved to: {output_dir}")


if __name__ == '__main__':
    main()
