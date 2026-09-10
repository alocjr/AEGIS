<script setup lang="ts">
import { computed } from 'vue'
import type { ArtifactVisibility } from '@/lib/visibility'
import { normalizeVisibility } from '@/lib/visibility'

const props = withDefaults(
  defineProps<{
    modelValue?: ArtifactVisibility | string | null
    compact?: boolean
    disabled?: boolean
  }>(),
  { compact: false, disabled: false }
)

const emit = defineEmits<{
  'update:modelValue': [ArtifactVisibility]
}>()

const current = computed(() => normalizeVisibility(props.modelValue))

function set(value: ArtifactVisibility) {
  if (props.disabled || value === current.value) return
  emit('update:modelValue', value)
}
</script>

<template>
  <div
    class="vis"
    :class="{ compact, disabled }"
    role="group"
    aria-label="Visibilidade"
  >
    <button
      type="button"
      class="vis-btn"
      :class="{ on: current === 'shared' }"
      :disabled="disabled"
      @click="set('shared')"
    >
      Compartilhado
    </button>
    <button
      type="button"
      class="vis-btn"
      :class="{ on: current === 'private' }"
      :disabled="disabled"
      @click="set('private')"
    >
      Privado
    </button>
  </div>
</template>

<style scoped>
.vis {
  display: inline-flex;
  border: 1px solid var(--bd, rgba(0, 0, 0, 0.12));
  border-radius: var(--r-xs, 6px);
  overflow: hidden;
  background: var(--wh, #fff);
}
.vis-btn {
  height: 32px;
  padding: 0 12px;
  border: none;
  background: transparent;
  font: inherit;
  font-size: 12px;
  letter-spacing: 0.02em;
  color: var(--k3, #666);
  cursor: pointer;
}
.vis-btn + .vis-btn {
  border-left: 1px solid var(--bd, rgba(0, 0, 0, 0.12));
}
.vis-btn.on {
  background: var(--k0, #1a1a1a);
  color: #fff;
}
.vis.disabled .vis-btn {
  cursor: default;
  opacity: 0.6;
}
.vis.compact .vis-btn {
  height: 28px;
  padding: 0 8px;
  font-size: 11px;
}
</style>
