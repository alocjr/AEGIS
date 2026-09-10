<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  listCanvasProjects,
  createCanvasProject,
  deleteCanvasProject,
  updateCanvasProject,
  aprovarPortfolio,
  aprovarProjeto,
  CANVAS_PRIORIDADES,
  type CanvasProjectSummary,
  type CanvasPrioridade,
  type CanvasMesInicio,
  type CanvasQuadrant,
  type CanvasAprovarProjetoPayload,
} from '@/api/canvasProjects'
import PageHeader from '@/components/ui/PageHeader.vue'
import StateBlock from '@/components/ui/StateBlock.vue'
import AppModal from '@/components/ui/AppModal.vue'
import AppButton from '@/components/ui/AppButton.vue'
import CanvasAprovarModal from '@/components/canvas/CanvasAprovarModal.vue'
import CanvasProjectListItem from '@/components/canvas/CanvasProjectListItem.vue'
import type { ArtifactVisibility } from '@/lib/visibility'

const router = useRouter()
const loading = ref(true)
const creating = ref(false)
const error = ref<string | null>(null)
const items = ref<CanvasProjectSummary[]>([])
const searchQuery = ref('')
const searching = ref(false)
const searchError = ref<string | null>(null)
let searchTimer: ReturnType<typeof setTimeout> | null = null
const deleteTarget = ref<CanvasProjectSummary | null>(null)
const deleteError = ref<string | null>(null)
const priorityFilter = ref<CanvasPrioridade[]>([])
const execError = ref<string | null>(null)

const PRIORITY_RANK: Record<CanvasPrioridade, number> = {
  P0: 0,
  P1: 1,
  P2: 2,
  P3: 3,
  P4: 4,
}

const QUADRANT_LABEL: Record<Exclude<CanvasQuadrant, null>, string> = {
  ganho_rapido: 'Ganho rápido',
  aposta_estrategica: 'Aposta estratégica',
  incremental: 'Incremental',
  evitar: 'Evitar · vaidade',
}

/** Área do plot SVG (eixo valor × viabilidade, scores 1–5) */
const PLOT = { x: 64, y: 40, w: 520, h: 440 }
const VIEWBOX = { w: 720, h: 560 }

type PlotPoint = {
  id: string
  title: string
  cx: number
  cy: number
  quadrant: Exclude<CanvasQuadrant, null>
  score_valor: number
  score_viabilidade: number
  area_negocio: string
  responsavel: string
  objetivo_estrategico: string
  proximo_passo: string
  prioridade: CanvasPrioridade
  mes_inicio: CanvasMesInicio
  fill: string
}

const QUAD_RGB: Record<Exclude<CanvasQuadrant, null>, [number, number, number]> = {
  ganho_rapido: [47, 110, 74],
  aposta_estrategica: [196, 138, 38],
  incremental: [91, 122, 134],
  evitar: [156, 59, 46],
}

/** P0 = cor cheia; P4 mistura quase toda com cinza. */
const PRIO_FADE: Record<CanvasPrioridade, number> = {
  P0: 0,
  P1: 0.22,
  P2: 0.48,
  P3: 0.72,
  P4: 0.9,
}

function dotFill(quadrant: Exclude<CanvasQuadrant, null>, prioridade: CanvasPrioridade): string {
  const [r, g, b] = QUAD_RGB[quadrant]
  const t = PRIO_FADE[prioridade] ?? PRIO_FADE.P4
  const gray = 152
  return `rgb(${Math.round(r + (gray - r) * t)}, ${Math.round(g + (gray - g) * t)}, ${Math.round(b + (gray - b) * t)})`
}

const displayedItems = computed(() => {
  if (!priorityFilter.value.length) return items.value
  const allowed = new Set(priorityFilter.value)
  return items.value.filter((i) => allowed.has(i.prioridade || 'P4'))
})

function isFeatured(item: CanvasProjectSummary): boolean {
  return !!item.projeto_aprovado || item.status === 'aprovado_portfolio'
}

const featuredItems = computed(() => displayedItems.value.filter(isFeatured))
const pipelineItems = computed(() => displayedItems.value.filter((i) => !isFeatured(i)))

const scoredItems = computed(() =>
  displayedItems.value.filter(
    (i) =>
      i.score_valor != null &&
      i.score_viabilidade != null &&
      i.quadrant != null
  )
)

