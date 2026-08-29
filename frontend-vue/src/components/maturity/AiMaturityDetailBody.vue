<script setup lang="ts">
import { RouterLink } from 'vue-router'
import type { MaturityDetailEditor } from '@/composables/useMaturityDetail'

const props = defineProps<{ editor: MaturityDetailEditor }>()
const {
  responseId, model, displayedResult, submittedAt, tierLabel,
  levelInfo, dimRows, strongest, weakest,
  RING_R, RING_C, ringOffset,
  RADAR_CX, RADAR_CY,
  gridRings, radarPolygon,
  formatDate, radarPoint, radarAxisEnd, radarLabelPos,
  isComplete, swotBusy, swotId, swotError,
  exportBusy, exportError,
  openSwot, exportJson,
} = props.editor
</script>

<template>
  <div v-if="model && displayedResult">
      <header class="page-header">
        <p class="eyebrow">Resultado · Maturidade em IA</p>
        <h1 class="page-title">
          {{ model.assessment_title || model.title || 'Diagnóstico de Maturidade em IA' }}
        </h1>
        <div class="meta-row">
          <span class="meta-item">{{ formatDate(submittedAt) }}</span>
          <span v-if="tierLabel" class="meta-pill">{{ tierLabel }}</span>
          <span v-if="model.version" class="meta-pill muted">v{{ model.version }}</span>
        </div>
      </header>

      <!-- Hero: score + nível -->
      <section class="hero card">
        <div class="hero-score">
          <div class="score-ring" aria-hidden="true">
            <svg viewBox="0 0 120 120" class="ring-svg">
              <circle class="ring-bg" cx="60" cy="60" :r="RING_R" />
              <circle
                class="ring-fill"
                cx="60"
                cy="60"
                :r="RING_R"
                fill="none"
                :stroke-dasharray="RING_C"
                :stroke-dashoffset="ringOffset"
                transform="rotate(-90 60 60)"
              />
            </svg>
            <div class="ring-center">
              <span class="ring-pct">{{ Math.round(displayedResult.percent_score) }}%</span>
            </div>
          </div>
          <div class="hero-nums">
            <div class="score-line">
              <span class="score-value">{{ displayedResult.total_score }}</span>
              <span class="score-max">/ {{ displayedResult.max_score }} pts</span>
            </div>
            <div class="level-badge">{{ levelInfo.label }}</div>
            <p v-if="levelInfo.description" class="level-desc">{{ levelInfo.description }}</p>
          </div>
        </div>
      </section>

      <!-- KPIs -->
      <section class="kpi-grid" v-if="dimRows.length">
        <div class="kpi-card">
          <div class="kpi-label">Dimensões</div>
          <div class="kpi-value">{{ dimRows.length }}</div>
          <div class="kpi-sub">avaliadas</div>
        </div>
        <div class="kpi-card" v-if="strongest">
          <div class="kpi-label">Mais madura</div>
          <div class="kpi-value gold">{{ strongest.avg.toFixed(1) }}</div>
          <div class="kpi-sub">{{ strongest.name }}</div>
        </div>
        <div class="kpi-card" v-if="weakest">
          <div class="kpi-label">Mais frágil</div>
          <div class="kpi-value">{{ weakest.avg.toFixed(1) }}</div>
          <div class="kpi-sub">{{ weakest.name }}</div>
        </div>
      </section>

      <!-- Radar + dimensões -->
      <section class="split">
        <div class="card radar-card">
          <h2 class="sec-title">Radar por dimensão</h2>
          <div class="radar-wrap" v-if="dimRows.length">
            <svg viewBox="0 0 200 200" class="radar-svg" role="img" aria-label="Radar de maturidade por dimensão">
              <defs>
                <linearGradient id="maturityRadarFill" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stop-color="var(--gold)" stop-opacity="0.28" />
                  <stop offset="100%" stop-color="var(--k0)" stop-opacity="0.18" />
                </linearGradient>
              </defs>
              <g v-for="(ring, ri) in gridRings" :key="'ring-' + ri">
                <polygon
                  class="radar-grid"
                  :points="
                    dimRows
                      .map((_, i) => {
                        const p = radarPoint(i, dimRows.length, ring * 100)
                        return `${p.x},${p.y}`
                      })
                      .join(' ')
                  "
                />
              </g>
              <g v-for="(d, idx) in dimRows" :key="'ax-' + d.id">
                <line
                  class="radar-axis"
                  :x1="RADAR_CX"
                  :y1="RADAR_CY"
                  :x2="radarAxisEnd(idx, dimRows.length).x"
                  :y2="radarAxisEnd(idx, dimRows.length).y"
                />
              </g>
              <polygon
                class="radar-poly"
                :points="radarPolygon"
                fill="url(#maturityRadarFill)"
              />
              <g v-for="(d, idx) in dimRows" :key="'pt-' + d.id">
                <circle
                  class="radar-dot"
                  :cx="radarPoint(idx, dimRows.length, d.pct).x"
                  :cy="radarPoint(idx, dimRows.length, d.pct).y"
                  r="3.5"
                  :fill="d.accent"
                />
              </g>
              <text
                v-for="(d, idx) in dimRows"
                :key="'lb-' + d.id"
                class="radar-label"
                :x="radarLabelPos(idx, dimRows.length).x"
                :y="radarLabelPos(idx, dimRows.length).y"
                text-anchor="middle"
                dominant-baseline="middle"
              >{{ d.initials }}</text>
            </svg>
            <ul class="radar-legend">
              <li v-for="d in dimRows" :key="'lg-' + d.id">
                <span class="dot" :style="{ background: d.accent }" />
                <span class="lg-name">{{ d.name }}</span>
                <span class="lg-avg">{{ d.avg.toFixed(1) }}</span>
              </li>
            </ul>
          </div>
        </div>

        <div class="card dims-card">
          <h2 class="sec-title">Pontuação por dimensão</h2>
          <ul class="dim-list">
            <li v-for="d in dimRows" :key="d.id" class="dim-row">
              <div class="dim-head">
                <span class="dim-accent" :style="{ background: d.accent }" aria-hidden="true" />
                <span class="dim-name">{{ d.name }}</span>
                <span class="dim-pct">{{ d.pct }}%</span>
              </div>
              <div class="dim-bar-track" role="meter" :aria-valuenow="d.pct" aria-valuemin="0" aria-valuemax="100">
                <div
                  class="dim-bar-fill"
                  :style="{ width: d.pct + '%', background: `linear-gradient(90deg, var(--k0), ${d.accent})` }"
                />
              </div>
              <div class="dim-meta">
                <span>{{ d.score }} / {{ d.max }} pts</span>
                <span>média {{ d.avg.toFixed(1) }} / 5</span>
              </div>
            </li>
          </ul>
        </div>
      </section>

      <div class="actions">
        <RouterLink :to="`/ai-maturity/${responseId}/edit`" class="btn-primary">
          Editar respostas
        </RouterLink>
        <button
          v-if="isComplete"
          type="button"
          class="btn-ghost"
          :disabled="swotBusy"
          @click="openSwot"
        >
          {{ swotBusy ? 'Gerando…' : swotId ? 'Abrir SWOT' : 'Criar SWOT' }}
        </button>
        <RouterLink
          :to="`/mapa-estrategico?maturidade=${responseId}`"
          class="btn-ghost"
        >Mapa Estratégico</RouterLink>
        <button
          type="button"
          class="btn-ghost"
          :disabled="exportBusy"
          title="Baixar respostas e resultado em JSON"
          @click="exportJson"
        >
          {{ exportBusy ? 'Exportando…' : 'Exportar JSON' }}
        </button>
        <RouterLink to="/ai-maturity/new" class="btn-ghost">Nova autoavaliação</RouterLink>
        <RouterLink to="/ai-maturity" class="btn-ghost">Ver todas</RouterLink>
        <p v-if="swotError" class="swot-error">{{ swotError }}</p>
        <p v-if="exportError" class="swot-error">{{ exportError }}</p>
      </div>
  </div>
