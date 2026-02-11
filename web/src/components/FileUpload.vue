<script setup lang="ts">
import { ref, computed } from 'vue';
import { fileToUint8Array, formatFileSize } from '@ctrk-exporter/astro-integration/utils';
import { useTelemetryData } from '@ctrk-exporter/astro-integration/composables';
import { useParserStatus } from '@ctrk-exporter/astro-integration/composables';
import { useToast } from '../lib/toast-store';
import { validateCTRKFile } from '../lib/file-validator';
import type { WorkerRequest, WorkerResponse } from '../workers/parser-worker';

const { loadRecords, hasData, clear: clearData } = useTelemetryData();
const { status, startParsing, completeParsing, setError, reset } = useParserStatus();
const { showSuccess, showError } = useToast();

const fileInput = ref<HTMLInputElement | null>(null);
const dragOver = ref(false);
const currentFile = ref<File | null>(null);
const worker = ref<Worker | null>(null);

const isUploading = computed(() => status.value === 'parsing');

// Initialize Web Worker
if (typeof Worker !== 'undefined') {
  worker.value = new Worker(new URL('../workers/parser-worker.ts', import.meta.url), {
    type: 'module',
  });

  worker.value.onmessage = (event: MessageEvent<WorkerResponse>) => {
    const response = event.data;

    if (response.type === 'success' && response.records && currentFile.value) {
      // Load records into state
      loadRecords({
        records: response.records,
        fileName: currentFile.value.name,
        fileSize: currentFile.value.size,
        parseTime: response.parseTime || 0,
      });

      completeParsing();

      showSuccess(
        `Successfully parsed ${response.records.length} records from ${currentFile.value.name}`
      );

      // Scroll to analysis section after a short delay
      setTimeout(() => {
        const analysisSection = document.getElementById('analysis-section');
        if (analysisSection) {
          analysisSection.scrollIntoView({ behavior: 'smooth' });
        }
      }, 500);
    } else if (response.type === 'error') {
      setError({
        message: response.error || 'Unknown parsing error',
        fileName: currentFile.value?.name,
      });

      showError(`Parse failed: ${response.error || 'Unknown error'}`);
    }
  };

  worker.value.onerror = (err) => {
    setError({
      message: `Worker error: ${err.message}`,
      fileName: currentFile.value?.name,
    });

    showError('Parsing worker crashed. Please try again.');
  };
}

function handleDragOver(event: DragEvent) {
  event.preventDefault();
  if (!isUploading.value) {
    dragOver.value = true;
  }
}

function handleDragLeave() {
  dragOver.value = false;
}

async function handleDrop(event: DragEvent) {
  event.preventDefault();
  dragOver.value = false;

  if (isUploading.value) return;

  const file = event.dataTransfer?.files[0];
  if (file) {
    await parseFile(file);
  }
}

async function handleFileSelect(event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  if (file && !isUploading.value) {
    await parseFile(file);
  }
}

async function parseFile(file: File) {
  // Validate file
  const validationError = await validateCTRKFile(file);
  if (validationError) {
    showError(validationError.message);
    setError({
      message: validationError.message,
      fileName: file.name,
    });
    return;
  }

  // Check if Web Worker is available
  if (!worker.value) {
    showError('Web Worker not supported in this browser');
    setError({
      message: 'Web Worker not supported',
      fileName: file.name,
    });
    return;
  }

  try {
    reset();
    startParsing();
    currentFile.value = file;

    // Convert file to Uint8Array
    const data = await fileToUint8Array(file);

    // Send to Web Worker for parsing
    const request: WorkerRequest = {
      type: 'parse',
      data,
    };

    // Use transferable for performance
    worker.value.postMessage(request, [data.buffer]);
  } catch (err) {
    console.error('Parse error:', err);
    setError({
      message: err instanceof Error ? err.message : 'Unknown error',
      fileName: file.name,
      originalError: err instanceof Error ? err : undefined,
    });

    showError(`Failed to read file: ${err instanceof Error ? err.message : 'Unknown error'}`);
  }
}

