import { ref, computed, onMounted, onUnmounted, reactive } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  getCanvasProject,
  updateCanvasProject,
  importIntoCanvasProject,
  type CanvasProject,
  type CanvasProjectPayload,
  type CanvasListField,
  type CanvasQuadrant,
  type CanvasImportDocument,
} from '@/api/canvasProjects'
import {
  getSwotAnalysisById,
  listSwotAnalyses,
  type SwotAnalysis,
  type SwotAnalysisSummary,
  type SwotInitiative,
  type SwotListField,
} from '@/api/swotAnalysis'
import { SWOT_QUADRANT_LABEL, TOWS_GROUPS } from '@/lib/domain/swot'
import { getActiveOkrCycle, type OkrCycle } from '@/api/okrs'
import { useAutosave } from '@/composables/useAutosave'
import { EVAL_CELLS } from '@/lib/canvasModel'

export function useCanvasEditor() {
  const route = useRoute()
  const router = useRouter()
  const projectId = computed(() => String(route.params.id || ''))

  const loading = ref(true)
  const error = ref<string | null>(null)
  // AR-03: fila de gravação, debounce e guarda de saída vêm do composable
  // compartilhado — ver src/composables/useAutosave.ts.
  const autosave = useAutosave(async () => {
    const payload: CanvasProjectPayload = { ...form.value }
    const updated = await updateCanvasProject(projectId.value, payload)
    applyProject(updated)
  })
  const saveState = autosave.saveState
  const saveError = autosave.error
  const importState = ref<'idle' | 'importing' | 'ok' | 'error'>('idle')
  const importError = ref<string | null>(null)
  const importOkMsg = ref('')
  const fileInput = ref<HTMLInputElement | null>(null)
  const project = ref<CanvasProject | null>(null)
  const openHelp = ref<CanvasListField | null>(null)

  const drafts = reactive<Record<CanvasListField, string>>({
    contexto: '',
    dores: '',
    oportunidade: '',
    dados: '',
    valor: '',
    custo: '',
    riscos: '',
  })

  const form = ref({
    title: '',
    area_negocio: '',
    responsavel: '',
    data: '',
    objetivo_estrategico: '',
    contexto: [] as string[],
    dores: [] as string[],
    oportunidade: [] as string[],
    oportunidade_tipos: [] as string[],
    dados: [] as string[],
    valor: [] as string[],
    custo: [] as string[],
    riscos: [] as string[],
    score_valor: null as number | null,
    score_viabilidade: null as number | null,
    proximo_passo: '',
    justificativa_tows: '',
    swot_id: null as string | null,
    swot_item_ids: [] as string[],
    tows_ids: [] as string[],
    kr_ids: [] as string[],
  })

  const MAX_TOWS_LINKS = 20

  const swotList = ref<SwotAnalysisSummary[]>([])
  const swot = ref<SwotAnalysis | null>(null)
  const swotLoading = ref(false)
  const swotError = ref<string | null>(null)
  const originOpen = ref(false)

  /** Itens SWOT por id, para mostrar o que cada estratégia cruza. */
  const swotItemsById = computed(() => {
    const map = new Map<string, { texto: string; quadrant: SwotListField }>()
    const doc = swot.value
    if (!doc) return map
    for (const field of ['forcas', 'fraquezas', 'oportunidades', 'ameacas'] as SwotListField[]) {
      for (const item of doc[field] || []) {
        map.set(item.id, { texto: item.texto, quadrant: field })
      }
    }
    return map
  })

  const selectedInitiatives = computed(() => {
    const doc = swot.value
    if (!doc) return []
    const chosen = new Set(form.value.tows_ids)
    return TOWS_GROUPS.flatMap((group) =>
      (doc[group.field] || [])
        .filter((initiative) => initiative.id && chosen.has(initiative.id))
        .map((initiative) => ({ ...initiative, groupLabel: group.label }))
    )
  })

  const selectedItems = computed(() =>
    form.value.swot_item_ids
      .map((id) => ({ id, item: swotItemsById.value.get(id) }))
      .filter((entry): entry is { id: string; item: { texto: string; quadrant: SwotListField } } =>
        !!entry.item
      )
  )

  /** Rótulo das contrapartes de uma iniciativa (lado interno × lado externo). */
  function crossingLabel(initiative: SwotInitiative): string {
    const texts = [...(initiative.itens_internos || []), ...(initiative.itens_externos || [])]
      .map((id) => swotItemsById.value.get(id)?.texto)
      .filter((text): text is string => !!text)
    return texts.join(' × ')
  }

  function isTowsSelected(initiativeId?: string): boolean {
    return !!initiativeId && form.value.tows_ids.includes(initiativeId)
  }

  async function loadSwot(swotId: string) {
    swotLoading.value = true
    swotError.value = null
    try {
      swot.value = await getSwotAnalysisById(swotId)
    } catch (e) {
      swot.value = null
      swotError.value = e instanceof Error ? e.message : 'Falha ao carregar a SWOT.'
    } finally {
      swotLoading.value = false
    }
  }

  async function loadOrigin(p: CanvasProject) {
    try {
      const list = await listSwotAnalyses()
      swotList.value = list.items
    } catch (e) {
      swotError.value = e instanceof Error ? e.message : 'Falha ao listar as SWOTs.'
      return
    }
    const linked = p.swot_id && swotList.value.some((s) => s.id === p.swot_id) ? p.swot_id : null
    if (p.swot_id && !linked) {
      // SWOT de origem foi apagada: solta os vínculos para não travar o autosave
      form.value.swot_id = null
      form.value.swot_item_ids = []
      form.value.tows_ids = []
    }
    const preferred = linked || swotList.value[0]?.id || null
    if (preferred) await loadSwot(preferred)
  }

  async function onSelectSwot(event: Event) {
    const nextId = (event.target as HTMLSelectElement).value
    if (!nextId || nextId === swot.value?.id) return
    // Vínculos pertencem à SWOT anterior — trocar de SWOT limpa a seleção
    const had = form.value.tows_ids.length + form.value.swot_item_ids.length > 0
    form.value.tows_ids = []
    form.value.swot_item_ids = []
    form.value.swot_id = null
    await loadSwot(nextId)
    if (had) await persist()
  }

  async function toggleTows(initiativeId?: string) {
    if (!initiativeId || !swot.value) return
    const chosen = new Set(form.value.tows_ids)
    if (chosen.has(initiativeId)) {
      chosen.delete(initiativeId)
    } else {
      if (chosen.size >= MAX_TOWS_LINKS) {
        swotError.value = `Máximo de ${MAX_TOWS_LINKS} iniciativas por projeto.`
        return
      }
      chosen.add(initiativeId)
    }
    swotError.value = null
    form.value.tows_ids = [...chosen]
    const stillLinked = form.value.tows_ids.length + form.value.swot_item_ids.length > 0
    form.value.swot_id = stillLinked ? swot.value.id : null
    await persist()
  }

  async function removeSwotItemLink(itemId: string) {
    form.value.swot_item_ids = form.value.swot_item_ids.filter((id) => id !== itemId)
    const stillLinked = form.value.tows_ids.length + form.value.swot_item_ids.length > 0
    form.value.swot_id = stillLinked ? form.value.swot_id : null
    await persist()
  }

  /** Key Results (OKR) que este projeto endereça — do ciclo OKR ativo da organização. */
  const MAX_KR_LINKS = 20
  const okrCycle = ref<OkrCycle | null>(null)
  const okrLoading = ref(false)
  const okrError = ref<string | null>(null)
  const krSectionOpen = ref(false)

  const krsById = computed(() => {
    const map = new Map<string, { titulo: string; objetivoTitulo: string; progress_pct: number }>()
    for (const obj of okrCycle.value?.objectives || []) {
      for (const kr of obj.key_results) {
        map.set(kr.id, { titulo: kr.titulo, objetivoTitulo: obj.titulo, progress_pct: kr.progress_pct })
      }
    }
    return map
  })

  const selectedKeyResults = computed(() =>
    form.value.kr_ids
      .map((id) => ({ id, kr: krsById.value.get(id) }))
      .filter((entry): entry is { id: string; kr: { titulo: string; objetivoTitulo: string; progress_pct: number } } => !!entry.kr)
  )

  function isKrSelected(krId?: string): boolean {
    return !!krId && form.value.kr_ids.includes(krId)
  }

  async function toggleKr(krId?: string) {
    if (!krId) return
    const chosen = new Set(form.value.kr_ids)
    if (chosen.has(krId)) {
      chosen.delete(krId)
    } else {
      if (chosen.size >= MAX_KR_LINKS) {
        okrError.value = `Máximo de ${MAX_KR_LINKS} Key Results por projeto.`
        return
      }
      chosen.add(krId)
    }
    okrError.value = null
    form.value.kr_ids = [...chosen]
    await persist()
  }

  async function loadActiveOkrCycle() {
    okrLoading.value = true
    try {
      okrCycle.value = await getActiveOkrCycle()
    } catch {
      // Sem ciclo ativo (404) é estado normal — o template mostra um aviso apontando para /okrs
      okrCycle.value = null
    } finally {
      okrLoading.value = false
    }
  }

  const typeOptions = ref<string[]>([
    'Automação',
    'Classificação/Previsão',
    'Extração/Busca',
    'Geração',
    'Copiloto',
    'Agente autônomo',
  ])

  const quadrant = computed<CanvasQuadrant>(() => {
    const v = form.value.score_valor
    const f = form.value.score_viabilidade
    if (v == null || f == null) return null
    const highV = v >= 4
    const highF = f >= 4
    if (highV && highF) return 'ganho_rapido'
    if (highV && !highF) return 'aposta_estrategica'
    if (!highV && highF) return 'incremental'
    return 'evitar'
  })

  function asList(value: unknown): string[] {
    if (Array.isArray(value)) return value.map(String).map((s) => s.trim()).filter(Boolean)
    if (typeof value === 'string' && value.trim()) return [value.trim()]
    return []
  }

  function maskDate(raw: string): string {
    const digits = raw.replace(/\D/g, '').slice(0, 8)
    const parts: string[] = []
    if (digits.length > 0) parts.push(digits.slice(0, 2))
    if (digits.length > 2) parts.push(digits.slice(2, 4))
    if (digits.length > 4) parts.push(digits.slice(4, 8))
    return parts.join('/')
  }

  function onDateInput(ev: Event) {
    const input = ev.target as HTMLInputElement
    const masked = maskDate(input.value)
    form.value.data = masked
    input.value = masked
  }

  function applyProject(p: CanvasProject) {
    project.value = p
    form.value = {
      title: p.title || 'Novo projeto',
      area_negocio: p.area_negocio || '',
      responsavel: p.responsavel || '',
      data: maskDate(p.data || ''),
      objetivo_estrategico: p.objetivo_estrategico || '',
      contexto: asList(p.contexto),
      dores: asList(p.dores),
      oportunidade: asList(p.oportunidade),
      oportunidade_tipos: [...(p.oportunidade_tipos || [])],
      dados: asList(p.dados),
      valor: asList(p.valor),
      custo: asList(p.custo),
      riscos: asList(p.riscos),
      score_valor: p.score_valor,
      score_viabilidade: p.score_viabilidade,
      proximo_passo: p.proximo_passo || '',
      justificativa_tows: p.justificativa_tows || '',
      swot_id: p.swot_id ?? null,
      swot_item_ids: [...(p.swot_item_ids || [])],
      tows_ids: [...(p.tows_ids || [])],
      kr_ids: [...(p.kr_ids || [])],
    }
    if (p.opportunity_type_options?.length) {
      typeOptions.value = p.opportunity_type_options
    }
  }

  function addItem(field: CanvasListField) {
    const text = drafts[field].trim()
    if (!text) return
    if (form.value[field].length >= 40) return
    form.value[field] = [...form.value[field], text]
    drafts[field] = ''
    void persist()
  }

  function removeItem(field: CanvasListField, index: number) {
    form.value[field] = form.value[field].filter((_, i) => i !== index)
    void persist()
  }

  function autosizeItem(el: HTMLTextAreaElement | null | Event) {
    const ta =
      el instanceof Event ? (el.target as HTMLTextAreaElement | null) : el
    if (!ta) return
    ta.style.height = 'auto'
    ta.style.height = `${ta.scrollHeight}px`
  }

  function onItemBlur(field: CanvasListField, index: number, ev: Event) {
    const input = ev.target as HTMLTextAreaElement
    const next = input.value.trim()
    const list = [...form.value[field]]
    if (!next) {
      list.splice(index, 1)
    } else {
      list[index] = next
    }
    form.value[field] = list
    void persist()
  }

  function onDraftKeydown(field: CanvasListField, ev: KeyboardEvent) {
    if (ev.key === 'Enter') {
      ev.preventDefault()
      addItem(field)
    }
  }

  function toggleHelp(field: CanvasListField, ev?: Event) {
    ev?.stopPropagation()
    openHelp.value = openHelp.value === field ? null : field
  }

  function onDocPointerDown(ev: Event) {
    const target = ev.target as HTMLElement | null
    if (!target) return
    if (target.closest('.cell-help') || target.closest('.cell-help-btn')) return
    openHelp.value = null
  }

  function toggleType(t: string) {
    const set = new Set(form.value.oportunidade_tipos)
    if (set.has(t)) set.delete(t)
    else set.add(t)
    form.value.oportunidade_tipos = [...set]
    void persist()
  }

  function setScore(field: 'score_valor' | 'score_viabilidade', n: number) {
    form.value[field] = form.value[field] === n ? null : n
    void persist()
  }

  function openImportPicker() {
    importError.value = null
    importState.value = 'idle'
    importOkMsg.value = ''
    fileInput.value?.click()
  }

  async function onImportFile(ev: Event) {
    const input = ev.target as HTMLInputElement
    const file = input.files?.[0]
    input.value = ''
    if (!file || !projectId.value) return

    importState.value = 'importing'
    importError.value = null
    importOkMsg.value = ''
    try {
      const text = await file.text()
      let parsed: unknown
      try {
        parsed = JSON.parse(text)
      } catch {
        throw new Error('Arquivo inválido. Envie um JSON válido.')
      }
      if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
        throw new Error('JSON inválido. Esperado um objeto aegis.canvas-oportunidades.')
      }
      const doc = parsed as CanvasImportDocument
      if (doc.schema != null && doc.schema !== 'aegis.canvas-oportunidades') {
        throw new Error('Formato inválido. Esperado schema=aegis.canvas-oportunidades.')
      }
      if (doc.versao != null && String(doc.versao) !== '1') {
        throw new Error('Versão não suportada. Use versao "1".')
      }
      const result = await importIntoCanvasProject(projectId.value, doc)
      applyProject(result.item)
      importState.value = 'ok'
      saveState.value = 'saved'
      importOkMsg.value =
        result.available > 1
          ? `Canvas preenchido com a 1ª oportunidade (${result.available} no arquivo). Use Importar JSON na lista para criar todas.`
          : 'JSON importado com sucesso.'
      window.setTimeout(() => {
        if (importState.value === 'ok') importState.value = 'idle'
        if (saveState.value === 'saved') saveState.value = 'idle'
      }, 4000)
    } catch (e) {
      importState.value = 'error'
      importError.value = e instanceof Error ? e.message : 'Falha na importação.'
    }
  }

  function persist(): Promise<void> {
    if (!projectId.value) return Promise.resolve()
    return autosave.save()
  }

  onMounted(async () => {
    document.addEventListener('pointerdown', onDocPointerDown)
    try {
      const p = await getCanvasProject(projectId.value)
      applyProject(p)
      if ((p.tows_ids || []).length || (p.swot_item_ids || []).length) originOpen.value = true
      void loadOrigin(p)
      if ((p.kr_ids || []).length) krSectionOpen.value = true
      void loadActiveOkrCycle()
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Erro ao carregar projeto.'
      if (String(error.value).includes('nao encontrado') || String(error.value).includes('não encontrado')) {
        setTimeout(() => router.push('/projetos'), 1500)
      }
    } finally {
      loading.value = false
    }
  })

  onUnmounted(() => {
    document.removeEventListener('pointerdown', onDocPointerDown)
  })
  return {
    projectId, loading, error, saveState, saveError, importState, importError, importOkMsg,
    fileInput, project, openHelp, drafts, form, swotList, swot, swotLoading, swotError,
    originOpen, okrCycle, okrLoading, okrError, krSectionOpen, typeOptions,
    swotItemsById, selectedInitiatives, selectedItems, selectedKeyResults, krsById, quadrant,
    EVAL_CELLS, TOWS_GROUPS, SWOT_QUADRANT_LABEL,
    crossingLabel, isTowsSelected, isKrSelected, toggleTows, toggleKr, removeSwotItemLink,
    onSelectSwot, loadSwot, onDateInput, addItem, removeItem, autosizeItem, onItemBlur,
    onDraftKeydown, toggleHelp, toggleType, setScore, openImportPicker, onImportFile, persist,
  }
}

export type CanvasEditor = ReturnType<typeof useCanvasEditor>
