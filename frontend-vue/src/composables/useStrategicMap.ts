import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
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
import { createSwotFromMaturity } from '@/api/swotAnalysis'
import { SWOT_QUADRANT_LABEL, TOWS_LABEL } from '@/lib/domain/swot'
import {
  buildStrategicMapGraph,
  lineageOf,
  visibleEdges,
  type MapEdge,
  type MapLens,
  type MapNode,
  type StrategicMapGraph,
} from '@/lib/strategicMapGraph'
import { clip, formatDate } from '@/lib/mapHelpers'

export function useStrategicMap() {
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
      return { stroke: cssVar('--gold', '#c6a15b'), width: 1.3, opacity: 0.55, dash: '4 4' }
    }
    if (kind === 'sec') {
      return { stroke: cssVar('--gold2', '#b8975a'), width: 1.1, opacity: 0.35, dash: '' }
    }
    return { stroke: cssVar('--gold', '#c6a15b'), width: 1.4, opacity: 0.55, dash: '' }
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
      title: clip(item.texto || `${SWOT_QUADRANT_LABEL[item.quadrant]}`, 200),
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
  return {
    loading, error, notice, busy, map, projects, lens, focusId, dockOpen, staging, actIndex,
    linkPanel, mapEl, paths, graph, stats, head, focusSet, focusedNode, visibleColumns, acts,
    currentAct, sourceOptions, selectedSource, unlinkedSummary, SWOT_QUADRANT_LABEL, TOWS_LABEL,
    setLens, focusNode, clearFocus, startStage, stopStage, prevAct, nextAct, nodeClass,
    onSelectSource, generateSwot, applyLink, createProject, isLinked, togglePanel,
    dockInitiatives, dockItems, emptyHint, findItemContext, findInitiative,
    itemPrefill, initiativePrefill,
  }
}

export type StrategicMapEditor = ReturnType<typeof useStrategicMap>
