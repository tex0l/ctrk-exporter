/**
 * Vue composable for managing parser status and errors
 *
 * Provides reactive state for parsing operations, progress tracking,
 * and error handling.
 */

import { ref, computed, readonly } from 'vue';
import type { ParserStatus, ParserError } from '../types.js';

// Global state (singleton pattern)
const status = ref<ParserStatus>('idle');
const error = ref<ParserError | null>(null);
const progress = ref<number>(0);

/**
 * Composable for parser status management
 *
 * @example
 * ```vue
 * <script setup>
 * import { useParserStatus } from '@tex0l/ctrk-astro/composables';
 *
 * const { status, error, isLoading, reset } = useParserStatus();
 * </script>
 * ```
 */
export function useParserStatus() {
  /**
   * Set parser status to parsing
   */
  function startParsing(): void {
    status.value = 'parsing';
    error.value = null;
    progress.value = 0;
  }

  /**
   * Set parser status to success
   */
  function completeParsing(): void {
    status.value = 'success';
    progress.value = 100;
  }

  /**
   * Set parser status to error
   *
   * @param err - Parser error with message and context
   */
  function setError(err: ParserError): void {
    status.value = 'error';
    error.value = err;
    progress.value = 0;
  }

  /**
   * Update parsing progress
   *
   * @param percent - Progress percentage (0-100)
   */
  function updateProgress(percent: number): void {
    progress.value = Math.min(100, Math.max(0, percent));
  }

  /**
   * Reset parser status to idle
   */
  function reset(): void {
    status.value = 'idle';
    error.value = null;
    progress.value = 0;
  }

  /**
   * Check if parser is currently parsing
   */
  const isLoading = computed(() => status.value === 'parsing');

  /**
   * Check if parser has an error
   */
  const hasError = computed(() => status.value === 'error' && error.value !== null);

  /**
   * Check if parser completed successfully
   */
  const isSuccess = computed(() => status.value === 'success');

  return {
    // State (readonly)
    status: readonly(status),
    error: readonly(error),
    progress: readonly(progress),

    // Computed
    isLoading,
    hasError,
    isSuccess,

    // Actions
    startParsing,
    completeParsing,
    setError,
    updateProgress,
    reset,
  };
}
