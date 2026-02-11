/**
 * Vue composable for managing telemetry data state
 *
 * Provides reactive state for parsed CTRK telemetry records with
 * lap filtering, statistics, and channel access.
 */

import { ref, computed, readonly } from 'vue';
import type { TelemetryRecord } from '@ctrk/parser';
import type { ParserResult } from '../types.js';

// Global state (singleton pattern for composables)
const records = ref<TelemetryRecord[]>([]);
const selectedLap = ref<number | null>(null);
const metadata = ref<Omit<ParserResult, 'records'> | null>(null);

/**
 * Composable for telemetry data management
 *
 * @example
 * ```vue
 * <script setup>
 * import { useTelemetryData } from '@ctrk-exporter/astro-integration/composables';
 *
 * const { records, laps, selectedLap, selectLap, clear } = useTelemetryData();
 * </script>
 * ```
 */
export function useTelemetryData() {
  /**
   * List of unique lap numbers in the dataset
   */
  const laps = computed(() => {
    const lapSet = new Set(records.value.map((r) => r.lap));
    return [...lapSet].sort((a, b) => a - b);
  });

  /**
   * Records filtered by selected lap (or all if none selected)
   */
  const filteredRecords = computed(() => {
    if (selectedLap.value === null) {
      return records.value;
    }
    return records.value.filter((r) => r.lap === selectedLap.value);
  });

  /**
   * Statistics about the current dataset
   */
  const statistics = computed(() => {
    const filtered = filteredRecords.value;
    if (filtered.length === 0) {
      return null;
    }

    const first = filtered[0];
    const last = filtered[filtered.length - 1];

    return {
      recordCount: filtered.length,
      lapCount: laps.value.length,
      duration: (last.time_ms - first.time_ms) / 1000, // seconds
      startTime: first.time_ms,
      endTime: last.time_ms,
    };
  });

  /**
   * Load parsed telemetry data
   *
   * @param result - Parser result containing records and metadata
   */
  function loadRecords(result: ParserResult): void {
    records.value = result.records;
    metadata.value = {
      fileName: result.fileName,
      fileSize: result.fileSize,
      parseTime: result.parseTime,
    };
    selectedLap.value = null;
  }

  /**
   * Select a specific lap to filter records
   *
   * @param lap - Lap number to select, or null for all laps
   */
  function selectLap(lap: number | null): void {
    selectedLap.value = lap;
  }

  /**
   * Clear all telemetry data
   */
  function clear(): void {
    records.value = [];
    selectedLap.value = null;
    metadata.value = null;
  }

  /**
   * Check if telemetry data is loaded
   */
  const hasData = computed(() => records.value.length > 0);

  return {
    // State (readonly to prevent external mutations)
    records: readonly(records),
    selectedLap: readonly(selectedLap),
    metadata: readonly(metadata),

    // Computed
    laps,
    filteredRecords,
    statistics,
    hasData,

    // Actions
    loadRecords,
    selectLap,
    clear,
  };
}
