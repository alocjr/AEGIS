<script setup lang="ts">
import { ref, onMounted } from 'vue'
import {
  listLandingMaterials,
  createLandingMaterial,
  updateLandingMaterial,
  deleteLandingMaterial,
  uploadLandingMaterialFile,
} from '@/api/admin'
import type { LandingMaterial } from '@/api/admin'
import { formatCount, formatLastAccess } from '@/lib/accessFormat'

type UrlField = 'material_url' | 'summary_url' | 'audio_url'

/** Detalhe do acesso no tooltip: a coluna precisa caber, mas o número sozinho engana —
 * cliques repetidos da mesma pessoa contam, e visitantes únicos é que dizem o alcance. */
function accessTitle(item: LandingMaterial): string {
  if (item.access_count === 0) return 'Nenhum acesso registrado'
  const visitors = `${formatCount(item.access_visitors)} visitante(s) único(s)`
  return `${formatCount(item.access_count)} clique(s) em "Baixar material" e "Resumo executivo" · ${visitors}`
}

const loading = ref(true)
const error = ref<string | null>(null)
const items = ref<LandingMaterial[]>([])

const modalOpen = ref(false)
const modalMode = ref<'create' | 'edit'>('create')
const editingId = ref<string | null>(null)
const modalSaving = ref(false)
const modalError = ref<string | null>(null)
const uploading = ref<Record<UrlField, boolean>>({
  material_url: false,
  summary_url: false,
  audio_url: false,
})

const form = ref({
  title: '',
  description: '',
  material_url: '',
  summary_url: '',
  audio_url: '',
  order: 0,
  active: true,
})

const deleteTarget = ref<LandingMaterial | null>(null)
const deleteConfirming = ref(false)
const deleteError = ref<string | null>(null)

function resetForm() {
  form.value = {
    title: '',
    description: '',
    material_url: '',
    summary_url: '',
    audio_url: '',
    order: items.value.length,
    active: true,
  }
  editingId.value = null
  modalError.value = null
}

function openCreate() {
  modalMode.value = 'create'
  resetForm()
  modalOpen.value = true
}

function openEdit(item: LandingMaterial) {
  modalMode.value = 'edit'
  editingId.value = item.id
  modalError.value = null
  form.value = {
    title: item.title,
    description: item.description,
    material_url: item.material_url,
    summary_url: item.summary_url,
    audio_url: item.audio_url || '',
    order: item.order,
    active: item.active,
  }
  modalOpen.value = true
}

function closeModal() {
  modalOpen.value = false
  modalSaving.value = false
  modalError.value = null
}

async function onUpload(field: UrlField, event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  modalError.value = null
  uploading.value[field] = true
  try {
    const result = await uploadLandingMaterialFile(file)
    form.value[field] = result.url
  } catch (e: unknown) {
    modalError.value =
      e instanceof Error ? e.message : 'Erro ao enviar arquivo.'
  } finally {
    uploading.value[field] = false
    input.value = ''
  }
}

async function saveModal() {
  modalError.value = null
  const title = form.value.title.trim()
  const description = form.value.description.trim()
  const material_url = form.value.material_url.trim()
  const summary_url = form.value.summary_url.trim()
  const audio_url = form.value.audio_url.trim() || null
  if (!title || !description || !material_url || !summary_url) {
    modalError.value = 'Preencha título, descrição e os dois links (URL ou upload).'
    return
  }
  modalSaving.value = true
  try {
    const payload = {
      title,
      description,
      material_url,
      summary_url,
      audio_url,
      order: Number(form.value.order) || 0,
      active: form.value.active,
    }
    if (modalMode.value === 'create') {
      await createLandingMaterial(payload)
    } else if (editingId.value) {
      await updateLandingMaterial(editingId.value, payload)
    }
    items.value = await listLandingMaterials()
    closeModal()
  } catch (e: unknown) {
    modalError.value =
      e instanceof Error ? e.message : 'Erro ao salvar material.'
  } finally {
    modalSaving.value = false
  }
}

function askDelete(item: LandingMaterial) {
  deleteTarget.value = item
  deleteError.value = null
  deleteConfirming.value = true
}

function cancelDelete() {
  deleteTarget.value = null
  deleteError.value = null
  deleteConfirming.value = false
}

async function confirmDelete() {
  if (!deleteTarget.value) return
  deleteError.value = null
  try {
    await deleteLandingMaterial(deleteTarget.value.id)
    items.value = await listLandingMaterials()
    cancelDelete()
  } catch (e: unknown) {
    deleteError.value =
      e instanceof Error ? e.message : 'Erro ao excluir material.'
  }
}

