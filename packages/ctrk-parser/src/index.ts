/**
 * CTRK Parser - TypeScript/Browser Edition
 *
 * A platform-agnostic parser for Yamaha Y-Trac CTRK telemetry files.
 * Works in both Node.js and browsers using only Uint8Array and DataView.
 */

export { CTRKParser } from './ctrk-parser.js';
export { BufferReader } from './buffer-reader.js';
export { Calibration } from './calibration.js';
export { sideOfLine, crossesLine } from './finish-line.js';
export {
  parseCan0x0209,
  parseCan0x0215,
  parseCan0x023e,
  parseCan0x0250,
  parseCan0x0258,
  parseCan0x0260,
  parseCan0x0264,
  parseCan0x0268,
  CAN_HANDLERS,
} from './can-handlers.js';
export {
  validateMagic,
  findDataStart,
  parseFinishLine,
} from './header-parser.js';
export {
  getTimeData,
  getTimeDataEx,
  createTimestampState,
  timestampsEqual,
} from './timestamp.js';
export {
  validateNmeaChecksum,
  parseGprmcSentence,
} from './nmea-parser.js';

export { formatCalibratedCsv, formatRawCsv } from './csv-export.js';

export type {
  FinishLine,
  TelemetryRecord,
  ChannelState,
  GpsState,
  GprmcData,
} from './types.js';
export type { TimestampState } from './timestamp.js';
