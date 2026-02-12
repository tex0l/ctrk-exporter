# Product Backlog: Web Browser CTRK Parser

**Last Updated:** 2026-02-07
**Product:** CTRK-Exporter Web Edition
**Objective:** Build a TypeScript-based CTRK parser that runs entirely in the browser with interactive visualization

---

## Vision

Create a fully client-side web application that allows motorcyclists to drag-and-drop their CTRK telemetry files into a browser and immediately see:
1. An interactive GPS track map with laps colored by lap number
2. Live telemetry graphs showing all 21 channels synchronized with the track position
3. Lap timing summaries and comparisons

This application will be built using TypeScript (for the parser) and Astro (for the static site framework), with zero server-side processing.

---

## Project Constraints

1. **Zero server-side processing**: All parsing happens in the browser using JavaScript/TypeScript
2. **Static site deployment**: Must work as a static Astro site deployable to Netlify/Vercel/GitHub Pages
3. **No external APIs**: Cannot call external services for telemetry processing
4. **Accuracy requirement**: TypeScript parser must match Python parser output within existing tolerances
5. **Browser compatibility**: Must work in modern browsers (Chrome, Firefox, Safari, Edge - last 2 versions)
6. **Performance target**: Parse a 10MB CTRK file in under 5 seconds on average hardware
7. **Permissive licenses only**: All third-party libraries must use permissive licenses (MIT, BSD, ISC, Apache 2.0). GPL-3.0, AGPL-3.0, and proprietary licenses are NOT allowed. Verify licenses before adding dependencies.

---

## Success Metrics

1. **Parser accuracy**: 95%+ match rate against Python parser output across all 21 channels
2. **Test coverage**: 90%+ code coverage for parser core logic
3. **Performance**: Parse 10MB CTRK files in under 5 seconds
4. **User experience**: From file drop to visualization in under 10 seconds for typical files
5. **Code quality**: Zero TypeScript type errors, ESLint clean

---

## Epic Overview

| # | Epic | Scope | Dependencies | Est. Effort |
|---|------|-------|--------------|-------------|
| 1 | TypeScript Parser Foundation | Binary parsing, data structures, CAN handlers | None | 3-4 days |
| 2 | TypeScript Parser Core Logic | Timestamp computation, emission logic, GPS parsing | Epic 1 | 3-4 days |
| 3 | TypeScript Parser Validation | Test suite, comparison framework, validation reports | Epic 1, 2 | 2-3 days |
| 4 | Astro Project Setup | Static site structure, TypeScript config, build pipeline | None | 1 day |
| 5 | File Upload Component | Drag-and-drop UI, file validation, progress feedback | Epic 4 | 1-2 days |
| 6 | GPS Track Map Visualization | Interactive map with laps, leaflet.js integration | Epic 5 | 2-3 days |
| 7 | Telemetry Graph Visualization | Multi-channel graphs, lap selection, zoom/pan | Epic 5 | 3-4 days |
| 8 | Lap Timing Summary | Lap table, best lap highlighting, lap comparison | Epic 5 | 1-2 days |
| 9 | Integration and Polish | End-to-end testing, performance optimization, UX refinement | All | 2-3 days |

**Total Estimated Effort:** 18-26 days

---

## Epic 1: TypeScript Parser Foundation

**Objective:** Port the Python parser's data structures, binary parsing utilities, and CAN message handlers to TypeScript.

**Owner:** dev

### Scope

- TypeScript project setup with proper tooling (tsconfig, ESLint, Prettier)
- Binary buffer reading utilities (little-endian, big-endian)
- Data structures (TelemetryRecord, FinishLine, Calibration)
- CAN message parser functions (all 8 CAN IDs)
- Header parsing (magic, variable-length entries, finish line coordinates)
- No Node.js-specific APIs (must work in browser)
- All dependencies must use permissive licenses (see Project Constraints)

### User Stories

1. As a developer, I want a TypeScript project with strict typing so that I catch errors at compile time
2. As a developer, I want binary buffer utilities that work in both Node and browser so that the parser is platform-agnostic
3. As a developer, I want all CAN message parsers implemented so that I can decode all 21 telemetry channels
4. As a developer, I want calibration functions for all channels so that I can convert raw values to engineering units

### Tasks

#### Task 1.1: TypeScript Project Setup
- **Type:** feature
- **Effort:** S
- **Owner:** dev
- **Acceptance Criteria:**
  - Create `parser/` directory with TypeScript project
  - Configure tsconfig.json with strict mode, ES2020 target
  - Setup ESLint with TypeScript rules
  - Setup Prettier for code formatting
  - Add package.json with build scripts
  - No dependencies except TypeScript and dev tools
- **Files:**
  - `parser/package.json` (new)
  - `parser/tsconfig.json` (new)
  - `parser/.eslintrc.js` (new)
  - `parser/.prettierrc` (new)

#### Task 1.2: Binary Buffer Utilities
- **Type:** feature
- **Effort:** M
- **Owner:** dev
- **Dependencies:** Task 1.1
- **Acceptance Criteria:**
  - Implement BufferReader class that works with Uint8Array
  - Support readUInt16LE, readUInt32LE, readUInt8
  - Support readUInt16BE (for CAN data)
  - Support readFloat64LE (for GPS coordinates)
  - Support readString (ASCII decoding)
  - Support readBytes (arbitrary byte array extraction)
  - Include bounds checking with clear error messages
  - Works in both Node.js and browser (use Uint8Array, not Buffer)
