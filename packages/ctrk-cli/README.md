# @tex0l/ctrk-cli

Command-line interface for parsing Yamaha Y-Trac CTRK telemetry files to CSV.

## Installation

```bash
npm install -g @tex0l/ctrk-cli
```

## Usage

### Parse Command

Converts CTRK files to calibrated CSV format.

```bash
ctrk-parser parse <file.CTRK>... [options]
```

**Options:**
- `-o, --output <dir>` -- Output directory (default: `output/<timestamp>/`)
- `--raw` -- Also export raw uncalibrated values

**Examples:**

```bash
# Parse a single file
ctrk-parser parse session.CTRK

# Parse multiple files
ctrk-parser parse *.CTRK

# Export to custom directory with raw values
ctrk-parser parse session.CTRK -o my_data/ --raw
```

### Output

Each run creates CSV files in the output directory:

```
output/2026-02-12_14-30-00/
  session_parsed.csv         # Calibrated values (26 columns)
  session_parsed.raw.csv     # Raw sensor values (optional, with --raw)
```

### CSV Columns (Calibrated)

| Column | Unit |
|--------|------|
| lap | -- |
| time_ms | ms (Unix) |
| latitude, longitude | degrees |
| gps_speed_kmh | km/h |
| rpm | RPM |
| throttle_grip, throttle | % |
| water_temp, intake_temp | C |
| front_speed_kmh, rear_speed_kmh | km/h |
| fuel_cc | cc |
| lean_deg, lean_signed_deg | degrees |
| pitch_deg_s | degrees/s |
| acc_x_g, acc_y_g | G |
| front_brake_bar, rear_brake_bar | bar |
| gear | 0-6 |
| f_abs, r_abs, tcs, scs, lif, launch | bool |

## License

MIT
