<script setup lang="ts">
import { ref, onMounted, watch, nextTick } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import Plotly from 'plotly.js-dist-min'
import {
  fetchMaturityModel,
  fetchMaturityResponseById,
  type MaturityModel,
  type MaturityResult,
} from '@/api/maturity'

const route = useRoute()
const responseId = route.params.id as string

const loading = ref(true)
const error = ref<string | null>(null)
const model = ref<MaturityModel | null>(null)
const displayedResult = ref<MaturityResult | null>(null)
const submittedAt = ref<string | null>(null)

const gaugeEl = ref<HTMLDivElement | null>(null)
const radarEl = ref<HTMLDivElement | null>(null)
const dimBarsEl = ref<HTMLDivElement | null>(null)

const CHART_COLORS = {
  navy: '#0c2340',
  gold: '#9b7e46',
  step0: '#e2e2e7',
  step1: 'rgba(155, 126, 70, 0.18)',
  step2: 'rgba(155, 126, 70, 0.4)',
  step3: '#9b7e46',
  step4: '#0c2340',
  radarFill: 'rgba(155, 126, 70, 0.25)',
}

function getLevelByScore(score: number): { label?: string; description?: string } | null {
  const m = model.value
  if (!m?.scoring_logic) return null
  for (const k of Object.keys(m.scoring_logic)) {
    const it = m.scoring_logic[k]
    if (score >= it.min && score <= it.max) return it
  }
  return null
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

onMounted(async () => {
  if (!responseId) {
    error.value = 'Resposta não encontrada.'
    loading.value = false
    return
  }
  try {
    const [mod, resp] = await Promise.all([
      fetchMaturityModel(),
      fetchMaturityResponseById(responseId),
    ])
    model.value = mod
    displayedResult.value = resp.result ?? null
    submittedAt.value = resp.submitted_at ?? null
    error.value = null
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Resposta não encontrada.'
  } finally {
    loading.value = false
  }
})

watch(
  () => displayedResult.value,
  async (result) => {
    await nextTick()
    const m = model.value
    if (!m || !result) {
      if (gaugeEl.value) Plotly.purge(gaugeEl.value)
      if (radarEl.value) Plotly.purge(radarEl.value)
      if (dimBarsEl.value) Plotly.purge(dimBarsEl.value)
      return
    }
    const level =
      result.level ?? getLevelByScore(result.total_score) ?? { label: '-', description: '-' }

    if (gaugeEl.value) {
      Plotly.newPlot(
        gaugeEl.value,
        [{
          type: 'indicator',
          mode: 'gauge+number',
          value: result.percent_score,
          number: { suffix: '%', font: { size: 36 } },
          gauge: {
            axis: { range: [0, 100], tickwidth: 1 },
            bar: { color: CHART_COLORS.navy },
            bgcolor: 'white',
            borderwidth: 2,
            bordercolor: CHART_COLORS.navy,
            steps: [
              { range: [0, 20], color: CHART_COLORS.step0 },
              { range: [20, 40], color: CHART_COLORS.step1 },
              { range: [40, 60], color: CHART_COLORS.step2 },
              { range: [60, 80], color: CHART_COLORS.step3 },
              { range: [80, 100], color: CHART_COLORS.step4 },
            ],
            threshold: { line: { color: CHART_COLORS.gold, width: 3 }, value: result.percent_score },
          },
        }],
        { margin: { t: 20, r: 30, b: 20, l: 30 }, paper_bgcolor: 'rgba(0,0,0,0)' },
        { displayModeBar: false, responsive: true }
      )
    }
    const dims = m.dimensions ?? []
    if (radarEl.value && dims.length) {
      const dimNames = dims.map((d) => d.name)
      const dimValues = dims.map((d) => (result.dimension_scores?.[d.id] || {}).avg || 0)
      Plotly.newPlot(
        radarEl.value,
        [{
          type: 'scatterpolar',
          r: [...dimValues, dimValues[0]],
          theta: [...dimNames, dimNames[0]],
          fill: 'toself',
          line: { color: CHART_COLORS.navy, width: 2 },
          fillcolor: CHART_COLORS.radarFill,
          marker: { size: 8, color: CHART_COLORS.gold, line: { color: '#fff', width: 1.5 } },
        }],
        {
          autosize: true,
          margin: { t: 36, r: 80, b: 36, l: 80 },
          paper_bgcolor: 'rgba(0,0,0,0)',
          polar: {
            bgcolor: 'rgba(0,0,0,0)',
            radialaxis: { visible: true, range: [0, 5], tickvals: [1, 2, 3, 4, 5] },
          },
          showlegend: false,
        },
        { displayModeBar: false, responsive: true }
      )
    }
    if (dimBarsEl.value && dims.length) {
      const dimNames = dims.map((d) => d.name)
      const dimPcts = dims.map((d) => {
        const ds = result.dimension_scores?.[d.id] || {}
        const max = ds.max || 1
        return max ? Math.round((ds.score / max) * 100) : 0
      })
      Plotly.newPlot(
        dimBarsEl.value,
        [{
          type: 'bar',
          y: dimNames,
          x: dimPcts,
          orientation: 'h',
          marker: {
            color: dimPcts.map((p) => {
              if (p >= 80) return CHART_COLORS.step4
              if (p >= 60) return CHART_COLORS.step3
              if (p >= 40) return CHART_COLORS.step2
              if (p >= 20) return CHART_COLORS.step1
              return CHART_COLORS.step0
            }),
          },
          text: dimPcts.map((p) => p + '%'),
          textposition: 'outside',
        }],
        {
          margin: { t: 10, r: 60, b: 40, l: 140 },
          xaxis: { range: [0, 105], title: 'Percentual', ticksuffix: '%' },
          yaxis: { automargin: true },
          paper_bgcolor: 'rgba(0,0,0,0)',
          plot_bgcolor: 'rgba(0,0,0,0)',
        },
        { displayModeBar: false, responsive: true }
      )
    }
  },
  { immediate: true }
)
</script>

<template>
  <div class="wrap">
    <div class="back-row">
      <RouterLink to="/ai-maturity" class="back-link">← Voltar à lista</RouterLink>
    </div>
    <div v-if="loading" class="card">Carregando...</div>
    <div v-else-if="error" class="card error-msg">{{ error }}</div>
    <template v-else-if="model && displayedResult">
      <div class="card card-header">
        <h1 class="title">{{ model.assessment_title ?? 'Diagnóstico' }}</h1>
        <p class="muted">Realizada em {{ formatDate(submittedAt) }}</p>
      </div>
      <div class="results-top">
        <div class="card">
          <h3>Pontuação Geral</h3>
          <div class="results-chart-wrap">
            <div class="score-card">
              <div class="score-value">{{ displayedResult.total_score }}</div>
              <div class="score-max">/ {{ displayedResult.max_score }}</div>
              <div class="score-pct">{{ displayedResult.percent_score }}%</div>
              <div class="level-badge">
                {{ (displayedResult.level ?? getLevelByScore(displayedResult.total_score))?.label ?? '-' }}
              </div>
              <div class="level-desc">
                {{ (displayedResult.level ?? getLevelByScore(displayedResult.total_score))?.description ?? '' }}
              </div>
            </div>
            <div ref="gaugeEl" class="chart-gauge"></div>
          </div>
        </div>
        <div class="card">
          <h3>Radar por Dimensão</h3>
          <div ref="radarEl" class="chart-radar"></div>
        </div>
      </div>
      <div class="card">
        <h3>Pontuação por Dimensão</h3>
        <div ref="dimBarsEl" class="chart-dimbars"></div>
        <div class="dim-cards">
          <div
            v-for="dim in (model.dimensions ?? [])"
            :key="dim.id"
            class="dim-card"
          >
            <div class="dim-name">
              {{ (displayedResult.dimension_scores?.[dim.id] || {}).name || dim.name }}
            </div>
            <div class="dim-bar-wrap">
              <div
                class="dim-bar"
                :style="{
                  width:
                    (() => {
                      const ds = displayedResult.dimension_scores?.[dim.id] || { score: 0, max: 1 }
                      return ds.max ? Math.round((ds.score / ds.max) * 100) : 0
                    })() + '%',
                }"
              ></div>
            </div>
            <div class="dim-nums">
              {{
                (() => {
                  const ds =
                    displayedResult.dimension_scores?.[dim.id] || { score: 0, max: 0, avg: 0 }
                  return `${ds.score} / ${ds.max} (média ${ds.avg})`
                })()
              }}
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.wrap {
  max-width: 1080px;
  margin: 0 auto;
  padding: 22px 16px 40px;
}
.back-row {
  margin-bottom: 16px;
}
.back-link {
  font-size: 14px;
  color: var(--k0);
  text-decoration: none;
}
.back-link:hover {
  text-decoration: underline;
}
.card {
  background: var(--wh);
  border: 1px solid var(--bd);
  padding: 18px;
  margin-bottom: 14px;
  border-radius: 8px;
}
.card-header .title {
  font-family: var(--serif);
  font-size: 24px;
  margin: 0 0 6px 0;
  color: var(--k0);
}
.muted {
  font-size: 14px;
  color: var(--k5);
  margin: 0;
}
.error-msg {
  color: #8f2b2b;
}
.card h3 {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 14px;
  color: var(--k0);
}
.results-top {
  display: grid;
  grid-template-columns: minmax(260px, 360px) minmax(260px, 1fr);
  gap: 18px;
  margin-bottom: 20px;
}
.results-chart-wrap {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.chart-gauge {
  max-width: 320px;
  margin: 0 auto;
  height: 220px;
}
.chart-radar {
  min-height: 420px;
  max-width: 420px;
  margin: 0 auto;
}
.chart-dimbars {
  height: 260px;
}
.score-card {
  padding: 20px 20px 18px;
  border-radius: 12px;
  background: linear-gradient(160deg, #fafaf9 0%, #f5f3f0 100%);
  color: var(--k0);
  border: 1px solid var(--bd);
  box-shadow: 0 2px 12px rgba(12, 35, 64, 0.06);
}
.score-card .score-value {
  font-family: var(--serif);
  font-size: 32px;
  font-weight: 600;
  line-height: 1.1;
  margin-bottom: 2px;
}
.score-card .score-max {
  font-size: 14px;
  color: var(--k4);
}
.score-card .score-pct {
  font-family: var(--serif);
  font-size: 20px;
  font-weight: 600;
  color: var(--gold2);
  margin-top: 8px;
}
.score-card .level-badge {
  display: inline-block;
  margin-top: 10px;
  padding: 6px 14px;
  background: rgba(155, 126, 70, 0.12);
  border-radius: 999px;
  border: 1px solid rgba(155, 126, 70, 0.35);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--gold2);
}
.score-card .level-desc {
  font-size: 13px;
  color: var(--k4);
  margin-top: 12px;
  line-height: 1.45;
}
.dim-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 14px;
  margin-top: 16px;
}
.dim-card {
  background: var(--wh);
  border: 1px solid var(--bd);
  padding: 16px;
  border-radius: 6px;
}
.dim-card .dim-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--k0);
  margin-bottom: 10px;
}
.dim-card .dim-bar-wrap {
  height: 10px;
  background: var(--k7);
  border-radius: 5px;
  overflow: hidden;
  margin-bottom: 6px;
}
.dim-card .dim-bar {
  height: 100%;
  border-radius: 5px;
  background: linear-gradient(90deg, var(--k0), var(--gold));
}
.dim-card .dim-nums {
  font-size: 12px;
  color: var(--k5);
}
@media (max-width: 760px) {
  .results-top {
    grid-template-columns: 1fr;
  }
}
</style>
