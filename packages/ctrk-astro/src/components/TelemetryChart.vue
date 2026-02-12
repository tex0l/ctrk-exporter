<script setup lang="ts">
import { ref, computed, onMounted, watch, onUnmounted } from 'vue';
import { useTelemetryData } from '@tex0l/ctrk-astro/composables';
import { Calibration } from '@tex0l/ctrk-astro';
import {
  getAllChannels,
  getDefaultEnabledChannelIds,
  filterAnalogChannelIds,
  filterBooleanChannelIds,
  type ChannelDefinition,
} from '@tex0l/ctrk-astro/lib/chart-config';
import { downsampleMultiSeries, applyDownsampling } from '@tex0l/ctrk-astro/lib/downsample';
import ChannelSelector from './ChannelSelector.vue';
import type {
  Chart as ChartJS,
  ChartConfiguration,
  ScaleOptions,
} from 'chart.js';

const { filteredRecords } = useTelemetryData();

const analogCanvas = ref<HTMLCanvasElement | null>(null);
const booleanCanvas = ref<HTMLCanvasElement | null>(null);
let analogChart: ChartJS | null = null;
let booleanChart: ChartJS | null = null;
let ChartModule: typeof import('chart.js') | null = null;

// Channel selection
const enabledChannelIds = ref<string[]>(getDefaultEnabledChannelIds());

const allChannels = getAllChannels();

const enabledAnalogChannels = computed(() => {
  const analogIds = filterAnalogChannelIds(enabledChannelIds.value);
  return allChannels.filter((c) => analogIds.includes(c.id));
});

const enabledBooleanChannels = computed(() => {
  const booleanIds = filterBooleanChannelIds(enabledChannelIds.value);
  return allChannels.filter((c) => booleanIds.includes(c.id));
});

const hasData = computed(() => filteredRecords.value.length > 0);
const hasAnalogChannels = computed(() => enabledAnalogChannels.value.length > 0);
const hasBooleanChannels = computed(() => enabledBooleanChannels.value.length > 0);

const analogChartSummary = computed(() => {
  const channelCount = enabledAnalogChannels.value.length;
  const recordCount = filteredRecords.value.length;
  return `Analog telemetry chart displaying ${channelCount} channel${channelCount !== 1 ? 's' : ''} over ${recordCount} data points`;
});

const booleanChartSummary = computed(() => {
  const channelCount = enabledBooleanChannels.value.length;
  const recordCount = filteredRecords.value.length;
  return `Boolean telemetry chart displaying ${channelCount} channel${channelCount !== 1 ? 's' : ''} over ${recordCount} data points`;
});

// Initialize Chart.js
onMounted(async () => {
  try {
    ChartModule = await import('chart.js');
    const {
      Chart,
      LinearScale,
      LineElement,
      PointElement,
      LineController,
      Tooltip,
      Legend,
      Filler,
    } = ChartModule;

    Chart.register(
      LinearScale,
      LineElement,
      PointElement,
      LineController,
      Tooltip,
      Legend,
      Filler
    );

    renderCharts();
  } catch (err) {
    console.error('Failed to initialize Chart.js:', err);
  }
});

// Cleanup on unmount
onUnmounted(() => {
  if (renderTimer !== null) {
    cancelAnimationFrame(renderTimer);
    renderTimer = null;
  }
  if (analogChart) {
    analogChart.destroy();
    analogChart = null;
  }
  if (booleanChart) {
    booleanChart.destroy();
    booleanChart = null;
  }
});

// Debounced render via requestAnimationFrame
let renderTimer: number | null = null;

function scheduleRender() {
  if (renderTimer !== null) {
    cancelAnimationFrame(renderTimer);
  }
  renderTimer = requestAnimationFrame(() => {
    renderTimer = null;
    renderCharts();
  });
}

// Watch for data or selection changes (debounced)
watch([filteredRecords, enabledChannelIds], () => {
  scheduleRender();
});

