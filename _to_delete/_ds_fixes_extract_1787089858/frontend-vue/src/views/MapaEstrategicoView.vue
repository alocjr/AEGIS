<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import {
  fetchStrategicMap,
  type StrategicMap,
  type StrategicMapDimension,
  type StrategicMapInitiative,
  type StrategicMapItem,
  type StrategicMapQuestion,
} from '@/api/strategicMap'
import {
  createCanvasProject,
  listCanvasProjects,
  updateCanvasProject,
  type CanvasProjectPayload,
  type CanvasProjectSummary,
} from '@/api/canvasProjects'
import { createSwotFromMaturity, type SwotListField, type SwotTowsField } from '@/api/swotAnalysis'
import {
  buildStrategicMapGraph,
  lineageOf,
  visibleEdges,
  type MapEdge,
  type MapLens,
  type MapNode,
  type StrategicMapGraph,
} from '@/lib/strategicMapGraph'

const route = useRoute()
const router = useRouter()

const loading = ref(true)
const error = ref<string | null>(null)
const notice = ref<string | null>(null)
const busy = ref(false)
const map = ref<StrategicMap | null>(null)
const projects = ref<CanvasProjectSummary[]>([])

const lens = ref<MapLens>('ges')
const focusId = ref<string | null>(null)
const dockOpen = ref(false)
const staging = ref(false)
const actIndex = ref(0)
const linkPanel = ref<string | null>(null)

const mapEl = ref<HTMLElement | null>(null)
const paths = ref<DrawnPath[]>([])
let resizeObserver: ResizeObserver | null = null

type DrawnPath = {
  d: string
  stroke: string
  width: number
  opacity: number
  dash: string
}

const QUADRANT_LABEL: Record<SwotListField, string> = {
  forcas: 'Força',
  oportunidades: 'Oportunidade',
  fraquezas: 'Fraqueza',
  ameacas: 'Ameaça',
}

const TOWS_LABEL: Record<SwotTowsField, string> = {
  tows_fo: 'F × O · Ofensiva',
  tows_fa: 'F × A · Defesa',
  tows_fxo: 'f × O · Reforço',
  tows_fxa: 'f × A · Sobrevivência',
}

function clip(text: string, max: number): string {
  const value = (text || '').trim()
  return value.length <= max ? value : `${value.slice(0, max - 1).trimEnd()}…`
}

function formatDate(iso: string | null): string {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleDateString('pt-BR', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    })
  } catch {
    return iso
  }
}

const graph = computed<StrategicMapGraph>(() => buildStrategicMapGraph(map.value))
const stats = computed(() => map.value?.stats ?? null)
const head = computed(() => map.value?.source ?? null)
const focusSet = computed(() => {
  if (!focusId.value) return null
  return lineageOf(focusId.value, graph.value.edges)
})
const focusedNode = computed<MapNode | null>(() => {
  if (!focusId.value) return null
  return graph.value.nodeById.get(focusId.value) ?? null
})
const visibleColumns = computed(() => graph.value.columns)
const acts = computed(() => graph.value.acts)
const currentAct = computed(() => acts.value[actIndex.value] ?? null)

const sourceOptions = computed(() =>
  (map.value?.sources ?? []).map((source) => {
    const parts = [formatDate(source.submitted_at)]
    if (source.tier_label) parts.push(source.tier_label)
    if (source.level_label) parts.push(source.level_label)
    if (!source.complete && source.maturity_response_id) parts.push('rascunho')
    return {
      value: source.swot_id ? `sw:${source.swot_id}` : `mr:${source.maturity_response_id}`,
      label: parts.filter(Boolean).join(' · '),
      hasSwot: !!source.swot_id,
    }
  })
)

const selectedSource = computed(() => {
  const current = head.value
  if (!current) return ''
  if (current.swot_id) return `sw:${current.swot_id}`
  return current.maturity_response_id ? `mr:${current.maturity_response_id}` : ''
})

const unlinkedSummary = computed(() => {
  const doc = map.value
  if (!doc) return null
  const counts = {
    items: doc.unlinked.swot_items.length,
    initiatives: doc.unlinked.initiatives.length,
    projects: doc.unlinked.projects.length,
    objectives: doc.unlinked.objectives.length,
    krs: doc.unlinked.key_results.length,
  }
  if (!Object.values(counts).some(Boolean)) return null
  return counts
})

function cssVar(name: string, fallback: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback
}

function edgeStyle(kind: MapEdge['kind']): { stroke: string; width: number; opacity: number; dash: string } {
  if (kind === 'hot') return { stroke: cssVar('--low', '#b63737'), width: 2, opacity: 0.8, dash: '' }
  if (kind === 'dash') {
    return { stroke: cssVar('--gold', '#9b7e46'), width: 1.3, opacity: 0.55, dash: '4 4' }
  }
  if (kind === 'sec') {
    return { stroke: cssVar('--gold2', '#b8975a'), width: 1.1, opacity: 0.35, dash: '' }
  }
  return { stroke: cssVar('--gold', '#9b7e46'), width: 1.4, opacity: 0.55, dash: '' }
}

function redraw() {
  const root = mapEl.value
  if (!root || lens.value === 'pan') {
    paths.value = []
    return
  }
  const box = root.getBoundingClientRect()
  if (box.width < 8 || box.height < 8) {
    paths.value = []
    return
  }
  const next: DrawnPath[] = []
  const focused = focusSet.value
  for (const edge of visibleEdges(graph.value.edges, lens.value)) {
    const fromEl = root.querySelector<HTMLElement>(`[data-nid="${edge.from}"]`)
    const toEl = root.querySelector<HTMLElement>(`[data-nid="${edge.to}"]`)
    if (!fromEl || !toEl || fromEl.offsetParent === null || toEl.offsetParent === null) continue
    const a = fromEl.getBoundingClientRect()
    const b = toEl.getBoundingClientRect()
    const x1 = a.right - box.left
    const y1 = a.top - box.top + a.height / 2
    const x2 = b.left - box.left
    const y2 = b.top - box.top + b.height / 2
    const dx = (x2 - x1) * 0.55
    const inFocus = !focused || (focused.has(edge.from) && focused.has(edge.to))
    const style = edgeStyle(edge.kind)
    next.push({
      d: `M ${x1} ${y1} C ${x1 + dx} ${y1}, ${x2 - dx} ${y2}, ${x2} ${y2}`,
      stroke: style.stroke,
      width: style.width,
      opacity: focused && !inFocus ? 0.06 : style.opacity,
      dash: style.dash,
    })
  }
  paths.value = next
}

