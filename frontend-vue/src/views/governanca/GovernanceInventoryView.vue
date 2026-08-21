<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { listAiSystems, createAiSystem } from '@/api/governance'
import type { AiSystem, SistemaStatus, RiscoNivel, OrigemIA } from '@/api/governance'
import PageHeader from '@/components/ui/PageHeader.vue'
import StateBlock from '@/components/ui/StateBlock.vue'
import AppButton from '@/components/ui/AppButton.vue'

const router = useRouter()

const loading = ref(true)
const error = ref<string | null>(null)
const creating = ref(false)
const systems = ref<AiSystem[]>([])

const filterStatus = ref('')
const filterRisco = ref('')
const filterOrigem = ref('')
const filterArea = ref('')

const STATUS_LABEL: Record<SistemaStatus, string> = {
  rascunho: 'Rascunho',
  aguardando_avaliacao: 'Aguardando avaliação',
  avaliado: 'Avaliado',
  em_gate: 'Em gate',
  producao: 'Em produção',
  reavaliacao_pendente: 'Reavaliação pendente',
  descontinuado: 'Descontinuado',
}

const RISCO_LABEL: Record<RiscoNivel, string> = {
  baixo: 'Baixo',
  medio: 'Médio',
  alto: 'Alto',
  critico: 'Crítico',
}

const ORIGEM_LABEL: Record<OrigemIA, string> = {
  interno: 'Interno',
  oss_customizado: 'OSS customizado',
  api_terceiros: 'API de terceiros',
}

const filtered = computed(() => {
  return systems.value.filter((s) => {
    if (filterStatus.value && s.status !== filterStatus.value) return false
    if (filterRisco.value && s.classificacao_risco.nivel !== filterRisco.value) return false
    if (filterOrigem.value && s.origem_ia !== filterOrigem.value) return false
    if (filterArea.value && !(s.area_negocio || '').toLowerCase().includes(filterArea.value.toLowerCase())) {
      return false
    }
    return true
  })
})

async function onCreate() {
  creating.value = true
  error.value = null
  try {
    const created = await createAiSystem({ nome: 'Novo sistema de IA' })
    router.push(`/governanca/sistemas/${created.id}`)
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Erro ao registrar sistema.'
  } finally {
    creating.value = false
  }
}

