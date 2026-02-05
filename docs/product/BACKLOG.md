# Product Backlog

**Last Updated:** 2026-02-04
**Product:** CTRK-Exporter — Python parser for Yamaha Y-Trac telemetry files

---

## State of the Project

### What Works Today

- **Core parser** (`src/ctrk_parser.py`, 1048 lines, zero dependencies): Parses all 22 telemetry channels from CTRK binary files at 10 Hz. Validated against the native library at 94.9% overall match rate across 47 files and 420K+ telemetry records. All CAN data extraction (byte positions, bit masks, formulas) is 100% correct per disassembly.
- **Two parsing modes**: Default continuous mode (better data quality, no impossible values at lap boundaries) and `--native` per-lap mode (matches native library architecture for validation).
- **Lap detection**: GPS finish-line crossing from header coordinates. Agrees with native in 39/42 files.
- **CSV export**: 26-column output with calibrated engineering units. Optional raw (uncalibrated) export for comparison.
- **Graph generation**: Per-lap matplotlib visualizations of all channels via `visualize_all_channels.py`.
- **CLI** (`ctrk-exporter`): Supports `parse` (batch), `graph`, and `android` subcommands.
- **Android bridge**: Can invoke the native library via Android emulator for reference validation.
- **Documentation**: Complete binary format specification (v2.1), native library reverse-engineering notes, validation review report.

### Current Gaps and Limitations

1. **No programmatic API**: The parser is only usable as a CLI tool or by importing the class directly. No pip-installable package, no `__init__.py`, no stable public API.
2. **No session metadata in output**: The JSON footer (track name, rider, date, weather, CCU version) is parsed but not exposed in any output.
3. **No lap time summary**: Users must compute lap times from timestamps manually. The native library has `GetLapTimeRecordData()` but the parser does not expose lap timing.
4. **Limited export formats**: CSV only. No JSON, no GPX (for GPS track overlay), no direct import into popular telemetry tools (MoTeC i2, RaceStudio 3, AiM).
5. **Visualization is basic**: Single-file PNG per lap. No interactive charts, no lap comparison overlay, no track map.
6. **RPM match rate ceiling**: 83% RPM match in continuous mode due to architectural emission grid divergence. Not a data quality issue (all values are correct), but limits validation confidence.
7. **No error reporting or diagnostics**: Parser fails silently on corrupt files. No structured error output, no file health report.
8. **No multi-session analysis**: Each file is parsed independently. No session comparison, no trend tracking across sessions.
9. **Platform limitation**: Android bridge requires macOS ARM with Android SDK. Graph generation requires virtual environment setup.

### User Pain Points (by Persona)

**Track riders:**
- Cannot easily see lap times and best lap without scrolling through CSV rows
- Cannot compare laps side-by-side (braking points, cornering speed, throttle application)
- No way to visualize their riding line on a track map
- Must use the proprietary Y-Trac app or manually process CSVs

**Data engineers / coaches:**
- CSV output lacks session metadata context (track, rider, conditions)
- No programmatic API for batch analysis workflows
- Cannot import directly into standard telemetry tools (MoTeC, AiM, RaceStudio)
- No JSON output for web-based dashboards

**Developers:**
- No pip-installable package makes integration difficult
- No typed return objects from the API (just CSV files)
- Parser internals are not clearly separated from I/O concerns
- Format spec is excellent but there is no reference implementation with clear API boundaries

### Opportunities

1. **Open-format advantage**: Y-Trac is a closed ecosystem. An open, documented parser is the only way to get data into standard tools.
2. **Lap comparison is the killer feature**: Track riders primarily want to compare their best and worst laps to find time. This is the most requested feature in any telemetry tool.
3. **MoTeC/AiM export unlocks the coaching market**: Professional coaches already use these tools. CTRK export to these formats would make Y-Trac data usable in existing workflows.
4. **Python package distribution**: pip install would make the parser accessible to thousands of data-literate riders and engineers.
5. **GPX export for track maps**: Riders love visualizing their GPS trace on satellite imagery. GPX is trivially derivable from existing output.

---

## Epics (Prioritized by Value/Effort)

### Must Have

| # | Epic | Value | Effort | Rationale |
|---|------|-------|--------|-----------|
| 1 | [EPIC-001: Session Summary and Lap Timing](epics/EPIC-001-session-summary-lap-timing.md) | HIGH | LOW | Highest-value feature for track riders. Exposes data already parsed but not surfaced. No new parsing logic needed. |
| 2 | [EPIC-002: Export Format Expansion](epics/EPIC-002-export-format-expansion.md) | HIGH | MEDIUM | Unlocks integration with standard telemetry tools and GPS visualization. Each format is independently deliverable. |

### Should Have

| # | Epic | Value | Effort | Rationale |
|---|------|-------|--------|-----------|
| 3 | [EPIC-003: Python Package and API](epics/EPIC-003-python-package-api.md) | MEDIUM | MEDIUM | Foundation for developer adoption and downstream tooling. Enables pip install and programmatic access. |

### Could Have (Future)

| # | Epic | Value | Effort | Notes |
|---|------|-------|--------|-------|
| 4 | Interactive Lap Comparison Dashboard | HIGH | HIGH | Web-based or Jupyter lap overlay with track map. Depends on EPIC-001 and EPIC-003. |
| 5 | Multi-Session Trend Analysis | MEDIUM | HIGH | Cross-session comparison (lap time progression, consistency metrics). Depends on EPIC-003. |
| 6 | File Recovery and Diagnostics | LOW | MEDIUM | Implement equivalents of native `DamageRecoveryLogFile()` and file health reporting. |

### Won't Have (Out of Scope)

| # | Item | Reason |
|---|------|--------|
| - | Native library distribution | Proprietary code cannot be committed or distributed |
| - | Real-time telemetry streaming | CTRK is a post-session format; live streaming is a different product |
| - | Mobile app | The Y-Trac app already exists; our value is in desktop/server analysis |
| - | Exact native library replication | The ~5% match gap is architectural and intentional; our output is more correct at lap boundaries |

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-02-04 | Prioritize session summary over export formats | Track riders need immediate value; session summary is low-effort/high-impact |
| 2026-02-04 | Include GPX in export formats epic rather than standalone | GPX is a simple coordinate-list format derivable from existing output |
| 2026-02-04 | Defer interactive dashboard to after package API | A proper API makes dashboard development sustainable |
| 2026-02-04 | Keep parser dependency-free as a hard constraint | Core parsing must work with zero pip install; optional features can have dependencies |
