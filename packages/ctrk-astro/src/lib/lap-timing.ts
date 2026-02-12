/**
 * Lap timing computation utilities
 *
 * Computes lap times, deltas, and session statistics from telemetry records.
 */

import type { TelemetryRecord } from '@tex0l/ctrk-parser';

/**
 * Lap timing information
 */
export interface LapTime {
  lap: number;
  time_ms: number;
  delta_ms: number | null; // Delta to best lap
  isBest: boolean;
}

/**
 * Session timing summary
 */
export interface SessionSummary {
  totalLaps: number;
  bestLap: number | null;
  bestTime_ms: number | null;
  averageTime_ms: number | null;
}

/**
 * Compute lap times from telemetry records
 *
 * @param records - Telemetry records sorted by time
 * @returns Array of lap times
 */
export function computeLapTimes(records: TelemetryRecord[]): LapTime[] {
  if (records.length === 0) {
    return [];
  }

  // Group records by lap
  const lapGroups = new Map<number, TelemetryRecord[]>();

  for (const record of records) {
    const lapRecords = lapGroups.get(record.lap) || [];
    lapRecords.push(record);
    lapGroups.set(record.lap, lapRecords);
  }

  // Compute lap times
  const lapTimes: LapTime[] = [];

  for (const [lap, lapRecords] of lapGroups.entries()) {
    if (lapRecords.length === 0) continue;

    // Sort by time to ensure correct order
    lapRecords.sort((a, b) => a.time_ms - b.time_ms);

    const first = lapRecords[0];
    const last = lapRecords[lapRecords.length - 1];
    const time_ms = last.time_ms - first.time_ms;

    lapTimes.push({
      lap,
      time_ms,
      delta_ms: null, // Will be computed after finding best lap
      isBest: false,
    });
  }

  // Sort by lap number
  lapTimes.sort((a, b) => a.lap - b.lap);

  // Find best lap (skip lap 0 if it exists, as it's often partial)
  const validLapTimes = lapTimes.filter((lt) => lt.lap > 0);
  if (validLapTimes.length === 0) {
    return lapTimes;
  }

  const bestLapTime = Math.min(...validLapTimes.map((lt) => lt.time_ms));
  const bestLap = validLapTimes.find((lt) => lt.time_ms === bestLapTime);

  if (bestLap) {
    bestLap.isBest = true;

    // Compute deltas
    for (const lapTime of lapTimes) {
      if (lapTime.lap > 0) {
        lapTime.delta_ms = lapTime.time_ms - bestLapTime;
      }
    }
  }

  return lapTimes;
}

/**
 * Compute session summary statistics
 *
 * @param lapTimes - Lap times
 * @returns Session summary
 */
export function computeSessionSummary(lapTimes: LapTime[]): SessionSummary {
  const validLapTimes = lapTimes.filter((lt) => lt.lap > 0);

  if (validLapTimes.length === 0) {
    return {
      totalLaps: 0,
      bestLap: null,
      bestTime_ms: null,
      averageTime_ms: null,
    };
  }

  const bestLap = validLapTimes.find((lt) => lt.isBest);
  const avgTime =
    validLapTimes.reduce((sum, lt) => sum + lt.time_ms, 0) / validLapTimes.length;

  return {
    totalLaps: validLapTimes.length,
    bestLap: bestLap?.lap ?? null,
    bestTime_ms: bestLap?.time_ms ?? null,
    averageTime_ms: avgTime,
  };
}

/**
 * Format lap time as MM:SS.sss
 *
 * @param time_ms - Time in milliseconds
 * @returns Formatted time string
 */
export function formatLapTime(time_ms: number): string {
  const minutes = Math.floor(time_ms / 60000);
  const seconds = (time_ms % 60000) / 1000;

  const secStr = seconds.toFixed(3).padStart(6, '0');
  return `${minutes}:${secStr}`;
}

/**
 * Format delta time with sign
 *
 * @param delta_ms - Delta in milliseconds
 * @returns Formatted delta string (e.g., "+1.234" or "-0.567")
 */
export function formatDelta(delta_ms: number): string {
  const sign = delta_ms >= 0 ? '+' : '-';
  const seconds = Math.abs(delta_ms) / 1000;
  return `${sign}${seconds.toFixed(3)}`;
}
