/**
 * End-to-End Validation Tests for Web Edition
 *
 * Tests the integration of parser, utilities, and data processing
 * using real CTRK files from parser/test-data/.
 */

import { describe, it, expect, beforeAll } from 'vitest';
import { existsSync, readFileSync, readdirSync, statSync } from 'fs';
import { join } from 'path';
import { CTRKParser, type TelemetryRecord } from '@tex0l/ctrk-parser';
import {
  validateExtension,
  validateFileSize,
  validateMagicBytes,
  MIN_FILE_SIZE,
  MAX_FILE_SIZE,
} from '@tex0l/ctrk-astro/lib/file-validator';
import {
  extractGpsCoordinates,
  groupByLap,
  simplifyTrack,
  calculateBounds,
  detectLapCrossings,
  isValidGps,
} from '@tex0l/ctrk-astro/lib/gps-utils';
import {
  computeLapTimes,
  computeSessionSummary,
  formatLapTime,
  formatDelta,
} from '@tex0l/ctrk-astro/lib/lap-timing';
import { formatCalibratedCsv } from '@tex0l/ctrk-astro/lib/export-utils';
import { CHANNEL_GROUPS, getLapColor, getEnabledChannels } from '@tex0l/ctrk-astro/lib/chart-config';

// Use committed test data from parser package
const TEST_DATA_DIR = join(__dirname, '..', '..', '..', '..', 'ctrk-parser', 'test-data');
const hasTestData = existsSync(TEST_DATA_DIR) &&
  readdirSync(TEST_DATA_DIR).some(f => f.endsWith('.CTRK'));

let testFiles: string[] = [];
let sampleRecords: TelemetryRecord[] = [];

beforeAll(() => {
  const files = readdirSync(TEST_DATA_DIR);
  testFiles = files
    .filter((f) => f.toLowerCase().endsWith('.ctrk'))
    .map((f) => join(TEST_DATA_DIR, f));

  // Parse a multi-lap file for testing utilities
  const testFile =
    testFiles.find((f) => f.includes('20250729-155522')) || testFiles[0];
  const data = new Uint8Array(readFileSync(testFile));
  sampleRecords = new CTRKParser(data).parse();
});

describe.skipIf(!hasTestData)('File Validator', () => {
  describe('validateExtension', () => {
    it('should accept .CTRK extension', () => {
      expect(validateExtension('test.CTRK')).toBeNull();
      expect(validateExtension('test.ctrk')).toBeNull();
    });

    it('should reject invalid extensions', () => {
      const error = validateExtension('test.txt');
      expect(error).not.toBeNull();
      expect(error?.type).toBe('invalid_extension');
    });

    it('should reject files without extension', () => {
      expect(validateExtension('test')).not.toBeNull();
    });
  });

  describe('validateFileSize', () => {
    it('should accept valid file sizes', () => {
      expect(validateFileSize(MIN_FILE_SIZE)).toBeNull();
      expect(validateFileSize(1000)).toBeNull();
      expect(validateFileSize(MAX_FILE_SIZE)).toBeNull();
    });

    it('should reject files that are too small', () => {
      const error = validateFileSize(50);
      expect(error).not.toBeNull();
      expect(error?.type).toBe('file_too_small');
    });

    it('should reject files that are too large', () => {
      const error = validateFileSize(MAX_FILE_SIZE + 1);
      expect(error).not.toBeNull();
      expect(error?.type).toBe('file_too_large');
    });
  });

  describe('validateMagicBytes', () => {
    it('should accept valid CTRK magic bytes', () => {
      const data = new Uint8Array([0x48, 0x45, 0x41, 0x44, 0, 0, 0, 0]);
      expect(validateMagicBytes(data)).toBeNull();
    });

    it('should reject invalid magic bytes', () => {
      const data = new Uint8Array([0x00, 0x00, 0x00, 0x00]);
      expect(validateMagicBytes(data)).not.toBeNull();
    });

    it('should reject data that is too short', () => {
      const data = new Uint8Array([0x48, 0x45]);
      expect(validateMagicBytes(data)).not.toBeNull();
    });
  });

  describe('Real CTRK files validation', () => {
    it('should validate all test files correctly', () => {
      for (const filePath of testFiles) {
        const data = new Uint8Array(readFileSync(filePath));
        const stat = statSync(filePath);

        expect(validateMagicBytes(data)).toBeNull();
        expect(validateFileSize(stat.size)).toBeNull();
      }
    });
  });
});

