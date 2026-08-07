<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ANALYTICS_RANGES, fetchResourceAccessReport } from '@/api/admin'
import type { ResourceAccessCategory, ResourceAccessItem, ResourceAccessReport } from '@/api/admin'

const RANGE_LABELS: Record<number, string> = {
  7: '7 dias',
  30: '30 dias',
  90: '90 dias',
  365: '12 meses',
}

const loading = ref(true)
const error = ref<string | null>(null)
const report = ref<ResourceAccessReport | null>(null)
const days = ref<number>(30)

const numberFmt = new Intl.NumberFormat('pt-BR')

function formatNumber(value: number): string {
  return numberFmt.format(value)
}

function formatLastAccess(iso: string | null): string {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleDateString('pt-BR', {
      day: '2-digit',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return '—'
  }
}

interface ResourceGroup {
  name: string
  events: number
  items: ResourceAccessItem[]
}

interface Section {
  key: string
  label: string
  events: number
  /** Categoria com um grupo só vira tabela única: repetir o cabeçalho "Materiais gratuitos"
   * dentro do bloco "Materiais gratuitos" não informa nada. */
  showGroupNames: boolean
  /** Maior contagem da categoria — referência das barras, para comparar dentro do bloco. */
  max: number
  groups: ResourceGroup[]
}

const sections = computed<Section[]>(() =>
  (report.value?.categories ?? []).map((category: ResourceAccessCategory) => {
    const byName = new Map<string, ResourceAccessItem[]>()
    for (const item of category.resources) {
      const bucket = byName.get(item.group)
      if (bucket) bucket.push(item)
      else byName.set(item.group, [item])
    }
    const groups: ResourceGroup[] = [...byName.entries()].map(([name, items]) => ({
      name,
      items,
      events: items.reduce((acc, item) => acc + item.events, 0),
    }))
    groups.sort((a, b) => b.events - a.events || a.name.localeCompare(b.name))
    return {
      key: category.key,
      label: category.label,
      events: category.events,
      showGroupNames: groups.length > 1,
      max: Math.max(...category.resources.map((r) => r.events), 0),
      groups,
    }
  })
)

function barWidth(item: ResourceAccessItem, max: number): string {
  if (max <= 0) return '0%'
  return `${Math.max(2, Math.round((item.events / max) * 100))}%`
}

/** Série diária completa: o backend só devolve dias com acesso, e um gráfico com buracos
 * mentiria sobre o ritmo de uso. As datas são montadas em UTC porque é assim que o backend
 * fecha o dia — usar o fuso local faria o dia corrente sumir do gráfico à noite no Brasil. */
const dailySeries = computed<{ day: string; events: number }[]>(() => {
  const data = report.value
  if (!data) return []
  const counts = new Map(data.daily.map((d) => [d.day, d.events]))
  const series: { day: string; events: number }[] = []
  const cursor = new Date(data.since)
  const end = new Date(data.generated_at)
  cursor.setUTCHours(0, 0, 0, 0)
  end.setUTCHours(0, 0, 0, 0)
  while (cursor <= end) {
    const key = cursor.toISOString().slice(0, 10)
    series.push({ day: key, events: counts.get(key) ?? 0 })
    cursor.setUTCDate(cursor.getUTCDate() + 1)
  }
  return series
})

const dailyMax = computed(() => Math.max(...dailySeries.value.map((d) => d.events), 1))

function dayTooltip(entry: { day: string; events: number }): string {
  const [year, month, day] = entry.day.split('-')
  return `${day}/${month}/${year} · ${formatNumber(entry.events)} acessos`
}

async function load() {
  loading.value = true
  error.value = null
  try {
    report.value = await fetchResourceAccessReport(days.value)
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Erro ao carregar as métricas de acesso.'
  } finally {
    loading.value = false
  }
}

watch(days, load, { immediate: true })
</script>

<template>
  <div class="analytics">
    <header class="analytics-head">
      <div>
        <h1 class="analytics-title">Acessos</h1>
        <p class="analytics-sub">Quantas vezes cada recurso da plataforma foi aberto</p>
      </div>
      <div class="range-picker" role="group" aria-label="Período">
        <button
          v-for="range in ANALYTICS_RANGES"
          :key="range"
          type="button"
          class="range-btn"
          :class="{ active: days === range }"
          @click="days = range"
        >
          {{ RANGE_LABELS[range] }}
        </button>
      </div>
    </header>

    <div v-if="loading" class="loading">Carregando...</div>
    <div v-else-if="error" class="error-msg">{{ error }}</div>

    <template v-else-if="report">
      <div class="kpi-grid">
        <article class="kpi">
          <span class="kpi-label">Acessos</span>
          <strong class="kpi-value">{{ formatNumber(report.totals.events) }}</strong>
        </article>
        <article class="kpi">
          <span class="kpi-label">Usuários identificados</span>
          <strong class="kpi-value">{{ formatNumber(report.totals.unique_users) }}</strong>
        </article>
        <article class="kpi">
          <span class="kpi-label">Visitantes únicos</span>
          <strong class="kpi-value">{{ formatNumber(report.totals.unique_visitors) }}</strong>
          <span class="kpi-hint">inclui quem não está logado</span>
        </article>
        <article class="kpi">
          <span class="kpi-label">Recursos monitorados</span>
          <strong class="kpi-value">{{ formatNumber(report.totals.tracked_resources) }}</strong>
        </article>
      </div>

      <section v-if="report.totals.events > 0" class="chart-card">
        <h2 class="chart-title">Acessos por dia</h2>
        <div class="chart">
          <div
            v-for="entry in dailySeries"
            :key="entry.day"
            class="chart-bar"
            :style="{ height: Math.max(2, (entry.events / dailyMax) * 100) + '%' }"
            :title="dayTooltip(entry)"
          />
        </div>
      </section>

      <p v-if="report.totals.events === 0" class="empty">
        Nenhum acesso registrado neste período. A contagem começa a partir da publicação desta
        versão — dados anteriores não existem.
      </p>

      <section v-for="section in sections" :key="section.key" class="cat">
        <header class="cat-head">
          <h2 class="cat-name">{{ section.label }}</h2>
          <span class="cat-total">{{ formatNumber(section.events) }} acessos</span>
        </header>

        <div v-for="group in section.groups" :key="group.name" class="group">
          <h3 v-if="section.showGroupNames" class="group-name">
            {{ group.name }}
            <span class="group-total">{{ formatNumber(group.events) }}</span>
          </h3>
          <table class="data-table">
            <thead>
              <tr>
                <th>Funcionalidade</th>
                <th class="num">Acessos</th>
                <th class="num">Usuários</th>
                <th class="num">Visitantes</th>
                <th class="num">Último acesso</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in group.items" :key="item.key">
                <td>
                  <span class="res-label">{{ item.label }}</span>
                  <span class="res-bar">
                    <span class="res-bar-fill" :style="{ width: barWidth(item, section.max) }" />
                  </span>
                </td>
                <td class="num strong">{{ formatNumber(item.events) }}</td>
                <td class="num">{{ formatNumber(item.unique_users) }}</td>
                <td class="num">{{ formatNumber(item.unique_visitors) }}</td>
                <td class="num muted">{{ formatLastAccess(item.last_at) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.analytics {
  max-width: 1200px;
  margin: 0 auto;
}
.analytics-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 16px;
  margin-bottom: 24px;
}
.analytics-title {
  font-family: var(--serif);
  font-size: 28px;
  color: var(--k0);
  margin-bottom: 4px;
}
.analytics-sub {
  font-size: 14px;
  color: var(--k5);
}
.range-picker {
  display: flex;
  border: 1px solid var(--bd);
  border-radius: 8px;
  overflow: hidden;
  background: var(--wh);
}
.range-btn {
  border: none;
  background: none;
  padding: 8px 14px;
  font-size: 13px;
  color: var(--k4);
  cursor: pointer;
  border-right: 1px solid var(--bd2);
}
.range-btn:last-child {
  border-right: none;
}
.range-btn:hover {
  background: var(--k9);
}
.range-btn.active {
  background: var(--k0);
  color: var(--wh);
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

.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}
.kpi {
  background: var(--wh);
  border: 1px solid var(--bd);
  border-radius: 12px;
  padding: 18px 20px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  box-shadow: 0 1px 3px rgba(12, 35, 64, 0.04);
}
.kpi-label {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--k5);
}
.kpi-value {
  font-family: var(--serif);
  font-size: 30px;
  color: var(--k0);
  line-height: 1.1;
}
.kpi-hint {
  font-size: 11px;
  color: var(--k5);
}

.chart-card {
  background: var(--wh);
  border: 1px solid var(--bd);
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 32px;
}
.chart-title {
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--k5);
  margin-bottom: 16px;
}
.chart {
  display: flex;
  align-items: flex-end;
  gap: 2px;
  height: 120px;
}
.chart-bar {
  flex: 1;
  min-width: 2px;
  background: linear-gradient(180deg, #1a3a5c, var(--k0));
  border-radius: 2px 2px 0 0;
  transition: opacity 0.15s ease;
}
.chart-bar:hover {
  opacity: 0.7;
}

.cat {
  margin-bottom: 36px;
}
.cat-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--bd);
  margin-bottom: 16px;
}
.cat-name {
  font-family: var(--serif);
  font-size: 18px;
  color: var(--k0);
  margin: 0;
}
.cat-total {
  font-size: 12px;
  font-weight: 600;
  color: var(--k5);
}

