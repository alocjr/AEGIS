<script setup lang="ts">
import { RouterLink } from 'vue-router'
import type { MaturityEditor } from '@/composables/useMaturityEditor'

const props = defineProps<{ editor: MaturityEditor }>()
const {
  model, answers, selectedTier, responseId, isEditingExisting,
  saveState, saveError, swotId, swotBusy, swotError,
  answeredCount, totalVisible, isComplete, progressPct, progressLabel, selectedTierDescription,
  MATURITY_TIER_KEYS, MATURITY_TIER_LABEL_SHORT, MATURITY_DIMENSION_ABBR,
  isVisibleTier, sortedQuestions, maturityOriginLine, maturityDimensionAccent,
  dimVisibleQuestions, dimAnswered, dimAvg, setTier, toggleSelect,
  openSwot, scrollToDim, onCellKeydown,
} = props.editor
</script>

<template>
  <div v-if="model">
      <nav v-if="isEditingExisting && responseId" class="edit-nav">
        <RouterLink :to="`/ai-maturity/${responseId}`" class="edit-back">← Ver resultado</RouterLink>
        <RouterLink to="/ai-maturity" class="edit-back muted">Todas as autoavaliações</RouterLink>
      </nav>
      <header class="page-header">
        <div class="header-main">
          <p class="eyebrow">
            {{ isEditingExisting ? 'Editando autoavaliação · Valorian' : 'Instrumento diagnóstico · Valorian' }}
          </p>
          <h1 class="page-title">Maturidade em <em>IA</em></h1>
          <p class="page-desc">
            <template v-if="isEditingExisting">
              Suas respostas foram carregadas. Altere o que precisar — o salvamento continua automático
              e o resultado (e a SWOT, se existir) acompanham as mudanças.
            </template>
            <template v-else>
              Avalie a organização em quatro dimensões. Escolha a abrangência do diagnóstico
              (Básico, Completo ou Complementar) e, em cada pergunta, selecione a alternativa
              na escala de maturidade de 1 a 5 que melhor descreve a realidade da empresa.
            </template>
          </p>
        </div>

        <div class="header-tier">
          <p class="tier-label">Abrangência do diagnóstico</p>
          <div class="tier-select" role="tablist" aria-label="Abrangência do diagnóstico">
            <button
              v-for="key in MATURITY_TIER_KEYS"
              :key="key"
              type="button"
              class="tier-btn"
              :class="{ active: selectedTier === key }"
              :title="model.levels?.[key]?.description || ''"
              @click="setTier(key)"
            >
              <span class="tier-name">{{ model.levels?.[key]?.label ?? MATURITY_TIER_LABEL_SHORT[key] }}</span>
              <span class="tier-count">{{ model.levels?.[key]?.question_count ?? 0 }} perguntas</span>
            </button>
          </div>
          <p v-if="selectedTierDescription" class="tier-hint">{{ selectedTierDescription }}</p>
        </div>

        <div class="header-chart" aria-label="Média por dimensão">
          <p class="chart-title">Média por dimensão</p>
          <div class="chart-bars">
            <div
              v-for="dim in model.dimensions"
              :key="'bar-' + dim.id"
              class="chart-bar-col"
            >
              <span class="chart-bar-value">
                {{ dimAvg(dim) == null ? '–' : dimAvg(dim)!.toFixed(1) }}
              </span>
              <div class="chart-bar-track">
                <div
                  class="chart-bar-fill"
                  :style="{
                    background: maturityDimensionAccent(dim.id) || 'var(--gold)',
                    height: dimAvg(dim) == null ? '0%' : (dimAvg(dim)! / 5) * 100 + '%',
                  }"
                />
              </div>
              <span class="chart-bar-label">{{ MATURITY_DIMENSION_ABBR[dim.id] || dim.name.slice(0, 3) }}</span>
            </div>
          </div>
        </div>
      </header>

      <div class="toolbar">
        <div class="progress-block">
          <div class="num">{{ answeredCount }}/{{ totalVisible }}</div>
          <div class="progress-meta">
            <div class="progress-track">
              <div class="progress-fill" :style="{ width: progressPct + '%' }" />
            </div>
            <div class="progress-label">{{ progressLabel }}</div>
          </div>
        </div>

        <div class="toolbar-actions">
          <span
            class="save-pill"
            :data-state="saveState"
            :title="saveError || undefined"
          >
            <template v-if="saveState === 'saving'">Salvando…</template>
            <template v-else-if="saveState === 'saved'">Salvo</template>
            <template v-else-if="saveState === 'error'">Falha ao salvar</template>
            <template v-else>Respostas salvas ao clicar</template>
          </span>
          <button
            v-if="isComplete"
            type="button"
            class="btn-swot"
            :disabled="swotBusy || !responseId"
            @click="openSwot"
          >
            {{
              swotBusy
                ? 'Gerando…'
                : swotId
                  ? 'Atualizar SWOT'
                  : 'Criar SWOT'
            }}
          </button>
          <span v-if="swotError" class="swot-error" :title="swotError">{{ swotError }}</span>
        </div>

        <div class="scale-legend" title="Escala de resposta por pergunta">
          <span>Escala&nbsp;</span>
          <div class="swatch">
            <span style="background: var(--lvl1)" />
            <span style="background: var(--lvl2)" />
            <span style="background: var(--lvl3)" />
            <span style="background: var(--lvl4)" />
            <span style="background: var(--lvl5)" />
          </div>
          <span>1 → 5</span>
        </div>

        <nav class="pillar-nav" aria-label="Dimensões">
          <button
            v-for="(dim, dIdx) in model.dimensions"
            :key="'nav-' + dim.id"
            type="button"
            class="pillar-chip"
            @click="scrollToDim(dIdx)"
          >
            <span class="dot" :style="{ background: maturityDimensionAccent(dim.id) || 'var(--gold)' }" />
            {{ dim.name }}
            <span class="n">{{ dimAnswered(dim).length }}/{{ dimVisibleQuestions(dim).length }}</span>
          </button>
        </nav>
      </div>

      <div class="matrix-wrap">
        <div class="matrix-scroll">
          <div class="col-legend" aria-hidden="true">
            <div class="stem-head" />
            <div v-for="n in 5" :key="'lh-' + n" class="lvl-head" :data-l="n">
              <span class="tag">{{ n }}</span>
              <span class="word">Maturidade</span>
            </div>
          </div>

          <section
            v-for="(dim, dIdx) in model.dimensions"
            :id="'dim-' + dIdx"
            :key="dim.id"
            class="pillar-section"
          >
            <div
              class="pillar-band"
              :style="{ '--dim-color': maturityDimensionAccent(dim.id) || 'var(--gold)' }"
            >
              <h2>{{ dim.name }}</h2>
              <div class="pillar-meta">
                <span class="avg">
                  Média
                  <span class="bulbs">
                    <i
                      v-for="n in 5"
                      :key="'b-' + dim.id + '-' + n"
                      :class="{ on: dimAvg(dim) != null && n <= Math.round(dimAvg(dim)!) }"
                    />
                  </span>
                </span>
                <span>{{ dimAnswered(dim).length }}/{{ dimVisibleQuestions(dim).length }}</span>
              </div>
            </div>

            <div
              v-for="q in sortedQuestions(dim)"
              v-show="isVisibleTier(q.tier)"
              :key="q.id"
              class="csf-row"
            >
              <div class="stem">
                <span
                  class="code"
                  :style="{
                    background: 'color-mix(in srgb, ' + (maturityDimensionAccent(dim.id) || 'var(--gold)') + ' 18%, transparent)',
                    color: maturityDimensionAccent(dim.id) || 'var(--gold)',
                  }"
                >{{ q.id }}</span>
                <span class="tier-pill" :data-tier="q.tier">{{ MATURITY_TIER_LABEL_SHORT[q.tier] }}</span>
                <p class="title">{{ q.text }}</p>
                <p class="q">{{ maturityOriginLine(q) }}</p>
              </div>

              <div
                v-for="lvl in 5"
                :key="q.id + '-' + lvl"
                class="cell"
                :class="{
                  selected: answers[q.id] === lvl,
                  faded: answers[q.id] != null && answers[q.id] !== lvl,
                }"
                :data-l="lvl"
                tabindex="0"
                role="button"
                :aria-pressed="answers[q.id] === lvl"
                @click="toggleSelect(q.id, lvl)"
                @keydown="onCellKeydown($event, q.id, lvl)"
              >
                <span class="txt">{{ q.levels[String(lvl)] }}</span>
              </div>
            </div>
          </section>
        </div>

        <div class="footnote">
          <b>Como funciona:</b> a abrangência (Básico → Completo → Complementar) é progressiva —
          cada opção inclui todas as perguntas da anterior. Trocar a abrangência só mostra ou
          esconde perguntas; as respostas já dadas permanecem e são salvas automaticamente a cada
          clique. Em cada pergunta, escolha uma alternativa na escala de maturidade 1–5. No celular,
          as alternativas aparecem empilhadas; em telas largas, em matriz. Ao concluir, você pode
          gerar a SWOT.
        </div>

        <details v-if="model.overlaps?.length" class="overlap-notes">
          <summary>
            Notas de sobreposição entre perguntas ({{ model.overlaps.length }})
          </summary>
          <ul>
            <li v-for="(o, i) in model.overlaps" :key="'ov-' + i">
              <span class="overlap-pair">{{ o.pair.join(' × ') }}</span>
              — {{ o.distinction }}
            </li>
          </ul>
        </details>
      </div>
  </div>
