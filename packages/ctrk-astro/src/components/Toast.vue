<script setup lang="ts">
import { useToast } from '@tex0l/ctrk-astro/composables';

const { toasts, removeToast } = useToast();

function getIcon(type: string): string {
  switch (type) {
    case 'success': return '✓';
    case 'error': return '✗';
    case 'warning': return '⚠';
    case 'info': return 'ℹ';
    default: return '';
  }
}

function iconColorClass(type: string): string {
  switch (type) {
    case 'success': return 'text-(--color-success)';
    case 'error': return 'text-(--color-error)';
    case 'warning': return 'text-(--color-warning)';
    case 'info': return 'text-(--color-info)';
    default: return '';
  }
}

function borderColorClass(type: string): string {
  switch (type) {
    case 'success': return 'border-l-4 border-l-(--color-success)';
    case 'error': return 'border-l-4 border-l-(--color-error)';
    case 'warning': return 'border-l-4 border-l-(--color-warning)';
    case 'info': return 'border-l-4 border-l-(--color-info)';
    default: return '';
  }
}
</script>

<template>
  <div class="fixed top-4 right-4 z-[9999] flex flex-col gap-2 pointer-events-none">
    <transition-group name="toast">
      <div
        v-for="toast in toasts"
        :key="toast.id"
        :class="[
          'flex items-center gap-3 min-w-[300px] max-w-[500px] px-5 py-4 bg-(--color-bg-secondary) border border-(--color-border) rounded-md shadow-lg cursor-pointer pointer-events-auto transition-all duration-250 hover:-translate-y-0.5 hover:shadow-xl',
          borderColorClass(toast.type),
        ]"
        @click="removeToast(toast.id)"
      >
        <span :class="['text-xl font-bold shrink-0', iconColorClass(toast.type)]">{{ getIcon(toast.type) }}</span>
        <span class="flex-1 text-[0.95rem] leading-relaxed">{{ toast.message }}</span>
        <button
          class="bg-transparent text-(--color-text-secondary) border-none p-0 w-6 h-6 flex items-center justify-center text-2xl leading-none cursor-pointer transition-colors duration-150 shrink-0 hover:text-(--color-text-primary)"
          @click.stop="removeToast(toast.id)"
          aria-label="Close"
        >
          ×
        </button>
      </div>
    </transition-group>
  </div>
</template>

<style>
/* Vue transition classes — can't be expressed as Tailwind utilities */
.toast-enter-active,
.toast-leave-active {
  transition: all 250ms ease;
}

.toast-enter-from {
  opacity: 0;
  transform: translateX(100%);
}

.toast-leave-to {
  opacity: 0;
  transform: translateX(50%) scale(0.8);
}

.toast-move {
  transition: transform 250ms ease;
}
</style>