.group {
  margin-bottom: 20px;
}
.group-name {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--gold);
  margin-bottom: 6px;
}
.group-total {
  color: var(--k5);
  letter-spacing: 0;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  background: var(--wh);
  border: 1px solid var(--bd);
  border-radius: 10px;
  overflow: hidden;
  font-size: 13px;
}
.data-table th {
  text-align: left;
  padding: 10px 14px;
  background: var(--k9);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--k5);
  border-bottom: 1px solid var(--bd2);
}
.data-table td {
  padding: 10px 14px;
  border-bottom: 1px solid var(--bd2);
  color: var(--k3);
  vertical-align: middle;
}
.data-table tbody tr:last-child td {
  border-bottom: none;
}
.num {
  text-align: right;
  white-space: nowrap;
}
.strong {
  font-weight: 600;
  color: var(--k0);
}
.muted {
  color: var(--k5);
  font-size: 12px;
}
.res-label {
  display: block;
  margin-bottom: 5px;
}
.res-bar {
  display: block;
  height: 5px;
  background: var(--k8);
  border-radius: 3px;
  overflow: hidden;
  max-width: 340px;
}
.res-bar-fill {
  display: block;
  height: 100%;
  background: linear-gradient(90deg, var(--gold), var(--gold2));
  border-radius: 3px;
}
</style>
