<script setup lang="ts">
import { computed, nextTick, onUnmounted, watch } from 'vue'
import AppButton from '@/components/ui/AppButton.vue'
import {
  CANVAS_MESES,
  CANVAS_PRIORIDADES,
  type CanvasCronograma,
  type CanvasMesInicio,
  type CanvasPrioridade,
  type CanvasQuadrant,
} from '@/api/canvasProjects'
import {
  ANALISE_CRITERIOS,
  analisePonderada,
  formatNota,
  type CanvasAnaliseExecutiva,
} from '@/lib/canvasAnaliseExecutiva'

const props = defineProps<{
  open: boolean
  title: string
  areaNegocio: string
  responsavel: string
  data: string
  objetivoEstrategico: string
  prioridade: CanvasPrioridade
  mesInicio: CanvasMesInicio
  contexto: string[]
  dores: string[]
  oportunidade: string[]
  oportunidadeTipos: string[]
  dados: string[]
  valor: string[]
  custo: string[]
  riscos: string[]
  scoreValor: number | null
  scoreViabilidade: number | null
  quadrant: CanvasQuadrant
  proximoPasso: string
  justificativaTows: string
  cronograma: CanvasCronograma
  analiseExecutiva?: CanvasAnaliseExecutiva | null
}>()

const emit = defineEmits<{ close: [] }>()

const WEEKS_PER_MONTH = 4
const MONTH_VIEW_AFTER = 12

const prioridadeLabel = computed(() => {
  return CANVAS_PRIORIDADES.find((p) => p.id === props.prioridade)?.label || props.prioridade
})

const mesLabel = computed(() => {
  if (!props.mesInicio) return 'A definir'
  return CANVAS_MESES.find((m) => m.id === props.mesInicio)?.label || props.mesInicio
})

const weeks = computed(() => Array.from({ length: Math.max(1, props.cronograma.semanas || 8) }, (_, i) => i + 1))
const useMonths = computed(() => (props.cronograma.semanas || 0) > MONTH_VIEW_AFTER)
const months = computed(() => {
  const total = props.cronograma.semanas || 8
  const cols: { index: number; start: number; end: number; label: string }[] = []
  let start = 1
  let index = 1
  while (start <= total) {
    const end = Math.min(start + WEEKS_PER_MONTH - 1, total)
    cols.push({ index, start, end, label: `M${index}` })
    start = end + 1
    index += 1
  }
  return cols
})

const horizonteLabel = computed(() => {
  const n = props.cronograma.semanas || 8
  if (n <= MONTH_VIEW_AFTER) return `${n} semanas`
  const meses = Math.ceil(n / WEEKS_PER_MONTH)
  return `${n} sem. · ${meses} ${meses === 1 ? 'mês' : 'meses'}`
})

const analiseScores = computed(() => {
  const scores = props.analiseExecutiva?.scores
  return ANALISE_CRITERIOS.map((c) => ({
    ...c,
    score: scores?.[c.id] ?? null,
  }))
})
const analiseNota = computed(() => analisePonderada(props.analiseExecutiva?.scores))

function items(list: string[]): string[] {
  return (list || []).map((s) => s.trim()).filter(Boolean)
}

function dash(value: string): string {
  const t = (value || '').trim()
  return t || '—'
}

function padId(index: number): string {
  return String(index + 1).padStart(2, '0')
}

function barLabel(start: number, end: number): string {
  if (start === end) return `S${start}`
  return `S${start}–${end}`
}

function barColor(start: number): string {
  const n = props.cronograma.semanas || 8
  const t = start / n
  if (t >= 0.95) return '#BF360C'
  if (t >= 0.8) return '#2f5d4a'
  if (t >= 0.55) return '#12232e'
  return start % 2 === 0 ? '#607D8B' : '#4F868E'
}

function barStyle(start: number, end: number): Record<string, string> {
  const max = props.cronograma.semanas || 8
  const s = Math.min(Math.max(1, start), max)
  const e = Math.min(Math.max(s, end), max)
  return {
    gridColumn: `${s} / ${e + 1}`,
    background: barColor(s),
  }
}

function marcoLeft(semana: number): string {
  const n = props.cronograma.semanas || 8
  const w = Math.min(Math.max(1, semana), n)
  return `calc((${w} - 0.5) / ${n} * 100%)`
}

function onKey(e: KeyboardEvent) {
  if (e.key === 'Escape') emit('close')
}