- **Files:**
  - `parser/src/buffer-reader.ts` (new)
  - `parser/src/buffer-reader.test.ts` (new)

#### Task 1.3: Data Structures
- **Type:** feature
- **Effort:** M
- **Owner:** dev
- **Dependencies:** Task 1.1
- **Acceptance Criteria:**
  - Define TelemetryRecord interface matching Python dataclass
  - Define FinishLine class with side_of_line and crosses_line methods
  - Define Calibration class with static methods for all 15 analog channels
  - All types exported from index.ts
  - Include JSDoc comments with formulas and examples
- **Files:**
  - `parser/src/types.ts` (new)
  - `parser/src/finish-line.ts` (new)
  - `parser/src/calibration.ts` (new)
  - `parser/src/finish-line.test.ts` (new)
  - `parser/src/calibration.test.ts` (new)

#### Task 1.4: CAN Message Handlers
- **Type:** feature
- **Effort:** L
- **Owner:** dev
- **Dependencies:** Task 1.2, Task 1.3
- **Acceptance Criteria:**
  - Implement parse_can_0x0209 (RPM, Gear)
  - Implement parse_can_0x0215 (Throttle, TCS, SCS, LIF, Launch)
  - Implement parse_can_0x023e (Temperature, Fuel delta)
  - Implement parse_can_0x0250 (Acceleration)
  - Implement parse_can_0x0258 (Lean, Pitch) with full deadband/truncation algorithm
  - Implement parse_can_0x0260 (Brake pressure)
  - Implement parse_can_0x0264 (Wheel speed)
  - Implement parse_can_0x0268 (ABS status)
  - All handlers match Python implementation byte-for-byte
  - Include unit tests with known CAN payloads and expected outputs
- **Files:**
  - `parser/src/can-handlers.ts` (new)
  - `parser/src/can-handlers.test.ts` (new)

#### Task 1.5: Header Parser
- **Type:** feature
- **Effort:** M
- **Owner:** dev
- **Dependencies:** Task 1.2, Task 1.3
- **Acceptance Criteria:**
  - Validate CTRK magic bytes (HEAD)
  - Parse variable-length header entries starting at 0x34
  - Extract RECORDLINE.P1/P2.LAT/LNG coordinates
  - Return FinishLine object or null if not found
  - Find data section start offset
  - Match Python implementation behavior exactly
- **Files:**
  - `parser/src/header-parser.ts` (new)
  - `parser/src/header-parser.test.ts` (new)

---

## Epic 2: TypeScript Parser Core Logic

**Objective:** Implement the main parsing loop, timestamp computation, GPS NMEA parsing, and emission logic.

**Owner:** dev

### Scope

- Main CTRKParser class with parse() method
- Timestamp computation (GetTimeData + GetTimeDataEx with incremental updates)
- GPS NMEA sentence parsing (GPRMC with checksum validation)
- 100ms emission logic with GPS gating
- Lap detection via finish line crossing
- State management (zero-order hold)
- Fuel accumulator
- All dependencies must use permissive licenses (see Project Constraints)

### User Stories

1. As a developer, I want a CTRKParser class that mirrors the Python API so that porting is straightforward
2. As a developer, I want accurate timestamp computation so that telemetry is properly time-aligned
3. As a developer, I want GPS parsing with checksum validation so that corrupt data is rejected
4. As a developer, I want 100ms emission timing so that output is at 10 Hz
5. As a developer, I want lap detection so that laps are correctly numbered

### Tasks

#### Task 2.1: CTRKParser Class Skeleton
- **Type:** feature
- **Effort:** S
- **Owner:** dev
- **Dependencies:** Epic 1 complete
- **Acceptance Criteria:**
  - Create CTRKParser class with constructor(data: Uint8Array)
  - Add parse() method that returns TelemetryRecord[]
  - Initialize state dictionary for CAN channels
  - Initialize GPS state (lat, lon, speed_knots)
  - Initialize emission state (last_emitted_ms, has_gprmc)
  - Initialize lap state (current_lap, prev_lat, prev_lng)
  - Initialize fuel accumulator
- **Files:**
  - `parser/src/ctrk-parser.ts` (new)

#### Task 2.2: Timestamp Computation
- **Type:** feature
- **Effort:** M
- **Owner:** dev
- **Dependencies:** Task 2.1
- **Acceptance Criteria:**
  - Implement GetTimeData (full timestamp computation from 10-byte timestamp)
  - Implement GetTimeDataEx (incremental computation for same-second records)
  - Handle millis wrapping with +1000ms correction
  - Match Python implementation exactly
  - Include unit tests with known timestamp bytes and expected epoch_ms
- **Files:**
  - `parser/src/timestamp.ts` (new)
  - `parser/src/timestamp.test.ts` (new)

#### Task 2.3: NMEA GPS Parser
- **Type:** feature
- **Effort:** M
- **Owner:** dev
- **Dependencies:** Task 2.1
- **Acceptance Criteria:**
  - Parse GPRMC sentence format (comma-separated fields)
  - Validate checksum (XOR of bytes between $ and *)
  - Convert degrees-minutes to decimal degrees
  - Handle status A (active) and V (void)
  - Return {latitude, longitude, speed_knots} or null
  - Match Python implementation exactly
  - Include unit tests with known GPRMC sentences
- **Files:**
  - `parser/src/nmea-parser.ts` (new)
  - `parser/src/nmea-parser.test.ts` (new)

