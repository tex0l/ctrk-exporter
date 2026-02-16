<script setup lang="ts">
import { ref, computed } from 'vue';
import { CHANNEL_GROUPS, getAllChannels } from '@tex0l/ctrk-astro/lib/chart-config';
import type { ChannelDefinition } from '@tex0l/ctrk-astro/lib/chart-config';

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
  <div class="w-full">
    <button
      @click="toggleExpanded"
      class="flex items-center gap-2 w-full py-3 px-4 max-sm:py-2.5 max-sm:px-3.5 max-sm:min-h-[44px] bg-(--color-bg-tertiary) border border-(--color-border) rounded-sm cursor-pointer transition-colors duration-150 text-[0.95rem] max-sm:text-sm text-(--color-text-primary) hover:bg-(--color-bg-secondary) focus-visible:outline-2 focus-visible:outline-(--color-accent) focus-visible:outline-offset-2"
      :aria-expanded="expanded"
      aria-controls="channel-selector-panel"
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        class="w-5 h-5 max-sm:w-[1.125rem] max-sm:h-[1.125rem] text-(--color-accent)"
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
        class="w-4 h-4 max-sm:w-3.5 max-sm:h-3.5 ml-auto transition-transform duration-150"
        :class="{ 'rotate-180': expanded }"
        aria-hidden="true"
      >
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
      </svg>
    </button>

    <div v-if="expanded" class="mt-2 p-3 max-sm:p-2 bg-(--color-bg-tertiary) border border-(--color-border) rounded-sm" id="channel-selector-panel" role="group" aria-label="Channel selection">
      <div class="grid grid-cols-4 sm:grid-cols-3 lg:grid-cols-4 max-sm:grid-cols-2 gap-3 max-sm:gap-2">
        <div
          v-for="group in CHANNEL_GROUPS"
          :key="group.id"
          class="min-w-0"
        >
          <label class="flex items-center gap-1.5 py-1 px-1.5 mb-1 cursor-pointer rounded-sm hover:bg-(--color-bg-secondary) focus-within:outline-2 focus-within:outline-(--color-accent) focus-within:outline-offset-2">
            <input
              type="checkbox"
              :checked="isGroupFullyEnabled(group.id)"
              v-indeterminate="isGroupPartiallyEnabled(group.id)"
              @change="toggleGroup(group.id)"
              class="cursor-pointer accent-(--color-accent) m-0"
              :aria-label="`Toggle all channels in ${group.label} group`"
            />
            <span class="font-semibold text-xs max-sm:text-[0.7rem] text-(--color-text-primary) uppercase tracking-wide">{{ group.label }}</span>
          </label>

          <div class="flex flex-col gap-px" role="group" :aria-label="`${group.label} channels`">
            <label
              v-for="channel in group.channels"
              :key="channel.id"
              class="flex items-center gap-1.5 py-1 px-1.5 max-sm:py-1.5 max-sm:px-1 max-sm:min-h-[36px] rounded-sm cursor-pointer transition-colors duration-150 text-xs max-sm:text-[0.75rem] hover:bg-(--color-bg-secondary) focus-within:outline-2 focus-within:outline-(--color-accent) focus-within:outline-offset-2"
              :class="{ 'bg-(--color-highlight-info-subtle)': isChannelEnabled(channel.id) }"
            >
              <input
                type="checkbox"
                :checked="isChannelEnabled(channel.id)"
                @change="toggleChannel(channel.id)"
                class="cursor-pointer accent-(--color-accent) m-0 w-3.5 h-3.5 shrink-0"
                :aria-label="`Toggle ${channel.label}`"
              />
              <span class="w-2 h-2 max-sm:w-1.5 max-sm:h-1.5 rounded-full shrink-0" :style="{ backgroundColor: channel.color }"></span>
              <span class="font-normal text-(--color-text-primary) whitespace-nowrap overflow-hidden text-ellipsis">{{ channel.label }}</span>
              <span v-if="channel.unit" class="ml-auto text-[0.7rem] text-(--color-text-secondary) font-normal shrink-0">{{ channel.unit }}</span>
            </label>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
