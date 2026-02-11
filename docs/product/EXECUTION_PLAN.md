# CTRK-Exporter Web Edition: Execution Plan

**Version:** 1.0
**Created:** 2026-02-07
**Status:** READY FOR EXECUTION
**Total Estimated Effort:** 18-26 days
**Estimated Agent Invocations:** 24 invocations

---

## Overview

This document provides a step-by-step execution plan for building the CTRK-Exporter Web Edition, a fully client-side TypeScript-based CTRK parser with interactive visualization. The plan orchestrates the `dev`, `qa`, `review`, and `doc` agents to implement all 9 epics from the product backlog.

### Key Constraints

1. **Zero server-side processing** - All parsing happens in the browser
2. **Static site deployment** - Works as a static Astro site
3. **Accuracy requirement** - TypeScript parser must match Python parser within existing tolerances (95%+ match rate)
4. **Performance target** - Parse 10MB CTRK file in under 5 seconds
5. **Permissive licenses only** - All dependencies must use MIT, BSD, ISC, or Apache 2.0 licenses. NO GPL-3.0, AGPL-3.0, or proprietary licenses

### Reference Implementation

- **Python parser:** `/Users/timotheerebours/PersonalProjects/louis-file/src/ctrk_parser.py` (1,048 lines)
- **Format spec:** `/Users/timotheerebours/PersonalProjects/louis-file/docs/CTRK_FORMAT_SPECIFICATION.md`
- **Validation report:** `/Users/timotheerebours/PersonalProjects/louis-file/docs/COMPARISON.md` (95.40% match rate)
- **Test data:** `/Users/timotheerebours/PersonalProjects/louis-file/input/*.CTRK`

---

## Execution Steps

### Phase 1: TypeScript Parser Foundation (Epic 1)

**Duration:** 3-4 days | **Agent Invocations:** 2

---

#### Step 1.1: Build TypeScript Parser Foundation

**Agent:** `dev`
**Epic:** Epic 1 (Tasks 1.1-1.5)
**Estimated Turns:** 25-30

**Prompt:**

```
You are building the TypeScript parser foundation for the CTRK-Exporter Web Edition. Your task is to port the Python parser's data structures, binary parsing utilities, and CAN message handlers to TypeScript.

CONTEXT:
- Reference implementation: /Users/timotheerebours/PersonalProjects/louis-file/src/ctrk_parser.py
- Format specification: /Users/timotheerebours/PersonalProjects/louis-file/docs/CTRK_FORMAT_SPECIFICATION.md
- This parser must run in the browser (no Node.js-specific APIs)

REQUIREMENTS:
1. Create a new TypeScript project at /Users/timotheerebours/PersonalProjects/louis-file/parser/
2. Setup tsconfig.json with strict mode, ES2020 target, and ESM module system
3. Setup ESLint with TypeScript rules and Prettier for formatting
4. Implement BufferReader class that works with Uint8Array (not Node Buffer)
5. Define TypeScript interfaces/types for TelemetryRecord, FinishLine, Calibration
6. Implement all 8 CAN message parsers (0x0209, 0x0215, 0x023e, 0x0250, 0x0258, 0x0260, 0x0264, 0x0268)
7. Implement header parser (magic validation, variable-length entries, finish line extraction)
8. Include unit tests for all components using a test framework (Vitest recommended)

CRITICAL CONSTRAINTS:
- All third-party dependencies MUST use permissive licenses (MIT, BSD, ISC, Apache 2.0)
- GPL-3.0, AGPL-3.0, and proprietary licenses are NOT allowed
- Verify licenses before adding any dependency (check package.json "license" field or LICENSE file)
- If a dependency has an incompatible license, find an alternative or implement the functionality yourself

CAN MESSAGE PARSERS (all formulas verified against native library):
- 0x0209: RPM (raw/2.56), Gear (direct)
- 0x0215: Throttle (((raw/8.192)*100)/84.96), TCS/SCS/LIF/Launch flags
- 0x023e: Water temp ((raw/1.6)-30), Intake temp, Fuel delta
- 0x0250: Acceleration X/Y ((raw/1000.0)-7.0)
- 0x0258: Lean ((raw/100.0)-90.0), Pitch ((raw/100.0)-300.0) - includes deadband algorithm
- 0x0260: Front/Rear brake (raw/32.0)
- 0x0264: Front/Rear speed ((raw/64.0)*3.6)
- 0x0268: F_ABS, R_ABS flags

DELIVERABLES:
- parser/package.json with dev dependencies only (TypeScript, ESLint, Prettier, test framework)
- parser/tsconfig.json with strict configuration
- parser/src/buffer-reader.ts with unit tests
- parser/src/types.ts with all TypeScript interfaces
- parser/src/finish-line.ts with side_of_line and crosses_line methods
- parser/src/calibration.ts with static calibration methods for all 15 analog channels
- parser/src/can-handlers.ts with all 8 CAN parsers
- parser/src/header-parser.ts with magic validation and finish line extraction
- parser/src/index.ts exporting all public APIs
- All tests passing (npm test)

VERIFICATION:
- Run: npm run build (should compile with zero TypeScript errors)
- Run: npm test (all unit tests should pass)
- Check: npx license-checker --production --onlyAllow "MIT;BSD-2-Clause;BSD-3-Clause;ISC;Apache-2.0" (should pass)
```

**Expected Deliverables:**
- Complete TypeScript parser foundation with binary utilities, data structures, CAN handlers, and header parser
- All unit tests passing
- Zero TypeScript compilation errors
- All dependencies verified to use permissive licenses

**Verification Criteria:**
- `npm run build` completes without errors
- `npm test` passes all tests
- License check passes for all dependencies
- Files exist: package.json, tsconfig.json, src/buffer-reader.ts, src/types.ts, src/finish-line.ts, src/calibration.ts, src/can-handlers.ts, src/header-parser.ts

---

#### Step 1.2: Code Review - Parser Foundation

**Agent:** `review`
**Dependencies:** Step 1.1
**Estimated Turns:** 10-15

**Prompt:**

```
Review the TypeScript parser foundation created in /Users/timotheerebours/PersonalProjects/louis-file/parser/.

REVIEW FOCUS:
1. TypeScript configuration - Check tsconfig.json for strict mode, proper target/module settings
2. Code quality - Verify ESLint configuration and that code follows best practices
3. Type safety - Ensure all functions have proper type annotations, no "any" types without justification
4. Browser compatibility - Verify no Node.js-specific APIs (Buffer, fs, path, etc.)
5. License compliance - Check all dependencies use permissive licenses (MIT, BSD, ISC, Apache 2.0)
6. CAN parser accuracy - Compare formulas against /Users/timotheerebours/PersonalProjects/louis-file/src/ctrk_parser.py
7. Test coverage - Ensure all critical functions have unit tests
8. Documentation - Check JSDoc comments for public APIs

SPECIFIC CHECKS:
- BufferReader uses Uint8Array, not Node Buffer
- All CAN parsers match Python implementation byte-for-byte
- Lean angle parser includes the native deadband/truncation algorithm (0x0258)
- FinishLine.crosses_line detects finish line crossings correctly
- Calibration formulas match docs/CTRK_FORMAT_SPECIFICATION.md

OUTPUT:
- List of issues found (blocking vs non-blocking)
- Recommendations for improvements
- Confirmation that code is ready for next phase or list of required fixes
```

