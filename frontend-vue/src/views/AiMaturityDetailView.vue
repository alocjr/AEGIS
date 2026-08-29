<script setup lang="ts">
import { RouterLink } from 'vue-router'
import { useMaturityDetail } from '@/composables/useMaturityDetail'
import AiMaturityDetailBody from '@/components/maturity/AiMaturityDetailBody.vue'

const editor = useMaturityDetail()
const { loading, error, model, displayedResult } = editor
</script>

<template>
  <div class="wrap">
    <nav class="back-row">
      <RouterLink to="/ai-maturity" class="back-link">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <path d="M15 18l-6-6 6-6" />
        </svg>
        Voltar às autoavaliações
      </RouterLink>
    </nav>

    <div v-if="loading" class="state-card">Carregando resultado…</div>
    <div v-else-if="error" class="state-card error">{{ error }}</div>
    <AiMaturityDetailBody v-else-if="model && displayedResult" :editor="editor" />
  </div>
</template>

<style scoped>
.wrap {
  max-width: 920px;
  margin: 0 auto;
  padding: 16px 16px 48px;
}

.back-row {
  margin-bottom: 18px;
}
.back-link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  font-weight: 500;
  color: var(--k3);
  text-decoration: none;
  transition: color 0.15s;
}
.back-link svg {
  width: 18px;
  height: 18px;
}
.back-link:hover {
  color: var(--k0);
}

.state-card {
  background: var(--wh);
  border: 1px solid var(--bd);
  border-radius: var(--r-sm);
  padding: 28px 20px;
  text-align: center;
  color: var(--k3);
}
.state-card.error {
  color: var(--low);
  text-align: left;
}

@media (min-width: 560px) {
  .wrap {
    padding: 22px 20px 56px;
  }
}
</style>
