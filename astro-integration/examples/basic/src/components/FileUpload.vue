<script setup lang="ts">
import { ref } from 'vue';
import {
  CTRKParser,
  fileToUint8Array,
  isCTRKFile,
  formatFileSize,
} from '@ctrk-exporter/astro-integration';
import { useTelemetryData, useParserStatus } from '@ctrk-exporter/astro-integration/composables';

const { loadRecords } = useTelemetryData();
const { status, error, startParsing, completeParsing, setError, reset } = useParserStatus();

const fileInput = ref<HTMLInputElement | null>(null);
const dragOver = ref(false);

async function handleFileSelect(event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  if (file) {
    await parseFile(file);
  }
}

function handleDragOver(event: DragEvent) {
  event.preventDefault();
  dragOver.value = true;
}

function handleDragLeave() {
  dragOver.value = false;
}

async function handleDrop(event: DragEvent) {
  event.preventDefault();
  dragOver.value = false;

  const file = event.dataTransfer?.files[0];
  if (file) {
    await parseFile(file);
  }
}

async function parseFile(file: File) {
  // Validate file extension
  if (!isCTRKFile(file.name)) {
    setError({
      message: 'Invalid file type. Please select a .CTRK file.',
      fileName: file.name,
    });
    return;
  }

  try {
    reset();
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
      parseTime,
    });

    completeParsing();

    console.log(`Parsed ${records.length} records in ${parseTime.toFixed(2)}ms`);
  } catch (err) {
    console.error('Parse error:', err);
    setError({
      message: err instanceof Error ? err.message : 'Unknown parsing error',
      fileName: file.name,
      originalError: err instanceof Error ? err : undefined,
    });
  }
}

function clearFile() {
  if (fileInput.value) {
    fileInput.value.value = '';
  }
  reset();
}
</script>

<template>
  <div class="file-upload card">
    <h2>Upload CTRK File</h2>

    <div
      class="drop-zone"
      :class="{ 'drag-over': dragOver, 'has-file': status === 'success' }"
      @dragover="handleDragOver"
      @dragleave="handleDragLeave"
      @drop="handleDrop"
    >
      <input
        ref="fileInput"
        type="file"
        accept=".CTRK"
        @change="handleFileSelect"
        class="file-input"
      />

      <div class="drop-zone-content">
        <p v-if="status === 'idle'">
          Drag and drop a .CTRK file here, or click to browse
        </p>
        <p v-else-if="status === 'parsing'" class="parsing">
          Parsing...
        </p>
        <p v-else-if="status === 'success'" class="success">
          ✓ File parsed successfully
        </p>
        <p v-else-if="status === 'error'" class="error-status">
          ✗ Parse failed
        </p>
      </div>
    </div>

    <div v-if="error" class="error">
      <strong>Error:</strong> {{ error.message }}
      <div v-if="error.fileName" class="error-detail">
        File: <code>{{ error.fileName }}</code>
      </div>
    </div>

    <button v-if="status === 'success' || status === 'error'" @click="clearFile">
      Clear and Upload Another
    </button>
  </div>
</template>

<style scoped>
.file-upload {
  margin-bottom: 2rem;
}

.drop-zone {
  border: 2px dashed var(--color-border);
  border-radius: 8px;
  padding: 3rem 2rem;
  text-align: center;
  transition: all 0.3s ease;
  position: relative;
  cursor: pointer;
}

.drop-zone:hover {
  border-color: var(--color-accent);
  background: rgba(0, 102, 204, 0.05);
}

.drop-zone.drag-over {
  border-color: var(--color-accent);
  background: rgba(0, 102, 204, 0.1);
}

.drop-zone.has-file {
  border-color: var(--color-success);
  background: rgba(0, 170, 0, 0.05);
}

.file-input {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  opacity: 0;
  cursor: pointer;
}

.drop-zone-content {
  pointer-events: none;
}

.parsing {
  color: var(--color-accent);
  font-weight: 500;
}

.success {
  color: var(--color-success);
  font-weight: 500;
}

.error-status {
  color: var(--color-error);
  font-weight: 500;
}

.error {
  margin-top: 1rem;
}

.error-detail {
  margin-top: 0.5rem;
  font-size: 0.9rem;
}

button {
  margin-top: 1rem;
}
</style>
