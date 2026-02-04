#!/usr/bin/env python3
"""
Generate a comprehensive graph showing ALL telemetry channels.
"""

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from pathlib import Path
import sys

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


def load_data(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    start_time = df['time_ms'].iloc[0]
    df['time_s'] = (df['time_ms'] - start_time) / 1000.0
    # Convert boolean columns (true/false strings) to numeric
    for col in ['f_abs', 'r_abs', 'tcs', 'scs', 'lif', 'launch']:
        if col in df.columns:
            df[col] = df[col].map({'true': 1, 'false': 0, True: 1, False: 0, 1: 1, 0: 0}).fillna(0).astype(int)
    return df


def create_all_channels_graph(df: pd.DataFrame, output_path: Path, lap: int = None):
    """Create a graph showing ALL channels organized by category."""

    if lap is not None:
        df = df[df['lap'] == lap].copy()
        title = f"All Telemetry Channels - Lap {lap}"
    else:
        title = "All Telemetry Channels - Full Session"

    # Define all channels grouped by category
    channel_groups = {
        'Engine': [
            {'col': 'rpm', 'label': 'RPM', 'unit': 'r/min', 'color': '#ff6b6b'},
            {'col': 'throttle_grip', 'label': 'Throttle Grip', 'unit': '%', 'color': '#ffa502'},
            {'col': 'throttle', 'label': 'Throttle', 'unit': '%', 'color': '#ffe66d'},
            {'col': 'gear', 'label': 'Gear', 'unit': '', 'color': '#ff4757'},
        ],
        'Speed': [
            {'col': 'rear_speed_kmh', 'label': 'R-Speed', 'unit': 'km/h', 'color': '#4ecdc4'},
            {'col': 'front_speed_kmh', 'label': 'F-Speed', 'unit': 'km/h', 'color': '#00d2d3'},
            {'col': 'gps_speed_kmh', 'label': 'GPS Speed', 'unit': 'km/h', 'color': '#1dd1a1'},
        ],
        'Chassis': [
            {'col': 'lean_deg', 'label': 'Lean', 'unit': '°', 'color': '#ff9ff3'},
            {'col': 'pitch_deg_s', 'label': 'Pitch', 'unit': '°/s', 'color': '#f368e0'},
        ],
        'Acceleration': [
            {'col': 'acc_x_g', 'label': 'Acc-X (Longitudinal)', 'unit': 'g', 'color': '#54a0ff'},
            {'col': 'acc_y_g', 'label': 'Acc-Y (Lateral)', 'unit': 'g', 'color': '#5f27cd'},
        ],
        'Brakes': [
            {'col': 'front_brake_bar', 'label': 'F-Brake', 'unit': 'bar', 'color': '#ff6348'},
            {'col': 'rear_brake_bar', 'label': 'R-Brake', 'unit': 'bar', 'color': '#ee5a24'},
        ],
        'Temperature': [
            {'col': 'water_temp', 'label': 'Water Temp', 'unit': '°C', 'color': '#3498db'},
            {'col': 'intake_temp', 'label': 'Intake Temp', 'unit': '°C', 'color': '#0abde3'},
        ],
        'Fuel': [
            {'col': 'fuel_cc', 'label': 'Fuel', 'unit': 'cc', 'color': '#2ecc71'},
        ],
        'Control Systems': [
            {'col': 'f_abs', 'label': 'F-ABS', 'unit': '', 'color': '#e74c3c'},
            {'col': 'r_abs', 'label': 'R-ABS', 'unit': '', 'color': '#c0392b'},
            {'col': 'tcs', 'label': 'TCS', 'unit': '', 'color': '#9b59b6'},
            {'col': 'scs', 'label': 'SCS', 'unit': '', 'color': '#8e44ad'},
            {'col': 'lif', 'label': 'LIF', 'unit': '', 'color': '#3498db'},
            {'col': 'launch', 'label': 'Launch', 'unit': '', 'color': '#2980b9'},
        ],
    }

    # Count total channels
    total_channels = sum(len(channels) for channels in channel_groups.values())

    # Create figure with subplots for each channel
    fig = plt.figure(figsize=(20, total_channels * 1.2))
    gs = GridSpec(total_channels, 1, hspace=0.05)

    time_data = df['time_s']
    row_idx = 0

    for group_name, channels in channel_groups.items():
        for ch in channels:
            ax = fig.add_subplot(gs[row_idx])

            # Get data
            data = df[ch['col']]

            # Plot
            ax.plot(time_data, data, color=ch['color'], linewidth=0.6, alpha=0.9)
            ax.fill_between(time_data, data, alpha=0.15, color=ch['color'])

            # Label on the left (horizontal only)
            unit_str = f" ({ch['unit']})" if ch['unit'] else ""
            ax.set_ylabel(f"{ch['label']}{unit_str}", fontsize=8, rotation=0, ha='right', va='center')
            ax.yaxis.set_label_coords(-0.06, 0.5)

            # Stats annotation
            max_val = data.max()
            min_val = data.min()
            ax.text(1.01, 0.7, f'max:{max_val:.1f}', transform=ax.transAxes, fontsize=6, color='#888')
            ax.text(1.01, 0.3, f'min:{min_val:.1f}', transform=ax.transAxes, fontsize=6, color='#888')

            # Grid and limits
            ax.grid(True, alpha=0.2)
            ax.set_xlim(time_data.iloc[0], time_data.iloc[-1])

            # Hide x labels except for last
            if row_idx < total_channels - 1:
                ax.set_xticklabels([])
            else:
                ax.set_xlabel('Time (s)', fontsize=10)

            # Reduce y tick labels
            ax.tick_params(axis='y', labelsize=7)
            ax.tick_params(axis='x', labelsize=8)

            row_idx += 1

    fig.suptitle(title, fontsize=14, y=0.995)

    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()
    print(f"Saved: {output_path}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python visualize_all_channels.py <csv_file> [lap_number|all]")
        print("  lap_number: generate graph for specific lap")
        print("  all: generate one graph per lap")
        sys.exit(1)

    csv_path = Path(sys.argv[1])
    mode = sys.argv[2] if len(sys.argv) > 2 else "all"

    df = load_data(csv_path)
    laps = sorted(df['lap'].unique())
    print(f"Loaded {len(df)} points, {len(laps)} laps")

    output_dir = csv_path.parent / "graphs"
    output_dir.mkdir(exist_ok=True)

    if mode == "all":
        # Generate one file per lap
        for lap in laps:
            output_path = output_dir / f"all_channels_lap{lap}.png"
            create_all_channels_graph(df, output_path, lap=lap)
        print(f"\nGenerated {len(laps)} files in {output_dir}")
    else:
        # Single lap
        lap = int(mode)
        output_path = output_dir / f"all_channels_lap{lap}.png"
        create_all_channels_graph(df, output_path, lap=lap)


if __name__ == '__main__':
    main()