function scheduleDraw() {
  void nextTick(() => requestAnimationFrame(redraw))
}

function nodeClass(node: MapNode): Record<string, boolean> {
  const focused = focusSet.value
  return {
    [node.accent]: !!node.accent,
    lit: focusId.value === node.id,
    dim: !!focused && !focused.has(node.id),
    'only-lin': node.kind === 'watch',
  }
}

function setLens(next: MapLens) {
  lens.value = next
  if (next === 'pan') {
    dockOpen.value = false
    if (!staging.value) focusId.value = null
  } else if (focusId.value && graph.value.nodeById.get(focusId.value)?.kind === 'watch' && next !== 'lin') {
    clearFocus()
  }
  scheduleDraw()
}

function focusNode(id: string, openDock = true) {
  if (!graph.value.nodeById.has(id)) return
  if (lens.value === 'pan') lens.value = 'ges'
  focusId.value = id
  dockOpen.value = openDock
  linkPanel.value = null
  scheduleDraw()
}

function clearFocus() {
  focusId.value = null
  dockOpen.value = false
  linkPanel.value = null
  scheduleDraw()
}

function startStage() {
  if (!acts.value.length) return
  staging.value = true
  actIndex.value = 0
  if (lens.value === 'pan') lens.value = 'ges'
  showAct()
}

function showAct() {
  const act = acts.value[actIndex.value]
  if (!act) return
  focusNode(act.focusId, false)
  dockOpen.value = false
}

function stopStage() {
  staging.value = false
  clearFocus()
}

function prevAct() {
  if (actIndex.value > 0) {
    actIndex.value -= 1
    showAct()
  }
}

function nextAct() {
  if (actIndex.value < acts.value.length - 1) {
    actIndex.value += 1
    showAct()
  }
}

function onKeydown(event: KeyboardEvent) {
  if (event.key !== 'Escape') return
  if (staging.value) stopStage()
  else clearFocus()
}

function isLinked(project: CanvasProjectSummary, kind: 'item' | 'tows', refId: string): boolean {
  const refs = kind === 'item' ? project.swot_item_ids : project.tows_ids
  return refs.includes(refId)
}

function togglePanel(key: string) {
  linkPanel.value = linkPanel.value === key ? null : key
}

function currentParams(): { maturityResponseId?: string | null; swotId?: string | null } {
  const current = head.value
  if (current?.swot_id) return { swotId: current.swot_id }
  return { maturityResponseId: current?.maturity_response_id ?? null }
}

function originContext(dim: StrategicMapDimension, question: StrategicMapQuestion): string[] {
  const answer = `Resposta: nota ${question.answer}/5`
  return [
    clip(`Origem: ${dim.name} · ${question.id} — ${question.text}`, 400),
    clip(question.answer_text ? `${answer} — ${question.answer_text}` : answer, 400),
  ]
}

function findItemContext(itemId: string): {
  dim: StrategicMapDimension
  question: StrategicMapQuestion
  item: StrategicMapItem
} | null {
  const doc = map.value
  if (!doc) return null
  for (const dim of doc.dimensions) {
    for (const question of dim.questions) {
      const item = question.items.find((entry) => entry.id === itemId)
      if (item) return { dim, question, item }
    }
  }
  return null
}

function findInitiative(id: string): { initiative: StrategicMapInitiative; item: StrategicMapItem | null } | null {
  const doc = map.value
  if (!doc) return null
  for (const dim of doc.dimensions) {
    for (const question of dim.questions) {
      for (const item of question.items) {
        const initiative = item.initiatives.find((entry) => entry.id === id)
        if (initiative) return { initiative, item }
      }
    }
  }
  const orphan = doc.unlinked.initiatives.find((entry) => entry.id === id)
  if (orphan) return { initiative: orphan, item: null }
  return null
}

function itemPrefill(item: StrategicMapItem, dim?: StrategicMapDimension, question?: StrategicMapQuestion): CanvasProjectPayload {
  const negative = item.quadrant === 'fraquezas' || item.quadrant === 'ameacas'
  return {
    title: clip(item.texto || `${QUADRANT_LABEL[item.quadrant]}`, 200),
    objetivo_estrategico: clip(head.value?.optica || '', 2000),
    contexto: dim && question ? originContext(dim, question) : [],
    dores: negative ? [clip(item.texto, 400)] : [],
    oportunidade: negative ? [] : [clip(item.texto, 400)],
    swot_id: head.value?.swot_id ?? null,
    swot_item_ids: [item.id],
    tows_ids: [],
  }
}

function initiativePrefill(initiative: StrategicMapInitiative, item: StrategicMapItem | null): CanvasProjectPayload {
  const ctx = item ? findItemContext(item.id) : null
  const negative = item?.quadrant === 'fraquezas' || item?.quadrant === 'ameacas'
  const opportunities = initiative.counterparts
    .filter((counterpart) => counterpart.quadrant === 'oportunidades')
    .map((counterpart) => clip(counterpart.texto, 400))
    .filter(Boolean)
  const threats = initiative.counterparts
    .filter((counterpart) => counterpart.quadrant === 'ameacas')
    .map((counterpart) => clip(counterpart.texto, 400))
    .filter(Boolean)
  return {
    title: clip(initiative.acao || TOWS_LABEL[initiative.field], 200),
    objetivo_estrategico: clip(initiative.acao || head.value?.optica || '', 2000),
    contexto: [
      ...(ctx ? originContext(ctx.dim, ctx.question) : []),
      item ? clip(`Estratégia ${TOWS_LABEL[initiative.field]} sobre «${item.texto}»`, 400) : '',
    ].filter(Boolean),
    dores: negative && item ? [clip(item.texto, 400)] : [],
    oportunidade: opportunities.length ? opportunities : item ? [clip(item.texto, 400)] : [],
    riscos: threats,
    proximo_passo: clip(initiative.acao, 4000),
    swot_id: head.value?.swot_id ?? null,
    swot_item_ids: item ? [item.id] : [],
    tows_ids: [initiative.id],
  }
}

