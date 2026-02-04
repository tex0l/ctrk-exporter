# Epic: Python Package and API

**Epic ID:** EPIC-003
**Priority:** Should Have
**Value:** MEDIUM | **Effort:** MEDIUM
**Status:** Proposed

---

## Objective

Restructure the parser into a pip-installable Python package with a clean, typed public API, so that developers and data engineers can integrate CTRK parsing into their own applications and analysis pipelines with a single `pip install`.

---

## Scope

### Included

- **Package structure**: Standard Python package layout with `pyproject.toml`, `__init__.py`, and clear module boundaries.
- **Public API**: Typed, documented API for parsing files, accessing records, session metadata, and lap timing.
- **CLI entry point**: `ctrk-exporter` command installed via pip (`[project.scripts]` in pyproject.toml).
- **Backward compatibility**: The `./ctrk-exporter` bash script continues to work for users who clone the repo directly.
- **Optional dependencies**: Graph generation (`matplotlib`, `pandas`) as an optional extra (`pip install ctrk-exporter[graphs]`).
- **Type hints**: Full type annotations on all public API methods and return types.
- **API documentation**: Docstrings on all public classes and methods, following Google or NumPy docstring conventions.

### Excluded

- Publishing to PyPI (deferred until API is stable; local `pip install -e .` is sufficient initially)
- REST API or web server
- Plugin/extension system
- Async/concurrent parsing
- Breaking changes to the CSV output format

---

## User Stories

### Data Engineers / Coaches

- **US-3.1:** As a data engineer, I want to `pip install ctrk-exporter` so that I can use it in my Python projects without cloning the repo.
- **US-3.2:** As a data engineer, I want to call `parser.parse()` and get back typed Python objects so that I can process telemetry data programmatically.
- **US-3.3:** As a data engineer, I want to access `parser.session_info` and `parser.lap_times` as Python dicts/lists so that I can build automated reports.
- **US-3.4:** As a coach, I want to write a simple Python script that parses multiple sessions and compares lap times, without dealing with CSV parsing.

### Developers

- **US-3.5:** As a developer, I want the package to have clear module boundaries (parser, exporters, calibration) so that I can understand and extend the codebase.
- **US-3.6:** As a developer, I want type hints on all public API methods so that my IDE provides autocomplete and type checking.
- **US-3.7:** As a developer, I want a `CTRKSession` return type from `parse()` that bundles records, metadata, and lap timing, so that I have a single entry point to all parsed data.
- **US-3.8:** As a developer, I want the parser to raise specific exception types (e.g., `CTRKFormatError`, `CTRKChecksumError`) so that I can handle errors appropriately.

---

## Acceptance Criteria

### Package Installation

1. **AC-3.1:** Running `pip install -e .` from the project root installs the package and makes `ctrk-exporter` available as a CLI command.
2. **AC-3.2:** Running `pip install -e ".[graphs]"` also installs matplotlib and pandas for graph generation.
3. **AC-3.3:** The core package has zero runtime dependencies (standard library only).

### Public API

4. **AC-3.4:** The following import works after installation:
   ```python
   from ctrk_exporter import CTRKParser

   parser = CTRKParser("session.CTRK")
   session = parser.parse()

   # Typed access to parsed data
   session.records       # list[TelemetryRecord]
   session.session_info  # SessionInfo dataclass
   session.lap_times     # list[LapTime]
   session.metadata      # dict (raw footer JSON)
   ```

5. **AC-3.5:** `TelemetryRecord`, `SessionInfo`, and `LapTime` are dataclasses with full type annotations, importable from `ctrk_exporter.models`.

6. **AC-3.6:** `CTRKParser` raises `CTRKFormatError` (subclass of `ValueError`) for invalid files (bad magic, truncated data, etc.).

7. **AC-3.7:** All public API methods and classes have docstrings.

### Module Structure

8. **AC-3.8:** The package follows this structure:
   ```
   ctrk_exporter/
   +-- __init__.py          # Public API exports
   +-- parser.py            # CTRKParser class
   +-- models.py            # TelemetryRecord, SessionInfo, LapTime, FinishLine
   +-- calibration.py       # Calibration class
   +-- can.py               # CAN parsing functions and handlers
   +-- lap_detection.py     # FinishLine, crossing detection
   +-- exporters/
   |   +-- __init__.py
   |   +-- csv_exporter.py
   |   +-- json_exporter.py  # (from EPIC-002)
   |   +-- gpx_exporter.py   # (from EPIC-002)
   |   +-- motec_exporter.py # (from EPIC-002)
   +-- cli.py               # CLI entry point (argparse)
   ```