#### Task 2.4: Data Section Parser Loop
- **Type:** feature
- **Effort:** L
- **Owner:** dev
- **Dependencies:** Task 2.2, Task 2.3
- **Acceptance Criteria:**
  - Read 14-byte record headers sequentially
  - Dispatch to CAN handlers for type 1 records
  - Dispatch to GPS parser for type 2 records
  - Handle type 5 lap markers (re-align emission clock)
  - Implement end-of-data detection (5 conditions)
  - Validate record_type and total_size
  - Advance offset by total_size after each record
- **Files:**
  - Update `parser/src/ctrk-parser.ts`
  - `parser/src/ctrk-parser.test.ts` (new)

#### Task 2.5: Emission Logic
- **Type:** feature
- **Effort:** M
- **Owner:** dev
- **Dependencies:** Task 2.4
- **Acceptance Criteria:**
  - Initialize emission clock at first record
  - Implement GPS gating (has_gprmc flag)
  - Emit initial record at first valid GPRMC
  - Emit record every 100ms after has_gprmc is true
  - Update last_emitted_ms after each emission
  - Emit final record after parsing loop ends
  - Create TelemetryRecord from current state snapshot
  - Match Python emission timing exactly
- **Files:**
  - Update `parser/src/ctrk-parser.ts`

#### Task 2.6: Lap Detection
- **Type:** feature
- **Effort:** M
- **Owner:** dev
- **Dependencies:** Task 2.5
- **Acceptance Criteria:**
  - Check finish line crossing at each emitted record
  - Use FinishLine.crosses_line method
  - Increment lap counter on crossing
  - Reset fuel accumulator on crossing
  - Handle initial position (0.0, 0.0)
  - Match Python lap detection logic
- **Files:**
  - Update `parser/src/ctrk-parser.ts`

---

## Epic 3: TypeScript Parser Validation

**Objective:** Build a comprehensive test suite that validates the TypeScript parser against the Python parser output.

**Owner:** qa

### Scope

- Node.js test runner to compare TS vs Python output
- Load Python CSV output as ground truth
- Parse same CTRK files with TypeScript parser
- Compare all 21 channels with appropriate tolerances
- Generate validation report (per-file, per-channel match rates)
- Ensure 95%+ overall match rate
- All dependencies must use permissive licenses (see Project Constraints)

### User Stories

1. As a QA engineer, I want a test suite that compares TS and Python output so that I can validate accuracy
2. As a QA engineer, I want per-channel match rates so that I can identify problem areas
3. As a QA engineer, I want per-file statistics so that I can find edge cases
4. As a developer, I want automated tests that fail if match rate drops below 95% so that regressions are caught

### Tasks

#### Task 3.1: Test Data Preparation
- **Type:** test
- **Effort:** S
- **Owner:** qa
- **Dependencies:** Epic 2 complete
- **Acceptance Criteria:**
  - Select 10-15 representative CTRK files from input/ directory
  - Include small files (100-500 records)
  - Include medium files (5,000-10,000 records)
  - Include large files (15,000+ records)
  - Include files with multiple laps
  - Generate Python CSV output for all test files
  - Store test data in parser/test-data/ directory
- **Files:**
  - `parser/test-data/*.CTRK` (copied)
  - `parser/test-data/*.csv` (Python output)
  - `parser/test-data/README.md` (new)

#### Task 3.2: Comparison Framework
- **Type:** test
- **Effort:** M
- **Owner:** dev
- **Dependencies:** Task 3.1
- **Acceptance Criteria:**
  - Create Node.js script to run parser comparison
  - Load Python CSV (ground truth)
  - Parse CTRK with TypeScript parser
  - Align records by index (same record count expected)
  - Compare all 21 channels with tolerances from COMPARISON.md
  - Compute per-channel match rates
  - Compute per-file match rates
  - Generate JSON report with statistics
- **Files:**
  - `parser/test/comparison-suite.ts` (new)
  - `parser/test/comparison-suite.test.ts` (new)

#### Task 3.3: Automated Test Suite
- **Type:** test
- **Effort:** M
- **Owner:** qa
- **Dependencies:** Task 3.2
- **Acceptance Criteria:**
  - Run comparison suite against all test files
  - Assert overall match rate >= 95%
  - Assert per-channel match rates meet minimums (RPM >= 82%, others >= 90%)
  - Fail CI build if thresholds not met
  - Generate detailed report on failure with specific mismatches
  - Run in under 30 seconds for full suite
- **Files:**
  - `parser/test/validation.test.ts` (new)
  - Update `parser/package.json` with test script

#### Task 3.4: Edge Case Tests
- **Type:** test
- **Effort:** M
- **Owner:** qa
- **Dependencies:** Task 3.3
- **Acceptance Criteria:**
  - Test empty CTRK files (zero records)
  - Test files with no GPS (should produce zero output records)
  - Test files with default date (2000-01-01)
  - Test files with millis wrapping
  - Test files with missing finish line (all records lap 1)
  - Test files with single lap
  - Test files with 10+ laps
  - All edge cases match Python behavior
- **Files:**
  - `parser/test/edge-cases.test.ts` (new)

#### Task 3.5: Documentation and Report
- **Type:** docs
- **Owner:** doc
- **Dependencies:** Task 3.3, Task 3.4
- **Acceptance Criteria:**
  - Create TYPESCRIPT_PARSER.md in docs/
  - Document TypeScript parser architecture
  - Include validation results (match rates)
  - List known differences from Python (if any)
  - Provide usage examples
  - Link to test suite and comparison methodology
- **Files:**
  - `docs/TYPESCRIPT_PARSER.md` (new)

---