watch(
  () => props.open,
  (open) => {
    if (open) {
      document.addEventListener('keydown', onKey)
      window.addEventListener('beforeprint', onBeforePrint)
      window.addEventListener('afterprint', onAfterPrint)
      document.body.style.overflow = 'hidden'
    } else {
      cleanupPrint()
      document.removeEventListener('keydown', onKey)
      window.removeEventListener('beforeprint', onBeforePrint)
      window.removeEventListener('afterprint', onAfterPrint)
      document.body.style.overflow = ''
    }
  }
)

onUnmounted(() => {
  cleanupPrint()
  document.removeEventListener('keydown', onKey)
  window.removeEventListener('beforeprint', onBeforePrint)
  window.removeEventListener('afterprint', onAfterPrint)
  document.body.style.overflow = ''
})

let prevTitle = ''

function cleanupPrint() {
  document.documentElement.classList.remove('printing-canvas')
  if (prevTitle) {
    document.title = prevTitle
    prevTitle = ''
  }
}

function onBeforePrint() {
  if (!prevTitle) prevTitle = document.title
  const slug = (props.title || 'canvas').replace(/\s+/g, ' ').trim() || 'canvas'
  document.title = `Canvas IA — ${slug}`
  document.documentElement.classList.add('printing-canvas')
}

function onAfterPrint() {
  cleanupPrint()
}

