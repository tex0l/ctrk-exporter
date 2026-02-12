# @ctrk/parser

TypeScript parser for Yamaha Y-Trac CTRK telemetry files.

## Features

- **Platform-agnostic**: Works in both Node.js and browsers (no Node.js Buffer API)
- **Zero runtime dependencies**: Parser has no npm dependencies
- **Strict TypeScript**: Full type safety with strict mode enabled
- **Byte-for-byte compatible**: Matches Python reference implementation
- **Comprehensive tests**: Full unit test coverage with Vitest

## Installation

```bash
npm install @ctrk/parser
```

## Usage

### Import the parser

```typescript
import {
  BufferReader,
  Calibration,
  validateMagic,
  parseFinishLine,
  parseCan0x0209,
  // ... other exports
} from '@ctrk/parser';
```

### Parse a CTRK file

```typescript
// In Node.js
import { readFileSync } from 'fs';
const data = new Uint8Array(readFileSync('session.CTRK'));

// In browser
const response = await fetch('session.CTRK');
const arrayBuffer = await response.arrayBuffer();
const data = new Uint8Array(arrayBuffer);

// Validate magic
if (!validateMagic(data.slice(0, 4))) {
  throw new Error('Invalid CTRK file');
}

// Parse finish line
const finishLine = parseFinishLine(data.slice(0, 500));
console.log('Finish line:', finishLine);

// Use BufferReader for binary parsing
const reader = new BufferReader(data);
const rpm = reader.readUInt16BE(); // Read big-endian uint16
```

### Calibrate raw values

```typescript
import { Calibration } from '@ctrk/parser';

const rpm = Calibration.rpm(25600); // 10000 RPM
const speed = Calibration.wheelSpeedKmh(6400); // 360.0 km/h
const lean = Calibration.lean(12000); // 30.0 degrees
```

## API Reference

### BufferReader

Platform-agnostic binary parser using `Uint8Array` and `DataView`.

```typescript
class BufferReader {
  constructor(data: Uint8Array);
  readUInt8(): number;
  readUInt16LE(): number;
  readUInt16BE(): number;
  readUInt32LE(): number;
  readFloat64LE(): number;
  readBytes(length: number): Uint8Array;
  peekUInt8(offset: number): number;
  indexOf(pattern: Uint8Array, startOffset?: number): number;
  // ... more methods
}
```

### Calibration

Static methods for converting raw sensor values to engineering units.

```typescript
class Calibration {
  static rpm(raw: number): number;
  static wheelSpeedKmh(raw: number): number;
  static throttle(raw: number): number;
  static brake(raw: number): number;
  static lean(raw: number): number;
  static pitch(raw: number): number;
  static acceleration(raw: number): number;
  static temperature(raw: number): number;
  static fuel(raw: number): number;
  static gpsSpeedKmh(knots: number): number;
}
```

### CAN Handlers

Functions for parsing CAN message payloads.

```typescript
parseCan0x0209(data: Uint8Array, state: ChannelState): void; // RPM, Gear
parseCan0x0215(data: Uint8Array, state: ChannelState): void; // Throttle, Controls
parseCan0x023e(data: Uint8Array, state: ChannelState, fuelAcc: { value: number }): void; // Temp, Fuel
parseCan0x0250(data: Uint8Array, state: ChannelState): void; // Acceleration
parseCan0x0258(data: Uint8Array, state: ChannelState): void; // Lean, Pitch
parseCan0x0260(data: Uint8Array, state: ChannelState): void; // Brake
parseCan0x0264(data: Uint8Array, state: ChannelState): void; // Wheel Speed
parseCan0x0268(data: Uint8Array, state: ChannelState): void; // ABS
```

### Header Parsing

```typescript
validateMagic(data: Uint8Array): boolean;
findDataStart(reader: BufferReader): number;
parseFinishLine(data: Uint8Array): FinishLine | null;
```

### Finish Line

```typescript
sideOfLine(finishLine: FinishLine, lat: number, lng: number): number;
crossesLine(
  finishLine: FinishLine,
  lat1: number,
  lng1: number,
  lat2: number,
  lng2: number
): boolean;
```

## Development

```bash
# Install dependencies
npm install

# Run tests
npm test

# Run tests in watch mode
npm run test:watch

# Type check
npm run typecheck

# Lint
npm run lint

# Format
npm run format

# Build
npm run build
```

## License

MIT