</template>

<style scoped>
.edit-nav {
  display: flex;
  flex-wrap: wrap;
  gap: 12px 18px;
  margin-bottom: 14px;
}
.edit-back {
  font-size: 13px;
  font-weight: 600;
  color: var(--navy, #0e1b33);
  text-decoration: none;
}
.edit-back:hover {
  color: var(--gold-text);
}
.edit-back.muted {
  color: var(--muted, #6e6a60);
  font-weight: 500;
}
.state-card {
  background: var(--ivory-2);
  border: 1px solid var(--line);
  border-radius: var(--r-xs);
  padding: 24px 18px;
  text-align: center;
  color: var(--muted);
}
.state-card.error {
  color: var(--oxblood);
  text-align: left;
}

.page-header {
  display: flex;
  flex-direction: column;
  gap: 18px;
  margin-bottom: 18px;
}
.header-main {
  min-width: 0;
}
.eyebrow {
  font-size: 0.7rem;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: var(--gold-text);
  font-weight: 600;
  margin: 0 0 6px;
}
.page-title {
  font-family: var(--serif);
  font-weight: 600;
  font-size: clamp(1.9rem, 5.5vw, 2.6rem);
  line-height: 1.05;
  color: var(--ink);
  margin: 0 0 8px;
}
.page-title em {
  font-style: italic;
  color: var(--gold-text);
}
.page-desc {
  margin: 0;
  color: var(--muted);
  font-size: 14px;
  line-height: 1.55;
  max-width: 52ch;
}
.header-tier {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  min-width: 0;
  text-align: center;
}
.header-chart {
  background: var(--ivory-2);
  border: 1px solid var(--line);
  border-radius: var(--r-xs);
  padding: 14px 16px;
  flex: 0 0 auto;
}
.chart-title {
  font-size: 0.7rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--muted);
  font-weight: 600;
  margin: 0 0 10px;
}
.chart-bars {
  display: flex;
  align-items: flex-end;
  gap: 14px;
  height: 88px;
}
.chart-bar-col {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  width: 28px;
}
.chart-bar-value {
  font-family: var(--serif);
  font-size: 12px;
  font-weight: 600;
  color: var(--ink);
  min-height: 14px;
}
.chart-bar-track {
  width: 10px;
  height: 52px;
  background: rgba(198, 161, 91, 0.16);
  border-radius: var(--r-pill);
  display: flex;
  align-items: flex-end;
  overflow: hidden;
}
.chart-bar-fill {
  width: 100%;
  border-radius: var(--r-pill);
  transition: height 0.4s ease;
}
.chart-bar-label {
  font-size: 9px;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--muted);
  font-weight: 600;
}

