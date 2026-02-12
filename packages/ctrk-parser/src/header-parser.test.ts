import { describe, it, expect } from 'vitest';
import {
  validateMagic,
  findDataStart,
  parseFinishLine,
} from './header-parser.js';
import { BufferReader } from './buffer-reader.js';

describe('Header Parser', () => {
  describe('validateMagic', () => {
    it('should validate correct magic', () => {
      const magic = new Uint8Array([0x48, 0x45, 0x41, 0x44]); // "HEAD"
      expect(validateMagic(magic)).toBe(true);
    });

    it('should reject incorrect magic', () => {
      const magic = new Uint8Array([0x48, 0x45, 0x41, 0x45]); // "HEAE"
      expect(validateMagic(magic)).toBe(false);
    });

    it('should reject short data', () => {
      const magic = new Uint8Array([0x48, 0x45]);
      expect(validateMagic(magic)).toBe(false);
    });
  });

  describe('findDataStart', () => {
    it('should find data start after variable entries', () => {
      // Build a minimal header with one entry
      const header = new Uint8Array(100);
      header.set([0x48, 0x45, 0x41, 0x44]); // Magic at 0x00

      // Entry at 0x34: size=20, name_len=4, name="TEST"
      const entryOffset = 0x34;
      header[entryOffset] = 20; // entry_size (LE)
      header[entryOffset + 1] = 0;
      header[entryOffset + 2] = 0;
      header[entryOffset + 3] = 0;
      header[entryOffset + 4] = 4; // name_len
      header[entryOffset + 5] = 0x54; // 'T'
      header[entryOffset + 6] = 0x45; // 'E'
      header[entryOffset + 7] = 0x53; // 'S'
      header[entryOffset + 8] = 0x54; // 'T'

      const reader = new BufferReader(header);
      const dataStart = findDataStart(reader);

      expect(dataStart).toBe(0x34 + 20); // After the entry
    });

    it('should stop at invalid entry size', () => {
      const header = new Uint8Array(100);
      header.set([0x48, 0x45, 0x41, 0x44]);

      // Entry at 0x34: invalid size=3 (< 5)
      const entryOffset = 0x34;
      header[entryOffset] = 3;
      header[entryOffset + 1] = 0;

      const reader = new BufferReader(header);
      const dataStart = findDataStart(reader);

      expect(dataStart).toBe(0x34); // Stops at invalid entry
    });
  });

  describe('parseFinishLine', () => {
    it('should parse all four RECORDLINE coordinates', () => {
      const header = new Uint8Array(500);

      // Helper to write a RECORDLINE entry
      const writeEntry = (
        offset: number,
        name: string,
        value: number
      ): number => {
        const encoder = new TextEncoder();
        const nameBytes = encoder.encode(name + '(');

        // Entry size: 4 (size) + 1 (name_len) + name.length + 1 (prefix '(') + 8 (double)
        const entrySize = 4 + 1 + nameBytes.length + 8;

        // Write entry_size (uint32 LE)
        header[offset] = entrySize & 0xff;
        header[offset + 1] = (entrySize >> 8) & 0xff;
        header[offset + 2] = 0;
        header[offset + 3] = 0;

        // Write name_len
        header[offset + 4] = nameBytes.length;

        // Write name (includes '(' at end)
        header.set(nameBytes, offset + 5);

        // Write double value (LE)
        const view = new DataView(
          header.buffer,
          header.byteOffset,
          header.byteLength
        );
        view.setFloat64(offset + 5 + nameBytes.length, value, true);

        return entrySize;
      };

      let offset = 0x34;
      offset += writeEntry(offset, 'RECORDLINE.P1.LAT', 47.949887);
      offset += writeEntry(offset, 'RECORDLINE.P1.LNG', 0.208753);
      offset += writeEntry(offset, 'RECORDLINE.P2.LAT', 47.950123);
      offset += writeEntry(offset, 'RECORDLINE.P2.LNG', 0.209456);

      const finishLine = parseFinishLine(header);

      expect(finishLine).not.toBeNull();
      expect(finishLine?.p1_lat).toBeCloseTo(47.949887, 6);
      expect(finishLine?.p1_lng).toBeCloseTo(0.208753, 6);
      expect(finishLine?.p2_lat).toBeCloseTo(47.950123, 6);
      expect(finishLine?.p2_lng).toBeCloseTo(0.209456, 6);
    });

    it('should return null if coordinates not found', () => {
      const header = new Uint8Array(500);
      const finishLine = parseFinishLine(header);
      expect(finishLine).toBeNull();
    });

    it('should return null if incomplete coordinates', () => {
      const header = new Uint8Array(500);
      const encoder = new TextEncoder();

      // Only write P1.LAT
      const name = encoder.encode('RECORDLINE.P1.LAT(');
      header.set(name, 0x34);

      const view = new DataView(
        header.buffer,
        header.byteOffset,
        header.byteLength
      );
      view.setFloat64(0x34 + name.length, 47.949887, true);

      const finishLine = parseFinishLine(header);
      expect(finishLine).toBeNull(); // Missing P1.LNG, P2.LAT, P2.LNG
    });
  });
});