**Expected Deliverables:**
- Code review report with findings
- List of blocking issues (if any)
- Confirmation of readiness for Epic 2

**Verification Criteria:**
- No blocking issues identified
- All CAN formulas verified against Python parser
- License compliance confirmed

---

### Phase 2: TypeScript Parser Core Logic (Epic 2)

**Duration:** 3-4 days | **Agent Invocations:** 2

---

#### Step 2.1: Implement Parser Core Logic

**Agent:** `dev`
**Epic:** Epic 2 (Tasks 2.1-2.6)
**Dependencies:** Step 1.2 approved
**Estimated Turns:** 25-30

**Prompt:**

```
Implement the core parsing logic for the TypeScript CTRK parser. This includes the main parsing loop, timestamp computation, GPS parsing, emission logic, and lap detection.

CONTEXT:
- Reference implementation: /Users/timotheerebours/PersonalProjects/louis-file/src/ctrk_parser.py (lines 600-950)
- Parser foundation: /Users/timotheerebours/PersonalProjects/louis-file/parser/src/
- Format specification: /Users/timotheerebours/PersonalProjects/louis-file/docs/CTRK_FORMAT_SPECIFICATION.md

REQUIREMENTS:
1. Create CTRKParser class with constructor(data: Uint8Array) and parse() method
2. Implement timestamp computation (GetTimeData and GetTimeDataEx)
3. Implement NMEA GPS parser (GPRMC sentence with checksum validation)
4. Implement main parsing loop (14-byte record headers, type dispatch)
5. Implement 100ms emission logic with GPS gating
6. Implement lap detection via finish line crossing
7. Implement fuel accumulator with per-lap reset
8. Handle state management (zero-order hold for CAN channels)

TIMESTAMP COMPUTATION:
- GetTimeData: Full timestamp from 10-byte timestamp field (bytes 0-9 of record header)
- GetTimeDataEx: Incremental update for same-second records (reuse YYYY-MM-DD HH:MM:SS, update millis)
- Handle millis wrapping: If new_millis < prev_millis, add 1000ms compensation

GPS PARSING:
- Parse GPRMC sentence: $GPRMC,HHMMSS.sss,A,DDMM.MMMM,N,DDDMM.MMMM,E,speed_knots,...*checksum
- Validate checksum (XOR of bytes between $ and *)
- Convert degrees-minutes to decimal degrees
- Handle status A (active) vs V (void)

EMISSION LOGIC:
- Initialize emission clock at first record
- Set has_gprmc flag when first valid GPRMC is received
- Emit initial record immediately after has_gprmc = true
- Emit subsequent records every 100ms (epoch_ms >= last_emitted_ms + 100)
- Emit final record after parsing loop ends

LAP DETECTION:
- Use FinishLine.crosses_line method with current and previous GPS positions
- Increment lap counter on crossing
- Reset fuel accumulator on crossing

DELIVERABLES:
- parser/src/ctrk-parser.ts with CTRKParser class
- parser/src/timestamp.ts with GetTimeData and GetTimeDataEx
- parser/src/nmea-parser.ts with GPRMC parsing and checksum validation
- Unit tests for timestamp computation (known timestamps)
- Unit tests for GPS parsing (known GPRMC sentences)
- Integration test that parses a small CTRK file and produces telemetry records

VERIFICATION:
- Run: npm test (all tests pass)
- Test with: /Users/timotheerebours/PersonalProjects/louis-file/input/<small-file.CTRK>
- Compare record count against Python parser output
```

**Expected Deliverables:**
- Complete CTRKParser class with parse() method
- Timestamp computation module
- NMEA GPS parser module
- All unit tests passing
- Integration test parsing a real CTRK file

**Verification Criteria:**
- `npm test` passes all tests
- Parser produces telemetry records for a test CTRK file
- Record count matches Python parser (within ±1% tolerance)

---

#### Step 2.2: Code Review - Parser Core Logic

**Agent:** `review`
**Dependencies:** Step 2.1
**Estimated Turns:** 10-15

**Prompt:**

```
Review the TypeScript parser core logic in /Users/timotheerebours/PersonalProjects/louis-file/parser/src/ctrk-parser.ts.

REVIEW FOCUS:
1. Timestamp computation - Verify GetTimeData and GetTimeDataEx match Python implementation exactly
2. GPS parsing - Check GPRMC checksum validation and coordinate conversion
3. Emission logic - Verify 100ms timing and GPS gating
4. Lap detection - Confirm finish line crossing algorithm is correct
5. State management - Ensure CAN state is carried forward correctly (zero-order hold)
6. Edge cases - Verify handling of empty files, files with no GPS, millis wrapping

SPECIFIC CHECKS:
- Timestamp millis wrapping compensation (+1000ms when new_millis < prev_millis)
- GPS checksum validation (XOR of bytes between $ and *)
- Emission clock initialization and 100ms interval enforcement
- Fuel accumulator reset on lap crossing
- End-of-data detection (all 5 conditions)

COMPARE AGAINST PYTHON:
- Read: /Users/timotheerebours/PersonalProjects/louis-file/src/ctrk_parser.py
- Verify timestamp logic matches lines 450-550
- Verify GPS parsing matches lines 350-400
- Verify emission logic matches lines 750-850

OUTPUT:
- List of issues found (blocking vs non-blocking)
- Confirmation that logic matches Python parser
- Approval to proceed to Epic 3 validation phase
```

**Expected Deliverables:**
- Code review report with findings
- Confirmation that core logic matches Python implementation
- Approval to proceed to validation

**Verification Criteria:**
- No blocking issues identified
- Timestamp and GPS logic verified
- Emission and lap detection logic approved

---

### Phase 3: TypeScript Parser Validation (Epic 3)

**Duration:** 2-3 days | **Agent Invocations:** 3

---

#### Step 3.1: Build Validation Test Suite

**Agent:** `dev`
**Epic:** Epic 3 (Tasks 3.1-3.2)
**Dependencies:** Step 2.2 approved
**Estimated Turns:** 20-25

**Prompt:**

```
Build a comprehensive validation test suite that compares the TypeScript parser output against the Python parser output.

CONTEXT:
- Python parser: /Users/timotheerebours/PersonalProjects/louis-file/src/ctrk_parser.py
- Python CLI: /Users/timotheerebours/PersonalProjects/louis-file/ctrk-exporter parse
- Test data: /Users/timotheerebours/PersonalProjects/louis-file/input/*.CTRK
- Comparison methodology: /Users/timotheerebours/PersonalProjects/louis-file/docs/COMPARISON.md

REQUIREMENTS:
1. Select 10-15 representative CTRK files from input/ directory
2. Generate Python CSV output for all test files (./ctrk-exporter parse <files>)
3. Copy test files to parser/test-data/ directory
4. Build Node.js comparison script that:
   - Parses CTRK files with TypeScript parser
   - Loads corresponding Python CSV as ground truth
   - Aligns records by index (same record count expected)
   - Compares all 22 channels with appropriate tolerances
   - Computes per-channel match rates
   - Computes per-file match rates
   - Generates JSON report with statistics

COMPARISON TOLERANCES (from docs/COMPARISON.md):
- rpm: ±2 RPM
- throttle, throttle_grip: ±0.5%
- front_speed_kmh, rear_speed_kmh, gps_speed_kmh: ±0.5 km/h
- gear: exact match
- acc_x_g, acc_y_g: ±0.02 G
- lean_deg, pitch_deg_s: ±0.5°
- water_temp, intake_temp: ±0.5°C
- fuel_cc: ±0.05 cc
- front_brake_bar, rear_brake_bar: ±0.1 bar
- Boolean channels (f_abs, r_abs, tcs, scs, lif, launch): exact match

SUCCESS CRITERIA:
- Overall match rate >= 95%
- Per-channel match rates:
  - RPM >= 82% (known emission grid offset)
  - All other channels >= 90%

DELIVERABLES:
- parser/test-data/ directory with 10-15 CTRK files and Python CSV outputs
- parser/test-data/README.md documenting test files
- parser/test/comparison-suite.ts with comparison logic
- parser/test/validation.test.ts with automated thresholds
- JSON report: parser/test-results/validation-report.json

VERIFICATION:
- Run: npm test
- Check: validation-report.json shows >= 95% overall match rate
```