const plotPoints = computed<PlotPoint[]>(() => {
  const groups = new Map<string, CanvasProjectSummary[]>()
  for (const item of scoredItems.value) {
    const key = `${item.score_valor}-${item.score_viabilidade}`
    const list = groups.get(key) ?? []
    list.push(item)
    groups.set(key, list)
  }

  const points: PlotPoint[] = []
  for (const group of groups.values()) {
    group.forEach((item, idx) => {
      const v = item.score_viabilidade as number
      const val = item.score_valor as number
      const baseX = PLOT.x + ((v - 1) / 4) * PLOT.w
      const baseY = PLOT.y + PLOT.h - ((val - 1) / 4) * PLOT.h
      const angle = group.length === 1 ? 0 : (idx / group.length) * Math.PI * 2
      const radius = group.length === 1 ? 0 : 14 + Math.min(idx, 3) * 3
      points.push({
        id: item.id,
        title: item.title || 'Novo projeto',
        cx: baseX + Math.cos(angle) * radius,
        cy: baseY + Math.sin(angle) * radius,
        quadrant: item.quadrant as Exclude<CanvasQuadrant, null>,
        score_valor: val,
        score_viabilidade: v,
        area_negocio: item.area_negocio || '',
        responsavel: item.responsavel || '',
        objetivo_estrategico: item.objetivo_estrategico || '',
        proximo_passo: item.proximo_passo || '',
        prioridade: item.prioridade || 'P4',
        mes_inicio: item.mes_inicio || '',
        fill: dotFill(item.quadrant as Exclude<CanvasQuadrant, null>, item.prioridade || 'P4'),
      })
    })
  }
  return points
})

const unscoredCount = computed(
  () => displayedItems.value.length - scoredItems.value.length
)

const QUADRANT_RANK: Record<Exclude<CanvasQuadrant, null>, number> = {
  ganho_rapido: 0,
  aposta_estrategica: 1,
  incremental: 2,
  evitar: 3,
}

function sortByPriority(list: CanvasProjectSummary[]): CanvasProjectSummary[] {
  return [...list].sort((a, b) => {
    const byPrio = (PRIORITY_RANK[a.prioridade] ?? 4) - (PRIORITY_RANK[b.prioridade] ?? 4)
    if (byPrio !== 0) return byPrio
    const qa = a.quadrant ? (QUADRANT_RANK[a.quadrant] ?? 4) : 4
    const qb = b.quadrant ? (QUADRANT_RANK[b.quadrant] ?? 4) : 4
    const byQuad = qa - qb
    if (byQuad !== 0) return byQuad
    return (b.updated_at || '').localeCompare(a.updated_at || '')
  })
}

function togglePriorityFilter(code: CanvasPrioridade) {
  const current = priorityFilter.value
  priorityFilter.value = current.includes(code)
    ? current.filter((c) => c !== code)
    : [...current, code]
}

async function patchExec(
  item: CanvasProjectSummary,
  body: { prioridade?: CanvasPrioridade; mes_inicio?: CanvasMesInicio; visibility?: ArtifactVisibility }
) {
  execError.value = null
  try {
    const updated = await updateCanvasProject(item.id, body)
    item.prioridade = updated.prioridade || 'P4'
    item.mes_inicio = updated.mes_inicio || ''
    item.visibility = updated.visibility || 'shared'
    items.value = sortByPriority(items.value)
  } catch (e) {
    execError.value = e instanceof Error ? e.message : 'Erro ao salvar prioridade.'
  }
}

function onPrioridadeChange(item: CanvasProjectSummary, ev: Event) {
  const value = (ev.target as HTMLSelectElement).value as CanvasPrioridade
  void patchExec(item, { prioridade: value })
}

function onMesInicioChange(item: CanvasProjectSummary, ev: Event) {
  const value = (ev.target as HTMLSelectElement).value as CanvasMesInicio
  void patchExec(item, { mes_inicio: value })
}

function onVisibilityChange(item: CanvasProjectSummary, value: ArtifactVisibility) {
  void patchExec(item, { visibility: value })
}

function openProject(id: string) {
  hideChartTooltip()
  void router.push(`/projetos/${id}`)
}

function clipText(text: string, max = 180): string {
  const t = text.trim()
  if (t.length <= max) return t
  return `${t.slice(0, max - 1)}…`
}

