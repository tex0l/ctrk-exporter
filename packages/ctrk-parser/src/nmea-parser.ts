/**
 * NMEA sentence parser for GPS data.
 *
 * Handles GPRMC sentence parsing with checksum validation and
 * coordinate conversion from degrees-minutes to decimal degrees.
 */

import type { GprmcData } from './types.js';

/**
 * Validate NMEA sentence XOR checksum.
 *
 * Computes XOR of all bytes between '$' and '*', then compares
 * with the stated 2-digit hex checksum after '*'.
 *
 * @param sentence - Complete NMEA sentence string including $ and *XX
 * @returns True if checksum is valid, False otherwise
 */
export function validateNmeaChecksum(sentence: string): boolean {
  const starIdx = sentence.indexOf('*');
  if (starIdx < 1 || starIdx + 3 > sentence.length) {
    return false;
  }

  // Compute XOR of all characters between $ and *
  let computed = 0;
  for (let i = 1; i < starIdx; i++) {
    computed ^= sentence.charCodeAt(i);
  }

  // Parse stated checksum (2 hex digits after *)
  try {
    const stated = parseInt(sentence.substring(starIdx + 1, starIdx + 3), 16);
    return computed === stated;
  } catch {
    return false;
  }
}

/**
 * Parse NMEA GPRMC sentence for GPS position and speed.
 *
 * Extracts latitude, longitude, and ground speed from a valid
 * GPRMC sentence. Only processes sentences with status 'A' (active fix).
 *
 * GPRMC format:
 * $GPRMC,HHMMSS.sss,S,DDMM.MMMM,N,DDDMM.MMMM,E,SPD,CRS,DDMMYY,,,M*HH
 *
 * @param sentence - GPRMC sentence string (comma-separated fields)
 * @returns GprmcData object with parsed values, or null if invalid or void status
 */
export function parseGprmcSentence(sentence: string): GprmcData | null {
  try {
    const parts = sentence.split(',');

    // Must have at least 8 fields and status must be 'A' (active)
    if (parts.length < 8 || parts[2] !== 'A') {
      return null;
    }

    // Parse latitude (DDMM.MMMM format)
    const latStr = parts[3];
    if (!latStr || latStr.length < 4) {
      return null;
    }
    const latDeg = parseFloat(latStr.substring(0, 2));
    const latMin = parseFloat(latStr.substring(2));
    let lat = latDeg + latMin / 60.0;

    // Apply hemisphere sign
    if (parts[4] === 'S') {
      lat = -lat;
    }

    // Parse longitude (DDDMM.MMMM format)
    const lonStr = parts[5];
    if (!lonStr || lonStr.length < 5) {
      return null;
    }
    const lonDeg = parseFloat(lonStr.substring(0, 3));
    const lonMin = parseFloat(lonStr.substring(3));
    let lon = lonDeg + lonMin / 60.0;

    // Apply hemisphere sign
    if (parts[6] === 'W') {
      lon = -lon;
    }

    // Parse speed (knots)
    const speedKnots = parts[7] ? parseFloat(parts[7]) : 0.0;

    return {
      latitude: lat,
      longitude: lon,
      speed_knots: speedKnots,
    };
  } catch {
    return null;
  }
}