**Expected Deliverables:**
- Test data directory with 10-15 CTRK files and Python CSV outputs
- Comparison framework that validates TS vs Python output
- JSON validation report with match rates

**Verification Criteria:**
- Test suite runs successfully
- Validation report generated
- Overall match rate calculated (target: >= 95%)

---

#### Step 3.2: QA Validation and Edge Case Testing

**Agent:** `qa`
**Epic:** Epic 3 (Tasks 3.3-3.4)
**Dependencies:** Step 3.1
**Estimated Turns:** 15-20

**Prompt:**

```
Execute the validation test suite and perform comprehensive edge case testing for the TypeScript parser.

CONTEXT:
- Validation suite: /Users/timotheerebours/PersonalProjects/louis-file/parser/test/validation.test.ts
- Test data: /Users/timotheerebours/PersonalProjects/louis-file/parser/test-data/
- Target: 95%+ overall match rate against Python parser

TASKS:
1. Run the validation test suite (npm test)
2. Analyze validation report (parser/test-results/validation-report.json)
3. Identify channels with match rates below threshold
4. Create edge case test suite:
   - Empty CTRK files (zero records)
   - Files with no GPS (should produce zero output records)
   - Files with default date (2000-01-01)
   - Files with millis wrapping
   - Files with missing finish line (all records lap 1)
   - Files with single lap
   - Files with 10+ laps
5. Document any failures with specific examples
6. Test performance: Parse a 10MB file and measure time (target: <5 seconds)

SUCCESS CRITERIA:
- Overall match rate >= 95%
- RPM match rate >= 82%
- All other channels >= 90%
- All edge cases match Python behavior
- 10MB file parses in < 5 seconds

DELIVERABLES:
- parser/test/edge-cases.test.ts with comprehensive edge case tests
- parser/test-results/qa-validation-report.md with findings
- Performance benchmark results
- List of any blocking issues for dev team

VERIFICATION:
- All tests pass or failures are documented with root cause
- Performance meets target
- Edge cases behave identically to Python parser
```

**Expected Deliverables:**
- Edge case test suite
- QA validation report with match rates and findings
- Performance benchmark results
- List of issues (if any)

**Verification Criteria:**
- Overall match rate >= 95%
- All edge cases tested
- Performance target met (<5 seconds for 10MB file)
- Pass/fail decision on parser readiness

---

#### Step 3.3: Documentation - Parser Validation Report

**Agent:** `doc`
**Epic:** Epic 3 (Task 3.5)
**Dependencies:** Step 3.2
**Estimated Turns:** 8-10

**Prompt:**

```
Document the TypeScript parser validation results and create comprehensive parser documentation.

CONTEXT:
- Validation report: /Users/timotheerebours/PersonalProjects/louis-file/parser/test-results/qa-validation-report.md
- Python parser: /Users/timotheerebours/PersonalProjects/louis-file/src/ctrk_parser.py
- Format spec: /Users/timotheerebours/PersonalProjects/louis-file/docs/CTRK_FORMAT_SPECIFICATION.md

REQUIREMENTS:
Create /Users/timotheerebours/PersonalProjects/louis-file/docs/TYPESCRIPT_PARSER.md with:

1. Overview - Purpose and scope of TypeScript parser
2. Architecture - High-level design and component structure
3. Validation Results - Match rates from QA validation report
4. Known Differences - Any intentional divergences from Python parser
5. Usage Examples - How to use the parser API
6. Browser Compatibility - Supported browsers and limitations
7. Performance Characteristics - Parse time for different file sizes
8. Testing Methodology - How validation was performed
9. References - Links to format spec, Python parser, validation report

CONTENT REQUIREMENTS:
- Include validation statistics (overall match rate, per-channel rates)
- Document any known issues or limitations
- Provide code examples for basic usage
- Link to comparison methodology from docs/COMPARISON.md
- Note that parser uses permissive licenses only

DELIVERABLES:
- docs/TYPESCRIPT_PARSER.md (new file)
- Update docs/CTRK_FORMAT_SPECIFICATION.md to reference TypeScript parser
- Update README.md to mention TypeScript parser

VERIFICATION:
- All links are valid
- Code examples are syntactically correct
- Validation statistics match QA report
```

**Expected Deliverables:**
- docs/TYPESCRIPT_PARSER.md with complete documentation
- Updated references in other documentation files

**Verification Criteria:**
- Documentation is complete and accurate
- Validation results clearly presented
- Usage examples are clear

---

### Phase 4: Astro Integration Package (Epic 4)

**Duration:** 1 day | **Agent Invocations:** 2

---

#### Step 4.1: Build Astro Integration Package

**Agent:** `dev`
**Epic:** Epic 4 (Tasks 4.1-4.4)
**Dependencies:** Epic 3 complete (parser validated)
**Estimated Turns:** 20-25

**Prompt:**

```
Create an Astro integration package that wraps the TypeScript CTRK parser and provides Vue.js components for easy integration.

CONTEXT:
- Parser: /Users/timotheerebours/PersonalProjects/louis-file/parser/
- Target: Package as reusable Astro integration with Vue components
- Must support client-side only (no SSR for parser)

REQUIREMENTS:
1. Create new package at /Users/timotheerebours/PersonalProjects/louis-file/astro-integration/
2. Setup package.json with:
   - name: @ctrk-exporter/astro-integration
   - Proper exports (parser, components, composables)
   - Dependencies: @astrojs/vue, parser package
3. Create Astro integration configuration
4. Re-export parser from parser package
5. Create browser utilities (File to Uint8Array conversion)
6. Create Vue composables:
   - useTelemetryData (reactive telemetry state)
   - useParserStatus (loading, error, progress)
7. Create example Astro project demonstrating integration

CRITICAL CONSTRAINTS:
- All third-party dependencies MUST use permissive licenses (MIT, BSD, ISC, Apache 2.0)
- Verify @astrojs/vue and all transitive dependencies have compatible licenses
- Parser must run client-side only (client:only="vue" directive)

FILE STRUCTURE:
```
astro-integration/
├── package.json
├── tsconfig.json
├── README.md
├── src/
│   ├── integration.ts       # Astro integration entry point
│   ├── index.ts             # Main exports
│   ├── parser.ts            # Parser re-exports
│   ├── types.ts             # TypeScript types
│   ├── utils.ts             # Browser utilities
│   └── composables/
│       ├── useTelemetryData.ts
│       └── useParserStatus.ts
└── examples/
    └── basic/               # Example Astro project
        ├── package.json
        ├── astro.config.mjs
        └── src/
            └── pages/
                └── index.astro