## Epic 4: Astro Integration Package

**Objective:** Package the CTRK parser as an Astro integration/library that can be imported into an existing Astro project with minimal effort.

**Owner:** dev

### Scope

- Package parser as npm library with TypeScript support
- Create Astro integration configuration
- Develop reusable Vue.js components via @astrojs/vue
- Export composables for state management (Vue-native)
- Provide clear integration documentation
- All dependencies must use permissive licenses (see Project Constraints)

### User Stories

1. As a developer with an existing Astro project, I want to import the CTRK parser as a library so that I can integrate it with minimal effort
2. As a developer, I want Vue.js components ready to use so that I don't have to build the UI from scratch
3. As a developer, I want TypeScript types exported so that I get autocomplete and type safety
4. As a developer, I want Vue composables for state management so that I can manage telemetry data reactively

### Tasks

#### Task 4.1: NPM Package Structure
- **Type:** feature
- **Effort:** M
- **Owner:** dev
- **Dependencies:** Epic 3 complete
- **Acceptance Criteria:**
  - Create package.json for npm library (name: @ctrk-exporter/astro-integration or similar)
  - Configure exports for parser, components, and composables
  - Setup TypeScript declaration generation (*.d.ts files)
  - Configure build pipeline (tsup or vite library mode)
  - Add README with installation and usage instructions
  - Verify tree-shakeable exports
- **Files:**
  - `astro-integration/package.json` (new)
  - `astro-integration/tsconfig.json` (new)
  - `astro-integration/README.md` (new)
  - `astro-integration/vite.config.ts` or `astro-integration/tsup.config.ts` (new)

#### Task 4.2: Astro Integration Configuration
- **Type:** feature
- **Effort:** M
- **Owner:** dev
- **Dependencies:** Task 4.1
- **Acceptance Criteria:**
  - Create integration entry point (index.ts)
  - Export Astro integration function
  - Configure @astrojs/vue integration automatically
  - Setup client:only="vue" directives for components
  - Add integration hooks if needed (build hooks, etc.)
  - Document integration usage in README
- **Files:**
  - `astro-integration/src/integration.ts` (new)
  - `astro-integration/src/index.ts` (new)
  - Update `astro-integration/README.md`

#### Task 4.3: Parser Re-export and Utilities
- **Type:** feature
- **Effort:** S
- **Owner:** dev
- **Dependencies:** Task 4.1
- **Acceptance Criteria:**
  - Re-export CTRKParser from parser package
  - Export all TypeScript types (TelemetryRecord, etc.)
  - Add browser-specific utilities (File to Uint8Array conversion)
  - Export calibration functions for client-side use
  - Ensure no Node.js dependencies
- **Files:**
  - `astro-integration/src/parser.ts` (new)
  - `astro-integration/src/types.ts` (new)
  - `astro-integration/src/utils.ts` (new)

#### Task 4.4: Example Integration Project
- **Type:** docs
- **Effort:** M
- **Owner:** dev
- **Dependencies:** Task 4.2, Task 4.3
- **Acceptance Criteria:**
  - Create minimal Astro project in examples/ directory
  - Install and configure the integration
  - Show basic usage (import parser, parse file, display data)
  - Document step-by-step setup process
  - Verify it works with npm link or local file install
  - Include package.json, astro.config.mjs, and sample page
- **Files:**
  - `astro-integration/examples/basic/package.json` (new)
  - `astro-integration/examples/basic/astro.config.mjs` (new)
  - `astro-integration/examples/basic/src/pages/index.astro` (new)
  - `astro-integration/examples/basic/README.md` (new)

---

## Epic 5: File Upload Component

**Objective:** Create a drag-and-drop file upload component that loads CTRK files and triggers parsing.

**Owner:** dev

### Scope

- Drag-and-drop UI with visual feedback (Vue.js component)
- File validation (magic bytes, size limits)
- Progress indicator during parsing
- Error handling and user feedback
- Store parsed data using Vue composables
- All dependencies must use permissive licenses (see Project Constraints)

### User Stories

1. As a user, I want to drag-and-drop a CTRK file so that I can load my telemetry data
2. As a user, I want visual feedback during parsing so that I know the app is working
3. As a user, I want clear error messages if the file is invalid so that I know what went wrong

### Tasks

#### Task 5.1: File Drop Zone UI
- **Type:** feature
- **Effort:** M
- **Owner:** dev
- **Dependencies:** Epic 4 complete
- **Acceptance Criteria:**
  - Create FileUpload.vue component
  - Implement drag-and-drop zone with visual states (default, hover, active)
  - Add file picker button as fallback
  - Restrict to .CTRK files (extension check)
  - Show file name and size after selection
  - Style with dark theme and smooth animations
  - Use in Astro with client:only="vue" directive
- **Files:**
  - `astro-integration/src/components/FileUpload.vue` (new)
  - `astro-integration/src/components/FileUpload.css` (new)

#### Task 5.2: File Validation
- **Type:** feature
- **Effort:** S
- **Owner:** dev
- **Dependencies:** Task 5.1
- **Acceptance Criteria:**
  - Read first 4 bytes and validate magic (HEAD)
  - Reject files larger than 50MB (reasonable limit)
  - Reject files smaller than 100 bytes (too small)
  - Show error toast for invalid files
  - Log validation errors to console with details
- **Files:**
  - Update `astro-integration/src/components/FileUpload.vue`
  - `astro-integration/src/lib/file-validator.ts` (new)

