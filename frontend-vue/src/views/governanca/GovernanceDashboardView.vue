<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ApiError } from '@/api/client'
import {
  getMetrics,
  createEvidenceSnapshot,
  getProfundidade,
  recalcularProfundidade,
  confirmarProfundidade,
} from '@/api/governance'
import type { MetricsResponse, ProfundidadeSettings, Profundidade, EvidenceMetrics } from '@/api/governance'

const loading = ref(true)
const error = ref<string | null>(null)
const metrics = ref<MetricsResponse | null>(null)
const profundidade = ref<ProfundidadeSettings | null>(null)

const PROFUNDIDADE_LABEL: Record<Profundidade, string> = {
  fundacao: 'Fundação',
  intermediario: 'Intermediário',
  completo: 'Completo',
}
const PROFUNDIDADE_DESC: Record<Profundidade, string> = {
  fundacao: 'Habilita apenas Inventário de Sistemas e Política de uso de IA.',
  intermediario: 'Também habilita Avaliação de Risco/AIA e Comitê de Governança.',
  completo: 'Os 4 pilares completos, com métricas de evidência e teste de auditabilidade.',
}

type NumericMetricKey = Exclude<keyof EvidenceMetrics, 'periodo'>

const INDICATORS: { key: NumericMetricKey; label: string; suffix: string }[] = [
  { key: 'pct_sistemas_inventariados', label: 'Sistemas inventariados', suffix: '%' },
  { key: 'tempo_medio_registro_dias', label: 'Tempo médio de registro', suffix: 'dias' },
  { key: 'pct_sistemas_classificados', label: 'Sistemas classificados', suffix: '%' },
  { key: 'lead_time_avaliacao_dias', label: 'Lead time de avaliação', suffix: 'dias' },
  { key: 'pct_acoes_criticas_com_hitl', label: 'Ações críticas com HITL', suffix: '%' },
  { key: 'tempo_reconstrucao_decisao_horas', label: 'Tempo de reconstrução de decisão', suffix: 'h' },
  { key: 'pct_fichas_atualizadas_6m', label: 'Fichas atualizadas (6m)', suffix: '%' },
  { key: 'bloqueios_guardrail_periodo', label: 'Bloqueios de guardrail no período', suffix: '' },
]

function fmt(key: NumericMetricKey, value: number): string {
  if (key.startsWith('pct_')) return `${Math.round(value * 100)}%`
  return String(value)
}

const recalculando = ref(false)
const confirmando = ref(false)
const settingsError = ref<string | null>(null)

async function onRecalcular() {
  recalculando.value = true
  settingsError.value = null
  try {
    profundidade.value = await recalcularProfundidade()
  } catch (e) {
    settingsError.value = e instanceof ApiError ? e.message : e instanceof Error ? e.message : 'Erro ao recalcular.'
  } finally {
    recalculando.value = false
  }
}

async function onConfirmar() {
  confirmando.value = true
  settingsError.value = null
  try {
    profundidade.value = await confirmarProfundidade()
  } catch (e) {
    settingsError.value = e instanceof ApiError ? e.message : e instanceof Error ? e.message : 'Erro ao confirmar.'
  } finally {
    confirmando.value = false
  }
}

// ——— novo snapshot ———

const showSnapshotForm = ref(false)
const snapshotForm = ref({
  pct_sistemas_inventariados: 0,
  tempo_medio_registro_dias: 0,
  pct_sistemas_classificados: 0,
  lead_time_avaliacao_dias: 0,
  pct_acoes_criticas_com_hitl: 0,
  tempo_reconstrucao_decisao_horas: 0,
  pct_fichas_atualizadas_6m: 0,
  bloqueios_guardrail_periodo: 0,
  periodo_inicio: '',
  periodo_fim: '',
})
const snapshotSaving = ref(false)
const snapshotError = ref<string | null>(null)