</template>

<style scoped>
.page-header {
  margin-bottom: 20px;
}
.eyebrow {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--gold-text);
  margin: 0 0 8px;
}
.page-title {
  font-family: var(--serif);
  font-size: clamp(22px, 5.5vw, 28px);
  font-weight: 400;
  color: var(--k0);
  margin: 0 0 12px;
  line-height: 1.2;
}
.meta-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}
.meta-item {
  font-size: 13px;
  color: var(--k3);
}
.meta-pill {
  display: inline-flex;
  align-items: center;
  padding: 3px 10px;
  border-radius: var(--r-pill);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  background: var(--golddim);
  border: 1px solid var(--goldbd);
  color: var(--gold-text);
}
.meta-pill.muted {
  background: var(--k8);
  border-color: var(--bd);
  color: var(--k4);
}

.card {
  background: var(--wh);
  border: 1px solid var(--bd);
  border-radius: var(--r-sm);
  padding: 18px;
}

.hero {
  position: relative;
  overflow: hidden;
  margin-bottom: 14px;
}
.hero::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, var(--k0) 0%, var(--gold) 100%);
}
.hero-score {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 18px;
  text-align: center;
  padding-top: 6px;
}
.score-ring {
  position: relative;
  width: 140px;
  height: 140px;
  flex-shrink: 0;
}
.ring-svg {
  width: 100%;
  height: 100%;
  display: block;
}
.ring-bg {
  fill: none;
  stroke: var(--k7);
  stroke-width: 8;
}
.ring-fill {
  stroke: var(--gold);
  stroke-width: 8;
  stroke-linecap: round;
  transition: stroke-dashoffset 0.6s ease;
}
.ring-center {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}
.ring-pct {
  font-family: var(--serif);
  font-size: 28px;
  font-weight: 600;
  color: var(--k0);
  line-height: 1;
}
.hero-nums {
  min-width: 0;
}
.score-line {
  display: flex;
  align-items: baseline;
  justify-content: center;
  gap: 6px;
  flex-wrap: wrap;
}
.score-value {
  font-family: var(--serif);
  font-size: 36px;
  font-weight: 600;
  color: var(--k0);
  line-height: 1;
}
.score-max {
  font-size: 15px;
  color: var(--k4);
}
.level-badge {
  display: inline-flex;
  margin-top: 12px;
  padding: 6px 14px;
  background: var(--golddim);
  border: 1px solid var(--goldbd);
  border-radius: var(--r-pill);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--gold-text);
}
.level-desc {
  margin: 12px 0 0;
  font-size: 13px;
  line-height: 1.5;
  color: var(--k3);
  max-width: 36em;
}

