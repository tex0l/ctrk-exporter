<script setup lang="ts">
import { ref, computed } from 'vue';
import { CHANNEL_GROUPS, getAllChannels } from '../lib/chart-config';
import type { ChannelDefinition } from '../lib/chart-config';

interface Props {
  modelValue: string[]; // Array of enabled channel IDs
}

interface Emits {
  (e: 'update:modelValue', value: string[]): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();

const expanded = ref(false);

// Custom directive for indeterminate checkbox state
const vIndeterminate = {
  mounted(el: HTMLInputElement, binding: { value: boolean }) {
    el.indeterminate = binding.value;
  },
  updated(el: HTMLInputElement, binding: { value: boolean }) {
    el.indeterminate = binding.value;
  },
};

// Total number of channels across all groups
const totalChannelCount = computed(() => {
  return getAllChannels().length;
});

// Number of enabled channels
const enabledChannelCount = computed(() => {
  return props.modelValue.length;
});

// Toggle main selector panel
function toggleExpanded() {
  expanded.value = !expanded.value;
}

// Get enabled count for a group
function getGroupEnabledCount(groupId: string): number {
  const group = CHANNEL_GROUPS.find((g) => g.id === groupId);
  if (!group) return 0;

  const channelIds = group.channels.map((c) => c.id);
  return channelIds.filter((id) => props.modelValue.includes(id)).length;
}

// Check if all channels in a group are enabled
function isGroupFullyEnabled(groupId: string): boolean {
  const group = CHANNEL_GROUPS.find((g) => g.id === groupId);
  if (!group) return false;

  const channelIds = group.channels.map((c) => c.id);
  return channelIds.every((id) => props.modelValue.includes(id));
}

// Check if some (but not all) channels in a group are enabled
function isGroupPartiallyEnabled(groupId: string): boolean {
  const enabledCount = getGroupEnabledCount(groupId);
  const group = CHANNEL_GROUPS.find((g) => g.id === groupId);
  if (!group) return false;

  return enabledCount > 0 && enabledCount < group.channels.length;
}

// Toggle all channels in a group
function toggleGroup(groupId: string) {
  const group = CHANNEL_GROUPS.find((g) => g.id === groupId);
  if (!group) return;

  const channelIds = group.channels.map((c) => c.id);
  const enabled = new Set(props.modelValue);

  if (isGroupFullyEnabled(groupId)) {
    // Deselect all channels in group
    channelIds.forEach((id) => enabled.delete(id));
  } else {
    // Select all channels in group
    channelIds.forEach((id) => enabled.add(id));
  }

  emit('update:modelValue', Array.from(enabled));
}

// Toggle a single channel
function toggleChannel(channelId: string) {
  const enabled = new Set(props.modelValue);

  if (enabled.has(channelId)) {
    enabled.delete(channelId);
  } else {
    enabled.add(channelId);
  }

  emit('update:modelValue', Array.from(enabled));
}

// Check if a channel is enabled
function isChannelEnabled(channelId: string): boolean {
  return props.modelValue.includes(channelId);
}
</script>

<template>
  <div class="channel-selector">
    <button
      @click="toggleExpanded"
      class="selector-toggle"
      :aria-expanded="expanded"
      aria-controls="channel-selector-panel"
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        class="icon"
        aria-hidden="true"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4"
        />
      </svg>
      <span>Channels ({{ enabledChannelCount }}/{{ totalChannelCount }})</span>
      <svg
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        class="chevron"
        :class="{ expanded }"
        aria-hidden="true"
      >
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
      </svg>
    </button>

    <div v-if="expanded" class="selector-panel" id="channel-selector-panel" role="group" aria-label="Channel selection">
      <div class="channel-grid">
        <div
          v-for="group in CHANNEL_GROUPS"
          :key="group.id"
          class="channel-group"
        >
          <label class="group-header">
            <input
              type="checkbox"
              :checked="isGroupFullyEnabled(group.id)"
              v-indeterminate="isGroupPartiallyEnabled(group.id)"
              @change="toggleGroup(group.id)"
              :aria-label="`Toggle all channels in ${group.label} group`"
            />
            <span class="group-label">{{ group.label }}</span>
          </label>

