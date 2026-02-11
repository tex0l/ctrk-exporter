<script setup lang="ts">
import { computed } from 'vue';
import { useTelemetryData } from '@ctrk-exporter/astro-integration/composables';
import { computeLapTimes, computeSessionSummary, formatLapTime, formatDelta } from '../lib/lap-timing';
import { exportAndDownloadLapTimes } from '../lib/export-utils';

const { records, selectedLap, selectLap } = useTelemetryData();

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
  if (lapTimes.value.length === 0) return;
  exportAndDownloadLapTimes(lapTimes.value, 'lap_times');
}
</script>

<template>
  <div class="lap-timing-table">
    <div class="table-header">
      <h2>Lap Timing</h2>
      <button
        v-if="lapTimes.length > 0"
        @click="handleExport"
        class="export-button"
        title="Export to CSV"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          class="icon"
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

    <div v-if="sessionSummary.totalLaps === 0" class="no-data">
      <p>No lap data available</p>
    </div>

    <div v-else>
      <!-- Session Summary -->
      <div class="session-summary">
        <div class="summary-item">
          <span class="summary-label">Total Laps</span>
          <span class="summary-value">{{ sessionSummary.totalLaps }}</span>
        </div>
        <div class="summary-item">
          <span class="summary-label">Best Lap</span>
          <span class="summary-value">{{ sessionSummary.bestLap ?? '-' }}</span>
        </div>
        <div class="summary-item">
          <span class="summary-label">Best Time</span>
          <span class="summary-value">
            {{ sessionSummary.bestTime_ms ? formatLapTime(sessionSummary.bestTime_ms) : '-' }}
          </span>
        </div>
        <div class="summary-item">
          <span class="summary-label">Average Time</span>
          <span class="summary-value">
            {{ sessionSummary.averageTime_ms ? formatLapTime(sessionSummary.averageTime_ms) : '-' }}
          </span>
        </div>
      </div>

      <!-- Lap Times Table -->
      <div class="table-container">
        <table>
          <caption class="sr-only">
            Lap timing data showing {{ lapTimes.length }} laps
          </caption>
          <thead>
            <tr>
              <th scope="col">Lap</th>
              <th scope="col">Time</th>
              <th scope="col">Delta</th>
            </tr>
          </thead>
          <tbody>
            <tr
              :class="{ 'selected': selectedLap === null }"
              aria-label="All laps"
              tabindex="0"
              @click="handleLapClick(null)"
              @keydown="handleKeyDown($event, null, 0)"
            >
              <td class="lap-number all-laps-label" colspan="3">All Laps</td>
            </tr>
            <tr
              v-for="(lapTime, index) in lapTimes"
              :key="lapTime.lap"
              :class="{
                'best-lap': lapTime.isBest,
                'selected': selectedLap === lapTime.lap,
              }"
              :aria-label="lapTime.isBest ? `Lap ${lapTime.lap} (best lap)` : `Lap ${lapTime.lap}`"
              tabindex="0"
              @click="handleLapClick(lapTime.lap)"
              @keydown="handleKeyDown($event, lapTime.lap, index + 1)"
            >
              <td class="lap-number">{{ lapTime.lap }}</td>
              <td class="lap-time">{{ formatLapTime(lapTime.time_ms) }}</td>
              <td class="lap-delta" :class="{ 'zero-delta': lapTime.delta_ms === 0 }">
                {{ lapTime.delta_ms !== null ? formatDelta(lapTime.delta_ms) : '-' }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<style scoped>
.lap-timing-table {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.table-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.table-header h2 {
  margin: 0;
  font-size: 1.25rem;
}

.export-button {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  font-size: 0.875rem;
  background: var(--color-accent);
  color: white;
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: background var(--transition-fast);
}

.export-button:hover {
  background: var(--color-accent-hover, #005fa3);
}

.export-button .icon {
  width: 1rem;
  height: 1rem;
}

.no-data {
  padding: 2rem;
  text-align: center;
  color: var(--color-text-secondary);
}

.session-summary {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 1rem;
  margin-bottom: 1rem;
  padding: 1rem;
  background: var(--color-bg-tertiary);
  border-radius: var(--radius-sm);
}

.summary-item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.summary-label {
  font-size: 0.75rem;
  color: var(--color-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.summary-value {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--color-text);
}

.table-container {
  overflow-x: auto;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
}

thead {
  background: var(--color-bg-tertiary);
  border-bottom: 2px solid var(--color-border);
}

th {
  text-align: left;
  padding: 0.75rem 1rem;
  font-weight: 600;
  color: var(--color-text-secondary);
  font-size: 0.875rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

tbody tr {
  border-bottom: 1px solid var(--color-border);
  cursor: pointer;
  transition: background var(--transition-fast);
}

tbody tr:hover {
  background: var(--color-bg-tertiary);
}

tbody tr.selected {
  background: rgba(0, 102, 204, 0.1);
  font-weight: 600;
}

tbody tr.best-lap {
  background: rgba(46, 204, 113, 0.1);
}

tbody tr.best-lap:hover {
  background: rgba(46, 204, 113, 0.2);
}

tbody tr.best-lap.selected {
  background: rgba(46, 204, 113, 0.2);
}

td {
  padding: 0.75rem 1rem;
}

.lap-number {
  font-weight: 600;
  color: var(--color-text);
}

.all-laps-label {
  text-align: center;
  font-size: 0.875rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-text-secondary);
}

.lap-time {
  font-family: 'Monaco', 'Courier New', monospace;
  color: var(--color-text);
}

.lap-delta {
  font-family: 'Monaco', 'Courier New', monospace;
  color: var(--color-text-secondary);
}

.lap-delta.zero-delta {
  color: var(--color-success, #2ecc71);
  font-weight: 600;
}

/* Mobile: < 640px */
@media (max-width: 639px) {
  .table-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.5rem;
  }

  .table-header h2 {
    font-size: 1.125rem;
  }

  .export-button {
    padding: 0.5rem 0.875rem;
    font-size: 0.8rem;
    min-height: 44px;
  }

  .export-button .icon {
    width: 0.875rem;
    height: 0.875rem;
  }

  .session-summary {
    grid-template-columns: repeat(2, 1fr);
    gap: 0.75rem;
    padding: 0.75rem;
  }

  .summary-label {
    font-size: 0.7rem;
  }

  .summary-value {
    font-size: 1rem;
  }

  .table-container {
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
  }

  table {
    font-size: 0.85rem;
    min-width: 300px;
  }

  th {
    padding: 0.5rem 0.75rem;
    font-size: 0.8rem;
  }

  td {
    padding: 0.5rem 0.75rem;
  }

  .no-data {
    padding: 1.5rem;
    font-size: 0.9rem;
  }
}

/* Tablet: 640px - 1023px */
@media (min-width: 640px) and (max-width: 1023px) {
  .session-summary {
    grid-template-columns: repeat(2, 1fr);
  }
}

/* Desktop: >= 1024px */
@media (min-width: 1024px) {
  .session-summary {
    grid-template-columns: repeat(4, 1fr);
  }
}
</style>