9. **AC-3.9:** The `src/ctrk_parser.py` monolith is refactored into the module structure above without changing any parsing logic or output.

### Backward Compatibility

10. **AC-3.10:** The existing `./ctrk-exporter` bash script continues to work for repo-clone users.
11. **AC-3.11:** CSV output from the refactored package is byte-identical to the current parser for the same input file and mode.
12. **AC-3.12:** The `--native` and `--raw` flags continue to work.

### Type Safety

13. **AC-3.13:** Running `mypy ctrk_exporter/` passes with no errors on strict mode (or near-strict with documented exceptions).

---

## Dependencies

- **EPIC-001 (Session Summary)**: The `SessionInfo` and `LapTime` models defined here should align with what EPIC-001 implements. If EPIC-001 is delivered first, the package refactoring absorbs those additions. If delivered in parallel, coordinate on the data model.
- **EPIC-002 (Export Formats)**: The exporter module structure defined here provides the home for EPIC-002's format implementations. Can be delivered in either order.

---

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Refactoring introduces parsing regressions | MEDIUM | HIGH | Create a regression test that compares output of refactored parser against current parser for all 47 test files. Must be byte-identical. |
| API design is hard to get right on first try | MEDIUM | MEDIUM | Start with a minimal API surface. Use `__all__` to control public exports. Mark anything uncertain as `_private`. Expand based on actual usage feedback. |
| Breaking `./ctrk-exporter` bash script | LOW | MEDIUM | Keep the bash script as a thin wrapper. Add integration test that runs the bash script and verifies output. |
| mypy strict mode is too restrictive | LOW | LOW | Start with basic type checking, escalate to strict incrementally. The parser uses standard types (int, float, bytes, dict) that are easy to annotate. |

---

## Implementation Notes

### pyproject.toml

```toml
[project]
name = "ctrk-exporter"
version = "0.1.0"
description = "Parser for Yamaha Y-Trac CTRK telemetry files"
requires-python = ">=3.9"
license = {text = "MIT"}
dependencies = []  # Zero runtime dependencies

[project.optional-dependencies]
graphs = ["matplotlib>=3.5", "pandas>=1.4"]

[project.scripts]
ctrk-exporter = "ctrk_exporter.cli:main"

[build-system]
requires = ["setuptools>=64"]
build-backend = "setuptools.backends._legacy:_Backend"
```

### Migration Strategy

The refactoring from monolith (`src/ctrk_parser.py`) to package (`ctrk_exporter/`) should be done in a single PR to avoid a split-brain period. Steps:

1. Create the package directory structure
2. Extract models (dataclasses) into `models.py`
3. Extract calibration into `calibration.py`
4. Extract CAN parsing into `can.py`
5. Extract lap detection into `lap_detection.py`
6. Extract CSV export into `exporters/csv_exporter.py`
7. Move parser core into `parser.py`
8. Create `__init__.py` with public exports
9. Create `cli.py` from the current `ctrk-exporter` script
10. Add `pyproject.toml`
11. Run regression test (byte-identical CSV output for all test files)
12. Update `./ctrk-exporter` bash script to use the package or keep as fallback

### CTRKSession Return Type

```python
@dataclass
class CTRKSession:
    """Complete parsed session data."""
    records: List[TelemetryRecord]
    session_info: SessionInfo
    lap_times: List[LapTime]
    finish_line: Optional[FinishLine]
    metadata: dict  # Raw JSON footer
    file_path: Path
    parse_stats: ParseStats  # Record counts, checksum failures, etc.
```

### Estimated Effort

| Task | Lines Changed | Time |
|------|--------------|------|
| Create package structure and pyproject.toml | ~50 | 0.5 hours |
| Extract models.py | ~80 (moved) | 0.5 hours |
| Extract calibration.py | ~50 (moved) | 0.5 hours |
| Extract can.py | ~120 (moved) | 0.5 hours |
| Extract lap_detection.py | ~70 (moved) | 0.5 hours |
| Extract exporters/csv_exporter.py | ~80 (moved) | 0.5 hours |
| Refactor parser.py (imports, wiring) | ~100 | 1 hour |
| Create cli.py from ctrk-exporter script | ~120 (moved + adapted) | 1 hour |
| Add type hints to public API | ~50 | 1 hour |
| Add docstrings | ~80 | 1 hour |
| Create regression test | ~60 | 1 hour |
| **Total** | **~860** | **~8 hours** |

Note: Most of this is moving existing code, not writing new code. The actual parsing logic does not change.