async function savePdf() {
  onBeforePrint()
  await nextTick()
  window.print()
}
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="pdf-root" role="dialog" aria-modal="true" aria-labelledby="canvas-pdf-title">
      <div class="pdf-chrome">
        <p class="pdf-chrome-hint">
          Uma página A3 paisagem. No diálogo, escolha <b>Salvar como PDF</b>,
          papel A3 e orientação paisagem; desmarque cabeçalhos/rodapés do navegador.
        </p>
        <div class="pdf-chrome-actions">
          <AppButton variant="ghost" size="sm" @click="emit('close')">Fechar</AppButton>
          <AppButton variant="primary" size="sm" @click="savePdf">Salvar PDF</AppButton>
        </div>
      </div>

      <div class="pdf-stage">
        <article class="sheet canvas-pdf-sheet" :style="{ '--weeks': String(cronograma.semanas || 8) }">
          <header class="head">
            <div class="head-brand">
              <div class="brand">Valorian · Instrumento estratégico</div>
              <h1 id="canvas-pdf-title">
                {{ dash(title) }}
              </h1>
              <p class="sub">Canvas de Oportunidades de IA por área de negócio</p>
            </div>
            <dl class="meta">
              <div>
                <dt>Área</dt>
                <dd>{{ dash(areaNegocio) }}</dd>
              </div>
              <div>
                <dt>Responsável</dt>
                <dd>{{ dash(responsavel) }}</dd>
              </div>
              <div>
                <dt>Data</dt>
                <dd>{{ dash(data) }}</dd>
              </div>
              <div>
                <dt>Prioridade</dt>
                <dd>{{ prioridadeLabel }}</dd>
              </div>
              <div>
                <dt>Início</dt>
                <dd>{{ mesLabel }}</dd>
              </div>
              <div class="meta-wide">
                <dt>Objetivo da área</dt>
                <dd>{{ dash(objetivoEstrategico) }}</dd>
              </div>
            </dl>
          </header>

          <div class="grid diag">
            <section class="cell band-diag">
              <span class="num">01</span>
              <h2>Contexto da área</h2>
              <ul v-if="items(contexto).length">
                <li v-for="(t, i) in items(contexto)" :key="'c' + i">{{ t }}</li>
              </ul>
              <p v-else class="empty">—</p>
            </section>
            <section class="cell band-diag">
              <span class="num">02</span>
              <h2>Dores &amp; gargalos</h2>
              <ul v-if="items(dores).length">
                <li v-for="(t, i) in items(dores)" :key="'d' + i">{{ t }}</li>
              </ul>
              <p v-else class="empty">—</p>
            </section>
            <section class="cell band-diag last">
              <span class="num">03</span>
              <h2>Oportunidade de IA</h2>
              <ul v-if="items(oportunidade).length">
                <li v-for="(t, i) in items(oportunidade)" :key="'o' + i">{{ t }}</li>
              </ul>
              <p v-else class="empty">—</p>
              <div v-if="oportunidadeTipos.length" class="chips">
                <span v-for="t in oportunidadeTipos" :key="t" class="chip">{{ t }}</span>
              </div>
            </section>
          </div>

          <div class="grid eval">
            <section class="cell band-eval">
              <span class="num">04</span>
              <h2>Valor esperado</h2>
              <ul v-if="items(valor).length">
                <li v-for="(t, i) in items(valor)" :key="'v' + i">{{ t }}</li>
              </ul>
              <p v-else class="empty">—</p>
            </section>
            <section class="cell band-eval">
              <span class="num">05</span>
              <h2>Dados &amp; insumos</h2>
              <ul v-if="items(dados).length">
                <li v-for="(t, i) in items(dados)" :key="'da' + i">{{ t }}</li>
              </ul>
              <p v-else class="empty">—</p>
            </section>
            <section class="cell band-eval">
              <span class="num">06</span>
              <h2>Custo &amp; complexidade</h2>
              <ul v-if="items(custo).length">
                <li v-for="(t, i) in items(custo)" :key="'cu' + i">{{ t }}</li>
              </ul>
              <p v-else class="empty">—</p>
            </section>
            <section class="cell band-eval last">
              <span class="num">07</span>
              <h2>Riscos &amp; governança</h2>
              <ul v-if="items(riscos).length">
                <li v-for="(t, i) in items(riscos)" :key="'r' + i">{{ t }}</li>
              </ul>
              <p v-else class="empty">—</p>
            </section>
          </div>

          <section class="exec">
            <div class="exec-kicker">
              <span class="num">08</span>
              <h2>Análise executiva</h2>
              <span v-if="analiseNota.value != null" class="exec-score">
                {{ formatNota(analiseNota.value) }}/5 · {{ Math.round(analiseNota.pct || 0) }}%
              </span>
            </div>
            <div class="exec-row">
              <div v-for="c in analiseScores" :key="c.id" class="exec-cell">
                <b>{{ c.label }}</b>
                <span>{{ c.peso }}%</span>
                <em>{{ c.score ?? '—' }}</em>
              </div>
            </div>
          </section>

          <div class="decision">
            <section class="dec-left">
              <span class="num num-amber">09</span>
              <h2>Decisão</h2>
              <div class="scores">
                <div>
                  <b>Valor</b>
                  <div class="dots">
                    <span v-for="n in 5" :key="'sv' + n" class="dot" :class="{ on: scoreValor === n }">{{ n }}</span>
                  </div>
                </div>
                <div>
                  <b>Viabilidade</b>
                  <div class="dots">
                    <span v-for="n in 5" :key="'sf' + n" class="dot" :class="{ on: scoreViabilidade === n }">{{ n }}</span>
                  </div>
                </div>
              </div>
              <p class="next"><b>Próximo passo.</b> {{ dash(proximoPasso) }}</p>
              <p v-if="justificativaTows.trim()" class="tows">
                <b>TOWS.</b> {{ justificativaTows.trim() }}
              </p>
            </section>
            <div class="matrix-wrap">
              <div class="matrix-cap">Onde essa oportunidade cai</div>
              <div class="matrix">
                <div class="qy">Valor →</div>
                <div class="q q-bet" :class="{ on: quadrant === 'aposta_estrategica' }">
                  <b>Aposta estratégica</b>Alto valor, baixa viab.
                </div>
                <div class="q q-go" :class="{ on: quadrant === 'ganho_rapido' }">
                  <b>Ganho rápido</b>Alto valor, alta viab.
                </div>
                <div class="q q-avoid" :class="{ on: quadrant === 'evitar' }">
                  <b>Evitar</b>Baixo valor, baixa viab.
                </div>
                <div class="q q-inc" :class="{ on: quadrant === 'incremental' }">
                  <b>Incremental</b>Baixo valor, alta viab.
                </div>
                <div /><div class="qx">Viabilidade →</div>
              </div>
            </div>
          </div>

          <section class="crono">
            <div class="crono-kicker">
              <span class="num num-amber">10</span>
              <h2>Cronograma</h2>
              <span class="horizonte">{{ horizonteLabel }}</span>
              <span v-if="cronograma.subtitulo" class="crono-sub">{{ cronograma.subtitulo }}</span>
            </div>
            <div v-if="cronograma.pre_requisito" class="crono-note">
              <b>Pré-requisito.</b> {{ cronograma.pre_requisito }}
            </div>

            <div v-if="cronograma.atividades.length" class="gantt">
              <div class="gantt-head">
                <div class="c-id">ID</div>
                <div class="c-act">Atividade / entrega</div>
                <div class="c-lead">Liderança</div>
                <div class="c-weeks">
                  <template v-if="useMonths">
                    <span
                      v-for="m in months"
                      :key="'h' + m.index"
                      class="month-h"
                      :style="{ gridColumn: m.start + ' / ' + (m.end + 1) }"
                    >{{ m.label }}</span>
                  </template>
                  <template v-else>
                    <span v-for="w in weeks" :key="'h' + w">S{{ w }}</span>
                  </template>
                </div>
              </div>
              <div
                v-for="(act, idx) in cronograma.atividades"
                :key="act.id"
                class="gantt-row"
                :class="{ zebra: idx % 2 === 1 }"
              >
                <div class="c-id">{{ padId(idx) }}</div>
                <div class="c-act">{{ act.titulo || '—' }}</div>
                <div class="c-lead">{{ act.lideranca || '—' }}</div>
                <div class="c-weeks">
                  <span
                    v-for="w in weeks"
                    :key="act.id + 'w' + w"
                    class="week-cell"
                  />
                  <div class="bar" :style="barStyle(act.semana_inicio, act.semana_fim)">
                    {{ barLabel(act.semana_inicio, act.semana_fim) }}
                  </div>
                </div>
              </div>
              <div v-if="cronograma.marcos.length" class="marco-row">
                <div class="marco-label">Marcos</div>
                <div class="c-weeks marco-track">
                  <span
                    v-for="(marco, mi) in cronograma.marcos"
                    :key="marco.id"
                    class="diamond"
                    :style="{ left: marcoLeft(marco.semana) }"
                    :title="`M${mi + 1} · S${marco.semana} · ${marco.titulo}`"
                  >
                    <i />
                    <em>M{{ mi + 1 }}</em>
                  </span>
                </div>
              </div>
            </div>
            <p v-else class="crono-empty">Nenhuma atividade no cronograma.</p>

            <ul v-if="cronograma.marcos.length" class="marco-legend">
              <li v-for="(marco, mi) in cronograma.marcos" :key="'ml' + marco.id">
                <b>M{{ mi + 1 }}</b>
                S{{ marco.semana }} · {{ marco.titulo || '—' }}
              </li>
            </ul>
            <p v-if="cronograma.criterio_aceite" class="crono-note aceite">
              <b>Critério de aceite.</b> {{ cronograma.criterio_aceite }}
            </p>
          </section>
        </article>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.pdf-root {
  --ink: #12232e;
  --ink-soft: #3c525f;
  --paper: #f7f5ef;
  --line: #d8d2c6;
  --amber: #c17a2c;
  --amber-tint: #f3e7cc;
  --slate: #5b7a86;
  --slate-tint: #e4ecee;
  --teal: #2f6e6a;
  --ok: #2f6e4a;
  --danger: #9c3b2e;
  position: fixed;
  inset: 0;
  z-index: 80;
  background: rgba(18, 35, 46, 0.55);
  display: flex;
  flex-direction: column;
  color: var(--ink);
}
.pdf-chrome {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 10px 18px;
  background: #fff;
  border-bottom: 1px solid var(--line);
}
.pdf-chrome-hint {
  margin: 0;
  font-size: 12px;
  color: var(--ink-soft);
  line-height: 1.35;
}
.pdf-chrome-hint b {
  color: var(--ink);
}
.pdf-chrome-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}
.pdf-stage {
  flex: 1;
  overflow: auto;
  padding: 20px 16px 32px;
  display: flex;
  justify-content: center;
  align-items: flex-start;
}