```

DELIVERABLES:
- astro-integration/ package with complete integration
- examples/basic/ with working demo
- astro-integration/README.md with installation and usage instructions
- Verified license compatibility for all dependencies

VERIFICATION:
- cd astro-integration/examples/basic && npm install && npm run dev
- Integration loads without errors
- License check passes for all dependencies
```

**Expected Deliverables:**
- Complete Astro integration package
- Vue composables for state management
- Example project demonstrating usage
- All dependencies using permissive licenses

**Verification Criteria:**
- Example project runs successfully
- Integration can be imported and used
- License compliance verified
- README provides clear usage instructions

---

#### Step 4.2: Code Review - Astro Integration

**Agent:** `review`
**Dependencies:** Step 4.1
**Estimated Turns:** 8-10

**Prompt:**

```
Review the Astro integration package created in /Users/timotheerebours/PersonalProjects/louis-file/astro-integration/.

REVIEW FOCUS:
1. Package configuration - Check exports, dependencies, build setup
2. Integration setup - Verify Astro integration hooks and Vue configuration
3. Composables - Review Vue composables for reactive state management
4. Browser compatibility - Ensure no Node.js APIs in browser code
5. License compliance - Verify all dependencies use permissive licenses
6. Documentation - Check README for completeness and accuracy
7. Example project - Test that example runs and demonstrates features

SPECIFIC CHECKS:
- Parser is only imported in client-side code (client:only="vue")
- File to Uint8Array conversion works in browser
- Composables use Vue 3 Composition API correctly
- TypeScript types are properly exported
- Example project can install and run without errors

OUTPUT:
- List of issues found
- Verification that integration is ready for use in Epic 5
- License compliance confirmation
```

**Expected Deliverables:**
- Code review report with findings
- Confirmation of readiness for Epic 5

**Verification Criteria:**
- No blocking issues
- License compliance confirmed
- Example project functional

---

### Phase 5: File Upload and Visualization Components (Epics 5-8)

**Duration:** 7-10 days | **Agent Invocations:** 5

This phase runs Epics 5, 6, 7, and 8 in sequence. Epics 6, 7, 8 can partially overlap once Epic 5 is complete.

---

#### Step 5.1: Build File Upload Component

**Agent:** `dev`
**Epic:** Epic 5 (Tasks 5.1-5.4)
**Dependencies:** Step 4.2 approved
**Estimated Turns:** 20-25

**Prompt:**

```
Create a Vue.js file upload component with drag-and-drop support, file validation, and parser integration.

CONTEXT:
- Astro integration: /Users/timotheerebours/PersonalProjects/louis-file/astro-integration/
- Must parse CTRK files in Web Worker to avoid blocking UI
- Must use composables from astro-integration for state management

REQUIREMENTS:
1. Create FileUpload.vue component with:
   - Drag-and-drop zone with visual feedback
   - File picker button fallback
   - File extension validation (.CTRK only)
   - Magic byte validation (HEAD)
   - File size limits (100 bytes - 50 MB)
2. Create file-validator.ts utility
3. Create parser Web Worker (parser-worker.ts)
4. Integrate with useTelemetryData composable
5. Show progress during parsing
6. Handle errors gracefully with Toast notifications
7. Create Toast.vue component for notifications

CRITICAL CONSTRAINTS:
- All UI libraries (if any) MUST use permissive licenses
- If using a UI component library, verify license before installation
- Parser runs in Web Worker (non-blocking)

FILE STRUCTURE:
```
astro-integration/src/
├── components/
│   ├── FileUpload.vue
│   ├── FileUpload.css
│   └── Toast.vue
├── workers/
│   └── parser-worker.ts
└── lib/
    └── file-validator.ts
```

PARSER INTEGRATION:
1. User drops file
2. Validate magic bytes (HEAD)
3. Read File as ArrayBuffer
4. Convert to Uint8Array
5. Send to Web Worker
6. Worker instantiates CTRKParser
7. Worker calls parse() and returns records
8. Main thread updates useTelemetryData composable
9. Navigate to /analyze page (or show results)

DELIVERABLES:
- FileUpload.vue with drag-and-drop and validation
- parser-worker.ts for non-blocking parsing
- file-validator.ts with magic byte and size checks
- Toast.vue for error notifications
- Integration with useTelemetryData composable

VERIFICATION:
- Drop a CTRK file from /Users/timotheerebours/PersonalProjects/louis-file/input/
- Verify parser runs without blocking UI
- Check that telemetry records are stored in composable
- Test error cases (invalid file, no magic bytes, file too large)
```

**Expected Deliverables:**
- Complete FileUpload.vue component
- Web Worker for parsing
- File validation utilities
- Toast notification component

**Verification Criteria:**
- User can drag-and-drop CTRK files
- Parsing runs in Web Worker (non-blocking)
- Errors are handled gracefully
- Telemetry data stored in reactive state

---

#### Step 5.2: Build GPS Track Map Visualization

**Agent:** `dev`
**Epic:** Epic 6 (Tasks 6.1-6.4)
**Dependencies:** Step 5.1
**Estimated Turns:** 25-30

**Prompt:**

```
Create an interactive GPS track map visualization using Leaflet.js and Vue.js.

CONTEXT:
- Astro integration: /Users/timotheerebours/PersonalProjects/louis-file/astro-integration/
- Telemetry data from useTelemetryData composable
- Must display GPS track with laps colored by lap number

REQUIREMENTS:
1. Install Leaflet.js (verify MIT license)
2. Create TrackMap.vue component with:
   - Leaflet map initialization
   - OpenStreetMap tiles (or similar free tile provider)
   - GPS polyline rendering (one per lap)
   - Lap color palette (10+ distinct colors)
   - Lap markers at finish line crossings
   - Click interactions (select lap)
   - Zoom/pan controls
   - Fit-to-track button
3. Create MapLegend.vue component
4. Create gps-utils.ts with:
   - Filter sentinel GPS values (9999.0)
   - Polyline simplification for performance (>10,000 points)
   - Lap segmentation

CRITICAL CONSTRAINTS:
- Leaflet.js is MIT licensed (verify before installation)
- Tile provider must be free and open (OpenStreetMap, Mapbox with free tier, etc.)
- No paid map APIs

VISUALIZATION FEATURES:
- Each lap rendered as a separate polyline with distinct color
- Markers at start of each lap with lap number label
- Clickable laps to select (emit event to parent)
- Synchronize with useTelemetryData composable (selectedLap ref)
- Legend showing lap colors and lap times

FILE STRUCTURE:
```
astro-integration/src/
├── components/
│   ├── TrackMap.vue
│   ├── TrackMap.css
│   └── MapLegend.vue
└── lib/
    └── gps-utils.ts
```

DELIVERABLES:
- TrackMap.vue with Leaflet integration
- MapLegend.vue with lap colors
- gps-utils.ts with GPS utilities
- Integration with useTelemetryData composable

VERIFICATION:
- Load a CTRK file with GPS data
- Verify map displays GPS track
- Check that laps are colored differently
- Test click interaction to select lap
- Verify performance with large tracks (>10,000 points)
```

