<script setup lang="ts">
import { RouterLink } from 'vue-router'
import { useOkrCycleEditor } from '@/composables/useOkrCycleEditor'
import OkrCycleBody from '@/components/okrs/OkrCycleBody.vue'

const editor = useOkrCycleEditor()
const { loading, error, saveState, saveError, savedAtLabel, dirty, cycle, saveNow } = editor
</script>

<template>
  <div class="page">
    <div class="toolbar">
      <RouterLink to="/okrs" class="back">← OKR</RouterLink>
      <div class="save-status">
        <span v-if="saveState === 'error'" class="err">{{ saveError || 'Erro ao salvar' }}</span>
        <span v-else-if="saveState === 'saving'">Salvando…</span>
        <span v-else-if="dirty" class="pending">Alterações não salvas</span>
        <span v-else-if="savedAtLabel" class="ok">Salvo às {{ savedAtLabel }}</span>
        <span v-else class="muted">Salva automaticamente enquanto você escreve</span>
        <button
          v-if="dirty || saveState === 'error'"
          type="button"
          class="btn-save"
          title="Salvar agora (⌘S / Ctrl+S)"
          :disabled="saveState === 'saving'"
          @click="saveNow()"
        >
          {{ saveState === 'error' ? 'Tentar novamente' : 'Salvar agora' }}
        </button>
      </div>
    </div>

    <div v-if="loading" class="card">Carregando...</div>
    <div v-else-if="error" class="card error-msg">{{ error }}</div>
    <OkrCycleBody v-else-if="cycle" :editor="editor" />
  </div>
</template>

<style scoped>
.page {
  max-width: var(--w-read);
  margin: 0 auto;
  padding: 20px 20px 60px;
}
.toolbar {
  position: sticky;
  top: var(--bar-h, 64px);
  z-index: 20;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 0;
  margin-bottom: 6px;
  background: var(--k9);
  border-bottom: 1px solid var(--bd);
}
.back {
  font-size: 13px;
  color: var(--k3);
  text-decoration: none;
}
.back:hover {
  color: var(--k0);
}
.save-status {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 12px;
  color: var(--k3);
}
.save-status .ok {
  color: #2f6e4a;
}
.save-status .err {
  color: #8f2b2b;
}
.save-status .pending {
  color: var(--warn-text);
}
.btn-save {
  font-size: 12px;
  padding: 5px 12px;
  border-radius: var(--r-sm);
  border: 1px solid var(--k0);
  background: var(--k0);
  color: var(--wh);
  cursor: pointer;
}
.btn-save:disabled {
  opacity: 0.6;
  cursor: wait;
}
.card {
  background: var(--wh);
  border: 1px solid var(--bd);
  border-radius: var(--r-lg);
  padding: 18px 20px;
  margin-bottom: 16px;
}
.error-msg {
  color: #8f2b2b;
}
</style>