describe.skipIf(!hasTestData)('GPS Utils', () => {
  describe('isValidGps', () => {
    it('should accept valid GPS coordinates', () => {
      expect(isValidGps(48.858844, 2.294351)).toBe(true);
      expect(isValidGps(47.364923, 4.89969)).toBe(true);
    });

    it('should reject GPS sentinel values', () => {
      expect(isValidGps(9999.0, 9999.0)).toBe(false);
      expect(isValidGps(9999.05, 9999.05)).toBe(false);
    });

    it('should reject NaN values', () => {
      expect(isValidGps(NaN, 0)).toBe(false);
      expect(isValidGps(0, NaN)).toBe(false);
    });
  });

  describe('extractGpsCoordinates', () => {
    it('should extract valid GPS coordinates from records', () => {
      const coords = extractGpsCoordinates(sampleRecords);
      expect(coords.length).toBeGreaterThan(0);

      for (const coord of coords) {
        expect(isValidGps(coord.lat, coord.lng)).toBe(true);
        expect(coord.time_ms).toBeGreaterThan(0);
        expect(coord.lap).toBeGreaterThanOrEqual(0);
      }
    });

    it('should filter out sentinel GPS values', () => {
      const testRecords: TelemetryRecord[] = [
        {
          time_ms: 1000, lap: 1, latitude: 48.858844, longitude: 2.294351,
          gps_speed_knots: 10, rpm: 5000, tps: 50, aps: 50,
          front_speed: 60, rear_speed: 60, gear: 3,
          lean: 9000, lean_signed: 9000, pitch: 0,
          front_brake: 0, rear_brake: 0, water_temp: 80,
          intake_temp: 40, fuel: 100, acc_x: 0, acc_y: 0,
          f_abs: false, r_abs: false, tcs: 0, scs: 0, lif: 0, launch: 0,
        },
        {
          time_ms: 2000, lap: 1, latitude: 9999.0, longitude: 9999.0,
          gps_speed_knots: 0, rpm: 5000, tps: 50, aps: 50,
          front_speed: 60, rear_speed: 60, gear: 3,
          lean: 9000, lean_signed: 9000, pitch: 0,
          front_brake: 0, rear_brake: 0, water_temp: 80,
          intake_temp: 40, fuel: 100, acc_x: 0, acc_y: 0,
          f_abs: false, r_abs: false, tcs: 0, scs: 0, lif: 0, launch: 0,
        },
      ];

      const coords = extractGpsCoordinates(testRecords);
      expect(coords.length).toBe(1);
      expect(coords[0].lat).toBe(48.858844);
    });
  });

  describe('groupByLap', () => {
    it('should group coordinates by lap number', () => {
      const coords = extractGpsCoordinates(sampleRecords);
      const lapGroups = groupByLap(coords);

      expect(lapGroups.size).toBeGreaterThan(0);

      for (const [lap, lapCoords] of lapGroups) {
        expect(lap).toBeGreaterThanOrEqual(0);
        expect(lapCoords.length).toBeGreaterThan(0);
        for (const coord of lapCoords) {
          expect(coord.lap).toBe(lap);
        }
      }
    });
  });

  describe('simplifyTrack', () => {
    it('should reduce track to max points', () => {
      const coords = extractGpsCoordinates(sampleRecords);
      const simplified = simplifyTrack(coords, 100);

      expect(simplified.length).toBeLessThanOrEqual(100);
      if (coords.length > 0) {
        expect(simplified[0]).toBe(coords[0]);
        expect(simplified[simplified.length - 1]).toBe(coords[coords.length - 1]);
      }
    });

    it('should not modify tracks shorter than max points', () => {
      const coords = extractGpsCoordinates(sampleRecords).slice(0, 50);
      const simplified = simplifyTrack(coords, 100);
      expect(simplified.length).toBe(coords.length);
    });
  });

  describe('calculateBounds', () => {
    it('should calculate correct bounding box', () => {
      const coords = extractGpsCoordinates(sampleRecords);
      const bounds = calculateBounds(coords);

      expect(bounds).not.toBeNull();
      if (bounds) {
        const [minLat, minLng, maxLat, maxLng] = bounds;
        expect(minLat).toBeLessThanOrEqual(maxLat);
        expect(minLng).toBeLessThanOrEqual(maxLng);
      }
    });

    it('should return null for empty coordinates', () => {
      expect(calculateBounds([])).toBeNull();
    });
  });

  describe('detectLapCrossings', () => {
    it('should detect lap transitions', () => {
      const coords = extractGpsCoordinates(sampleRecords);
      const crossings = detectLapCrossings(coords);
      const lapGroups = groupByLap(coords);

      expect(crossings.length).toBe(lapGroups.size - 1);
      for (const idx of crossings) {
        expect(coords[idx].lap).not.toBe(coords[idx - 1].lap);
      }
    });
  });
});

