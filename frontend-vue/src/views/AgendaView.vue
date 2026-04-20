<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { fetchCurrentCourse } from '@/api/course'
import type { JornadaSemana, Encontro } from '@/types'

interface AgendaItem {
  semana: number
  encontro: Encontro
  dateStr: string | null
  dateLabel: string | null
  timeLabel: string | null
}

const loading = ref(true)
const error = ref<string | null>(null)
const courseTitle = ref('')
const numSemanas = ref(0)
const numEncontros = ref(0)
const itemsByWeek = ref<Record<number, AgendaItem[]>>({})
const weekNums = computed(() => Object.keys(itemsByWeek.value).map(Number).sort((a, b) => a - b))

/** Todos os itens em uma única lista, para facilitar agrupamentos */
const allItems = computed<AgendaItem[]>(() => {
  const out: AgendaItem[] = []
  weekNums.value.forEach((w) => {
    ;(itemsByWeek.value[w] ?? []).forEach((it) => {
      out.push(it)
    })
  })
  return out
})

/** Itens com data definida, para exportação .ics e cálculo de próximo encontro */
const exportableItems = computed(() => {
  return allItems.value
    .filter((it) => !!it.dateStr)
    .slice()
    .sort((a, b) => (a.dateStr ?? '').localeCompare(b.dateStr ?? ''))
})

/** ID do próximo encontro (por data/hora) para destaque visual */
const nextEncontroId = computed<number | null>(() => {
  const arr = exportableItems.value
    .map((it) => {
      const ts = it.dateStr ? new Date(it.dateStr).getTime() : NaN
      return { it, ts }
    })
    .filter((x) => !isNaN(x.ts))
  if (!arr.length) return null
  const now = Date.now()
  const future = arr.filter((x) => x.ts >= now).sort((a, b) => a.ts - b.ts)
  if (future[0]) return future[0].it.encontro.id
  arr.sort((a, b) => a.ts - b.ts)
  return arr[0].it.encontro.id
})

function isNext(item: AgendaItem): boolean {
  return nextEncontroId.value != null && item.encontro.id === nextEncontroId.value
}

function isPast(item: AgendaItem): boolean {
  if (!item.dateStr) return false
  const d = new Date(item.dateStr)
  if (isNaN(d.getTime())) return false
  return d.getTime() < Date.now() && !isNext(item)
}

const tooltip = ref<{
  show: boolean
  x: number
  y: number
  title: string
  sub: string
  tema: string
  objetivos: string[]
}>({
  show: false,
  x: 0,
  y: 0,
  title: '',
  sub: '',
  tema: '',
  objetivos: [],
})

const GAP = 14

function formatDate(isoStr: string | null | undefined): string | null {
  if (!isoStr) return null
  try {
    const d = new Date(isoStr)
    if (isNaN(d.getTime())) return null
    return d.toLocaleDateString('pt-BR', { weekday: 'short', day: 'numeric', month: 'short' })
  } catch {
    return null
  }
}

function formatTime(isoStr: string | null | undefined): string | null {
  if (!isoStr) return null
  try {
    const d = new Date(isoStr)
    if (isNaN(d.getTime())) return null
    return d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
  } catch {
    return null
  }
}

function buildAgendaItems(
  jornada: JornadaSemana[],
  encontroAgendas: Record<string, string>
): AgendaItem[] {
  const items: AgendaItem[] = []
  ;(jornada || []).forEach((sem) => {
    ;(sem.encontros || []).forEach((enc) => {
      const dateStr = encontroAgendas[String(enc.id)] || null
      items.push({
        semana: sem.semana,
        encontro: enc,
        dateStr,
        dateLabel: formatDate(dateStr),
        timeLabel: formatTime(dateStr),
      })
    })
  })
  return items
}

function showTooltip(ev: MouseEvent, item: AgendaItem) {
  const enc = item.encontro
  tooltip.value = {
    show: true,
    x: ev.clientX + GAP,
    y: ev.clientY + GAP,
    title: enc.titulo ?? '',
    sub: enc.subtitulo ?? '',
    tema: enc.tema ?? '',
    objetivos: (enc.objetivos ?? []).slice(0, 3),
  }
}

