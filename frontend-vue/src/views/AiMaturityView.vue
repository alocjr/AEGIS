<script setup lang="ts">
import { ref, onMounted, watch, nextTick, computed } from 'vue'
import { useRouter } from 'vue-router'
import Plotly from 'plotly.js-dist-min'
import {
  fetchMaturityModel,
  saveMaturityResponse,
  type MaturityModel,
  type MaturityResult,
} from '@/api/maturity'

const router = useRouter()
const loading = ref(true)
const error = ref<string | null>(null)
const model = ref<MaturityModel | null>(null)
const answers = ref<Record<string, number>>({})
const saving = ref(false)
const saveInfo = ref('')

const gaugeEl = ref<HTMLDivElement | null>(null)
const radarEl = ref<HTMLDivElement | null>(null)
const dimBarsEl = ref<HTMLDivElement | null>(null)

const scale = ref<{ value: number; label: string }[]>([])
const displayedResult = ref<MaturityResult | null>(null)

/* Paleta alinhada ao slider: cinza claro → dourado → navy */
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

const totalQuestions = computed(() => {
  const m = model.value
  if (!m?.dimensions) return 0
  return m.dimensions.reduce((acc, d) => acc + (d.questions?.length ?? 0), 0)
})

const scaleBounds = computed(() => {
  const s = scale.value
  if (!s.length) return { min: 1, max: 5 }
  const vals = s.map((x) => x.value)
  return { min: Math.min(...vals), max: Math.max(...vals) }
})

