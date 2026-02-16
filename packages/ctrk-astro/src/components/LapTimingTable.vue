<script setup lang="ts">
import { computed } from 'vue';
import { useTelemetryData } from '@tex0l/ctrk-astro/composables';
import { computeLapTimes, computeSessionSummary, formatLapTime, formatDelta } from '@tex0l/ctrk-astro/lib/lap-timing';
import { exportAndDownloadTelemetry } from '@tex0l/ctrk-astro/lib/export-utils';

const { records, selectedLap, selectLap, metadata } = useTelemetryData();

const lapTimes = computed(() => computeLapTimes(records.value));
const sessionSummary = computed(() => computeSessionSummary(lapTimes.value));

function handleLapClick(lap: number | null) {
  if (lap === null || selectedLap.value === lap) {
    selectLap(null);
  } else {
    selectLap(lap);
  }
}

function handleKeyDown(event: KeyboardEvent, lap: number | null, index: number) {
  const target = event.currentTarget as HTMLElement;
  const allRows = target.parentElement?.querySelectorAll('tr') || [];

  switch (event.key) {
    case 'Enter':
    case ' ':
      event.preventDefault();
      handleLapClick(lap);
      break;
    case 'ArrowUp':
      event.preventDefault();
      if (index > 0) {
        (allRows[index - 1] as HTMLElement)?.focus();
      }
      break;
    case 'ArrowDown':
      event.preventDefault();
      if (index < allRows.length - 1) {
        (allRows[index + 1] as HTMLElement)?.focus();
      }
      break;
  }
}

function handleExport() {
  if (records.value.length === 0) return;
  const stem = metadata.value?.fileName?.replace(/\.ctrk$/i, '') ?? 'telemetry';
  exportAndDownloadTelemetry(records.value, `${stem}_parsed`);
}
</script>

