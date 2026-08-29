<script setup lang="ts">
import { RouterLink } from 'vue-router'
import { useCanvasEditor } from '@/composables/useCanvasEditor'
import CanvasEditorBody from '@/components/canvas/CanvasEditorBody.vue'

const editor = useCanvasEditor()
const {
  loading, error, saveState, saveError, importState, importError, importOkMsg,
  fileInput, openImportPicker, onImportFile,
} = editor
</script>

<template>
  <div class="page">
    <div class="toolbar">
      <RouterLink to="/projetos" class="back">← Projetos</RouterLink>
      <div class="toolbar-actions">
        <input
          ref="fileInput"
          type="file"
          accept="application/json,.json"
          class="sr-only"
          @change="onImportFile"
        />
        <button
          type="button"
          class="import-btn"
          :disabled="loading || importState === 'importing'"
          @click="openImportPicker"
        >
          {{ importState === 'importing' ? 'Importando…' : 'Importar JSON' }}
        </button>
        <div class="save-status">
          <span v-if="saveState === 'saving'">Salvando…</span>
          <span v-else-if="saveState === 'saved'" class="ok">Salvo</span>
          <span v-else-if="saveState === 'error'" class="err">{{ saveError || 'Erro ao salvar' }}</span>
          <span v-else class="muted">Salva ao sair do campo</span>
        </div>
      </div>
    </div>

    <div v-if="importState === 'error'" class="banner err">{{ importError }}</div>
    <div v-else-if="importState === 'ok'" class="banner ok">{{ importOkMsg }}</div>

    <div v-if="loading" class="state">Carregando canvas…</div>
    <div v-else-if="error" class="state err">{{ error }}</div>
    <CanvasEditorBody v-else :editor="editor" />
  </div>
</template>

<style scoped>
/* DS-05: @import de fonte removido daqui — era uma requisição bloqueante de
   terceira família tipográfica no meio do CSS de uma rota. As 13 declarações
   de 'Space Grotesk' abaixo foram trocadas pela pilha --sans/--serif já usada
   no resto do produto (DS-01: uma família editorial única). */

.page {
  max-width: 1180px;
  margin: 0 auto;
  padding: 20px 16px 48px;
  color: var(--canvas-ink);
}
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
  flex-wrap: wrap;
}
.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.import-btn {
  border: 1px solid var(--bd);
  background: #fff;
  color: var(--k0);
  font-size: 11px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  padding: 6px 12px;
  border-radius: var(--r-pill);
  cursor: pointer;
  font-family: inherit;
}
.import-btn:hover:not(:disabled) {
  border-color: var(--k0);
}
.import-btn:disabled {
  opacity: 0.6;
  cursor: wait;
}
.banner {
  border-radius: 10px;
  padding: 12px 14px;
  margin-bottom: 12px;
  font-size: 13px;
  border: 1px solid var(--bd);
  background: var(--wh);
}
.banner.ok {
  color: #2f6e4a;
  border-color: #bbd3b7;
  background: #e8f0e7;
}
.banner.err {
  color: #8f2b2b;
  border-color: #e2bcbc;
  background: #f8ecec;
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
.back {
  color: var(--k0, var(--canvas-ink));
  text-decoration: none;
  font-size: 14px;
}
.back:hover {
  text-decoration: underline;
}
.save-status {
  font-size: 12px;
  color: var(--canvas-ink-soft);
}
.save-status .ok {
  color: var(--success-text);
}
.save-status .err,
.state.err {
  color: var(--low);
}
.state {
  padding: 40px 0;
  color: var(--canvas-ink-soft);
}
</style>
