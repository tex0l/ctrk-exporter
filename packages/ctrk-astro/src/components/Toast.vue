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
</script>

<template>
  <div class="toast-container">
    <transition-group name="toast">
      <div
        v-for="toast in toasts"
        :key="toast.id"
        :class="['toast', `toast-${toast.type}`]"
        @click="removeToast(toast.id)"
      >
        <span class="toast-icon">{{ getIcon(toast.type) }}</span>
        <span class="toast-message">{{ toast.message }}</span>
        <button class="toast-close" @click.stop="removeToast(toast.id)" aria-label="Close">
          ×
        </button>
      </div>
    </transition-group>
  </div>
</template>

<style scoped>
.toast-container {
  position: fixed;
  top: 1rem;
  right: 1rem;
  z-index: 9999;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  pointer-events: none;
}

.toast {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  min-width: 300px;
  max-width: 500px;
  padding: 1rem 1.25rem;
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.5);
  cursor: pointer;
  pointer-events: auto;
  transition: all var(--transition-normal);
}

.toast:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.6);
}

.toast-success {
  border-left: 4px solid var(--color-success);
}

.toast-error {
  border-left: 4px solid var(--color-error);
}

.toast-warning {
  border-left: 4px solid var(--color-warning);
}

.toast-info {
  border-left: 4px solid var(--color-info);
}

.toast-icon {
  font-size: 1.25rem;
  font-weight: bold;
  flex-shrink: 0;
}

.toast-success .toast-icon {
  color: var(--color-success);
}

.toast-error .toast-icon {
  color: var(--color-error);
}

.toast-warning .toast-icon {
  color: var(--color-warning);
}

.toast-info .toast-icon {
  color: var(--color-info);
}

.toast-message {
  flex: 1;
  font-size: 0.95rem;
  line-height: 1.4;
}

.toast-close {
  background: none;
  color: var(--color-text-secondary);
  border: none;
  padding: 0;
  width: 1.5rem;
  height: 1.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.5rem;
  line-height: 1;
  cursor: pointer;
  transition: color var(--transition-fast);
  flex-shrink: 0;
}

.toast-close:hover {
  color: var(--color-text);
}

/* Transition animations */
.toast-enter-active,
.toast-leave-active {
  transition: all var(--transition-normal);
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
  transition: transform var(--transition-normal);
}
</style>