<template>
  <div class="flex flex-col gap-4">
    <div class="flex justify-between items-center mb-2 max-sm:flex-col max-sm:items-start max-sm:gap-2">
      <h2 class="m-0 text-xl max-sm:text-lg">Lap Timing</h2>
      <button
        v-if="lapTimes.length > 0"
        @click="handleExport"
        class="flex items-center gap-2 px-4 py-2 max-sm:px-3.5 max-sm:py-2 max-sm:min-h-[44px] text-sm max-sm:text-xs bg-(--color-accent) text-white border-none rounded-sm cursor-pointer transition-colors duration-150 hover:bg-(--color-accent-hover)"
        title="Export to CSV"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          class="w-4 h-4 max-sm:w-3.5 max-sm:h-3.5"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
          />
        </svg>
        Export CSV
      </button>
    </div>

    <div v-if="sessionSummary.totalLaps === 0" class="p-8 max-sm:p-6 text-center text-(--color-text-secondary) max-sm:text-sm">
      <p>No lap data available</p>
    </div>

    <div v-else>
      <!-- Session Summary -->
      <div class="grid grid-cols-[repeat(auto-fit,minmax(120px,1fr))] max-sm:grid-cols-2 sm:grid-cols-[repeat(auto-fit,minmax(120px,1fr))] lg:grid-cols-4 gap-4 max-sm:gap-3 mb-4 p-4 max-sm:p-3 bg-(--color-bg-tertiary) rounded-sm">
        <div class="flex flex-col gap-1">
          <span class="text-xs max-sm:text-[0.7rem] text-(--color-text-secondary) uppercase tracking-wide">Total Laps</span>
          <span class="text-lg max-sm:text-base font-semibold text-(--color-text-primary)">{{ sessionSummary.totalLaps }}</span>
        </div>
        <div class="flex flex-col gap-1">
          <span class="text-xs max-sm:text-[0.7rem] text-(--color-text-secondary) uppercase tracking-wide">Best Lap</span>
          <span class="text-lg max-sm:text-base font-semibold text-(--color-text-primary)">{{ sessionSummary.bestLap ?? '-' }}</span>
        </div>
        <div class="flex flex-col gap-1">
          <span class="text-xs max-sm:text-[0.7rem] text-(--color-text-secondary) uppercase tracking-wide">Best Time</span>
          <span class="text-lg max-sm:text-base font-semibold text-(--color-text-primary)">
            {{ sessionSummary.bestTime_ms ? formatLapTime(sessionSummary.bestTime_ms) : '-' }}
          </span>
        </div>
        <div class="flex flex-col gap-1">
          <span class="text-xs max-sm:text-[0.7rem] text-(--color-text-secondary) uppercase tracking-wide">Average Time</span>
          <span class="text-lg max-sm:text-base font-semibold text-(--color-text-primary)">
            {{ sessionSummary.averageTime_ms ? formatLapTime(sessionSummary.averageTime_ms) : '-' }}
          </span>
        </div>
      </div>

      <!-- Lap Times Table -->
      <div class="overflow-x-auto max-sm:touch-pan-x border border-(--color-border) rounded-sm">
        <table class="w-full border-collapse text-sm max-sm:text-[0.85rem] max-sm:min-w-[300px]">
          <caption class="sr-only">
            Lap timing data showing {{ lapTimes.length }} laps
          </caption>
          <thead class="bg-(--color-bg-tertiary) border-b-2 border-(--color-border)">
            <tr>
              <th class="text-left px-4 py-3 max-sm:px-3 max-sm:py-2 font-semibold text-(--color-text-secondary) text-sm max-sm:text-xs uppercase tracking-wide" scope="col">Lap</th>
              <th class="text-left px-4 py-3 max-sm:px-3 max-sm:py-2 font-semibold text-(--color-text-secondary) text-sm max-sm:text-xs uppercase tracking-wide" scope="col">Time</th>
              <th class="text-left px-4 py-3 max-sm:px-3 max-sm:py-2 font-semibold text-(--color-text-secondary) text-sm max-sm:text-xs uppercase tracking-wide" scope="col">Delta</th>
            </tr>
          </thead>
          <tbody>
            <tr
              :class="[
                'border-b border-(--color-border) cursor-pointer transition-colors duration-150 hover:bg-(--color-bg-tertiary)',
                selectedLap === null ? 'bg-(--color-highlight-info) font-semibold' : '',
              ]"
              aria-label="All laps"
              tabindex="0"
              @click="handleLapClick(null)"
              @keydown="handleKeyDown($event, null, 0)"
            >
              <td class="px-4 py-3 max-sm:px-3 max-sm:py-2 text-center font-semibold text-sm uppercase tracking-wide text-(--color-text-secondary)" colspan="3">All Laps</td>
            </tr>
            <tr
              v-for="(lapTime, index) in lapTimes"
              :key="lapTime.lap"
              :class="[
                'border-b border-(--color-border) cursor-pointer transition-colors duration-150',
                lapTime.isBest ? 'bg-(--color-highlight-success) hover:bg-(--color-highlight-success-hover)' : 'hover:bg-(--color-bg-tertiary)',
                selectedLap === lapTime.lap ? (lapTime.isBest ? 'bg-(--color-highlight-success-hover) font-semibold' : 'bg-(--color-highlight-info) font-semibold') : '',
              ]"
              :aria-label="lapTime.isBest ? `Lap ${lapTime.lap} (best lap)` : `Lap ${lapTime.lap}`"
              tabindex="0"
              @click="handleLapClick(lapTime.lap)"
              @keydown="handleKeyDown($event, lapTime.lap, index + 1)"
            >
              <td class="px-4 py-3 max-sm:px-3 max-sm:py-2 font-semibold text-(--color-text-primary)">{{ lapTime.lap }}</td>
              <td class="px-4 py-3 max-sm:px-3 max-sm:py-2 font-mono text-(--color-text-primary)">{{ formatLapTime(lapTime.time_ms) }}</td>
              <td :class="[
                'px-4 py-3 max-sm:px-3 max-sm:py-2 font-mono text-(--color-text-secondary)',
                lapTime.delta_ms === 0 ? 'text-(--color-success) font-semibold' : '',
              ]">
                {{ lapTime.delta_ms !== null ? formatDelta(lapTime.delta_ms) : '-' }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