function clearFile() {
  if (fileInput.value) {
    fileInput.value.value = '';
  }
  currentFile.value = null;
  reset();
}

function triggerFileInput() {
  if (!isUploading.value && fileInput.value) {
    fileInput.value.click();
  }
}

function handleKeydown(event: KeyboardEvent) {
  if ((event.key === 'Enter' || event.key === ' ') && !isUploading.value) {
    event.preventDefault();
    triggerFileInput();
  }
}

function handleUploadAnother() {
  clearData();
  reset();
  if (fileInput.value) {
    fileInput.value.value = '';
  }
  currentFile.value = null;
}
</script>

<template>
  <!-- Compact "Upload another?" button when data is already loaded -->
  <div v-if="hasData" class="upload-another-bar">
    <button @click="handleUploadAnother" class="upload-another-button">
      <svg
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        class="upload-another-icon"
        aria-hidden="true"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
        />
      </svg>
      Upload another file
    </button>
    <input
      ref="fileInput"
      type="file"
      accept=".CTRK,.ctrk"
      @change="handleFileSelect"
      class="file-input"
      aria-label="Upload CTRK telemetry file"
    />
  </div>

  <!-- Full upload form when no data is loaded -->
  <div v-else class="file-upload card">
    <h2>Upload CTRK File</h2>
    <p class="upload-hint">
      Upload a .CTRK telemetry file from your Yamaha Y-Trac device to begin analysis.
    </p>

    <div
      class="drop-zone"
      :class="{
        'drag-over': dragOver,
        'is-uploading': isUploading,
        'has-error': status === 'error',
      }"
      role="region"
      aria-label="File upload drop zone"
      tabindex="0"
      @dragover="handleDragOver"
      @dragleave="handleDragLeave"
      @drop="handleDrop"
      @click="triggerFileInput"
      @keydown="handleKeydown"
    >
      <input
        ref="fileInput"
        type="file"
        accept=".CTRK,.ctrk"
        @change="handleFileSelect"
        class="file-input"
        :disabled="isUploading"
        aria-label="Upload CTRK telemetry file"
      />

      <div class="drop-zone-content">
        <div v-if="isUploading" class="upload-status" role="status" aria-live="polite">
          <div class="spinner large" aria-hidden="true"></div>
          <p class="status-text">Parsing file...</p>
          <p v-if="currentFile" class="file-info">
            {{ currentFile.name }} ({{ formatFileSize(currentFile.size) }})
          </p>
        </div>

        <div v-else-if="status === 'error'" class="upload-status error" role="alert" aria-live="assertive">
          <span class="status-icon" aria-hidden="true">✗</span>
          <p class="status-text">Upload failed</p>
          <button @click.stop="clearFile" class="retry-button">Try Again</button>
        </div>

        <div v-else class="upload-prompt">
          <svg
            class="upload-icon"
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
              d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
            />
          </svg>
          <p class="prompt-text">
            <strong>Drop your .CTRK file here</strong><br />
            or click to browse
          </p>
          <p class="prompt-detail">Maximum file size: 50 MB</p>
        </div>
      </div>
    </div>

    <div class="file-requirements">
      <h3>Requirements</h3>
      <ul>
        <li>File extension must be .CTRK</li>
        <li>Minimum file size: 100 bytes</li>
        <li>Maximum file size: 50 MB</li>
        <li>File must contain valid CTRK header ("HEAD")</li>
      </ul>
    </div>
  </div>
</template>

<style scoped>
.upload-another-bar {
  display: flex;
  justify-content: flex-end;
  position: relative;
  margin-bottom: 1rem;
}

