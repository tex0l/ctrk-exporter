/**
 * File validation utilities for CTRK files
 */

/**
 * Minimum file size (100 bytes)
 */
export const MIN_FILE_SIZE = 100;

/**
 * Maximum file size (50 MB)
 */
export const MAX_FILE_SIZE = 50 * 1024 * 1024;

/**
 * CTRK file magic bytes (first 4 bytes should be "HEAD")
 */
export const CTRK_MAGIC_BYTES = [0x48, 0x45, 0x41, 0x44]; // "HEAD"

/**
 * Validation error types
 */
export type ValidationErrorType =
  | 'invalid_extension'
  | 'file_too_small'
  | 'file_too_large'
  | 'invalid_magic_bytes'
  | 'read_error';

/**
 * Validation error
 */
export interface ValidationError {
  type: ValidationErrorType;
  message: string;
}

/**
 * Validates file extension (.CTRK)
 *
 * @param fileName - File name to validate
 * @returns Error if invalid, null if valid
 */
export function validateExtension(fileName: string): ValidationError | null {
  if (!fileName.toLowerCase().endsWith('.ctrk')) {
    return {
      type: 'invalid_extension',
      message: 'Invalid file type. Please select a .CTRK file.',
    };
  }
  return null;
}

/**
 * Validates file size (100 bytes minimum, 50 MB maximum)
 *
 * @param fileSize - File size in bytes
 * @returns Error if invalid, null if valid
 */
export function validateFileSize(fileSize: number): ValidationError | null {
  if (fileSize < MIN_FILE_SIZE) {
    return {
      type: 'file_too_small',
      message: `File is too small (${fileSize} bytes). Minimum size is ${MIN_FILE_SIZE} bytes.`,
    };
  }
  if (fileSize > MAX_FILE_SIZE) {
    return {
      type: 'file_too_large',
      message: `File is too large (${(fileSize / 1024 / 1024).toFixed(2)} MB). Maximum size is ${MAX_FILE_SIZE / 1024 / 1024} MB.`,
    };
  }
  return null;
}

/**
 * Validates CTRK magic bytes (first 4 bytes should be "HEAD")
 *
 * @param data - File data
 * @returns Error if invalid, null if valid
 */
export function validateMagicBytes(data: Uint8Array): ValidationError | null {
  if (data.length < 4) {
    return {
      type: 'invalid_magic_bytes',
      message: 'File is too small to contain valid CTRK header.',
    };
  }

  for (let i = 0; i < CTRK_MAGIC_BYTES.length; i++) {
    if (data[i] !== CTRK_MAGIC_BYTES[i]) {
      return {
        type: 'invalid_magic_bytes',
        message: `Invalid CTRK file format. Expected magic bytes "HEAD", got "${String.fromCharCode(data[0], data[1], data[2], data[3])}".`,
      };
    }
  }

  return null;
}

/**
 * Validates a CTRK file
 *
 * Performs all validation checks:
 * - Extension check
 * - File size check
 * - Magic bytes check (requires reading file)
 *
 * @param file - File to validate
 * @returns Promise resolving to error if invalid, null if valid
 */
export async function validateCTRKFile(file: File): Promise<ValidationError | null> {
  // Check extension
  const extError = validateExtension(file.name);
  if (extError) return extError;

  // Check file size
  const sizeError = validateFileSize(file.size);
  if (sizeError) return sizeError;

  // Read first 4 bytes to check magic bytes
  try {
    const buffer = await file.slice(0, 4).arrayBuffer();
    const data = new Uint8Array(buffer);
    const magicError = validateMagicBytes(data);
    if (magicError) return magicError;
  } catch (err) {
    return {
      type: 'read_error',
      message: `Failed to read file: ${err instanceof Error ? err.message : 'Unknown error'}`,
    };
  }

  return null;
}