.sheet {
  width: 420mm;
  height: 297mm;
  background: var(--paper);
  border: 1px solid var(--line);
  box-shadow: var(--shadow-3);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  print-color-adjust: exact;
  -webkit-print-color-adjust: exact;
}
@media screen {
  .sheet {
    transform: scale(0.7);
    transform-origin: top center;
    margin-bottom: calc(297mm * -0.3);
  }
}

.head {
  display: flex;
  gap: 20px;
  justify-content: space-between;
  padding: 10px 14px 8px;
  border-bottom: 2.5px solid var(--ink);
  flex-shrink: 0;
}
.brand {
  font-size: 8px;
  font-weight: 700;
  letter-spacing: 0.28em;
  text-transform: uppercase;
  color: var(--amber);
  margin-bottom: 3px;
}
h1 {
  font-family: var(--serif);
  font-size: 18px;
  line-height: 1.1;
  margin: 0;
  max-width: 42ch;
}
.sub {
  margin: 3px 0 0;
  font-size: 9px;
  color: var(--ink-soft);
}
.meta {
  display: grid;
  grid-template-columns: repeat(3, minmax(90px, 1fr));
  gap: 4px 14px;
  min-width: 340px;
  margin: 0;
}
.meta div {
  min-width: 0;
}
.meta-wide {
  grid-column: 1 / -1;
}
.meta dt {
  font-size: 8px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--ink-soft);
  font-weight: 600;
}
.meta dd {
  margin: 0;
  font-size: 11px;
  border-bottom: 1px dotted var(--slate);
  min-height: 16px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.meta-wide dd {
  white-space: normal;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.grid {
  display: grid;
  flex: 0 1 auto;
}
.diag {
  grid-template-columns: 1fr 1fr 1fr;
}
.eval {
  grid-template-columns: 1fr 1fr 1fr 1fr;
}
.cell {
  border-right: 1px solid var(--line);
  border-bottom: 1px solid var(--line);
  padding: 7px 10px 8px;
  position: relative;
  min-height: 0;
  overflow: hidden;
}
.cell.last {
  border-right: none;
}
.cell::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  background: var(--stage, var(--slate));
}
.band-diag {
  --stage: var(--slate);
}
.band-eval {
  --stage: var(--teal);
}
.num {
  font-size: 9px;
  font-weight: 700;
  color: var(--stage, var(--slate));
}
.num-amber {
  color: var(--amber);
}
h2 {
  font-family: var(--sans);
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin: 1px 0 4px;
}
.cell ul {
  margin: 0;
  padding-left: 14px;
  font-size: 10px;
  line-height: 1.3;
}
.cell li + li {
  margin-top: 2px;
}
.empty {
  margin: 0;
  font-size: 10px;
  color: #a9a296;
}
.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 3px;
  margin-top: 5px;
}
.chip {
  font-size: 8px;
  border: 1px solid var(--line);
  border-radius: 20px;
  padding: 1px 7px;
  background: #fff;
  color: var(--ink-soft);
}

