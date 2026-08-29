<script setup lang="ts">
import { RouterLink } from 'vue-router'
import AppModal from '@/components/ui/AppModal.vue'
import AppButton from '@/components/ui/AppButton.vue'
import type { ProjetosListEditor } from '@/composables/useProjetosList'

const props = defineProps<{ editor: ProjetosListEditor }>()
const {
  items, deleteTarget, deleteError, importState, importError, importOkMsg, fileInput,
  plotPoints, unscoredCount, hoverPoint, tooltipPos, tooltipRef, approvingId, approveError,
  CANVAS_QUADRANT_LABEL, PORTFOLIO_PLOT, PORTFOLIO_VIEWBOX,
  formatDate, clipText, openProject, showChartTooltip, placeChartTooltip, hideChartTooltip,
  creating, onCreate, openImportPicker, onImportFile, askDelete, cancelDelete,
  onApprovePortfolio, confirmDelete,
} = props.editor
</script>

<template>
      <div class="card card-chart">
        <div class="chart-head">
          <h2 class="chart-title">Gráfico dos Quadrantes</h2>
          <p class="chart-sub">
            Posição pelo score de Valor × Viabilidade (1–5) no bloco Decisão do canvas.
            <template v-if="unscoredCount > 0">
              {{ unscoredCount }} projeto{{ unscoredCount === 1 ? '' : 's' }} ainda sem pontuação.
            </template>
          </p>
        </div>

        <div class="chart-body">
          <svg
            class="quad-svg"
            :viewBox="`0 0 ${PORTFOLIO_VIEWBOX.w} ${PORTFOLIO_VIEWBOX.h}`"
            role="img"
            aria-label="Matriz de valor versus viabilidade com os projetos pontuados"
          >
            <rect
              :x="PORTFOLIO_PLOT.x"
              :y="PORTFOLIO_PLOT.y"
              :width="PORTFOLIO_PLOT.w / 2"
              :height="PORTFOLIO_PLOT.h / 2"
              class="qbg qbg-bet"
            />
            <rect
              :x="PORTFOLIO_PLOT.x + PORTFOLIO_PLOT.w / 2"
              :y="PORTFOLIO_PLOT.y"
              :width="PORTFOLIO_PLOT.w / 2"
              :height="PORTFOLIO_PLOT.h / 2"
              class="qbg qbg-go"
            />
            <rect
              :x="PORTFOLIO_PLOT.x"
              :y="PORTFOLIO_PLOT.y + PORTFOLIO_PLOT.h / 2"
              :width="PORTFOLIO_PLOT.w / 2"
              :height="PORTFOLIO_PLOT.h / 2"
              class="qbg qbg-avoid"
            />
            <rect
              :x="PORTFOLIO_PLOT.x + PORTFOLIO_PLOT.w / 2"
              :y="PORTFOLIO_PLOT.y + PORTFOLIO_PLOT.h / 2"
              :width="PORTFOLIO_PLOT.w / 2"
              :height="PORTFOLIO_PLOT.h / 2"
              class="qbg qbg-inc"
            />

            <text
              :x="PORTFOLIO_PLOT.x + PORTFOLIO_PLOT.w / 4"
              :y="PORTFOLIO_PLOT.y + 22"
              class="qlabel qlabel-bet"
              text-anchor="middle"
            >Aposta estratégica</text>
            <text
              :x="PORTFOLIO_PLOT.x + (PORTFOLIO_PLOT.w * 3) / 4"
              :y="PORTFOLIO_PLOT.y + 22"
              class="qlabel qlabel-go"
              text-anchor="middle"
            >Ganho rápido</text>
            <text
              :x="PORTFOLIO_PLOT.x + PORTFOLIO_PLOT.w / 4"
              :y="PORTFOLIO_PLOT.y + PORTFOLIO_PLOT.h / 2 + 22"
              class="qlabel qlabel-avoid"
              text-anchor="middle"
            >Evitar · vaidade</text>
            <text
              :x="PORTFOLIO_PLOT.x + (PORTFOLIO_PLOT.w * 3) / 4"
              :y="PORTFOLIO_PLOT.y + PORTFOLIO_PLOT.h / 2 + 22"
              class="qlabel qlabel-inc"
              text-anchor="middle"
            >Incremental</text>

            <line
              :x1="PORTFOLIO_PLOT.x + PORTFOLIO_PLOT.w / 2"
              :y1="PORTFOLIO_PLOT.y"
              :x2="PORTFOLIO_PLOT.x + PORTFOLIO_PLOT.w / 2"
              :y2="PORTFOLIO_PLOT.y + PORTFOLIO_PLOT.h"
              class="axis-cross"
            />
            <line
              :x1="PORTFOLIO_PLOT.x"
              :y1="PORTFOLIO_PLOT.y + PORTFOLIO_PLOT.h / 2"
              :x2="PORTFOLIO_PLOT.x + PORTFOLIO_PLOT.w"
              :y2="PORTFOLIO_PLOT.y + PORTFOLIO_PLOT.h / 2"
              class="axis-cross"
            />

            <rect
              :x="PORTFOLIO_PLOT.x"
              :y="PORTFOLIO_PLOT.y"
              :width="PORTFOLIO_PLOT.w"
              :height="PORTFOLIO_PLOT.h"
              class="plot-frame"
              fill="none"
            />

            <text
              :x="PORTFOLIO_PLOT.x + PORTFOLIO_PLOT.w / 2"
              :y="PORTFOLIO_PLOT.y + PORTFOLIO_PLOT.h + 38"
              class="axis-caption"
              text-anchor="middle"
            >Viabilidade →</text>
            <text
              :x="20"
              :y="PORTFOLIO_PLOT.y + PORTFOLIO_PLOT.h / 2"
              class="axis-caption"
              text-anchor="middle"
              :transform="`rotate(-90, 20, ${PORTFOLIO_PLOT.y + PORTFOLIO_PLOT.h / 2})`"
            >Valor →</text>

            <g v-for="n in 5" :key="'tx' + n">
              <text
                :x="PORTFOLIO_PLOT.x + ((n - 1) / 4) * PORTFOLIO_PLOT.w"
                :y="PORTFOLIO_PLOT.y + PORTFOLIO_PLOT.h + 16"
                class="tick"
                text-anchor="middle"
              >{{ n }}</text>
            </g>
            <g v-for="n in 5" :key="'ty' + n">
              <text
                :x="PORTFOLIO_PLOT.x - 12"
                :y="PORTFOLIO_PLOT.y + PORTFOLIO_PLOT.h - ((n - 1) / 4) * PORTFOLIO_PLOT.h + 4"
                class="tick"
                text-anchor="end"
              >{{ n }}</text>
            </g>

            <g
              v-for="p in plotPoints"
              :key="p.id"
              class="dot-group"
              role="link"
              tabindex="0"
              :aria-label="`${p.title}. ${CANVAS_QUADRANT_LABEL[p.quadrant]}. Valor ${p.score_valor}, Viabilidade ${p.score_viabilidade}. Abrir canvas.`"
              @click="openProject(p.id)"
              @keydown.enter.prevent="openProject(p.id)"
              @keydown.space.prevent="openProject(p.id)"
              @mouseenter="showChartTooltip($event, p)"
              @mousemove="placeChartTooltip($event)"
              @mouseleave="hideChartTooltip"
            >
              <circle
                :cx="p.cx"
                :cy="p.cy"
                r="13"
                class="dot"
                :data-q="p.quadrant"
              />
              <text
                :x="p.cx"
                :y="p.cy + 4"
                class="dot-label"
                text-anchor="middle"
              >{{ p.title.slice(0, 1).toUpperCase() }}</text>
            </g>
          </svg>

          <p v-if="plotPoints.length === 0" class="chart-empty">
            Nenhum projeto pontuado ainda. Abra um canvas e preencha Valor e Viabilidade no bloco 08.
          </p>
        </div>
      </div>

      <div class="card card-cta">
        <input
          ref="fileInput"
          type="file"
          accept="application/json,.json"
          class="sr-only"
          @change="onImportFile"
        />
        <button type="button" class="btn-new" :disabled="creating" @click="onCreate">
          {{ creating ? 'Criando…' : '+ Novo projeto' }}
        </button>
        <button
          type="button"
          class="btn-import"
          :disabled="importState === 'importing'"
          @click="openImportPicker"
        >
          {{ importState === 'importing' ? 'Importando…' : 'Importar JSON' }}
        </button>
      </div>

      <div v-if="importState === 'error'" class="card error-msg">{{ importError }}</div>
      <div v-else-if="importState === 'ok'" class="card import-ok">{{ importOkMsg }}</div>

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
              <dl class="list-fields">
                <div class="list-field">
                  <dt>Área de negócio</dt>
                  <dd>{{ item.area_negocio || '—' }}</dd>
                </div>
                <div class="list-field">
                  <dt>Responsável</dt>
                  <dd>{{ item.responsavel || '—' }}</dd>
                </div>
                <div class="list-field">
                  <dt>Data</dt>
                  <dd>{{ item.data || '—' }}</dd>
                </div>
                <div class="list-field list-field-wide">
                  <dt>Objetivo estratégico da área</dt>
                  <dd>{{ item.objetivo_estrategico || '—' }}</dd>
                </div>
                <div class="list-field list-field-wide">
                  <dt>Próximo passo concreto</dt>
                  <dd>{{ item.proximo_passo || '—' }}</dd>
                </div>
              </dl>
              <div class="list-foot">
                <span v-if="item.quadrant" class="list-quad" :data-q="item.quadrant">
                  {{ CANVAS_QUADRANT_LABEL[item.quadrant] }}
                </span>
                <span class="list-meta">Atualizado {{ formatDate(item.updated_at) }}</span>
              </div>
            </div>
            <span class="list-arrow">Abrir canvas →</span>
          </RouterLink>
          <div class="list-actions">
            <RouterLink
              v-if="item.status === 'aprovado_portfolio' && item.ai_system_id"
              :to="`/governanca/sistemas/${item.ai_system_id}`"
              class="badge-portfolio"
              title="Ver na Governança de IA"
              @click.stop
            >
              No portfólio ✓
            </RouterLink>
            <button
              v-else
              type="button"
              class="btn-approve"
              :disabled="approvingId === item.id"
              @click="onApprovePortfolio(item, $event)"
            >
              {{ approvingId === item.id ? 'Aprovando…' : 'Aprovar para portfólio' }}
            </button>
            <button
              type="button"
              class="btn-del"
              title="Excluir projeto"
              @click="askDelete(item, $event)"
            >
              Excluir
            </button>
          </div>
        </li>
      </ul>
      <p v-if="approveError" class="error-msg">{{ approveError }}</p>

    <Teleport to="body">
      <div
        ref="tooltipRef"
        class="chart-tooltip"
        :class="{ visible: !!hoverPoint }"
        :style="{ left: tooltipPos.x + 'px', top: tooltipPos.y + 'px' }"
        role="tooltip"
      >
        <template v-if="hoverPoint">
          <div class="chart-tooltip-title">{{ hoverPoint.title }}</div>
          <div class="chart-tooltip-quad" :data-q="hoverPoint.quadrant">
            {{ CANVAS_QUADRANT_LABEL[hoverPoint.quadrant] }}
          </div>
          <dl class="chart-tooltip-dl">
            <div>
              <dt>Valor</dt>
              <dd>{{ hoverPoint.score_valor }} / 5</dd>
            </div>
            <div>
              <dt>Viabilidade</dt>
              <dd>{{ hoverPoint.score_viabilidade }} / 5</dd>
            </div>
            <div v-if="hoverPoint.area_negocio">
              <dt>Área</dt>
              <dd>{{ hoverPoint.area_negocio }}</dd>
            </div>
            <div v-if="hoverPoint.responsavel">
              <dt>Responsável</dt>
              <dd>{{ hoverPoint.responsavel }}</dd>
            </div>
            <div v-if="hoverPoint.objetivo_estrategico" class="chart-tooltip-wide">
              <dt>Objetivo estratégico</dt>
              <dd>{{ clipText(hoverPoint.objetivo_estrategico) }}</dd>
            </div>
            <div v-if="hoverPoint.proximo_passo" class="chart-tooltip-wide">
              <dt>Próximo passo</dt>
              <dd>{{ clipText(hoverPoint.proximo_passo) }}</dd>
            </div>
          </dl>
          <p class="chart-tooltip-hint">Clique para abrir o canvas</p>
        </template>
      </div>
    </Teleport>

    <AppModal :open="!!deleteTarget" title="Excluir projeto?" size="sm" @close="cancelDelete">
      <p v-if="deleteTarget">
        Remover <strong>{{ deleteTarget.title }}</strong> e o canvas preenchido. Esta ação não pode ser desfeita.
      </p>
      <p v-if="deleteError" class="error-msg">{{ deleteError }}</p>
      <template #footer>
        <AppButton variant="secondary" @click="cancelDelete">Cancelar</AppButton>
        <AppButton variant="danger" @click="confirmDelete">Excluir</AppButton>
      </template>
    </AppModal>