**Expected Deliverables:**
- Complete TrackMap.vue component
- Interactive map with lap visualization
- GPS utilities for data processing

**Verification Criteria:**
- Map displays GPS track correctly
- Laps colored distinctly
- Click interactions work
- Performance acceptable for large tracks

---

#### Step 5.3: Build Telemetry Graph Visualization

**Agent:** `dev`
**Epic:** Epic 7 (Tasks 7.1-7.5)
**Dependencies:** Step 5.1
**Estimated Turns:** 30-35

**Prompt:**

```
Create an interactive multi-channel telemetry graph visualization using Chart.js or Plotly.js and Vue.js.

CONTEXT:
- Astro integration: /Users/timotheerebours/PersonalProjects/louis-file/astro-integration/
- Telemetry data from useTelemetryData composable
- Must display all 22 channels in stacked subplots
- Reference: /Users/timotheerebours/PersonalProjects/louis-file/src/visualize_all_channels.py

REQUIREMENTS:
1. Evaluate and choose chart library:
   - Chart.js: MIT license, simpler but less features
   - Plotly.js: MIT license, more features but larger bundle
   - Decision criteria: performance with 20,000+ points, bundle size, features
2. Create TelemetryChart.vue component with:
   - Stacked multi-channel layout (8-10 subplots)
   - Shared X-axis (time in seconds or lap time)
   - Auto-scaling Y-axes per channel
   - Color scheme matching visualize_all_channels.py
   - Zoom/pan interactions
   - Hover tooltip showing all channel values
   - Lap selection filter
   - Channel selection (show/hide channels)
3. Create LapSelector.vue component
4. Create ChannelSelector.vue component
5. Create chart-config.ts with channel groupings and colors

CRITICAL CONSTRAINTS:
- Chosen chart library MUST use MIT license (both Chart.js and Plotly.js are MIT)
- Optimize for performance (lazy rendering, virtualization if needed)
- Bundle size should be reasonable (<500KB for chart library)

CHANNEL GROUPING (matching Python visualization):
1. Engine: RPM, Throttle (TPS), Throttle Grip (APS), Gear
2. Speed: Front Speed, Rear Speed, GPS Speed
3. Chassis: Lean Angle, Pitch Rate
4. Acceleration: Acc X, Acc Y
5. Brakes: Front Brake, Rear Brake
6. Temperature: Water Temp, Intake Temp
7. Fuel: Fuel Level
8. Electronics: TCS, SCS, LIF, Launch, F_ABS, R_ABS

VISUALIZATION FEATURES:
- Stacked subplots with shared X-axis
- Lap filtering (show all laps, single lap, or lap comparison)
- Zoom/pan synchronized across all subplots
- Hover shows vertical line across all subplots with values
- Channel selector to show/hide individual channels
- Export view as PNG

FILE STRUCTURE:
```
astro-integration/src/
├── components/
│   ├── TelemetryChart.vue
│   ├── TelemetryChart.css
│   ├── LapSelector.vue
│   └── ChannelSelector.vue
└── lib/
    └── chart-config.ts
```

DELIVERABLES:
- TelemetryChart.vue with multi-channel graphs
- LapSelector.vue for lap filtering
- ChannelSelector.vue for channel visibility
- chart-config.ts with colors and groupings
- Integration with useTelemetryData composable

VERIFICATION:
- Load a CTRK file with multiple laps
- Verify all 22 channels display correctly
- Test lap selection and filtering
- Test zoom/pan interactions
- Verify performance with 20,000+ records
```

**Expected Deliverables:**
- Complete TelemetryChart.vue component
- Multi-channel graph with stacked layout
- Lap and channel selection components

**Verification Criteria:**
- All 22 channels display correctly
- Lap filtering works
- Zoom/pan interactions smooth
- Performance acceptable for large datasets

---

#### Step 5.4: Build Lap Timing Summary

**Agent:** `dev`
**Epic:** Epic 8 (Tasks 8.1-8.4)
**Dependencies:** Step 5.1
**Estimated Turns:** 15-20

**Prompt:**

```
Create a lap timing summary component with lap times, deltas, and export functionality.

CONTEXT:
- Astro integration: /Users/timotheerebours/PersonalProjects/louis-file/astro-integration/
- Telemetry data from useTelemetryData composable
- Lap times computed from first record of lap N to first record of lap N+1

REQUIREMENTS:
1. Create lap-timing.ts utility with:
   - Compute lap times from telemetry records
   - Format as MM:SS.sss
   - Compute delta to best lap
   - Compute session statistics (avg, std dev)
2. Create LapTimingTable.vue component with:
   - Table showing lap number, time, delta to best
   - Highlight best lap (green)
   - Clickable rows to select lap
   - Sort by lap number or time
   - Export to CSV button
3. Create SessionSummary.vue component with:
   - Total laps, total time, average lap time
   - Best lap time and lap number
   - Consistency metric (std dev)
4. Create export-utils.ts with CSV export function

FILE STRUCTURE:
```
astro-integration/src/
├── components/
│   ├── LapTimingTable.vue
│   ├── LapTimingTable.css
│   └── SessionSummary.vue
└── lib/
    ├── lap-timing.ts
    └── export-utils.ts
```

LAP TIME COMPUTATION:
- Lap N start: First record with lap = N
- Lap N end: First record with lap = N+1 (or last record if final lap)
- Lap time = end_timestamp - start_timestamp

DELIVERABLES:
- lap-timing.ts with computation logic
- LapTimingTable.vue with table and export
- SessionSummary.vue with statistics
- export-utils.ts with CSV export

VERIFICATION:
- Load a CTRK file with multiple laps
- Verify lap times are computed correctly
- Check that best lap is highlighted
- Test CSV export
- Verify clicking row selects lap (syncs with map/chart)
```

**Expected Deliverables:**
- Complete LapTimingTable.vue component
- SessionSummary.vue component
- Lap timing computation utilities
- CSV export functionality

**Verification Criteria:**
- Lap times computed correctly
- Best lap highlighted
- CSV export works
- Row click selects lap

---

#### Step 5.5: Code Review - All Visualization Components

**Agent:** `review`
**Dependencies:** Steps 5.1-5.4
**Estimated Turns:** 15-20

**Prompt:**

```
Review all visualization components created in /Users/timotheerebours/PersonalProjects/louis-file/astro-integration/src/components/.

REVIEW FOCUS:
1. Component architecture - Check Vue Composition API usage, component structure
2. State management - Verify composables are used correctly, reactive state updates
3. Performance - Ensure no performance issues with large datasets (20,000+ records)
4. Browser compatibility - Test in Chrome, Firefox, Safari
5. License compliance - Verify all UI dependencies use permissive licenses
6. User experience - Check visual design, interactions, error handling
7. Accessibility - Basic a11y checks (keyboard navigation, focus indicators)

SPECIFIC CHECKS:
- FileUpload: Parser runs in Web Worker, file validation works
- TrackMap: Leaflet integration correct, GPS data filtered properly
- TelemetryChart: Chart library performs well, lap filtering works
- LapTimingTable: Lap time computation accurate, CSV export functional
- All components use useTelemetryData composable correctly
- No memory leaks (components clean up on unmount)

TEST SCENARIOS:
1. Upload a CTRK file with multiple laps
2. Verify map, chart, and table all update correctly
3. Select a lap on map -> chart and table should update
4. Select a lap in table -> map and chart should update
5. Export CSV and verify format
6. Test with large file (>10,000 records)

OUTPUT:
- List of issues found (blocking vs non-blocking)
- Performance assessment
- License compliance confirmation
- Approval to proceed to Epic 9 or list of required fixes
```