async function reload(params?: { maturityResponseId?: string | null; swotId?: string | null }) {
  const [doc, list] = await Promise.all([fetchStrategicMap(params), listCanvasProjects()])
  map.value = doc
  projects.value = list.items
  return doc
}

async function load(params?: { maturityResponseId?: string | null; swotId?: string | null }) {
  loading.value = true
  error.value = null
  try {
    await reload(params)
    scheduleDraw()
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Falha ao carregar o mapa estratégico.'
  } finally {
    loading.value = false
  }
}

async function onSelectSource(event: Event) {
  const value = (event.target as HTMLSelectElement).value
  const [kind, id] = value.split(':')
  if (!id) return
  linkPanel.value = null
  notice.value = null
  clearFocus()
  const params = kind === 'sw' ? { swotId: id } : { maturityResponseId: id }
  await router.replace({
    query: kind === 'sw' ? { swot: id } : { maturidade: id },
  })
  await load(params)
}

async function generateSwot() {
  const responseId = head.value?.maturity_response_id
  if (!responseId || busy.value) return
  busy.value = true
  notice.value = null
  try {
    const created = await createSwotFromMaturity(responseId)
    await reload({ swotId: created.id })
    notice.value = 'SWOT gerada a partir da autoavaliação.'
    scheduleDraw()
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Falha ao gerar a SWOT.'
  } finally {
    busy.value = false
  }
}

async function applyLink(
  project: CanvasProjectSummary,
  kind: 'item' | 'tows',
  refId: string,
  link: boolean
) {
  if (busy.value) return
  busy.value = true
  notice.value = null
  try {
    const itemRefs = new Set(project.swot_item_ids)
    const towsRefs = new Set(project.tows_ids)
    const target = kind === 'item' ? itemRefs : towsRefs
    if (link) target.add(refId)
    else target.delete(refId)
    const stillLinked = itemRefs.size + towsRefs.size > 0
    await updateCanvasProject(project.id, {
      swot_item_ids: [...itemRefs],
      tows_ids: [...towsRefs],
      swot_id: stillLinked ? head.value?.swot_id ?? null : null,
    })
    await reload(currentParams())
    notice.value = link ? 'Projeto vinculado ao mapa.' : 'Vínculo removido.'
    scheduleDraw()
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Falha ao atualizar o vínculo.'
  } finally {
    busy.value = false
  }
}

async function createProject(prefill: CanvasProjectPayload) {
  if (busy.value) return
  busy.value = true
  notice.value = null
  try {
    const created = await createCanvasProject(prefill.title || 'Novo projeto')
    await updateCanvasProject(created.id, prefill)
    await reload(currentParams())
    linkPanel.value = null
    notice.value = 'Projeto criado a partir do mapa — complete o canvas em Projetos.'
    scheduleDraw()
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Falha ao criar o projeto.'
  } finally {
    busy.value = false
  }
}

function dockInitiatives(node: MapNode): StrategicMapInitiative[] {
  if (node.kind !== 'tows' || !node.towsField) return []
  return node.initiativeIds
    .map((id) => findInitiative(id)?.initiative)
    .filter((init): init is StrategicMapInitiative => !!init)
}

function dockItems(node: MapNode): StrategicMapItem[] {
  if (node.kind !== 'quad') return []
  const doc = map.value
  if (!doc || !node.quadrant) return []
  const byId = new Map<string, StrategicMapItem>()
  for (const dim of doc.dimensions) {
    for (const question of dim.questions) {
      for (const item of question.items) {
        if (item.quadrant === node.quadrant) byId.set(item.id, item)
      }
    }
  }
  for (const item of doc.unlinked.swot_items) {
    if (item.quadrant === node.quadrant) byId.set(item.id, item)
  }
  return node.itemIds.map((id) => byId.get(id)).filter((item): item is StrategicMapItem => !!item)
}

function emptyHint(columnTitle: string, roman: string): string {
  if (roman === 'I') return 'Sem diagnóstico de origem.'
  if (roman === 'II') return head.value?.swot_id ? 'Sem posições nesta SWOT.' : 'Gere a SWOT para ver as posições.'
  if (roman === 'III') return 'Sem cruzamento TOWS ainda.'
  if (roman === 'IV') return map.value?.okr_cycle ? 'Objectives ainda sem origem no mapa.' : 'Ative um ciclo OKR.'
  if (roman === 'V') return 'Sem projetos vinculados à árvore.'
  return `Sem nós em ${columnTitle}.`
}

onMounted(() => {
  const swot = (route.query.swot as string) || null
  const maturity = (route.query.maturidade as string) || null
  const hash = location.hash.replace('#', '')
  if (hash === 'pan' || hash === 'lin' || hash === 'ges') lens.value = hash
  document.addEventListener('keydown', onKeydown)
  void load(swot ? { swotId: swot } : maturity ? { maturityResponseId: maturity } : undefined)
})

onUnmounted(() => {
  document.removeEventListener('keydown', onKeydown)
  resizeObserver?.disconnect()
})

watch(mapEl, (el) => {
  resizeObserver?.disconnect()
  if (!el || typeof ResizeObserver === 'undefined') return
  resizeObserver = new ResizeObserver(() => scheduleDraw())
  resizeObserver.observe(el)
})

watch([lens, graph, focusId], () => scheduleDraw())
</script>

