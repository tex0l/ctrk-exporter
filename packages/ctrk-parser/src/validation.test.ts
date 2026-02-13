/**
 * Cross-validation test suite - TypeScript parser vs Python parser (ground truth).
 *
 * Parses all CTRK test files with the TS parser, calibrates values, and compares
 * record-by-record against Python CSV ground truth. No pre-built dist/ or external
 * scripts required.
 *
 * Test data:
 * - 15 CTRK files in parser/test-data/
 * - Python CSV ground truth in parser/test-data/python-output/
 */

import { describe, it, expect, beforeAll } from 'vitest';
import { existsSync, readFileSync, readdirSync } from 'fs';
import { join, basename } from 'path';
import { CTRKParser } from './ctrk-parser.js';
import { Calibration } from './calibration.js';
import type { TelemetryRecord } from './types.js';

const TEST_DATA_DIR = join(__dirname, '..', 'test-data');
const PYTHON_OUTPUT_DIR = join(TEST_DATA_DIR, 'python-output');
const hasTestData = existsSync(TEST_DATA_DIR) &&
  readdirSync(TEST_DATA_DIR).some(f => f.endsWith('.CTRK'));

// Tolerances per channel (maximum allowed absolute difference)
const TOLERANCES: Record<string, number> = {
  rpm: 2,
  throttle_grip: 0.5,
  throttle: 0.5,
  front_speed_kmh: 0.5,
  rear_speed_kmh: 0.5,
  gps_speed_kmh: 0.5,
  gear: 0,
  acc_x_g: 0.02,
  acc_y_g: 0.02,
  lean_deg: 0.5,
  lean_signed_deg: 0.5,
  pitch_deg_s: 0.5,
  water_temp: 0.5,
  intake_temp: 0.5,
  fuel_cc: 0.05,
  front_brake_bar: 0.1,
  rear_brake_bar: 0.1,
  f_abs: 0,
  r_abs: 0,
  tcs: 0,
  scs: 0,
  lif: 0,
  launch: 0,
};

const CHANNELS = Object.keys(TOLERANCES);

interface CalibratedRecord {
  lap: number;
  time_ms: number;
  [key: string]: number | boolean;
}

interface ChannelStats {
  matches: number;
  total: number;
  maxDiff: number;
}

interface FileResult {
  fileName: string;
  tsRecordCount: number;
  pyRecordCount: number;
  alignedRecords: number;
  overallMatchRate: number;
  channelStats: Record<string, ChannelStats>;
}

/** Parse a Python CSV file into records. */
function parsePythonCsv(csvPath: string): Record<string, any>[] {
  const content = readFileSync(csvPath, 'utf-8');
  const lines = content.trim().split('\n');
  const headers = lines[0].split(',').map((h) => h.trim());

  return lines.slice(1).map((line) => {
    const values = line.split(',');
    const record: Record<string, any> = {};

    headers.forEach((header, i) => {
      const value = values[i]?.trim() || '';
      if (value === 'true' || value === 'false') {
        record[header] = value === 'true';
      } else if (value !== '' && !isNaN(parseFloat(value))) {
        record[header] = parseFloat(value);
      } else {
        record[header] = value;
      }
    });

    return record;
  });
}

/** Calibrate a raw TelemetryRecord to engineering units matching Python CSV columns. */
function calibrateRecord(raw: TelemetryRecord): CalibratedRecord {
  return {
    lap: raw.lap,
    time_ms: raw.time_ms,
    gps_speed_kmh: Calibration.gpsSpeedKmh(raw.gps_speed_knots),
    rpm: Calibration.rpm(raw.rpm),
    throttle_grip: Calibration.throttle(raw.aps),
    throttle: Calibration.throttle(raw.tps),
    water_temp: Calibration.temperature(raw.water_temp),
    intake_temp: Calibration.temperature(raw.intake_temp),
    front_speed_kmh: Calibration.wheelSpeedKmh(raw.front_speed),
    rear_speed_kmh: Calibration.wheelSpeedKmh(raw.rear_speed),
    fuel_cc: Calibration.fuel(raw.fuel),
    lean_deg: Calibration.lean(raw.lean),
    lean_signed_deg: Calibration.lean(raw.lean_signed),
    pitch_deg_s: Calibration.pitch(raw.pitch),
    acc_x_g: Calibration.acceleration(raw.acc_x),
    acc_y_g: Calibration.acceleration(raw.acc_y),
    front_brake_bar: Calibration.brake(raw.front_brake),
    rear_brake_bar: Calibration.brake(raw.rear_brake),
    gear: raw.gear,
    f_abs: raw.f_abs,
    r_abs: raw.r_abs,
    tcs: raw.tcs,
    scs: raw.scs,
    lif: raw.lif,
    launch: raw.launch,
  };
}

