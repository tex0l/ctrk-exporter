/**
 * Browser utilities for working with CTRK files
 */

/**
 * Converts a File object to Uint8Array for parsing
 *
 * @param file - The File object from a file input or drag-and-drop
 * @returns Promise resolving to Uint8Array
 *
 * @example
 * ```typescript
 * const input = document.querySelector('input[type="file"]');
 * input.addEventListener('change', async (e) => {
 *   const file = e.target.files[0];
 *   const data = await fileToUint8Array(file);
 *   const parser = new CTRKParser(data);
 *   const records = parser.parse();
 * });
 * ```
 */
export async function fileToUint8Array(file: File): Promise<Uint8Array> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();

    reader.onload = () => {
      if (reader.result instanceof ArrayBuffer) {
        resolve(new Uint8Array(reader.result));
      } else {
        reject(new Error('Failed to read file as ArrayBuffer'));
      }
    };

    reader.onerror = () => {
      reject(new Error('FileReader error: ' + reader.error?.message));
    };

    reader.readAsArrayBuffer(file);
  });
}

/**
 * Validates that a file has the .CTRK extension
 *
 * @param fileName - The file name to validate
 * @returns True if the file has .CTRK extension (case-insensitive)
 */
export function isCTRKFile(fileName: string): boolean {
  return fileName.toLowerCase().endsWith('.ctrk');
}

/**
 * Formats file size in human-readable format
 *
 * @param bytes - File size in bytes
 * @returns Formatted string (e.g., "1.5 MB")
 */
export function formatFileSize(bytes: number): string {
  const units = ['B', 'KB', 'MB', 'GB'];
  let size = bytes;
  let unitIndex = 0;

  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex++;
  }

  return `${size.toFixed(unitIndex === 0 ? 0 : 1)} ${units[unitIndex]}`;
}

/**
 * Formats parse time in human-readable format
 *
 * @param milliseconds - Parse time in milliseconds
 * @returns Formatted string (e.g., "1.2s" or "345ms")
 */
export function formatParseTime(milliseconds: number): string {
  if (milliseconds < 1000) {
    return `${Math.round(milliseconds)}ms`;
  }
  return `${(milliseconds / 1000).toFixed(2)}s`;
}