<template>
  <div class="wrap" :class="[`lens-${lens}`, { staging }]">
    <header class="page-header">
      <p class="eyebrow">Etapa VI · leitura viva da estratégia</p>
      <h1 class="page-title">Mapa Estratégico</h1>
      <p class="page-lead">
        Diagnóstico → posições → apostas → compromissos → entrega. Clique em um nó para iluminar o
        fio — origem e consequência — e abrir o dossiê.
      </p>
    </header>

    <div v-if="loading" class="state-card">Carregando o mapa…</div>

    <template v-else>
      <div v-if="error" class="state-card error">{{ error }}</div>

      <div v-if="!head?.maturity_response_id && !head?.swot_id" class="state-card">
        <p class="empty-title">Ainda não há o que mapear</p>
        <p class="empty-text">
          Responda o Modelo de Maturidade e gere a SWOT para ver o mapa de rastreabilidade.
        </p>
        <RouterLink to="/ai-maturity" class="btn primary">Abrir Modelo de Maturidade</RouterLink>
      </div>

      <template v-else>
        <section class="card source-card">
          <div class="source-main">
            <div class="source-field">
              <label class="field-label" for="source-select">Ciclo de origem</label>
              <select
                id="source-select"
                class="select"
                :value="selectedSource"
                @change="onSelectSource"
              >
                <option v-for="option in sourceOptions" :key="option.value" :value="option.value">
                  {{ option.label }}{{ option.hasSwot ? '' : ' · sem SWOT' }}
                </option>
              </select>
            </div>
            <div class="source-meta">
              <span v-if="head?.tier_label" class="meta-pill">{{ head.tier_label }}</span>
              <span v-if="head?.result?.level_label" class="meta-pill">{{ head.result.level_label }}</span>
              <span v-if="head?.result" class="meta-item">
                {{ head.result.total_score }}/{{ head.result.max_score }} pts ·
                {{ Math.round(head.result.percent_score) }}%
              </span>
              <span v-if="map?.okr_cycle" class="meta-item">
                OKR
                <RouterLink :to="`/okrs/${map.okr_cycle.id}`" class="link">{{ map.okr_cycle.label }}</RouterLink>
              </span>
            </div>
          </div>
          <p v-if="head?.optica" class="source-optica">{{ head.optica }}</p>
          <div class="source-actions">
            <RouterLink
              v-if="head?.maturity_response_id"
              :to="`/ai-maturity/${head.maturity_response_id}`"
              class="btn"
            >Ver diagnóstico</RouterLink>
            <RouterLink v-if="head?.swot_id" :to="`/swot/${head.swot_id}`" class="btn">Abrir SWOT</RouterLink>
            <button
              v-else-if="head?.maturity_response_id"
              type="button"
              class="btn primary"
              :disabled="busy"
              @click="generateSwot"
            >{{ busy ? 'Gerando…' : 'Gerar SWOT' }}</button>
            <RouterLink to="/okrs" class="btn">OKR</RouterLink>
            <RouterLink to="/projetos" class="btn">Projetos</RouterLink>
          </div>
          <p v-if="notice" class="notice">{{ notice }}</p>
          <p v-if="!map?.okr_cycle" class="notice warn-note">
            Nenhum ciclo OKR ativo — a coluna de compromissos fica vazia.
            <RouterLink to="/okrs" class="link">Abrir painel de OKR</RouterLink>
          </p>
        </section>

        <section v-if="stats" class="kpi-grid">
          <div class="kpi-card">
            <div class="kpi-label">Pilares</div>
            <div class="kpi-value">{{ stats.dimensions }}</div>
            <div class="kpi-sub">{{ stats.questions }} pergunta(s)</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-label">Posições</div>
            <div class="kpi-value">{{ stats.swot_items }}</div>
            <div class="kpi-sub">{{ stats.watchlist }} em atenção</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-label">Apostas</div>
            <div class="kpi-value">{{ stats.initiatives }}</div>
            <div class="kpi-sub">estratégias TOWS</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-label">Compromissos</div>
            <div class="kpi-value">{{ stats.objectives_linked }}</div>
            <div class="kpi-sub">de {{ stats.objectives }} objectives</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-label">Entrega</div>
            <div class="kpi-value gold">{{ stats.projects_linked }}</div>
            <div class="kpi-sub">de {{ stats.projects_total }} projetos</div>
          </div>
        </section>

        <div class="toolrow">
          <div class="seg" role="tablist" aria-label="Lentes de leitura">
            <button type="button" :class="{ on: lens === 'pan' }" @click="setLens('pan')">
              Panorama · Conselho
            </button>
            <button type="button" :class="{ on: lens === 'ges' }" @click="setLens('ges')">
              Gestão · Diretoria
            </button>
            <button type="button" :class="{ on: lens === 'lin' }" @click="setLens('lin')">
              Linhagem · Auditoria
            </button>
          </div>
          <div class="tool-actions">
            <button type="button" class="btn" @click="clearFocus">Limpar foco</button>
            <button type="button" class="btn primary" :disabled="!acts.length" @click="startStage">
              Modo apresentação
            </button>
          </div>
        </div>
        <p class="mobile-note">
          O mapa é otimizado para telas grandes — no celular, deslize horizontalmente ou use a lente
          Panorama.
        </p>

        <section v-if="lens === 'pan'" class="pan">
          <div v-if="graph.panorama" class="card reading">
            <span class="eyebrow-p">Leitura em 30 segundos</span>
            <p>{{ graph.panorama.reading }}</p>
          </div>
          <div v-if="graph.panorama?.apostas.length" class="pan-grid">
            <div
              v-for="aposta in graph.panorama.apostas"
              :key="aposta.towsField"
              class="card aposta"
              :class="`tone-${aposta.tone}`"
            >
              <span class="ak">{{ aposta.kindLabel }}</span>
              <h3>{{ aposta.title }}</h3>
              <p>{{ aposta.blurb }}</p>
              <span class="st">
                <span class="dot" :class="`st-${aposta.tone}`" />
                {{ aposta.meta }}
              </span>
            </div>
          </div>
          <div v-if="graph.panorama" class="pan-alert">
            <span class="pa-ic">!</span>
            <div>
              <b>{{ graph.panorama.alertTitle }}</b>
              <p>{{ graph.panorama.alertBody }}</p>
            </div>
          </div>
          <p class="lede">
            Esta é a leitura de Conselho. Para os resultados-chave e os projetos, mude a lente para
            <b>Gestão</b>; para auditar a origem de cada item, use <b>Linhagem</b>.
          </p>
        </section>

        <section v-else id="map-sec" class="map-sec">
          <div class="card map-card">
            <div class="map-wrap">
              <div
                ref="mapEl"
                class="map"
                :style="{ '--cols': Math.max(visibleColumns.length, 1) }"
              >
                <svg class="map-svg" aria-hidden="true">
                  <path
                    v-for="(path, index) in paths"
                    :key="index"
                    :d="path.d"
                    fill="none"
                    :stroke="path.stroke"
                    :stroke-width="path.width"
                    :opacity="path.opacity"
                    :stroke-dasharray="path.dash || undefined"
                  />
                </svg>
                <div v-for="column in visibleColumns" :key="column.roman" class="mcol">
                  <div class="mcol-h">
                    <span class="rn">{{ column.roman }}</span>
                    {{ column.title }}
                  </div>
                  <p v-if="!column.nodes.length" class="m-empty">{{ emptyHint(column.title, column.roman) }}</p>
                  <button
                    v-for="node in column.nodes"
                    :key="node.id"
                    type="button"
                    class="mnode"
                    :class="nodeClass(node)"
                    :data-nid="node.id"
                    @click="focusNode(node.id)"
                  >
                    <b>{{ node.title }}</b>
                    <span class="mv">{{ node.subtitle }}</span>
                    <span v-if="node.tone === 'ok' || node.tone === 'warn' || node.tone === 'risk'" class="sd dot" :class="`st-${node.tone}`" />
                  </button>
                </div>
              </div>
            </div>
            <div class="map-legend">
              <span>
                <i class="leg-line gold" />
                fio da linhagem
              </span>
              <span>
                <i class="leg-line risk" />
                fio crítico do ciclo
              </span>
              <span><span class="dot st-ok" /> no ritmo</span>
              <span><span class="dot st-warn" /> atenção</span>
              <span><span class="dot st-risk" /> em risco</span>
            </div>
          </div>
          <p class="lede">
            <b>Modo foco:</b> clique em qualquer nó para iluminar o fio — origem e consequência — e
            abrir o dossiê. Esc limpa.
          </p>
        </section>

        <section v-if="unlinkedSummary" class="card orphan-card">
          <p class="sec-title">Fora do mapa</p>
          <p class="panel-label">
            {{ unlinkedSummary.items }} item(ns) ·
            {{ unlinkedSummary.initiatives }} estratégia(s) ·
            {{ unlinkedSummary.objectives }} objective(s) ·
            {{ unlinkedSummary.krs }} KR(s) ·
            {{ unlinkedSummary.projects }} projeto(s) sem fio de origem.
          </p>
          <ul class="plain-list">
            <li v-for="item in map?.unlinked.swot_items ?? []" :key="item.id">
              <span class="tag muted">{{ QUADRANT_LABEL[item.quadrant] }}</span>
              {{ item.texto }}
            </li>
            <li v-for="objective in map?.unlinked.objectives ?? []" :key="objective.id">
              <span class="tag muted">Objective</span>
              {{ objective.titulo }}
            </li>
            <li v-for="project in map?.unlinked.projects ?? []" :key="project.id">
              <RouterLink :to="`/projetos/${project.id}`" class="link">{{ project.title }}</RouterLink>
              <span class="tag muted">
                {{ project.linked_to_swot ? 'sem item de origem' : 'sem SWOT de origem' }}
              </span>
            </li>
          </ul>
        </section>

        <div class="save-seal">
          <span>{{ graph.updatedLabel }}</span>
          <span>Lentes Conselho · Diretoria · Auditoria</span>
        </div>
      </template>
    </template>

    <Teleport to="body">
      <aside class="dock" :class="{ open: dockOpen && focusedNode }" aria-label="Dossiê do nó">
        <template v-if="focusedNode">
          <div class="dh">
            <div>
              <div class="dh-tags">
                <span class="tag-id">{{ focusedNode.labelId }}</span>
                <span class="tag" :class="`tag--${focusedNode.tone}`">{{ focusedNode.statusLabel }}</span>
              </div>
              <b>{{ focusedNode.title }}</b>
            </div>
            <button type="button" class="btn quiet" @click="clearFocus">Esc</button>
          </div>
          <div class="dblock">
            <span class="dk">O que este nó diz</span>
            <p>{{ focusedNode.body }}</p>
          </div>
          <div class="dblock">
            <span class="dk">Fio da linhagem</span>
            <span class="chain">{{ focusedNode.trail }}</span>
          </div>
          <div class="dblock">
            <span class="dk">Próximo movimento</span>
            <p>{{ focusedNode.next }}</p>
          </div>
          <div class="dblock ask">
            <span class="dk">A pergunta para a sala</span>
            <p>{{ focusedNode.ask }}</p>
          </div>

          <div v-if="focusedNode.kind === 'dim' && head?.maturity_response_id" class="dblock">
            <RouterLink :to="`/ai-maturity/${head.maturity_response_id}`" class="btn">Abrir diagnóstico</RouterLink>
          </div>
          <div v-else-if="(focusedNode.kind === 'quad' || focusedNode.kind === 'tows' || focusedNode.kind === 'watch') && head?.swot_id" class="dblock">
            <RouterLink :to="`/swot/${head.swot_id}`" class="btn">Abrir SWOT / TOWS</RouterLink>
          </div>
          <div v-else-if="focusedNode.kind === 'obj' && map?.okr_cycle" class="dblock">
            <RouterLink :to="`/okrs/${map.okr_cycle.id}`" class="btn">Abrir ciclo OKR</RouterLink>
          </div>
          <div v-else-if="focusedNode.kind === 'proj' && focusedNode.projectId" class="dblock">
            <RouterLink :to="`/projetos/${focusedNode.projectId}`" class="btn primary">Abrir canvas</RouterLink>
          </div>

          <div v-if="focusedNode.kind === 'tows' && dockInitiatives(focusedNode).length" class="dblock">
            <span class="dk">Estratégias desta aposta</span>
            <ul class="dock-list">
              <li v-for="initiative in dockInitiatives(focusedNode)" :key="initiative.id">
                <p class="dock-item-title">{{ initiative.acao || TOWS_LABEL[initiative.field] }}</p>
                <p v-if="initiative.dono || initiative.horizonte" class="dock-item-meta">
                  {{ [initiative.dono, initiative.horizonte].filter(Boolean).join(' · ') }}
                </p>
                <button type="button" class="btn-mini" @click="togglePanel(`t:${initiative.id}`)">
                  + projeto desta estratégia
                </button>
                <div v-if="linkPanel === `t:${initiative.id}`" class="link-panel">
                  <button
                    type="button"
                    class="btn-mini"
                    :disabled="busy"
                    @click="createProject(initiativePrefill(initiative, findInitiative(initiative.id)?.item ?? null))"
                  >Criar projeto pré-preenchido</button>
                  <p class="panel-label">ou vincular um projeto existente</p>
                  <p v-if="!projects.length" class="panel-empty">Nenhum projeto criado ainda.</p>
                  <ul v-else class="panel-list">
                    <li v-for="project in projects" :key="project.id">
                      <button
                        type="button"
                        class="panel-item"
                        :class="{ 'is-linked': isLinked(project, 'tows', initiative.id) }"
                        :disabled="busy"
                        @click="applyLink(project, 'tows', initiative.id, !isLinked(project, 'tows', initiative.id))"
                      >
                        <span>{{ isLinked(project, 'tows', initiative.id) ? '✓' : '+' }}</span>
                        {{ project.title }}
                      </button>
                    </li>
                  </ul>
                </div>
              </li>
            </ul>
          </div>

          <div v-if="focusedNode.kind === 'quad' && dockItems(focusedNode).length" class="dblock">
            <span class="dk">Itens deste quadrante</span>
            <ul class="dock-list">
              <li v-for="item in dockItems(focusedNode)" :key="item.id">
                <p class="dock-item-title">{{ item.texto }}</p>
                <button type="button" class="btn-mini" @click="togglePanel(`i:${item.id}`)">
                  + projeto deste item
                </button>
                <div v-if="linkPanel === `i:${item.id}`" class="link-panel">
                  <button
                    type="button"
                    class="btn-mini"
                    :disabled="busy"
                    @click="createProject(itemPrefill(item, findItemContext(item.id)?.dim, findItemContext(item.id)?.question))"
                  >Criar projeto pré-preenchido</button>
                  <p class="panel-label">ou vincular um projeto existente</p>
                  <ul class="panel-list">
                    <li v-for="project in projects" :key="project.id">
                      <button
                        type="button"
                        class="panel-item"
                        :class="{ 'is-linked': isLinked(project, 'item', item.id) }"
                        :disabled="busy"
                        @click="applyLink(project, 'item', item.id, !isLinked(project, 'item', item.id))"
                      >
                        <span>{{ isLinked(project, 'item', item.id) ? '✓' : '+' }}</span>
                        {{ project.title }}
                      </button>
                    </li>
                  </ul>
                </div>
              </li>
            </ul>
          </div>
        </template>
      </aside>
    </Teleport>

    <Teleport to="body">
      <div class="stage-bar" :class="{ on: staging && currentAct }">
        <div v-if="currentAct" class="st-t">{{ currentAct.kicker }} · <em>{{ currentAct.title }}</em></div>
        <p v-if="currentAct">{{ currentAct.caption }}</p>
        <div class="stage-ctl">
          <button type="button" class="sbtn" :disabled="actIndex === 0" @click="prevAct">← Anterior</button>
          <button type="button" class="sbtn" :disabled="actIndex >= acts.length - 1" @click="nextAct">
            Avançar →
          </button>
          <button type="button" class="sbtn" @click="stopStage">Encerrar</button>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.wrap {
  /* DS-01/DS-02: --navy, --mono e --dim-* removidos — já existem em main.css
     com o mesmo valor (eram duplicação pura, não conflito). */
  --navy: var(--k0);
  --gold-strong: var(--gold);
  --muted: var(--k3);
  --s: var(--success);
  --w: var(--warn);
  --o: #3d6fa8;
  --t: var(--low);
  --a: #b9822f;
  max-width: 1320px;
  margin: 0 auto;
  padding: 16px 16px 72px;
}
.wrap.staging {
  padding-bottom: 140px;
}