**Expected Deliverables:**
- Code review report with findings
- Performance assessment
- Confirmation of readiness for Epic 9

**Verification Criteria:**
- No blocking issues
- Performance acceptable
- License compliance confirmed

---

### Phase 6: Integration and Polish (Epic 9)

**Duration:** 2-3 days | **Agent Invocations:** 6

---

#### Step 6.1: End-to-End Testing

**Agent:** `qa`
**Epic:** Epic 9 (Task 9.1)
**Dependencies:** Step 5.5 approved
**Estimated Turns:** 15-20

**Prompt:**

```
Perform comprehensive end-to-end testing of the web application with real CTRK files.

CONTEXT:
- Web app: /Users/timotheerebours/PersonalProjects/louis-file/astro-integration/
- Test data: /Users/timotheerebours/PersonalProjects/louis-file/input/*.CTRK (47 files)

TEST SCENARIOS:
1. File upload flow:
   - Drag-and-drop file
   - Click file picker
   - Upload invalid file (error handling)
   - Upload empty file
   - Upload file with no GPS
   - Upload very large file (>10 MB)
2. GPS track map:
   - Map renders correctly for all files
   - Laps colored correctly
   - Click lap to select
   - Zoom/pan interactions
3. Telemetry graph:
   - All 22 channels render
   - Lap selection works
   - Channel show/hide works
   - Zoom/pan interactions
4. Lap timing table:
   - Lap times correct
   - Best lap highlighted
   - CSV export works
5. Component synchronization:
   - Select lap on map -> chart and table update
   - Select lap in table -> map and chart update
   - Select lap in chart -> map and table update

TEST WITH:
- Small files (100-500 records)
- Medium files (5,000-10,000 records)
- Large files (15,000-24,000 records)
- Files from different tracks
- Files with different lap counts (1, 5, 10+ laps)

DELIVERABLES:
- astro-integration/test/e2e/upload-flow.test.ts (if using Playwright/Cypress)
- astro-integration/test/e2e/visualization.test.ts (if using Playwright/Cypress)
- QA test report with findings (markdown)
- List of bugs found with reproduction steps

VERIFICATION:
- All test scenarios pass or failures documented
- Report includes pass/fail for each scenario
- Bugs prioritized by severity
```

**Expected Deliverables:**
- E2E test suite (if automated)
- QA test report with findings
- List of bugs (if any)

**Verification Criteria:**
- All critical scenarios pass
- Bugs documented with reproduction steps
- Report includes coverage summary

---

#### Step 6.2: Performance Profiling and Optimization

**Agent:** `dev`
**Epic:** Epic 9 (Task 9.2)
**Dependencies:** Step 6.1
**Estimated Turns:** 20-25

**Prompt:**

```
Profile and optimize the web application for performance.

CONTEXT:
- Web app: /Users/timotheerebours/PersonalProjects/louis-file/astro-integration/
- Target: Parse 10MB file in <5 seconds
- Target: Time to Interactive (TTI) <3 seconds

PROFILING TASKS:
1. Profile parser with Chrome DevTools Performance tab
   - Measure parse time for 1MB, 5MB, 10MB files
   - Identify hot paths (timestamp computation, CAN decoding, etc.)
   - Optimize critical functions
2. Profile Web Worker overhead
   - Measure time to transfer data to worker
   - Measure worker initialization time
3. Profile chart rendering
   - Measure time to render 20,000+ data points
   - Test virtualization or downsampling if needed
4. Profile bundle size
   - Run: npm run build
   - Check bundle size (target: <500KB gzipped for main app)
   - Lazy-load heavy components (map, chart)
5. Measure web vitals
   - Install web-vitals library (MIT license)
   - Measure FCP, LCP, TTI, CLS, FID

OPTIMIZATION OPPORTUNITIES:
- Parser: Optimize hot loops, use typed arrays efficiently
- Worker: Use transferable objects (ArrayBuffer transfer)
- Chart: Downsample data if >20,000 points (keep every Nth point)
- Map: Simplify polyline if >10,000 points (Douglas-Peucker algorithm)
- Bundle: Code-split, lazy-load, tree-shake

DELIVERABLES:
- astro-integration/src/lib/performance.ts with web-vitals monitoring
- Optimization applied to critical paths
- Performance report (markdown) with before/after metrics
- Bundle size report

VERIFICATION:
- Parse 10MB file in <5 seconds
- Bundle size <500KB gzipped
- Web vitals meet targets (FCP <1.5s, LCP <2.5s, TTI <3s)
```

**Expected Deliverables:**
- Performance optimizations applied
- Performance report with metrics
- Bundle size optimized

**Verification Criteria:**
- 10MB file parses in <5 seconds
- Bundle size <500KB gzipped
- Web vitals meet targets

---

#### Step 6.3: Responsive Design

**Agent:** `dev`
**Epic:** Epic 9 (Task 9.3)
**Dependencies:** Step 6.1
**Estimated Turns:** 15-20

**Prompt:**

```
Implement responsive design for mobile and tablet devices.

CONTEXT:
- Web app: /Users/timotheerebours/PersonalProjects/louis-file/astro-integration/
- Target: Work on mobile (375px), tablet (768px), desktop (1920px)

REQUIREMENTS:
1. Update all component CSS for responsive breakpoints
2. Test layouts on different screen sizes:
   - Mobile: 375px x 667px (iPhone SE)
   - Tablet: 768px x 1024px (iPad)
   - Desktop: 1920px x 1080px
3. Adjust component layouts:
   - FileUpload: Full-width on mobile
   - TrackMap: Stack above chart on mobile
   - TelemetryChart: Reduce subplot count on mobile (show fewer channels)
   - LapTimingTable: Horizontal scroll on mobile
4. Make interactions touch-friendly:
   - Increase tap target sizes (44px minimum)
   - Test gestures (pinch-zoom on map)
5. Test on real devices (iOS Safari, Android Chrome)

RESPONSIVE BREAKPOINTS:
- Mobile: < 640px
- Tablet: 640px - 1024px
- Desktop: > 1024px

DELIVERABLES:
- astro-integration/src/styles/responsive.css with breakpoint styles
- Updated component CSS with media queries
- Test report for different devices/browsers

VERIFICATION:
- Test on Chrome DevTools device emulation (all breakpoints)
- Test on real iOS and Android devices (if available)
- All components usable on mobile
```

**Expected Deliverables:**
- Responsive CSS for all components
- Touch-friendly interactions
- Device testing report

**Verification Criteria:**
- Components work on mobile, tablet, desktop
- Touch interactions functional
- Layouts adapt correctly

---

#### Step 6.4: Accessibility (a11y)

**Agent:** `dev`
**Epic:** Epic 9 (Task 9.4)
**Dependencies:** Step 6.1
**Estimated Turns:** 15-20

**Prompt:**

