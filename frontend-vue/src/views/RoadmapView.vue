<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import PageHeader from '@/components/ui/PageHeader.vue'
import StateBlock from '@/components/ui/StateBlock.vue'
import {
  listRoadmapProjects,
  moveRoadmapProject,
  type CanvasPrioridade,
  type CanvasRoadmapItem,
} from '@/api/canvasProjects'

const MONTHS = 18
const WEEKS_PER_MONTH = 4
const MONTH_LABELS = [
  'Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
  'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez',
] as const

const loading = ref(true)
const error = ref<string | null>(null)
const items = ref<CanvasRoadmapItem[]>([])
const windowStart = ref(startOfMonth(new Date()))
const draggingId = ref<string | null>(null)
const dragPreview = ref<string | null>(null)
const saveError = ref<string | null>(null)
let drag: {
  id: string
  originIso: string
  startX: number
  colWidth: number
  pointerId: number
} | null = null

function startOfMonth(d: Date): Date {
  return new Date(d.getFullYear(), d.getMonth(), 1)
}

function addMonths(d: Date, n: number): Date {
  return new Date(d.getFullYear(), d.getMonth() + n, 1)
}

function monthsBetween(from: Date, to: Date): number {
  return (to.getFullYear() - from.getFullYear()) * 12 + (to.getMonth() - from.getMonth())
}

function parseIso(iso: string): Date {
  const [y, m, day] = iso.split('-').map(Number)
  return new Date(y || 0, (m || 1) - 1, day || 1)
}

function toIsoDate(d: Date): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function shiftIsoMonths(iso: string, delta: number): string {
  const [y, m, day] = iso.split('-').map(Number)
  const target = new Date(y || 0, (m || 1) - 1 + delta, 1)
  const last = new Date(target.getFullYear(), target.getMonth() + 1, 0).getDate()
  const clamped = Math.min(day || 1, last)
  return toIsoDate(new Date(target.getFullYear(), target.getMonth(), clamped))
}

function durationMonths(semanas: number): number {
  return Math.max(1, Math.round((semanas || 8) / WEEKS_PER_MONTH))
}

function formatIso(iso: string): string {
  const d = parseIso(iso)
  return `${String(d.getDate()).padStart(2, '0')}/${String(d.getMonth() + 1).padStart(2, '0')}/${d.getFullYear()}`
}

const monthCols = computed(() =>
  Array.from({ length: MONTHS }, (_, i) => {
    const d = addMonths(windowStart.value, i)
    return {
      index: i,
      date: d,
      label: MONTH_LABELS[d.getMonth()],
      year: d.getFullYear(),
      isCurrent:
        d.getFullYear() === new Date().getFullYear() && d.getMonth() === new Date().getMonth(),
    }
  })
)

const windowLabel = computed(() => {
  const a = monthCols.value[0]
  const b = monthCols.value[MONTHS - 1]
  if (!a || !b) return ''
  return `${a.label} ${a.year} — ${b.label} ${b.year}`
})

function liveStart(item: CanvasRoadmapItem): string {
  if (draggingId.value === item.id && dragPreview.value) return dragPreview.value
  return item.data_inicio_real
}

function barLayout(item: CanvasRoadmapItem): {
  from: number
  to: number
  clippedStart: boolean
  clippedEnd: boolean
  hidden: boolean
} {
  const start = startOfMonth(parseIso(liveStart(item)))
  const offset = monthsBetween(windowStart.value, start)
  const dur = durationMonths(item.semanas)
  const from = Math.max(0, offset)
  const to = Math.min(MONTHS, offset + dur)
  return {
    from,
    to,
    clippedStart: offset < 0,
    clippedEnd: offset + dur > MONTHS,
    hidden: to <= 0 || from >= MONTHS,
  }
}

function barStyle(item: CanvasRoadmapItem): Record<string, string> {
  const { from, to, hidden } = barLayout(item)
  if (hidden) return { display: 'none' }
  return { gridColumn: `${from + 1} / ${to + 1}` }
}

