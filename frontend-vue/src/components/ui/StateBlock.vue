<script setup lang="ts">
/**
 * AR-01: substitui as reimplementações artesanais de loading/empty/error que
 * existiam em ~43 arquivos (.loading em 20, .error-msg em 23, .empty em 11),
 * cada uma com marcação e microcópia próprias — inclusive misturando
 * reticências ASCII ("Carregando...") e tipográficas ("Carregando…") no
 * mesmo produto (UX-02). Uma só fonte de verdade para os três estados.
 *
 * Uso típico:
 *   <StateBlock v-if="loading" state="loading" />
 *   <StateBlock v-else-if="error" state="error" :message="error" :retry="load" />
 *   <StateBlock v-else-if="items.length === 0" state="empty" message="Nada por aqui ainda." />
 *   <template v-else>...</template>
 */
withDefaults(
  defineProps<{
    state: 'loading' | 'empty' | 'error'
    /** Sobrescreve a mensagem padrão do estado. */
    message?: string | null
    /** Quando definido, mostra um botão "Tentar novamente" (só no estado error). */
    retry?: (() => void) | null
  }>(),
  { message: null, retry: null }
)

const DEFAULTS: Record<'loading' | 'empty' | 'error', string> = {
  loading: 'Carregando…',
  empty: 'Nada por aqui ainda.',
  error: 'Não foi possível carregar.',
}
</script>

<template>
  <div class="state-block" :class="`state-block--${state}`" role="status" :aria-live="state === 'error' ? 'assertive' : 'polite'">
    <span v-if="state === 'loading'" class="state-block__spinner" aria-hidden="true" />
    <p class="state-block__text">{{ message ?? DEFAULTS[state] }}</p>
    <button v-if="state === 'error' && retry" type="button" class="state-block__retry" @click="retry">
      Tentar novamente
    </button>
  </div>
</template>

<style scoped>
.state-block {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 48px 20px;
  text-align: center;
  color: var(--k4);
}
.state-block--error {
  color: var(--low);
}
.state-block__text {
  font-size: var(--fs-md);
  line-height: 1.55;
  max-width: 46ch;
}
.state-block__spinner {
  width: 22px;
  height: 22px;
  border-radius: var(--r-pill);
  border: 2px solid var(--k7);
  border-top-color: var(--gold);
  animation: state-block-spin 0.8s linear infinite;
}
.state-block__retry {
  margin-top: 4px;
  padding: 8px 18px;
  border: 1px solid var(--low);
  border-radius: var(--r-sm);
  background: transparent;
  color: var(--low);
  font-size: var(--fs-sm);
  font-weight: 600;
}
.state-block__retry:hover {
  background: var(--lowBg);
}

@media (prefers-reduced-motion: reduce) {
  .state-block__spinner {
    animation-duration: 2s;
  }
}

@keyframes state-block-spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
