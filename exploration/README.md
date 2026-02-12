# Exploration

This directory contains the original Python parser and reverse-engineering work that preceded the TypeScript rewrite.

## Contents

- **`ctrk-exporter`** — Python CLI for parsing CTRK files and generating graphs
- **`src/`** — Python parser (`ctrk_parser.py`), visualization, and validation scripts
- **`android_app/`** — Kotlin Android app that bridges to the official native library (`libSensorsRecordIF.so`) via an emulator
- **`apk_analysis/`** — Tools for extracting the native `.so` from the Y-Trac APK
- **`docs/`** — Comparison reports, native library reverse-engineering notes, and product planning documents
- **`requirements.txt`** — Python dependencies (pandas, matplotlib) for graph generation

## Usage

```bash
# Set up Python environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Parse a CTRK file
./ctrk-exporter parse session.CTRK

# Generate graphs
./ctrk-exporter graph output/session_parsed.csv
```

The TypeScript parser in `packages/ctrk-parser/` supersedes this code with 100% match rate, browser support, and significantly better performance.
