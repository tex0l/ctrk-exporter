# TypeScript Parser Validation Test Data

This directory contains test data for validating the TypeScript parser against the Python parser (ground truth).

## Directory Structure

```
test-data/
├── *.CTRK                  # 15 representative CTRK files (symlinks to ../../input/)
├── python-output/          # Python parser CSV outputs (ground truth)
│   └── *_parsed.csv       # Calibrated output from Python parser
└── README.md              # This file
```

## Test File Selection

The 15 test files were selected to provide comprehensive coverage:

| File | Size | Records | Laps | Track | Notes |
|------|------|---------|------|-------|-------|
| 20250829-192509.CTRK | 30 KB | 102 | 1 | Croix-en-Ternois | Tiny file |
| 20250905-101210.CTRK | 43 KB | 129 | 1 | Magny-Cours | Small file |
| 20250829-201501.CTRK | 42 KB | 138 | 1 | Croix-en-Ternois | Small file |
| 20250905-134407.CTRK | 415 KB | 1,247 | 1 | Magny-Cours | Medium file |
| 20000101-010216.CTRK | 451 KB | 1,409 | 1 | Croix-en-Ternois | Medium file |
| 20250826-115827.CTRK | 2.4 MB | 7,081 | 5 | Croix-en-Ternois | Large file |
| 20250906-091428.CTRK | 2.6 MB | 7,428 | 8 | Magny-Cours | Large file |
| 20250729-155522.CTRK | 2.9 MB | 8,306 | 4 | Le Mans Bugatti | Large file |
| 20251005-152124.CTRK | 4.1 MB | 11,930 | 7 | Croix-en-Ternois | Large file |
| 20251017-112812.CTRK | 4.5 MB | 13,045 | 13 | Carole | Very large, many laps |
| 20250729-144412.CTRK | 4.7 MB | 13,679 | 9 | Le Mans Bugatti | Very large |
| 20250826-154710.CTRK | 5.0 MB | 14,447 | 8 | Croix-en-Ternois | Very large |
| 20250729-170818.CTRK | 5.7 MB | 16,454 | 9 | Le Mans Bugatti | Very large |
| 20250906-151214.CTRK | 8.4 MB | 24,494 | 14 | Magny-Cours | Largest file |

**Total:** 15 files, 123,476 records, 68 laps across 4 tracks

## Track Identification (via GPS Finish Line)

| Track | Finish Line P1 | Finish Line P2 |
|-------|----------------|----------------|
| Croix-en-Ternois | 49.107705, 3.507921 | 49.107669, 3.508262 |
| Le Mans Bugatti | 47.949887, 0.207159 | 47.949876, 0.207953 |
| Magny-Cours | 47.364923, 4.899690 | 47.364758, 4.899942 |
| Carole | 48.978741, 2.522624 | 48.978765, 2.522969 |

## Validation Methodology

The validation suite compares TypeScript parser output against Python parser output:

1. **Parse CTRK files** — TypeScript parser processes each file
2. **Load Python CSV** — Ground truth from Python parser
3. **Apply calibration** — Convert TypeScript raw values to engineering units
4. **Align records** — Compare by index (1:1 alignment expected)
5. **Channel-by-channel comparison** — Apply tolerances per channel
6. **Generate report** — JSON report with statistics

### Comparison Tolerances

| Channel | Tolerance | Rationale |
|---------|-----------|-----------|
| rpm | ±2 RPM | Integer rounding |
| throttle_grip, throttle | ±0.5% | ADC noise |
| front_speed_kmh, rear_speed_kmh | ±0.5 km/h | Float precision |
| gps_speed_kmh | ±0.5 km/h | GPS precision |
| gear | exact | Integer, must match |
| acc_x_g, acc_y_g | ±0.02 G | Accelerometer precision |
| lean_deg, lean_signed_deg | ±0.5° | Gyroscope precision |
| pitch_deg_s | ±0.5°/s | Gyroscope precision |
| water_temp, intake_temp | ±0.5°C | Temp sensor precision |
| fuel_cc | ±0.05 cc | Fuel level precision |
| front_brake_bar, rear_brake_bar | ±0.1 bar | Pressure sensor precision |
| f_abs, r_abs, tcs, scs, lif, launch | exact | Boolean/flags |

## Running Validation

### Quick Validation

```bash
# Run validation script directly
node scripts/validate.mjs
```

### Via Vitest

```bash
# Run validation test suite
npm test -- validation.test.ts

# Run all tests
npm test
```

## Validation Results

Last run: 2026-02-07

- Files validated: 15
- Total aligned records: 123,476
- Total comparisons: 2,839,948 (123,476 records × 23 channels)
- Total matches: 2,839,948
- **Overall match rate: 100.00%** ✓

All 23 channels achieve 100% match rate within tolerances.

## Regenerating Python Ground Truth

If you need to regenerate the Python CSV files:

```bash
# From project root
cd /Users/timotheerebours/PersonalProjects/louis-file
./ctrk-exporter parse parser/test-data/*.CTRK -o parser/test-data/python-output
```

This will overwrite the existing CSV files with fresh output from the Python parser.

## Adding New Test Files

To add new test files to the validation suite:

1. Symlink the CTRK file from `../../input/`:
   ```bash
   cd parser/test-data
   ln -s ../../input/new-file.CTRK .
   ```

2. Generate Python ground truth:
   ```bash
   cd ../..
   ./ctrk-exporter parse parser/test-data/new-file.CTRK -o parser/test-data/python-output
   ```

3. Run validation:
   ```bash
   cd parser
   node scripts/validate.mjs
   ```

The validation script automatically discovers all `.CTRK` files in the test-data directory.