// Calibrate a raw value to engineering units
function calibrateValue(channel: ChannelDefinition, raw: number): number {
  switch (channel.id) {
    case 'rpm':
      return Calibration.rpm(raw);
    case 'tps':
    case 'aps':
      return Calibration.throttle(raw);
    case 'front_speed':
    case 'rear_speed':
      return Calibration.wheelSpeedKmh(raw);
    case 'gps_speed_knots':
      return Calibration.gpsSpeedKmh(raw);
    case 'front_brake':
    case 'rear_brake':
      return Calibration.brake(raw);
    case 'lean':
    case 'lean_signed':
      return Calibration.lean(raw);
    case 'pitch':
      return Calibration.pitch(raw);
    case 'acc_x':
    case 'acc_y':
      return Calibration.acceleration(raw);
    case 'water_temp':
    case 'intake_temp':
      return Calibration.temperature(raw);
    case 'fuel':
      return Calibration.fuel(raw);
    case 'gear':
      return raw;
    case 'f_abs':
    case 'r_abs':
      return raw ? 1 : 0;
    case 'tcs':
    case 'scs':
    case 'lif':
    case 'launch':
      return raw > 0 ? 1 : 0;
    default:
      return raw;
  }
}

// Downsampling threshold
const CHART_MAX_POINTS = 5000;

// Shared data cache to avoid recomputation between analog/boolean charts
let cachedTimeAxis: number[] = [];
let cachedXMin = 0;
let cachedXMax = 0;

// Per-chart left padding to align chart areas
let analogExtraPadding = 0;
let booleanExtraPadding = 0;

// Render both charts with X-axis alignment
function renderCharts() {
  if (!ChartModule || !hasData.value) {
    if (analogChart) {
      analogChart.destroy();
      analogChart = null;
    }
    if (booleanChart) {
      booleanChart.destroy();
      booleanChart = null;
    }
    return;
  }

  // Compute shared time axis once
  const records = filteredRecords.value;
  const firstTime = records[0].time_ms;
  cachedTimeAxis = records.map((r) => (r.time_ms - firstTime) / 1000);
  cachedXMin = cachedTimeAxis[0];
  cachedXMax = cachedTimeAxis[cachedTimeAxis.length - 1];

  // First pass: render with no extra padding to measure natural chartArea.left
  analogExtraPadding = 0;
  booleanExtraPadding = 0;
  renderAnalogChart();
  renderBooleanChart();

  // Second pass: synchronize chart areas if both charts exist
  if (analogChart && booleanChart) {
    const analogLeft = analogChart.chartArea?.left ?? 0;
    const booleanLeft = booleanChart.chartArea?.left ?? 0;

    // Only re-render if there's a meaningful difference (>1px)
    if (Math.abs(analogLeft - booleanLeft) > 1) {
      // Add padding only to the chart with less natural Y-axis space
      if (analogLeft > booleanLeft) {
        booleanExtraPadding = analogLeft - booleanLeft;
        renderBooleanChart();
      } else {
        analogExtraPadding = booleanLeft - analogLeft;
        renderAnalogChart();
      }
    }
  }
}

// Build {x,y} point datasets with downsampling
function buildPointData(
  channels: ChannelDefinition[],
  timeAxis: number[]
): { sampledData: { x: number; y: number }[][]; sampledTimeAxis: number[] } {
  const records = filteredRecords.value;

  // Extract raw channel data
  const allChannelData = channels.map((channel) =>
    records.map((record) => calibrateValue(channel, (record as any)[channel.id]))
  );

  let sampledTimeAxis = timeAxis;
  let sampledChannelData = allChannelData;

  if (timeAxis.length > CHART_MAX_POINTS) {
    const downsampleIndices = downsampleMultiSeries(allChannelData, CHART_MAX_POINTS);
    sampledTimeAxis = applyDownsampling(timeAxis, downsampleIndices);
    sampledChannelData = allChannelData.map((data) =>
      applyDownsampling(data, downsampleIndices)
    );
  }

  // Build {x,y} point arrays for Chart.js (optimal for linear scales)
  const sampledData = sampledChannelData.map((data) =>
    data.map((y, i) => ({ x: sampledTimeAxis[i], y }))
  );

  return { sampledData, sampledTimeAxis };
}

// Shared X-axis config (ensures alignment between charts)
function getXAxisConfig(showTitle: boolean): ScaleOptions<'linear'> {
  return {
    type: 'linear',
    min: cachedXMin,
    max: cachedXMax,
    title: {
      display: showTitle,
      text: 'Time (s)',
    },
    ticks: {
      callback: (value) => `${value}`,
    },
  } as ScaleOptions<'linear'>;
}