function barTitle(item: CanvasRoadmapItem): string {
  const start = parseIso(liveStart(item))
  const end = addMonths(startOfMonth(start), durationMonths(item.semanas))
  end.setDate(0)
  return `${item.title}: ${formatIso(liveStart(item))} → ${formatIso(toIsoDate(end))}`
}

function prioTone(p: CanvasPrioridade | string): string {
  const id = (p || 'P4') as CanvasPrioridade
  return ['P0', 'P1', 'P2', 'P3', 'P4'].includes(id) ? id : 'P4'
}

function shiftWindow(delta: number) {
  windowStart.value = addMonths(windowStart.value, delta)
}

function resetWindow() {
  windowStart.value = startOfMonth(new Date())
}

async function load() {
  loading.value = true
  error.value = null
  try {
    const res = await listRoadmapProjects()
    items.value = res.items || []
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Erro ao carregar o roadmap.'
  } finally {
    loading.value = false
  }
}

function onBarPointerDown(item: CanvasRoadmapItem, ev: PointerEvent) {
  if (ev.button !== 0) return
  const track = (ev.currentTarget as HTMLElement).closest('.track') as HTMLElement | null
  if (!track) return
  ev.preventDefault()
  const colWidth = track.clientWidth / MONTHS
  drag = {
    id: item.id,
    originIso: item.data_inicio_real,
    startX: ev.clientX,
    colWidth,
    pointerId: ev.pointerId,
  }
  draggingId.value = item.id
  dragPreview.value = item.data_inicio_real
  saveError.value = null
  ;(ev.currentTarget as HTMLElement).setPointerCapture(ev.pointerId)
}

function onBarPointerMove(ev: PointerEvent) {
  if (!drag || ev.pointerId !== drag.pointerId) return
  const delta = Math.round((ev.clientX - drag.startX) / drag.colWidth)
  dragPreview.value = shiftIsoMonths(drag.originIso, delta)
}

async function onBarPointerUp(ev: PointerEvent) {
  if (!drag || ev.pointerId !== drag.pointerId) return
  const { id, originIso } = drag
  const next = dragPreview.value || originIso
  drag = null
  draggingId.value = null
  dragPreview.value = null
  if (next === originIso) return
  const item = items.value.find((p) => p.id === id)
  if (!item) return
  const previous = item.data_inicio_real
  item.data_inicio_real = next
  try {
    const updated = await moveRoadmapProject(id, next)
    Object.assign(item, updated)
  } catch (e) {
    item.data_inicio_real = previous
    saveError.value = e instanceof Error ? e.message : 'Não foi possível mover o projeto.'
  }
}

function onBarLostCapture() {
  if (!drag) return
  drag = null
  draggingId.value = null
  dragPreview.value = null
}

onMounted(() => {
  void load()
})

onUnmounted(() => {
  drag = null
})
</script>