.toolbar {
  position: sticky;
  top: var(--bar-h, 64px);
  z-index: 40;
  background: rgba(251, 248, 241, 0.96);
  backdrop-filter: blur(8px);
  border: 1px solid var(--line);
  border-radius: var(--r-xs);
  padding: 14px;
  margin-bottom: 14px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.progress-block {
  display: flex;
  align-items: center;
  gap: 12px;
}
.progress-block .num {
  font-family: var(--serif);
  font-size: 22px;
  color: var(--navy);
  font-weight: 600;
  min-width: 52px;
}
.progress-meta {
  flex: 1;
  min-width: 0;
}
.progress-track {
  width: 100%;
  max-width: 240px;
  height: 6px;
  background: rgba(14, 27, 51, 0.08);
  border-radius: var(--r-pill);
  overflow: hidden;
}
.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--navy), var(--gold));
  transition: width 0.35s ease;
}
.progress-label {
  margin-top: 4px;
  font-size: 11px;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--muted);
  line-height: 1.35;
}

.tier-label {
  margin: 0;
  font-size: 0.7rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--muted);
  font-weight: 600;
}
.tier-select {
  display: flex;
  align-items: stretch;
  justify-content: center;
  flex-wrap: nowrap;
  gap: 8px;
}
.tier-btn {
  display: inline-flex;
  flex-direction: column;
  align-items: flex-start;
  justify-content: center;
  gap: 2px;
  padding: 8px 14px;
  border-radius: var(--r-xs);
  border: 1px solid var(--navy);
  background: #fff;
  color: var(--navy);
  cursor: pointer;
  flex: 0 0 auto;
  white-space: nowrap;
  font-family: inherit;
  transition: opacity 0.2s, background 0.15s, color 0.15s;
}
.tier-btn:hover {
  opacity: 0.9;
}
.tier-btn .tier-name {
  font-size: 13px;
  font-weight: 600;
  line-height: 1.2;
}
.tier-btn .tier-count {
  font-size: 11px;
  font-weight: 500;
  opacity: 0.75;
}
.tier-btn.active {
  background: var(--navy);
  border-color: var(--navy);
  color: #fff;
}
.tier-btn.active:hover {
  opacity: 0.9;
}
.tier-hint {
  margin: 0;
  font-size: 12px;
  line-height: 1.45;
  color: var(--muted);
  max-width: 36ch;
  text-align: center;
}
.toolbar-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: stretch;
  gap: 8px;
}