.kpi-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 10px;
  margin-bottom: 14px;
}
.kpi-card {
  background: var(--wh);
  border: 1px solid var(--bd);
  border-radius: var(--r-sm);
  padding: 16px;
  position: relative;
  overflow: hidden;
}
.kpi-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: var(--gold);
}
.kpi-label {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--k3);
  margin-bottom: 6px;
}
.kpi-value {
  font-family: var(--serif);
  font-size: 26px;
  font-weight: 400;
  color: var(--k0);
  line-height: 1.1;
}
.kpi-value.gold {
  color: var(--gold-text);
}
.kpi-sub {
  font-size: 12px;
  color: var(--k3);
  margin-top: 4px;
  line-height: 1.35;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.split {
  display: flex;
  flex-direction: column;
  gap: 14px;
  margin-bottom: 20px;
}
.sec-title {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--k3);
  margin: 0 0 16px;
}

.radar-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}
.radar-svg {
  width: min(100%, 280px);
  aspect-ratio: 1;
  display: block;
}
.radar-grid {
  fill: none;
  stroke: var(--k7);
  stroke-width: 0.8;
}
.radar-axis {
  stroke: var(--k7);
  stroke-width: 0.9;
}
.radar-poly {
  stroke: var(--k0);
  stroke-width: 1.6;
  transition: opacity 0.2s;
}
.radar-label {
  font-size: 11px;
  font-weight: 700;
  fill: var(--k4);
  font-family: var(--sans);
}
.radar-legend {
  list-style: none;
  margin: 0;
  padding: 0;
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.radar-legend li {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}
.radar-legend .dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.radar-legend .lg-name {
  flex: 1;
  min-width: 0;
  color: var(--k0);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.radar-legend .lg-avg {
  font-family: var(--serif);
  font-weight: 600;
  color: var(--k0);
  flex-shrink: 0;
}

.dim-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.dim-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.dim-accent {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.dim-name {
  flex: 1;
  min-width: 0;
  font-size: 14px;
  font-weight: 600;
  color: var(--k0);
  line-height: 1.3;
}
.dim-pct {
  font-family: var(--serif);
  font-size: 16px;
  font-weight: 600;
  color: var(--k0);
  flex-shrink: 0;
}
.dim-bar-track {
  height: 8px;
  background: var(--k8);
  border-radius: var(--r-xs);
  overflow: hidden;
  margin-bottom: 6px;
}
.dim-bar-fill {
  height: 100%;
  border-radius: var(--r-xs);
  min-width: 2px;
  transition: width 0.45s ease;
}
.dim-meta {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  font-size: 12px;
  color: var(--k3);
}

.actions {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.btn-primary,
.btn-ghost {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 44px;
  padding: 12px 20px;
  border-radius: var(--r-md);
  font-size: 14px;
  font-weight: 600;
  text-decoration: none;
  transition: opacity 0.15s, background 0.15s, border-color 0.15s;
}
.btn-primary {
  background: var(--k0);
  color: var(--wh);
  border: 1px solid var(--k0);
  cursor: pointer;
  font-family: inherit;
}
.btn-primary:hover:not(:disabled) {
  opacity: 0.92;
}
.btn-primary:disabled {
  opacity: 0.65;
  cursor: wait;
}
.swot-error {
  width: 100%;
  margin: 0;
  font-size: 13px;
  color: #8f2b2b;
}
.btn-ghost {
  background: var(--wh);
  color: var(--k0);
  border: 1px solid var(--bd);
  cursor: pointer;
  font-family: inherit;
}
.btn-ghost:hover:not(:disabled) {
  border-color: var(--goldbd);
  background: var(--k9);
}
.btn-ghost:disabled {
  opacity: 0.65;
  cursor: wait;
}

/* —— Tablet+ —— */
@media (min-width: 560px) {
  .wrap {
    padding: 22px 20px 56px;
  }
  .kpi-grid {
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
  }
  .hero-score {
    flex-direction: row;
    align-items: center;
    text-align: left;
    gap: 28px;
    padding: 8px 8px 4px;
  }
  .score-line {
    justify-content: flex-start;
  }
  .actions {
    flex-direction: row;
    flex-wrap: wrap;
  }
  .btn-primary,
  .btn-ghost {
    width: auto;
    min-width: 160px;
  }
}

@media (min-width: 800px) {
  .card {
    padding: 22px;
  }
  .hero {
    margin-bottom: 16px;
  }
  .split {
    display: grid;
    grid-template-columns: minmax(260px, 0.95fr) minmax(280px, 1.05fr);
    gap: 16px;
    align-items: start;
  }
  .radar-svg {
    width: min(100%, 300px);
  }
  .score-ring {
    width: 156px;
    height: 156px;
  }
  .ring-pct {
    font-size: 32px;
  }
  .score-value {
    font-size: 40px;
  }
}
</style>