#### Task 5.3: Parser Integration and Progress
- **Type:** feature
- **Effort:** M
- **Owner:** dev
- **Dependencies:** Task 5.2
- **Acceptance Criteria:**
  - Read File as ArrayBuffer
  - Convert to Uint8Array
  - Instantiate CTRKParser with data
  - Call parse() method in a Web Worker (for non-blocking)
  - Show progress spinner with estimated time
  - Handle parser errors gracefully
  - Store parsed records using Vue composable (useTelemetryData or similar)
  - Navigate to /analyze page on success
- **Files:**
  - Update `astro-integration/src/components/FileUpload.vue`
  - `astro-integration/src/workers/parser-worker.ts` (new)
  - `astro-integration/src/composables/useTelemetryData.ts` (new)

#### Task 5.4: Error Handling and UX
- **Type:** feature
- **Effort:** S
- **Owner:** dev
- **Dependencies:** Task 5.3
- **Acceptance Criteria:**
  - Show toast notifications for errors (invalid file, parse error)
  - Add retry button on error
  - Add "choose different file" button after parse
  - Log detailed errors to browser console
  - Display user-friendly error messages
- **Files:**
  - Update `astro-integration/src/components/FileUpload.vue`
  - `astro-integration/src/components/Toast.vue` (new)

---

## Epic 6: GPS Track Map Visualization

**Objective:** Display an interactive GPS track map with laps colored by lap number.

**Owner:** dev

### Scope

- Integrate Leaflet.js for interactive map (Vue.js component)
- Plot GPS coordinates as polyline
- Color each lap distinctly
- Add lap markers at finish line crossings
- Support zoom, pan, and hover interactions
- Display track name if available (from header/footer)
- All dependencies must use permissive licenses (see Project Constraints)

### User Stories

1. As a user, I want to see my GPS track on a map so that I can visualize my riding line
2. As a user, I want each lap colored differently so that I can distinguish between laps
3. As a user, I want to click on a lap to see details so that I can analyze specific laps
4. As a user, I want to zoom and pan so that I can explore details

### Tasks

#### Task 6.1: Leaflet.js Integration
- **Type:** feature
- **Effort:** S
- **Owner:** dev
- **Dependencies:** Epic 5 complete
- **Acceptance Criteria:**
  - Install leaflet (verify MIT license)
  - Create TrackMap.vue component
  - Initialize Leaflet map with OpenStreetMap tiles
  - Center map on first GPS coordinate
  - Set initial zoom level to fit entire track
  - Handle component lifecycle (onMounted/onUnmounted) properly
  - Use client:only="vue" in Astro
- **Files:**
  - `astro-integration/src/components/TrackMap.vue` (new)
  - `astro-integration/src/components/TrackMap.css` (new)
  - Update `astro-integration/package.json`

#### Task 6.2: GPS Polyline Rendering
- **Type:** feature
- **Effort:** M
- **Owner:** dev
- **Dependencies:** Task 6.1
- **Acceptance Criteria:**
  - Extract lat/lon from telemetry records
  - Filter out sentinel values (9999.0)
  - Draw polyline for each lap
  - Color laps with distinct palette (10+ colors)
  - Add line weight and opacity
  - Optimize for performance (simplify polyline if >10,000 points)
- **Files:**
  - Update `astro-integration/src/components/TrackMap.vue`
  - `astro-integration/src/lib/gps-utils.ts` (new)

#### Task 6.3: Lap Markers and Interactions
- **Type:** feature
- **Effort:** M
- **Owner:** dev
- **Dependencies:** Task 6.2
- **Acceptance Criteria:**
  - Add marker at start of each lap
  - Label marker with lap number
  - Make polyline clickable
  - Show lap number and time on click
  - Highlight selected lap (thicker line)
  - Emit event to synchronize with graph component
- **Files:**
  - Update `astro-integration/src/components/TrackMap.vue`
  - Update `astro-integration/src/composables/useTelemetryData.ts` (add selectedLap ref)

#### Task 6.4: Map Controls and Metadata
- **Type:** feature
- **Effort:** S
- **Owner:** dev
- **Dependencies:** Task 6.3
- **Acceptance Criteria:**
  - Add zoom controls
  - Add layer selector (satellite vs street map)
  - Display track name if available from CTRK footer
  - Add legend showing lap colors
  - Add "fit to track" button to reset view
- **Files:**
  - Update `astro-integration/src/components/TrackMap.vue`
  - `astro-integration/src/components/MapLegend.vue` (new)

---

## Epic 7: Telemetry Graph Visualization

**Objective:** Display interactive multi-channel telemetry graphs synchronized with the GPS track map.

**Owner:** dev

### Scope

- Chart library integration (Chart.js or Plotly.js) - Vue.js component
- Multi-channel graph display (all 21 channels)
- Lap selection and filtering
- Zoom, pan, and hover interactions
- Synchronization with map (hover shows position)
- Channel selection (show/hide channels)
- All dependencies must use permissive licenses (see Project Constraints)

### User Stories

1. As a user, I want to see telemetry graphs so that I can analyze my riding data
2. As a user, I want to select specific laps so that I can compare performance
3. As a user, I want to zoom into specific sections so that I can see details
4. As a user, I want to hover on the graph and see the position on the map so that I can correlate data with track location

### Tasks

