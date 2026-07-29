<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import {
  listCanvasProjects,
  createCanvasProject,
  deleteCanvasProject,
  type CanvasProjectSummary,
  type CanvasQuadrant,
} from '@/api/canvasProjects'

const router = useRouter()
const loading = ref(true)
const creating = ref(false)
const error = ref<string | null>(null)
const items = ref<CanvasProjectSummary[]>([])
const deleteTarget = ref<CanvasProjectSummary | null>(null)
const deleteError = ref<string | null>(null)

const QUADRANT_LABEL: Record<Exclude<CanvasQuadrant, null>, string> = {
  ganho_rapido: 'Ganho rápido',
  aposta_estrategica: 'Aposta estratégica',
  incremental: 'Incremental',
  evitar: 'Evitar',
}

function formatDate(iso: string | null): string {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString('pt-BR', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return iso
  }
}

async function refresh() {
  const res = await listCanvasProjects()
  items.value = res.items ?? []
}

async function onCreate() {
  creating.value = true
  error.value = null
  try {
    const created = await createCanvasProject('Novo projeto')
    await router.push(`/projetos/${created.id}`)
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Erro ao criar projeto.'
    creating.value = false
  }
}

function askDelete(item: CanvasProjectSummary, ev: Event) {
  ev.preventDefault()
  ev.stopPropagation()
  deleteTarget.value = item
  deleteError.value = null
}

function cancelDelete() {
  deleteTarget.value = null
  deleteError.value = null
}

async function confirmDelete() {
  if (!deleteTarget.value) return
  try {
    await deleteCanvasProject(deleteTarget.value.id)
    items.value = items.value.filter((i) => i.id !== deleteTarget.value!.id)
    cancelDelete()
  } catch (e) {
    deleteError.value = e instanceof Error ? e.message : 'Erro ao excluir.'
  }
}

onMounted(async () => {
  try {
    await refresh()
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Erro ao carregar projetos.'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="wrap">
    <div class="page-header">
      <h1 class="page-title">Projetos · Canvas de Oportunidades</h1>
      <p class="page-desc">
        Um canvas por área de negócio. Crie um projeto, abra o canvas e preencha da dor à decisão (01→08).
      </p>
    </div>

    <div v-if="loading" class="card">Carregando...</div>
    <div v-else-if="error" class="card error-msg">{{ error }}</div>

    <template v-else>
      <div class="card card-cta">
        <button type="button" class="btn-new" :disabled="creating" @click="onCreate">
          {{ creating ? 'Criando…' : '+ Novo projeto' }}
        </button>
      </div>

      <div v-if="items.length === 0" class="card card-empty">
        <p>Você ainda não tem projetos.</p>
        <button type="button" class="link-new" :disabled="creating" @click="onCreate">
          Criar primeiro projeto →
        </button>
      </div>

      <ul v-else class="list">
        <li v-for="item in items" :key="item.id" class="list-item">
          <RouterLink :to="`/projetos/${item.id}`" class="list-link">
            <div class="list-main">
              <span class="list-title">{{ item.title || 'Novo projeto' }}</span>
              <span class="list-meta">
                <template v-if="item.area_negocio">{{ item.area_negocio }} · </template>
                Atualizado {{ formatDate(item.updated_at) }}
              </span>
              <span v-if="item.quadrant" class="list-quad" :data-q="item.quadrant">
                {{ QUADRANT_LABEL[item.quadrant] }}
              </span>
            </div>
            <span class="list-arrow">Abrir canvas →</span>
          </RouterLink>
          <button
            type="button"
            class="btn-del"
            title="Excluir projeto"
            @click="askDelete(item, $event)"
          >
            Excluir
          </button>
        </li>
      </ul>
    </template>

    <Teleport to="body">
      <div v-if="deleteTarget" class="modal-backdrop" @click.self="cancelDelete">
        <div class="modal" role="dialog" aria-modal="true">
          <h2 class="modal-title">Excluir projeto?</h2>
          <p class="modal-text">
            Remover <strong>{{ deleteTarget.title }}</strong> e o canvas preenchido. Esta ação não pode ser desfeita.
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
.wrap {
  max-width: 860px;
  margin: 0 auto;
  padding: 28px 20px 60px;
}
.page-header {
  margin-bottom: 24px;
}
.page-title {
  font-family: var(--serif);
  font-size: 28px;
  color: var(--k0);
  margin-bottom: 6px;
}
.page-desc {
  font-size: 14px;
  color: var(--k5);
  line-height: 1.55;
  max-width: 52ch;
}
.card {
  background: var(--wh);
  border: 1px solid var(--bd);
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 16px;
}
.error-msg {
  color: #8f2b2b;
}
.card-cta {
  display: flex;
  justify-content: flex-start;
}
.btn-new {
  display: inline-flex;
  align-items: center;
  padding: 10px 18px;
  background: var(--k0);
  color: var(--wh);
  border: none;
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
}
.btn-new:disabled {
  opacity: 0.6;
  cursor: wait;
}
.card-empty {
  text-align: center;
  color: var(--k5);
  padding: 36px 20px;
}
.link-new {
  margin-top: 12px;
  background: none;
  border: none;
  color: var(--k0);
  text-decoration: underline;
  cursor: pointer;
  font-size: 14px;
}
.list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.list-item {
  display: flex;
  align-items: stretch;
  gap: 8px;
  background: var(--wh);
  border: 1px solid var(--bd);
  border-radius: 12px;
  overflow: hidden;
}
.list-link {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 16px 18px;
  text-decoration: none;
  color: inherit;
  min-width: 0;
}
.list-link:hover {
  background: rgba(0, 0, 0, 0.02);
}
.list-main {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}
.list-title {
  font-weight: 600;
  font-size: 16px;
  color: var(--k0);
}
.list-meta {
  font-size: 12px;
  color: var(--k5);
}
.list-quad {
  display: inline-flex;
  width: fit-content;
  margin-top: 4px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  padding: 3px 8px;
  border-radius: 999px;
  border: 1px solid var(--bd);
  color: var(--k3);
}
.list-quad[data-q='ganho_rapido'] {
  background: #e8f0e7;
  border-color: #bbd3b7;
  color: #2f6e4a;
}
.list-quad[data-q='aposta_estrategica'] {
  background: #f3e7cc;
  border-color: #e3ce9c;
  color: #c48a26;
}
.list-quad[data-q='incremental'] {
  background: #e4ecee;
  border-color: #cbd8db;
  color: #5b7a86;
}
.list-quad[data-q='evitar'] {
  background: #f1e1dd;
  border-color: #ddbcb4;
  color: #9c3b2e;
}
.list-arrow {
  font-size: 13px;
  color: var(--k5);
  white-space: nowrap;
}
.btn-del {
  border: none;
  background: transparent;
  color: #8f2b2b;
  padding: 0 14px;
  font-size: 12px;
  cursor: pointer;
  border-left: 1px solid var(--bd);
}
.btn-del:hover {
  background: #faf2f1;
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
  padding: 24px;
  width: min(420px, 100%);
}
.modal-title {
  font-family: var(--serif);
  font-size: 20px;
  margin-bottom: 10px;
}
.modal-text {
  font-size: 14px;
  color: var(--k3);
  margin-bottom: 16px;
}
.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
.btn-secondary,
.btn-danger {
  font-size: 13px;
  padding: 8px 14px;
  border-radius: 6px;
  cursor: pointer;
  border: none;
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
</style>
