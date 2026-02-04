# Epic: Export Format Expansion

**Epic ID:** EPIC-002
**Priority:** Must Have
**Value:** HIGH | **Effort:** MEDIUM
**Status:** Proposed

---

## Objective

Add JSON, GPX, and MoTeC CSV export formats so that parsed telemetry data can be used in GPS track visualization tools, standard telemetry analysis software, and web-based dashboards -- unlocking workflows that are impossible with the proprietary Y-Trac app.

---

## Scope

### Included

- **JSON export** (`--format json`): Full telemetry data as structured JSON, including session metadata and lap timing. Suitable for web dashboards and programmatic consumption.
- **GPX export** (`--format gpx`): GPS track as a standard GPX file with timestamps and speed, importable into Google Earth, Strava, GPS Visualizer, etc.
- **MoTeC CSV export** (`--format motec`): CSV formatted for direct import into MoTeC i2 Pro, the industry-standard telemetry analysis tool used by coaches and racing teams.
- **Format selection via CLI**: `--format` flag accepting `csv` (default), `json`, `gpx`, `motec`, or `all`.
- **Multi-format output**: `--format all` generates all formats in a single parse pass.

### Excluded

- AiM RaceStudio format (proprietary binary; could be added later)
- Live telemetry streaming formats (out of project scope)
- Custom user-defined export templates
- Direct upload to cloud services (Strava, etc.)

---

## User Stories

### Track Riders

- **US-2.1:** As a track rider, I want to export my session as a GPX file so that I can visualize my riding line on Google Earth or GPS Visualizer.
- **US-2.2:** As a track rider, I want to overlay my GPS trace on a satellite image of the track so that I can see where I am riding on the circuit.
- **US-2.3:** As a track rider, I want to share my session data as a JSON file with friends or online communities so that they can view it in web-based tools.

### Data Engineers / Coaches

- **US-2.4:** As a coach, I want to import Y-Trac data into MoTeC i2 so that I can use its professional analysis features (channel math, sector analysis, driver comparison).
- **US-2.5:** As a data engineer, I want JSON output with structured metadata so that I can build web dashboards that display session data.
- **US-2.6:** As a data engineer, I want to generate all export formats in a single command so that I do not have to parse the file multiple times.

### Developers

- **US-2.7:** As a developer, I want the export logic to be modular so that I can add new export formats without modifying the parser core.
- **US-2.8:** As a developer, I want the JSON schema to be documented so that I can build tools that consume it.

---

## Acceptance Criteria

### JSON Export

1. **AC-2.1:** Running `./ctrk-exporter parse file.CTRK --format json` produces a `.json` file containing:
   - `session`: metadata object (date, track, rider, weather, CCU version)
   - `laps`: array of lap summary objects (number, start_ms, end_ms, duration_ms, record_count)
   - `records`: array of telemetry record objects with all 26 fields
   - `format_version`: schema version string for forward compatibility

2. **AC-2.2:** The JSON file is valid JSON and parseable by `json.loads()` without errors.

3. **AC-2.3:** The JSON schema uses snake_case keys consistent with the CSV column naming.

### GPX Export

4. **AC-2.4:** Running `./ctrk-exporter parse file.CTRK --format gpx` produces a `.gpx` file that:
   - Is valid GPX 1.1 XML
   - Contains a `<trk>` element with one `<trkseg>` per lap
   - Each `<trkpt>` has `lat`, `lon` attributes and `<time>`, `<speed>` (m/s), `<ele>` (set to 0) child elements
   - Uses ISO 8601 timestamps in UTC

5. **AC-2.5:** The GPX file opens correctly in Google Earth, GPX Visualizer, or Strava route import.

6. **AC-2.6:** Records with sentinel GPS coordinates (9999.0, 9999.0) are excluded from the GPX output.

### MoTeC CSV Export

7. **AC-2.7:** Running `./ctrk-exporter parse file.CTRK --format motec` produces a CSV file with:
   - MoTeC i2 compatible header format (channel name, unit, sample rate on separate header rows)
   - Time column in seconds (relative to session start)
   - Channel names and units matching MoTeC conventions (e.g., "Engine RPM [rpm]", "Ground Speed [km/h]")
   - Lap markers as a separate channel or as MoTeC beacon markers