```
Implement accessibility improvements for WCAG AA compliance.

CONTEXT:
- Web app: /Users/timotheerebours/PersonalProjects/louis-file/astro-integration/
- Target: WCAG 2.1 Level AA compliance

REQUIREMENTS:
1. Add ARIA labels to all interactive elements:
   - Buttons, links, form inputs
   - Map markers, chart points
   - Table rows
2. Ensure keyboard navigation works:
   - Tab through all interactive elements
   - Enter/Space to activate buttons
   - Arrow keys for table navigation
   - Escape to close modals/dialogs
3. Test with screen reader:
   - Use NVDA (Windows) or VoiceOver (macOS)
   - Ensure all content is announced
   - Check reading order
4. Add focus indicators:
   - Visible outline on focus (2px solid)
   - Contrast ratio >= 3:1
5. Ensure color contrast:
   - Text: >= 4.5:1 (WCAG AA)
   - Large text: >= 3:1
   - Check with Chrome DevTools color picker
6. Add skip-to-content link
7. Run axe-core or Lighthouse accessibility audit

DELIVERABLES:
- astro-integration/src/styles/accessibility.css with focus and contrast styles
- ARIA labels added to all components
- Keyboard navigation implemented
- Accessibility audit report

VERIFICATION:
- Run: Lighthouse accessibility audit (score >= 90)
- Test keyboard navigation (no mouse)
- Test with screen reader
```

**Expected Deliverables:**
- ARIA labels on all interactive elements
- Keyboard navigation functional
- Focus indicators visible
- Accessibility audit report

**Verification Criteria:**
- Lighthouse accessibility score >= 90
- Keyboard navigation works
- Screen reader announces content correctly

---

#### Step 6.5: Production Build and Deployment

**Agent:** `dev`
**Epic:** Epic 9 (Task 9.6)
**Dependencies:** Steps 6.2, 6.3, 6.4
**Estimated Turns:** 10-15

**Prompt:**

```
Create production build and deployment configuration.

CONTEXT:
- Web app: /Users/timotheerebours/PersonalProjects/louis-file/astro-integration/
- Target: Deploy to Netlify or Vercel as static site

REQUIREMENTS:
1. Create production build configuration:
   - Astro build settings (static mode)
   - Minification, tree-shaking enabled
   - Source maps for debugging
2. Create deployment configuration:
   - netlify.toml or vercel.json
   - Build command: npm run build
   - Output directory: dist/
3. Setup environment variables (if needed)
4. Test production build locally:
   - npm run build
   - npm run preview
5. Deploy to staging environment
6. Run smoke tests on deployed site:
   - Upload CTRK file
   - Verify visualization works
   - Check performance (Lighthouse)
7. (Optional) Setup custom domain
8. (Optional) Add privacy-focused analytics (Plausible, Fathom)

DELIVERABLES:
- astro-integration/netlify.toml or vercel.json
- Production build tested locally
- Deployed to staging environment
- Smoke test report

VERIFICATION:
- Production build succeeds (npm run build)
- Deployed site accessible
- CTRK file upload and visualization work
- Lighthouse score >90 on all metrics
```

**Expected Deliverables:**
- Production build configuration
- Deployment configuration
- Deployed staging site
- Smoke test report

**Verification Criteria:**
- Production build succeeds
- Site deployed and accessible
- Core functionality works on deployed site
- Lighthouse score >90

---

#### Step 6.6: User Documentation

**Agent:** `doc`
**Epic:** Epic 9 (Task 9.7)
**Dependencies:** Step 6.5
**Estimated Turns:** 10-15

**Prompt:**

```
Create comprehensive user documentation for the web application.

CONTEXT:
- Web app: Deployed at <staging-url>
- Target audience: Motorcyclists using Y-Trac data logger

REQUIREMENTS:
Create user guide at /Users/timotheerebours/PersonalProjects/louis-file/docs/WEB_USER_GUIDE.md with:

1. Overview - What is CTRK-Exporter Web Edition
2. Getting Started - How to use the web app
3. Uploading Files - Step-by-step instructions
4. GPS Track Map - How to use the map, select laps
5. Telemetry Graphs - How to read graphs, select channels
6. Lap Timing - How to use the timing table, export CSV
7. Supported Browsers - Browser compatibility matrix
8. Limitations - File size limits, known issues
9. FAQ - Common questions and troubleshooting
10. Privacy - Clarify that files are processed locally (no upload to server)

CONTENT REQUIREMENTS:
- Include screenshots of each major feature
- Provide step-by-step tutorials
- List supported browsers and versions
- Document keyboard shortcuts
- Explain privacy/security (client-side only)
- Link to format specification and GitHub repo

DELIVERABLES:
- docs/WEB_USER_GUIDE.md (new file)
- Screenshots in docs/images/ directory
- Update README.md to link to web app
- (Optional) Create video walkthrough

VERIFICATION:
- All links are valid
- Screenshots are current
- Instructions are clear and accurate
```

**Expected Deliverables:**
- docs/WEB_USER_GUIDE.md with comprehensive guide
- Screenshots of major features
- Updated README.md

**Verification Criteria:**
- Documentation is complete and clear
- Screenshots match current UI
- Links are valid

---

### Phase 7: Final Review and Release

**Duration:** 1 day | **Agent Invocations:** 2

---

#### Step 7.1: Final Code Review

**Agent:** `review`
**Dependencies:** All Epic 9 tasks complete
**Estimated Turns:** 15-20

**Prompt:**

```
Perform final code review of the entire codebase before release.

CONTEXT:
- Parser: /Users/timotheerebours/PersonalProjects/louis-file/parser/
- Integration: /Users/timotheerebours/PersonalProjects/louis-file/astro-integration/
- Web app: Deployed at <staging-url>

REVIEW FOCUS:
1. Code quality - Final check for TypeScript errors, linting issues
2. Test coverage - Verify all critical paths tested
3. License compliance - Final verification of all dependencies
4. Documentation - Check that all documentation is current
5. Performance - Verify optimization targets met
6. Accessibility - Confirm a11y standards met
7. Security - Check for any security issues (XSS, etc.)
8. Browser compatibility - Verify tested on all target browsers

COMPREHENSIVE CHECKS:
- Run: npm run build (parser and astro-integration)
- Run: npm test (all tests pass)
- Run: npm run lint (no errors)
- Run license checker for all dependencies
- Run Lighthouse audit on deployed site
- Verify no console errors in browser
- Check that all images/assets have appropriate licenses

DELIVERABLES:
- Final code review report
- List of any remaining issues (if any)
- Sign-off for release or list of blockers

VERIFICATION:
- All builds succeed
- All tests pass
- License compliance confirmed
- Lighthouse score >90 on all metrics
- No console errors
```

**Expected Deliverables:**
- Final code review report
- Sign-off for release or list of blockers

**Verification Criteria:**
- All builds and tests pass
- License compliance verified
- Performance and accessibility targets met
- No critical issues remaining

---

#### Step 7.2: Final Documentation Review

**Agent:** `doc`
**Dependencies:** Step 7.1
**Estimated Turns:** 8-10

**Prompt:**