<template>
  <div class="wrap">
    <PageHeader
      title="Roadmap"
      subtitle="Projetos aprovados com data de início, em um Gantt de 18 meses. Arraste a barra para adiantar ou adiar."
    >
      <template #actions>
        <RouterLink to="/projetos" class="link-back">← Projetos</RouterLink>
      </template>
    </PageHeader>

    <StateBlock v-if="loading" state="loading" />
    <StateBlock v-else-if="error" state="error" :message="error" :retry="load" />
    <StateBlock
      v-else-if="!items.length"
      state="empty"
      message="Nenhum projeto aprovado com data de início. Aprove um canvas e informe a data real de início."
    />

    <template v-else>
      <div class="toolbar">
        <div class="window-nav">
          <button type="button" class="nav-btn" aria-label="Recuar 1 mês" @click="shiftWindow(-1)">‹</button>
          <span class="window-label">{{ windowLabel }}</span>
          <button type="button" class="nav-btn" aria-label="Avançar 1 mês" @click="shiftWindow(1)">›</button>
        </div>
        <button type="button" class="today-btn" @click="resetWindow">Este mês</button>
        <p v-if="saveError" class="save-err">{{ saveError }}</p>
      </div>

      <div class="gantt-card">
        <div class="gantt" :style="{ '--months': String(MONTHS) }">
          <div class="gantt-head">
            <div class="label-col">Projeto</div>
            <div class="months">
              <span
                v-for="col in monthCols"
                :key="col.index"
                class="month"
                :class="{ current: col.isCurrent, 'year-start': col.date.getMonth() === 0 || col.index === 0 }"
              >
                <em v-if="col.date.getMonth() === 0 || col.index === 0">{{ col.year }}</em>
                {{ col.label }}
              </span>
            </div>
          </div>

          <div
            v-for="item in items"
            :key="item.id"
            class="gantt-row"
            :class="{ dragging: draggingId === item.id }"
          >
            <div class="label-col">
              <RouterLink :to="`/projetos/${item.id}`" class="proj-title">
                {{ item.title || 'Projeto' }}
              </RouterLink>
              <span class="proj-meta">
                <b :data-p="prioTone(item.prioridade)">{{ item.prioridade || 'P4' }}</b>
                {{ item.area_negocio || '—' }}
                · {{ durationMonths(item.semanas) }}
                {{ durationMonths(item.semanas) === 1 ? 'mês' : 'meses' }}
              </span>
            </div>
            <div class="track">
              <span
                v-for="col in monthCols"
                :key="'g' + item.id + col.index"
                class="cell"
                :class="{ current: col.isCurrent }"
              />
              <button
                v-if="!barLayout(item).hidden"
                type="button"
                class="bar"
                :data-p="prioTone(item.prioridade)"
                :class="{
                  clipped: barLayout(item).clippedStart || barLayout(item).clippedEnd,
                  'clip-start': barLayout(item).clippedStart,
                  'clip-end': barLayout(item).clippedEnd,
                }"
                :style="barStyle(item)"
                :title="barTitle(item)"
                :aria-label="barTitle(item) + '. Arraste para reagendar.'"
                @pointerdown="onBarPointerDown(item, $event)"
                @pointermove="onBarPointerMove"
                @pointerup="onBarPointerUp"
                @pointercancel="onBarLostCapture"
                @lostpointercapture="onBarLostCapture"
              >
                <span class="bar-text">{{ formatIso(liveStart(item)) }}</span>
              </button>
              <span v-else class="off-window">fora da janela · {{ formatIso(liveStart(item)) }}</span>
            </div>
          </div>
        </div>
      </div>
      <p class="hint">
        A largura da barra segue o horizonte do cronograma do canvas ({{ WEEKS_PER_MONTH }} semanas ≈ 1 mês).
        Arrastar move a data de início real; a duração não muda.
      </p>
    </template>
  </div>
</template>