8. **AC-2.8:** The MoTeC CSV imports correctly into MoTeC i2 Pro via "Import CSV" with automatic channel recognition.

### CLI

9. **AC-2.9:** The `--format` flag accepts: `csv`, `json`, `gpx`, `motec`, `all`.
10. **AC-2.10:** `--format all` generates all four formats from a single parse pass.
11. **AC-2.11:** The default format remains `csv` (backward compatible).

### General

12. **AC-2.12:** All export formats use the same parsed data (single parse, multiple exports). No re-parsing per format.
13. **AC-2.13:** All exporters remain dependency-free (standard library only). GPX uses string formatting or `xml.etree`, JSON uses `json` module.

---

## Dependencies

- **EPIC-001 (Session Summary)**: The JSON export benefits from session metadata and lap timing being available on the CTRKParser instance. This epic can proceed in parallel but will integrate EPIC-001's outputs once available.
- No external library dependencies.

---

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| MoTeC CSV format is undocumented | MEDIUM | MEDIUM | MoTeC i2 has a well-known CSV import wizard. Test with the free i2 Pro software. Multiple open-source projects document the format. |
| GPX files are large for long sessions | LOW | LOW | A 10-minute session at 10 Hz = 6000 points, which is ~500 KB GPX. Acceptable. |
| JSON files are large for long sessions | LOW | LOW | Same session = ~2 MB JSON. Acceptable. Could add optional gzip compression later. |
| MoTeC beacon/lap marker format is tricky | MEDIUM | LOW | Start with a simple lap number channel. Beacon markers can be added later as an enhancement. |

---

## Implementation Notes

### Architecture: Exporter Interface

Introduce a simple exporter pattern. Each format implements an `export(records, session_info, lap_times, output_path)` function:

```python
# src/exporters/json_exporter.py
def export_json(records, session_info, lap_times, output_path):
    ...

# src/exporters/gpx_exporter.py
def export_gpx(records, session_info, lap_times, output_path):
    ...

# src/exporters/motec_exporter.py
def export_motec(records, session_info, lap_times, output_path):
    ...
```

The existing `export_csv()` method on `CTRKParser` remains but is refactored to use the same pattern internally.

### GPX Format Reference

```xml
<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="ctrk-exporter"
     xmlns="http://www.topografix.com/GPX/1/1">
  <trk>
    <name>Session 20250729-170818</name>
    <trkseg>  <!-- Lap 1 -->
      <trkpt lat="47.950683" lon="0.208733">
        <time>2025-07-29T12:21:34.879Z</time>
        <speed>26.5</speed>
      </trkpt>
      ...
    </trkseg>
    <trkseg>  <!-- Lap 2 -->
      ...
    </trkseg>
  </trk>
</gpx>
```

### MoTeC CSV Format Reference

```csv
"Format","MoTeC CSV File"
"Venue","Circuit Name"
"Vehicle","Yamaha Y-Trac"
"Driver","R122"
"Comment","Parsed by ctrk-exporter"
"Date","29/07/2025"
"Time","12:21:34"
"Sample Rate","10"

"Time","Engine RPM","Throttle Position","Ground Speed","Lean Angle",...
"s","rpm","%","km/h","deg",...
0.000,0,0.0,0.0,0.0,...
0.100,5234,15.2,45.3,12.0,...
```

### Estimated Effort

| Format | Lines of Code | Time |
|--------|--------------|------|
| JSON exporter | ~60 | 1 hour |
| GPX exporter | ~80 | 1.5 hours |
| MoTeC CSV exporter | ~100 | 2 hours |
| CLI changes (--format flag) | ~40 | 0.5 hours |
| Testing and validation | -- | 2 hours |
| **Total** | **~280** | **~7 hours** |

### Delivery Order

1. JSON (simplest, most broadly useful)
2. GPX (high rider appeal, simple format)
3. MoTeC CSV (highest coaching value, requires format research)

Each format can be delivered independently as a standalone PR.