.exec {
  flex-shrink: 0;
  padding: 6px 12px 7px 14px;
  border-bottom: 1px solid var(--line);
  position: relative;
}
.exec::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  background: var(--teal);
}
.exec-kicker {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-bottom: 5px;
}
.exec-kicker h2 {
  margin: 0;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}
.exec-score {
  margin-left: auto;
  font-size: 10px;
  font-weight: 700;
  color: var(--teal);
}
.exec-row {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 6px;
}
.exec-cell {
  min-width: 0;
  font-size: 7.5px;
  line-height: 1.25;
  color: var(--ink-soft);
}
.exec-cell b {
  display: block;
  font-size: 8px;
  color: var(--ink);
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.exec-cell span {
  display: block;
}
.exec-cell em {
  font-style: normal;
  font-weight: 700;
  font-size: 11px;
  color: var(--ink);
}

.decision {
  display: grid;
  grid-template-columns: 1.2fr 1fr;
  flex-shrink: 0;
}
.dec-left {
  padding: 8px 12px 8px 14px;
  border-right: 1px solid var(--line);
  border-bottom: 1px solid var(--line);
  position: relative;
  overflow: hidden;
}
.dec-left::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  background: var(--amber);
}
.scores {
  display: flex;
  gap: 22px;
  margin: 6px 0;
}
.scores b {
  display: block;
  font-size: 8px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--ink-soft);
  margin-bottom: 4px;
}
.dots {
  display: flex;
  gap: 4px;
}
.dot {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  border: 1.5px solid var(--slate);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 9px;
  font-weight: 600;
  color: var(--ink-soft);
  background: #fff;
}
.dot.on {
  background: var(--amber);
  border-color: var(--amber);
  color: #fff;
}
.next,
.tows {
  margin: 4px 0 0;
  font-size: 10px;
  line-height: 1.3;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.matrix-wrap {
  padding: 8px 10px;
  border-bottom: 1px solid var(--line);
}
.matrix-cap {
  font-size: 8px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--ink-soft);
  margin-bottom: 5px;
}
.matrix {
  display: grid;
  grid-template-columns: 12px 1fr 1fr;
  grid-template-rows: 1fr 1fr 12px;
  gap: 4px;
  min-height: 92px;
}
.qy,
.qx {
  font-size: 7px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--ink-soft);
  text-align: center;
}
.qy {
  writing-mode: vertical-rl;
  transform: rotate(180deg);
  grid-row: span 2;
  align-self: center;
}
.qx {
  grid-column: 2 / 4;
}
.q {
  border-radius: 5px;
  padding: 5px 7px;
  font-size: 8px;
  line-height: 1.2;
  border: 1px solid var(--line);
}
.q b {
  display: block;
  font-size: 9px;
  margin-bottom: 1px;
}
.q-go {
  background: #e8f0e7;
  border-color: #bbd3b7;
}
.q-go b {
  color: var(--ok);
}
.q-bet {
  background: var(--amber-tint);
  border-color: #e3ce9c;
}
.q-bet b {
  color: var(--amber);
}
.q-inc {
  background: var(--slate-tint);
  border-color: #cbd8db;
}
.q-inc b {
  color: var(--slate);
}
.q-avoid {
  background: #f1e1dd;
  border-color: #ddbcb4;
}
.q-avoid b {
  color: var(--danger);
}
.q.on {
  outline: 2px solid var(--ink);
  outline-offset: -1px;
}

