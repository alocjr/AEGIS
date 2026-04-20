<script setup lang="ts">
import { ref, onMounted } from 'vue'
import {
  fetchCourseList,
  fetchCourse,
  createCourse,
  updateCourse,
  deleteCourse,
} from '@/api/admin'
import type { CourseListItem } from '@/api/admin'

const loading = ref(true)
const error = ref<string | null>(null)
const trilhas = ref<CourseListItem[]>([])

const modalOpen = ref(false)
const modalMode = ref<'create' | 'edit'>('create')
const modalSlug = ref('')
const modalJson = ref('')
const modalSaving = ref(false)
const modalError = ref<string | null>(null)
const editingSlug = ref<string | null>(null)

const deleteTarget = ref<CourseListItem | null>(null)
const deleteConfirming = ref(false)

const EMPTY_PFE = `{
  "cabecalho": {
    "titulo": "",
    "tema": "",
    "publico": "",
    "trilha": "",
    "estrutura_resumo": "",
    "status": "",
    "ano": ""
  },
  "visao_geral": {
    "objetivo": "",
    "instrutor": ""
  },
  "jornada_aprendizagem": []
}`

function openCreate() {
  modalMode.value = 'create'
  modalSlug.value = ''
  modalJson.value = EMPTY_PFE
  modalError.value = null
  editingSlug.value = null
  modalOpen.value = true
}

async function openEdit(item: CourseListItem) {
  modalMode.value = 'edit'
  editingSlug.value = item.slug
  modalSlug.value = item.slug
  modalError.value = null
  modalOpen.value = true
  try {
    const course = await fetchCourse(item.slug)
    modalJson.value = JSON.stringify(course.programa_formacao_executiva, null, 2)
  } catch (e) {
    modalError.value = e instanceof Error ? e.message : 'Erro ao carregar trilha.'
  }
}

function closeModal() {
  modalOpen.value = false
  modalError.value = null
  modalSaving.value = false
}

function parseJson(): Record<string, unknown> | null {
  try {
    return JSON.parse(modalJson.value) as Record<string, unknown>
  } catch {
    return null
  }
}

async function saveModal() {
  modalError.value = null
  const pfe = parseJson()
  if (!pfe) {
    modalError.value = 'JSON inválido. Corrija o conteúdo do programa.'
    return
  }
  const slug = modalSlug.value.trim().toLowerCase().replace(/\s+/g, '-')
  if (!slug) {
    modalError.value = 'Slug é obrigatório (apenas letras, números e hífens).'
    return
  }
  if (!/^[a-z0-9-]+$/.test(slug)) {
    modalError.value = 'Slug deve conter apenas letras minúsculas, números e hífens.'
    return
  }
  modalSaving.value = true
  try {
    if (modalMode.value === 'create') {
      await createCourse(slug, pfe)
      trilhas.value = await fetchCourseList()
      closeModal()
    } else {
      await updateCourse(editingSlug.value!, pfe)
      trilhas.value = await fetchCourseList()
      closeModal()
    }
  } catch (e) {
    modalError.value = e instanceof Error ? e.message : 'Erro ao salvar.'
  } finally {
    modalSaving.value = false
  }
}

function askDelete(item: CourseListItem) {
  deleteTarget.value = item
  deleteConfirming.value = true
}

function cancelDelete() {
  deleteTarget.value = null
  deleteConfirming.value = false
}

async function confirmDelete() {
  if (!deleteTarget.value) return
  const slug = deleteTarget.value.slug
  try {
    await deleteCourse(slug)
    trilhas.value = await fetchCourseList()
    cancelDelete()
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Erro ao excluir trilha.'
    cancelDelete()
  }
}