const hoverPoint = ref<PlotPoint | null>(null)
const tooltipPos = ref({ x: 0, y: 0 })
const tooltipRef = ref<HTMLElement | null>(null)
const TOOLTIP_GAP = 14

function showChartTooltip(ev: MouseEvent, p: PlotPoint) {
  hoverPoint.value = p
  placeChartTooltip(ev)
}

function placeChartTooltip(ev: MouseEvent) {
  if (!hoverPoint.value) return
  const rect = tooltipRef.value?.getBoundingClientRect()
  let left = ev.clientX + TOOLTIP_GAP
  let top = ev.clientY + TOOLTIP_GAP
  if (rect?.width) {
    if (left + rect.width > window.innerWidth - 8) left = ev.clientX - rect.width - TOOLTIP_GAP
    if (left < 8) left = 8
    if (top + rect.height > window.innerHeight - 8) top = ev.clientY - rect.height - TOOLTIP_GAP
    if (top < 8) top = 8
  }
  tooltipPos.value = { x: left, y: top }
}

function hideChartTooltip() {
  hoverPoint.value = null
}

async function refresh() {
  const res = await listCanvasProjects(searchQuery.value)
  items.value = sortByPriority(res.items ?? [])
}

watch(searchQuery, () => {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    void applySearch()
  }, 280)
})

async function applySearch() {
  searching.value = true
  searchError.value = null
  try {
    await refresh()
  } catch (e) {
    searchError.value = e instanceof Error ? e.message : 'Erro ao buscar projetos.'
  } finally {
    searching.value = false
  }
}

async function onCreate() {
  creating.value = true
  error.value = null
  try {
    const created = await createCanvasProject('Novo projeto')
    await router.push(`/projetos/${created.id}`)
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Erro ao criar projeto.'
    creating.value = false
  }
}

function askDelete(item: CanvasProjectSummary, ev: Event) {
  ev.preventDefault()
  ev.stopPropagation()
  deleteTarget.value = item
  deleteError.value = null
}

function cancelDelete() {
  deleteTarget.value = null
  deleteError.value = null
}

const approvingId = ref<string | null>(null)
const approveError = ref<string | null>(null)
const approveTarget = ref<CanvasProjectSummary | null>(null)
const approvingExec = ref(false)
const approveExecError = ref<string | null>(null)

function applyApproval(item: CanvasProjectSummary, updated: CanvasProjectSummary) {
  item.projeto_aprovado = updated.projeto_aprovado
  item.aprovacao_comentario = updated.aprovacao_comentario
  item.data_inicio_real = updated.data_inicio_real
  item.periodicidade = updated.periodicidade
  item.aprovado_em = updated.aprovado_em
}

function openApprove(item: CanvasProjectSummary, ev?: Event) {
  ev?.preventDefault()
  ev?.stopPropagation()
  approveTarget.value = item
  approveExecError.value = null
}

function cancelApprove() {
  if (approvingExec.value) return
  approveTarget.value = null
  approveExecError.value = null
}

async function submitApprove(payload: CanvasAprovarProjetoPayload) {
  if (!approveTarget.value) return
  approvingExec.value = true
  approveExecError.value = null
  try {
    const updated = await aprovarProjeto(approveTarget.value.id, payload)
    applyApproval(approveTarget.value, updated)
    approveTarget.value = null
  } catch (e) {
    approveExecError.value = e instanceof Error ? e.message : 'Erro ao aprovar o projeto.'
  } finally {
    approvingExec.value = false
  }
}

async function onApprovePortfolio(item: CanvasProjectSummary, ev: Event) {
  ev.preventDefault()
  ev.stopPropagation()
  approvingId.value = item.id
  approveError.value = null
  try {
    const result = await aprovarPortfolio(item.id)
    item.status = 'aprovado_portfolio'
    item.ai_system_id = result.ai_system_id
  } catch (e) {
    approveError.value = e instanceof Error ? e.message : 'Erro ao aprovar para o portfólio.'
  } finally {
    approvingId.value = null
  }
}

async function confirmDelete() {
  if (!deleteTarget.value) return
  try {
    await deleteCanvasProject(deleteTarget.value.id)
    items.value = items.value.filter((i) => i.id !== deleteTarget.value!.id)
    cancelDelete()
  } catch (e) {
    deleteError.value = e instanceof Error ? e.message : 'Erro ao excluir.'
  }
}

