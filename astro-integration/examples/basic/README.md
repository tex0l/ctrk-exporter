# CTRK Parser - Basic Example

This is a basic example demonstrating the `@ctrk-exporter/astro-integration` package with Astro and Vue.js.

## Features

- File upload with drag-and-drop support
- Client-side CTRK parsing (no server required)
- Reactive telemetry data display
- Lap selection and filtering
- Calibrated value display
- Error handling

## Setup

```bash
npm install
```

## Development

```bash
npm run dev
```

Open [http://localhost:4321](http://localhost:4321) in your browser.

## Build

```bash
npm run build
```

Static site generated to `dist/`.

## Project Structure

```
src/
├── layouts/
│   └── BaseLayout.astro      # Base HTML layout
├── pages/
│   └── index.astro           # Main page
└── components/
    ├── FileUpload.vue        # File upload component
    └── TelemetryDisplay.vue  # Data display component
```

## Key Concepts

### Client-Side Only Components

Components that use browser APIs (FileReader, parser) must use `client:only="vue"`:

```astro
<FileUpload client:only="vue" />
```

### Vue Composables

State management uses Vue composables:

```vue
<script setup>
import { useTelemetryData, useParserStatus } from '@ctrk-exporter/astro-integration/composables';

const { records, laps, selectLap } = useTelemetryData();
const { status, error } = useParserStatus();
</script>
```

### Calibration

Raw values must be calibrated before display:

```typescript
import { Calibration } from '@ctrk-exporter/astro-integration';

const rpmValue = Calibration.rpm(record.rpm);
const speedKmh = Calibration.front_speed(record.front_speed);
```

## License

MIT