.crono {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  padding: 6px 12px 8px;
  overflow: hidden;
}
.crono-kicker {
  display: flex;
  align-items: baseline;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 4px;
}
.crono-kicker h2 {
  margin: 0;
}
.horizonte {
  font-size: 9px;
  color: var(--ink-soft);
}
.crono-sub {
  font-size: 10px;
  color: var(--ink);
}
.crono-note {
  font-size: 9px;
  line-height: 1.3;
  margin: 0 0 4px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.crono-empty {
  font-size: 11px;
  color: var(--ink-soft);
  margin: 8px 0;
}
.gantt {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  font-size: 9px;
  overflow: hidden;
}
.gantt-head,
.gantt-row,
.marco-row {
  display: grid;
  grid-template-columns: 22px minmax(90px, 1.4fr) minmax(70px, 0.8fr) minmax(160px, 2.2fr);
  gap: 4px;
  align-items: center;
}
.gantt-head {
  font-size: 8px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--ink-soft);
  font-weight: 600;
  padding-bottom: 3px;
  border-bottom: 1px solid var(--line);
}
.gantt-row {
  padding: 1px 0;
  min-height: 16px;
}
.gantt-row.zebra {
  background: rgba(91, 122, 134, 0.06);
}
.c-id {
  font-variant-numeric: tabular-nums;
  color: var(--ink-soft);
  text-align: center;
}
.c-act,
.c-lead {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.c-weeks {
  display: grid;
  grid-template-columns: repeat(var(--weeks), minmax(0, 1fr));
  position: relative;
  height: 14px;
  align-items: center;
}
.gantt-head .c-weeks {
  height: auto;
}
.month-h,
.gantt-head .c-weeks span {
  text-align: center;
  font-size: 7px;
}
.week-cell {
  border-left: 1px solid #eee8dc;
  height: 14px;
}
.bar {
  position: absolute;
  top: 2px;
  height: 10px;
  border-radius: 2px;
  color: #fff;
  font-size: 7px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 3px;
  overflow: hidden;
  white-space: nowrap;
}
.marco-row {
  margin-top: 4px;
}
.marco-label {
  grid-column: 1 / 4;
  font-size: 8px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--ink-soft);
  font-weight: 600;
}
.marco-track {
  height: 18px;
}
.diamond {
  position: absolute;
  top: 0;
  transform: translateX(-50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 16px;
}
.diamond i {
  width: 8px;
  height: 8px;
  background: var(--amber);
  transform: rotate(45deg);
  display: block;
}
.diamond em {
  font-style: normal;
  font-size: 7px;
  font-weight: 700;
  color: var(--amber);
  line-height: 1;
  margin-top: 1px;
}
.marco-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 2px 12px;
  list-style: none;
  margin: 4px 0 0;
  padding: 0;
  font-size: 8px;
  color: var(--ink-soft);
}
.marco-legend b {
  color: var(--amber);
  margin-right: 4px;
}

@media print {
  .pdf-chrome {
    display: none !important;
  }
  .pdf-stage {
    padding: 0 !important;
    overflow: visible !important;
  }
  .sheet {
    transform: none;
    margin-bottom: 0;
    box-shadow: none;
    border: none;
  }
}
</style>
