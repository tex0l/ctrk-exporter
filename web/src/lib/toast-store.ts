/**
 * Toast notification state management
 */

import { ref, readonly } from 'vue';

/**
 * Toast types
 */
export type ToastType = 'success' | 'error' | 'info' | 'warning';

/**
 * Toast notification
 */
export interface Toast {
  id: number;
  type: ToastType;
  message: string;
  duration?: number;
}

// Global state
const toasts = ref<Toast[]>([]);
let nextId = 1;

/**
 * Default toast duration (5 seconds)
 */
const DEFAULT_DURATION = 5000;

/**
 * Composable for toast notifications
 *
 * @example
 * ```vue
 * <script setup>
 * import { useToast } from '../lib/toast-store';
 *
 * const { showSuccess, showError } = useToast();
 * showSuccess('File parsed successfully!');
 * </script>
 * ```
 */
export function useToast() {
  /**
   * Add a toast notification
   *
   * @param type - Toast type
   * @param message - Toast message
   * @param duration - Duration in milliseconds (default: 5000)
   * @returns Toast ID
   */
  function addToast(type: ToastType, message: string, duration = DEFAULT_DURATION): number {
    const id = nextId++;
    const toast: Toast = { id, type, message, duration };

    toasts.value.push(toast);

    // Auto-remove after duration
    if (duration > 0) {
      setTimeout(() => {
        removeToast(id);
      }, duration);
    }

    return id;
  }

  /**
   * Remove a toast by ID
   *
   * @param id - Toast ID
   */
  function removeToast(id: number): void {
    const index = toasts.value.findIndex((t) => t.id === id);
    if (index !== -1) {
      toasts.value.splice(index, 1);
    }
  }

  /**
   * Clear all toasts
   */
  function clearAll(): void {
    toasts.value = [];
  }

  /**
   * Show a success toast
   *
   * @param message - Success message
   * @param duration - Duration in milliseconds
   */
  function showSuccess(message: string, duration?: number): void {
    addToast('success', message, duration);
  }

  /**
   * Show an error toast
   *
   * @param message - Error message
   * @param duration - Duration in milliseconds (default: 7000 for errors)
   */
  function showError(message: string, duration = 7000): void {
    addToast('error', message, duration);
  }

  /**
   * Show an info toast
   *
   * @param message - Info message
   * @param duration - Duration in milliseconds
   */
  function showInfo(message: string, duration?: number): void {
    addToast('info', message, duration);
  }

  /**
   * Show a warning toast
   *
   * @param message - Warning message
   * @param duration - Duration in milliseconds
   */
  function showWarning(message: string, duration?: number): void {
    addToast('warning', message, duration);
  }

  return {
    // State (readonly)
    toasts: readonly(toasts),

    // Actions
    addToast,
    removeToast,
    clearAll,
    showSuccess,
    showError,
    showInfo,
    showWarning,
  };
}
