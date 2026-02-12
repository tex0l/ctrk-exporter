import type { FinishLine } from './types.js';

/**
 * Determine which side of the finish line a point is on.
 *
 * Uses the cross product of vectors to compute signed distance from
 * the line. The sign indicates which side of the line the point is on.
 *
 * @param finishLine - The finish line definition
 * @param lat - Latitude of the point in decimal degrees
 * @param lng - Longitude of the point in decimal degrees
 * @returns Signed value indicating side of line
 */
export function sideOfLine(
  finishLine: FinishLine,
  lat: number,
  lng: number
): number {
  // Vector from P1 to P2
  const dx = finishLine.p2_lng - finishLine.p1_lng;
  const dy = finishLine.p2_lat - finishLine.p1_lat;
  // Vector from P1 to point
  const px = lng - finishLine.p1_lng;
  const py = lat - finishLine.p1_lat;
  // Cross product (z component)
  return dx * py - dy * px;
}

/**
 * Check if a trajectory segment crosses the finish line.
 *
 * Determines if the line segment from (lat1, lng1) to (lat2, lng2)
 * intersects with the finish line segment from P1 to P2.
 *
 * @param finishLine - The finish line definition
 * @param lat1 - Starting latitude in decimal degrees
 * @param lng1 - Starting longitude in decimal degrees
 * @param lat2 - Ending latitude in decimal degrees
 * @param lng2 - Ending longitude in decimal degrees
 * @returns True if the trajectory crosses the finish line, False otherwise
 */
export function crossesLine(
  finishLine: FinishLine,
  lat1: number,
  lng1: number,
  lat2: number,
  lng2: number
): boolean {
  const side1 = sideOfLine(finishLine, lat1, lng1);
  const side2 = sideOfLine(finishLine, lat2, lng2);

  // Sign change means potential crossing
  if (side1 * side2 >= 0) {
    return false;
  }

  // Check if the crossing point is within the finish line segment
  // Using parametric intersection
  const dx1 = finishLine.p2_lng - finishLine.p1_lng;
  const dy1 = finishLine.p2_lat - finishLine.p1_lat;
  const dx2 = lng2 - lng1;
  const dy2 = lat2 - lat1;

  const denom = dx1 * dy2 - dy1 * dx2;
  if (Math.abs(denom) < 1e-12) {
    return false; // Parallel lines
  }

  const t =
    ((lng1 - finishLine.p1_lng) * dy2 - (lat1 - finishLine.p1_lat) * dx2) /
    denom;

  // t should be between 0 and 1 for crossing to be on the finish line segment
  return 0 <= t && t <= 1;
}
