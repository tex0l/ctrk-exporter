# @ctrk-exporter/astro-integration

Astro integration for Yamaha Y-Trac CTRK telemetry parser with Vue.js components and composables.

## Features

- **100% Client-Side Parsing** - No server-side processing required
- **Vue.js Composables** - Reactive state management for telemetry data
- **Type-Safe** - Full TypeScript support with strict typing
- **Zero Runtime Dependencies** - Parser has no external dependencies
- **Platform-Agnostic** - Works in any browser environment
- **Permissive License** - MIT licensed (compatible with all dependencies)

## Installation

```bash
npm install @ctrk-exporter/astro-integration
```

### Peer Dependencies

This package requires the following peer dependencies:

```bash
npm install astro @astrojs/vue vue
```

All dependencies use permissive licenses (MIT/BSD/Apache 2.0).

## Quick Start

### 1. Configure Astro

```js
// astro.config.mjs
import { defineConfig } from 'astro/config';
import vue from '@astrojs/vue';
import ctrk from '@ctrk-exporter/astro-integration';

export default defineConfig({
  output: 'static',
  integrations: [
    vue(),
    ctrk()
  ]
});
```

### 2. Create a Parser Component

```vue
<!-- src/components/CTRKParser.vue -->
<script setup lang="ts">
import { ref } from 'vue';
import { CTRKParser, fileToUint8Array } from '@ctrk-exporter/astro-integration';
import { useTelemetryData, useParserStatus } from '@ctrk-exporter/astro-integration/composables';

const { loadRecords } = useTelemetryData();
const { startParsing, completeParsing, setError } = useParserStatus();
const fileInput = ref<HTMLInputElement | null>(null);

async function handleFileSelect(event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) return;

  try {
    startParsing();
    const startTime = performance.now();

    // Convert file to Uint8Array
    const data = await fileToUint8Array(file);

    // Parse CTRK file
    const parser = new CTRKParser(data);
    const records = parser.parse();

    const parseTime = performance.now() - startTime;

    // Load into state
    loadRecords({
      records,
      fileName: file.name,
      fileSize: file.size,
      parseTime
    });

    completeParsing();
  } catch (err) {
    setError({
      message: err instanceof Error ? err.message : 'Unknown error',
      fileName: file.name,
      originalError: err instanceof Error ? err : undefined
    });
  }
}
</script>

<template>
  <div class="ctrk-parser">
    <label for="file-input">Select CTRK File:</label>
    <input
      id="file-input"
      ref="fileInput"
      type="file"
      accept=".CTRK"
      @change="handleFileSelect"
    />
  </div>
</template>
```

### 3. Use in Astro Page

```astro
---
// src/pages/index.astro
import BaseLayout from '../layouts/BaseLayout.astro';
import CTRKParser from '../components/CTRKParser.vue';
import TelemetryDisplay from '../components/TelemetryDisplay.vue';
---

<BaseLayout title="CTRK Parser">
  <h1>CTRK Telemetry Parser</h1>

  <!-- Must use client:only="vue" for browser APIs -->
  <CTRKParser client:only="vue" />
  <TelemetryDisplay client:only="vue" />
</BaseLayout>
```

## API Reference

### Parser

Re-exported from `@ctrk/parser`:

```typescript
import { CTRKParser, Calibration } from '@ctrk-exporter/astro-integration';

// Parse CTRK file
const parser = new CTRKParser(data);
const records = parser.parse();

// Apply calibration
const rpm = Calibration.rpm(records[0].rpm);
const speed = Calibration.wheelSpeedKmh(records[0].front_speed);
```

See [@ctrk/parser documentation](../parser/README.md) for full parser API.

### Utilities

#### `fileToUint8Array(file: File): Promise<Uint8Array>`

Converts a File object to Uint8Array for parsing.

```typescript
const data = await fileToUint8Array(file);
const parser = new CTRKParser(data);
```

#### `isCTRKFile(fileName: string): boolean`

Validates file extension (case-insensitive).

```typescript
if (isCTRKFile(file.name)) {
  // Process file
}
```

#### `formatFileSize(bytes: number): string`

Formats file size in human-readable format.

```typescript
formatFileSize(1024);      // "1.0 KB"
formatFileSize(1048576);   // "1.0 MB"
```

#### `formatParseTime(milliseconds: number): string`

Formats parse time.

```typescript
formatParseTime(342);   // "342ms"
formatParseTime(1234);  // "1.23s"
```

### Composables

#### `useTelemetryData()`

Manages telemetry data state with lap filtering.

```typescript
const {
  records,           // readonly Ref<TelemetryRecord[]>
  selectedLap,       // readonly Ref<number | null>
  metadata,          // readonly Ref<ParserResult | null>
  laps,              // ComputedRef<number[]>
  filteredRecords,   // ComputedRef<TelemetryRecord[]>
  statistics,        // ComputedRef<Stats | null>
  hasData,           // ComputedRef<boolean>
  loadRecords,       // (result: ParserResult) => void
  selectLap,         // (lap: number | null) => void
  clear              // () => void
} = useTelemetryData();
```

