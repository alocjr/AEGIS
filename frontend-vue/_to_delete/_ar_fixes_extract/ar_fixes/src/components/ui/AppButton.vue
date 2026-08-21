<script setup lang="ts">
import { RouterLink } from 'vue-router'

/**
 * AR-01: consolida .btn-primary (12 arquivos), .btn-secondary (10),
 * .btn-danger (8) e variações soltas de "ghost"/"sm" em botão único.
 * Passa `to` para navegar (renderiza RouterLink); sem `to`, renderiza
 * <button> nativo — cobre os dois padrões já usados na base.
 */
withDefaults(
  defineProps<{
    variant?: 'primary' | 'secondary' | 'danger' | 'ghost'
    size?: 'md' | 'sm'
    disabled?: boolean
    type?: 'button' | 'submit'
    to?: string | Record<string, unknown> | null
  }>(),
  { variant: 'secondary', size: 'md', disabled: false, type: 'button', to: null }
)

defineEmits<{ click: [MouseEvent] }>()
</script>

<template>
  <component
    :is="to ? RouterLink : 'button'"
    :to="to ?? undefined"
    :type="to ? undefined : type"
    :disabled="to ? undefined : disabled"
    class="app-btn"
    :class="[`app-btn--${variant}`, `app-btn--${size}`, { 'app-btn--disabled': to && disabled }]"
    :aria-disabled="to && disabled ? 'true' : undefined"
    @click="(e: MouseEvent) => !disabled && $emit('click', e)"
  >
    <slot />
  </component>
</template>

<style scoped>
.app-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-family: inherit;
  font-size: var(--fs-base);
  font-weight: 600;
  line-height: 1;
  border-radius: var(--r-sm);
  border: 1px solid transparent;
  cursor: pointer;
  text-decoration: none;
  transition: background 0.15s, border-color 0.15s, color 0.15s, opacity 0.15s;
  white-space: nowrap;
}
.app-btn--md {
  height: 40px;
  padding: 0 18px;
}
.app-btn--sm {
  height: 32px;
  padding: 0 13px;
  font-size: var(--fs-sm);
}

.app-btn--primary {
  background: var(--k0);
  border-color: var(--k0);
  color: var(--wh);
}
.app-btn--primary:hover:not(:disabled):not(.app-btn--disabled) {
  background: var(--navy-deep);
}

.app-btn--secondary {
  background: var(--wh);
  border-color: var(--bd);
  color: var(--k1);
}
.app-btn--secondary:hover:not(:disabled):not(.app-btn--disabled) {
  border-color: var(--k5);
  background: var(--k9);
}

.app-btn--danger {
  background: var(--wh);
  border-color: var(--low);
  color: var(--low);
}
.app-btn--danger:hover:not(:disabled):not(.app-btn--disabled) {
  background: var(--lowBg);
}

.app-btn--ghost {
  background: transparent;
  border-color: transparent;
  color: var(--k3);
}
.app-btn--ghost:hover:not(:disabled):not(.app-btn--disabled) {
  background: var(--k8);
  color: var(--k1);
}

.app-btn:disabled,
.app-btn--disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.app-btn:focus-visible {
  outline: 2px solid var(--gold);
  outline-offset: 2px;
}
</style>
