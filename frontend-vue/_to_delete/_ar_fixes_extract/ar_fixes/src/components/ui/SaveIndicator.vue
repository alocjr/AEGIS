<script setup lang="ts">
import type { AutosaveState } from '@/composables/useAutosave'

/**
 * AR-01 / AR-03: par visual do estado devolvido por useAutosave(). Antes,
 * cada uma das 4 telas migradas desenhava seu próprio "Salvando…/Salvo/Erro"
 * com marcação e cores levemente diferentes; agora é uma leitura direta de
 * AutosaveState, sem reimplementação em cada view.
 */
defineProps<{
  state: AutosaveState
  /** Mensagem de erro a exibir quando state === 'error'. */
  error?: string | null
}>()

const LABEL: Record<AutosaveState, string> = {
  idle: '',
  saving: 'Salvando…',
  saved: 'Salvo',
  error: 'Erro ao salvar',
}
</script>

<template>
  <p v-if="state !== 'idle'" class="save-indicator" :class="`save-indicator--${state}`" role="status" aria-live="polite">
    <span v-if="state === 'saving'" class="save-indicator__spinner" aria-hidden="true" />
    <span v-else-if="state === 'saved'" class="save-indicator__dot" aria-hidden="true" />
    <span v-else-if="state === 'error'" class="save-indicator__dot" aria-hidden="true" />
    {{ state === 'error' ? (error ?? LABEL.error) : LABEL[state] }}
  </p>
</template>

<style scoped>
.save-indicator {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  font-size: var(--fs-sm);
  font-weight: 600;
  color: var(--k4);
}
.save-indicator--saved {
  color: var(--success);
}
.save-indicator--error {
  color: var(--low);
}
.save-indicator__dot {
  width: 7px;
  height: 7px;
  border-radius: var(--r-pill);
  background: currentColor;
  flex-shrink: 0;
}
.save-indicator__spinner {
  width: 12px;
  height: 12px;
  border-radius: var(--r-pill);
  border: 2px solid var(--k7);
  border-top-color: var(--gold);
  animation: save-indicator-spin 0.8s linear infinite;
  flex-shrink: 0;
}

@media (prefers-reduced-motion: reduce) {
  .save-indicator__spinner {
    animation-duration: 2s;
  }
}

@keyframes save-indicator-spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