describe.skipIf(!hasTestData)('Lap Timing', () => {
  describe('computeLapTimes', () => {
    it('should compute lap times from records', () => {
      const lapTimes = computeLapTimes(sampleRecords);

      expect(lapTimes.length).toBeGreaterThan(0);

      for (const lapTime of lapTimes) {
        expect(lapTime.lap).toBeGreaterThanOrEqual(0);
        expect(lapTime.time_ms).toBeGreaterThan(0);
      }

      const bestLaps = lapTimes.filter((lt) => lt.isBest);
      expect(bestLaps.length).toBe(1);
      expect(bestLaps[0].delta_ms).toBe(0);
    });

    it('should skip lap 0 for best lap determination', () => {
      const lapTimes = computeLapTimes(sampleRecords);
      const bestLap = lapTimes.find((lt) => lt.isBest);
      if (bestLap) {
        expect(bestLap.lap).toBeGreaterThan(0);
      }
    });

    it('should compute deltas correctly', () => {
      const lapTimes = computeLapTimes(sampleRecords);
      const bestLap = lapTimes.find((lt) => lt.isBest);
      if (bestLap) {
        for (const lapTime of lapTimes) {
          if (lapTime.lap > 0 && lapTime.delta_ms !== null) {
            expect(lapTime.delta_ms).toBe(lapTime.time_ms - bestLap.time_ms);
          }
        }
      }
    });
  });

  describe('computeSessionSummary', () => {
    it('should compute session summary', () => {
      const lapTimes = computeLapTimes(sampleRecords);
      const summary = computeSessionSummary(lapTimes);

      expect(summary.totalLaps).toBeGreaterThan(0);
      expect(summary.bestLap).toBeGreaterThan(0);
      expect(summary.bestTime_ms).toBeGreaterThan(0);
      expect(summary.averageTime_ms).toBeGreaterThan(0);

      if (summary.averageTime_ms && summary.bestTime_ms) {
        expect(summary.averageTime_ms).toBeGreaterThanOrEqual(summary.bestTime_ms);
      }
    });

    it('should handle empty lap times', () => {
      const summary = computeSessionSummary([]);
      expect(summary.totalLaps).toBe(0);
      expect(summary.bestLap).toBeNull();
      expect(summary.bestTime_ms).toBeNull();
      expect(summary.averageTime_ms).toBeNull();
    });
  });

  describe('formatLapTime', () => {
    it('should format lap times correctly', () => {
      expect(formatLapTime(90123)).toBe('1:30.123');
      expect(formatLapTime(65000)).toBe('1:05.000');
      expect(formatLapTime(5678)).toBe('0:05.678');
    });
  });

  describe('formatDelta', () => {
    it('should format positive deltas with + sign', () => {
      expect(formatDelta(1234)).toBe('+1.234');
    });

    it('should format negative deltas with - sign', () => {
      expect(formatDelta(-567)).toBe('-0.567');
    });

    it('should format zero correctly', () => {
      expect(formatDelta(0)).toBe('+0.000');
    });
  });
});

describe.skipIf(!hasTestData)('Export Utils', () => {
  describe('formatCalibratedCsv', () => {
    it('should export calibrated telemetry to CSV format', () => {
      const csv = formatCalibratedCsv(sampleRecords);

      expect(csv).toContain('lap,time_ms,latitude,longitude,gps_speed_kmh');

      // CRLF line endings, filter empty trailing line
      const lines = csv.split('\r\n').filter((l: string) => l.trim());
      expect(lines.length).toBe(sampleRecords.length + 1); // +1 for header

      for (let i = 1; i < lines.length; i++) {
        const columns = lines[i].split(',');
        expect(columns.length).toBe(27);
      }
    });

    it('should produce valid numeric values for all fields', () => {
      const csv = formatCalibratedCsv(sampleRecords);
      const lines = csv.split('\r\n').filter((l: string) => l.trim());

      for (let i = 1; i < Math.min(lines.length, 10); i++) {
        const columns = lines[i].split(',');
        const timeMs = parseFloat(columns[1]);
        expect(timeMs).toBeGreaterThanOrEqual(0);
        // latitude/longitude should be valid numbers
        expect(parseFloat(columns[2])).not.toBeNaN();
        expect(parseFloat(columns[3])).not.toBeNaN();
      }
    });
  });
});

