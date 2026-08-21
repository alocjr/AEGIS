<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  listOkrCycles,
  createOkrCycle,
  deleteOkrCycle,
  type OkrCycleSummary,
  type OkrCycleTipo,
} from '@/api/okrs'
import PageHeader from '@/components/ui/PageHeader.vue'
import StateBlock from '@/components/ui/StateBlock.vue'
import AppModal from '@/components/ui/AppModal.vue'
import AppButton from '@/components/ui/AppButton.vue'

const router = useRouter()
const loading = ref(true)
const error = ref<string | null>(null)
const items = ref<OkrCycleSummary[]>([])

const STATUS_LABEL: Record<OkrCycleSummary['status'], string> = {
  planejamento: 'Em planejamento',
  ativo: 'Ativo',
  encerrado: 'Encerrado',
}

const newForm = ref<{ tipo: OkrCycleTipo; ano: number; trimestre: number }>({
  tipo: 'trimestre',
  ano: new Date().getFullYear(),
  trimestre: Math.floor(new Date().getMonth() / 3) + 1,
})
const creating = ref(false)
const createError = ref<string | null>(null)

const sortedItems = computed(() =>
  [...items.value].sort((a, b) => {
    if (a.status !== b.status) {
      const order = { ativo: 0, planejamento: 1, encerrado: 2 }
      return order[a.status] - order[b.status]
    }
    return (b.ano - a.ano) || ((b.trimestre ?? 0) - (a.trimestre ?? 0))
  })
)

function formatDate(iso: string | null): string {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleDateString('pt-BR', { day: '2-digit', month: 'short', year: 'numeric' })
  } catch {
    return iso
  }
}

async function refresh() {
  const res = await listOkrCycles()
  items.value = res.items ?? []
}

async function onCreate() {
  creating.value = true
  createError.value = null
  try {
    const created = await createOkrCycle({
      tipo: newForm.value.tipo,
      ano: newForm.value.ano,
      trimestre: newForm.value.tipo === 'trimestre' ? newForm.value.trimestre : undefined,
    })
    await router.push(`/okrs/${created.id}`)
  } catch (e) {
    createError.value = e instanceof Error ? e.message : 'Erro ao criar ciclo.'
    creating.value = false
  }
}

const deleteTarget = ref<OkrCycleSummary | null>(null)
const deleteError = ref<string | null>(null)