.page-header { margin-bottom: 16px; }
.eyebrow {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--gold);
  margin: 0 0 8px;
}
.page-title {
  font-family: var(--serif);
  font-size: clamp(22px, 5.5vw, 32px);
  font-weight: 400;
  color: var(--k0);
  margin: 0 0 10px;
  line-height: 1.2;
}
.page-lead {
  margin: 0;
  max-width: 62em;
  font-size: 14px;
  line-height: 1.6;
  color: var(--k3);
}

.card {
  background: var(--wh);
  border: 1px solid var(--bd);
  border-radius: var(--r-sm);
  padding: 16px;
  margin-bottom: 14px;
}
.state-card {
  background: var(--wh);
  border: 1px solid var(--bd);
  border-radius: var(--r-sm);
  padding: 24px 20px;
  margin-bottom: 14px;
  color: var(--k3);
}
.state-card.error {
  color: var(--low);
  background: var(--lowBg);
  border-color: rgba(182, 55, 55, 0.2);
}
.empty-title {
  font-family: var(--serif);
  font-size: 18px;
  color: var(--k0);
  margin: 0 0 6px;
}
.empty-text { margin: 0 0 14px; font-size: 14px; }

.source-card { border-top: 3px solid var(--gold); }
.source-main {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.field-label {
  display: block;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--k5);
  margin-bottom: 6px;
}
.select {
  width: 100%;
  min-height: 40px;
  padding: 8px 10px;
  border: 1px solid var(--k7);
  border-radius: var(--r-sm);
  background: var(--wh);
  color: var(--k0);
  font-family: inherit;
  font-size: 14px;
}
.select:focus { outline: none; border-color: var(--goldbd); }
.source-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}
.meta-item { font-size: 13px; color: var(--k3); }
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
  color: var(--gold2);
}
.source-optica {
  margin: 12px 0 0;
  font-size: 14px;
  line-height: 1.6;
  color: var(--k3);
}
.source-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 14px;
}
.notice { margin: 12px 0 0; font-size: 13px; color: var(--success); }
.notice.warn-note { color: var(--warn); }

