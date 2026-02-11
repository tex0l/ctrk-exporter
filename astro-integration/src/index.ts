/**
 * @ctrk-exporter/astro-integration
 *
 * Astro integration for CTRK telemetry parser with Vue.js components
 */

// Integration
export { default } from './integration.js';
export type { CTRKIntegrationOptions } from './integration.js';

// Re-export parser
export * from './parser.js';

// Re-export types
export type {
  ParserStatus,
  ParserResult,
  ParserError,
  TelemetryConfig,
} from './types.js';

// Re-export utilities
export {
  fileToUint8Array,
  isCTRKFile,
  formatFileSize,
  formatParseTime,
} from './utils.js';

// Re-export composables
export { useTelemetryData, useParserStatus } from './composables/index.js';