</template>

<style scoped>
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
.card-chart {
  padding: 22px 22px 16px;
}
.chart-head {
  margin-bottom: 12px;
}
.chart-title {
  font-family: var(--serif);
  font-size: 20px;
  color: var(--k0);
  margin: 0 0 4px;
}
.chart-sub {
  font-size: 13px;
  color: var(--k3);
  margin: 0;
  line-height: 1.45;
}
.chart-body {
  display: flex;
  flex-direction: column;
  align-items: center;
}
.quad-svg {
  width: 100%;
  max-width: 100%;
  height: auto;
  display: block;
}
.qbg-bet {
  fill: #f3e7cc;
}
.qbg-go {
  fill: #e8f0e7;
}
.qbg-avoid {
  fill: #f1e1dd;
}
.qbg-inc {
  fill: #e4ecee;
}
.qlabel {
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.03em;
  pointer-events: none;
}
.qlabel-bet {
  fill: #c48a26;
}
.qlabel-go {
  fill: #2f6e4a;
}
.qlabel-avoid {
  fill: #9c3b2e;
}
.qlabel-inc {
  fill: #5b7a86;
}
.axis-cross {
  stroke: rgba(18, 35, 46, 0.18);
  stroke-width: 1;
  stroke-dasharray: 4 3;
}
.plot-frame {
  stroke: rgba(18, 35, 46, 0.35);
  stroke-width: 1.25;
}
.axis-caption {
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  fill: #3c525f;
}
.tick {
  font-size: 11px;
  fill: #6b7e9a;
}
.dot-group {
  cursor: pointer;
}
.dot-group:focus {
  outline: none;
}
.dot-group:focus .dot,
.dot-group:hover .dot {
  stroke-width: 2.5;
  stroke: #12232e;
}
.dot {
  stroke: #fff;
  stroke-width: 1.5;
}
.dot[data-q='ganho_rapido'] {
  fill: #2f6e4a;
}
.dot[data-q='aposta_estrategica'] {
  fill: #c48a26;
}
.dot[data-q='incremental'] {
  fill: #5b7a86;
}
.dot[data-q='evitar'] {
  fill: #9c3b2e;
}
.dot-label {
  fill: #fff;
  font-size: 11px;
  font-weight: 700;
  pointer-events: none;
}
.chart-tooltip {
  position: fixed;
  z-index: 500;
  max-width: 340px;
  min-width: 220px;
  background: var(--k0);
  color: var(--wh);
  padding: 16px 18px 14px;
  border-radius: var(--r-md);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.28);
  pointer-events: none;
  opacity: 0;
  visibility: hidden;
  transition: opacity 0.12s ease, visibility 0.12s ease;
}
.chart-tooltip.visible {
  opacity: 1;
  visibility: visible;
}
.chart-tooltip-title {
  font-family: var(--serif);
  font-size: 17px;
  line-height: 1.3;
  color: #fff;
  margin-bottom: 8px;
}
.chart-tooltip-quad {
  display: inline-flex;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  padding: 3px 8px;
  border-radius: var(--r-pill);
  margin-bottom: 12px;
  background: rgba(255, 255, 255, 0.12);
  color: rgba(255, 255, 255, 0.9);
}
.chart-tooltip-quad[data-q='ganho_rapido'] {
  background: #2f6e4a;
  color: #fff;
}
.chart-tooltip-quad[data-q='aposta_estrategica'] {
  background: #c48a26;
  color: #fff;
}
.chart-tooltip-quad[data-q='incremental'] {
  background: #5b7a86;
  color: #fff;
}
.chart-tooltip-quad[data-q='evitar'] {
  background: #9c3b2e;
  color: #fff;
}
.chart-tooltip-dl {
  margin: 0;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px 14px;
}
.chart-tooltip-dl .chart-tooltip-wide {
  grid-column: 1 / -1;
}
.chart-tooltip-dl dt {
  margin: 0;
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.5);
}
.chart-tooltip-dl dd {
  margin: 2px 0 0;
  font-size: 13px;
  line-height: 1.4;
  color: rgba(255, 255, 255, 0.92);
}
.chart-tooltip-hint {
  margin: 12px 0 0;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.45);
}
.chart-empty {
  font-size: 13px;
  color: var(--k3);
  text-align: center;
  margin: 8px 0 12px;
  max-width: 42ch;
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
  border-radius: var(--r-md);
  font-size: 14px;
  cursor: pointer;
}
.btn-new:disabled {
  opacity: 0.6;
  cursor: wait;
}
.card-cta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}
.btn-import {
  display: inline-flex;
  align-items: center;
  padding: 10px 18px;
  background: #fff;
  color: var(--k0);
  border: 1px solid var(--bd);
  border-radius: var(--r-md);
  font-size: 14px;
  cursor: pointer;
  font-family: inherit;
}
.btn-import:hover:not(:disabled) {
  border-color: var(--k0);
}
.btn-import:disabled {
  opacity: 0.6;
  cursor: wait;
}
.import-ok {
  color: #2f6e4a;
  border-color: #bbd3b7;
  background: #e8f0e7;
}
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
.card-empty {
  text-align: center;
  color: var(--k3);
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
  border-radius: var(--r-lg);
  overflow: hidden;
}
.list-link {
  flex: 1;
  display: flex;
  align-items: flex-start;
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
  gap: 10px;
  min-width: 0;
  flex: 1;
}
.list-title {
  font-weight: 600;
  font-size: 16px;
  color: var(--k0);
}
.list-fields {
  margin: 0;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px 14px;
}
.list-field {
  min-width: 0;
}
.list-field-wide {
  grid-column: 1 / -1;
}
.list-field dt {
  margin: 0;
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--k3);
}
.list-field dd {
  margin: 3px 0 0;
  font-size: 13px;
  color: var(--k0);
  line-height: 1.4;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
.list-foot {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 12px;
}
.list-meta {
  font-size: 12px;
  color: var(--k3);
}
.list-quad {
  display: inline-flex;
  width: fit-content;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  padding: 3px 8px;
  border-radius: var(--r-pill);
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
  color: var(--k3);
  white-space: nowrap;
  margin-top: 2px;
}
@media (max-width: 640px) {
  .list-fields {
    grid-template-columns: 1fr;
  }
  .list-arrow {
    display: none;
  }
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
.btn-approve {
  border: none;
  background: transparent;
  color: var(--k4);
  padding: 0 14px;
  font-size: 12px;
  cursor: pointer;
  border-left: 1px solid var(--bd);
  white-space: nowrap;
}
.btn-approve:hover:not(:disabled) {
  background: var(--k9);
}
.btn-approve:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}
.badge-portfolio {
  padding: 4px 14px;
  font-size: 12px;
  font-weight: 600;
  color: var(--k0);
  background: var(--golddim);
  border-left: 1px solid var(--bd);
  text-decoration: none;
  white-space: nowrap;
}
.badge-portfolio:hover {
  background: var(--goldbd);
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
</style>
