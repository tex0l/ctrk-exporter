/**
 * GPS data processing utilities
 *
 * Utilities for filtering, validating, and processing GPS coordinates
 * from telemetry records.
 */

import type { TelemetryRecord } from '@ctrk/parser';

/**
 * GPS sentinel value indicating no fix
 */
const GPS_SENTINEL = 9999.0;

/**
 * Tolerance for GPS sentinel check (accounts for floating point precision)
 */
const GPS_SENTINEL_TOLERANCE = 0.1;

/**
 * GPS coordinate pair
 */
export interface GpsCoordinate {
  lat: number;
  lng: number;
  time_ms: number;
  lap: number;
}

/**
 * Check if GPS coordinates are valid (not sentinel values)
 *
 * @param lat - Latitude
 * @param lng - Longitude
 * @returns True if coordinates are valid
 */
export function isValidGps(lat: number, lng: number): boolean {
  return (
    Math.abs(lat - GPS_SENTINEL) > GPS_SENTINEL_TOLERANCE &&
    Math.abs(lng - GPS_SENTINEL) > GPS_SENTINEL_TOLERANCE &&
    !isNaN(lat) &&
    !isNaN(lng)
  );
}

/**
 * Extract GPS coordinates from telemetry records
 *
 * @param records - Telemetry records
 * @returns Array of valid GPS coordinates
 */
export function extractGpsCoordinates(records: TelemetryRecord[]): GpsCoordinate[] {
  return records
    .filter((r) => isValidGps(r.latitude, r.longitude))
    .map((r) => ({
      lat: r.latitude,
      lng: r.longitude,
      time_ms: r.time_ms,
      lap: r.lap,
    }));
}

/**
 * Group GPS coordinates by lap
 *
 * @param coords - GPS coordinates
 * @returns Map of lap number to coordinates
 */
export function groupByLap(coords: GpsCoordinate[]): Map<number, GpsCoordinate[]> {
  const lapMap = new Map<number, GpsCoordinate[]>();

  for (const coord of coords) {
    const lapCoords = lapMap.get(coord.lap) || [];
    lapCoords.push(coord);
    lapMap.set(coord.lap, lapCoords);
  }

  return lapMap;
}

/**
 * Calculate perpendicular distance from a point to a line segment
 *
 * @param point - Point to measure distance from
 * @param lineStart - Start of line segment
 * @param lineEnd - End of line segment
 * @returns Perpendicular distance in degrees (approximation)
 */
function perpendicularDistance(
  point: GpsCoordinate,
  lineStart: GpsCoordinate,
  lineEnd: GpsCoordinate
): number {
  // For small distances, approximate as Euclidean distance in lat/lng space
  const dx = lineEnd.lng - lineStart.lng;
  const dy = lineEnd.lat - lineStart.lat;

  // Normalize line segment
  const magnitude = Math.sqrt(dx * dx + dy * dy);
  if (magnitude === 0) {
    // Line segment is a point
    const pdx = point.lng - lineStart.lng;
    const pdy = point.lat - lineStart.lat;
    return Math.sqrt(pdx * pdx + pdy * pdy);
  }

  // Calculate perpendicular distance using cross product
  const u = ((point.lng - lineStart.lng) * dx + (point.lat - lineStart.lat) * dy) / (magnitude * magnitude);

  // Clamp to line segment
  const uClamped = Math.max(0, Math.min(1, u));

  const closestX = lineStart.lng + uClamped * dx;
  const closestY = lineStart.lat + uClamped * dy;

  const pdx = point.lng - closestX;
  const pdy = point.lat - closestY;

  return Math.sqrt(pdx * pdx + pdy * pdy);
}

/**
 * Ramer-Douglas-Peucker polyline simplification algorithm
 *
 * Recursively simplifies a polyline by removing points that are
 * within epsilon distance from the line segment.
 *
 * @param coords - GPS coordinates
 * @param epsilon - Distance threshold in degrees (default 0.00001 ≈ 1 meter)
 * @returns Simplified coordinates
 */