.btn,
.btn-mini {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--r-sm);
  font-weight: 600;
  text-decoration: none;
  background: var(--wh);
  color: var(--k0);
  border: 1px solid var(--bd);
}
.btn {
  min-height: 40px;
  padding: 8px 14px;
  font-size: 13px;
}
.btn.primary {
  background: var(--k0);
  color: var(--wh);
  border-color: var(--k0);
}
.btn.quiet { min-height: 32px; font-size: 12px; }
.btn:hover:not(:disabled),
.btn-mini:hover:not(:disabled) {
  border-color: var(--goldbd);
  background: var(--k9);
}
.btn.primary:hover:not(:disabled) { opacity: 0.92; background: var(--k0); }
.btn:disabled,
.btn-mini:disabled { opacity: 0.6; cursor: wait; }
.btn-mini {
  min-height: 28px;
  padding: 4px 10px;
  font-size: 12px;
  margin-top: 6px;
}

.kpi-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
  margin-bottom: 14px;
}
.kpi-card {
  background: var(--wh);
  border: 1px solid var(--bd);
  border-radius: var(--r-sm);
  padding: 14px;
}
.kpi-label {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--k5);
  margin-bottom: 4px;
}
.kpi-value {
  font-family: var(--serif);
  font-size: 24px;
  color: var(--k0);
  line-height: 1.1;
}
.kpi-value.gold { color: var(--gold); }
.kpi-sub { font-size: 12px; color: var(--k5); margin-top: 2px; }

