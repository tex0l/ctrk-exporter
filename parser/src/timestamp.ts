/**
 * Timestamp computation for CTRK record headers.
 *
 * Implements GetTimeData and GetTimeDataEx algorithms from the native
 * library, including incremental timestamp computation and millis wrapping.
 */

/**
 * Convert 10-byte timestamp structure to Unix epoch milliseconds.
 *
 * Matches the native GetTimeData function behavior. Parses calendar
 * fields from the timestamp bytes and converts to epoch time.
 *
 * @param tsBytes - 10-byte timestamp from record header
 *                  Format: [millis(2LE)][sec][min][hour][wday][day][month][year(2LE)]
 * @returns Unix timestamp in milliseconds (UTC)
 */
export function getTimeData(tsBytes: Uint8Array): number {
  if (tsBytes.length < 10) {
    throw new RangeError('Timestamp must be at least 10 bytes');
  }

  const millis = tsBytes[0] | (tsBytes[1] << 8);
  const sec = tsBytes[2];
  const min = tsBytes[3];
  const hour = tsBytes[4];
  // tsBytes[5] is weekday (not used)
  const day = tsBytes[6];
  const month = tsBytes[7];
  const year = tsBytes[8] | (tsBytes[9] << 8);

  // Convert to UTC epoch milliseconds
  const dt = new Date(Date.UTC(year, month - 1, day, hour, min, sec));
  return dt.getTime() + millis;
}

/**
 * State for incremental timestamp computation.
 */
export interface TimestampState {
  prevTsBytes: Uint8Array | null;
  prevEpochMs: number;
}

/**
 * Create initial timestamp state.
 *
 * @returns Empty timestamp state for first record
 */
export function createTimestampState(): TimestampState {
  return {
    prevTsBytes: null,
    prevEpochMs: 0,
  };
}

/**
 * Compute timestamp with incremental optimization (GetTimeDataEx algorithm).
 *
 * This function implements the native library's GetTimeDataEx optimization:
 * - For the first record, compute full timestamp
 * - For identical timestamps (all 10 bytes), reuse previous value
 * - For same second (bytes 2-9 identical), update only millis incrementally
 * - For different second, recompute full timestamp
 *
 * @param tsBytes - 10-byte timestamp from current record header
 * @param state - Mutable state object to track previous timestamp
 * @returns Unix timestamp in milliseconds (UTC)
 */
export function getTimeDataEx(
  tsBytes: Uint8Array,
  state: TimestampState
): number {
  // First record: full computation
  if (state.prevTsBytes === null) {
    const epochMs = getTimeData(tsBytes);
    state.prevEpochMs = epochMs;
    state.prevTsBytes = tsBytes.slice(); // Copy bytes
    return epochMs;
  }

  // Check if timestamps are identical (all 10 bytes)
  let identical = true;
  for (let i = 0; i < 10; i++) {
    if (tsBytes[i] !== state.prevTsBytes[i]) {
      identical = false;
      break;
    }
  }

  if (identical) {
    // Reuse previous value
    return state.prevEpochMs;
  }

  // Check if same second (bytes 2-9: sec, min, hour, wday, day, month, year)
  let sameSecond = true;
  for (let i = 2; i < 10; i++) {
    if (tsBytes[i] !== state.prevTsBytes[i]) {
      sameSecond = false;
      break;
    }
  }

  let epochMs: number;

  if (sameSecond) {
    // Same second, different millis: incremental update
    const prevMillis = state.prevTsBytes[0] | (state.prevTsBytes[1] << 8);
    const currMillis = tsBytes[0] | (tsBytes[1] << 8);
    epochMs = currMillis + (state.prevEpochMs - prevMillis);

    // Handle millis wrapping (hardware edge case)
    // The CCU timestamp capture is non-atomic. In rare cases, millis wraps
    // from ~999 to ~0 while seconds has not yet incremented.
    if (currMillis < prevMillis) {
      epochMs += 1000;
    }
  } else {
    // Different second: full recomputation
    epochMs = getTimeData(tsBytes);
  }

  // Update state
  state.prevEpochMs = epochMs;
  state.prevTsBytes = tsBytes.slice();

  return epochMs;
}

/**
 * Compare two 10-byte timestamp arrays for equality.
 *
 * @param a - First timestamp
 * @param b - Second timestamp
 * @returns True if all 10 bytes are identical
 */
export function timestampsEqual(a: Uint8Array, b: Uint8Array): boolean {
  if (a.length !== 10 || b.length !== 10) return false;
  for (let i = 0; i < 10; i++) {
    if (a[i] !== b[i]) return false;
  }
  return true;
}
