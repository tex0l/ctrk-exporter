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
  <div class="flex flex-col h-full min-h-[400px] max-sm:min-h-[250px] sm:min-h-[350px] lg:min-h-[450px]">
    <div class="flex justify-between items-center mb-4">
      <h2 class="m-0 text-xl max-sm:text-lg">GPS Track Map</h2>
      <button
        v-if="hasGpsData"
        @click="fitToBounds"
        class="flex items-center justify-center w-10 h-10 max-sm:w-11 max-sm:h-11 max-sm:min-w-[44px] max-sm:min-h-[44px] p-0 bg-(--color-accent) text-white border-none rounded-sm cursor-pointer transition-colors duration-150 hover:bg-(--color-accent-hover)"
        title="Fit to track"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          class="w-5 h-5 max-sm:w-[1.125rem] max-sm:h-[1.125rem]"
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

    <div v-if="!hasGpsData" class="flex flex-col items-center justify-center h-[400px] max-sm:h-[250px] sm:h-[350px] lg:h-[450px] text-(--color-text-secondary) text-center" role="img" aria-label="No GPS data available">
      <svg
        class="w-12 h-12 mb-4 opacity-50"
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

    <div
      v-else
      ref="mapContainer"
      class="flex-1 min-h-[400px] max-sm:min-h-[250px] sm:min-h-[350px] lg:min-h-[450px] rounded-sm overflow-hidden border border-(--color-border) z-[1] touch-manipulation"
      role="img"
      :aria-label="trackSummary"
    >
      <span class="sr-only">{{ trackSummary }}</span>
    </div>
  </div>
</template>

<style>
/* Global styles for Leaflet markers (not scoped — Leaflet injects these dynamically) */
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

/* Ensure Leaflet map renders correctly */
.leaflet-container {
  z-index: 1;
  border-radius: 0.5rem;
}
</style>
