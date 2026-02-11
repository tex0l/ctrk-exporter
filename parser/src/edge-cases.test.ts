/**
 * Edge case test suite - Tests parser robustness with extreme inputs.
 *
 * Uses committed test files in parser/test-data/ (15 files, 30KB to 8.4MB).
 */

import { describe, it, expect } from 'vitest';
import { readFileSync, readdirSync, statSync } from 'fs';
import { join } from 'path';
import { CTRKParser } from './ctrk-parser';

const TEST_DATA_DIR = join(__dirname, '..', 'test-data');

describe('Edge Case Tests', () => {
  describe('Minimal files', () => {
    it('should parse file with only 102 records (20250829-192509.CTRK)', () => {
      const data = readFileSync(join(TEST_DATA_DIR, '20250829-192509.CTRK'));
      const records = new CTRKParser(new Uint8Array(data)).parse();

      expect(records.length).toBeGreaterThanOrEqual(100);
      expect(records.length).toBeLessThanOrEqual(110);

      for (const record of records) {
        expect(record.lap).toBeGreaterThanOrEqual(1);
        expect(record.time_ms).toBeGreaterThanOrEqual(0);
        expect(record.gear).toBeGreaterThanOrEqual(0);
        expect(record.gear).toBeLessThanOrEqual(6);
      }
    });

    it('should parse file with only 129 records (20250905-101210.CTRK)', () => {
      const data = readFileSync(join(TEST_DATA_DIR, '20250905-101210.CTRK'));
      const records = new CTRKParser(new Uint8Array(data)).parse();

      expect(records.length).toBeGreaterThanOrEqual(120);
      expect(records.length).toBeLessThanOrEqual(140);
    });

    it('should parse file with only 138 records (20250829-201501.CTRK)', () => {
      const data = readFileSync(join(TEST_DATA_DIR, '20250829-201501.CTRK'));
      const records = new CTRKParser(new Uint8Array(data)).parse();

      expect(records.length).toBeGreaterThanOrEqual(130);
      expect(records.length).toBeLessThanOrEqual(150);
    });
  });

  describe('Default date files', () => {
    it('should parse file with default date 2000-01-01 (20000101-010216.CTRK)', () => {
      const data = readFileSync(join(TEST_DATA_DIR, '20000101-010216.CTRK'));
      const records = new CTRKParser(new Uint8Array(data)).parse();

      expect(records.length).toBeGreaterThan(1000);

      for (const record of records) {
        expect(record.lap).toBeGreaterThanOrEqual(1);
        expect(record.time_ms).toBeGreaterThanOrEqual(0);
      }
    });
  });

  describe('Small files', () => {
    it('should parse 30KB file (20250829-192509.CTRK)', () => {
      const data = readFileSync(join(TEST_DATA_DIR, '20250829-192509.CTRK'));
      const records = new CTRKParser(new Uint8Array(data)).parse();
      expect(records.length).toBeGreaterThan(0);
    });

    it('should parse 42KB file (20250829-201501.CTRK)', () => {
      const data = readFileSync(join(TEST_DATA_DIR, '20250829-201501.CTRK'));
      const records = new CTRKParser(new Uint8Array(data)).parse();
      expect(records.length).toBeGreaterThan(0);
    });
  });

  describe('Large files', () => {
    it('should parse 8MB file with 24,494 records (20250906-151214.CTRK)', () => {
      const data = readFileSync(join(TEST_DATA_DIR, '20250906-151214.CTRK'));
      const records = new CTRKParser(new Uint8Array(data)).parse();

      expect(records.length).toBeGreaterThan(24000);
      expect(records.length).toBeLessThan(25000);
      expect(records[0].lap).toBe(1);
      expect(records[records.length - 1].lap).toBeGreaterThanOrEqual(1);
    });

    it('should parse 5.6MB file (20250729-170818.CTRK)', () => {
      const data = readFileSync(join(TEST_DATA_DIR, '20250729-170818.CTRK'));
      const records = new CTRKParser(new Uint8Array(data)).parse();
      expect(records.length).toBeGreaterThan(15000);
      expect(records.length).toBeLessThan(17000);
    });
  });

  describe('All test-data files - robustness test', () => {
    it('should parse all files without crashing', () => {
      const files = readdirSync(TEST_DATA_DIR)
        .filter((f) => f.endsWith('.CTRK'))
        .sort();

      expect(files.length).toBeGreaterThanOrEqual(15);

      let totalRecords = 0;
      let totalBytes = 0;
      const failedFiles: string[] = [];

      for (const file of files) {
        try {
          const filePath = join(TEST_DATA_DIR, file);
          const stats = statSync(filePath);
          const data = readFileSync(filePath);
          totalBytes += stats.size;

          const records = new CTRKParser(new Uint8Array(data)).parse();
          totalRecords += records.length;

          expect(Array.isArray(records)).toBe(true);
          if (records.length > 0) {
            expect(records[0]).toHaveProperty('lap');
            expect(records[0]).toHaveProperty('time_ms');
            expect(records[0]).toHaveProperty('rpm');
            expect(records[0]).toHaveProperty('gear');
          }
        } catch (error: any) {
          failedFiles.push(`${file}: ${error.message}`);
        }
      }

      expect(failedFiles.length).toBe(0);
    });
  });

  describe('Performance benchmarks', () => {
    it('should parse largest file (8MB) in under 5 seconds', () => {
      const data = readFileSync(join(TEST_DATA_DIR, '20250906-151214.CTRK'));

      const start = Date.now();
      const records = new CTRKParser(new Uint8Array(data)).parse();
      const duration = Date.now() - start;

      expect(duration).toBeLessThan(5000);
      expect(records.length).toBeGreaterThan(20000);
    });

    it('should parse medium file (2.8MB) in under 2 seconds', () => {
      const data = readFileSync(join(TEST_DATA_DIR, '20250729-155522.CTRK'));

      const start = Date.now();
      const records = new CTRKParser(new Uint8Array(data)).parse();
      const duration = Date.now() - start;

      expect(duration).toBeLessThan(2000);
    });

    it('should parse small file (30KB) in under 50ms', () => {
      const data = readFileSync(join(TEST_DATA_DIR, '20250829-192509.CTRK'));

      const start = Date.now();
      new CTRKParser(new Uint8Array(data)).parse();
      const duration = Date.now() - start;

      expect(duration).toBeLessThan(50);
    });
  });

  describe('Data integrity checks', () => {
    it('should maintain monotonic timestamps within each lap', () => {
      const data = readFileSync(join(TEST_DATA_DIR, '20250906-151214.CTRK'));
      const records = new CTRKParser(new Uint8Array(data)).parse();

      let currentLap = 1;
      let previousTime = 0;

      for (const record of records) {
        if (record.lap !== currentLap) {
          currentLap = record.lap;
          previousTime = record.time_ms;
        } else {
          expect(record.time_ms).toBeGreaterThanOrEqual(previousTime);
          previousTime = record.time_ms;
        }
      }
    });

    it(
      'should have valid channel ranges for all records',
      () => {
        const data = readFileSync(join(TEST_DATA_DIR, '20250906-151214.CTRK'));
        const records = new CTRKParser(new Uint8Array(data)).parse();

        for (const record of records) {
          expect(record.rpm).toBeGreaterThanOrEqual(0);
          expect(record.rpm).toBeLessThanOrEqual(51200);
          expect(record.lean).toBeGreaterThanOrEqual(0);
          expect(record.lean).toBeLessThanOrEqual(18000);
          expect(record.gear).toBeGreaterThanOrEqual(0);
          expect(record.gear).toBeLessThanOrEqual(6);
          expect(record.tps).toBeGreaterThanOrEqual(0);
          expect(record.tps).toBeLessThanOrEqual(8191);
          expect(record.aps).toBeGreaterThanOrEqual(0);
          expect(record.aps).toBeLessThanOrEqual(8191);
          expect(record.front_speed).toBeGreaterThanOrEqual(0);
          expect(record.front_speed).toBeLessThanOrEqual(65535);
          expect(record.rear_speed).toBeGreaterThanOrEqual(0);
          expect(record.rear_speed).toBeLessThanOrEqual(65535);
          expect(record.fuel).toBeGreaterThanOrEqual(0);
          expect(record.fuel).toBeLessThanOrEqual(65535);
          expect(record.water_temp).toBeGreaterThanOrEqual(0);
          expect(record.water_temp).toBeLessThanOrEqual(65535);
          expect(record.intake_temp).toBeGreaterThanOrEqual(0);
          expect(record.intake_temp).toBeLessThanOrEqual(65535);
          expect(record.front_brake).toBeGreaterThanOrEqual(0);
          expect(record.front_brake).toBeLessThanOrEqual(65535);
          expect(record.rear_brake).toBeGreaterThanOrEqual(0);
          expect(record.rear_brake).toBeLessThanOrEqual(65535);
          expect(record.acc_x).toBeGreaterThanOrEqual(0);
          expect(record.acc_x).toBeLessThanOrEqual(14000);
          expect(record.acc_y).toBeGreaterThanOrEqual(0);
          expect(record.acc_y).toBeLessThanOrEqual(14000);
          expect(record.pitch).toBeGreaterThanOrEqual(0);
          expect(record.pitch).toBeLessThanOrEqual(65535);
          expect(typeof record.f_abs).toBe('boolean');
          expect(typeof record.r_abs).toBe('boolean');
          expect(record.tcs).toBeGreaterThanOrEqual(0);
          expect(record.tcs).toBeLessThanOrEqual(1);
          expect(record.scs).toBeGreaterThanOrEqual(0);
          expect(record.scs).toBeLessThanOrEqual(1);
          expect(record.lif).toBeGreaterThanOrEqual(0);
          expect(record.lif).toBeLessThanOrEqual(1);
          expect(record.launch).toBeGreaterThanOrEqual(0);
          expect(record.launch).toBeLessThanOrEqual(1);
        }
      },
      30_000,
    );

    it('should detect multiple laps correctly', () => {
      const data = readFileSync(join(TEST_DATA_DIR, '20250906-151214.CTRK'));
      const records = new CTRKParser(new Uint8Array(data)).parse();

      const uniqueLaps = new Set(records.map((r) => r.lap));
      expect(uniqueLaps.size).toBeGreaterThan(1);

      const laps = Array.from(uniqueLaps).sort((a, b) => a - b);
      for (let i = 1; i < laps.length; i++) {
        expect(laps[i]).toBe(laps[i - 1] + 1);
      }
    });
  });
});
