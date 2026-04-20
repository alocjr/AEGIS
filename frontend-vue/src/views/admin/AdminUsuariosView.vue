<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import {
  listUsers,
  getUser,
  createUser,
  updateUser,
  deleteUser,
  fetchCourseList,
} from '@/api/admin'
import type { AdminUser, AdminUserDetail, CourseListItem } from '@/api/admin'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const currentUserId = computed(() => auth.user?.id ?? '')

const loading = ref(true)
const error = ref<string | null>(null)
const users = ref<AdminUser[]>([])
const courses = ref<CourseListItem[]>([])
const searchQuery = ref('')

const filteredUsers = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  if (!q) return users.value
  return users.value.filter((u) => {
    const matchSlug =
      (u.course_slug ?? '').toLowerCase().includes(q) ||
      (u.course_slugs ?? []).some((s) => s.toLowerCase().includes(q))
    return (
      (u.name ?? '').toLowerCase().includes(q) ||
      (u.email ?? '').toLowerCase().includes(q) ||
      (u.phone && String(u.phone).includes(q)) ||
      matchSlug
    )
  })
})

const modalOpen = ref(false)
const modalMode = ref<'create' | 'edit'>('create')
const editingId = ref<string | null>(null)
const modalSaving = ref(false)
const modalError = ref<string | null>(null)
const form = ref<{
  name: string
  email: string
  password: string
  course_slugs: string[]
  phone: string
  is_admin: boolean
}>({
  name: '',
  email: '',
  password: '',
  course_slugs: [],
  phone: '',
  is_admin: false,
})

const deleteTarget = ref<AdminUser | null>(null)
const deleteConfirming = ref(false)
const deleteError = ref<string | null>(null)

function resetForm() {
  form.value = {
    name: '',
    email: '',
    password: '',
    course_slugs: courses.value[0]?.slug ? [courses.value[0].slug] : [],
    phone: '',
    is_admin: false,
  }
  editingId.value = null
  modalError.value = null
}

function openCreate() {
  modalMode.value = 'create'
  resetForm()
  if (courses.value.length && form.value.course_slugs.length === 0) {
    form.value.course_slugs = [courses.value[0].slug]
  }
  modalOpen.value = true
}

async function openEdit(user: AdminUser) {
  modalMode.value = 'edit'
  editingId.value = user.id
  modalError.value = null
  modalOpen.value = true
  try {
    const detail = await getUser(user.id) as AdminUserDetail
    const slugs = detail.course_slugs?.length
      ? detail.course_slugs
      : detail.course_slug
        ? [detail.course_slug]
        : courses.value[0]?.slug
          ? [courses.value[0].slug]
          : []
    form.value = {
      name: detail.name,
      email: detail.email,
      password: '',
      course_slugs: [...slugs],
      phone: detail.phone || '',
      is_admin: detail.is_admin,
    }
  } catch (e) {
    modalError.value = e instanceof Error ? e.message : 'Erro ao carregar usuário.'
  }
}

function closeModal() {
  modalOpen.value = false
  modalSaving.value = false
  modalError.value = null
}

function formatDate(iso: string | null | undefined) {
  if (iso == null || iso === '') return '—'
  try {
    return new Date(iso).toLocaleDateString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    })
  } catch {
    return '—'
  }
}

async function saveModal() {
  modalError.value = null
  const { name, email, password, course_slugs, phone, is_admin } = form.value
  if (!name.trim()) {
    modalError.value = 'Nome é obrigatório.'
    return
  }
  if (!email.trim()) {
    modalError.value = 'E-mail é obrigatório.'
    return
  }
  if (modalMode.value === 'create' && !password.trim()) {
    modalError.value = 'Senha é obrigatória ao criar usuário (mín. 6 caracteres).'
    return
  }
  if (modalMode.value === 'create' && password.length < 6) {
    modalError.value = 'Senha deve ter no mínimo 6 caracteres.'
    return
  }
  const slugs = (course_slugs ?? []).filter((s) => s?.trim())
  if (slugs.length === 0) {
    modalError.value = 'Selecione ao menos uma trilha.'
    return
  }

  modalSaving.value = true
  try {
    if (modalMode.value === 'create') {
      await createUser({
        name: name.trim(),
        email: email.trim().toLowerCase(),
        password: password,
        course_slugs: slugs,
        phone: phone.trim() || undefined,
      })
      users.value = await listUsers()
      closeModal()
    } else {
      const id = editingId.value!
      const body: Parameters<typeof updateUser>[1] = {
        name: name.trim(),
        email: email.trim().toLowerCase(),
        course_slugs: slugs,
        phone: phone.trim() || '',
        is_admin,
      }
      if (password.trim()) body.password = password
      await updateUser(id, body)
      users.value = await listUsers()
      closeModal()
    }
  } catch (e: unknown) {
    const msg = e && typeof e === 'object' && 'detail' in e
      ? String((e as { detail: string }).detail)
      : e instanceof Error ? e.message : 'Erro ao salvar.'
    modalError.value = msg
  } finally {
    modalSaving.value = false
  }
}

