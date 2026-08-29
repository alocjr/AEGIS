<script setup lang="ts">
import { RouterLink } from 'vue-router'
import { useSwotEditor } from '@/composables/useSwotEditor'
import StateBlock from '@/components/ui/StateBlock.vue'
import SwotEditorBody from '@/components/swot/SwotEditorBody.vue'

const editor = useSwotEditor()
const {
  loading,
  error,
  importState,
  importError,
  saveState,
  saveError,
  maturityResponseId,
  fileInput,
  openImportPicker,
  onImportFile,
} = editor
</script>

<template>
  <div class="wrap">
    <div class="page-header">
      <div>
        <p class="eyebrow">Instrumento estratégico · Valorian</p>
        <h1 class="page-title">SWOT de <em>IA</em></h1>
        <p class="page-desc">
          Traduz a prontidão do
          <RouterLink class="inline-link" to="/ai-maturity">Modelo de Maturidade</RouterLink>
          em FOFA estratégica — sob a ótica da estratégia de IA, da matriz ao veredito.
        </p>
        <p v-if="maturityResponseId" class="page-desc maturity-origin">
          Gerada a partir do
          <RouterLink class="inline-link" :to="`/ai-maturity/${maturityResponseId}`">
            diagnóstico de maturidade
          </RouterLink>
          · esta é a SWOT em edição (a barra SWOT abre sempre a mais recente).
        </p>
      </div>
      <div class="header-actions">
        <input
          ref="fileInput"
          type="file"
          accept="application/json,.json"
          class="sr-only"
          @change="onImportFile"
        />
        <RouterLink class="maturity-link" to="/ai-maturity">Modelo de Maturidade</RouterLink>
        <button
          type="button"
          class="import-btn"
          :disabled="importState === 'importing'"
          @click="openImportPicker"
        >
          {{ importState === 'importing' ? 'Importando…' : 'Importar JSON' }}
        </button>
        <div class="save-pill" :data-state="saveState">
          <span v-if="saveState === 'saving'">Salvando…</span>
          <span v-else-if="saveState === 'saved'">Salvo</span>
          <span v-else-if="saveState === 'error'">{{ saveError || 'Erro ao salvar' }}</span>
          <span v-else>Auto-salva</span>
        </div>
      </div>
    </div>

    <div v-if="importState === 'error'" class="card error-msg">{{ importError }}</div>
    <div v-else-if="importState === 'ok'" class="card import-ok">JSON importado com sucesso.</div>

    <StateBlock v-if="loading" state="loading" />
    <StateBlock v-else-if="error" state="error" :message="error" />

    <SwotEditorBody v-else :editor="editor" />
  </div>
</template>

<style scoped>
.wrap {
  max-width: 920px;
  margin: 0 auto;
  padding: 28px 20px 72px;
  color: var(--ink);
}
.page-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
  margin-bottom: 22px;
}
.header-actions {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 8px;
  flex-shrink: 0;
}
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
.import-btn {
  border: 1px solid var(--line);
  background: #fff;
  color: var(--navy);
  font-size: 11px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  font-weight: 600;
  padding: 6px 12px;
  border-radius: var(--r-pill);
  cursor: pointer;
  font-family: inherit;
}
.import-btn:hover:not(:disabled) {
  border-color: var(--gold);
  color: var(--gold);
}
.import-btn:disabled {
  opacity: 0.6;
  cursor: wait;
}
.import-ok {
  color: #2f6e4a;
  border-color: #bbd3b7;
  background: #e8f0e7;
}
.eyebrow {
  font-size: 0.7rem;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: var(--gold);
  font-weight: 600;
  margin: 0 0 6px;
}
.page-title {
  font-family: var(--serif);
  font-weight: 600;
  font-size: clamp(1.9rem, 5vw, 2.6rem);
  line-height: 1.05;
  color: var(--navy);
  margin: 0 0 8px;
}
.page-title em {
  font-style: italic;
  color: var(--gold);
}
.page-desc {
  margin: 0;
  color: var(--muted);
  font-size: 14px;
  line-height: 1.5;
  max-width: 52ch;
}
.page-desc.maturity-origin {
  margin-top: 8px;
  font-size: 13px;
}
.inline-link {
  color: var(--navy);
  font-weight: 600;
  text-decoration: underline;
  text-underline-offset: 2px;
}
.inline-link:hover {
  color: var(--gold);
}
.maturity-link {
  display: inline-flex;
  align-items: center;
  padding: 8px 14px;
  border: 1px solid var(--navy);
  border-radius: var(--r-xs);
  background: #fff;
  color: var(--navy);
  font-size: 13px;
  font-weight: 600;
  text-decoration: none;
  white-space: nowrap;
  transition: opacity 0.2s;
}
.maturity-link:hover {
  opacity: 0.9;
}
.save-pill {
  flex-shrink: 0;
  font-size: 11px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  padding: 6px 10px;
  border: 1px solid var(--line);
  border-radius: var(--r-pill);
  color: var(--muted);
  background: #fff;
}
.save-pill[data-state='saving'] {
  color: var(--navy);
}
.save-pill[data-state='saved'] {
  color: #2f6e4a;
  border-color: #bbd3b7;
  background: #e8f0e7;
}
.save-pill[data-state='error'] {
  color: var(--oxblood);
  border-color: #ddbcb4;
  background: #f1e1dd;
  text-transform: none;
  letter-spacing: 0;
  max-width: 180px;
}
.card {
  background: var(--ivory-2);
  border: 1px solid var(--line);
  border-radius: var(--r-xs);
  padding: 18px 20px;
  margin-bottom: 16px;
}
.error-msg {
  color: #8f2b2b;
}
@media (max-width: 700px) {
  .page-header {
    flex-direction: column;
  }
  .header-actions {
    align-items: flex-start;
    flex-direction: row;
    flex-wrap: wrap;
  }
}
</style>