// Render analog chart
function renderAnalogChart() {
  if (!analogCanvas.value || !ChartModule || !hasData.value) {
    if (analogChart) {
      analogChart.destroy();
      analogChart = null;
    }
    return;
  }

  const { Chart } = ChartModule;

  if (analogChart) {
    analogChart.destroy();
  }

  const channels = enabledAnalogChannels.value;
  if (channels.length === 0) {
    return;
  }

  const { sampledData } = buildPointData(channels, cachedTimeAxis);

  // Build datasets with {x,y} points
  const datasets = channels.map((channel, idx) => ({
    label: channel.label,
    data: sampledData[idx],
    borderColor: channel.color,
    backgroundColor: channel.color,
    borderWidth: 1.5,
    pointRadius: 0,
    pointHitRadius: 0,
    tension: 0,
    yAxisID: channel.yAxisId,
    normalized: true,
  }));

  // Build Y-axes
  const yAxes: Record<string, ScaleOptions<'linear'>> = {};
  const axisIds = new Set(channels.map((c) => c.yAxisId));

  for (const axisId of axisIds) {
    const axisChannels = channels.filter((c) => c.yAxisId === axisId);
    const firstChannel = axisChannels[0];

    yAxes[axisId] = {
      type: 'linear',
      display: true,
      position: 'left',
      title: {
        display: true,
        text: firstChannel.unit,
        font: { size: 11 },
      },
      grid: {
        drawOnChartArea: axisId === channels[0].yAxisId,
      },
    } as ScaleOptions<'linear'>;
  }

  const config: ChartConfiguration<'line'> = {
    type: 'line',
    data: { datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      normalized: true,
      parsing: false,
      layout: {
        padding: {
          left: analogExtraPadding,
        },
      },
      interaction: {
        mode: 'nearest',
        axis: 'x',
        intersect: false,
      },
      plugins: {
        legend: {
          display: true,
          position: 'top',
          labels: {
            boxWidth: 12,
            font: { size: 11 },
          },
        },
        tooltip: {
          enabled: true,
          mode: 'nearest',
          axis: 'x',
          intersect: false,
          callbacks: {
            title: (tooltipItems) => {
              const time = tooltipItems[0].parsed.x;
              return `Time: ${time.toFixed(2)}s`;
            },
            label: (tooltipItem) => {
              const channel = channels[tooltipItem.datasetIndex];
              const value = tooltipItem.parsed.y.toFixed(2);
              return `${channel.label}: ${value} ${channel.unit}`;
            },
          },
        },
      },
      scales: {
        x: getXAxisConfig(false),
        ...yAxes,
      },
    },
  };

  analogChart = new Chart(analogCanvas.value, config);

  // Expose chart area left for alignment testing/synchronization
  const wrapper = analogCanvas.value.closest('.chart-analog');
  if (wrapper && analogChart.chartArea) {
    wrapper.setAttribute('data-chart-area-left', String(Math.round(analogChart.chartArea.left)));
  }
}

