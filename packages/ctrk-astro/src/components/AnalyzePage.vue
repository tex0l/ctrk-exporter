<script setup lang="ts">
import { computed } from 'vue';
import { useTelemetryData } from '@tex0l/ctrk-astro/composables';
import { formatFileSize } from '@tex0l/ctrk-astro/utils';
import TrackMap from './TrackMap.vue';
import TelemetryChart from './TelemetryChart.vue';
import LapTimingTable from './LapTimingTable.vue';

const { records, laps, filteredRecords, selectedLap, selectLap, metadata, hasData } = useTelemetryData();

const statistics = computed(() => {
  if (filteredRecords.value.length === 0) return null;

  const first = filteredRecords.value[0];
  const last = filteredRecords.value[filteredRecords.value.length - 1];

  return {
    recordCount: filteredRecords.value.length,
    lapCount: laps.value.length,
    duration: (last.time_ms - first.time_ms) / 1000,
    startTime: first.time_ms,
    endTime: last.time_ms,
  };
});

function handleLapChange(event: Event) {
  const select = event.target as HTMLSelectElement;
  const value = select.value;
  selectLap(value === 'all' ? null : parseInt(value, 10));
}

function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = (seconds % 60).toFixed(1);
  return `${mins}:${secs.padStart(4, '0')}`;
}

function formatDateTime(epochMs: number): string {
  const date = new Date(epochMs);
  return date.toLocaleString(undefined, {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}
</script>

<template>
  <div v-if="hasData" class="max-w-[1400px] mx-auto max-sm:max-w-full">
    <!-- File Info -->
    <div class="bg-(--color-bg-secondary) border border-(--color-border) rounded-md p-6 max-sm:p-4 mb-6">
      <h2 class="text-xl max-sm:text-lg font-semibold mb-4">File Information</h2>
      <div class="grid grid-cols-[repeat(auto-fit,minmax(200px,1fr))] max-sm:grid-cols-1 sm:grid-cols-2 gap-6 max-sm:gap-4 mt-4">
        <div class="flex flex-col gap-1">
          <span class="text-sm max-sm:text-xs text-(--color-text-secondary) font-medium">File Name</span>
          <span class="text-lg max-sm:text-base text-(--color-text-primary) font-semibold">{{ metadata?.fileName }}</span>
        </div>
        <div class="flex flex-col gap-1">
          <span class="text-sm max-sm:text-xs text-(--color-text-secondary) font-medium">File Size</span>
          <span class="text-lg max-sm:text-base text-(--color-text-primary) font-semibold">{{ metadata ? formatFileSize(metadata.fileSize) : '-' }}</span>
        </div>
        <div class="flex flex-col gap-1">
          <span class="text-sm max-sm:text-xs text-(--color-text-secondary) font-medium">Parse Time</span>
          <span class="text-lg max-sm:text-base text-(--color-text-primary) font-semibold">{{ metadata ? (metadata.parseTime).toFixed(2) + 'ms' : '-' }}</span>
        </div>
        <div class="flex flex-col gap-1">
          <span class="text-sm max-sm:text-xs text-(--color-text-secondary) font-medium">Total Records</span>
          <span class="text-lg max-sm:text-base text-(--color-text-primary) font-semibold">{{ records.length.toLocaleString() }}</span>
        </div>
      </div>
    </div>

    <!-- Lap Selector -->
    <div class="bg-(--color-bg-secondary) border border-(--color-border) rounded-md p-6 max-sm:p-4 mb-6">
      <div class="flex justify-between items-center flex-wrap gap-4 mb-6 max-sm:flex-col max-sm:items-start max-sm:gap-3">
        <h2 class="m-0 text-xl max-sm:text-lg font-semibold">Lap Selection</h2>
        <div class="flex items-center gap-3 max-sm:w-full">
          <label for="lap-select" class="font-medium text-[0.95rem] max-sm:text-sm">Select Lap:</label>
          <select
            id="lap-select"
            :value="selectedLap ?? 'all'"
            @change="handleLapChange"
            class="max-sm:flex-1 max-sm:min-h-[44px]"
          >
            <option value="all">All Laps ({{ laps.length }} total)</option>
            <option v-for="lap in laps" :key="lap" :value="lap">
              Lap {{ lap }}
            </option>
          </select>
        </div>
      </div>

      <div v-if="statistics" class="grid grid-cols-[repeat(auto-fit,minmax(150px,1fr))] max-sm:grid-cols-2 gap-4 max-sm:gap-3">
        <div class="flex flex-col gap-1 p-4 max-sm:p-3 bg-(--color-bg-tertiary) rounded-sm">
          <span class="text-sm max-sm:text-xs text-(--color-text-secondary)">Records</span>
          <span class="text-2xl max-sm:text-xl font-semibold text-(--color-accent)">{{ statistics.recordCount.toLocaleString() }}</span>
        </div>
        <div class="flex flex-col gap-1 p-4 max-sm:p-3 bg-(--color-bg-tertiary) rounded-sm">
          <span class="text-sm max-sm:text-xs text-(--color-text-secondary)">Duration</span>
          <span class="text-2xl max-sm:text-xl font-semibold text-(--color-accent)">{{ formatDuration(statistics.duration) }}</span>
        </div>
        <div class="flex flex-col gap-1 p-4 max-sm:p-3 bg-(--color-bg-tertiary) rounded-sm">
          <span class="text-sm max-sm:text-xs text-(--color-text-secondary)">Start Time</span>
          <span class="text-base font-semibold text-(--color-accent)">{{ formatDateTime(statistics.startTime) }}</span>
        </div>
        <div class="flex flex-col gap-1 p-4 max-sm:p-3 bg-(--color-bg-tertiary) rounded-sm">
          <span class="text-sm max-sm:text-xs text-(--color-text-secondary)">End Time</span>
          <span class="text-base font-semibold text-(--color-accent)">{{ formatDateTime(statistics.endTime) }}</span>
        </div>
      </div>
    </div>

    <!-- GPS Track Map and Lap Timing (side by side) -->
    <div class="grid grid-cols-2 lg:grid-cols-2 max-lg:grid-cols-1 gap-6">
      <div class="bg-(--color-bg-secondary) border border-(--color-border) rounded-md p-6 max-sm:p-4 mb-6 min-h-[500px] max-lg:min-h-0 flex flex-col">
        <TrackMap />
      </div>

      <div class="bg-(--color-bg-secondary) border border-(--color-border) rounded-md p-6 max-sm:p-4 mb-6 min-h-[500px] max-lg:min-h-0 flex flex-col">
        <LapTimingTable />
      </div>
    </div>

    <!-- Telemetry Charts (full width) -->
    <div class="bg-(--color-bg-secondary) border border-(--color-border) rounded-md p-6 max-sm:p-4 mb-6">
      <TelemetryChart />
    </div>
  </div>
</template>
