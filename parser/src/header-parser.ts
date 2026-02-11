/**
 * Header parsing utilities for CTRK files.
 */

import { BufferReader } from './buffer-reader.js';
import type { FinishLine } from './types.js';

const MAGIC = new Uint8Array([0x48, 0x45, 0x41, 0x44]); // "HEAD"

/**
 * Validate CTRK file magic signature.
 *
 * @param data - The first 4 bytes of the file
 * @returns True if the magic is valid
 */
export function validateMagic(data: Uint8Array): boolean {
  if (data.length < 4) return false;
  return (
    data[0] === MAGIC[0] &&
    data[1] === MAGIC[1] &&
    data[2] === MAGIC[2] &&
    data[3] === MAGIC[3]
  );
}

/**
 * Find the byte offset where the data section begins.
 *
 * The CTRK header contains variable-length entries starting at 0x34.
 * This function iterates through those entries to find where they end
 * and the data records begin.
 *
 * @param reader - BufferReader positioned at the start of the file
 * @returns Byte offset of the first data record (typically ~0xCB)
 */
export function findDataStart(reader: BufferReader): number {
  let offset = 0x34;
  const maxHeaderSize = Math.min(reader.getLength(), 500);

  while (offset < maxHeaderSize) {
    if (offset + 4 > reader.getLength()) {
      break;
    }

    const entrySize = reader.peekUInt16LE(offset);
    if (entrySize < 5 || entrySize > 200) {
      break;
    }

    if (offset + 4 >= reader.getLength()) {
      break;
    }

    const nameLen = reader.peekUInt8(offset + 4);
    if (nameLen < 1 || nameLen > entrySize - 5) {
      break;
    }

    offset += entrySize;
  }

  return offset;
}

/**
 * Extract finish line coordinates from CTRK file header.
 *
 * Searches for RECORDLINE.P1.LAT, P1.LNG, P2.LAT, and P2.LNG entries
 * in the header and parses their double-precision floating point values.
 *
 * @param data - Raw bytes from the CTRK file (at least first ~500 bytes)
 * @returns FinishLine object with parsed coordinates, or null if not found
 */
export function parseFinishLine(data: Uint8Array): FinishLine | null {
  try {
    const reader = new BufferReader(data);

    // Helper to find a pattern and read double after it
    const findAndReadDouble = (pattern: string): number | null => {
      const patternBytes = new TextEncoder().encode(pattern);
      const index = reader.indexOf(patternBytes);
      if (index === -1) return null;

      // Pattern ends with '(', followed by 8 bytes of double LE
      const offset = index + patternBytes.length;
      if (offset + 8 > data.length) return null;

      const view = new DataView(data.buffer, data.byteOffset, data.byteLength);
      return view.getFloat64(offset, true); // little-endian
    };

    const p1Lat = findAndReadDouble('RECORDLINE.P1.LAT(');
    if (p1Lat === null) return null;

    const p1Lng = findAndReadDouble('RECORDLINE.P1.LNG(');
    if (p1Lng === null) return null;

    const p2Lat = findAndReadDouble('RECORDLINE.P2.LAT(');
    if (p2Lat === null) return null;

    const p2Lng = findAndReadDouble('RECORDLINE.P2.LNG(');
    if (p2Lng === null) return null;

    return {
      p1_lat: p1Lat,
      p1_lng: p1Lng,
      p2_lat: p2Lat,
      p2_lng: p2Lng,
    };
  } catch {
    return null;
  }
}
