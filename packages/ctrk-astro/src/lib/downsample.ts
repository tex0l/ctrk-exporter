/**
 * Data downsampling utilities
 *
 * Provides efficient downsampling algorithms for reducing
 * chart data points while preserving visual fidelity.
 */

/**
 * Largest-Triangle-Three-Buckets (LTTB) downsampling algorithm
 *
 * This algorithm provides perceptually accurate downsampling by
 * preserving data features that would be visible in a chart.
 * It divides data into buckets and selects the point from each bucket
 * that has the largest triangle area with its neighbors.
 *
 * Reference: Sveinn Steinarsson, 2013
 * https://skemman.is/bitstream/1946/15343/3/SS_MSthesis.pdf
 *
 * @param data - Array of data points (y-values)
 * @param threshold - Target number of points after downsampling
 * @returns Downsampled indices into original data array
 */
export function downsampleLTTB(data: number[], threshold: number): number[] {
  const dataLength = data.length;

  // If data is already small enough, return all indices
  if (threshold >= dataLength || threshold <= 2) {
    return Array.from({ length: dataLength }, (_, i) => i);
  }

  const sampled: number[] = [];

  // Always include first point
  sampled.push(0);

  // Bucket size (excluding first and last points)
  const bucketSize = (dataLength - 2) / (threshold - 2);

  let a = 0; // Initially point a is the first point in the triangle

  for (let i = 0; i < threshold - 2; i++) {
    // Calculate point average for next bucket (point c)
    let avgX = 0;
    let avgY = 0;

    const avgRangeStart = Math.floor((i + 1) * bucketSize) + 1;
    const avgRangeEnd = Math.min(
      Math.floor((i + 2) * bucketSize) + 1,
      dataLength
    );
    const avgRangeLength = avgRangeEnd - avgRangeStart;

    for (let j = avgRangeStart; j < avgRangeEnd; j++) {
      avgX += j;
      avgY += data[j];
    }
    avgX /= avgRangeLength;
    avgY /= avgRangeLength;

    // Get the range for this bucket
    const rangeStart = Math.floor(i * bucketSize) + 1;
    const rangeEnd = Math.floor((i + 1) * bucketSize) + 1;

    // Point a (x, y)
    const pointAX = a;
    const pointAY = data[a];

    let maxArea = -1;
    let maxAreaPoint = rangeStart;

    // Find point with largest triangle area in current bucket
    for (let j = rangeStart; j < rangeEnd; j++) {
      // Calculate triangle area over three buckets
      const area = Math.abs(
        (pointAX - avgX) * (data[j] - pointAY) -
          (pointAX - j) * (avgY - pointAY)
      );

      if (area > maxArea) {
        maxArea = area;
        maxAreaPoint = j;
      }
    }

    sampled.push(maxAreaPoint);
    a = maxAreaPoint; // This point is the next point a
  }

  // Always include last point
  sampled.push(dataLength - 1);

  return sampled;
}

/**
 * Simple nth-point downsampling
 *
 * Keeps every Nth point plus the first and last points.
 * Faster than LTTB but less accurate for complex waveforms.
 *
 * @param dataLength - Length of data array
 * @param maxPoints - Maximum number of points to keep
 * @returns Array of indices to keep
 */
export function downsampleNthPoint(dataLength: number, maxPoints: number): number[] {
  if (maxPoints >= dataLength) {
    return Array.from({ length: dataLength }, (_, i) => i);
  }

  const step = Math.ceil(dataLength / maxPoints);
  const sampled: number[] = [];

  for (let i = 0; i < dataLength; i += step) {
    sampled.push(i);
  }

  // Always include last point if not already included
  if (sampled[sampled.length - 1] !== dataLength - 1) {
    sampled.push(dataLength - 1);
  }

  return sampled;
}

/**
 * Downsample multiple data series with the same X-axis
 *
 * Uses LTTB algorithm based on the first data series,
 * then applies the same indices to all series.
 * This ensures all series remain aligned.
 *
 * @param dataSeries - Array of data series (each is an array of y-values)
 * @param threshold - Target number of points after downsampling
 * @returns Downsampled indices applicable to all series
 */
export function downsampleMultiSeries(
  dataSeries: number[][],
  threshold: number
): number[] {
  if (dataSeries.length === 0) {
    return [];
  }

  // Use first series for LTTB calculation
  // (all series share the same X-axis, so any series works)
  return downsampleLTTB(dataSeries[0], threshold);
}

/**
 * Apply downsampling indices to a data array
 *
 * @param data - Source data array
 * @param indices - Indices to keep (from downsampleLTTB or downsampleNthPoint)
 * @returns Downsampled data array
 */
export function applyDownsampling<T>(data: T[], indices: number[]): T[] {
  return indices.map((i) => data[i]);
}