          <div class="channel-list" role="group" :aria-label="`${group.label} channels`">
            <label
              v-for="channel in group.channels"
              :key="channel.id"
              class="channel-item"
              :class="{ enabled: isChannelEnabled(channel.id) }"
            >
              <input
                type="checkbox"
                :checked="isChannelEnabled(channel.id)"
                @change="toggleChannel(channel.id)"
                :aria-label="`Toggle ${channel.label}`"
              />
              <span class="channel-color-dot" :style="{ backgroundColor: channel.color }"></span>
              <span class="channel-label">{{ channel.label }}</span>
              <span v-if="channel.unit" class="channel-unit">{{ channel.unit }}</span>
            </label>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.channel-selector {
  width: 100%;
}

.selector-toggle {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  width: 100%;
  padding: 0.75rem 1rem;
  background: var(--color-bg-tertiary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: background var(--transition-fast);
  font-size: 0.95rem;
  color: var(--color-text);
}

.selector-toggle:hover {
  background: var(--color-bg-secondary);
}

.selector-toggle .icon {
  width: 1.25rem;
  height: 1.25rem;
  color: var(--color-accent);
}

.selector-toggle .chevron {
  width: 1rem;
  height: 1rem;
  margin-left: auto;
  transition: transform var(--transition-fast);
}

.selector-toggle .chevron.expanded {
  transform: rotate(180deg);
}

.selector-panel {
  margin-top: 0.5rem;
  padding: 0.75rem;
  background: var(--color-bg-tertiary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
}

.channel-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0.75rem;
}

.channel-group {
  min-width: 0;
}

.group-header {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.25rem 0.375rem;
  margin-bottom: 0.25rem;
  cursor: pointer;
  border-radius: var(--radius-xs);
}

.group-header:hover {
  background: var(--color-bg-secondary);
}

.group-header input[type='checkbox'] {
  cursor: pointer;
  accent-color: var(--color-accent);
  margin: 0;
}

.group-label {
  font-weight: 600;
  font-size: 0.8rem;
  color: var(--color-text);
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.channel-list {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.channel-item {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.25rem 0.375rem;
  border-radius: var(--radius-xs);
  cursor: pointer;
  transition: background var(--transition-fast);
  font-size: 0.8rem;
}

.channel-item:hover {
  background: var(--color-bg-secondary);
}

.channel-item.enabled {
  background: rgba(0, 102, 204, 0.06);
}

.channel-item input[type='checkbox'] {
  cursor: pointer;
  accent-color: var(--color-accent);
  margin: 0;
  width: 14px;
  height: 14px;
  flex-shrink: 0;
}

.channel-color-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.channel-label {
  font-weight: 400;
  color: var(--color-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.channel-unit {
  margin-left: auto;
  font-size: 0.7rem;
  color: var(--color-text-secondary);
  font-weight: 400;
  flex-shrink: 0;
}

/* Mobile: < 640px */
@media (max-width: 639px) {
  .selector-toggle {
    padding: 0.625rem 0.875rem;
    font-size: 0.875rem;
    min-height: 44px;
  }

  .selector-toggle .icon {
    width: 1.125rem;
    height: 1.125rem;
  }

  .selector-toggle .chevron {
    width: 0.875rem;
    height: 0.875rem;
  }

  .selector-panel {
    padding: 0.5rem;
  }

  .channel-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 0.5rem;
  }

  .channel-item {
    padding: 0.375rem 0.25rem;
    font-size: 0.75rem;
    min-height: 36px;
  }

  .group-label {
    font-size: 0.7rem;
  }

  .channel-color-dot {
    width: 6px;
    height: 6px;
  }
}

/* Tablet: 640px - 1023px */
@media (min-width: 640px) and (max-width: 1023px) {
  .channel-grid {
    grid-template-columns: repeat(3, 1fr);
  }

  .channel-item {
    font-size: 0.78rem;
  }
}

/* Desktop: >= 1024px */
@media (min-width: 1024px) {
  .channel-grid {
    grid-template-columns: repeat(4, 1fr);
  }
}

/* Focus styles for accessibility */
.selector-toggle:focus-visible,
.group-header:focus-within,
.channel-item:focus-within {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}
</style>
