# Changelog

All notable changes to this project will be documented in this file.

Versions follow [Semantic Versioning](https://semver.org/).

For the Python exploration phase history, see [exploration/CHANGELOG.md](exploration/CHANGELOG.md).

## [0.1.0] - 2026-02-16

### Changed

- **@tex0l/ctrk-astro**: Migrate all 8 Vue components from scoped BEM CSS to Tailwind utility classes using the site's `(--color-*)` custom properties
- **@tex0l/ctrk-astro**: Replace lap timing CSV export with full calibrated telemetry CSV matching CLI output (same 27-column header, Calibration functions, Python-compatible banker's rounding, CRLF line endings)
- **@tex0l/ctrk-astro**: Add `@source inline()` CSS file and `index.css` export for Tailwind consumers

### Fixed

- **@tex0l/ctrk-astro**: Fix e2e test to use `formatCalibratedCsv` after export-utils rewrite

### Added

- **@tex0l/ctrk-astro**: Unit tests for calibrated CSV export (6 tests)
- **@tex0l/ctrk-astro**: Vitest config to exclude Playwright e2e tests from unit test runs

### Removed

- **@tex0l/ctrk-astro**: Global CSS file (`src/styles/global.css`) — replaced by Tailwind utilities

### CI/CD

- Switch publish workflow to npm trusted publishing (OIDC provenance)
- Add `--tag next` for prerelease npm publishes
- Add version lifecycle script and document release process

## [0.1.0-0] - 2026-02-12

### Structure

- Monorepo with 3 npm packages under `@tex0l` scope: `ctrk-parser`, `ctrk-cli`, `ctrk-astro`
- Package directories named to match package names: `packages/ctrk-parser/`, `packages/ctrk-cli/`, `packages/ctrk-astro/`
- `@tex0l/ctrk-astro` contains the full web toolkit: Astro integration, Vue composables, components, lib utilities, workers, and styles as importable exports
- Web app example at `packages/ctrk-astro/examples/web/` (workspace: `@tex0l/ctrk-web`, private)
- Original Python parser and R&D work in `exploration/`

### @tex0l/ctrk-parser

- Platform-agnostic TypeScript parser (Node.js + browser), zero dependencies
- 8 decoded CAN IDs, 21 telemetry channels (15 analog + 6 boolean)
- Lap detection via GPS finish line crossing
- 155 tests, 100% match rate vs Python parser (2.8M comparisons)
- 8.4 MB file parses in ~125 ms (67 MB/s throughput)

### @tex0l/ctrk-cli

- CLI extracted from parser into its own package
- Batch parsing: `ctrk-parser parse *.CTRK -o results/`
- CSV export with Python-compatible rounding, optional `--raw` mode

### @tex0l/ctrk-astro

- Astro integration hook (optimizeDeps + worker format)
- Vue composables: `useTelemetryData`, `useParserStatus`, `useToast` (singleton pattern)
- 8 Vue components: `FileUpload`, `AnalyzePage`, `TelemetryChart`, `TrackMap`, `LapTimingTable`, `ChannelSelector`, `AppHeader`, `Toast`
- Lib utilities: chart config, LTTB downsampling, file validation, GPS utils, lap timing, CSV export
- Web Worker for non-blocking CTRK parsing
- Global CSS with dark theme and 3-tier responsive breakpoints
- Package exports: `.`, `./parser`, `./composables`, `./utils`, `./lib/*`, `./components/*`, `./workers/*`, `./styles/*`
- `chart.js` and `leaflet` as optional peer dependencies

### CI/CD

- GitHub Actions CI workflow (Node 20 + 22 matrix) on push/PR to main
- GitHub Actions publish workflow on version tags with npm provenance
- Committed Sample.CTRK fixture from Y-Trac APK for CI integration testing

### Documentation

- CTRK binary format specification (v2.1)
- TypeScript parser architecture and validation docs
- Web app user guide
- WCAG AA accessibility (ARIA, focus-visible, skip-to-content, keyboard nav)
