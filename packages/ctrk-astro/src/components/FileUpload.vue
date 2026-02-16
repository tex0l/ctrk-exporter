<script setup lang="ts">
import { ref, computed } from 'vue';
import { fileToUint8Array, formatFileSize } from '@tex0l/ctrk-astro/utils';
import { useTelemetryData } from '@tex0l/ctrk-astro/composables';
import { useParserStatus } from '@tex0l/ctrk-astro/composables';
import { useToast } from '@tex0l/ctrk-astro/composables';
import { validateCTRKFile } from '@tex0l/ctrk-astro/lib/file-validator';
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
  <div v-if="hasData" class="flex justify-end relative mb-4">
    <button
      @click="handleUploadAnother"
      class="flex items-center gap-2 px-4 py-2 bg-(--color-bg-tertiary) border border-(--color-border) rounded-sm text-(--color-text-primary) text-sm font-medium cursor-pointer transition-all duration-150 hover:bg-(--color-accent) hover:text-white hover:border-(--color-accent) focus-visible:outline-2 focus-visible:outline-(--color-accent) focus-visible:outline-offset-2"
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        class="w-4 h-4"
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
      class="absolute inset-0 w-full h-full opacity-0 cursor-pointer pointer-events-none"
      aria-label="Upload CTRK telemetry file"
    />
  </div>

  <!-- Full upload form when no data is loaded -->
  <div v-else class="max-w-[800px] max-sm:max-w-full sm:max-w-[90%] lg:max-w-[800px] mx-auto bg-(--color-bg-secondary) border border-(--color-border) rounded-md p-6 mb-6">
    <h2 class="text-xl max-sm:text-lg font-semibold mb-4">Upload CTRK File</h2>
    <p class="text-(--color-text-secondary) mb-6 text-[0.95rem]">
      Upload a .CTRK telemetry file from your Yamaha Y-Trac device to begin analysis.
    </p>

    <div
      class="border-2 border-dashed border-(--color-border) rounded-md py-12 px-8 max-sm:py-8 max-sm:px-4 text-center transition-all duration-250 relative cursor-pointer bg-(--color-bg-tertiary)"
      :class="{
        'border-(--color-accent) bg-(--color-highlight-info) scale-[1.02]': dragOver,
        'cursor-not-allowed opacity-80': isUploading,
        'border-(--color-error) bg-(--color-highlight-error)': status === 'error',
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
        class="absolute inset-0 w-full h-full opacity-0 cursor-pointer pointer-events-none"
        :disabled="isUploading"
        aria-label="Upload CTRK telemetry file"
      />

      <div class="pointer-events-none">
        <div v-if="isUploading" class="flex flex-col items-center gap-4" role="status" aria-live="polite">
          <div class="w-12 h-12 border-4 border-(--color-border) border-t-(--color-accent) rounded-full animate-spin" aria-hidden="true"></div>
          <p class="text-lg font-medium m-0">Parsing file...</p>
          <p v-if="currentFile" class="text-sm text-(--color-text-secondary) m-0">
            {{ currentFile.name }} ({{ formatFileSize(currentFile.size) }})
          </p>
        </div>

        <div v-else-if="status === 'error'" class="flex flex-col items-center gap-4" role="alert" aria-live="assertive">
          <span class="text-5xl font-bold text-(--color-error)" aria-hidden="true">✗</span>
          <p class="text-lg font-medium m-0">Upload failed</p>
          <button @click.stop="clearFile" class="pointer-events-auto mt-2">Try Again</button>
        </div>

        <div v-else class="flex flex-col items-center gap-4">
          <svg
            class="w-16 h-16 max-sm:w-12 max-sm:h-12 text-(--color-accent) transition-transform duration-150"
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
          <p class="text-lg max-sm:text-[0.95rem] m-0 leading-relaxed">
            <strong class="text-(--color-text-primary)">Drop your .CTRK file here</strong><br class="max-sm:hidden" />
            or click to browse
          </p>
          <p class="text-sm text-(--color-text-secondary) m-0">Maximum file size: 50 MB</p>
        </div>
      </div>
    </div>

    <div class="mt-8 pt-8 border-t border-(--color-border)">
      <h3 class="text-base max-sm:text-sm mb-3 text-(--color-text-secondary)">Requirements</h3>
      <ul class="list-none p-0 flex flex-col gap-2 max-sm:gap-1.5">
        <li class="text-sm max-sm:text-xs text-(--color-text-secondary) pl-6 relative before:content-['•'] before:absolute before:left-2 before:text-(--color-accent)">File extension must be .CTRK</li>
        <li class="text-sm max-sm:text-xs text-(--color-text-secondary) pl-6 relative before:content-['•'] before:absolute before:left-2 before:text-(--color-accent)">Minimum file size: 100 bytes</li>
        <li class="text-sm max-sm:text-xs text-(--color-text-secondary) pl-6 relative before:content-['•'] before:absolute before:left-2 before:text-(--color-accent)">Maximum file size: 50 MB</li>
        <li class="text-sm max-sm:text-xs text-(--color-text-secondary) pl-6 relative before:content-['•'] before:absolute before:left-2 before:text-(--color-accent)">File must contain valid CTRK header ("HEAD")</li>
      </ul>
    </div>
  </div>
</template>