function askDelete(user: AdminUser) {
  deleteTarget.value = user
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
  const id = deleteTarget.value.id
  deleteError.value = null
  try {
    await deleteUser(id)
    users.value = await listUsers()
    cancelDelete()
  } catch (e: unknown) {
    const msg = e && typeof e === 'object' && 'detail' in e
      ? String((e as { detail: string }).detail)
      : e instanceof Error ? e.message : 'Erro ao excluir.'
    deleteError.value = msg
  }
}

onMounted(async () => {
  try {
    const [usersList, coursesList] = await Promise.all([
      listUsers(),
      fetchCourseList(),
    ])
    users.value = Array.isArray(usersList) ? usersList : []
    courses.value = Array.isArray(coursesList) ? coursesList : []
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Erro ao carregar usuários.'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="usuarios-page">
    <header class="page-header">
      <h1 class="page-title">Usuários</h1>
      <p class="page-sub">Gerir usuários da plataforma: criar, editar e excluir.</p>
      <div class="page-actions">
        <input
          v-model="searchQuery"
          type="search"
          class="input search-input"
          placeholder="Buscar por nome, e-mail, telefone ou trilha..."
          aria-label="Buscar usuários"
        />
        <button type="button" class="btn-primary" @click="openCreate">Novo usuário</button>
      </div>
    </header>

    <div v-if="loading" class="loading">Carregando...</div>
    <div v-else-if="error" class="error-msg">{{ error }}</div>
    <div v-else-if="users.length === 0" class="empty">
      Nenhum usuário cadastrado. Clique em <strong>Novo usuário</strong> para criar.
    </div>
    <div v-else class="table-wrap">
      <table class="data-table">
        <thead>
          <tr>
            <th>Nome</th>
            <th>E-mail</th>
            <th>Telefone</th>
            <th>Trilha</th>
            <th>Admin</th>
            <th>Criado em</th>
            <th class="th-actions">Ações</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(u, idx) in filteredUsers" :key="u?.id ?? `user-${idx}`">
            <td class="name-cell">{{ u?.name ?? '—' }}</td>
            <td>{{ u?.email ?? '—' }}</td>
            <td>{{ u?.phone || '—' }}</td>
            <td class="slug-cell">
              <span v-if="(u?.course_slugs?.length ?? 0) > 0">{{ (u?.course_slugs ?? []).join(', ') }}</span>
              <code v-else>{{ u?.course_slug || '—' }}</code>
            </td>
            <td>
              <span v-if="u?.is_admin" class="badge badge-admin">Admin</span>
              <span v-else class="muted">—</span>
            </td>
            <td>{{ formatDate(u?.created_at) }}</td>
            <td class="actions-cell">
              <button type="button" class="btn-secondary btn-sm" @click="openEdit(u)">Editar</button>
              <RouterLink v-if="u?.id" :to="`/admin/progresso/${u.id}`" class="btn-secondary btn-sm link-btn">
                Progresso
              </RouterLink>
              <button
                v-if="u?.id != null && u.id !== currentUserId"
                type="button"
                class="btn-danger btn-sm"
                @click="askDelete(u)"
              >
                Excluir
              </button>
              <span v-else class="self-hint" title="Não é possível excluir seu próprio usuário">—</span>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-if="searchQuery && filteredUsers.length < users.length" class="filter-hint">
        Mostrando {{ filteredUsers.length }} de {{ users.length }} usuários.
      </p>
    </div>

    <!-- Modal Criar / Editar -->
    <Teleport to="body">
      <div v-if="modalOpen" class="modal-backdrop" @click.self="closeModal">
        <div class="modal-box">
          <div class="modal-header">
            <h2>{{ modalMode === 'create' ? 'Novo usuário' : 'Editar usuário' }}</h2>
            <button type="button" class="modal-close" aria-label="Fechar" @click="closeModal">×</button>
          </div>
          <div class="modal-body">
            <div v-if="modalError" class="modal-error">{{ modalError }}</div>
            <div class="form-group">
              <label for="user-name">Nome</label>
              <input id="user-name" v-model="form.name" type="text" class="input" placeholder="Nome completo" />
            </div>
            <div class="form-group">
              <label for="user-email">E-mail</label>
              <input id="user-email" v-model="form.email" type="email" class="input" placeholder="email@exemplo.com" />
            </div>
            <div class="form-group">
              <label for="user-password">
                {{ modalMode === 'create' ? 'Senha (obrigatória)' : 'Nova senha (deixe em branco para manter)' }}
              </label>
              <input
                id="user-password"
                v-model="form.password"
                type="password"
                class="input"
                :placeholder="modalMode === 'edit' ? '••••••••' : 'Mínimo 6 caracteres'"
                autocomplete="new-password"
              />
            </div>
            <div class="form-group">
              <span class="label-block">Trilhas</span>
              <p class="form-hint">Selecione uma ou mais trilhas para o usuário.</p>
              <div class="course-checkboxes">
                <label
                  v-for="c in courses"
                  :key="c.slug"
                  class="checkbox-label"
                >
                  <input
                    v-model="form.course_slugs"
                    type="checkbox"
                    :value="c.slug"
                  />
                  {{ c.titulo || c.slug }}
                </label>
              </div>
            </div>
            <div class="form-group">
              <label for="user-phone">Telefone (opcional)</label>
              <input id="user-phone" v-model="form.phone" type="text" class="input" placeholder="ex: 5511987654321" />
            </div>
            <div v-if="modalMode === 'edit'" class="form-group form-group-check">
              <label>
                <input v-model="form.is_admin" type="checkbox" />
                Administrador
              </label>
              <span class="form-hint">Usuários admin podem acessar o painel e gerir a plataforma.</span>
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
            <h2>Excluir usuário</h2>
            <button type="button" class="modal-close" aria-label="Fechar" @click="cancelDelete">×</button>
          </div>
          <div class="modal-body">
            <div v-if="deleteError" class="modal-error">{{ deleteError }}</div>
            <p>
              Tem certeza que deseja excluir o usuário
              <strong>{{ deleteTarget.name }}</strong> ({{ deleteTarget.email }})?
              O progresso e respostas associados também serão removidos. Esta ação não pode ser desfeita.
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
.usuarios-page {
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
}

.data-table th {
  font-weight: 600;
  color: var(--k0);
  background: var(--k8);
}

.data-table tbody tr:hover {
  background: var(--k9);
}

.data-table .name-cell {
  font-weight: 500;
  color: var(--k0);
}

.slug-cell {
  font-size: 12px;
  color: var(--k4);
  background: var(--k8);
  padding: 4px 8px;
  border-radius: 6px;
}

.badge-admin {
  display: inline-block;
  padding: 2px 8px;
  font-size: 12px;
  font-weight: 600;
  color: var(--k0);
  background: var(--golddim);
  border: 1px solid var(--goldbd);
  border-radius: 6px;
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

.link-btn {
  display: inline-flex;
  align-items: center;
  text-decoration: none;
  padding: 6px 12px;
  font-size: 13px;
  border-radius: 8px;
  border: 1px solid var(--bd);
  background: var(--wh);
  color: var(--k0);
}

.link-btn:hover {
  background: var(--k8);
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

.muted {
  color: var(--k5);
}

/* Reuso dos estilos de modal/forms do AdminTrilhasView (globais ou iguais) */
.form-group-check label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  cursor: pointer;
}

.form-group-check input[type="checkbox"] {
  width: auto;
  accent-color: var(--k0);
}

.label-block {
  display: block;
  font-weight: 600;
  margin-bottom: 4px;
}

.course-checkboxes {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 200px;
  overflow-y: auto;
  padding: 8px 0;
}

.course-checkboxes .checkbox-label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  font-weight: 400;
}

.course-checkboxes input[type="checkbox"] {
  width: auto;
  accent-color: var(--k0);
}

/* Botões e formulário (mesmo padrão do AdminTrilhasView) */
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

.input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--bd);
  border-radius: 8px;
  font-size: 14px;
  font-family: inherit;
}

select.input {
  cursor: pointer;
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

.form-hint {
  display: block;
  font-size: 12px;
  color: var(--k5);
  margin-top: 4px;
}
</style>