#### Task 7.1: Chart Library Integration
- **Type:** feature
- **Effort:** M
- **Owner:** dev
- **Dependencies:** Epic 5 complete
- **Acceptance Criteria:**
  - Evaluate Chart.js vs Plotly.js (performance, features, bundle size, licenses)
  - Verify chosen library has permissive license (Chart.js is MIT, Plotly.js is MIT)
  - Install chosen library
  - Create TelemetryChart.vue component
  - Setup chart configuration with dark theme
  - Display single channel (e.g., RPM) as proof-of-concept
  - Verify performance with 20,000+ data points
  - Use client:only="vue" in Astro
- **Files:**
  - `astro-integration/src/components/TelemetryChart.vue` (new)
  - `astro-integration/src/components/TelemetryChart.css` (new)
  - Update `astro-integration/package.json`

#### Task 7.2: Multi-Channel Graph Layout
- **Type:** feature
- **Effort:** L
- **Owner:** dev
- **Dependencies:** Task 7.1
- **Acceptance Criteria:**
  - Create stacked chart layout (8-10 subplots)
  - Group channels by category (Engine, Speed, Chassis, etc.)
  - Each subplot shares X-axis (time)
  - Y-axis scales automatically per channel
  - Color channels matching visualize_all_channels.py
  - Optimize rendering (virtualization if needed)
- **Files:**
  - Update `astro-integration/src/components/TelemetryChart.vue`
  - `astro-integration/src/lib/chart-config.ts` (new)

#### Task 7.3: Lap Selection and Filtering
- **Type:** feature
- **Effort:** M
- **Owner:** dev
- **Dependencies:** Task 7.2
- **Acceptance Criteria:**
  - Add lap selector dropdown (all laps, lap 1, lap 2, etc.)
  - Filter telemetry data by selected lap
  - Update X-axis to show lap time (seconds from lap start)
  - Synchronize with map (selecting lap on map updates chart)
  - Add "compare laps" mode (overlay multiple laps)
- **Files:**
  - Update `astro-integration/src/components/TelemetryChart.vue`
  - `astro-integration/src/components/LapSelector.vue` (new)
  - Update `astro-integration/src/composables/useTelemetryData.ts`

#### Task 7.4: Interactive Features
- **Type:** feature
- **Effort:** M
- **Owner:** dev
- **Dependencies:** Task 7.3
- **Acceptance Criteria:**
  - Implement zoom/pan with mouse wheel and drag
  - Add hover tooltip showing all channel values at time point
  - Highlight current time position on all subplots
  - Emit event on hover to show position on map
  - Add reset zoom button
  - Persist zoom state across lap changes
- **Files:**
  - Update `web/src/components/TelemetryChart.vue`

#### Task 7.5: Channel Selection and Customization
- **Type:** feature
- **Effort:** M
- **Owner:** dev
- **Dependencies:** Task 7.4
- **Acceptance Criteria:**
  - Add channel selector panel (checkboxes)
  - Show/hide individual channels
  - Reorder channels via drag-and-drop
  - Save preferences to localStorage
  - Add presets (All, Core, Advanced)
  - Export current view as PNG
- **Files:**
  - Update `web/src/components/TelemetryChart.vue`
  - `web/src/components/ChannelSelector.vue` (new)

---

## Epic 8: Lap Timing Summary

**Objective:** Display a lap timing table with best lap highlighting and lap-to-lap comparison.

**Owner:** dev

### Scope

- Lap timing table (lap number, lap time, best sector times)
- Best lap highlighting
- Lap-to-lap delta display
- Sort by lap time
- Export to CSV

### User Stories

1. As a user, I want to see lap times so that I can identify my best and worst laps
2. As a user, I want to see lap-to-lap deltas so that I can track improvement
3. As a user, I want to export lap times so that I can share them

### Tasks

#### Task 8.1: Lap Time Computation
- **Type:** feature
- **Effort:** M
- **Owner:** dev
- **Dependencies:** Epic 5 complete
- **Acceptance Criteria:**
  - Compute lap times from telemetry records (first record of lap N to first record of lap N+1)
  - Handle edge case (last lap time is until final record)
  - Store lap times in store
  - Format as MM:SS.sss
  - Compute sector times if finish line defines sectors (future enhancement)
- **Files:**
  - `web/src/lib/lap-timing.ts` (new)
  - `web/src/lib/lap-timing.test.ts` (new)

#### Task 8.2: Lap Timing Table UI
- **Type:** feature
- **Effort:** M
- **Owner:** dev
- **Dependencies:** Task 8.1
- **Acceptance Criteria:**
  - Create LapTimingTable.vue component
  - Display table with columns: Lap, Time, Delta to Best, Status
  - Highlight best lap (green)
  - Show delta to best lap (+1.234s)
  - Make rows clickable to select lap
  - Sort by lap number or lap time
- **Files:**
  - `web/src/components/LapTimingTable.vue` (new)
  - `web/src/components/LapTimingTable.css` (new)

#### Task 8.3: Session Summary
- **Type:** feature
- **Effort:** S
- **Owner:** dev
- **Dependencies:** Task 8.2
- **Acceptance Criteria:**
  - Display session metadata (date, track, rider)
  - Show total laps, total time, average lap time
  - Show best lap time and lap number
  - Show consistency metric (std dev of lap times)
  - Display in header or sidebar
- **Files:**
  - `web/src/components/SessionSummary.vue` (new)

#### Task 8.4: Export and Sharing
- **Type:** feature
- **Effort:** S
- **Owner:** dev
- **Dependencies:** Task 8.2
- **Acceptance Criteria:**
  - Add "Export CSV" button
  - Generate CSV with lap number, time, delta
  - Trigger browser download
  - Add "Share" button (copy link with session ID if hosted)
  - Add "Print" friendly CSS for lap table