**Example:**

```vue
<script setup>
import { useTelemetryData } from '@ctrk-exporter/astro-integration/composables';

const { laps, selectedLap, selectLap, filteredRecords } = useTelemetryData();
</script>

<template>
  <select @change="selectLap($event.target.value)">
    <option :value="null">All Laps</option>
    <option v-for="lap in laps" :key="lap" :value="lap">
      Lap {{ lap }}
    </option>
  </select>

  <p>{{ filteredRecords.length }} records</p>
</template>
```

#### `useParserStatus()`

Manages parser status and error state.

```typescript
const {
  status,           // readonly Ref<ParserStatus>
  error,            // readonly Ref<ParserError | null>
  progress,         // readonly Ref<number>
  isLoading,        // ComputedRef<boolean>
  hasError,         // ComputedRef<boolean>
  isSuccess,        // ComputedRef<boolean>
  startParsing,     // () => void
  completeParsing,  // () => void
  setError,         // (err: ParserError) => void
  updateProgress,   // (percent: number) => void
  reset             // () => void
} = useParserStatus();
```

**Example:**

```vue
<script setup>
import { useParserStatus } from '@ctrk-exporter/astro-integration/composables';

const { status, error, isLoading } = useParserStatus();
</script>

<template>
  <div v-if="isLoading">Parsing...</div>
  <div v-if="status === 'error'" class="error">
    {{ error?.message }}
  </div>
</template>
```

## Types

```typescript
import type {
  TelemetryRecord,
  FinishLine,
  ParserStatus,
  ParserResult,
  ParserError
} from '@ctrk-exporter/astro-integration';
```

### `TelemetryRecord`

Single telemetry sample with all channels (raw values).

```typescript
interface TelemetryRecord {
  lap: number;
  time_ms: number;
  latitude: number;
  longitude: number;
  gps_speed_knots: number;
  rpm: number;           // raw (calibrate with Calibration.rpm())
  gear: number;          // 0-6
  aps: number;           // raw throttle grip
  tps: number;           // raw throttle position
  water_temp: number;    // raw
  intake_temp: number;   // raw
  front_speed: number;   // raw
  rear_speed: number;    // raw
  fuel: number;          // raw cumulative
  lean: number;          // raw
  lean_signed: number;   // raw signed angle
  pitch: number;         // raw
  acc_x: number;         // raw
  acc_y: number;         // raw
  front_brake: number;   // raw
  rear_brake: number;    // raw
  f_abs: boolean;
  r_abs: boolean;
  tcs: number;
  scs: number;
  lif: number;
  launch: number;
}
```

### `ParserStatus`

```typescript
type ParserStatus = 'idle' | 'parsing' | 'success' | 'error';
```

### `ParserResult`

```typescript
interface ParserResult {
  records: TelemetryRecord[];
  fileName: string;
  fileSize: number;
  parseTime: number;  // milliseconds
}
```

### `ParserError`

```typescript
interface ParserError {
  message: string;
  fileName?: string;
  originalError?: Error;
}
```

## Best Practices

### 1. Always Use `client:only="vue"`

Parser components must run client-side only:

```astro
<CTRKParser client:only="vue" />
```

### 2. Web Worker for Large Files

For better performance with large files, run the parser in a Web Worker:

```typescript
// worker.ts
import { CTRKParser } from '@ctrk-exporter/astro-integration';

self.onmessage = (e: MessageEvent<Uint8Array>) => {
  const parser = new CTRKParser(e.data);
  const records = parser.parse();
  self.postMessage(records);
};

// component
const worker = new Worker(new URL('./worker.ts', import.meta.url), {
  type: 'module'
});

worker.onmessage = (e) => {
  loadRecords({ records: e.data, ... });
};

worker.postMessage(data);
```

### 3. Calibration

Always calibrate raw values before display:

```typescript
import { Calibration } from '@ctrk-exporter/astro-integration';

const rpmValue = Calibration.rpm(record.rpm);
const speedKmh = Calibration.wheelSpeedKmh(record.front_speed);
const throttlePercent = Calibration.throttle(record.aps);
```

### 4. GPS Validation

Check for GPS fix before using coordinates:

```typescript
const hasGpsFix = record.latitude !== 9999.0 && record.longitude !== 9999.0;
```

## Example Project

See `examples/basic/` for a complete working example with:

- File upload component
- Telemetry data display
- Lap selector
- Error handling
- Progress tracking

## License

MIT

## Dependencies License Compliance

All dependencies use permissive licenses:

- **@ctrk/parser**: MIT
- **@astrojs/vue**: MIT
- **astro**: MIT
- **vue**: MIT

No GPL or proprietary licenses in dependency tree.