function ramerDouglasPeucker(coords: GpsCoordinate[], epsilon: number): GpsCoordinate[] {
  if (coords.length <= 2) {
    return coords;
  }

  // Find the point with the maximum distance from the line
  let maxDistance = 0;
  let index = 0;
  const end = coords.length - 1;

  for (let i = 1; i < end; i++) {
    const distance = perpendicularDistance(coords[i], coords[0], coords[end]);
    if (distance > maxDistance) {
      maxDistance = distance;
      index = i;
    }
  }

  // If max distance is greater than epsilon, recursively simplify
  if (maxDistance > epsilon) {
    const left = ramerDouglasPeucker(coords.slice(0, index + 1), epsilon);
    const right = ramerDouglasPeucker(coords.slice(index), epsilon);

    // Concatenate results, removing duplicate point at junction
    return [...left.slice(0, -1), ...right];
  } else {
    // All points are within epsilon, return only endpoints
    return [coords[0], coords[end]];
  }
}

/**
 * Simplify a GPS track using Ramer-Douglas-Peucker algorithm
 *
 * If the track has more than maxPoints, use RDP algorithm for
 * perceptually accurate simplification. Otherwise, use simple
 * nth-point downsampling.
 *
 * @param coords - GPS coordinates
 * @param maxPoints - Maximum number of points to keep (default 5000)
 * @returns Simplified coordinates
 */
export function simplifyTrack(coords: GpsCoordinate[], maxPoints: number = 5000): GpsCoordinate[] {
  if (coords.length <= maxPoints) {
    return coords;
  }

  // For tracks with > maxPoints, use RDP algorithm
  // Start with a conservative epsilon and increase if needed
  let epsilon = 0.00001; // ~1 meter
  let simplified = ramerDouglasPeucker(coords, epsilon);

  // If still too many points, increase epsilon iteratively
  while (simplified.length > maxPoints && epsilon < 0.001) {
    epsilon *= 2;
    simplified = ramerDouglasPeucker(coords, epsilon);
  }

  // Fallback to simple downsampling if RDP didn't reduce enough
  if (simplified.length > maxPoints) {
    const step = Math.ceil(simplified.length / maxPoints);
    const downsampled: GpsCoordinate[] = [];

    for (let i = 0; i < simplified.length; i += step) {
      downsampled.push(simplified[i]);
    }

    // Always include the last point
    const last = simplified[simplified.length - 1];
    if (downsampled[downsampled.length - 1] !== last) {
      downsampled.push(last);
    }

    return downsampled;
  }

  return simplified;
}

/**
 * Calculate bounding box for GPS coordinates
 *
 * @param coords - GPS coordinates
 * @returns Bounding box [minLat, minLng, maxLat, maxLng] or null if empty
 */
export function calculateBounds(
  coords: GpsCoordinate[]
): [number, number, number, number] | null {
  if (coords.length === 0) {
    return null;
  }

  let minLat = Infinity;
  let maxLat = -Infinity;
  let minLng = Infinity;
  let maxLng = -Infinity;

  for (const coord of coords) {
    minLat = Math.min(minLat, coord.lat);
    maxLat = Math.max(maxLat, coord.lat);
    minLng = Math.min(minLng, coord.lng);
    maxLng = Math.max(maxLng, coord.lng);
  }

  return [minLat, minLng, maxLat, maxLng];
}

/**
 * Detect lap finish line crossings (simplified approach)
 *
 * Returns the indices of records where a lap change occurs.
 *
 * @param coords - GPS coordinates
 * @returns Array of indices where lap changes
 */
export function detectLapCrossings(coords: GpsCoordinate[]): number[] {
  const crossings: number[] = [];

  for (let i = 1; i < coords.length; i++) {
    if (coords[i].lap !== coords[i - 1].lap) {
      crossings.push(i);
    }
  }

  return crossings;
}
