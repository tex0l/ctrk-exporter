import { describe, it, expect } from 'vitest';
import {
  getTimeData,
  getTimeDataEx,
  createTimestampState,
  timestampsEqual,
} from './timestamp.js';

describe('timestamp', () => {
  describe('getTimeData', () => {
    it('should convert full timestamp to epoch milliseconds', () => {
      // 2025-07-29 12:21:34.879
      const tsBytes = new Uint8Array([
        0x6f, 0x03, // millis = 879 (LE)
        0x22, // sec = 34
        0x15, // min = 21
        0x0c, // hour = 12
        0x02, // wday = Tuesday
        0x1d, // day = 29
        0x07, // month = 7 (July)
        0xe9, 0x07, // year = 2025 (LE)
      ]);

      const epochMs = getTimeData(tsBytes);

      // Verify date components
      const dt = new Date(epochMs);
      expect(dt.getUTCFullYear()).toBe(2025);
      expect(dt.getUTCMonth()).toBe(6); // 0-based (6 = July)
      expect(dt.getUTCDate()).toBe(29);
      expect(dt.getUTCHours()).toBe(12);
      expect(dt.getUTCMinutes()).toBe(21);
      expect(dt.getUTCSeconds()).toBe(34);
      expect(dt.getUTCMilliseconds()).toBe(879);
    });

    it('should handle year 2000 default date', () => {
      // 2000-01-01 00:00:00.000
      const tsBytes = new Uint8Array([
        0x00, 0x00, // millis = 0
        0x00, // sec = 0
        0x00, // min = 0
        0x00, // hour = 0
        0x06, // wday = Saturday
        0x01, // day = 1
        0x01, // month = 1
        0xd0, 0x07, // year = 2000 (LE)
      ]);

      const epochMs = getTimeData(tsBytes);
      const dt = new Date(epochMs);
      expect(dt.getUTCFullYear()).toBe(2000);
      expect(dt.getUTCMonth()).toBe(0);
      expect(dt.getUTCDate()).toBe(1);
    });

    it('should throw on insufficient bytes', () => {
      const tsBytes = new Uint8Array([0x00, 0x00, 0x00]); // Only 3 bytes
      expect(() => getTimeData(tsBytes)).toThrow('Timestamp must be at least 10 bytes');
    });
  });

  describe('getTimeDataEx', () => {
    it('should compute full timestamp on first call', () => {
      const state = createTimestampState();
      const tsBytes = new Uint8Array([
        0x6f, 0x03, 0x22, 0x15, 0x0c, 0x02, 0x1d, 0x07, 0xe9, 0x07,
      ]);

      const epochMs = getTimeDataEx(tsBytes, state);
      expect(epochMs).toBeGreaterThan(0);
      expect(state.prevTsBytes).not.toBeNull();
      expect(state.prevEpochMs).toBe(epochMs);
    });

    it('should reuse previous value for identical timestamps', () => {
      const state = createTimestampState();
      const tsBytes1 = new Uint8Array([
        0x6f, 0x03, 0x22, 0x15, 0x0c, 0x02, 0x1d, 0x07, 0xe9, 0x07,
      ]);
      const tsBytes2 = new Uint8Array([
        0x6f, 0x03, 0x22, 0x15, 0x0c, 0x02, 0x1d, 0x07, 0xe9, 0x07,
      ]);

      const epochMs1 = getTimeDataEx(tsBytes1, state);
      const epochMs2 = getTimeDataEx(tsBytes2, state);

      expect(epochMs1).toBe(epochMs2);
    });

    it('should update millis incrementally for same second', () => {
      const state = createTimestampState();

      // First record: 12:21:34.879
      const tsBytes1 = new Uint8Array([
        0x6f, 0x03, // millis = 879
        0x22, 0x15, 0x0c, 0x02, 0x1d, 0x07, 0xe9, 0x07,
      ]);

      // Second record: 12:21:34.920 (41ms later, same second)
      const tsBytes2 = new Uint8Array([
        0x98, 0x03, // millis = 920
        0x22, 0x15, 0x0c, 0x02, 0x1d, 0x07, 0xe9, 0x07,
      ]);

      const epochMs1 = getTimeDataEx(tsBytes1, state);
      const epochMs2 = getTimeDataEx(tsBytes2, state);

      // Delta should be 41ms
      expect(epochMs2 - epochMs1).toBe(41);
    });

    it('should handle millis wrapping within same second', () => {
      const state = createTimestampState();

      // First record: 12:21:34.999
      const tsBytes1 = new Uint8Array([
        0xe7, 0x03, // millis = 999
        0x22, 0x15, 0x0c, 0x02, 0x1d, 0x07, 0xe9, 0x07,
      ]);

      // Second record: 12:21:34.008 (millis wrapped but second not incremented yet)
      const tsBytes2 = new Uint8Array([
        0x08, 0x00, // millis = 8
        0x22, 0x15, 0x0c, 0x02, 0x1d, 0x07, 0xe9, 0x07,
      ]);

      const epochMs1 = getTimeDataEx(tsBytes1, state);
      const epochMs2 = getTimeDataEx(tsBytes2, state);

      // Delta should be 9ms (not -991ms)
      const delta = epochMs2 - epochMs1;
      expect(delta).toBe(9);
      expect(delta).toBeGreaterThan(0);
    });

    it('should recompute full timestamp when second changes', () => {
      const state = createTimestampState();

      // First record: 12:21:34.879
      const tsBytes1 = new Uint8Array([
        0x6f, 0x03, 0x22, 0x15, 0x0c, 0x02, 0x1d, 0x07, 0xe9, 0x07,
      ]);

      // Second record: 12:21:35.020 (different second)
      const tsBytes2 = new Uint8Array([
        0x14, 0x00, // millis = 20
        0x23, // sec = 35 (changed)
        0x15, 0x0c, 0x02, 0x1d, 0x07, 0xe9, 0x07,
      ]);

      const epochMs1 = getTimeDataEx(tsBytes1, state);
      const epochMs2 = getTimeDataEx(tsBytes2, state);

      // Delta should be ~141ms (to next second + 20ms)
      const delta = epochMs2 - epochMs1;
      expect(delta).toBeGreaterThanOrEqual(140);
      expect(delta).toBeLessThanOrEqual(142);
    });
  });

  describe('timestampsEqual', () => {
    it('should return true for identical timestamps', () => {
      const ts1 = new Uint8Array([0x6f, 0x03, 0x22, 0x15, 0x0c, 0x02, 0x1d, 0x07, 0xe9, 0x07]);
      const ts2 = new Uint8Array([0x6f, 0x03, 0x22, 0x15, 0x0c, 0x02, 0x1d, 0x07, 0xe9, 0x07]);
      expect(timestampsEqual(ts1, ts2)).toBe(true);
    });

    it('should return false for different timestamps', () => {
      const ts1 = new Uint8Array([0x6f, 0x03, 0x22, 0x15, 0x0c, 0x02, 0x1d, 0x07, 0xe9, 0x07]);
      const ts2 = new Uint8Array([0x70, 0x03, 0x22, 0x15, 0x0c, 0x02, 0x1d, 0x07, 0xe9, 0x07]);
      expect(timestampsEqual(ts1, ts2)).toBe(false);
    });

    it('should return false for wrong length', () => {
      const ts1 = new Uint8Array([0x6f, 0x03, 0x22, 0x15, 0x0c]);
      const ts2 = new Uint8Array([0x6f, 0x03, 0x22, 0x15, 0x0c, 0x02, 0x1d, 0x07, 0xe9, 0x07]);
      expect(timestampsEqual(ts1, ts2)).toBe(false);
    });
  });
});
