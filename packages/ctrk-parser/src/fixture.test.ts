/**
 * Integration tests using the committed Sample.CTRK fixture.
 *
 * This file is extracted from the official Yamaha Y-Trac APK and is always
 * available in CI, unlike the symlinked test-data files from input/.
 */

import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { join } from 'path';
import { CTRKParser } from './ctrk-parser.js';
import { Calibration } from './calibration.js';

const FIXTURE_PATH = join(__dirname, '..', 'test-data', 'fixtures', 'Sample.CTRK');

describe('Sample.CTRK fixture', () => {
  const data = readFileSync(FIXTURE_PATH);
  const parser = new CTRKParser(new Uint8Array(data));
  const records = parser.parse();

  it('should parse without errors', () => {
    expect(records.length).toBeGreaterThan(0);
  });

  it('should produce 4,190 records', () => {
    expect(records.length).toBe(4190);
  });

  it('should detect 4 laps', () => {
    const laps = new Set(records.map(r => r.lap));
    expect(laps.size).toBe(4);
    expect(Array.from(laps).sort((a, b) => a - b)).toEqual([1, 2, 3, 4]);
  });

  it('should have GPS coordinates near Sydney Motorsport Park', () => {
    // Sydney Motorsport Park: approx -33.80, 150.87
    const first = records[0];
    expect(first.latitude).toBeGreaterThan(-34);
    expect(first.latitude).toBeLessThan(-33.5);
    expect(first.longitude).toBeGreaterThan(150.5);
    expect(first.longitude).toBeLessThan(151.5);
  });

  it('should have monotonic timestamps within each lap', () => {
    let currentLap = 1;
    let prevTime = 0;

    for (const record of records) {
      if (record.lap !== currentLap) {
        currentLap = record.lap;
        prevTime = record.time_ms;
      } else {
        expect(record.time_ms).toBeGreaterThanOrEqual(prevTime);
        prevTime = record.time_ms;
      }
    }
  });

  it('should have valid channel ranges', () => {
    for (const r of records) {
      expect(r.gear).toBeGreaterThanOrEqual(0);
      expect(r.gear).toBeLessThanOrEqual(6);
      expect(r.rpm).toBeGreaterThanOrEqual(0);
      expect(r.rpm).toBeLessThanOrEqual(51200);
      expect(typeof r.f_abs).toBe('boolean');
      expect(typeof r.r_abs).toBe('boolean');
    }
  });

  it('should produce valid calibrated values', () => {
    const mid = records[Math.floor(records.length / 2)];
    const rpm = Calibration.rpm(mid.rpm);
    const speed = Calibration.wheelSpeedKmh(mid.front_speed);

    expect(rpm).toBeGreaterThanOrEqual(0);
    expect(rpm).toBeLessThanOrEqual(20000);
    expect(speed).toBeGreaterThanOrEqual(0);
    expect(speed).toBeLessThanOrEqual(400);
  });

  it('should parse within 2 seconds', () => {
    const start = Date.now();
    const freshParser = new CTRKParser(new Uint8Array(data));
    freshParser.parse();
    const duration = Date.now() - start;

    expect(duration).toBeLessThan(2000);
  });
});