function getLabelForValue(val: number): string {
  return scale.value.find((o) => o.value === val)?.label ?? String(val)
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

function setAnswer(qid: string, val: number) {
  answers.value = { ...answers.value, [qid]: val }
}

onMounted(async () => {
  try {
    const mod = await fetchMaturityModel()
    model.value = mod
    scale.value =
      mod.answer_scale?.map((s) => ({ value: s.value, label: s.label })) ?? []
    const defaultVal = scale.value[0]?.value ?? 1
    const withDefaults: Record<string, number> = {}
    for (const dim of mod.dimensions ?? []) {
      for (const q of dim.questions ?? []) {
        withDefaults[q.id] = defaultVal
      }
    }
    answers.value = withDefaults
    displayedResult.value = null
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Erro ao carregar modelo.'
  } finally {
    loading.value = false
  }
})

watch(
  displayedResult,
  async (result) => {
    await nextTick()
    if (!model.value || !result) {
      if (gaugeEl.value) Plotly.purge(gaugeEl.value)
      if (radarEl.value) Plotly.purge(radarEl.value)
      if (dimBarsEl.value) Plotly.purge(dimBarsEl.value)
      return
    }
    const level =
      result.level ?? getLevelByScore(result.total_score) ?? {
        label: '-',
        description: '-',
      }

    if (gaugeEl.value) {
      Plotly.newPlot(
        gaugeEl.value,
        [
          {
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
              threshold: {
                line: { color: CHART_COLORS.gold, width: 3 },
                value: result.percent_score,
              },
            },
          },
        ],
        {
          margin: { t: 20, r: 30, b: 20, l: 30 },
          paper_bgcolor: 'rgba(0,0,0,0)',
          font: {
            family: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif",
          },
        },
        { displayModeBar: false, responsive: true }
      )
    }

    const dims = model.value.dimensions ?? []
    if (radarEl.value && dims.length) {
      const dimNames = dims.map((d) => d.name)
      const dimValues = dims.map(
        (d) => (result.dimension_scores?.[d.id] || {}).avg || 0
      )
      Plotly.newPlot(
        radarEl.value,
        [
          {
            type: 'scatterpolar',
            r: [...dimValues, dimValues[0]],
            theta: [...dimNames, dimNames[0]],
            fill: 'toself',
            name: 'Maturidade',
            line: { color: CHART_COLORS.navy, width: 2 },
            fillcolor: CHART_COLORS.radarFill,
            marker: {
              size: 8,
              color: CHART_COLORS.gold,
              line: { color: '#fff', width: 1.5 },
            },
          },
        ],
        {
          autosize: true,
          margin: { t: 36, r: 80, b: 36, l: 80 },
          paper_bgcolor: 'rgba(0,0,0,0)',
          font: {
            family: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif",
            size: 12,
            color: '#1c1c1c',
          },
          polar: {
            bgcolor: 'rgba(0,0,0,0)',
            domain: { x: [0.08, 0.92], y: [0.08, 0.92] },
            radialaxis: {
              visible: true,
              range: [0, 5],
              tickvals: [1, 2, 3, 4, 5],
              tickfont: { size: 11, color: '#505050' },
              gridcolor: '#e2e2e2',
              linecolor: '#c8c8c8',
              linewidth: 1,
            },
            angularaxis: {
              tickfont: { size: 11, color: '#505050' },
              gridcolor: '#e2e2e2',
              linecolor: '#c8c8c8',
            },
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
        [
          {
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
          },
        ],
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

async function saveAnswers() {
  if (!model.value) return
  const missing: string[] = []
  for (const dim of model.value.dimensions ?? []) {
    for (const q of dim.questions ?? []) {
      if (answers.value[q.id] == null) missing.push(q.id)
    }
  }
  if (missing.length) {
    alert('Responda todas as perguntas antes de salvar.')
    return
  }
  saving.value = true
  try {
    const result = await saveMaturityResponse(answers.value)
    displayedResult.value = result.result
    saveInfo.value =
      'Salvo em ' + new Date(result.submitted_at).toLocaleString('pt-BR')
    setTimeout(() => router.push('/ai-maturity'), 1500)
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Erro ao salvar.'
  } finally {
    saving.value = false
  }
}

function clearForm() {
  const defaultVal = scale.value[0]?.value ?? 1
  const withDefaults: Record<string, number> = {}
  for (const dim of model.value?.dimensions ?? []) {
    for (const q of dim.questions ?? []) {
      withDefaults[q.id] = defaultVal
    }
  }
  answers.value = withDefaults
  displayedResult.value = null
  saveInfo.value = ''
}
</script>

<template>
  <div class="wrap">
    <div v-if="loading" class="card">Carregando...</div>
    <div v-else-if="error" class="card error-msg">{{ error }}</div>

    <template v-else-if="model">
      <div class="card">
        <div class="title">{{ model.assessment_title ?? 'Diagnóstico' }}</div>
        <div class="muted">
          Versão {{ model.version ?? '-' }} · {{ totalQuestions }} perguntas
        </div>
      </div>

      <!-- Resultados (quando há resultado salvo) -->
      <template v-if="displayedResult">
        <div class="results-top">
          <div class="card">
            <h3>Pontuação Geral</h3>
            <div class="results-chart-wrap">
              <div class="score-card">
                <div class="score-value">{{ displayedResult.total_score }}</div>
                <div class="score-max">/ {{ displayedResult.max_score }}</div>
                <div class="score-pct">{{ displayedResult.percent_score }}%</div>
                <div class="level-badge">
                  {{
                    (displayedResult.level ?? getLevelByScore(displayedResult.total_score))?.label ?? '-'
                  }}
                </div>
                <div class="level-desc">
                  {{
                    (displayedResult.level ?? getLevelByScore(displayedResult.total_score))?.description ?? ''
                  }}
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
                {{
                  (displayedResult.dimension_scores?.[dim.id] || {}).name ||
                  dim.name
                }}
              </div>
              <div class="dim-bar-wrap">
                <div
                  class="dim-bar"
                  :style="{
                    width:
                      (() => {
                        const ds = displayedResult.dimension_scores?.[dim.id] || {
                          score: 0,
                          max: 1,
                        }
                        return ds.max
                          ? Math.round((ds.score / ds.max) * 100)
                          : 0
                      })() + '%',
                  }"
                ></div>
              </div>
              <div class="dim-nums">
                {{
                  (() => {
                    const ds =
                      displayedResult.dimension_scores?.[dim.id] || {
                        score: 0,
                        max: 0,
                        avg: 0,
                      }
                    return `${ds.score} / ${ds.max} (média ${ds.avg})`
                  })()
                }}
              </div>
            </div>
          </div>
        </div>
      </template>

      <!-- Formulário por dimensão -->
      <template
        v-for="dim in (model.dimensions ?? [])"
        :key="dim.id"
      >
        <div class="card card-dim">
          <h2 class="dim-title">{{ dim.name }}</h2>
          <div
            v-for="(q, qIdx) in dim.questions"
            :key="q.id"
            class="q"
          >
            <div class="q-header">
              <span class="q-num">{{ qIdx + 1 }}</span>
              <p class="q-text">{{ q.text }}</p>
            </div>
            <div class="slider-wrap" role="group" :aria-label="'Resposta: ' + q.text.slice(0, 50)">
              <div
                class="slider-track-wrap"
                :style="{
                  '--slider-pct':
                    (100 *
                      (((answers[q.id] ?? scaleBounds.min) - scaleBounds.min) /
                        (scaleBounds.max - scaleBounds.min || 1))) +
                    '%',
                }"
              >
                <input
                  type="range"
                  class="slider-input"
                  :min="scaleBounds.min"
                  :max="scaleBounds.max"
                  :step="1"
                  :value="answers[q.id] ?? scaleBounds.min"
                  @input="(e) => setAnswer(q.id, Number((e.target as HTMLInputElement).value))"
                  :aria-valuemin="scaleBounds.min"
                  :aria-valuemax="scaleBounds.max"
                  :aria-valuenow="answers[q.id] ?? scaleBounds.min"
                  :aria-valuetext="getLabelForValue(answers[q.id] ?? scaleBounds.min)"
                />
                <div class="slider-ticks" v-if="scale.length">
                  <span
                    v-for="opt in scale"
                    :key="opt.value"
                    class="slider-tick"
                    :class="{ active: (answers[q.id] ?? scaleBounds.min) === opt.value }"
                    @click="setAnswer(q.id, opt.value)"
                  >
                    {{ opt.value }}
                  </span>
                </div>
                <div class="slider-labels" v-if="scale.length">
                  <span
                    v-for="opt in scale"
                    :key="'l-' + opt.value"
                    class="slider-label"
                  >
                    {{ opt.label }}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </template>

      <div class="card actions">
        <button type="button" class="btn" @click="saveAnswers" :disabled="saving">
          {{ saving ? 'Salvando...' : 'Salvar respostas' }}
        </button>
        <button type="button" class="btn light" @click="clearForm">
          Limpar
        </button>
        <span class="muted">{{ saveInfo }}</span>
      </div>
    </template>
  </div>
</template>

<style scoped>
.wrap {
  max-width: 1080px;
  margin: 0 auto;
  padding: 0 16px;
  padding-top: 22px;
  padding-bottom: 40px;
}
.card {
  background: var(--wh);
  border: 1px solid var(--bd);
  padding: 18px;
  margin-bottom: 14px;
}
.card h3 {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 14px;
  color: var(--k0);
}
.muted {
  color: var(--k3);
  font-size: 14px;
}
.title {
  font-size: 27px;
  margin-bottom: 6px;
  font-family: var(--serif);
  color: var(--k0);
}
.card-dim {
  padding: 24px;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(12, 35, 64, 0.06);
}
.dim-title {
  font-family: var(--serif);
  font-size: 20px;
  font-weight: 600;
  margin-bottom: 20px;
  padding-bottom: 12px;
  color: var(--k0);
  border-bottom: 2px solid var(--gold);
  letter-spacing: 0.02em;
}
.q {
  padding: 20px 0;
  border-top: 1px solid var(--k7);
  transition: background 0.2s ease;
}
.q:first-child {
  border-top: none;
  padding-top: 0;
}
.q:hover {
  background: linear-gradient(90deg, rgba(155, 126, 70, 0.04) 0%, transparent 100%);
  margin: 0 -24px;
  padding-left: 24px;
  padding-right: 24px;
  border-radius: 8px;
}
.q-header {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  margin-bottom: 14px;
}
.q-num {
  flex-shrink: 0;
  width: 28px;
  height: 28px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: var(--k0);
  color: var(--wh);
  font-size: 13px;
  font-weight: 700;
  border-radius: 50%;
  line-height: 1;
}
.q-text {
  margin: 0;
  font-size: 15px;
  color: var(--k0);
  line-height: 1.55;
  font-weight: 500;
}
.slider-wrap {
  margin-top: 4px;
}
.slider-track-wrap {
  --slider-pct: 0%;
  position: relative;
  padding: 8px 0 4px;
}
.slider-input {
  display: block;
  width: 100%;
  height: 44px;
  margin: 0;
  padding: 0 22px;
  appearance: none;
  background: transparent;
  cursor: pointer;
}
.slider-input::-webkit-slider-runnable-track {
  height: 12px;
  border-radius: 6px;
  background: linear-gradient(
    to right,
    var(--k0) 0%,
    var(--gold) var(--slider-pct),
    var(--k7) var(--slider-pct),
    var(--k7) 100%
  );
  box-shadow: inset 0 1px 2px rgba(0, 0, 0, 0.08);
}
.slider-input::-moz-range-track {
  height: 12px;
  border-radius: 6px;
  background: linear-gradient(
    to right,
    var(--k0) 0%,
    var(--gold) var(--slider-pct),
    var(--k7) var(--slider-pct),
    var(--k7) 100%
  );
  box-shadow: inset 0 1px 2px rgba(0, 0, 0, 0.08);
}
.slider-input::-webkit-slider-thumb {
  appearance: none;
  width: 28px;
  height: 28px;
  margin-top: -8px;
  background: linear-gradient(145deg, var(--wh) 0%, var(--k8) 100%);
  border: 2px solid var(--k0);
  border-radius: 50%;
  box-shadow: 0 2px 10px rgba(12, 35, 64, 0.25);
  cursor: grab;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.slider-input::-webkit-slider-thumb:hover {
  transform: scale(1.08);
  box-shadow: 0 4px 16px rgba(12, 35, 64, 0.3);
}
.slider-input::-webkit-slider-thumb:active {
  cursor: grabbing;
}
.slider-input::-moz-range-thumb {
  width: 28px;
  height: 28px;
  background: linear-gradient(145deg, var(--wh) 0%, var(--k8) 100%);
  border: 2px solid var(--k0);
  border-radius: 50%;
  box-shadow: 0 2px 10px rgba(12, 35, 64, 0.25);
  cursor: grab;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.slider-input::-moz-range-thumb:hover {
  transform: scale(1.08);
  box-shadow: 0 4px 16px rgba(12, 35, 64, 0.3);
}
.slider-input:focus-visible {
  outline: none;
}
.slider-input:focus-visible::-webkit-slider-thumb {
  box-shadow: 0 0 0 3px var(--golddim), 0 2px 10px rgba(12, 35, 64, 0.25);
}
.slider-input:focus-visible::-moz-range-thumb {
  box-shadow: 0 0 0 3px var(--golddim), 0 2px 10px rgba(12, 35, 64, 0.25);
}
.slider-ticks {
  display: flex;
  justify-content: space-between;
  margin-top: 6px;
  padding: 0 14px;
  max-width: 100%;
}
.slider-tick {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  color: var(--k5);
  background: var(--k8);
  border: 2px solid var(--bd);
  border-radius: 50%;
  cursor: pointer;
  transition: color 0.2s, background 0.2s, border-color 0.2s, transform 0.15s ease;
}
.slider-tick:hover {
  color: var(--k0);
  background: var(--golddim);
  border-color: var(--goldbd);
  transform: scale(1.1);
}
.slider-tick.active {
  color: var(--wh);
  background: var(--k0);
  border-color: var(--k0);
  box-shadow: 0 2px 8px rgba(12, 35, 64, 0.3);
}
.slider-labels {
  display: flex;
  justify-content: space-between;
  margin-top: 10px;
  padding: 0 4px;
  gap: 4px;
}
.slider-label {
  flex: 1;
  min-width: 0;
  font-size: 11px;
  font-weight: 500;
  color: var(--k5);
  text-align: center;
  line-height: 1.35;
}
.actions {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-top: 14px;
}
.btn {
  height: 36px;
  padding: 0 14px;
  border: 1px solid var(--k0);
  background: var(--k0);
  color: var(--wh);
  cursor: pointer;
  font-size: 14px;
}
.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.btn.light {
  background: var(--wh);
  color: var(--k0);
}
.btn.light:hover {
  background: var(--k8);
}

.results-top {
  display: grid;
  grid-template-columns: minmax(260px, 360px) minmax(260px, 1fr);
  gap: 18px;
  align-items: stretch;
  margin-bottom: 20px;
}
.results-top .card {
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.results-top .card h3 {
  flex: 0 0 auto;
}
.results-chart-wrap {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.results-chart-wrap .score-card {
  flex: 0 0 auto;
}
.results-chart-wrap .chart-gauge {
  flex: 1;
  min-height: 0;
  max-width: 320px;
  margin: 0 auto;
  height: 220px;
}
.chart-radar {
  flex: 1;
  min-height: 420px;
  max-width: 420px;
  margin: 0 auto;
}
.chart-dimbars {
  width: 100%;
  height: 260px;
}

.score-card {
  padding: 20px 20px 18px;
  border-radius: 12px;
  background: linear-gradient(160deg, #fafaf9 0%, #f5f3f0 100%);
  color: var(--k0);
  text-align: left;
  margin-bottom: 10px;
  border: 1px solid var(--bd);
  box-shadow: 0 2px 12px rgba(12, 35, 64, 0.06);
}
.score-card .score-value {
  font-family: var(--serif);
  font-size: 32px;
  font-weight: 600;
  line-height: 1.1;
  margin-bottom: 2px;
  letter-spacing: -0.02em;
}
.score-card .score-max {
  font-size: 14px;
  color: var(--k4);
  font-weight: 500;
}
.score-card .score-pct {
  font-family: var(--serif);
  font-size: 20px;
  font-weight: 600;
  color: var(--gold2);
  margin-top: 8px;
}
.score-card .level-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
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
  max-width: 280px;
  margin-left: 0;
  margin-right: 0;
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
  line-height: 1.3;
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
  transition: width 0.4s ease;
}
.dim-card .dim-nums {
  font-size: 12px;
  color: var(--k5);
}

.error-msg {
  color: #c00;
}

@media (max-width: 760px) {
  .results-top {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 900px) {
  .wrap {
    padding-left: 12px;
    padding-right: 12px;
  }
}
@media (max-width: 640px) {
  .card-dim {
    padding: 18px;
  }
  .q:hover {
    margin: 0 -18px;
    padding-left: 18px;
    padding-right: 18px;
  }
  .slider-label {
    font-size: 10px;
  }
}
</style>