function placeTooltip(ev: MouseEvent) {
  if (!tooltip.value.show) return
  const rect = tooltipRef.value?.getBoundingClientRect()
  if (!rect) return
  let left = ev.clientX + GAP
  let top = ev.clientY + GAP
  if (left + rect.width > window.innerWidth) left = ev.clientX - rect.width - GAP
  if (left < 0) left = 10
  if (top + rect.height > window.innerHeight) top = ev.clientY - rect.height - GAP
  if (top < 0) top = 10
  tooltip.value.x = left
  tooltip.value.y = top
}

function hideTooltip() {
  tooltip.value.show = false
}

const tooltipRef = ref<HTMLElement | null>(null)

/** Escapa texto para valor de propriedade ICS (RFC 5545) */
function icsEscape(s: string): string {
  return s.replace(/\\/g, '\\\\').replace(/;/g, '\\;').replace(/,/g, '\\,').replace(/\n/g, '\\n')
}

/** Formata ISO para DTSTART/DTEND no formato YYYYMMDDTHHMMSSZ */
function toIcsDatetime(isoStr: string): string {
  const d = new Date(isoStr)
  const y = d.getUTCFullYear()
  const m = String(d.getUTCMonth() + 1).padStart(2, '0')
  const day = String(d.getUTCDate()).padStart(2, '0')
  const h = String(d.getUTCHours()).padStart(2, '0')
  const min = String(d.getUTCMinutes()).padStart(2, '0')
  const sec = String(d.getUTCSeconds()).padStart(2, '0')
  return `${y}${m}${day}T${h}${min}${sec}Z`
}

/** Gera o conteúdo do arquivo .ics para importação no Google Calendar */
function buildIcsContent(): string {
  const lines: string[] = [
    'BEGIN:VCALENDAR',
    'VERSION:2.0',
    'PRODID:-//Aegis//Agenda//PT',
    'CALSCALE:GREGORIAN',
    'X-WR-CALNAME:' + icsEscape(courseTitle.value),
  ]
  const now = toIcsDatetime(new Date().toISOString())
  exportableItems.value.forEach((it) => {
    const enc = it.encontro
    const start = toIcsDatetime(it.dateStr!)
    const startDate = new Date(it.dateStr!)
    const endDate = new Date(startDate.getTime() + 60 * 60 * 1000)
    const end = toIcsDatetime(endDate.toISOString())
    const summary = `Encontro ${enc.id}${enc.titulo ? ' – ' + enc.titulo : ''}`
    const descParts = [enc.subtitulo, enc.tema, (enc.objetivos ?? []).join('\n')].filter(Boolean)
    const description = descParts.join('\n\n')
    const uid = `aegis-enc-${enc.id}-${start}@agenda`
    lines.push(
      'BEGIN:VEVENT',
      `UID:${uid}`,
      `DTSTAMP:${now}`,
      `DTSTART:${start}`,
      `DTEND:${end}`,
      'SUMMARY:' + icsEscape(summary),
      description ? 'DESCRIPTION:' + icsEscape(description) : '',
      'END:VEVENT'
    )
  })
  lines.push('END:VCALENDAR')
  return lines.filter(Boolean).join('\r\n')
}