onMounted(async () => {
  try {
    await refresh()
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Erro ao carregar projetos.'
  } finally {
    loading.value = false
  }
})

onUnmounted(() => {
  if (searchTimer) clearTimeout(searchTimer)
})
</script>

<template>
  <div class="wrap">
    <PageHeader
      title="Projetos · Canvas de Oportunidades"
      subtitle="Um canvas por área de negócio. Crie um projeto, abra o canvas e preencha da dor à decisão (01→08)."
    />

    <StateBlock v-if="loading" state="loading" />
    <StateBlock v-else-if="error" state="error" :message="error" />

    <template v-else>
      <div class="card card-cta">
        <input
          v-model="searchQuery"
          type="search"
          class="search-input"
          placeholder="Buscar por palavras no canvas"
          aria-label="Buscar projetos por palavras em qualquer texto do canvas"
        />
        <button type="button" class="btn-new" :disabled="creating" @click="onCreate">
          {{ creating ? 'Criando…' : '+ Novo projeto' }}
        </button>
        <div class="prio-filter" role="group" aria-label="Filtrar por prioridade">
          <span class="prio-filter-label">Prioridade</span>
          <button
            v-for="p in CANVAS_PRIORIDADES"
            :key="p.id"
            type="button"
            class="prio-chip"
            :class="{ on: priorityFilter.includes(p.id) }"
            :title="p.label"
            :aria-pressed="priorityFilter.includes(p.id)"
            @click="togglePriorityFilter(p.id)"
          >
            {{ p.id }}
          </button>
        </div>
      </div>

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
            :viewBox="`0 0 ${VIEWBOX.w} ${VIEWBOX.h}`"
            role="img"
            aria-label="Matriz de valor versus viabilidade com os projetos pontuados"
          >
            <rect
              :x="PLOT.x"
              :y="PLOT.y"
              :width="PLOT.w / 2"
              :height="PLOT.h / 2"
              class="qbg qbg-bet"
            />
            <rect
              :x="PLOT.x + PLOT.w / 2"
              :y="PLOT.y"
              :width="PLOT.w / 2"
              :height="PLOT.h / 2"
              class="qbg qbg-go"
            />
            <rect
              :x="PLOT.x"
              :y="PLOT.y + PLOT.h / 2"
              :width="PLOT.w / 2"
              :height="PLOT.h / 2"
              class="qbg qbg-avoid"
            />
            <rect
              :x="PLOT.x + PLOT.w / 2"
              :y="PLOT.y + PLOT.h / 2"
              :width="PLOT.w / 2"
              :height="PLOT.h / 2"
              class="qbg qbg-inc"
            />

            <text
              :x="PLOT.x + PLOT.w / 4"
              :y="PLOT.y + 22"
              class="qlabel qlabel-bet"
              text-anchor="middle"
            >Aposta estratégica</text>
            <text
              :x="PLOT.x + (PLOT.w * 3) / 4"
              :y="PLOT.y + 22"
              class="qlabel qlabel-go"
              text-anchor="middle"
            >Ganho rápido</text>
            <text
              :x="PLOT.x + PLOT.w / 4"
              :y="PLOT.y + PLOT.h / 2 + 22"
              class="qlabel qlabel-avoid"
              text-anchor="middle"
            >Evitar · vaidade</text>
            <text
              :x="PLOT.x + (PLOT.w * 3) / 4"
              :y="PLOT.y + PLOT.h / 2 + 22"
              class="qlabel qlabel-inc"
              text-anchor="middle"
            >Incremental</text>

            <line
              :x1="PLOT.x + PLOT.w / 2"
              :y1="PLOT.y"
              :x2="PLOT.x + PLOT.w / 2"
              :y2="PLOT.y + PLOT.h"
              class="axis-cross"
            />
            <line
              :x1="PLOT.x"
              :y1="PLOT.y + PLOT.h / 2"
              :x2="PLOT.x + PLOT.w"
              :y2="PLOT.y + PLOT.h / 2"
              class="axis-cross"
            />

            <rect
              :x="PLOT.x"
              :y="PLOT.y"
              :width="PLOT.w"
              :height="PLOT.h"
              class="plot-frame"
              fill="none"
            />

            <text
              :x="PLOT.x + PLOT.w / 2"
              :y="PLOT.y + PLOT.h + 38"
              class="axis-caption"
              text-anchor="middle"
            >Viabilidade →</text>
            <text
              :x="20"
              :y="PLOT.y + PLOT.h / 2"
              class="axis-caption"
              text-anchor="middle"
              :transform="`rotate(-90, 20, ${PLOT.y + PLOT.h / 2})`"
            >Valor →</text>

            <g v-for="n in 5" :key="'tx' + n">
              <text
                :x="PLOT.x + ((n - 1) / 4) * PLOT.w"
                :y="PLOT.y + PLOT.h + 16"
                class="tick"
                text-anchor="middle"
              >{{ n }}</text>
            </g>
            <g v-for="n in 5" :key="'ty' + n">
              <text
                :x="PLOT.x - 12"
                :y="PLOT.y + PLOT.h - ((n - 1) / 4) * PLOT.h + 4"
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
              :aria-label="`${p.title}. Prioridade ${p.prioridade}. ${QUADRANT_LABEL[p.quadrant]}. Valor ${p.score_valor}, Viabilidade ${p.score_viabilidade}. Abrir canvas.`"
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
                r="15"
                class="dot"
                :data-q="p.quadrant"
                :data-prio="p.prioridade"
                :style="{ fill: p.fill }"
              />
              <text
                :x="p.cx"
                :y="p.cy + 4"
                class="dot-label"
                text-anchor="middle"
              >{{ p.prioridade }}</text>
            </g>
          </svg>

          <p v-if="plotPoints.length === 0" class="chart-empty">
            <template v-if="searchQuery.trim()">
              Nenhum projeto pontuado corresponde à busca.
            </template>
            <template v-else>
              Nenhum projeto pontuado ainda. Abra um canvas e preencha Valor e Viabilidade no bloco 08.
            </template>
          </p>
        </div>
      </div>

      <div v-if="searchError" class="card error-msg">{{ searchError }}</div>
      <div v-if="execError" class="card error-msg">{{ execError }}</div>

      <div v-if="items.length === 0" class="card card-empty">
        <template v-if="searchQuery.trim()">
          <p>Nenhum projeto com essas palavras.</p>
          <p class="empty-hint">A busca olha título, área, dores, cronograma e o restante do canvas.</p>
        </template>
        <template v-else>
          <p>Você ainda não tem projetos.</p>
          <button type="button" class="link-new" :disabled="creating" @click="onCreate">
            Criar primeiro projeto →
          </button>
        </template>
      </div>

      <div v-else-if="displayedItems.length === 0" class="card card-empty">
        <p>Nenhum projeto com as prioridades selecionadas.</p>
        <p class="empty-hint">Desmarque os filtros P0–P4 para ver todos.</p>
      </div>

      <template v-else>
        <section v-if="featuredItems.length" class="list-block">
          <header class="list-block-head">
            <h2>Aprovados e no portfólio</h2>
            <p>
              {{ featuredItems.length }}
              {{ featuredItems.length === 1 ? 'projeto em execução' : 'projetos em execução' }}.
            </p>
          </header>
          <ul class="list" :class="{ dimmed: searching }">
            <CanvasProjectListItem
              v-for="item in featuredItems"
              :key="'f-' + item.id"
              :item="item"
              :approving-portfolio="approvingId === item.id"
              @prioridade="onPrioridadeChange(item, $event)"
              @mes="onMesInicioChange(item, $event)"
              @visibility="onVisibilityChange(item, $event)"
              @approve="openApprove(item, $event)"
              @approve-portfolio="onApprovePortfolio(item, $event)"
              @delete="askDelete(item, $event)"
            />
          </ul>
        </section>

        <section v-if="pipelineItems.length" class="list-block">
          <header class="list-block-head">
            <h2>Demais projetos</h2>
            <p>
              {{ pipelineItems.length }}
              {{ pipelineItems.length === 1 ? 'projeto em elaboração' : 'projetos em elaboração' }}.
            </p>
          </header>
          <ul class="list" :class="{ dimmed: searching }">
            <CanvasProjectListItem
              v-for="item in pipelineItems"
              :key="'p-' + item.id"
              :item="item"
              :approving-portfolio="approvingId === item.id"
              @prioridade="onPrioridadeChange(item, $event)"
              @mes="onMesInicioChange(item, $event)"
              @visibility="onVisibilityChange(item, $event)"
              @approve="openApprove(item, $event)"
              @approve-portfolio="onApprovePortfolio(item, $event)"
              @delete="askDelete(item, $event)"
            />
          </ul>
        </section>
      </template>
      <p v-if="(searchQuery.trim() || priorityFilter.length) && displayedItems.length > 0" class="filter-hint">
        {{ displayedItems.length }} {{ displayedItems.length === 1 ? 'projeto' : 'projetos' }}
        <template v-if="priorityFilter.length">
          · {{ priorityFilter.slice().sort().join(', ') }}
        </template>
      </p>
      <p v-if="approveError" class="error-msg">{{ approveError }}</p>
    </template>

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
            {{ hoverPoint.prioridade }} · {{ QUADRANT_LABEL[hoverPoint.quadrant] }}
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
            <div v-if="hoverPoint.mes_inicio">
              <dt>Início</dt>
              <dd>{{ hoverPoint.mes_inicio }}</dd>
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
    <CanvasAprovarModal
      :open="!!approveTarget"
      :saving="approvingExec"
      :error="approveExecError"
      :already-approved="!!approveTarget?.projeto_aprovado"
      :initial-comentario="approveTarget?.aprovacao_comentario"
      :initial-data-inicio-real="approveTarget?.data_inicio_real"
      :initial-periodicidade="approveTarget?.periodicidade || ''"
      @close="cancelApprove"
      @submit="submitApprove"
    />
  </div>