async function submitSnapshot() {
  snapshotSaving.value = true
  snapshotError.value = null
  try {
    const f = snapshotForm.value
    await createEvidenceSnapshot({
      pct_sistemas_inventariados: f.pct_sistemas_inventariados,
      tempo_medio_registro_dias: f.tempo_medio_registro_dias,
      pct_sistemas_classificados: f.pct_sistemas_classificados,
      lead_time_avaliacao_dias: f.lead_time_avaliacao_dias,
      pct_acoes_criticas_com_hitl: f.pct_acoes_criticas_com_hitl,
      tempo_reconstrucao_decisao_horas: f.tempo_reconstrucao_decisao_horas,
      pct_fichas_atualizadas_6m: f.pct_fichas_atualizadas_6m,
      bloqueios_guardrail_periodo: f.bloqueios_guardrail_periodo,
      periodo: { inicio: f.periodo_inicio, fim: f.periodo_fim },
    })
    metrics.value = await getMetrics()
    showSnapshotForm.value = false
  } catch (e) {
    snapshotError.value = e instanceof ApiError ? e.message : e instanceof Error ? e.message : 'Erro ao publicar snapshot.'
  } finally {
    snapshotSaving.value = false
  }
}

onMounted(async () => {
  try {
    const [m, p] = await Promise.all([getMetrics(), getProfundidade()])
    metrics.value = m
    profundidade.value = p
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : e instanceof Error ? e.message : 'Erro ao carregar dashboard.'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="dashboard-page">
    <header class="page-header">
      <nav class="subnav">
        <RouterLink to="/governanca/inventario" class="subnav-link">Inventário</RouterLink>
        <RouterLink to="/governanca/dashboard" class="subnav-link active">Dashboard</RouterLink>
      </nav>
      <h1 class="page-title">Governança de IA · Dashboard</h1>
      <p class="page-sub">Indicadores de evidência dos 4 pilares e profundidade de implantação vigente.</p>
    </header>

    <div v-if="loading" class="loading">Carregando...</div>
    <div v-else-if="error" class="error-msg">{{ error }}</div>
    <template v-else>
      <section v-if="profundidade" class="card profundidade-card">
        <h2 class="section-title">Profundidade de implantação</h2>
        <div v-if="settingsError" class="error-msg">{{ settingsError }}</div>
        <div class="profundidade-row">
          <span class="badge-profundidade">{{ PROFUNDIDADE_LABEL[profundidade.value] }}</span>
          <p class="profundidade-desc">{{ PROFUNDIDADE_DESC[profundidade.value] }}</p>
        </div>
        <div
          v-if="profundidade.suggested_value && profundidade.suggested_value !== profundidade.value"
          class="suggestion-banner"
        >
          Sugestão pendente: <strong>{{ PROFUNDIDADE_LABEL[profundidade.suggested_value] }}</strong>
          (é um rebaixamento — precisa de confirmação humana).
          <button type="button" class="btn-secondary" :disabled="confirmando" @click="onConfirmar">
            {{ confirmando ? 'Confirmando…' : 'Confirmar' }}
          </button>
        </div>
        <button type="button" class="btn-secondary" :disabled="recalculando" @click="onRecalcular">
          {{ recalculando ? 'Recalculando…' : 'Recalcular a partir da última maturidade' }}
        </button>
      </section>

      <section class="card">
        <div class="metrics-header">
          <h2 class="section-title">Evidências</h2>
          <button type="button" class="link-btn" @click="showSnapshotForm = !showSnapshotForm">
            {{ showSnapshotForm ? 'Cancelar' : 'Gerar novo snapshot' }}
          </button>
        </div>

        <p v-if="!metrics?.published" class="muted">Nenhum snapshot de evidências publicado ainda.</p>
        <div v-else class="metrics-grid">
          <div v-for="ind in INDICATORS" :key="ind.key" class="metric-tile">
            <span class="metric-value">{{ fmt(ind.key, metrics.metrics![ind.key]) }}</span>
            <span class="metric-label">{{ ind.label }}</span>
          </div>
        </div>
        <p v-if="metrics?.published_at" class="muted metrics-published-at">
          Publicado em {{ new Date(metrics.published_at).toLocaleDateString('pt-BR') }}
        </p>

        <form v-if="showSnapshotForm" class="snapshot-form" @submit.prevent="submitSnapshot">
          <div v-if="snapshotError" class="error-msg">{{ snapshotError }}</div>
          <div class="form-grid">
            <div class="form-group">
              <label>Sistemas inventariados (0–1)</label>
              <input v-model.number="snapshotForm.pct_sistemas_inventariados" type="number" step="0.01" min="0" max="1" class="input" />
            </div>
            <div class="form-group">
              <label>Tempo médio de registro (dias)</label>
              <input v-model.number="snapshotForm.tempo_medio_registro_dias" type="number" step="0.1" min="0" class="input" />
            </div>
            <div class="form-group">
              <label>Sistemas classificados (0–1)</label>
              <input v-model.number="snapshotForm.pct_sistemas_classificados" type="number" step="0.01" min="0" max="1" class="input" />
            </div>
            <div class="form-group">
              <label>Lead time de avaliação (dias)</label>
              <input v-model.number="snapshotForm.lead_time_avaliacao_dias" type="number" step="0.1" min="0" class="input" />
            </div>
            <div class="form-group">
              <label>Ações críticas com HITL (0–1)</label>
              <input v-model.number="snapshotForm.pct_acoes_criticas_com_hitl" type="number" step="0.01" min="0" max="1" class="input" />
            </div>
            <div class="form-group">
              <label>Tempo de reconstrução de decisão (horas)</label>
              <input v-model.number="snapshotForm.tempo_reconstrucao_decisao_horas" type="number" step="0.1" min="0" class="input" />
            </div>
            <div class="form-group">
              <label>Fichas atualizadas em 6m (0–1)</label>
              <input v-model.number="snapshotForm.pct_fichas_atualizadas_6m" type="number" step="0.01" min="0" max="1" class="input" />
            </div>
            <div class="form-group">
              <label>Bloqueios de guardrail no período</label>
              <input v-model.number="snapshotForm.bloqueios_guardrail_periodo" type="number" step="1" min="0" class="input" />
            </div>
            <div class="form-group">
              <label>Período — início</label>
              <input v-model="snapshotForm.periodo_inicio" type="date" class="input" />
            </div>
            <div class="form-group">
              <label>Período — fim</label>
              <input v-model="snapshotForm.periodo_fim" type="date" class="input" />
            </div>
          </div>
          <button type="submit" class="btn-primary" :disabled="snapshotSaving">
            {{ snapshotSaving ? 'Publicando…' : 'Publicar snapshot' }}
          </button>
        </form>
      </section>
    </template>
  </div>
</template>

<style scoped>
.dashboard-page {
  max-width: 900px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 24px;
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

.subnav-link.active {
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
}

.loading,
.error-msg {
  padding: 40px 0;
  color: var(--k5);
}

.error-msg {
  color: #8f2b2b;
}

.card {
  background: var(--wh);
  border: 1px solid var(--bd);
  border-radius: 12px;
  padding: 24px;
  margin-bottom: 24px;
}

.section-title {
  font-family: var(--serif);
  font-size: 18px;
  color: var(--k0);
  margin: 0 0 16px;
}

.profundidade-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.badge-profundidade {
  padding: 4px 14px;
  font-size: 13px;
  font-weight: 700;
  color: var(--k0);
  background: var(--golddim);
  border: 1px solid var(--goldbd);
  border-radius: 999px;
}

.profundidade-desc {
  font-size: 14px;
  color: var(--k4);
  margin: 0;
}

.suggestion-banner {
  padding: 12px 14px;
  margin-bottom: 16px;
  background: #fbf3e1;
  border: 1px solid #e8cf9a;
  color: #7a5a17;
  border-radius: 8px;
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.metrics-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 16px;
  margin-top: 8px;
}

.metric-tile {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 14px 16px;
  background: var(--k9);
  border-radius: 8px;
}

.metric-value {
  font-family: var(--serif);
  font-size: 22px;
  color: var(--k0);
}

.metric-label {
  font-size: 12px;
  color: var(--k5);
}

.metrics-published-at {
  margin-top: 12px;
  font-size: 12px;
}

.muted {
  color: var(--k5);
}

.snapshot-form {
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid var(--bd2);
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 14px;
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  font-size: 12px;
  font-weight: 600;
  color: var(--k0);
  margin-bottom: 4px;
}

.input {
  width: 100%;
  padding: 8px 10px;
  border: 1px solid var(--bd);
  border-radius: 8px;
  font-size: 13px;
  font-family: inherit;
}

.link-btn {
  background: none;
  border: none;
  color: var(--gold);
  cursor: pointer;
  font-size: 13px;
  padding: 0;
}

.btn-primary,
.btn-secondary {
  padding: 10px 18px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  border: 1px solid transparent;
  cursor: pointer;
}

.btn-primary {
  background: var(--k0);
  color: var(--wh);
}

.btn-primary:disabled,
.btn-secondary:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.btn-secondary {
  background: var(--wh);
  color: var(--k0);
  border-color: var(--bd);
}
</style>