.toolrow {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin: 4px 0 8px;
}
.tool-actions { display: flex; gap: 8px; flex-wrap: wrap; }
.seg {
  display: inline-flex;
  flex-wrap: wrap;
  border: 1px solid var(--bd);
  border-radius: var(--r-md);
  overflow: hidden;
  background: var(--wh);
}
.seg button {
  border: none;
  background: transparent;
  color: var(--k3);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.02em;
  padding: 10px 14px;
}
.seg button + button { border-left: 1px solid var(--bd); }
.seg button.on {
  background: var(--k0);
  color: var(--wh);
}
.mobile-note {
  margin: 0 0 10px;
  font-size: 12px;
  color: var(--k5);
}
@media (min-width: 980px) {
  .mobile-note { display: none; }
}

.pan { margin-top: 6px; }
.reading { border-left: 3px solid var(--gold); }
.eyebrow-p {
  display: block;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--gold);
  margin-bottom: 6px;
}
.reading p {
  margin: 0;
  font-size: 14px;
  max-width: 780px;
  color: var(--k1);
}
.pan-grid {
  display: grid;
  gap: 12px;
  margin-bottom: 12px;
}
@media (min-width: 980px) {
  .pan-grid { grid-template-columns: repeat(3, 1fr); }
}
.aposta {
  padding: 16px 18px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  border-top: 3px solid var(--gold);
}
.aposta.tone-risk { border-top-color: var(--low); }
.aposta.tone-warn { border-top-color: var(--warn); }
.aposta.tone-ok { border-top-color: var(--success); }
.aposta .ak {
  font-family: var(--mono);
  font-size: 9px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  font-weight: 700;
  color: var(--gold);
}
.aposta h3 {
  font-family: var(--serif);
  font-weight: 600;
  font-size: 18px;
  color: var(--k0);
  line-height: 1.3;
  margin: 0;
}
.aposta p { margin: 0; font-size: 13px; color: var(--k3); }
.aposta .st {
  display: flex;
  gap: 8px;
  align-items: center;
  font-family: var(--mono);
  font-size: 10px;
  color: var(--k4);
}
.pan-alert {
  border-left: 3px solid var(--low);
  background: var(--lowBg);
  border-radius: var(--r-sm);
  padding: 14px 16px;
  display: flex;
  gap: 12px;
  margin-bottom: 12px;
  font-size: 13px;
  color: var(--k1);
}
.pan-alert .pa-ic {
  font-family: var(--mono);
  font-weight: 700;
  color: var(--low);
  flex: none;
}
.pan-alert p { margin: 4px 0 0; color: var(--k3); }
.lede {
  margin: 10px 0 0;
  font-size: 13px;
  color: var(--k4);
}

.map-sec { margin-top: 8px; }
.map-card { padding: 0; overflow: hidden; }
.map-wrap { overflow-x: auto; padding-bottom: 6px; }
.map {
  position: relative;
  display: grid;
  grid-template-columns: repeat(var(--cols, 5), minmax(168px, 1fr));
  gap: 26px;
  min-width: 920px;
  padding: 16px;
}
.map-svg {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}
.mcol {
  display: flex;
  flex-direction: column;
  gap: 10px;
  position: relative;
  z-index: 1;
}
.mcol-h {
  font-family: var(--mono);
  font-size: 9px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  font-weight: 700;
  color: var(--k5);
  margin-bottom: 2px;
  display: flex;
  gap: 8px;
  align-items: baseline;
}
.mcol-h .rn {
  font-family: var(--serif);
  font-size: 15px;
  color: var(--k0);
  letter-spacing: 0;
  text-transform: none;
}
.m-empty {
  margin: 0;
  font-size: 12px;
  color: var(--k5);
  padding: 12px 10px;
  border: 1px dashed var(--bd);
  border-radius: var(--r-sm);
}
.mnode {
  position: relative;
  z-index: 1;
  width: 100%;
  text-align: left;
  background: var(--wh);
  border: 1px solid var(--bd);
  border-left: 3px solid var(--k6);
  border-radius: var(--r-sm);
  padding: 12px 14px 12px 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  box-shadow: 0 1px 0 rgba(12, 35, 64, 0.03);
}
.mnode b {
  font-family: var(--serif);
  font-size: 14px;
  font-weight: 600;
  color: var(--k0);
  line-height: 1.3;
}
.mnode .mv {
  font-size: 12px;
  color: var(--k4);
}
.mnode .sd {
  position: absolute;
  top: 10px;
  right: 10px;
}
.mnode.mn-strategy { border-left-color: var(--dim-strategy); }
.mnode.mn-data { border-left-color: var(--dim-data); }
.mnode.mn-people { border-left-color: var(--dim-people); }
.mnode.mn-gov { border-left-color: var(--dim-gov); }
.mnode.mn-s { border-left-color: var(--s); }
.mnode.mn-w { border-left-color: var(--w); }
.mnode.mn-o { border-left-color: var(--o); }
.mnode.mn-t { border-left-color: var(--t); }
.mnode.mn-a { border-left-color: var(--a); }
.mnode:hover { border-color: var(--goldbd); background: var(--k9); }
.mnode.lit {
  border-color: var(--gold);
  box-shadow: 0 0 0 2px var(--golddim);
  background: #fffdf8;
}
.mnode.dim { opacity: 0.28; }
.only-lin { display: none; }
.lens-lin .only-lin { display: flex; }