function askDelete(item: OkrCycleSummary, ev: Event) {
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
    await deleteOkrCycle(deleteTarget.value.id)
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
    error.value = e instanceof Error ? e.message : 'Erro ao carregar ciclos OKR.'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="wrap">
    <PageHeader
      title="OKR"
      subtitle="Objetivos nascem das iniciativas TOWS da SWOT; os Resultados-Chave são o que os projetos do AI Canvas endereçam. Ative um ciclo para que ele apareça no Mapa Estratégico."
    />

    <StateBlock v-if="loading" state="loading" />
    <StateBlock v-else-if="error" state="error" :message="error" />

    <template v-else>
      <div class="card card-new">
        <h2 class="card-new-title">Novo ciclo</h2>
        <div class="new-row">
          <label class="new-field">
            <span>Tipo</span>
            <select v-model="newForm.tipo">
              <option value="trimestre">Trimestre</option>
              <option value="ano">Ano</option>
            </select>
          </label>
          <label class="new-field">
            <span>Ano</span>
            <input v-model.number="newForm.ano" type="number" min="2020" max="2100" />
          </label>
          <label v-if="newForm.tipo === 'trimestre'" class="new-field">
            <span>Trimestre</span>
            <select v-model.number="newForm.trimestre">
              <option :value="1">Q1</option>
              <option :value="2">Q2</option>
              <option :value="3">Q3</option>
              <option :value="4">Q4</option>
            </select>
          </label>
          <button type="button" class="btn-new" :disabled="creating" @click="onCreate">
            {{ creating ? 'Criando…' : '+ Criar ciclo' }}
          </button>
        </div>
        <p v-if="createError" class="error-msg">{{ createError }}</p>
      </div>

      <div v-if="items.length === 0" class="card card-empty">
        <p>Nenhum ciclo OKR ainda. Crie o primeiro acima.</p>
      </div>

      <ul v-else class="list">
        <li v-for="item in sortedItems" :key="item.id" class="list-item">
          <RouterLink :to="`/okrs/${item.id}`" class="list-link">
            <div class="list-main">
              <div class="list-head">
                <span class="list-title">{{ item.label }}</span>
                <span class="list-status" :data-status="item.status">{{ STATUS_LABEL[item.status] }}</span>
              </div>
              <div class="list-meta-row">
                <span>{{ item.objectives_count }} objetivo{{ item.objectives_count === 1 ? '' : 's' }}</span>
                <span>{{ item.key_results_count }} resultado{{ item.key_results_count === 1 ? '-chave' : 's-chave' }}</span>
                <span v-if="item.drafts_count" class="list-drafts">
                  {{ item.drafts_count }} rascunho{{ item.drafts_count === 1 ? '' : 's' }}
                </span>
                <span>Atualizado {{ formatDate(item.updated_at) }}</span>
              </div>
              <div v-if="item.progress_pct != null" class="progress-bar">
                <div class="progress-fill" :style="{ width: `${item.progress_pct}%` }" />
                <span class="progress-label">{{ item.progress_pct.toFixed(0) }}%</span>
              </div>
            </div>
            <span class="list-arrow">Abrir →</span>
          </RouterLink>
          <div class="list-actions">
            <button type="button" class="btn-del" title="Excluir ciclo" @click="askDelete(item, $event)">
              Excluir
            </button>
          </div>
        </li>
      </ul>
    </template>

    <AppModal :open="!!deleteTarget" title="Excluir ciclo?" size="sm" @close="cancelDelete">
      <p class="modal-text">
        Remover <strong>{{ deleteTarget?.label }}</strong> e todos os seus Objectives/Key Results.
        Esta ação não pode ser desfeita.
      </p>
      <p v-if="deleteError" class="error-msg">{{ deleteError }}</p>
      <template #footer>
        <AppButton variant="secondary" @click="cancelDelete">Cancelar</AppButton>
        <AppButton variant="danger" @click="confirmDelete">Excluir</AppButton>
      </template>
    </AppModal>
  </div>
</template>

<style scoped>
.wrap {
  max-width: var(--w-read);
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
  max-width: 62ch;
}
.card {
  background: var(--wh);
  border: 1px solid var(--bd);
  border-radius: var(--r-lg);
  padding: 20px;
  margin-bottom: 16px;
}
.error-msg {
  color: #8f2b2b;
}
.card-new-title {
  font-family: var(--serif);
  font-size: 18px;
  color: var(--k0);
  margin: 0 0 12px;
}
.new-row {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: 12px;
}
.new-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
  color: var(--k5);
}
.new-field select,
.new-field input {
  padding: 8px 10px;
  border: 1px solid var(--bd);
  border-radius: var(--r-sm);
  font-size: 14px;
  color: var(--k0);
  background: var(--wh);
  min-width: 100px;
}
.btn-new {
  display: inline-flex;
  align-items: center;
  padding: 10px 18px;
  background: var(--k0);
  color: var(--wh);
  border: none;
  border-radius: var(--r-md);
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
  border-radius: var(--r-lg);
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
  gap: 8px;
  min-width: 0;
  flex: 1;
}
.list-head {
  display: flex;
  align-items: center;
  gap: 10px;
}
.list-title {
  font-weight: 600;
  font-size: 16px;
  color: var(--k0);
}
.list-status {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  padding: 3px 8px;
  border-radius: var(--r-pill);
  border: 1px solid var(--bd);
  color: var(--k4);
}
.list-status[data-status='ativo'] {
  background: #e8f0e7;
  border-color: #bbd3b7;
  color: #2f6e4a;
}
.list-status[data-status='encerrado'] {
  background: var(--k9);
  color: var(--k5);
}
.list-meta-row {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 14px;
  font-size: 12px;
  color: var(--k5);
}
.list-drafts {
  color: var(--warn);
}
.progress-bar {
  position: relative;
  height: 8px;
  background: var(--k9);
  border-radius: var(--r-pill);
  overflow: hidden;
  max-width: 320px;
}
.progress-fill {
  height: 100%;
  background: var(--gold, #c48a26);
  border-radius: var(--r-pill);
}
.progress-label {
  position: absolute;
  right: 0;
  top: -18px;
  font-size: 11px;
  color: var(--k5);
}
.list-arrow {
  font-size: 13px;
  color: var(--k5);
  white-space: nowrap;
}
.list-actions {
  display: flex;
  align-items: center;
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
  border-radius: var(--r-lg);
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
  border-radius: var(--r-sm);
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

@media (max-width: 640px) {
  .list-link {
    flex-direction: column;
    align-items: flex-start;
  }
  .list-arrow {
    display: none;
  }
}
</style>
