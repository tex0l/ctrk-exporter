# Epic: Session Summary and Lap Timing

**Epic ID:** EPIC-001
**Priority:** Must Have
**Value:** HIGH | **Effort:** LOW
**Status:** Proposed

---

## Objective

Surface session-level metadata and per-lap timing information that the parser already extracts but does not expose, so that track riders can immediately see their lap times, best lap, and session context without post-processing the CSV.

---

## Scope

### Included

- Parse and expose JSON footer metadata (track name, rider, date, weather, CCU version, tire info)
- Compute and display per-lap timing from existing telemetry timestamps (lap start time, lap duration, delta to best)
- Print a session summary to stdout after parsing (session info + lap time table)
- Add a `--summary` / `-s` CLI flag to output only the summary (no CSV)
- Add a `summary` CLI subcommand for quick inspection without full parse output
- Include lap timing data in CSV output (optional: as a separate summary CSV or as header comments)
- Expose session metadata and lap times via the CTRKParser API (programmatic access)
- **Hybrid lap detection** (from Review Rec #5): Use type-5 Lap marker records as primary lap detection, with GPS finish-line crossing as fallback when type-5 markers are absent. This improves native agreement from 39/42 to 41/42 files and ensures accurate lap timing even in edge cases (e.g., millis wrapping causing missing type-5 markers)

### Excluded

- Interactive lap comparison or visualization (see future EPIC-004)
- Sector timing or split times (not available in current data; would require sector definition)
- Cross-session comparison (see future EPIC-005)
- Changes to the binary parsing logic or CAN data extraction

---

## User Stories

### Track Riders

- **US-1.1:** As a track rider, I want to see my lap times printed after parsing so that I can identify my best and worst laps without opening a CSV.
- **US-1.2:** As a track rider, I want to see the track name and session date in the output so that I know which session I am looking at.
- **US-1.3:** As a track rider, I want a quick `summary` command that shows lap times without generating a full CSV, so that I can check my results in seconds.
- **US-1.4:** As a track rider, I want to see the delta to my best lap for each lap, so that I can identify where I lost time.

### Data Engineers / Coaches

- **US-1.5:** As a data engineer, I want session metadata (rider, track, date, weather) included in the output, so that I can organize and filter sessions programmatically.
- **US-1.6:** As a coach, I want a lap summary table with lap times and best/worst indicators, so that I can quickly assess a rider's session.
- **US-1.7:** As a data engineer, I want to access lap timing data via the Python API (not just stdout), so that I can build automated analysis pipelines.

### Developers

- **US-1.8:** As a developer, I want the CTRKParser to expose a `session_info` property with structured metadata, so that I can use it in my applications.
- **US-1.9:** As a developer, I want the CTRKParser to expose a `lap_times` property with per-lap timing, so that I can build lap comparison features.

---

## Acceptance Criteria

1. **AC-1:** Running `./ctrk-exporter parse file.CTRK` prints a session summary block to stdout including: session date, track name (if available), rider (if available), total laps, total duration, best lap time, and a per-lap timing table.

2. **AC-2:** The per-lap timing table shows: lap number, lap time (mm:ss.sss), delta to best lap (+/-ss.sss), and flags the best lap. Example:
   ```
   Session: 2025-07-29 | Track: (not set) | Rider: R122
   Laps: 6 | Duration: 9:42.3 | Best: Lap 4 (1:31.204)

   Lap    Time        Delta
   1      1:45.312    +14.108
   2      1:33.891    +2.687
   3      1:32.104    +0.900
   4      1:31.204    BEST
   5      1:31.998    +0.794
   6      1:37.805    +6.601
   ```

3. **AC-3:** Running `./ctrk-exporter summary file.CTRK` shows the summary without generating any CSV files.

4. **AC-4:** The JSON footer metadata is parsed and stored in a `session_info` dict on the `CTRKParser` instance, accessible after calling `parse()`.

5. **AC-5:** A `lap_times` list is computed from emitted records and stored on the `CTRKParser` instance, containing per-lap start time (ms), end time (ms), duration (ms), and record count.

6. **AC-6:** Session metadata is optionally written to a `_session.json` file alongside the CSV output (enabled by default, suppressible).

7. **AC-7:** The parser remains dependency-free. All new features use only the Python standard library.

8. **AC-8:** Lap timing computation works correctly for files with 0 laps (no GPS), 1 lap (no finish line crossing), and 10+ laps.

9. **AC-9:** Lap detection uses type-5 Lap marker records when present, falling back to GPS finish-line crossing when type-5 markers are absent. Native lap agreement improves from 39/42 to 41/42 files.

---

## Dependencies

- None. This epic builds entirely on existing parser capabilities.
- The JSON footer is already read by the parser (bytes are available); it just needs to be parsed and exposed.
- Lap boundaries are already detected (both GPS crossing and type-5 markers); timing is derivable from existing `time_ms` fields.
- **TASK-H3** (Spec Accuracy Update) should be completed first so that type-5 Lap marker payload format (`[lap_time_ms(4LE)][reserved(4)]`) is formally documented before implementation.

---

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| JSON footer is missing in some files | LOW | LOW | Handle gracefully: show "(not set)" for missing fields. Already observed that fields like CircuitName and LapCount are often empty strings. |
| Lap 1 timing includes warm-up / out-lap | MEDIUM | LOW | Document that lap 1 is from session start to first finish-line crossing, which typically includes the out-lap. This matches standard track day conventions. |
| Time computation edge case with default-date files (2000-01-01) | LOW | LOW | Lap duration computation (end_time - start_time) works correctly regardless of absolute date. |

---

## Implementation Notes

### JSON Footer Parsing

The footer is already locatable (last ~370 bytes of the file, starting with `{"Attribute"`). Parse it as JSON, extract the `Attribute` array of `{Key, Value}` pairs, and store as a flat dict:

```python
{
    "format_version": "1.0",
    "weather": "1",
    "date": "2025-07-29 15:08:18",
    "tire": "",
    "ssid": "YAMAHA MOTOR CCU D0142A",
    "lap_count": "",
    "circuit_name": "",
    "name": "20250729-170818",
    "user": "R122",
    "temperature": ""
}
```

### Lap Timing Computation

After parsing, iterate over `self.records` and group by `lap` field. For each lap:
- `start_ms` = first record's `time_ms`
- `end_ms` = last record's `time_ms`
- `duration_ms` = `end_ms - start_ms`
- `record_count` = number of records in that lap

### Hybrid Lap Detection (from Rec #5)

Replace the GPS-only lap detection with a hybrid approach:
- **Primary:** Type-5 Lap marker records (matching native library behavior)
- **Fallback:** GPS finish-line crossing (covers missing type-5 records)

**Cooldown-based anti-bounce:** Both type-5 and GPS crossing run concurrently in the single-pass parser. A 10-second cooldown prevents double-counting the same lap boundary.

| Scenario | Type-5 | GPS | Result |
|----------|--------|-----|--------|
| Normal boundary | Fires at t=68.0s | Fires at t=68.1s | Type-5 increments; GPS suppressed by cooldown |
| Missing type-5 (20250906-161606) | Absent | Fires | GPS increments (no recent cooldown) |
| Extra GPS crossing (20251017-095712) | Absent | Fires | GPS increments (fallback behavior) |
| File with no type-5 at all | N/A | Fires | Pure GPS mode (unchanged from current) |

**Key code changes:**
1. Add `LAP_COOLDOWN_MS = 10000` constant and `_last_lap_change_ms` state
2. Gate `_check_lap_crossing` with cooldown: only fire GPS-based lap if no type-5 within 10s
3. Add type-5 handler in `_parse_data_section`: increment lap on `rec_type == 5` with `lap_time_ms >= 15`
4. Update all 3 `_check_lap_crossing` call sites with `current_epoch_ms` parameter

**Verification:** Re-parse all files and check:
- 20250906-161606: should detect 11 laps (GPS fallback fills missing type-5)
- 20251017-095712: GPS fallback fires for extra crossing
- 20250729-155522: type-5 may resolve boundary-edge difference

### Estimated Effort

- Footer parsing: ~30 lines of code
- Lap timing computation: ~20 lines
- Summary formatting: ~40 lines
- CLI changes (summary subcommand, --summary flag): ~30 lines
- Session JSON export: ~20 lines
- Hybrid lap detection: ~30 lines
- Total: ~170 lines
