# Exploration Phase Changelog

History of the Python parser, Android bridge, and reverse-engineering work that preceded the TypeScript rewrite.

---

## February 5, 2026

Parser v7 — 1031 lines | Spec v2.1 | 94.9% match rate (47 files, 22 channels validated vs native)

### Parser

- **Native per-lap mode** (`--native`): new parsing path that resets state at each lap, replicating the per-lap architecture of `libSensorsRecordIF.so`. Achieves 95.6% global match rate and 98.7% on `fuel_cc` (vs 86.5% in continuous mode).
- **Structured header decoding** (`_find_data_start`): replaces naive pattern-matching with proper reading of header entries (RECORDLINE, CCU_VERSION, etc.) starting at offset 0x34.
- **Native timestamp conversion** (`_get_time_data`): implements exact native algorithm (`GetTimeData` @ 0xdf40) with millis wrapping handling (millisecond counter rollback).
- **Zero initial state**: default values for lean, pitch, acc_x, acc_y changed from their neutral offset (9000, 30000, 7000, 7000) to 0, in accordance with native `memset(0)`.
- **Emission clock reset** at type-5 (Lap) markers, improving RPM match from ~77% to ~83%.
- **Dead code removal**: unused `re` import, unreferenced `CAN_DLC` dict, counters (`gps_count`, `can_count`, `checksum_failures`) incremented but never read in `_parse_lap_range`, orphaned `ensure_output_dir()` function, unused variables.
- **Signed lean** (`lean_signed_deg`): derived field (not a new CAN channel) preserving lean direction. Same CAN data 0x0258, same deadband and rounding, but sign of `sum_val - 9000` is preserved. Absent from native output.
- **Docstring**: v6 → v7.

### CLI

- **`--native` flag** on `parse` command to enable per-lap mode.
- `re` import moved to top-level, unused `import os` removed.
- Unused variables `setup_parser` / `clean_parser` cleaned up.

### Format Specification (v2.0 → v2.1)

- **v2.0**: complete rewrite. Structured 14-byte header instead of pattern-matching. Documentation of: void GPS coordinates (9999, 9999), fuel accumulator with per-lap reset, complete hex examples from real files.
- **v2.1**: native behaviors only — 3-band time delta verification (secondary threshold 10ms @ 0xaf1b), line counter limit (72000 @ 0xaece), gear=7 rejection (0xe163), CAN 0x051b handler (0xe102).

### Documentation

- **New**: `docs/REVIEW_REPORT.md` — validation report with spec compliance matrix.
- **New**: `docs/product/BACKLOG.md` — prioritized product backlog (7 epics, decision log).
- **New**: 3 detailed epics (EPIC-001 Session Summary, EPIC-002 Export Formats, EPIC-003 Python Package).
- **New**: `src/test_parser_comparison.py` — Python vs Native comparison suite (361 lines), GPS alignment, per-channel tolerances.
- **Removed**: `docs/TODO.md` (replaced by backlog).
- **Harmonization**: canonical numbers (47 files, 22 channels, 420K+ records, 94.9%) unified across all documents. Fixed acc_x (Longitudinal) / acc_y (Lateral) inversion in README.
- **NATIVE_LIBRARY.md**: duplicate sections (CAN timestamp, LEAN formula) replaced with references to spec. Match rate corrected from 95.37% to 94.9%.
- **EPIC-001**: dead references cleaned up (TASK-H3, Rec #5, EPIC-004/005).
- **Agents** (`.claude/agents/`): CLI correctly described as Python (not Bash), line counts updated, referenced files corrected.
- **Removal of .CCT mentions**: the `.CCT` format is neither tested nor supported by the Python parser.

---

## January 27, 2026

Parser v6 — 836 lines | Spec v1.3 | Validation on 42 files

### Parser

- **CAN timestamp structure discovery**: the `E9 07` bytes were not a magic number but the year 2025 in little-endian (`uint16`, 0x07E9). The parser now reads year as a proper field, supporting **all files regardless of recording date** (not just 2025).
- **ABS bit order correction**: `R_ABS = bit0`, `F_ABS = bit1` (previously inverted), conforming to native disassembly @ 0xe2b7.
- **Multi-file support**: `./ctrk-exporter parse *.CTRK` processes all files at once with output to a directory.
- **Name alignment** between parser and specification.

### Documentation

- **Spec v1.3**: complete CAN timestamp structure documented (8 bytes: sec, min, hour, weekday, day, month, year LE).
- **NATIVE_LIBRARY.md**: validation extended to 42 files across 4 months (July-October 2025), 21 channels, JNI interface documented (`GetTotalLap`, `GetLapTimeRecordData`, `GetSensorsRecordData`), supported architectures.
- **New**: `docs/TODO.md` — task tracking.

---

## January 26, 2026

Parser v6 — 836 lines | Spec v1.2 | Validation on 1 file

### Parser

- **8 decoded CAN IDs**: 0x0209 (RPM/Gear), 0x0215 (Throttle/TCS/SCS/LIF/Launch), 0x023E (Temp/Fuel), 0x0250 (Accel X/Y), 0x0258 (Lean/Pitch), 0x0260 (Brakes), 0x0264 (Wheel Speed), 0x0268 (ABS). All verified by disassembly of `libSensorsRecordIF.so`.
- **21 telemetry channels**: 15 analog + 6 boolean, with complete calibration formulas.
- **Lap detection** via GPS finish line crossing (coordinates extracted from header).
- **Fuel accumulator** with per-lap reset.
- **Native LEAN algorithm**: ±5° deadband, rounding to hundred, nibble interleaving.
- **CSV export** calibrated (26 columns) + optional raw export (`--raw`).

### CLI

- 5 commands: `parse`, `graph`, `android setup`, `android convert`, `android clean`.
- `parse`: single file with `--raw` flag and `-o` option.
- `graph`: per-lap graph generation (matplotlib/pandas, requires venv).
- `android`: bridge to native library via Android emulator (macOS ARM only).

### Android Bridge

- Complete Kotlin app (`android_app/`) with `NativeBridge.kt`, `SessionContainer.kt`, `TelemetryPoint.kt`.
- `build_and_run.sh` script for compilation and execution.
- `.so` extraction from Y-Trac v1.3.8 APK.

### Documentation

- **Spec v1.2**: binary format documented (partially in French), verification on 1 file (16,462 native points vs 16,475 parser, +0.08%).
- **NATIVE_LIBRARY.md**: initial reverse engineering notes.
- **3 additional docs**: `REVERSE_ENGINEERING_SUMMARY.md`, `libSensorsRecordIF_howitworks.md`, `libSensorsRecordIF_usage.md`.
- **Analysis scripts**: `analyze_lean_formula.py`, `compare_raw_values.py`, `compare_values.py`, `extract_ytrac_values.py`, `test_can_parsing.py`, `visualize_comparison.py`, `visualize_ride.py`.