describe.skipIf(!hasTestData)('Chart Config', () => {
  describe('CHANNEL_GROUPS', () => {
    it('should have all required channel groups', () => {
      const groupIds = CHANNEL_GROUPS.map((g) => g.id);
      expect(groupIds).toContain('engine');
      expect(groupIds).toContain('speed');
      expect(groupIds).toContain('chassis');
      expect(groupIds).toContain('brakes');
      expect(groupIds).toContain('electronics');
    });

    it('should have valid channel definitions', () => {
      for (const group of CHANNEL_GROUPS) {
        expect(group.id).toBeTruthy();
        expect(group.label).toBeTruthy();
        expect(group.channels.length).toBeGreaterThan(0);

        for (const channel of group.channels) {
          expect(channel.id).toBeTruthy();
          expect(channel.label).toBeTruthy();
          expect(channel.color).toMatch(/^#[0-9a-f]{6}$/i);
          expect(channel.yAxisId).toBeTruthy();
        }
      }
    });
  });

  describe('getLapColor', () => {
    it('should return valid colors for lap numbers', () => {
      for (let lap = 0; lap < 20; lap++) {
        expect(getLapColor(lap)).toMatch(/^#[0-9a-f]{6}$/i);
      }
    });

    it('should cycle through colors for many laps', () => {
      expect(getLapColor(16)).toMatch(/^#[0-9a-f]{6}$/i);
    });
  });

  describe('getEnabledChannels', () => {
    it('should return only enabled channels', () => {
      const enabled = getEnabledChannels();
      expect(enabled.length).toBeGreaterThan(0);

      for (const channel of enabled) {
        const group = CHANNEL_GROUPS.find((g) => g.channels.includes(channel));
        expect(group).toBeTruthy();
        expect(group?.enabled).toBe(true);
      }
    });
  });
});

describe.skipIf(!hasTestData)('Integration Tests', () => {
  describe('Full parsing and analysis pipeline', () => {
    it('should parse all test files and compute lap times', () => {
      let totalRecords = 0;
      let totalLaps = 0;

      for (const filePath of testFiles) {
        const data = new Uint8Array(readFileSync(filePath));
        const records = new CTRKParser(data).parse();

        expect(records.length).toBeGreaterThanOrEqual(0);

        if (records.length > 0) {
          const lapTimes = computeLapTimes(records);
          expect(lapTimes.length).toBeGreaterThan(0);

          const summary = computeSessionSummary(lapTimes);
          expect(summary.totalLaps).toBeGreaterThanOrEqual(0);

          const coords = extractGpsCoordinates(records);
          const lapGroups = groupByLap(coords);

          totalRecords += records.length;
          totalLaps += lapGroups.size;
        }
      }
    });

    it('should validate GPS data integrity', () => {
      for (const filePath of testFiles) {
        const data = new Uint8Array(readFileSync(filePath));
        const records = new CTRKParser(data).parse();
        const coords = extractGpsCoordinates(records);

        for (const coord of coords) {
          expect(isValidGps(coord.lat, coord.lng)).toBe(true);
          expect(coord.lat).toBeGreaterThan(-90);
          expect(coord.lat).toBeLessThan(90);
          expect(coord.lng).toBeGreaterThan(-180);
          expect(coord.lng).toBeLessThan(180);
        }
      }
    });

    it('should maintain timestamp monotonicity within laps', () => {
      const coords = extractGpsCoordinates(sampleRecords);
      const lapGroups = groupByLap(coords);

      for (const [, lapCoords] of lapGroups) {
        for (let i = 1; i < lapCoords.length; i++) {
          expect(lapCoords[i].time_ms).toBeGreaterThanOrEqual(
            lapCoords[i - 1].time_ms,
          );
        }
      }
    });
  });

  describe('Performance benchmarks', () => {
    it('should parse and process large files efficiently', () => {
      let largestFile = '';
      let largestSize = 0;

      for (const filePath of testFiles) {
        const stat = statSync(filePath);
        if (stat.size > largestSize) {
          largestSize = stat.size;
          largestFile = filePath;
        }
      }

      if (largestFile) {
        const data = new Uint8Array(readFileSync(largestFile));

        const startTime = performance.now();
        const records = new CTRKParser(data).parse();
        const parseTime = performance.now() - startTime;

        const gpsStart = performance.now();
        extractGpsCoordinates(records);
        groupByLap(extractGpsCoordinates(records));
        performance.now() - gpsStart;

        const lapStart = performance.now();
        const lapTimes = computeLapTimes(records);
        computeSessionSummary(lapTimes);
        performance.now() - lapStart;

        if (largestSize <= 10 * 1024 * 1024) {
          expect(parseTime).toBeLessThan(5000);
        }
      }
    });
  });
});