<style scoped>
.wrap {
  max-width: 1180px;
  margin: 0 auto;
  padding: 28px 20px 60px;
}
.link-back {
  font-size: 14px;
  color: var(--k0);
  text-decoration: none;
}
.link-back:hover {
  text-decoration: underline;
}
.toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px 16px;
  margin-bottom: 14px;
}
.window-nav {
  display: flex;
  align-items: center;
  gap: 8px;
}
.nav-btn {
  width: 32px;
  height: 32px;
  border: 1px solid var(--bd);
  background: var(--wh);
  border-radius: var(--r-sm);
  font-size: 18px;
  line-height: 1;
  color: var(--k0);
}
.nav-btn:hover {
  border-color: var(--k0);
}
.window-label {
  font-family: var(--serif);
  font-size: 16px;
  min-width: 22ch;
  text-align: center;
}
.today-btn {
  border: 1px solid var(--bd);
  background: var(--wh);
  border-radius: var(--r-sm);
  padding: 6px 12px;
  font: inherit;
  font-size: 13px;
  font-weight: 600;
}
.today-btn:hover {
  border-color: var(--k0);
}
.save-err {
  margin: 0;
  color: #8f2b2b;
  font-size: 13px;
}
.gantt-card {
  background: var(--wh);
  border: 1px solid var(--bd);
  border-radius: var(--r-lg);
  overflow-x: auto;
}
.gantt {
  min-width: 860px;
}
.gantt-head,
.gantt-row {
  display: grid;
  grid-template-columns: minmax(180px, 220px) minmax(640px, 1fr);
  align-items: stretch;
}
.gantt-head {
  border-bottom: 1px solid var(--bd);
  background: var(--k9);
  position: sticky;
  top: 0;
  z-index: 1;
}
.label-col {
  padding: 8px 12px;
  border-right: 1px solid var(--bd);
  min-width: 0;
}
.gantt-head .label-col {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--k5);
  display: flex;
  align-items: flex-end;
}
.months,
.track {
  display: grid;
  grid-template-columns: repeat(var(--months), minmax(0, 1fr));
  position: relative;
}
.track {
  grid-template-rows: minmax(52px, auto);
}
.month {
  padding: 8px 2px 10px;
  text-align: center;
  font-size: 11px;
  font-weight: 600;
  color: var(--k3);
  border-left: 1px solid var(--bd2);
}
.month.current {
  background: var(--golddim);
  color: var(--k0);
}
.month.year-start {
  border-left: 1px solid var(--bd);
}
.month em {
  display: block;
  font-style: normal;
  font-size: 9px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--k5);
  font-weight: 700;
}
.gantt-row {
  border-bottom: 1px solid var(--bd2);
  min-height: 52px;
}
.gantt-row:last-child {
  border-bottom: none;
}
.gantt-row.dragging {
  background: var(--k9);
}
.proj-title {
  display: block;
  font-weight: 600;
  font-size: 13px;
  color: var(--k0);
  text-decoration: none;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.proj-title:hover {
  text-decoration: underline;
}
.proj-meta {
  display: block;
  margin-top: 2px;
  font-size: 11px;
  color: var(--k5);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.proj-meta b {
  font-size: 10px;
  letter-spacing: 0.04em;
  margin-right: 4px;
}
.proj-meta b[data-p='P0'] { color: #12232e; }
.proj-meta b[data-p='P1'] { color: #2f6e6a; }
.proj-meta b[data-p='P2'] { color: #c17a2c; }
.proj-meta b[data-p='P3'] { color: #5b7a86; }
.proj-meta b[data-p='P4'] { color: #8a8a8a; }
.cell {
  grid-row: 1;
  border-left: 1px solid var(--bd2);
  min-height: 52px;
}
.cell.current {
  background: var(--golddim);
}
.bar {
  grid-row: 1;
  align-self: center;
  z-index: 1;
  height: 24px;
  margin: 0 3px;
  min-width: 0;
  border: none;
  border-radius: 5px;
  color: #fff;
  font: inherit;
  font-size: 11px;
  font-weight: 700;
  cursor: grab;
  display: flex;
  align-items: center;
  padding: 0 8px;
  overflow: hidden;
  white-space: nowrap;
  touch-action: none;
  user-select: none;
  print-color-adjust: exact;
  -webkit-print-color-adjust: exact;
}
.bar:active,
.dragging .bar {
  cursor: grabbing;
}
.bar[data-p='P0'] { background: #12232e; }
.bar[data-p='P1'] { background: #2f6e6a; }
.bar[data-p='P2'] { background: #c17a2c; }
.bar[data-p='P3'] { background: #5b7a86; }
.bar[data-p='P4'] { background: #8a8a8a; }
.bar.clip-start {
  border-top-left-radius: 0;
  border-bottom-left-radius: 0;
}
.bar.clip-end {
  border-top-right-radius: 0;
  border-bottom-right-radius: 0;
}
.bar-text {
  pointer-events: none;
}
.off-window {
  grid-row: 1;
  grid-column: 1 / -1;
  align-self: center;
  padding-left: 8px;
  font-size: 11px;
  color: var(--k5);
}
.hint {
  margin: 12px 0 0;
  font-size: 12px;
  color: var(--k5);
  line-height: 1.45;
}
@media (max-width: 720px) {
  .gantt-head,
  .gantt-row {
    grid-template-columns: 140px minmax(560px, 1fr);
  }
}
</style>