.scale-legend {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
  color: var(--muted);
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}
.scale-legend .swatch {
  display: flex;
  gap: 3px;
}
.scale-legend .swatch span {
  width: 14px;
  height: 14px;
  border-radius: 2px;
  display: block;
}

.pillar-nav {
  display: flex;
  gap: 6px;
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}
.pillar-chip {
  font-size: 11px;
  letter-spacing: 0.02em;
  padding: 7px 11px;
  border-radius: var(--r-pill);
  border: 1px solid var(--line);
  color: var(--muted);
  background: #fff;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
  flex: 0 0 auto;
  white-space: nowrap;
  font-family: inherit;
  transition: 0.15s;
}
.pillar-chip:hover {
  border-color: var(--gold-text);
  color: var(--navy);
}
.pillar-chip .dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex: 0 0 auto;
}
.pillar-chip .n {
  opacity: 0.7;
}

.btn-swot {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  box-sizing: border-box;
  padding: 8px 14px;
  border-radius: var(--r-pill);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  cursor: pointer;
  font-family: inherit;
  transition: 0.15s;
  flex: 0 0 auto;
  white-space: nowrap;
  line-height: 1.2;
  border: 1px solid var(--gold);
  background: var(--gold);
  color: var(--navy);
}
.btn-swot:hover:not(:disabled) {
  background: var(--gold-light);
  border-color: var(--gold-light);
}
.btn-swot:disabled {
  opacity: 0.65;
  cursor: wait;
}
.swot-error {
  font-size: 11px;
  color: var(--lvl1, #b6543f);
  max-width: 220px;
  line-height: 1.3;
}
.save-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  box-sizing: border-box;
  padding: 8px 14px;
  border-radius: var(--r-pill);
  border: 1px solid var(--line);
  background: #fff;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--muted);
  flex: 0 0 auto;
  white-space: nowrap;
  line-height: 1.2;
}
.save-pill[data-state='saving'] {
  color: var(--navy);
}
.save-pill[data-state='saved'] {
  color: #2f6e4a;
  border-color: #bbd3b7;
  background: #e8f0e7;
}
.save-pill[data-state='error'] {
  color: var(--oxblood);
  border-color: #ddbcb4;
  background: #f1e1dd;
  text-transform: none;
  letter-spacing: 0;
  white-space: normal;
}

