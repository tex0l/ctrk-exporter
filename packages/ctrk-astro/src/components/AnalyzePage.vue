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
  <div v-if="hasData" class="analyze-page">
    <!-- File Info -->
    <div class="card">
      <h2>File Information</h2>
      <div class="info-grid">
        <div class="info-item">
          <span class="info-label">File Name</span>
          <span class="info-value">{{ metadata?.fileName }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">File Size</span>
          <span class="info-value">{{ metadata ? formatFileSize(metadata.fileSize) : '-' }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">Parse Time</span>
          <span class="info-value">{{ metadata ? (metadata.parseTime).toFixed(2) + 'ms' : '-' }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">Total Records</span>
          <span class="info-value">{{ records.length.toLocaleString() }}</span>
        </div>
      </div>
    </div>

    <!-- Lap Selector -->
    <div class="card">
      <div class="lap-selector-header">
        <h2>Lap Selection</h2>
        <div class="lap-selector">
          <label for="lap-select">Select Lap:</label>
          <select id="lap-select" :value="selectedLap ?? 'all'" @change="handleLapChange">
            <option value="all">All Laps ({{ laps.length }} total)</option>
            <option v-for="lap in laps" :key="lap" :value="lap">
              Lap {{ lap }}
            </option>
          </select>
        </div>
      </div>

      <div v-if="statistics" class="statistics-grid">
        <div class="stat-card">
          <span class="stat-label">Records</span>
          <span class="stat-value">{{ statistics.recordCount.toLocaleString() }}</span>
        </div>
        <div class="stat-card">
          <span class="stat-label">Duration</span>
          <span class="stat-value">{{ formatDuration(statistics.duration) }}</span>
        </div>
        <div class="stat-card">
          <span class="stat-label">Start Time</span>
          <span class="stat-value stat-value-sm">{{ formatDateTime(statistics.startTime) }}</span>
        </div>
        <div class="stat-card">
          <span class="stat-label">End Time</span>
          <span class="stat-value stat-value-sm">{{ formatDateTime(statistics.endTime) }}</span>
        </div>
      </div>
    </div>

    <!-- GPS Track Map and Lap Timing (side by side) -->
    <div class="visualization-grid">
      <div class="card">
        <TrackMap />
      </div>

      <div class="card">
        <LapTimingTable />
      </div>
    </div>

    <!-- Telemetry Charts (full width) -->
    <div class="card">
      <TelemetryChart />
    </div>
  </div>
</template>

<style scoped>
.analyze-page {
  max-width: 1400px;
  margin: 0 auto;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1.5rem;
  margin-top: 1rem;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.info-label {
  font-size: 0.875rem;
  color: var(--color-text-secondary);
  font-weight: 500;
}

.info-value {
  font-size: 1.125rem;
  color: var(--color-text);
  font-weight: 600;
}

.lap-selector-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.lap-selector-header h2 {
  margin: 0;
}

.lap-selector {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.lap-selector label {
  font-weight: 500;
  font-size: 0.95rem;
}

.statistics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 1rem;
}

.stat-card {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  padding: 1rem;
  background: var(--color-bg-tertiary);
  border-radius: var(--radius-sm);
}

.stat-label {
  font-size: 0.875rem;
  color: var(--color-text-secondary);
}

.stat-value {
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--color-accent);
}

.stat-value-sm {
  font-size: 1rem;
}

.visualization-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.5rem;
}

.visualization-grid .card {
  min-height: 500px;
  display: flex;
  flex-direction: column;
}

/* Mobile: < 640px */
@media (max-width: 639px) {
  .analyze-page {
    max-width: 100%;
  }

  .card {
    padding: 1rem;
  }

  .info-grid {
    grid-template-columns: 1fr;
    gap: 1rem;
  }

  .info-label {
    font-size: 0.8rem;
  }

  .info-value {
    font-size: 1rem;
  }

  .lap-selector-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.75rem;
  }

  .lap-selector-header h2 {
    font-size: 1.125rem;
  }

  .lap-selector {
    width: 100%;
  }

  .lap-selector label {
    font-size: 0.875rem;
  }

  .lap-selector select {
    flex: 1;
    min-height: 44px;
  }

  .statistics-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 0.75rem;
  }

  .stat-card {
    padding: 0.75rem;
  }

  .stat-label {
    font-size: 0.75rem;
  }

  .stat-value {
    font-size: 1.25rem;
  }

  .visualization-grid {
    grid-template-columns: 1fr;
    gap: 1rem;
  }

  .visualization-grid .card {
    min-height: auto;
  }
}

/* Tablet: 640px - 1023px */
@media (min-width: 640px) and (max-width: 1023px) {
  .analyze-page {
    max-width: 100%;
  }

  .info-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .statistics-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .visualization-grid {
    grid-template-columns: 1fr;
    gap: 1.5rem;
  }

  .visualization-grid .card {
    min-height: auto;
  }
}

/* Desktop: >= 1024px */
@media (min-width: 1024px) {
  .visualization-grid {
    grid-template-columns: 1fr 1fr;
  }
}
</style>