</template>

<style scoped>
.wrap {
  max-width: 1080px;
  margin: 0 auto;
  padding: 28px 20px 60px;
}
.page-header {
  margin-bottom: 24px;
}
.page-title {
  font-family: var(--serif);
  font-size: 28px;
  color: var(--k0);
  margin-bottom: 6px;
}
.page-desc {
  font-size: 14px;
  color: var(--k5);
  line-height: 1.55;
  max-width: 52ch;
}
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
  color: var(--k5);
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
.dot-label {
  fill: #fff;
  font-size: 9px;
  font-weight: 800;
  letter-spacing: 0.02em;
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
  color: var(--k5);
  text-align: center;
  margin: 8px 0 12px;
  max-width: 42ch;
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
.search-input {
  flex: 1 1 240px;
  min-width: 200px;
  padding: 10px 14px;
  border: 1px solid var(--bd);
  border-radius: var(--r-md);
  font-size: 14px;
  font-family: inherit;
  background: #fff;
  color: var(--k0);
}
.search-input:focus {
  outline: none;
  border-color: var(--k0);
}
.search-input::-webkit-search-cancel-button {
  cursor: pointer;
}
.prio-filter {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  margin-left: auto;
}
.prio-filter-label {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--k5);
  margin-right: 2px;
}
.prio-chip {
  min-width: 36px;
  padding: 5px 8px;
  border: 1px solid var(--bd);
  border-radius: var(--r-md);
  background: #fff;
  color: var(--k4);
  font-size: 12px;
  font-weight: 700;
  font-family: inherit;
  cursor: pointer;
}
.prio-chip:hover {
  border-color: var(--k0);
  color: var(--k0);
}
.prio-chip.on {
  background: var(--k0);
  border-color: var(--k0);
  color: var(--wh);
}
.card-empty {
  text-align: center;
  color: var(--k5);
  padding: 36px 20px;
}
.empty-hint {
  margin: 8px 0 0;
  font-size: 13px;
  color: var(--k5);
}
.filter-hint {
  margin: 8px 2px 0;
  font-size: 13px;
  color: var(--k5);
}
.list-block {
  margin-bottom: 28px;
}
.list-block-head {
  margin-bottom: 12px;
}
.list-block-head h2 {
  font-family: var(--serif);
  font-size: 20px;
  color: var(--k0);
  margin: 0 0 4px;
}
.list-block-head p {
  font-size: 13px;
  color: var(--k5);
  margin: 0;
  line-height: 1.45;
}
.list.dimmed {
  opacity: 0.65;
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
@media (max-width: 640px) {
  .prio-filter {
    margin-left: 0;
    width: 100%;
  }
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
