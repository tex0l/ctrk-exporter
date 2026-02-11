import { describe, it, expect } from 'vitest';
import { CTRKParser } from './ctrk-parser.js';

describe('CTRKParser', () => {
  describe('constructor', () => {
    it('should accept Uint8Array data', () => {
      const data = new Uint8Array([0x48, 0x45, 0x41, 0x44]); // "HEAD"
      const parser = new CTRKParser(data);
      expect(parser).toBeInstanceOf(CTRKParser);
    });
  });

  describe('parse', () => {
    it('should throw on invalid magic', () => {
      const data = new Uint8Array([0x00, 0x00, 0x00, 0x00]);
      const parser = new CTRKParser(data);
      expect(() => parser.parse()).toThrow('Invalid CTRK file: expected "HEAD" magic');
    });

    it('should parse minimal valid file with no data records', () => {
      // Minimal CTRK file: magic + header padding + null terminator
      const data = new Uint8Array(200);
      data[0] = 0x48; // 'H'
      data[1] = 0x45; // 'E'
      data[2] = 0x41; // 'A'
      data[3] = 0x44; // 'D'

      // Add invalid entry_size at 0x34 to terminate header scan
      data[0x34] = 0x00;
      data[0x35] = 0x00;

      // Add null terminator at data section start
      data[0x34] = 0x00; // rec_type = 0
      data[0x36] = 0x00; // total_size = 0

      const parser = new CTRKParser(data);
      const records = parser.parse();

      // No GPS data, so no records emitted
      expect(records).toHaveLength(0);
    });

    it('should parse file with single GPS record and emit initial record', () => {
      // Build minimal file with GPS record
      const data = new Uint8Array(500);
      data[0] = 0x48; // 'H'
      data[1] = 0x45; // 'E'
      data[2] = 0x41; // 'A'
      data[3] = 0x44; // 'D'

      // Header: add invalid entry at 0x34 to end header
      data[0x34] = 0x00;

      // Data section starts at 0x34
      let pos = 0x34;

      // Record 1: GPS GPRMC (type 2)
      const gprmc = '$GPRMC,120000.000,A,4757.0410,N,00012.5240,E,5.14,0.00,010125,,,A*6E\r\n';
      const gprmcBytes = new TextEncoder().encode(gprmc);
      const totalSize = 14 + gprmcBytes.length;

      // Write record header
      data[pos] = 0x02; // rec_type = 2 (GPS)
      data[pos + 1] = 0x00;
      data[pos + 2] = totalSize & 0xff; // total_size LE
      data[pos + 3] = (totalSize >> 8) & 0xff;

      // Timestamp: 2025-01-01 12:00:00.000
      data[pos + 4] = 0x00; // millis LE
      data[pos + 5] = 0x00;
      data[pos + 6] = 0x00; // sec
      data[pos + 7] = 0x00; // min
      data[pos + 8] = 0x0c; // hour = 12
      data[pos + 9] = 0x04; // wday
      data[pos + 10] = 0x01; // day
      data[pos + 11] = 0x01; // month
      data[pos + 12] = 0xe9; // year = 2025 LE
      data[pos + 13] = 0x07;

      // Write GPRMC payload
      for (let i = 0; i < gprmcBytes.length; i++) {
        data[pos + 14 + i] = gprmcBytes[i];
      }

      pos += totalSize;

      // Null terminator
      data[pos] = 0x00;
      data[pos + 2] = 0x00;

      const parser = new CTRKParser(data.slice(0, pos + 4));
      const records = parser.parse();

      // Should emit initial record after first GPRMC
      expect(records.length).toBeGreaterThanOrEqual(1);
      expect(records[0].latitude).toBeCloseTo(47.950683, 5);
      expect(records[0].longitude).toBeCloseTo(0.208733, 5);
      expect(records[0].gps_speed_knots).toBeCloseTo(5.14, 2);
      expect(records[0].lap).toBe(1);
    });

    it('should not emit records before first GPS fix', () => {
      // Build file with CAN records only (no GPS)
      const data = new Uint8Array(500);
      data[0] = 0x48; // 'H'
      data[1] = 0x45; // 'E'
      data[2] = 0x41; // 'A'
      data[3] = 0x44; // 'D'

      data[0x34] = 0x00;

      let pos = 0x34;

      // Record 1: CAN 0x0209 (RPM)
      const canData = new Uint8Array([
        0x64, 0x00, // RPM = 25600 (BE) -> 10000 RPM calibrated
        0x00, 0x00, 0x01, 0x00,
      ]);
      const totalSize = 14 + 5 + canData.length;

      data[pos] = 0x01; // rec_type = 1 (CAN)
      data[pos + 1] = 0x00;
      data[pos + 2] = totalSize & 0xff;
      data[pos + 3] = (totalSize >> 8) & 0xff;

      // Timestamp
      data[pos + 4] = 0x00;
      data[pos + 5] = 0x00;
      data[pos + 6] = 0x00;
      data[pos + 7] = 0x00;
      data[pos + 8] = 0x0c;
      data[pos + 9] = 0x04;
      data[pos + 10] = 0x01;
      data[pos + 11] = 0x01;
      data[pos + 12] = 0xe9;
      data[pos + 13] = 0x07;

      // CAN payload
      data[pos + 14] = 0x09; // CAN ID = 0x0209 LE
      data[pos + 15] = 0x02;
      data[pos + 16] = 0x00; // padding
      data[pos + 17] = 0x00;
      data[pos + 18] = canData.length; // DLC
      for (let i = 0; i < canData.length; i++) {
        data[pos + 19 + i] = canData[i];
      }

      pos += totalSize;

      // Null terminator
      data[pos] = 0x00;
      data[pos + 2] = 0x00;

      const parser = new CTRKParser(data.slice(0, pos + 4));
      const records = parser.parse();

      // No GPS, so no emission
      expect(records).toHaveLength(0);
    });

    it('should parse CAN messages and update state', () => {
      // Build file with CAN + GPS
      const data = new Uint8Array(500);
      data[0] = 0x48; // 'H'
      data[1] = 0x45; // 'E'
      data[2] = 0x41; // 'A'
      data[3] = 0x44; // 'D'

      data[0x34] = 0x00;
      let pos = 0x34;

      // Record 1: CAN 0x0209 (RPM + Gear)
      const canPayload = new Uint8Array([
        0x64, 0x00, // RPM = 25600 (BE)
        0x00, 0x00, 0x03, 0x00, // Gear = 3
      ]);
      let totalSize = 14 + 5 + canPayload.length;

      data[pos] = 0x01; // CAN
      data[pos + 1] = 0x00;
      data[pos + 2] = totalSize & 0xff;
      data[pos + 3] = 0x00;
      // Timestamp: 2025-01-01 12:00:00.000
      data[pos + 4] = 0x00;
      data[pos + 5] = 0x00;
      data[pos + 6] = 0x00;
      data[pos + 7] = 0x00;
      data[pos + 8] = 0x0c;
      data[pos + 9] = 0x04;
      data[pos + 10] = 0x01;
      data[pos + 11] = 0x01;
      data[pos + 12] = 0xe9;
      data[pos + 13] = 0x07;
      // CAN payload
      data[pos + 14] = 0x09; // CAN ID LE
      data[pos + 15] = 0x02;
      data[pos + 16] = 0x00;
      data[pos + 17] = 0x00;
      data[pos + 18] = canPayload.length;
      for (let i = 0; i < canPayload.length; i++) {
        data[pos + 19 + i] = canPayload[i];
      }
      pos += totalSize;

      // Record 2: GPS
      const gprmc = '$GPRMC,120000.000,A,4757.0410,N,00012.5240,E,5.14,0.00,010125,,,A*6E\r\n';
      const gprmcBytes = new TextEncoder().encode(gprmc);
      totalSize = 14 + gprmcBytes.length;

      data[pos] = 0x02; // GPS
      data[pos + 1] = 0x00;
      data[pos + 2] = totalSize & 0xff;
      data[pos + 3] = 0x00;
      // Timestamp: same second
      data[pos + 4] = 0x00;
      data[pos + 5] = 0x00;
      data[pos + 6] = 0x00;
      data[pos + 7] = 0x00;
      data[pos + 8] = 0x0c;
      data[pos + 9] = 0x04;
      data[pos + 10] = 0x01;
      data[pos + 11] = 0x01;
      data[pos + 12] = 0xe9;
      data[pos + 13] = 0x07;
      for (let i = 0; i < gprmcBytes.length; i++) {
        data[pos + 14 + i] = gprmcBytes[i];
      }
      pos += totalSize;

      // Null terminator
      data[pos] = 0x00;
      data[pos + 2] = 0x00;

      const parser = new CTRKParser(data.slice(0, pos + 4));
      const records = parser.parse();

      expect(records.length).toBeGreaterThanOrEqual(1);
      expect(records[0].rpm).toBe(25600); // Raw value
      expect(records[0].gear).toBe(3);
    });

    it('should reject GPRMC with bad checksum', () => {
      // Build file with bad checksum GPRMC
      const data = new Uint8Array(500);
      data[0] = 0x48; // 'H'
      data[1] = 0x45; // 'E'
      data[2] = 0x41; // 'A'
      data[3] = 0x44; // 'D'

      data[0x34] = 0x00;
      let pos = 0x34;

      // GPS with invalid checksum
      const gprmc = '$GPRMC,120000.000,A,4757.0410,N,00012.5240,E,5.14,0.00,010125,,,A*FF\r\n';
      const gprmcBytes = new TextEncoder().encode(gprmc);
      const totalSize = 14 + gprmcBytes.length;

      data[pos] = 0x02; // GPS
      data[pos + 1] = 0x00;
      data[pos + 2] = totalSize & 0xff;
      data[pos + 3] = 0x00;
      data[pos + 4] = 0x00;
      data[pos + 5] = 0x00;
      data[pos + 6] = 0x00;
      data[pos + 7] = 0x00;
      data[pos + 8] = 0x0c;
      data[pos + 9] = 0x04;
      data[pos + 10] = 0x01;
      data[pos + 11] = 0x01;
      data[pos + 12] = 0xe9;
      data[pos + 13] = 0x07;
      for (let i = 0; i < gprmcBytes.length; i++) {
        data[pos + 14 + i] = gprmcBytes[i];
      }
      pos += totalSize;

      // Null terminator
      data[pos] = 0x00;
      data[pos + 2] = 0x00;

      const parser = new CTRKParser(data.slice(0, pos + 4));
      const records = parser.parse();

      // Bad checksum -> no emission
      expect(records).toHaveLength(0);
    });
  });

  describe('getRecords', () => {
    it('should return empty array before parse', () => {
      const data = new Uint8Array([0x48, 0x45, 0x41, 0x44]);
      const parser = new CTRKParser(data);
      expect(parser.getRecords()).toHaveLength(0);
    });
  });
});