onMounted(async () => {
  try {
    const res = await listAiSystems()
    systems.value = res.items
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Erro ao carregar inventário.'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="inventory-page">
    <nav class="subnav">
      <RouterLink to="/governanca/inventario" class="subnav-link active">Inventário</RouterLink>
      <RouterLink to="/governanca/dashboard" class="subnav-link">Dashboard</RouterLink>
    </nav>
    <PageHeader title="Inventário de Sistemas de IA" subtitle="Registro vivo de todo sistema de IA da organização — de onde veio, que dados usa, qual risco, quem é dono.">
      <template #actions>
        <AppButton variant="primary" :disabled="creating" @click="onCreate">
          {{ creating ? 'Registrando…' : 'Registrar sistema' }}
        </AppButton>
      </template>
    </PageHeader>
    <div class="page-actions">
      <select v-model="filterStatus" class="input filter-select">
        <option value="">Todos os status</option>
        <option v-for="(label, value) in STATUS_LABEL" :key="value" :value="value">{{ label }}</option>
      </select>
      <select v-model="filterRisco" class="input filter-select">
        <option value="">Todos os riscos</option>
        <option v-for="(label, value) in RISCO_LABEL" :key="value" :value="value">{{ label }}</option>
      </select>
      <select v-model="filterOrigem" class="input filter-select">
        <option value="">Toda origem</option>
        <option v-for="(label, value) in ORIGEM_LABEL" :key="value" :value="value">{{ label }}</option>
      </select>
      <input v-model="filterArea" type="search" class="input filter-search" placeholder="Buscar por área..." />
    </div>

    <StateBlock v-if="loading" state="loading" />
    <StateBlock v-else-if="error" state="error" :message="error" />
    <div v-else-if="systems.length === 0" class="empty">
      Nenhum sistema de IA registrado.
      <button type="button" class="link-btn" @click="onCreate">Registrar o primeiro →</button>
    </div>
    <div v-else class="table-wrap">
      <table class="data-table">
        <thead>
          <tr>
            <th>Nome</th>
            <th>Área</th>
            <th>Origem</th>
            <th>Status</th>
            <th>Risco</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="s in filtered"
            :key="s.id"
            class="row-link"
            @click="router.push(`/governanca/sistemas/${s.id}`)"
          >
            <td class="name-cell">{{ s.nome }}</td>
            <td>{{ s.area_negocio || '—' }}</td>
            <td>{{ s.origem_ia ? ORIGEM_LABEL[s.origem_ia] : '—' }}</td>
            <td><span class="badge-status">{{ STATUS_LABEL[s.status] }}</span></td>
            <td>
              <span v-if="s.classificacao_risco.nivel" class="badge-risco" :data-nivel="s.classificacao_risco.nivel">
                {{ RISCO_LABEL[s.classificacao_risco.nivel] }}
              </span>
              <span v-else class="muted">Não classificado</span>
            </td>
            <td class="origin-cell">
              <span v-if="s.canvas_project_id" class="badge-origin" title="Criado a partir do portfólio de oportunidades">
                Veio do portfólio
              </span>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-if="filtered.length < systems.length" class="filter-hint">
        Mostrando {{ filtered.length }} de {{ systems.length }} sistemas.
      </p>
    </div>
  </div>
</template>

<style scoped>
.inventory-page {
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 28px;
}

.subnav {
  display: flex;
  gap: 16px;
  margin-bottom: 12px;
}

.subnav-link {
  font-size: 13px;
  font-weight: 600;
  color: var(--k5);
  text-decoration: none;
}

.subnav-link.active,
.subnav-link.router-link-exact-active {
  color: var(--k0);
  border-bottom: 2px solid var(--gold);
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
  margin-bottom: 24px;
}

.filter-select {
  width: auto;
  min-width: 160px;
}

.filter-search {
  max-width: 220px;
  min-width: 160px;
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

.link-btn {
  background: none;
  border: none;
  color: var(--gold);
  cursor: pointer;
  font: inherit;
  padding: 0;
  margin-left: 4px;
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

.row-link {
  cursor: pointer;
}

.row-link:hover {
  background: var(--k9);
}

.name-cell {
  font-weight: 500;
  color: var(--k0);
}

.muted {
  color: var(--k5);
}

.badge-status {
  display: inline-block;
  padding: 2px 8px;
  font-size: 12px;
  font-weight: 500;
  color: var(--k3);
  background: var(--k8);
  border: 1px solid var(--bd2);
  border-radius: var(--r-sm);
}

.badge-risco {
  display: inline-block;
  padding: 2px 10px;
  font-size: 12px;
  font-weight: 600;
  border-radius: var(--r-pill);
  border: 1px solid transparent;
}

.badge-risco[data-nivel='baixo'] {
  background: #e8f0e7;
  border-color: #bbd3b7;
  color: #2f6e4a;
}

.badge-risco[data-nivel='medio'] {
  background: #fbf3e1;
  border-color: #e8cf9a;
  color: #c48a26;
}

.badge-risco[data-nivel='alto'] {
  background: #fdecec;
  border-color: #f3b8b8;
  color: #8f2b2b;
}

.badge-risco[data-nivel='critico'] {
  background: #8f2b2b;
  border-color: #6e1f1f;
  color: #fff;
}

.badge-origin {
  display: inline-block;
  padding: 2px 8px;
  font-size: 11px;
  font-weight: 600;
  color: var(--k0);
  background: var(--golddim);
  border: 1px solid var(--goldbd);
  border-radius: var(--r-sm);
  white-space: nowrap;
}

.filter-hint {
  padding: 12px 16px;
  font-size: 13px;
  color: var(--k5);
  border-top: 1px solid var(--bd2);
}

.input {
  padding: 10px 12px;
  border: 1px solid var(--bd);
  border-radius: var(--r-md);
  font-size: 14px;
  font-family: inherit;
}

select.input {
  cursor: pointer;
}

.btn-primary {
  padding: 10px 18px;
  border-radius: var(--r-md);
  font-size: 14px;
  font-weight: 500;
  border: 1px solid transparent;
  background: var(--k0);
  color: var(--wh);
  transition: background 0.15s ease;
}

.btn-primary:hover:not(:disabled) {
  background: #132d52;
}

.btn-primary:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}
</style>