onMounted(async () => {
  try {
    trilhas.value = await fetchCourseList()
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Erro ao carregar trilhas.'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="trilhas-page">
    <header class="page-header">
      <h1 class="page-title">Trilhas</h1>
      <p class="page-sub">Criar e editar trilhas de formação (cursos).</p>
      <div class="page-actions">
        <button type="button" class="btn-primary" @click="openCreate">Nova trilha</button>
      </div>
    </header>

    <div v-if="loading" class="loading">Carregando...</div>
    <div v-else-if="error" class="error-msg">{{ error }}</div>
    <div v-else-if="trilhas.length === 0" class="empty">
      Nenhuma trilha cadastrada. Clique em <strong>Nova trilha</strong> para criar.
    </div>
    <div v-else class="card-grid">
      <article v-for="t in trilhas" :key="t.slug" class="trilha-card">
        <div class="trilha-card-header">
          <h2 class="trilha-title">{{ t.titulo || t.slug }}</h2>
          <span class="trilha-tema">{{ t.tema || '—' }}</span>
          <code class="trilha-slug">{{ t.slug }}</code>
        </div>
        <div class="trilha-card-actions">
          <button type="button" class="btn-secondary btn-sm" @click="openEdit(t)">Editar</button>
          <button type="button" class="btn-danger btn-sm" @click="askDelete(t)">Excluir</button>
        </div>
      </article>
    </div>

    <!-- Modal Criar / Editar -->
    <Teleport to="body">
      <div v-if="modalOpen" class="modal-backdrop" @click.self="closeModal">
        <div class="modal-box">
          <div class="modal-header">
            <h2>{{ modalMode === 'create' ? 'Nova trilha' : 'Editar trilha' }}</h2>
            <button type="button" class="modal-close" aria-label="Fechar" @click="closeModal">×</button>
          </div>
          <div class="modal-body">
            <div v-if="modalError" class="modal-error">{{ modalError }}</div>
            <div class="form-group">
              <label for="trilha-slug">Slug (identificador único)</label>
              <input
                id="trilha-slug"
                v-model="modalSlug"
                type="text"
                placeholder="ex: trilha-ia-executiva"
                :readonly="modalMode === 'edit'"
                class="input"
              />
              <span v-if="modalMode === 'edit'" class="form-hint">Slug não pode ser alterado na edição.</span>
            </div>
            <div class="form-group">
              <label for="trilha-json">Programa (JSON)</label>
              <textarea
                id="trilha-json"
                v-model="modalJson"
                class="input textarea-json"
                rows="18"
                spellcheck="false"
              />
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn-secondary" @click="closeModal">Cancelar</button>
            <button type="button" class="btn-primary" :disabled="modalSaving" @click="saveModal">
              {{ modalSaving ? 'Salvando…' : (modalMode === 'create' ? 'Criar' : 'Salvar') }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Confirmação excluir -->
    <Teleport to="body">
      <div v-if="deleteConfirming && deleteTarget" class="modal-backdrop" @click.self="cancelDelete">
        <div class="modal-box modal-confirm">
          <div class="modal-header">
            <h2>Excluir trilha</h2>
            <button type="button" class="modal-close" aria-label="Fechar" @click="cancelDelete">×</button>
          </div>
          <div class="modal-body">
            <p>
              Tem certeza que deseja excluir a trilha
              <strong>{{ deleteTarget.titulo || deleteTarget.slug }}</strong>
              (<code>{{ deleteTarget.slug }}</code>)? Esta ação não pode ser desfeita.
            </p>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn-secondary" @click="cancelDelete">Cancelar</button>
            <button type="button" class="btn-danger" @click="confirmDelete">Excluir</button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.trilhas-page {
  max-width: 1000px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 28px;
}

.page-title {
  font-family: var(--serif);
  font-size: 28px;
  color: var(--k0);
  margin-bottom: 4px;
}

.page-sub {
  font-size: 14px;
  color: var(--k5);
  margin-bottom: 16px;
}

.page-actions {
  display: flex;
  gap: 12px;
}

.loading,
.error-msg,
.empty {
  padding: 40px 0;
  color: var(--k5);
}

.error-msg {
  color: #8f2b2b;
}

.empty strong {
  color: var(--k0);
}

.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
}

.trilha-card {
  background: var(--wh);
  border: 1px solid var(--bd);
  border-radius: 12px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  transition: box-shadow 0.2s ease, border-color 0.2s ease;
}

.trilha-card:hover {
  box-shadow: 0 4px 16px rgba(12, 35, 64, 0.08);
  border-color: var(--goldbd);
}

.trilha-card-header {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.trilha-title {
  font-family: var(--serif);
  font-size: 18px;
  font-weight: 600;
  color: var(--k0);
  margin: 0;
  line-height: 1.3;
}

.trilha-tema {
  font-size: 12px;
  color: var(--k5);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.trilha-slug {
  font-size: 12px;
  color: var(--k4);
  background: var(--k8);
  padding: 4px 8px;
  border-radius: 6px;
  align-self: flex-start;
}

.trilha-card-actions {
  display: flex;
  gap: 10px;
  margin-top: auto;
}

.btn-primary,
.btn-secondary,
.btn-danger {
  padding: 10px 18px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  border: 1px solid transparent;
  transition: background 0.15s ease, color 0.15s ease, border-color 0.15s ease;
}

.btn-primary {
  background: var(--k0);
  color: var(--wh);
}

.btn-primary:hover:not(:disabled) {
  background: #132d52;
}

.btn-primary:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.btn-secondary {
  background: var(--wh);
  color: var(--k0);
  border-color: var(--bd);
}

.btn-secondary:hover {
  background: var(--k8);
}

.btn-danger {
  background: var(--wh);
  color: #8f2b2b;
  border-color: rgba(143, 43, 43, 0.35);
}

.btn-danger:hover {
  background: var(--lowBg);
}

.btn-sm {
  padding: 6px 12px;
  font-size: 13px;
}

/* Modal */
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 24px;
}

.modal-box {
  background: var(--wh);
  border-radius: 12px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
  max-width: 640px;
  width: 100%;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
}

.modal-confirm {
  max-width: 440px;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid var(--bd2);
}

.modal-header h2 {
  font-family: var(--serif);
  font-size: 20px;
  font-weight: 600;
  margin: 0;
  color: var(--k0);
}

.modal-close {
  width: 36px;
  height: 36px;
  border: none;
  background: none;
  font-size: 24px;
  line-height: 1;
  color: var(--k5);
  cursor: pointer;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.modal-close:hover {
  background: var(--k8);
  color: var(--k0);
}

.modal-body {
  padding: 24px;
  overflow-y: auto;
  flex: 1;
}

.modal-error {
  padding: 12px 14px;
  background: #fdecec;
  color: #8f2b2b;
  border-radius: 8px;
  font-size: 14px;
  margin-bottom: 16px;
}

.form-group {
  margin-bottom: 18px;
}

.form-group:last-child {
  margin-bottom: 0;
}

.form-group label {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: var(--k0);
  margin-bottom: 6px;
}

.form-hint {
  display: block;
  font-size: 12px;
  color: var(--k5);
  margin-top: 4px;
}

.input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--bd);
  border-radius: 8px;
  font-size: 14px;
  font-family: inherit;
}

.input:read-only {
  background: var(--k8);
  color: var(--k4);
}

.textarea-json {
  font-family: ui-monospace, 'Cascadia Code', 'Source Code Pro', Menlo, monospace;
  font-size: 13px;
  line-height: 1.5;
  resize: vertical;
  min-height: 320px;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 24px;
  border-top: 1px solid var(--bd2);
}
</style>
