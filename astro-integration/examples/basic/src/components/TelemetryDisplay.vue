<script setup lang="ts">
import { computed } from 'vue';
import { Calibration } from '@ctrk-exporter/astro-integration';
import { useTelemetryData } from '@ctrk-exporter/astro-integration/composables';
import type { TelemetryRecord } from '@ctrk-exporter/astro-integration';

const { records, selectedLap, laps, filteredRecords, statistics, hasData, selectLap, metadata } =
  useTelemetryData();

// Sample record for display (first record of filtered data)
const sampleRecord = computed<TelemetryRecord | null>(() => {
  return filteredRecords.value.length > 0 ? filteredRecords.value[0] : null;
});

// Calibrated values for sample record
const calibratedSample = computed(() => {
  if (!sampleRecord.value) return null;

  const r = sampleRecord.value;
  return {
    rpm: Calibration.rpm(r.rpm).toFixed(0),
    throttle: Calibration.throttle(r.aps).toFixed(1),
    frontSpeed: Calibration.wheelSpeedKmh(r.front_speed).toFixed(1),
    rearSpeed: Calibration.wheelSpeedKmh(r.rear_speed).toFixed(1),
    lean: Calibration.lean(r.lean).toFixed(1),
    leanSigned: Calibration.lean(r.lean_signed).toFixed(1),
    pitch: Calibration.pitch(r.pitch).toFixed(1),
    frontBrake: Calibration.brake(r.front_brake).toFixed(1),
    rearBrake: Calibration.brake(r.rear_brake).toFixed(1),
    waterTemp: Calibration.temperature(r.water_temp).toFixed(1),
    intakeTemp: Calibration.temperature(r.intake_temp).toFixed(1),
    fuel: Calibration.fuel(r.fuel).toFixed(1),
    accX: Calibration.acceleration(r.acc_x).toFixed(2),
    accY: Calibration.acceleration(r.acc_y).toFixed(2),
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
</script>

<template>
  <div v-if="hasData" class="telemetry-display">
    <!-- Metadata -->
    <div class="card">
      <h2>File Information</h2>
      <table>
        <tbody>
          <tr>
            <th>File Name</th>
            <td><code>{{ metadata?.fileName }}</code></td>
          </tr>
          <tr>
            <th>File Size</th>
            <td>{{ ((metadata?.fileSize || 0) / 1024).toFixed(2) }} KB</td>
          </tr>
          <tr>
            <th>Parse Time</th>
            <td>{{ (metadata?.parseTime || 0).toFixed(2) }}ms</td>
          </tr>
          <tr>
            <th>Total Records</th>
            <td>{{ records.length }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Lap Selector -->
    <div class="card">
      <h2>Lap Selection</h2>
      <div class="lap-selector">
        <label for="lap-select">Select Lap:</label>
        <select id="lap-select" @change="handleLapChange">
          <option value="all">All Laps ({{ laps.length }} total)</option>
          <option v-for="lap in laps" :key="lap" :value="lap">
            Lap {{ lap }}
          </option>
        </select>
      </div>

      <div v-if="statistics" class="statistics">
        <table>
          <tbody>
            <tr>
              <th>Records</th>
              <td>{{ statistics.recordCount }}</td>
            </tr>
            <tr>
              <th>Duration</th>
              <td>{{ formatDuration(statistics.duration) }}</td>
            </tr>
            <tr>
              <th>Start Time</th>
              <td>{{ (statistics.startTime / 1000).toFixed(1) }}s</td>
            </tr>
            <tr>
              <th>End Time</th>
              <td>{{ (statistics.endTime / 1000).toFixed(1) }}s</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Sample Data Display -->
    <div v-if="sampleRecord && calibratedSample" class="card">
      <h2>Sample Data (First Record)</h2>
      <p class="hint">Showing calibrated values from the first record of the selected data.</p>

      <table>
        <thead>
          <tr>
            <th>Channel</th>
            <th>Value</th>
            <th>Unit</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>Lap</td>
            <td>{{ sampleRecord.lap }}</td>
            <td>-</td>
          </tr>
          <tr>
            <td>Time</td>
            <td>{{ (sampleRecord.time_ms / 1000).toFixed(3) }}</td>
            <td>s</td>
          </tr>
          <tr>
            <td>RPM</td>
            <td>{{ calibratedSample.rpm }}</td>
            <td>RPM</td>
          </tr>
          <tr>
            <td>Gear</td>
            <td>{{ sampleRecord.gear }}</td>
            <td>-</td>
          </tr>
          <tr>
            <td>Throttle (APS)</td>
            <td>{{ calibratedSample.throttle }}</td>
            <td>%</td>
          </tr>
          <tr>
            <td>Front Speed</td>
            <td>{{ calibratedSample.frontSpeed }}</td>
            <td>km/h</td>
          </tr>
          <tr>
            <td>Rear Speed</td>
            <td>{{ calibratedSample.rearSpeed }}</td>
            <td>km/h</td>
          </tr>
          <tr>
            <td>Lean Angle</td>
            <td>{{ calibratedSample.lean }}</td>
            <td>°</td>
          </tr>
          <tr>
            <td>Lean Angle (Signed)</td>
            <td>{{ calibratedSample.leanSigned }}</td>
            <td>°</td>
          </tr>
          <tr>
            <td>Pitch Rate</td>
            <td>{{ calibratedSample.pitch }}</td>
            <td>°/s</td>
          </tr>
          <tr>
            <td>Front Brake</td>
            <td>{{ calibratedSample.frontBrake }}</td>
            <td>bar</td>
          </tr>
          <tr>
            <td>Rear Brake</td>
            <td>{{ calibratedSample.rearBrake }}</td>
            <td>bar</td>
          </tr>
          <tr>
            <td>Water Temp</td>
            <td>{{ calibratedSample.waterTemp }}</td>
            <td>°C</td>
          </tr>
          <tr>
            <td>Intake Temp</td>
            <td>{{ calibratedSample.intakeTemp }}</td>
            <td>°C</td>
          </tr>
          <tr>
            <td>Fuel</td>
            <td>{{ calibratedSample.fuel }}</td>
            <td>cc</td>
          </tr>
          <tr>
            <td>Acceleration X</td>
            <td>{{ calibratedSample.accX }}</td>
            <td>G</td>
          </tr>
          <tr>
            <td>Acceleration Y</td>
            <td>{{ calibratedSample.accY }}</td>
            <td>G</td>
          </tr>
          <tr>
            <td>GPS</td>
            <td>{{ sampleRecord.latitude.toFixed(6) }}, {{ sampleRecord.longitude.toFixed(6) }}</td>
            <td>lat/lng</td>
          </tr>
          <tr>
            <td>GPS Speed</td>
            <td>{{ sampleRecord.gps_speed_knots.toFixed(1) }}</td>
            <td>knots</td>
          </tr>
          <tr>
            <td>Front ABS</td>
            <td>{{ sampleRecord.f_abs ? 'Active' : 'Inactive' }}</td>
            <td>-</td>
          </tr>
          <tr>
            <td>Rear ABS</td>
            <td>{{ sampleRecord.r_abs ? 'Active' : 'Inactive' }}</td>
            <td>-</td>
          </tr>
          <tr>
            <td>TCS</td>
            <td>{{ sampleRecord.tcs }}</td>
            <td>-</td>
          </tr>
          <tr>
            <td>SCS</td>
            <td>{{ sampleRecord.scs }}</td>
            <td>-</td>
          </tr>
          <tr>
            <td>LIF</td>
            <td>{{ sampleRecord.lif }}</td>
            <td>-</td>
          </tr>
          <tr>
            <td>Launch</td>
            <td>{{ sampleRecord.launch }}</td>
            <td>-</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>

  <div v-else class="no-data card">
    <p>No telemetry data loaded. Upload a .CTRK file to get started.</p>
  </div>
</template>

<style scoped>
.telemetry-display {
  margin-top: 2rem;
}

.lap-selector {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1rem;
}

.lap-selector label {
  font-weight: 500;
}

.statistics {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid var(--color-border);
}

.hint {
  color: #999;
  font-size: 0.9rem;
  margin-bottom: 1rem;
  font-style: italic;
}

.no-data {
  text-align: center;
  padding: 3rem;
  color: #999;
}

table {
  margin-top: 0;
}
</style>