/** Validate one CTRK file against its Python CSV ground truth. */
function validateFile(ctrkPath: string, pythonCsvPath: string): FileResult {
  const fileName = basename(ctrkPath, '.CTRK');

  // Parse with TypeScript parser
  const ctrkData = readFileSync(ctrkPath);
  const parser = new CTRKParser(new Uint8Array(ctrkData));
  const tsRecords = parser.parse().map(calibrateRecord);

  // Load Python ground truth
  const pyRecords = parsePythonCsv(pythonCsvPath);

  const alignedCount = Math.min(tsRecords.length, pyRecords.length);
  const channelStats: Record<string, ChannelStats> = {};

  for (const channel of CHANNELS) {
    channelStats[channel] = { matches: 0, total: 0, maxDiff: 0 };
  }

  for (let i = 0; i < alignedCount; i++) {
    const ts = tsRecords[i];
    const py = pyRecords[i];

    for (const channel of CHANNELS) {
      const tsVal = ts[channel];
      const pyVal = py[channel];
      const tolerance = TOLERANCES[channel];
      const stats = channelStats[channel];

      stats.total++;

      if (typeof tsVal === 'boolean' && typeof pyVal === 'boolean') {
        if (tsVal === pyVal) stats.matches++;
      } else {
        const diff = Math.abs(Number(tsVal) - Number(pyVal));
        if (diff <= tolerance) stats.matches++;
        if (diff > stats.maxDiff) stats.maxDiff = diff;
      }
    }
  }

  const totalComparisons = alignedCount * CHANNELS.length;
  const totalMatches = Object.values(channelStats).reduce((s, c) => s + c.matches, 0);

  return {
    fileName,
    tsRecordCount: tsRecords.length,
    pyRecordCount: pyRecords.length,
    alignedRecords: alignedCount,
    overallMatchRate: totalComparisons > 0 ? totalMatches / totalComparisons : 0,
    channelStats,
  };
}

// ---- Test suite ----

describe.skipIf(!hasTestData)('Cross-validation: TypeScript parser vs Python ground truth', () => {
  let fileResults: FileResult[] = [];
  let globalChannelStats: Record<string, ChannelStats> = {};
  let totalAlignedRecords = 0;

  beforeAll(() => {
    // Discover test files
    const ctrkFiles = readdirSync(TEST_DATA_DIR)
      .filter((f) => f.endsWith('.CTRK'))
      .sort();

    for (const channel of CHANNELS) {
      globalChannelStats[channel] = { matches: 0, total: 0, maxDiff: 0 };
    }

    for (const ctrkFile of ctrkFiles) {
      const baseName = basename(ctrkFile, '.CTRK');
      const pythonCsvPath = join(PYTHON_OUTPUT_DIR, `${baseName}_parsed.csv`);

      try {
        readFileSync(pythonCsvPath); // check existence
      } catch {
        continue; // skip files without ground truth
      }

      const result = validateFile(join(TEST_DATA_DIR, ctrkFile), pythonCsvPath);
      fileResults.push(result);
      totalAlignedRecords += result.alignedRecords;

      for (const channel of CHANNELS) {
        const g = globalChannelStats[channel];
        const f = result.channelStats[channel];
        g.matches += f.matches;
        g.total += f.total;
        g.maxDiff = Math.max(g.maxDiff, f.maxDiff);
      }
    }
  }, 120_000);

  // -- Coverage --

  it('should validate at least 10 CTRK files', () => {
    expect(fileResults.length).toBeGreaterThanOrEqual(10);
  });

  it('should validate at least 100,000 records', () => {
    expect(totalAlignedRecords).toBeGreaterThanOrEqual(100_000);
  });

  it('should track all 23 channels', () => {
    expect(Object.keys(globalChannelStats)).toHaveLength(23);
  });

  // -- Global match rates --

  it('overall match rate >= 95%', () => {
    const total = Object.values(globalChannelStats).reduce((s, c) => s + c.total, 0);
    const matches = Object.values(globalChannelStats).reduce((s, c) => s + c.matches, 0);
    expect(matches / total).toBeGreaterThanOrEqual(0.95);
  });

  // -- Per-channel tolerance assertions --

  describe.each(CHANNELS.map((ch) => [ch, TOLERANCES[ch]] as const))(
    'channel %s (tolerance ±%s)',
    (channel, tolerance) => {
      it('match rate >= 90%', () => {
        const stats = globalChannelStats[channel];
        expect(stats.total).toBeGreaterThan(0);
        expect(stats.matches / stats.total).toBeGreaterThanOrEqual(0.9);
      });

      it(`max diff <= ${tolerance}`, () => {
        const stats = globalChannelStats[channel];
        expect(stats.maxDiff).toBeLessThanOrEqual(tolerance);
      });
    },
  );

  // -- Per-file assertions --

  it('every file should have matching record counts', () => {
    for (const result of fileResults) {
      expect(
        result.tsRecordCount,
        `${result.fileName}: TS=${result.tsRecordCount} vs Python=${result.pyRecordCount}`,
      ).toBe(result.pyRecordCount);
    }
  });

  it('every file should achieve >= 90% overall match rate', () => {
    for (const result of fileResults) {
      expect(
        result.overallMatchRate,
        `${result.fileName}: ${(result.overallMatchRate * 100).toFixed(2)}%`,
      ).toBeGreaterThanOrEqual(0.9);
    }
  });
});