.map-legend {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
  align-items: center;
  font-family: var(--mono);
  font-size: 10px;
  color: var(--k5);
  padding: 12px 16px;
  border-top: 1px solid var(--bd);
}
.map-legend span { display: inline-flex; gap: 6px; align-items: center; }
.leg-line {
  width: 22px;
  height: 1.5px;
  display: inline-block;
  background: var(--gold);
}
.leg-line.risk { background: var(--low); }

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
  background: var(--k6);
}
.dot.st-ok { background: var(--success); }
.dot.st-warn { background: var(--warn); }
.dot.st-risk { background: var(--low); }

.orphan-card .sec-title {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--k5);
  margin: 0 0 8px;
}
.panel-label {
  margin: 0 0 10px;
  font-size: 12px;
  color: var(--k4);
}
.plain-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 13px;
  color: var(--k3);
}
.plain-list li {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}
.tag {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: var(--r-pill);
  font-size: 11px;
  font-weight: 600;
  background: var(--k8);
  border: 1px solid var(--bd);
  color: var(--k4);
}
.tag.muted { color: var(--k4); }
.link { color: var(--k0); font-weight: 600; }
.link:hover { text-decoration: underline; }

.save-seal {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  margin-top: 8px;
  font-family: var(--mono);
  font-size: 10px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--k5);
}

@media (min-width: 760px) {
  .wrap { padding: 22px 20px 80px; }
  .kpi-grid { grid-template-columns: repeat(5, 1fr); }
  .source-main {
    flex-direction: row;
    align-items: flex-end;
    justify-content: space-between;
  }
  .source-field { min-width: 320px; }
}
</style>

<style>
.dock {
  position: fixed;
  top: var(--bar-h, 64px);
  right: 0;
  bottom: 0;
  width: min(400px, 100vw);
  transform: translateX(105%);
  transition: transform 0.35s ease;
  z-index: 350;
  overflow: auto;
  background: #fff;
  border-left: 1px solid var(--bd);
  box-shadow: -12px 0 40px rgba(12, 35, 64, 0.08);
  padding: 18px 18px 40px;
}
.dock.open { transform: none; }
.dock .dh {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
  margin-bottom: 16px;
}
.dock .dh b {
  font-family: var(--serif);
  font-size: 18px;
  color: var(--k0);
  line-height: 1.3;
}
.dh-tags { display: flex; gap: 8px; align-items: center; margin-bottom: 6px; flex-wrap: wrap; }
.tag-id {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 10px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  font-weight: 700;
  color: var(--gold);
}
.dock .tag { border-radius: var(--r-pill); padding: 2px 8px; font-size: 11px; font-weight: 600; }
.dock .tag--ok { background: var(--successBg); color: var(--success); border-color: transparent; }
.dock .tag--warn { background: var(--warnBg); color: var(--warn); border-color: transparent; }
.dock .tag--risk { background: var(--lowBg); color: var(--low); border-color: transparent; }
.dock .dblock { margin-bottom: 16px; }
.dock .dk {
  display: block;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--k5);
  margin-bottom: 6px;
}
.dock .dblock p,
.dock .chain {
  margin: 0;
  font-size: 14px;
  color: var(--k1);
  line-height: 1.55;
}
.dock .chain {
  display: block;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 12px;
  color: var(--k3);
}
.dock .dblock.ask {
  background: var(--beige-bg);
  border-radius: var(--r-sm);
  padding: 12px;
}
.dock-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.dock-item-title { margin: 0; font-size: 13px; color: var(--k0); }
.dock-item-meta { margin: 2px 0 0; font-size: 11px; color: var(--k5); }
.dock .link-panel {
  margin-top: 8px;
  padding: 10px;
  border: 1px dashed var(--goldbd);
  border-radius: var(--r-sm);
  background: var(--k9);
}
.dock .panel-label {
  margin: 10px 0 6px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--k5);
}
.dock .panel-empty { margin: 0; font-size: 13px; color: var(--k4); }
.dock .panel-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-height: 180px;
  overflow-y: auto;
}
.dock .panel-item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 6px 8px;
  border: 1px solid var(--bd);
  border-radius: var(--r-sm);
  background: var(--wh);
  font-size: 13px;
  text-align: left;
  color: var(--k0);
}
.dock .panel-item.is-linked { border-color: var(--success); color: var(--success); }

.stage-bar {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  background: var(--k0);
  color: var(--wh);
  padding: 14px 18px 18px;
  z-index: 360;
  display: none;
  box-shadow: 0 -10px 30px rgba(14, 27, 51, 0.3);
}
.stage-bar.on { display: block; }
.stage-bar .st-t {
  font-family: var(--serif);
  font-size: 16px;
  font-weight: 600;
}
.stage-bar .st-t em { color: var(--gold2); font-style: italic; }
.stage-bar p {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.72);
  max-width: 760px;
  margin-top: 4px;
}
.stage-ctl {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-top: 10px;
  flex-wrap: wrap;
}
.sbtn {
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: var(--r-sm);
  padding: 7px 12px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 10px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  font-weight: 600;
  color: var(--wh);
  background: transparent;
}
.sbtn:hover:not(:disabled) { border-color: var(--gold2); }
.sbtn:disabled { opacity: 0.4; cursor: default; }
</style>
