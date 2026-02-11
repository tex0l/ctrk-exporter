/**
 * Parser re-exports from @ctrk/parser
 *
 * Provides convenient access to the CTRK parser functionality
 * for Astro/Vue.js applications.
 */

export {
  CTRKParser,
  BufferReader,
  Calibration,
  sideOfLine,
  crossesLine,
  parseCan0x0209,
  parseCan0x0215,
  parseCan0x023e,
  parseCan0x0250,
  parseCan0x0258,
  parseCan0x0260,
  parseCan0x0264,
  parseCan0x0268,
  CAN_HANDLERS,
  validateMagic,
  findDataStart,
  parseFinishLine,
  getTimeData,
  getTimeDataEx,
  createTimestampState,
  timestampsEqual,
  validateNmeaChecksum,
  parseGprmcSentence,
} from '@ctrk/parser';

export type {
  FinishLine,
  TelemetryRecord,
  ChannelState,
  GpsState,
  GprmcData,
  TimestampState,
} from '@ctrk/parser';