.matrix-wrap {
  margin-top: 4px;
}
.matrix-scroll {
  overflow-x: visible;
}
.col-legend {
  display: none;
}
.lvl-head {
  font-size: 11px;
  letter-spacing: 0.04em;
  color: var(--muted);
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 6px;
  padding: 0 4px 6px;
  border-bottom: 2px solid;
}
.lvl-head .tag {
  font-weight: 700;
  font-size: 13px;
  font-family: var(--serif);
}
.lvl-head .word {
  text-transform: uppercase;
  font-size: 9px;
  letter-spacing: 0.08em;
  opacity: 0.75;
}
.lvl-head[data-l='1'] { border-color: var(--lvl1); color: var(--lvl1); }
.lvl-head[data-l='2'] { border-color: var(--lvl2); color: var(--lvl2); }
.lvl-head[data-l='3'] { border-color: var(--lvl3); color: var(--lvl3); }
.lvl-head[data-l='4'] { border-color: var(--lvl4); color: var(--lvl4); }
.lvl-head[data-l='5'] { border-color: var(--lvl5); color: var(--lvl5); }

.pillar-section {
  margin-bottom: 8px;
}
.pillar-band {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 12px;
  padding: 12px 14px;
  margin-top: 14px;
  border-radius: var(--r-xs);
  background: var(--ivory-2);
  border: 1px solid var(--line);
  border-left: 4px solid var(--dim-color, var(--gold));
  color: var(--navy);
}
.pillar-band h2 {
  font-family: var(--serif);
  font-weight: 600;
  font-size: 17px;
  margin: 0;
  color: var(--navy);
}
.pillar-meta {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 11px;
  color: var(--muted);
  font-weight: 600;
  letter-spacing: 0.03em;
  text-transform: uppercase;
  flex-wrap: wrap;
}
.avg {
  display: flex;
  align-items: center;
  gap: 6px;
}
.bulbs {
  display: flex;
  gap: 3px;
}
.bulbs i {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: rgba(14, 27, 51, 0.12);
  display: inline-block;
}
.bulbs i.on {
  background: var(--gold);
}

.csf-row {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 14px 0;
  border-bottom: 1px solid rgba(14, 27, 51, 0.08);
}
.stem .code {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.03em;
  display: inline-block;
  padding: 2px 7px;
  border-radius: 3px;
  margin-bottom: 6px;
}
.stem .tier-pill {
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  display: inline-block;
  padding: 2px 8px;
  border-radius: var(--r-pill);
  margin: 0 0 6px 6px;
  color: #fff;
}
.stem .tier-pill[data-tier='basico'] { background: var(--tier-basico); }
.stem .tier-pill[data-tier='completo'] { background: var(--tier-completo); color: var(--navy); }
.stem .tier-pill[data-tier='complementar'] { background: var(--tier-complementar); }
.stem .title {
  font-weight: 600;
  font-size: 14px;
  line-height: 1.35;
  margin: 0 0 4px;
  color: var(--navy);
}
.stem .q {
  font-size: 12px;
  line-height: 1.45;
  color: var(--muted);
  font-style: italic;
  margin: 0;
}