- **Files:**
  - Update `web/src/components/LapTimingTable.vue`
  - `web/src/lib/export-utils.ts` (new)

---

## Epic 9: Integration and Polish

**Objective:** End-to-end testing, performance optimization, UX refinement, and production readiness.

**Owner:** dev, qa, review

### Scope

- End-to-end testing with real CTRK files
- Performance profiling and optimization
- Responsive design for mobile/tablet
- Accessibility (a11y) improvements
- Error boundary and fallback UI
- Production build optimization

### User Stories

1. As a user, I want the app to work smoothly on all my devices so that I can use it anywhere
2. As a user, I want fast loading times so that I don't wait
3. As a developer, I want comprehensive tests so that I can deploy with confidence

### Tasks

#### Task 9.1: End-to-End Testing
- **Type:** test
- **Effort:** M
- **Owner:** qa
- **Dependencies:** Epic 6, 7, 8 complete
- **Acceptance Criteria:**
  - Test file upload flow with 10+ real CTRK files
  - Verify map renders correctly for all files
  - Verify graphs render correctly for all files
  - Verify lap timing is accurate
  - Test lap selection synchronization
  - Test error cases (corrupt file, no GPS, huge file)
  - Document test results
- **Files:**
  - `web/test/e2e/upload-flow.test.ts` (new)
  - `web/test/e2e/visualization.test.ts` (new)

#### Task 9.2: Performance Profiling and Optimization
- **Type:** refactor
- **Effort:** L
- **Owner:** dev
- **Dependencies:** Task 9.1
- **Acceptance Criteria:**
  - Profile parser with Chrome DevTools (aim for <5s on 10MB file)
  - Optimize hot paths (timestamp computation, CAN decoding)
  - Implement Web Worker for parsing (non-blocking UI)
  - Lazy-load chart library (code-splitting)
  - Optimize bundle size (tree-shaking, minification)
  - Measure Time to Interactive (TTI < 3s on 3G)
  - Add performance monitoring (web-vitals)
- **Files:**
  - Update `web/src/workers/parser-worker.ts`
  - `web/src/lib/performance.ts` (new)

#### Task 9.3: Responsive Design
- **Type:** feature
- **Effort:** M
- **Owner:** dev
- **Dependencies:** Epic 6, 7, 8 complete
- **Acceptance Criteria:**
  - Test on mobile (375px), tablet (768px), desktop (1920px)
  - Adjust layout for small screens (stack components)
  - Make map and charts touch-friendly
  - Test on iOS Safari, Android Chrome
  - Ensure readable text on all screen sizes
  - Test landscape and portrait orientations
- **Files:**
  - Update CSS in all component files
  - `web/src/styles/responsive.css` (new)

#### Task 9.4: Accessibility (a11y)
- **Type:** feature
- **Effort:** M
- **Owner:** dev
- **Dependencies:** Epic 6, 7, 8 complete
- **Acceptance Criteria:**
  - Add ARIA labels to interactive elements
  - Ensure keyboard navigation works (tab, enter)
  - Test with screen reader (NVDA or VoiceOver)
  - Add focus indicators (visible outlines)
  - Ensure color contrast meets WCAG AA (4.5:1)
  - Add skip-to-content link
  - Test with axe-core or Lighthouse
- **Files:**
  - Update all component files
  - `web/src/styles/accessibility.css` (new)

#### Task 9.5: Error Boundaries and Fallbacks
- **Type:** feature
- **Effort:** S
- **Owner:** dev
- **Dependencies:** Epic 5, 6, 7 complete
- **Acceptance Criteria:**
  - Add Vue error boundary (onErrorCaptured) around each major component
  - Show user-friendly error message on crash
  - Log errors to console with stack trace
  - Add retry button
  - Add fallback UI for loading states
  - Test by intentionally throwing errors
- **Files:**
  - `web/src/components/ErrorBoundary.vue` (new)

#### Task 9.6: Production Build and Deployment
- **Type:** feature
- **Effort:** M
- **Owner:** dev
- **Dependencies:** All epics complete
- **Acceptance Criteria:**
  - Run production build (npm run build)
  - Verify bundle size (target <500KB gzipped)
  - Test with Lighthouse (score >90 on all metrics)
  - Deploy to Netlify or Vercel
  - Test deployed site with real CTRK files
  - Setup custom domain (optional)
  - Add analytics (Plausible or similar, privacy-focused)
- **Files:**
  - Update `web/netlify.toml` or `web/vercel.json`
  - `web/README.md` (update with deployment instructions)

#### Task 9.7: User Documentation
- **Type:** docs
- **Owner:** doc
- **Dependencies:** Task 9.6
- **Acceptance Criteria:**
  - Create user guide (how to use the web app)
  - Document supported browsers
  - Add FAQ section
  - Document limitations (file size, browser compatibility)
  - Add screenshots and video walkthrough
  - Link from index page
- **Files:**
  - `web/src/pages/docs.astro` (new)
  - `docs/WEB_USER_GUIDE.md` (new)

---

## Dependencies and Critical Path

### Critical Path

```
Epic 1 (Parser Foundation)
  └─> Epic 2 (Parser Core Logic)
      └─> Epic 3 (Parser Validation)
          └─> Epic 4 (Astro Setup)
              └─> Epic 5 (File Upload)
                  ├─> Epic 6 (GPS Map)
                  ├─> Epic 7 (Telemetry Graph)
                  └─> Epic 8 (Lap Timing)
                      └─> Epic 9 (Integration & Polish)
```

