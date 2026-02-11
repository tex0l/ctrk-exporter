/**
 * Web Worker for non-blocking CTRK parsing
 *
 * Receives Uint8Array via postMessage, parses it, and returns the records.
 * Uses transferable ArrayBuffer for performance.
 */

import { CTRKParser } from '@ctrk/parser';
import type { TelemetryRecord } from '@ctrk/parser';

/**
 * Message sent from main thread to worker
 */
export interface WorkerRequest {
  type: 'parse';
  data: Uint8Array;
}

/**
 * Message sent from worker to main thread
 */
export interface WorkerResponse {
  type: 'success' | 'error';
  records?: TelemetryRecord[];
  error?: string;
  parseTime?: number;
}

// Worker message handler
self.onmessage = (event: MessageEvent<WorkerRequest>) => {
  const { type, data } = event.data;

  if (type !== 'parse') {
    const errorResponse: WorkerResponse = {
      type: 'error',
      error: `Unknown message type: ${type}`,
    };
    self.postMessage(errorResponse);
    return;
  }

  try {
    const startTime = performance.now();

    // Parse CTRK file
    const parser = new CTRKParser(data);
    const records = parser.parse();

    const parseTime = performance.now() - startTime;

    // Send success response
    const response: WorkerResponse = {
      type: 'success',
      records,
      parseTime,
    };

    self.postMessage(response);
  } catch (err) {
    // Send error response
    const errorResponse: WorkerResponse = {
      type: 'error',
      error: err instanceof Error ? err.message : 'Unknown parsing error',
    };
    self.postMessage(errorResponse);
  }
};

// Export types for use in main thread
export type { TelemetryRecord };