.upload-another-button {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background: var(--color-bg-tertiary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  color: var(--color-text);
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.upload-another-button:hover {
  background: var(--color-accent);
  color: white;
  border-color: var(--color-accent);
}

.upload-another-button:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}

.upload-another-icon {
  width: 1rem;
  height: 1rem;
}

.file-upload {
  max-width: 800px;
  margin: 0 auto;
}

.upload-hint {
  color: var(--color-text-secondary);
  margin-bottom: 1.5rem;
  font-size: 0.95rem;
}

.drop-zone {
  border: 2px dashed var(--color-border);
  border-radius: var(--radius-md);
  padding: 3rem 2rem;
  text-align: center;
  transition: all var(--transition-normal);
  position: relative;
  cursor: pointer;
  background: var(--color-bg-tertiary);
}

.drop-zone:hover:not(.is-uploading) {
  border-color: var(--color-accent);
  background: rgba(0, 102, 204, 0.05);
}

.drop-zone.drag-over {
  border-color: var(--color-accent);
  background: rgba(0, 102, 204, 0.1);
  transform: scale(1.02);
}

.drop-zone.is-uploading {
  cursor: not-allowed;
  opacity: 0.8;
}

.drop-zone.has-error {
  border-color: var(--color-error);
  background: var(--color-error-bg);
}

.file-input {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  opacity: 0;
  cursor: pointer;
  pointer-events: none;
}

.drop-zone-content {
  pointer-events: none;
}

.upload-status {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
}

.status-icon {
  font-size: 3rem;
  font-weight: bold;
}

.upload-status.error .status-icon {
  color: var(--color-error);
}

.status-text {
  font-size: 1.1rem;
  font-weight: 500;
  margin: 0;
}

.file-info {
  font-size: 0.9rem;
  color: var(--color-text-secondary);
  margin: 0;
}

.retry-button {
  pointer-events: auto;
  margin-top: 0.5rem;
}

.upload-prompt {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
}

.upload-icon {
  width: 4rem;
  height: 4rem;
  color: var(--color-accent);
  transition: transform var(--transition-fast);
}

.drop-zone:hover:not(.is-uploading) .upload-icon {
  transform: translateY(-4px);
}

.prompt-text {
  font-size: 1.1rem;
  margin: 0;
  line-height: 1.6;
}

.prompt-text strong {
  color: var(--color-text);
}

.prompt-detail {
  font-size: 0.875rem;
  color: var(--color-text-secondary);
  margin: 0;
}

.spinner {
  display: inline-block;
  width: 2rem;
  height: 2rem;
  border: 3px solid var(--color-border);
  border-top-color: var(--color-accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.spinner.large {
  width: 3rem;
  height: 3rem;
  border-width: 4px;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.file-requirements {
  margin-top: 2rem;
  padding-top: 2rem;
  border-top: 1px solid var(--color-border);
}

.file-requirements h3 {
  font-size: 1rem;
  margin-bottom: 0.75rem;
  color: var(--color-text-secondary);
}

.file-requirements ul {
  list-style: none;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.file-requirements li {
  font-size: 0.9rem;
  color: var(--color-text-secondary);
  padding-left: 1.5rem;
  position: relative;
}

.file-requirements li::before {
  content: '•';
  position: absolute;
  left: 0.5rem;
  color: var(--color-accent);
}

/* Mobile: < 640px */
@media (max-width: 639px) {
  .file-upload {
    max-width: 100%;
  }

  .drop-zone {
    padding: 2rem 1rem;
    min-height: 240px;
  }

  .upload-icon {
    width: 3rem;
    height: 3rem;
  }

  .prompt-text {
    font-size: 0.95rem;
  }

  .prompt-text br {
    display: none;
  }

  .file-requirements h3 {
    font-size: 0.9rem;
  }

  .file-requirements ul {
    gap: 0.375rem;
  }

  .file-requirements li {
    font-size: 0.8rem;
  }
}

/* Tablet: 640px - 1023px */
@media (min-width: 640px) and (max-width: 1023px) {
  .file-upload {
    max-width: 90%;
  }

  .drop-zone {
    padding: 2.5rem 1.5rem;
  }
}

/* Desktop: >= 1024px */
@media (min-width: 1024px) {
  .file-upload {
    max-width: 800px;
  }
}
</style>