function exportToGoogleCalendar() {
  if (exportableItems.value.length === 0) return
  const ics = buildIcsContent()
  const blob = new Blob([ics], { type: 'text/calendar;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `agenda-${courseTitle.value.replace(/[^a-z0-9]+/gi, '-').toLowerCase() || 'encontros'}.ics`
  a.click()
  URL.revokeObjectURL(url)
}

onMounted(async () => {
  try {
    const data = await fetchCurrentCourse()
    const pfe = data.programa_formacao_executiva as {
      cabecalho?: { titulo?: string }
      jornada_aprendizagem?: JornadaSemana[]
    }
    const jornada = pfe?.jornada_aprendizagem ?? []
    const encontroAgendas = data.progress?.encontro_agendas ?? {}

    courseTitle.value = pfe?.cabecalho?.titulo ?? 'Encontros'
    numSemanas.value = jornada.length
    numEncontros.value = jornada.reduce((acc, s) => acc + (s.encontros?.length ?? 0), 0)

    const items = buildAgendaItems(jornada, encontroAgendas)
    const byWeek: Record<number, AgendaItem[]> = {}
    items.forEach((it) => {
      const w = it.semana
      if (!byWeek[w]) byWeek[w] = []
      byWeek[w].push(it)
    })
    itemsByWeek.value = byWeek
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Erro ao carregar agenda.'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="shell">
    <div v-if="loading" class="loading">
      <div class="spin"></div>
      <span>Carregando agenda…</span>
    </div>
    <div v-else-if="error" class="error-msg">{{ error }}</div>
    <template v-else>
      <div class="agenda-head">
        <div class="agenda-kicker">Sua trilha</div>
        <h1 class="agenda-title">Agenda · {{ courseTitle }}</h1>
        <p class="agenda-desc">
          {{ numSemanas }} semanas · {{ numEncontros }} encontros. Passe o mouse sobre um dia para ver os detalhes.
        </p>
        <div v-if="exportableItems.length > 0" class="agenda-export">
          <button type="button" class="btn-export" @click="exportToGoogleCalendar">
            Exportar para Google Calendar
          </button>
          <span class="export-hint">Baixe o arquivo .ics e importe em calendar.google.com (Configurações → Importar)</span>
        </div>
      </div>
      <div class="calendar">
        <div v-for="w in weekNums" :key="w" class="week-col">
          <div class="week-label">Semana {{ w }}</div>
          <div
            v-for="(it, idx) in (itemsByWeek[w] ?? [])"
            :key="`${w}-${it.encontro.id}-${idx}`"
            class="day-card"
            :class="{ 'has-date': !!it.dateStr, 'is-next': isNext(it), 'is-past': isPast(it) }"
            @mouseenter="(e: MouseEvent) => showTooltip(e, it)"
            @mouseleave="hideTooltip"
            @mousemove="placeTooltip"
          >
            <div v-if="isNext(it)" class="day-badge">Próximo encontro</div>
            <div v-if="!isNext(it)" class="day-enc-num day-enc-num--top">Encontro {{ it.encontro.id }}</div>
            <div class="day-date" :class="{ undefined: !it.dateLabel }">
              {{ it.dateLabel ?? 'Data a definir' }}
            </div>
            <div v-if="it.timeLabel" class="day-time">{{ it.timeLabel }}</div>
            <div class="day-title">{{ it.encontro.titulo ?? `Encontro ${it.encontro.id}` }}</div>
          </div>
        </div>
      </div>
    </template>
  </div>

  <div
    ref="tooltipRef"
    class="tooltip"
    :class="{ visible: tooltip.show }"
    :style="{ left: tooltip.x + 'px', top: tooltip.y + 'px' }"
  >
    <div class="tooltip-title">{{ tooltip.title }}</div>
    <div class="tooltip-sub">{{ tooltip.sub }}</div>
    <div class="tooltip-tema">{{ tooltip.tema }}</div>
    <ul class="tooltip-obj">
      <li v-for="(o, i) in tooltip.objetivos" :key="i">{{ o }}</li>
    </ul>
  </div>
</template>

<style scoped>
.shell {
  margin: 0;
  min-height: calc(100vh - var(--bar-h));
  padding: 40px 44px 60px;
}
.loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 50vh;
  gap: 16px;
  color: var(--k5);
}
.spin {
  width: 28px;
  height: 28px;
  border: 1.5px solid var(--k7);
  border-top-color: var(--k3);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
.error-msg {
  text-align: center;
  padding: 60px 24px;
  color: var(--k4);
}

.agenda-head {
  margin-bottom: 36px;
}
.agenda-kicker {
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: var(--k5);
  margin-bottom: 10px;
}
.agenda-title {
  font-family: var(--serif);
  font-size: 32px;
  color: var(--k0);
  margin-bottom: 8px;
}
.agenda-desc {
  font-size: 14px;
  color: var(--k4);
}
.agenda-export {
  margin-top: 20px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
}
.btn-export {
  font-size: 13px;
  font-weight: 600;
  padding: 10px 18px;
  border: 1px solid var(--gold);
  background: transparent;
  color: var(--gold);
  border-radius: 4px;
  cursor: pointer;
  transition: background 0.2s ease, color 0.2s ease;
}
.btn-export:hover {
  background: var(--gold);
  color: var(--k0);
}
.export-hint {
  font-size: 12px;
  color: var(--k5);
}

.calendar {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  column-gap: 56px;
  row-gap: 20px;
  width: 100%;
  align-items: flex-start;
}
.week-col {
  display: flex;
  flex-direction: column;
  gap: 14px;
  align-items: stretch;
}
.week-label {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--k5);
  padding-bottom: 8px;
  border-bottom: 1px solid var(--bd);
}
.day-card {
  background: var(--wh);
  border: 1px solid var(--bd);
  border-radius: 4px;
  padding: 18px 16px;
  height: 140px;
  cursor: pointer;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
  position: relative;
  display: flex;
  flex-direction: column;
}
.day-card:hover {
  border-color: var(--goldbd);
  box-shadow: 0 4px 20px rgba(12, 35, 64, 0.08);
}
.day-card.has-date {
  border-left: 3px solid var(--gold);
}
.day-card.is-next {
  border-color: var(--gold);
  box-shadow: 0 8px 28px rgba(180, 140, 60, 0.4);
  transform: translateY(-1px);
  padding-top: 28px;
}
.day-card.is-past {
  opacity: 0.35;
}
.day-badge {
  position: absolute;
  top: 6px;
  right: 8px;
  font-size: 9px;
  font-weight: 600;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  padding: 3px 8px;
  border-radius: 999px;
  background: var(--gold);
  color: var(--k0);
}
.day-date {
  font-family: var(--serif);
  font-size: 13px;
  color: var(--k0);
  margin-bottom: 4px;
}
.day-date.undefined {
  font-style: italic;
  color: var(--k5);
}
.day-time {
  font-size: 11px;
  color: var(--k5);
  margin-bottom: 8px;
}
.day-enc-num {
  font-size: 9px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--gold);
  margin-top: 6px;
}
.day-title {
  font-size: 12px;
  font-weight: 500;
  color: var(--k1);
  line-height: 1.4;
}
.day-enc-num--top {
  margin-top: 0;
  margin-bottom: 4px;
}

.tooltip {
  position: fixed;
  z-index: 500;
  max-width: 360px;
  background: var(--k0);
  color: var(--wh);
  padding: 20px 22px;
  border-radius: 4px;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.25);
  pointer-events: none;
  opacity: 0;
  visibility: hidden;
  transition: opacity 0.15s ease, visibility 0.15s ease;
}
.tooltip.visible {
  opacity: 1;
  visibility: visible;
}
.tooltip-title {
  font-family: var(--serif);
  font-size: 17px;
  margin-bottom: 6px;
  color: #fff;
}
.tooltip-sub {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.6);
  margin-bottom: 10px;
}
.tooltip-tema {
  font-size: 13px;
  line-height: 1.5;
  color: rgba(255, 255, 255, 0.85);
  margin-bottom: 12px;
}
.tooltip-obj {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.5);
  list-style: none;
  padding-left: 0;
  margin: 0;
}
.tooltip-obj li {
  padding: 2px 0;
  padding-left: 12px;
  position: relative;
}
.tooltip-obj li::before {
  content: '';
  position: absolute;
  left: 0;
  top: 8px;
  width: 4px;
  height: 1px;
  background: var(--gold);
}

@media (max-width: 900px) {
  .calendar {
    grid-template-columns: 1fr 1fr;
  }
}
@media (max-width: 520px) {
  .calendar {
    grid-template-columns: 1fr;
  }
  .shell {
    padding: 24px 20px 40px;
  }
}
</style>
