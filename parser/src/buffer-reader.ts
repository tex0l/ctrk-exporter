/**
 * BufferReader for parsing binary data using Uint8Array and DataView.
 *
 * This class provides platform-agnostic binary parsing that works in
 * both Node.js and browsers. It does NOT use Node.js Buffer API.
 */
export class BufferReader {
  private data: Uint8Array;
  private view: DataView;
  private offset: number;

  constructor(data: Uint8Array) {
    this.data = data;
    this.view = new DataView(data.buffer, data.byteOffset, data.byteLength);
    this.offset = 0;
  }

  /**
   * Get current read offset
   */
  getOffset(): number {
    return this.offset;
  }

  /**
   * Set read offset
   */
  setOffset(offset: number): void {
    if (offset < 0 || offset > this.data.length) {
      throw new RangeError(
        `Offset ${offset} is out of bounds (0-${this.data.length})`
      );
    }
    this.offset = offset;
  }

  /**
   * Get total buffer length
   */
  getLength(): number {
    return this.data.length;
  }

  /**
   * Check if we can read N bytes from current offset
   */
  canRead(bytes: number): boolean {
    return this.offset + bytes <= this.data.length;
  }

  /**
   * Read uint8 (1 byte)
   */
  readUInt8(): number {
    if (!this.canRead(1)) {
      throw new RangeError('Cannot read uint8: out of bounds');
    }
    const value = this.data[this.offset];
    this.offset += 1;
    return value;
  }

  /**
   * Read uint16 little-endian (2 bytes)
   */
  readUInt16LE(): number {
    if (!this.canRead(2)) {
      throw new RangeError('Cannot read uint16LE: out of bounds');
    }
    const value = this.view.getUint16(this.offset, true);
    this.offset += 2;
    return value;
  }

  /**
   * Read uint16 big-endian (2 bytes)
   */
  readUInt16BE(): number {
    if (!this.canRead(2)) {
      throw new RangeError('Cannot read uint16BE: out of bounds');
    }
    const value = this.view.getUint16(this.offset, false);
    this.offset += 2;
    return value;
  }

  /**
   * Read uint32 little-endian (4 bytes)
   */
  readUInt32LE(): number {
    if (!this.canRead(4)) {
      throw new RangeError('Cannot read uint32LE: out of bounds');
    }
    const value = this.view.getUint32(this.offset, true);
    this.offset += 4;
    return value;
  }

  /**
   * Read float64 (double) little-endian (8 bytes)
   */
  readFloat64LE(): number {
    if (!this.canRead(8)) {
      throw new RangeError('Cannot read float64LE: out of bounds');
    }
    const value = this.view.getFloat64(this.offset, true);
    this.offset += 8;
    return value;
  }

  /**
   * Read N bytes as Uint8Array
   */
  readBytes(length: number): Uint8Array {
    if (!this.canRead(length)) {
      throw new RangeError(`Cannot read ${length} bytes: out of bounds`);
    }
    const slice = this.data.slice(this.offset, this.offset + length);
    this.offset += length;
    return slice;
  }

  /**
   * Peek uint8 at offset without advancing
   */
  peekUInt8(offset: number): number {
    if (offset < 0 || offset >= this.data.length) {
      throw new RangeError(`Peek offset ${offset} is out of bounds`);
    }
    return this.data[offset];
  }

  /**
   * Peek uint16LE at offset without advancing
   */
  peekUInt16LE(offset: number): number {
    if (offset < 0 || offset + 2 > this.data.length) {
      throw new RangeError(`Peek offset ${offset} is out of bounds`);
    }
    return this.view.getUint16(offset, true);
  }

  /**
   * Peek uint16BE at offset without advancing
   */
  peekUInt16BE(offset: number): number {
    if (offset < 0 || offset + 2 > this.data.length) {
      throw new RangeError(`Peek offset ${offset} is out of bounds`);
    }
    return this.view.getUint16(offset, false);
  }

  /**
   * Find the first occurrence of a byte sequence starting from offset
   */
  indexOf(pattern: Uint8Array, startOffset = 0): number {
    if (pattern.length === 0) return -1;
    if (startOffset < 0 || startOffset >= this.data.length) return -1;

    const maxIndex = this.data.length - pattern.length;
    for (let i = startOffset; i <= maxIndex; i++) {
      let match = true;
      for (let j = 0; j < pattern.length; j++) {
        if (this.data[i + j] !== pattern[j]) {
          match = false;
          break;
        }
      }
      if (match) return i;
    }
    return -1;
  }

  /**
   * Get a slice of the underlying data without copying
   */
  slice(start: number, end: number): Uint8Array {
    return this.data.slice(start, end);
  }

  /**
   * Get the raw Uint8Array
   */
  getRawData(): Uint8Array {
    return this.data;
  }
}