**Longest path:** Epic 1 -> Epic 2 -> Epic 3 -> Epic 4 -> Epic 5 -> Epic 7 -> Epic 9

**Parallelizable work:**
- Epic 4 (Astro setup) can start before Epic 3 completes (just needs Epic 1 + 2)
- Epic 6, 7, 8 can proceed in parallel once Epic 5 is done
- Epic 9 tasks can be incremental as features complete

### Agent Assignments

| Epic | Primary Agent | Supporting Agents |
|------|---------------|-------------------|
| Epic 1 | dev | review (code review), doc (API docs) |
| Epic 2 | dev | review (code review) |
| Epic 3 | qa | dev (tooling), doc (validation report) |
| Epic 4 | dev | - |
| Epic 5 | dev | review (code review) |
| Epic 6 | dev | review (code review) |
| Epic 7 | dev | review (code review) |
| Epic 8 | dev | review (code review) |
| Epic 9 | dev, qa | review (final review), doc (user guide) |

### Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Parser accuracy <95% | HIGH | Incremental validation after each Epic 1-2 task; Task 3.3 enforces threshold |
| Performance (parsing >10s) | MEDIUM | Profile early (Task 9.2); use Web Worker from start (Task 5.3) |
| Chart library performance | MEDIUM | Evaluate in Task 7.1 before committing; fallback to simpler library if needed |
| Browser compatibility | LOW | Test in Task 9.3 with BrowserStack or real devices |
| Bundle size bloat | MEDIUM | Monitor in each epic; lazy-load heavy components (map, charts) |

---

## Sprint Planning Guidance

### Sprint 1 (Days 1-5): Parser Foundation
- **Goal:** TypeScript parser project setup and core data structures
- **Epics:** Epic 1 (complete)
- **Deliverable:** Parser project with binary utilities, data structures, CAN handlers, header parser
- **Validation:** Unit tests pass, no TypeScript errors

### Sprint 2 (Days 6-10): Parser Core Logic
- **Goal:** Implement main parsing loop and emission logic
- **Epics:** Epic 2 (complete)
- **Deliverable:** Working CTRKParser.parse() method that produces telemetry records
- **Validation:** Manual testing with sample CTRK files

### Sprint 3 (Days 11-14): Parser Validation
- **Goal:** Validate TypeScript parser against Python parser
- **Epics:** Epic 3 (complete)
- **Deliverable:** Automated test suite with 95%+ match rate
- **Validation:** CI passes, validation report generated

### Sprint 4 (Days 15-17): Astro Setup + File Upload
- **Goal:** Web project foundation and file upload
- **Epics:** Epic 4 (complete), Epic 5 (complete)
- **Deliverable:** Working web app that parses CTRK files
- **Validation:** User can upload file and see parsed data in console

### Sprint 5 (Days 18-21): Visualizations
- **Goal:** GPS map and telemetry graphs
- **Epics:** Epic 6 (complete), Epic 7 (complete), Epic 8 (complete)
- **Deliverable:** Full visualization suite
- **Validation:** User can see map, graphs, and lap timing for uploaded file

### Sprint 6 (Days 22-26): Integration and Polish
- **Goal:** Production-ready application
- **Epics:** Epic 9 (complete)
- **Deliverable:** Deployed web app on Netlify/Vercel
- **Validation:** End-to-end tests pass, Lighthouse score >90, deployed and accessible

---

## Success Criteria

The web browser CTRK parser project is considered successful when:

1. **Parser accuracy:** TypeScript parser achieves 95%+ match rate against Python parser across all 21 channels
2. **Test coverage:** 90%+ code coverage for parser core logic
3. **Performance:** Parses 10MB CTRK file in under 5 seconds
4. **User experience:** From file drop to visualization in under 10 seconds
5. **Code quality:** Zero TypeScript errors, ESLint clean, passes all automated tests
6. **Deployment:** Static site deployed to Netlify/Vercel with custom domain
7. **Documentation:** User guide, API docs, and validation report complete
8. **Accessibility:** WCAG AA compliant, keyboard navigable, screen reader friendly
9. **Browser support:** Works in Chrome, Firefox, Safari, Edge (last 2 versions)
10. **Lighthouse score:** >90 on Performance, Accessibility, Best Practices, SEO

---

## Out of Scope

The following are explicitly **not** included in this backlog:

1. **Server-side processing:** All parsing must happen in the browser
2. **Cloud storage:** No upload to cloud services (files stay local)
3. **User accounts:** No authentication or user profiles
4. **Mobile app:** Web-only, no native iOS/Android app
5. **Real-time telemetry:** CTRK is post-session format only
6. **Video overlay:** No integration with GoPro/action camera footage
7. **Social features:** No sharing to social media, no leaderboards
8. **MoTeC/AiM export:** Desktop parser already supports this (out of scope for web version)
9. **Multi-file comparison:** Single file at a time (future enhancement)
10. **Proprietary code distribution:** No native library, no APK files

---

## References

- **Python parser:** `src/ctrk_parser.py` (1,048 lines, reference implementation)
- **Format specification:** `docs/CTRK_FORMAT_SPECIFICATION.md` (complete binary format documentation)
- **Validation report:** `docs/COMPARISON.md` (95.40% match rate validation)
- **Visualization reference:** `src/visualize_all_channels.py` (matplotlib-based graph generation)
- **CLAUDE.md:** Project overview and development rules

---

**Backlog Status:** DRAFT
**Next Review:** After Epic 1 completion
**Maintained By:** Product Manager (pm agent)