```
Perform final documentation review and harmonization.

CONTEXT:
- All documentation: /Users/timotheerebours/PersonalProjects/louis-file/docs/
- README: /Users/timotheerebours/PersonalProjects/louis-file/README.md
- Parser docs: /Users/timotheerebours/PersonalProjects/louis-file/parser/README.md
- Integration docs: /Users/timotheerebours/PersonalProjects/louis-file/astro-integration/README.md

REVIEW FOCUS:
1. Consistency - Ensure all documentation is consistent and up-to-date
2. Completeness - Verify all features are documented
3. Accuracy - Check that code examples are correct
4. Links - Verify all internal and external links work
5. Structure - Ensure logical organization and navigation

SPECIFIC CHECKS:
- README.md mentions web edition and links to demo
- TYPESCRIPT_PARSER.md has current validation results
- WEB_USER_GUIDE.md matches current UI
- CTRK_FORMAT_SPECIFICATION.md referenced correctly
- All code examples are syntactically correct
- License information is accurate

DELIVERABLES:
- Updated documentation (if changes needed)
- Final documentation checklist
- Sign-off that documentation is release-ready

VERIFICATION:
- All links work
- Code examples are correct
- Version numbers consistent
- License information accurate
```

**Expected Deliverables:**
- Final documentation review report
- Updated documentation (if needed)
- Sign-off for release

**Verification Criteria:**
- All documentation current and accurate
- Links functional
- Code examples correct

---

## Parallelization Opportunities

The following steps can run in parallel to reduce overall execution time:

### Parallel Group 1: Epic 1 + Epic 4 Prep
- **Step 1.1** (Epic 1: Parser Foundation) can proceed independently
- Once Step 1.1 is 50% complete, **Epic 4 planning** can begin

### Parallel Group 2: Epics 6, 7, 8
- Once **Step 5.1** (File Upload) is complete, these epics can proceed in parallel:
  - **Step 5.2** (Epic 6: GPS Map)
  - **Step 5.3** (Epic 7: Telemetry Graph)
  - **Step 5.4** (Epic 8: Lap Timing)
- These are independent Vue components that all consume the same `useTelemetryData` composable

### Parallel Group 3: Epic 9 Polish Tasks
- **Step 6.3** (Responsive Design) and **Step 6.4** (Accessibility) can run in parallel after Step 6.1 (E2E Testing)

---

## Checkpoints (Human Review Required)

The execution plan includes mandatory checkpoints where human review is required before proceeding:

### Checkpoint 1: After Epic 3 (Parser Validation)
**Location:** After Step 3.2 (QA Validation)
**Decision:** Proceed to Epic 4 only if parser achieves >= 95% match rate

**Criteria:**
- Overall match rate >= 95%
- All edge cases tested
- Performance target met (<5 seconds for 10MB file)

**If Failed:** Return to Epic 1 or 2 to fix issues before proceeding

---

### Checkpoint 2: After Epic 5 (Core UX)
**Location:** After Step 5.5 (Code Review - Visualization)
**Decision:** Proceed to Epic 9 only if core user experience is functional

**Criteria:**
- File upload works reliably
- All components render correctly
- State synchronization works (lap selection)
- No critical bugs

**If Failed:** Fix issues in Epic 5 before proceeding to polish phase

---

### Checkpoint 3: Before Production Deployment
**Location:** After Step 6.5 (Production Build)
**Decision:** Deploy to production only if all quality checks pass

**Criteria:**
- All tests pass
- Lighthouse score >= 90 on all metrics
- License compliance verified
- Smoke tests on staging pass
- Documentation complete

**If Failed:** Address blockers before production deployment

---

## Estimated Agent Invocations

| Phase | Epic(s) | Agent Calls | Estimated Turns |
|-------|---------|-------------|-----------------|
| Phase 1 | Epic 1 | 2 (dev, review) | 35-45 |
| Phase 2 | Epic 2 | 2 (dev, review) | 35-45 |
| Phase 3 | Epic 3 | 3 (dev, qa, doc) | 43-55 |
| Phase 4 | Epic 4 | 2 (dev, review) | 28-35 |
| Phase 5 | Epics 5-8 | 5 (dev × 4, review × 1) | 105-130 |
| Phase 6 | Epic 9 | 6 (qa, dev × 3, doc) | 85-110 |
| Phase 7 | Final Review | 2 (review, doc) | 23-30 |
| **Total** | **9 Epics** | **24 invocations** | **354-450 turns** |

---

## Risk Mitigation

| Risk | Probability | Impact | Mitigation Strategy |
|------|-------------|--------|---------------------|
| Parser accuracy <95% | Medium | HIGH | Incremental validation after each epic; Checkpoint 1 prevents proceeding with low accuracy |
| Performance issues (>10s parse) | Medium | MEDIUM | Early profiling in Epic 3; Web Worker from start; Optimization phase in Epic 9 |
| Chart library performance | Low | MEDIUM | Evaluate Chart.js vs Plotly.js in Task 7.1; Downsample data if needed |
| Bundle size bloat (>1MB) | Medium | MEDIUM | Monitor bundle size after each epic; Lazy-load map and chart libraries |
| License compliance issues | Low | HIGH | Verify licenses before installing any dependency; License check in every dev prompt |
| Browser compatibility | Low | MEDIUM | Test on all target browsers in Epic 9; Use well-supported libraries |
| Responsive design issues | Low | LOW | Test on multiple devices in Epic 9; Use standard CSS Grid/Flexbox |

---

## Success Criteria

The project is considered complete and successful when:

1. **Parser Accuracy:** TypeScript parser achieves >= 95% match rate against Python parser (verified in Epic 3)
2. **Test Coverage:** >= 90% code coverage for parser core logic
3. **Performance:** Parses 10MB CTRK file in < 5 seconds
4. **User Experience:** From file drop to visualization in < 10 seconds
5. **Code Quality:** Zero TypeScript errors, ESLint clean, all tests pass
6. **Deployment:** Static site deployed to Netlify/Vercel with public URL
7. **Documentation:** User guide, API docs, and validation report complete
8. **Accessibility:** Lighthouse accessibility score >= 90 (WCAG AA compliant)
9. **Browser Support:** Works in Chrome, Firefox, Safari, Edge (last 2 versions)
10. **Lighthouse Score:** >= 90 on Performance, Accessibility, Best Practices, SEO

---

## Execution Instructions

To execute this plan:

1. **Start with Step 1.1** - Invoke the `dev` agent with the prompt from Step 1.1
2. **Follow the sequence** - Complete each step in order unless parallelization is noted
3. **Verify at checkpoints** - Human review required at Checkpoints 1, 2, and 3 before proceeding
4. **Track progress** - Mark each step complete in this document as you go
5. **Document issues** - Log any deviations or issues encountered during execution
6. **Iterate as needed** - If a step fails verification, address issues before proceeding

---

## Notes

- **Agent Turn Limits:** The `dev` agent has a 30-turn limit, other agents have 20 turns. Prompts are designed to fit within these limits.
- **License Verification:** Every dev prompt includes a reminder to verify licenses. This is critical to avoid legal issues.
- **Reference Implementation:** The Python parser at `/Users/timotheerebours/PersonalProjects/louis-file/src/ctrk_parser.py` is the source of truth for all parsing logic.
- **Test Data:** Use files from `/Users/timotheerebours/PersonalProjects/louis-file/input/` for testing throughout the project.
- **Incremental Testing:** Test each component as it's built rather than waiting for full integration.
- **Performance Monitoring:** Profile early and often to avoid performance surprises late in the project.

---

**Plan Status:** READY FOR EXECUTION
**Last Updated:** 2026-02-07
**Maintained By:** Product Manager (pm agent)