onMounted(async () => {
  try {
    items.value = await listLandingMaterials()
  } catch (e) {
    error.value =
      e instanceof Error ? e.message : 'Erro ao carregar materiais.'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="materiais-landing-page">
    <header class="page-header">
      <h1 class="page-title">Materiais da Landing</h1>
      <p class="page-sub">
        Cards da vitrine no hero da landing: título, descrição, links e áudio narrado.
        Você pode colar uma URL ou fazer upload (salva em <code>/material_gratuito</code>).
      </p>
      <div class="page-actions">
        <button type="button" class="btn-primary" @click="openCreate">Novo material</button>
      </div>
    </header>

    <div v-if="loading" class="loading">Carregando...</div>
    <div v-else-if="error" class="error-msg">{{ error }}</div>
    <div v-else-if="items.length === 0" class="empty">
      Nenhum material cadastrado. Clique em <strong>Novo material</strong> para criar.
    </div>
    <div v-else class="table-wrap">
      <table class="data-table">
        <thead>
          <tr>
            <th>Ordem</th>
            <th>Título</th>
            <th>Ativo</th>
            <th>Material</th>
            <th>Resumo</th>
            <th>Áudio</th>
            <th class="th-access">Acessos</th>
            <th class="th-actions">Ações</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in items" :key="item.id">
            <td>{{ item.order }}</td>
            <td class="name-cell">
              <div>{{ item.title }}</div>
              <div class="desc-preview">{{ item.description }}</div>
            </td>
            <td>{{ item.active ? 'Sim' : 'Não' }}</td>
            <td>
              <a :href="item.material_url" target="_blank" rel="noopener" class="link">Abrir</a>
            </td>
            <td>
              <a :href="item.summary_url" target="_blank" rel="noopener" class="link">Abrir</a>
            </td>
            <td>{{ item.audio_url ? 'Sim' : '—' }}</td>
            <td class="td-access" :title="accessTitle(item)">
              <span class="access-count">{{ formatCount(item.access_count) }}</span>
              <span v-if="item.access_count > 0" class="access-meta">
                {{ formatLastAccess(item.last_access_at) }}
              </span>
            </td>
            <td class="td-actions">
              <button type="button" class="btn-secondary btn-sm" @click="openEdit(item)">Editar</button>
              <button type="button" class="btn-danger btn-sm" @click="askDelete(item)">Excluir</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <Teleport to="body">
      <div v-if="modalOpen" class="modal-backdrop" @click.self="closeModal">
        <div class="modal" role="dialog" aria-modal="true" aria-labelledby="mat-modal-title">
          <h2 id="mat-modal-title" class="modal-title">
            {{ modalMode === 'create' ? 'Novo material' : 'Editar material' }}
          </h2>
          <div class="form-grid">
            <label class="field">
              <span>Título</span>
              <input v-model="form.title" type="text" class="input" maxlength="200" />
            </label>
            <label class="field">
              <span>Ordem</span>
              <input v-model.number="form.order" type="number" class="input" min="0" max="9999" />
            </label>
            <label class="field field-full">
              <span>Descrição</span>
              <textarea v-model="form.description" class="input textarea" rows="3" maxlength="2000" />
            </label>

            <div class="field field-full">
              <span>Material (PDF, HTML ou link)</span>
              <div class="url-upload-row">
                <input
                  v-model="form.material_url"
                  type="text"
                  class="input"
                  placeholder="/material_gratuito/arquivo.pdf ou https://..."
                />
                <label class="btn-upload" :class="{ disabled: uploading.material_url }">
                  {{ uploading.material_url ? 'Enviando…' : 'Upload' }}
                  <input
                    type="file"
                    class="file-input"
                    accept=".pdf,.html,.htm,.doc,.docx,.ppt,.pptx,application/pdf,text/html"
                    :disabled="uploading.material_url"
                    @change="onUpload('material_url', $event)"
                  />
                </label>
              </div>
            </div>

            <div class="field field-full">
              <span>Resumo executivo (PDF ou link)</span>
              <div class="url-upload-row">
                <input
                  v-model="form.summary_url"
                  type="text"
                  class="input"
                  placeholder="/material_gratuito/resumo.pdf ou https://..."
                />
                <label class="btn-upload" :class="{ disabled: uploading.summary_url }">
                  {{ uploading.summary_url ? 'Enviando…' : 'Upload' }}
                  <input
                    type="file"
                    class="file-input"
                    accept=".pdf,.doc,.docx,application/pdf"
                    :disabled="uploading.summary_url"
                    @change="onUpload('summary_url', $event)"
                  />
                </label>
              </div>
            </div>

            <div class="field field-full">
              <span>Áudio narrado (opcional)</span>
              <div class="url-upload-row">
                <input
                  v-model="form.audio_url"
                  type="text"
                  class="input"
                  placeholder="/material_gratuito/narracao.mp3 ou https://..."
                />
                <label class="btn-upload" :class="{ disabled: uploading.audio_url }">
                  {{ uploading.audio_url ? 'Enviando…' : 'Upload' }}
                  <input
                    type="file"
                    class="file-input"
                    accept=".mp3,.m4a,.wav,.ogg,.aac,audio/*"
                    :disabled="uploading.audio_url"
                    @change="onUpload('audio_url', $event)"
                  />
                </label>
              </div>
            </div>

            <label class="field checkbox-field">
              <input v-model="form.active" type="checkbox" />
              <span>Ativo na landing</span>
            </label>
          </div>
          <p v-if="modalError" class="error-msg">{{ modalError }}</p>
          <div class="modal-actions">
            <button type="button" class="btn-secondary" :disabled="modalSaving" @click="closeModal">Cancelar</button>
            <button type="button" class="btn-primary" :disabled="modalSaving" @click="saveModal">
              {{ modalSaving ? 'Salvando...' : 'Salvar' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <Teleport to="body">
      <div v-if="deleteConfirming" class="modal-backdrop" @click.self="cancelDelete">
        <div class="modal modal-sm" role="dialog" aria-modal="true">
          <h2 class="modal-title">Excluir material?</h2>
          <p class="modal-text">
            Remover <strong>{{ deleteTarget?.title }}</strong> da vitrine da landing.
          </p>
          <p v-if="deleteError" class="error-msg">{{ deleteError }}</p>
          <div class="modal-actions">
            <button type="button" class="btn-secondary" @click="cancelDelete">Cancelar</button>
            <button type="button" class="btn-danger" @click="confirmDelete">Excluir</button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.materiais-landing-page {
  max-width: 1100px;
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
.page-sub code {
  font-size: 12px;
  background: rgba(0, 0, 0, 0.05);
  padding: 1px 6px;
  border-radius: 4px;
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
  padding: 8px 0;
}
.empty strong {
  color: var(--k0);
}
.table-wrap {
  background: var(--wh);
  border: 1px solid var(--bd);
  border-radius: 12px;
  overflow: hidden;
}
.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}
.data-table th,
.data-table td {
  padding: 12px 16px;
  text-align: left;
  border-bottom: 1px solid var(--bd2);
  vertical-align: top;
}
.data-table th {
  font-weight: 600;
  color: var(--k0);
  background: var(--bg, #f7f5f0);
}
.name-cell {
  font-weight: 500;
  color: var(--k0);
  max-width: 280px;
}
.desc-preview {
  font-weight: 400;
  font-size: 12px;
  color: var(--k5);
  margin-top: 4px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.link {
  color: var(--k0);
  text-decoration: underline;
}
.th-actions,
.td-actions {
  white-space: nowrap;
}
.th-access,
.td-access {
  white-space: nowrap;
  text-align: right;
}
.access-count {
  font-weight: 600;
  color: var(--k0);
}
.access-meta {
  display: block;
  font-size: 11px;
  color: var(--k5);
  margin-top: 2px;
}
.td-actions {
  display: flex;
  gap: 8px;
}
.btn-primary,
.btn-secondary,
.btn-danger {
  font-size: 13px;
  padding: 8px 14px;
  border: none;
  cursor: pointer;
  border-radius: 6px;
}
.btn-primary {
  background: var(--k0);
  color: var(--wh);
}
.btn-secondary {
  background: transparent;
  border: 1px solid var(--bd);
  color: var(--k0);
}
.btn-danger {
  background: #8f2b2b;
  color: #fff;
}
.btn-sm {
  padding: 6px 10px;
  font-size: 12px;
}
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(12, 24, 39, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 24px;
}
.modal {
  background: var(--wh);
  border-radius: 12px;
  padding: 28px;
  width: min(640px, 100%);
  max-height: 90vh;
  overflow: auto;
}
.modal-sm {
  width: min(420px, 100%);
}
.modal-title {
  font-family: var(--serif);
  font-size: 22px;
  margin-bottom: 16px;
  color: var(--k0);
}
.modal-text {
  font-size: 14px;
  color: var(--k3);
  margin-bottom: 16px;
}
.form-grid {
  display: grid;
  grid-template-columns: 1fr 120px;
  gap: 14px;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 13px;
  color: var(--k3);
}
.field-full {
  grid-column: 1 / -1;
}
.checkbox-field {
  flex-direction: row;
  align-items: center;
  gap: 8px;
  grid-column: 1 / -1;
}
.input {
  border: 1px solid var(--bd);
  border-radius: 6px;
  padding: 10px 12px;
  font-size: 14px;
  color: var(--k0);
  background: var(--wh);
  flex: 1;
  min-width: 0;
}
.textarea {
  resize: vertical;
  min-height: 72px;
}
.url-upload-row {
  display: flex;
  gap: 8px;
  align-items: stretch;
}
.btn-upload {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  padding: 0 14px;
  border: 1px solid var(--bd);
  border-radius: 6px;
  background: var(--bg, #f7f5f0);
  color: var(--k0);
  font-size: 13px;
  cursor: pointer;
  white-space: nowrap;
}
.btn-upload.disabled {
  opacity: 0.6;
  cursor: wait;
}
.file-input {
  position: absolute;
  inset: 0;
  opacity: 0;
  cursor: pointer;
  width: 100%;
  height: 100%;
}
.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 20px;
}
</style>