.cell {
  background: #fff;
  border: 1px solid var(--line);
  border-radius: var(--r-xs);
  padding: 11px 12px;
  font-size: 13px;
  line-height: 1.42;
  cursor: pointer;
  min-height: 44px;
  transition: transform 0.12s ease, box-shadow 0.12s ease, border-color 0.12s ease, background 0.12s ease;
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--ink);
}
.cell::before {
  content: attr(data-l);
  font-family: var(--serif);
  font-weight: 700;
  font-size: 12px;
  line-height: 1;
  flex: 0 0 auto;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
}
.cell[data-l='1']::before { background: var(--lvl1); }
.cell[data-l='2']::before { background: var(--lvl2); }
.cell[data-l='3']::before { background: var(--lvl3); }
.cell[data-l='4']::before { background: var(--lvl4); }
.cell[data-l='5']::before { background: var(--lvl5); }
.cell:hover {
  border-color: var(--gold-text);
  box-shadow: 0 2px 10px rgba(14, 27, 51, 0.06);
}
.cell:focus-visible {
  outline: 2px solid var(--gold);
  outline-offset: 1px;
}
.cell.faded {
  opacity: 0.42;
}
.cell.selected {
  background: var(--navy);
  border-color: var(--navy);
  color: var(--ivory);
  box-shadow: 0 4px 14px rgba(14, 27, 51, 0.16);
}
.cell.selected::before {
  background: var(--gold);
  color: var(--navy);
}
.cell .txt {
  flex: 1;
  min-width: 0;
  overflow-wrap: anywhere;
  word-break: break-word;
}

.footnote {
  margin: 18px 0 0;
  padding: 12px 14px;
  background: var(--ivory);
  border: 1px dashed var(--line);
  border-radius: var(--r-xs);
  font-size: 12px;
  color: var(--muted);
  line-height: 1.55;
}
.footnote b {
  color: var(--navy);
}
.overlap-notes {
  margin: 12px 0 0;
  padding: 12px 14px;
  background: var(--ivory-2);
  border: 1px solid var(--line);
  border-radius: var(--r-xs);
  font-size: 12px;
  color: var(--muted);
}
.overlap-notes summary {
  cursor: pointer;
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--gold-text);
  font-weight: 700;
}
.overlap-notes ul {
  list-style: none;
  margin: 12px 0 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.overlap-notes li {
  line-height: 1.5;
  padding: 8px 10px;
  background: #fff;
  border-radius: 3px;
  border: 1px solid rgba(14, 27, 51, 0.06);
}
.overlap-pair {
  font-weight: 700;
  color: var(--navy);
  margin-right: 2px;
}

@media (min-width: 640px) {
  .chart-bars {
    height: 100px;
    gap: 16px;
  }
}

@media (min-width: 860px) {
  .page-header {
    flex-direction: row;
    align-items: flex-end;
    justify-content: space-between;
    gap: 24px;
  }
  .header-main {
    flex: 1 1 280px;
  }
  .header-tier {
    flex: 1 1 auto;
  }
  .header-chart {
    flex: 0 0 auto;
  }
  .toolbar {
    flex-direction: row;
    flex-wrap: wrap;
    align-items: center;
    gap: 16px 20px;
    padding: 14px 18px;
  }
  .pillar-nav {
    flex: 1 1 100%;
    overflow-x: visible;
    flex-wrap: wrap;
  }
  .scale-legend {
    margin-left: auto;
  }
}

/* Matriz lado a lado só quando há largura suficiente — sem min-width forçado */
@media (min-width: 1100px) {
  .col-legend {
    display: grid;
    grid-template-columns: minmax(200px, 1.15fr) repeat(5, minmax(0, 1fr));
    gap: 8px;
    padding: 0 0 10px;
    width: 100%;
  }
  .pillar-band {
    position: sticky;
    top: calc(var(--bar-h, 64px) + 12px);
    z-index: 20;
  }
  .csf-row {
    display: grid;
    grid-template-columns: minmax(200px, 1.15fr) repeat(5, minmax(0, 1fr));
    gap: 8px;
    padding: 10px 0;
    width: 100%;
  }
  .stem {
    padding: 4px 8px 4px 0;
    min-width: 0;
  }
  .cell {
    align-items: flex-start;
    font-size: 12px;
    min-height: auto;
    min-width: 0;
    padding: 10px;
  }
  .cell:hover {
    transform: translateY(-1px);
  }
}
</style>
