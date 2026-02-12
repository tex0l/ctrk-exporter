import { describe, it, expect } from 'vitest';
import { BufferReader } from './buffer-reader.js';

describe('BufferReader', () => {
  it('should read uint8', () => {
    const data = new Uint8Array([0x42, 0xff, 0x00]);
    const reader = new BufferReader(data);

    expect(reader.readUInt8()).toBe(0x42);
    expect(reader.readUInt8()).toBe(0xff);
    expect(reader.readUInt8()).toBe(0x00);
    expect(reader.getOffset()).toBe(3);
  });

  it('should read uint16 little-endian', () => {
    const data = new Uint8Array([0x34, 0x12, 0xff, 0x00]);
    const reader = new BufferReader(data);

    expect(reader.readUInt16LE()).toBe(0x1234);
    expect(reader.readUInt16LE()).toBe(0x00ff);
    expect(reader.getOffset()).toBe(4);
  });

  it('should read uint16 big-endian', () => {
    const data = new Uint8Array([0x12, 0x34, 0x00, 0xff]);
    const reader = new BufferReader(data);

    expect(reader.readUInt16BE()).toBe(0x1234);
    expect(reader.readUInt16BE()).toBe(0x00ff);
    expect(reader.getOffset()).toBe(4);
  });

  it('should read uint32 little-endian', () => {
    const data = new Uint8Array([0x78, 0x56, 0x34, 0x12]);
    const reader = new BufferReader(data);

    expect(reader.readUInt32LE()).toBe(0x12345678);
    expect(reader.getOffset()).toBe(4);
  });

  it('should read float64 little-endian', () => {
    const buffer = new ArrayBuffer(8);
    const view = new DataView(buffer);
    view.setFloat64(0, 47.949887, true);
    const data = new Uint8Array(buffer);
    const reader = new BufferReader(data);

    const value = reader.readFloat64LE();
    expect(value).toBeCloseTo(47.949887, 6);
    expect(reader.getOffset()).toBe(8);
  });

  it('should read bytes', () => {
    const data = new Uint8Array([0x01, 0x02, 0x03, 0x04, 0x05]);
    const reader = new BufferReader(data);

    const bytes = reader.readBytes(3);
    expect(bytes).toEqual(new Uint8Array([0x01, 0x02, 0x03]));
    expect(reader.getOffset()).toBe(3);
  });

  it('should peek without advancing offset', () => {
    const data = new Uint8Array([0x12, 0x34, 0x56, 0x78]);
    const reader = new BufferReader(data);

    expect(reader.peekUInt8(0)).toBe(0x12);
    expect(reader.peekUInt8(3)).toBe(0x78);
    expect(reader.getOffset()).toBe(0);

    expect(reader.peekUInt16LE(0)).toBe(0x3412);
    expect(reader.peekUInt16BE(0)).toBe(0x1234);
    expect(reader.getOffset()).toBe(0);
  });

  it('should find byte patterns', () => {
    const data = new Uint8Array([0x00, 0x01, 0x48, 0x45, 0x41, 0x44, 0x99]);
    const reader = new BufferReader(data);

    const pattern = new Uint8Array([0x48, 0x45, 0x41, 0x44]); // "HEAD"
    expect(reader.indexOf(pattern)).toBe(2);
    expect(reader.indexOf(pattern, 3)).toBe(-1);
  });

  it('should throw on out-of-bounds reads', () => {
    const data = new Uint8Array([0x01, 0x02]);
    const reader = new BufferReader(data);

    reader.readUInt8();
    reader.readUInt8();
    expect(() => reader.readUInt8()).toThrow(RangeError);
    expect(() => reader.readUInt16LE()).toThrow(RangeError);
  });

  it('should set and get offset', () => {
    const data = new Uint8Array([0x01, 0x02, 0x03, 0x04]);
    const reader = new BufferReader(data);

    reader.setOffset(2);
    expect(reader.getOffset()).toBe(2);
    expect(reader.readUInt8()).toBe(0x03);

    expect(() => reader.setOffset(10)).toThrow(RangeError);
    expect(() => reader.setOffset(-1)).toThrow(RangeError);
  });

  it('should check if can read', () => {
    const data = new Uint8Array([0x01, 0x02, 0x03]);
    const reader = new BufferReader(data);

    expect(reader.canRead(3)).toBe(true);
    expect(reader.canRead(4)).toBe(false);

    reader.readUInt8();
    expect(reader.canRead(2)).toBe(true);
    expect(reader.canRead(3)).toBe(false);
  });

  it('should slice data', () => {
    const data = new Uint8Array([0x01, 0x02, 0x03, 0x04, 0x05]);
    const reader = new BufferReader(data);

    const slice = reader.slice(1, 4);
    expect(slice).toEqual(new Uint8Array([0x02, 0x03, 0x04]));
  });
});
