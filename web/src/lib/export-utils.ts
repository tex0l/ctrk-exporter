/**
 * Data export utilities
 *
 * Utilities for exporting telemetry data to various formats (CSV, etc.)
 */

import type { LapTime } from './lap-timing';

/**
 * Export lap times to CSV format
 *
 * @param lapTimes - Array of lap times
 * @param fileName - Base file name (default: 'lap_times')
 * @returns CSV string
 */
export function exportLapTimesToCsv(lapTimes: LapTime[], fileName = 'lap_times'): string {
  // CSV header
  const header = 'Lap,Time (s),Delta (s),Is Best\n';

  // CSV rows
  const rows = lapTimes
    .map((lt) => {
      const timeSec = (lt.time_ms / 1000).toFixed(3);
      const deltaSec = lt.delta_ms !== null ? (lt.delta_ms / 1000).toFixed(3) : '';
      const isBest = lt.isBest ? 'Yes' : 'No';
      return `${lt.lap},${timeSec},${deltaSec},${isBest}`;
    })
    .join('\n');

  return header + rows;
}

/**
 * Trigger browser download of CSV data
 *
 * @param csvContent - CSV content string
 * @param fileName - File name (with or without .csv extension)
 */
export function downloadCsv(csvContent: string, fileName: string): void {
  // Ensure .csv extension
  if (!fileName.endsWith('.csv')) {
    fileName += '.csv';
  }

  // Create blob
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });

  // Create download link
  const link = document.createElement('a');
  const url = URL.createObjectURL(blob);

  link.setAttribute('href', url);
  link.setAttribute('download', fileName);
  link.style.visibility = 'hidden';

  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);

  // Clean up object URL
  URL.revokeObjectURL(url);
}

/**
 * Export and download lap times as CSV
 *
 * @param lapTimes - Array of lap times
 * @param fileName - Base file name (default: 'lap_times')
 */
export function exportAndDownloadLapTimes(lapTimes: LapTime[], fileName = 'lap_times'): void {
  const csv = exportLapTimesToCsv(lapTimes, fileName);
  downloadCsv(csv, fileName);
}
