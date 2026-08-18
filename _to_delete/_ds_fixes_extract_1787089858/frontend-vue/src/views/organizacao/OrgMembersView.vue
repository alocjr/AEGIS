<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import {
  listOrgMembers,
  createOrgMember,
  updateOrgMember,
  deleteOrgMember,
} from '@/api/orgAdmin'
import type { OrgMember } from '@/api/orgAdmin'

const auth = useAuthStore()
const currentUserId = computed(() => auth.user?.id ?? '')

const loading = ref(true)
const error = ref<string | null>(null)
const members = ref<OrgMember[]>([])
const searchQuery = ref('')

const filteredMembers = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  if (!q) return members.value
  return members.value.filter(
    (m) =>
      (m.name ?? '').toLowerCase().includes(q) ||
      (m.email ?? '').toLowerCase().includes(q) ||
      (m.phone && String(m.phone).includes(q))
  )
})

const modalOpen = ref(false)
const modalMode = ref<'create' | 'edit'>('create')
const editingId = ref<string | null>(null)
const modalSaving = ref(false)
const modalError = ref<string | null>(null)
const form = ref<{ name: string; email: string; password: string; phone: string }>({
  name: '',
  email: '',
  password: '',
  phone: '',
})

const deleteTarget = ref<OrgMember | null>(null)
const deleteConfirming = ref(false)
const deleteError = ref<string | null>(null)

function resetForm() {
  form.value = { name: '', email: '', password: '', phone: '' }
  editingId.value = null
  modalError.value = null
}

function openCreate() {
  modalMode.value = 'create'
  resetForm()
  modalOpen.value = true
}

function openEdit(member: OrgMember) {
  modalMode.value = 'edit'
  editingId.value = member.id
  modalError.value = null
  form.value = { name: member.name, email: member.email, password: '', phone: member.phone || '' }
  modalOpen.value = true
}

function closeModal() {
  modalOpen.value = false
  modalSaving.value = false
  modalError.value = null
}

function formatDate(iso: string | null | undefined) {
  if (iso == null || iso === '') return '—'
  try {
    return new Date(iso).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric' })
  } catch {
    return '—'
  }
}

async function loadMembers() {
  members.value = (await listOrgMembers()).items
}

async function saveModal() {
  modalError.value = null
  const { name, email, password, phone } = form.value
  if (!name.trim()) {
    modalError.value = 'Nome é obrigatório.'
    return
  }
  if (!email.trim()) {
    modalError.value = 'E-mail é obrigatório.'
    return
  }
  if (modalMode.value === 'create' && !password.trim()) {
    modalError.value = 'Senha é obrigatória ao adicionar um membro (mín. 6 caracteres).'
    return
  }
  if (modalMode.value === 'create' && password.length < 6) {
    modalError.value = 'Senha deve ter no mínimo 6 caracteres.'
    return
  }

  modalSaving.value = true
  try {
    if (modalMode.value === 'create') {
      await createOrgMember({
        name: name.trim(),
        email: email.trim().toLowerCase(),
        password,
        phone: phone.trim() || undefined,
      })
    } else {
      const id = editingId.value!
      const body: Parameters<typeof updateOrgMember>[1] = {
        name: name.trim(),
        email: email.trim().toLowerCase(),
        phone: phone.trim() || '',
      }
      if (password.trim()) body.password = password
      await updateOrgMember(id, body)
    }
    await loadMembers()
    closeModal()
  } catch (e: unknown) {
    const msg = e && typeof e === 'object' && 'message' in e ? String((e as Error).message) : 'Erro ao salvar.'
    modalError.value = msg
  } finally {
    modalSaving.value = false
  }
}

function askDelete(member: OrgMember) {
  deleteTarget.value = member
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
  try {
    await deleteOrgMember(deleteTarget.value.id)
    await loadMembers()
    cancelDelete()
  } catch (e: unknown) {
    const msg = e && typeof e === 'object' && 'message' in e ? String((e as Error).message) : 'Erro ao remover.'
    deleteError.value = msg
  }
}

