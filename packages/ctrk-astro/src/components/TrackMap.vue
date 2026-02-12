<script setup lang="ts">
import { ref, computed, onMounted, watch, onUnmounted } from 'vue';
import { useTelemetryData } from '@tex0l/ctrk-astro/composables';
import {
  extractGpsCoordinates,
  groupByLap,
  simplifyTrack,
  calculateBounds,
  detectLapCrossings,
} from '@tex0l/ctrk-astro/lib/gps-utils';
import { getLapColor } from '@tex0l/ctrk-astro/lib/chart-config';
import type { Map as LeafletMap, TileLayer, Polyline, Marker, LatLngBoundsExpression } from 'leaflet';

const { records, selectedLap, selectLap } = useTelemetryData();

const mapContainer = ref<HTMLDivElement | null>(null);
let map: LeafletMap | null = null;
let tileLayer: TileLayer | null = null;
const polylines = ref<Map<number, Polyline>>(new Map());
const markers = ref<Marker[]>([]);

// Leaflet module (loaded dynamically)
let L: typeof import('leaflet') | null = null;

const gpsCoords = computed(() => extractGpsCoordinates(records.value));
const lapGroups = computed(() => groupByLap(gpsCoords.value));
const hasGpsData = computed(() => gpsCoords.value.length > 0);
const trackSummary = computed(() => {
  const laps = lapGroups.value.size;
  const points = gpsCoords.value.length;
  return `GPS track map showing ${laps} lap${laps !== 1 ? 's' : ''} with ${points} data points`;
});

// Initialize map
onMounted(async () => {
  if (!mapContainer.value) return;

  try {
    // Import Leaflet dynamically (client-side only)
    L = await import('leaflet');
    await import('leaflet/dist/leaflet.css');

    // Create map
    map = L.map(mapContainer.value, {
      center: [0, 0],
      zoom: 13,
      zoomControl: true,
    });

    // Add OpenStreetMap tiles
    tileLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      maxZoom: 19,
    }).addTo(map);

    // Initial render
    renderTracks();
  } catch (err) {
    console.error('Failed to initialize map:', err);
  }
});

// Cleanup on unmount
onUnmounted(() => {
  if (map) {
    map.remove();
    map = null;
  }
});

// Watch for data changes
watch([gpsCoords, selectedLap], () => {
  renderTracks();
});

// Render GPS tracks
function renderTracks() {
  if (!map || !L || !hasGpsData.value) return;

  // Clear existing polylines and markers
  polylines.value.forEach((polyline) => polyline.remove());
  polylines.value.clear();
  markers.value.forEach((marker) => marker.remove());
  markers.value = [];

  // Render each lap
  for (const [lap, coords] of lapGroups.value.entries()) {
    if (coords.length < 2) continue;

    // Simplify track if too many points
    const simplified = simplifyTrack(coords, 10000);

    // Convert to Leaflet LatLng array
    const latLngs = simplified.map((c) => L!.latLng(c.lat, c.lng));

    // Determine opacity based on selection
    const opacity = selectedLap.value === null || selectedLap.value === lap ? 0.8 : 0.3;
    const weight = selectedLap.value === lap ? 4 : 2;

    // Create polyline
    const polyline = L.polyline(latLngs, {
      color: getLapColor(lap),
      weight,
      opacity,
    }).addTo(map);

    // Add click handler to select lap
    polyline.on('click', () => {
      selectLap(lap);
    });

    polylines.value.set(lap, polyline);

    // Add marker at finish line crossing (first point of each lap)
    if (lap > 0) {
      const firstPoint = coords[0];
      const marker = L.marker([firstPoint.lat, firstPoint.lng], {
        icon: L.divIcon({
          className: 'lap-marker',
          html: `<div class="lap-marker-content">${lap}</div>`,
          iconSize: [24, 24],
          iconAnchor: [12, 12],
        }),
      }).addTo(map);

      marker.on('click', () => {
        selectLap(lap);
      });

      markers.value.push(marker);
    }
  }

  // Fit map to bounds
  fitToBounds();
}

// Fit map to track bounds
function fitToBounds() {
  if (!map || !L || !hasGpsData.value) return;

  const coords = selectedLap.value !== null
    ? (lapGroups.value.get(selectedLap.value) || [])
    : gpsCoords.value;

  if (coords.length === 0) return;

  const bounds = calculateBounds(coords);
  if (bounds) {
    const [minLat, minLng, maxLat, maxLng] = bounds;
    map.fitBounds(
      [
        [minLat, minLng],
        [maxLat, maxLng],
      ] as LatLngBoundsExpression,
      { padding: [50, 50] }
    );
  }
}
</script>

<template>
  <div class="track-map-container">
    <div class="map-header">
      <h2>GPS Track Map</h2>
      <button v-if="hasGpsData" @click="fitToBounds" class="fit-button" title="Fit to track">
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
            d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4"
          />
        </svg>
      </button>
    </div>

    <div v-if="!hasGpsData" class="no-gps" role="img" aria-label="No GPS data available">
      <svg
        class="no-gps-icon"
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
          d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"
        />
      </svg>
      <p>No GPS data available</p>
    </div>

    <div v-else ref="mapContainer" class="map" role="img" :aria-label="trackSummary">
      <span class="sr-only">{{ trackSummary }}</span>
    </div>
  </div>
</template>

<style scoped>
.track-map-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 400px;
}

.map-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.map-header h2 {
  margin: 0;
  font-size: 1.25rem;
}

.fit-button {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2.5rem;
  height: 2.5rem;
  padding: 0;
  background: var(--color-accent);
  color: white;
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: background var(--transition-fast);
}

.fit-button:hover {
  background: var(--color-accent-hover, #005fa3);
}

.fit-button .icon {
  width: 1.25rem;
  height: 1.25rem;
}

.no-gps {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 400px;
  color: var(--color-text-secondary);
  text-align: center;
}

.no-gps-icon {
  width: 3rem;
  height: 3rem;
  margin-bottom: 1rem;
  opacity: 0.5;
}

.map {
  flex: 1;
  min-height: 400px;
  border-radius: var(--radius-sm);
  overflow: hidden;
  border: 1px solid var(--color-border);
  z-index: 1;
  touch-action: manipulation;
}

/* Mobile: < 640px */
@media (max-width: 639px) {
  .track-map-container {
    min-height: 250px;
  }

  .map-header h2 {
    font-size: 1.125rem;
  }

  .fit-button {
    width: 2.75rem;
    height: 2.75rem;
    min-width: 44px;
    min-height: 44px;
  }

  .fit-button .icon {
    width: 1.125rem;
    height: 1.125rem;
  }

  .map {
    min-height: 250px;
  }

  .no-gps {
    height: 250px;
  }
}

/* Tablet: 640px - 1023px */
@media (min-width: 640px) and (max-width: 1023px) {
  .track-map-container {
    min-height: 350px;
  }

  .map {
    min-height: 350px;
  }

  .no-gps {
    height: 350px;
  }
}

/* Desktop: >= 1024px */
@media (min-width: 1024px) {
  .track-map-container {
    min-height: 450px;
  }

  .map {
    min-height: 450px;
  }

  .no-gps {
    height: 450px;
  }
}
</style>

<style>
/* Global styles for Leaflet markers (not scoped) */
.lap-marker {
  background: transparent !important;
  border: none !important;
}

.lap-marker-content {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  background: white;
  border: 2px solid #333;
  border-radius: 50%;
  font-size: 0.75rem;
  font-weight: 600;
  color: #333;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
}
</style>