// Render boolean chart
function renderBooleanChart() {
  if (!booleanCanvas.value || !ChartModule || !hasData.value) {
    if (booleanChart) {
      booleanChart.destroy();
      booleanChart = null;
    }
    return;
  }

  const { Chart } = ChartModule;

  if (booleanChart) {
    booleanChart.destroy();
  }

  const channels = enabledBooleanChannels.value;
  if (channels.length === 0) {
    return;
  }

  const { sampledData } = buildPointData(channels, cachedTimeAxis);

  const datasets = channels.map((channel, idx) => ({
    label: channel.label,
    data: sampledData[idx],
    borderColor: channel.color,
    backgroundColor: channel.color + '33',
    borderWidth: 1.5,
    pointRadius: 0,
    pointHitRadius: 0,
    stepped: 'before' as const,
    fill: true,
    yAxisID: 'bool',
    normalized: true,
  }));

  const config: ChartConfiguration<'line'> = {
    type: 'line',
    data: { datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      normalized: true,
      parsing: false,
      layout: {
        padding: {
          left: booleanExtraPadding,
        },
      },
      interaction: {
        mode: 'nearest',
        axis: 'x',
        intersect: false,
      },
      plugins: {
        legend: {
          display: true,
          position: 'top',
          labels: {
            boxWidth: 12,
            font: { size: 11 },
          },
        },
        tooltip: {
          enabled: true,
          mode: 'nearest',
          axis: 'x',
          intersect: false,
          callbacks: {
            title: (tooltipItems) => {
              const time = tooltipItems[0].parsed.x;
              return `Time: ${time.toFixed(2)}s`;
            },
            label: (tooltipItem) => {
              const channel = channels[tooltipItem.datasetIndex];
              const value = tooltipItem.parsed.y;
              const status = value > 0 ? 'ON' : 'OFF';
              return `${channel.label}: ${status}`;
            },
          },
        },
      },
      scales: {
        x: getXAxisConfig(true),
        bool: {
          type: 'linear',
          min: -0.1,
          max: 1.1,
          ticks: {
            stepSize: 1,
            callback: (value) => {
              if (value === 0) return 'OFF';
              if (value === 1) return 'ON';
              return '';
            },
          },
          title: {
            display: false,
          },
        },
      },
    },
  };

  booleanChart = new Chart(booleanCanvas.value, config);

  // Expose chart area left for alignment testing/synchronization
  const wrapper = booleanCanvas.value.closest('.chart-boolean');
  if (wrapper && booleanChart.chartArea) {
    wrapper.setAttribute('data-chart-area-left', String(Math.round(booleanChart.chartArea.left)));
  }
}
</script>

<template>
  <div class="telemetry-chart-container">
    <div class="chart-header">
      <h2>Telemetry Charts</h2>
    </div>

    <ChannelSelector v-model="enabledChannelIds" />

    <div v-if="!hasData" class="no-data" role="img" aria-label="No telemetry data available">
      <svg
        class="no-data-icon"
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        aria-hidden="true"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z"
        />
      </svg>
      <p>No telemetry data available</p>
    </div>

    <div v-else-if="enabledChannelIds.length === 0" class="no-channels">
      <p>No channels selected. Please select at least one channel above.</p>
    </div>

    <template v-else>
      <div
        v-if="hasAnalogChannels"
        class="chart-wrapper chart-analog"
        role="img"
        :aria-label="analogChartSummary"
      >
        <span class="sr-only">{{ analogChartSummary }}</span>
        <canvas ref="analogCanvas"></canvas>
      </div>

      <div
        v-if="hasBooleanChannels"
        class="chart-wrapper chart-boolean"
        role="img"
        :aria-label="booleanChartSummary"
      >
        <span class="sr-only">{{ booleanChartSummary }}</span>
        <canvas ref="booleanCanvas"></canvas>
      </div>
    </template>
  </div>
</template>

<style scoped>
.telemetry-chart-container {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.chart-header h2 {
  margin: 0;
  font-size: 1.25rem;
}

.no-data,
.no-channels {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem 2rem;
  color: var(--color-text-secondary);
  text-align: center;
}

.no-data-icon {
  width: 3rem;
  height: 3rem;
  margin-bottom: 1rem;
  opacity: 0.5;
}

.chart-wrapper {
  width: 100%;
  padding: 1rem;
  background: var(--color-bg-tertiary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
}

.chart-wrapper canvas {
  max-height: 100%;
}

.chart-analog {
  height: 500px;
}

.chart-boolean {
  height: 150px;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border-width: 0;
}

/* Mobile: < 640px */
@media (max-width: 639px) {
  .chart-header h2 {
    font-size: 1.125rem;
  }

  .chart-analog {
    height: 300px;
    padding: 0.75rem;
  }

  .chart-boolean {
    height: 120px;
    padding: 0.75rem;
  }

  .no-data,
  .no-channels {
    padding: 2rem 1rem;
  }

  .no-data-icon {
    width: 2.5rem;
    height: 2.5rem;
  }

  .no-data p,
  .no-channels p {
    font-size: 0.9rem;
  }
}

/* Tablet: 640px - 1023px */
@media (min-width: 640px) and (max-width: 1023px) {
  .chart-analog {
    height: 400px;
  }

  .chart-boolean {
    height: 140px;
  }
}

/* Desktop: >= 1024px */
@media (min-width: 1024px) {
  .chart-analog {
    height: 500px;
  }

  .chart-boolean {
    height: 150px;
  }
}
</style>