onMounted(async () => {
  try {
    await loadMembers()
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Erro ao carregar membros da organização.'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="org-page">
    <header class="page-header">
      <h1 class="page-title">Minha Organização</h1>
      <p class="page-sub">
        Adicione pessoas do seu time para usar as ferramentas do AI Hub (Canvas, SWOT, Maturidade,
        Governança). Acesso à mentoria (trilhas) continua exclusivo da equipe Valorian.
      </p>
      <div class="page-actions">
        <input
          v-model="searchQuery"
          type="search"
          class="input search-input"
          placeholder="Buscar por nome, e-mail ou telefone..."
          aria-label="Buscar membros"
        />
        <button type="button" class="btn-primary" @click="openCreate">Adicionar membro</button>
      </div>
    </header>

    <div v-if="loading" class="loading">Carregando...</div>
    <div v-else-if="error" class="error-msg">{{ error }}</div>
    <div v-else-if="members.length === 0" class="empty">
      Nenhum membro na organização ainda. Clique em <strong>Adicionar membro</strong> para criar o primeiro.
    </div>
    <div v-else class="table-wrap">
      <table class="data-table">
        <thead>
          <tr>
            <th>Nome</th>
            <th>E-mail</th>
            <th>Telefone</th>
            <th>Papel</th>
            <th>Desde</th>
            <th class="th-actions">Ações</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="m in filteredMembers" :key="m.id">
            <td class="name-cell">{{ m.name }}</td>
            <td>{{ m.email }}</td>
            <td>{{ m.phone || '—' }}</td>
            <td>
              <span v-if="m.is_org_admin" class="badge badge-org-admin">Admin da organização</span>
              <span v-else class="muted">Membro</span>
            </td>
            <td>{{ formatDate(m.created_at) }}</td>
            <td class="actions-cell">
              <button type="button" class="btn-secondary btn-sm" @click="openEdit(m)">Editar</button>
              <button
                v-if="m.id !== currentUserId"
                type="button"
                class="btn-danger btn-sm"
                @click="askDelete(m)"
              >
                Remover
              </button>
              <span v-else class="self-hint" title="Não é possível remover seu próprio usuário">—</span>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-if="searchQuery && filteredMembers.length < members.length" class="filter-hint">
        Mostrando {{ filteredMembers.length }} de {{ members.length }} membros.
      </p>
    </div>

    <Teleport to="body">
      <div v-if="modalOpen" class="modal-backdrop" @click.self="closeModal">
        <div class="modal-box">
          <div class="modal-header">
            <h2>{{ modalMode === 'create' ? 'Adicionar membro' : 'Editar membro' }}</h2>
            <button type="button" class="modal-close" aria-label="Fechar" @click="closeModal">×</button>
          </div>
          <div class="modal-body">
            <div v-if="modalError" class="modal-error">{{ modalError }}</div>
            <div class="form-group">
              <label for="member-name">Nome</label>
              <input id="member-name" v-model="form.name" type="text" class="input" placeholder="Nome completo" />
            </div>
            <div class="form-group">
              <label for="member-email">E-mail</label>
              <input id="member-email" v-model="form.email" type="email" class="input" placeholder="email@empresa.com" />
            </div>
            <div class="form-group">
              <label for="member-password">
                {{ modalMode === 'create' ? 'Senha (obrigatória)' : 'Nova senha (deixe em branco para manter)' }}
              </label>
              <input
                id="member-password"
                v-model="form.password"
                type="password"
                class="input"
                :placeholder="modalMode === 'edit' ? '••••••••' : 'Mínimo 6 caracteres'"
                autocomplete="new-password"
              />
            </div>
            <div class="form-group">
              <label for="member-phone">Telefone (opcional)</label>
              <input id="member-phone" v-model="form.phone" type="text" class="input" placeholder="ex: 5511987654321" />
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn-secondary" @click="closeModal">Cancelar</button>
            <button type="button" class="btn-primary" :disabled="modalSaving" @click="saveModal">
              {{ modalSaving ? 'Salvando…' : (modalMode === 'create' ? 'Adicionar' : 'Salvar') }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <Teleport to="body">
      <div v-if="deleteConfirming && deleteTarget" class="modal-backdrop" @click.self="cancelDelete">
        <div class="modal-box modal-confirm">
          <div class="modal-header">
            <h2>Remover membro</h2>
            <button type="button" class="modal-close" aria-label="Fechar" @click="cancelDelete">×</button>
          </div>
          <div class="modal-body">
            <div v-if="deleteError" class="modal-error">{{ deleteError }}</div>
            <p>
              Tem certeza que deseja remover <strong>{{ deleteTarget.name }}</strong> ({{ deleteTarget.email }})
              da organização? Esta ação não pode ser desfeita.
            </p>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn-secondary" @click="cancelDelete">Cancelar</button>
            <button type="button" class="btn-danger" @click="confirmDelete">Remover</button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.org-page {
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
  max-width: 640px;
}

.page-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
}

.search-input {
  max-width: 320px;
  min-width: 200px;
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

.table-wrap {
  background: var(--wh);
  border: 1px solid var(--bd);
  border-radius: var(--r-lg);
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
}

.data-table th {
  font-weight: 600;
  color: var(--k0);
  background: var(--k8);
}

.data-table tbody tr:hover {
  background: var(--k9);
}

.name-cell {
  font-weight: 500;
  color: var(--k0);
}

.muted {
  color: var(--k5);
}

.badge {
  display: inline-block;
  padding: 2px 8px;
  font-size: 12px;
  font-weight: 600;
  border-radius: var(--r-sm);
}

.badge-org-admin {
  color: var(--k0);
  background: var(--golddim);
  border: 1px solid var(--goldbd);
}

.th-actions,
.actions-cell {
  text-align: right;
  white-space: nowrap;
}

.actions-cell {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
  align-items: center;
}

.self-hint {
  color: var(--k5);
  font-size: 13px;
}

.filter-hint {
  padding: 12px 16px;
  font-size: 13px;
  color: var(--k5);
  border-top: 1px solid var(--bd2);
}

.btn-primary,
.btn-secondary,
.btn-danger {
  padding: 10px 18px;
  border-radius: var(--r-md);
  font-size: 14px;
  font-weight: 500;
  border: 1px solid transparent;
  cursor: pointer;
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

.input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--bd);
  border-radius: var(--r-md);
  font-size: 14px;
  font-family: inherit;
}

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
  border-radius: var(--r-lg);
  box-shadow: var(--shadow-3);
  max-width: 560px;
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
  border-radius: var(--r-md);
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
  border-radius: var(--r-md);
  font-size: 14px;
  margin-bottom: 16px;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 24px;
  border-top: 1px solid var(--bd2);
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
</style>
