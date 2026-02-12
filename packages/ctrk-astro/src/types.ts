/**
 * Type definitions for Astro integration
 */

import type { TelemetryRecord } from '@tex0l/ctrk-parser';

/**
 * Parser status states
 */
export type ParserStatus = 'idle' | 'parsing' | 'success' | 'error';

/**
 * Parser result containing records and metadata
 */
export interface ParserResult {
  records: TelemetryRecord[];
  fileName: string;
  fileSize: number;
  parseTime: number;
}

/**
 * Parser error with context
 */
export interface ParserError {
  message: string;
  fileName?: string;
  originalError?: Error;
}

/**
 * Configuration for telemetry composables
 */
export interface TelemetryConfig {
  autoCalibrate?: boolean;
  validateGps?: boolean;
}
