import { ref, reactive, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  getSwotAnalysis,
  getSwotAnalysisById,
  updateSwotAnalysis,
  importSwotAnalysis,
  SWOT_PILLARS,
  MATURITY_DIMENSIONS,
  emptyPilares,
  type SwotAnalysis,
  type SwotAnalysisPayload,
  type SwotItem,
  type SwotInitiative,
  type SwotListField,
  type SwotTowsField,
  type SwotVereditoTipo,
  type SwotPilarSlot,
  type SwotPilaresPorQuadrante,
  type SwotImportDocument,
  type SwotWatchlistItem,
} from '@/api/swotAnalysis'
import { useAutosave } from '@/composables/useAutosave'
import {
  QUADRANT_HINTS,
  SWOT_QUADRANTS as QUADRANTS,
  SWOT_TOWS_SECTIONS as TOWS,
  SWOT_VEREDITO_OPTIONS as VEREDITO_OPTIONS,
  SWOT_DEFAULT_SLOTS as DEFAULT_SLOTS,
  buildSwotCatalog,
  defaultNomeFor,
  normalizePilares,
  resolvePillar,
  emptySwotItem as emptyItem,
  emptySwotInitiative as emptyInitiative,
  normalizeSwotItem as normalizeItem,
  slugifyPillar,
  pillarLabel,
  type QuadrantPillar,
} from '@/lib/swotModel'

export type SwotFormState = {
  optica: string
  pilares: SwotPilaresPorQuadrante
  forcas: SwotItem[]
  fraquezas: SwotItem[]
  oportunidades: SwotItem[]
  ameacas: SwotItem[]
  tows_fo: SwotInitiative[]
  tows_fa: SwotInitiative[]
  tows_fxo: SwotInitiative[]
  tows_fxa: SwotInitiative[]
  veredito_tipo: SwotVereditoTipo
  veredito_titulo: string
  veredito_texto: string
}

export function useSwotEditor() {
  const route = useRoute()
  const router = useRouter()
  const loading = ref(true)
  const error = ref<string | null>(null)
  let pendingRebuildTows = false

  const importState = ref<'idle' | 'importing' | 'ok' | 'error'>('idle')
  const importError = ref<string | null>(null)
  const showMethod = ref(true)
  const showCatalog = ref(false)
  const openHelp = ref<SwotListField | null>(null)
  const addingPillarFor = ref<SwotListField | null>(null)
  const customPillarDraft = ref('')
  const fileInput = ref<HTMLInputElement | null>(null)
  const currentSwotId = ref<string | null>(null)
  const maturityResponseId = ref<string | null>(null)
  const watchlist = ref<SwotWatchlistItem[]>([])

  const form = ref<SwotFormState>({
    optica: '',
    pilares: emptyPilares(),
    forcas: [],
    fraquezas: [],
    oportunidades: [],
    ameacas: [],
    tows_fo: [],
    tows_fa: [],
    tows_fxo: [],
    tows_fxa: [],
    veredito_tipo: '',
    veredito_titulo: '',
    veredito_texto: '',
  })

  type DraftKey = `${SwotListField}:${string}`
  const drafts = reactive<Record<string, string>>({})

  function draftKey(field: SwotListField, pilar: string): DraftKey {
    return `${field}:${pilar || '_none'}`
  }

  function applyDoc(doc: SwotAnalysis) {
    currentSwotId.value = doc.id
    maturityResponseId.value = doc.maturity_response_id || null
    watchlist.value = Array.isArray(doc.watchlist)
      ? doc.watchlist.map((w) => ({
          id: w.id || '',
          texto: w.texto || '',
          pilar: w.pilar || '',
          dimensao: w.dimensao || '',
          nota: w.nota ?? null,
          evidencia: w.evidencia || '',
          swotCategory: w.swotCategory ?? null,
        }))
      : []
    form.value = {
      optica: doc.optica || '',
      pilares: normalizePilares(doc.pilares),
      forcas: (doc.forcas || []).map(normalizeItem),
      fraquezas: (doc.fraquezas || []).map(normalizeItem),
      oportunidades: (doc.oportunidades || []).map(normalizeItem),
      ameacas: (doc.ameacas || []).map(normalizeItem),
      tows_fo: (doc.tows_fo || []).map((i) => ({ ...emptyInitiative(), ...i })),
      tows_fa: (doc.tows_fa || []).map((i) => ({ ...emptyInitiative(), ...i })),
      tows_fxo: (doc.tows_fxo || []).map((i) => ({ ...emptyInitiative(), ...i })),
      tows_fxa: (doc.tows_fxa || []).map((i) => ({ ...emptyInitiative(), ...i })),
      veredito_tipo: (doc.veredito_tipo || '') as SwotVereditoTipo,
      veredito_titulo: doc.veredito_titulo || '',
      veredito_texto: doc.veredito_texto || '',
    }
    const routeId = typeof route.params.id === 'string' ? route.params.id : ''
    if (doc.id && routeId !== doc.id) {
      void router.replace({ name: 'SwotAnalysis', params: { id: doc.id } })
    }
  }

  const autosave = useAutosave(async () => {
    const rebuildTows = pendingRebuildTows
    pendingRebuildTows = false
    const payload: SwotAnalysisPayload = { ...form.value }
    const updated = await updateSwotAnalysis(payload, currentSwotId.value, { rebuildTows })
    applyDoc(updated)
  })

  const saveState = autosave.saveState
  const saveError = autosave.error

  const pillarsByMaturityDimension = computed(() =>
    MATURITY_DIMENSIONS.map((dim) => ({
      ...dim,
      pillars: SWOT_PILLARS.filter((p) => p.maturityDimension === dim.id),
    }))
  )

  const CATALOG = buildSwotCatalog()
  const watchlistGroups = computed(() => {
    const groups: { dimensao: string; items: SwotWatchlistItem[] }[] = []
    const index = new Map<string, number>()
    for (const item of watchlist.value) {
      const dim = (item.dimensao || '').trim() || 'Outros'
      let i = index.get(dim)
      if (i === undefined) {
        i = groups.length
        index.set(dim, i)
        groups.push({ dimensao: dim, items: [] })
      }
      groups[i]!.items.push(item)
    }
    return groups
  })

  const hasWatchlist = computed(() => watchlist.value.length > 0)
  const towsStep = computed(() => (hasWatchlist.value ? 4 : 3))
  const verdictStep = computed(() => (hasWatchlist.value ? 5 : 4))

  async function loadSwot() {
    loading.value = true
    error.value = null
    try {
      const routeId = typeof route.params.id === 'string' ? route.params.id : ''
      const doc = routeId ? await getSwotAnalysisById(routeId) : await getSwotAnalysis()
      applyDoc(doc)
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Erro ao carregar SWOT.'
    } finally {
      loading.value = false
    }
  }

  function saveSwot(opts?: { rebuildTows?: boolean }) {
    if (opts?.rebuildTows) pendingRebuildTows = true
    void autosave.save()
  }

  function getDraft(field: SwotListField, pilar: string): string {
    return drafts[draftKey(field, pilar)] || ''
  }

  function setDraft(field: SwotListField, pilar: string, value: string) {
    drafts[draftKey(field, pilar)] = value
  }

  function itemsForPilar(field: SwotListField, pilar: string) {
    return form.value[field]
      .map((item, index) => ({ item, index }))
      .filter(({ item }) => (item.pilar || '') === pilar)
  }

  function slotsForQuadrant(field: SwotListField): SwotPilarSlot[] {
    const saved = form.value.pilares[field] || []
    if (saved.length) return saved
    return DEFAULT_SLOTS[field].map((s) => ({ ...s }))
  }

  function knownPillarIds(field: SwotListField): Set<string> {
    return new Set(pillarsForQuadrant(field).map((p) => p.id))
  }

  function pillarsForQuadrant(field: SwotListField): QuadrantPillar[] {
    const seen = new Set<string>()
    const slots: SwotPilarSlot[] = []
    const push = (id: string, nome = '') => {
      const key = (id || '').trim().toLowerCase()
      if (!key || seen.has(key)) return
      seen.add(key)
      slots.push({ id: key, nome: (nome || '').trim() })
    }
    for (const s of slotsForQuadrant(field)) push(s.id, s.nome)
    for (const item of form.value[field]) {
      if (item.pilar) push(item.pilar)
    }
    return slots.map((s) => resolvePillar(field, s.id, s.nome))
  }

  function ensurePersistedSlots(field: SwotListField): SwotPilarSlot[] {
    const current = form.value.pilares[field] || []
    if (current.length) return current.map((s) => ({ ...s }))
    return DEFAULT_SLOTS[field].map((s) => ({ ...s }))
  }

  function unassignedItems(field: SwotListField) {
    const known = knownPillarIds(field)
    return form.value[field]
      .map((item, index) => ({ item, index }))
      .filter(({ item }) => !item.pilar || !known.has(item.pilar))
  }

  function availablePillarsToAdd(field: SwotListField): QuadrantPillar[] {
    const used = knownPillarIds(field)
    return SWOT_PILLARS.filter((p) => !used.has(p.id)).map((p) => resolvePillar(field, p.id))
  }

  function openAddPillar(field: SwotListField) {
    addingPillarFor.value = addingPillarFor.value === field ? null : field
    customPillarDraft.value = ''
  }

  function addCanonicalPillar(field: SwotListField, pilarId: string) {
    if (!pilarId || knownPillarIds(field).has(pilarId)) return
    const next = ensurePersistedSlots(field)
    next.push({ id: pilarId, nome: defaultNomeFor(field, pilarId) })
    form.value.pilares = { ...form.value.pilares, [field]: next }
    addingPillarFor.value = null
    customPillarDraft.value = ''
    void saveSwot()
  }

  function addCustomPillar(field: SwotListField) {
    const label = customPillarDraft.value.trim()
    const slug = slugifyPillar(label)
    if (!slug || knownPillarIds(field).has(slug)) return
    if (!/^[a-z][a-z0-9_-]{0,39}$/.test(slug)) return
    const next = ensurePersistedSlots(field)
    next.push({ id: slug, nome: label })
    form.value.pilares = { ...form.value.pilares, [field]: next }
    addingPillarFor.value = null
    customPillarDraft.value = ''
    void saveSwot()
  }

  function addItem(field: SwotListField, pilar: string) {
    const key = draftKey(field, pilar)
    const text = (drafts[key] || '').trim()
    if (!text) return
    if (form.value[field].length >= 40) return
    form.value[field] = [...form.value[field], { ...emptyItem(pilar), texto: text }]
    drafts[key] = ''
    void saveSwot({ rebuildTows: true })
  }

  function removeItem(field: SwotListField, index: number) {
    form.value[field] = form.value[field].filter((_, i) => i !== index)
    void saveSwot({ rebuildTows: true })
  }

  function toggleItemTows(field: SwotListField, index: number) {
    const list = form.value[field].map((item) => ({ ...item }))
    const current = list[index]
    if (!current) return
    list[index] = { ...current, tows: !current.tows }
    form.value[field] = list
    void saveSwot({ rebuildTows: true })
  }

  function onItemBlur(field: SwotListField, index: number, ev: Event) {
    const input = ev.target as HTMLInputElement
    const next = input.value.trim()
    const list = form.value[field].map((item) => ({ ...item }))
    if (!next) {
      list.splice(index, 1)
      form.value[field] = list
      void saveSwot({ rebuildTows: true })
      return
    }
    const current = list[index]
    if (!current) return
    list[index] = { ...current, texto: next }
    form.value[field] = list
    void saveSwot()
  }

  function onDraftKeydown(field: SwotListField, pilar: string, ev: KeyboardEvent) {
    if (ev.key === 'Enter') {
      ev.preventDefault()
      addItem(field, pilar)
    }
  }

  function addInitiative(field: SwotTowsField) {
    if (form.value[field].length >= 20) return
    form.value[field] = [...form.value[field], emptyInitiative()]
  }

  function removeInitiative(field: SwotTowsField, index: number) {
    form.value[field] = form.value[field].filter((_, i) => i !== index)
    void saveSwot()
  }

  function onInitiativeBlur(field: SwotTowsField, index: number, key: keyof SwotInitiative, ev: Event) {
    const input = ev.target as HTMLInputElement
    const list = form.value[field].map((row) => ({ ...row }))
    const current = list[index]
    if (!current) return
    const row = { ...current, [key]: input.value }
    if (!(row.acao || '').trim() && !(row.dono || '').trim() && !(row.horizonte || '').trim()) {
      list.splice(index, 1)
    } else {
      list[index] = row
    }
    form.value[field] = list
    void saveSwot()
  }

  function setVereditoTipo(tipo: SwotVereditoTipo) {
    form.value.veredito_tipo = tipo
    void saveSwot()
  }

  function toggleHelp(field: SwotListField, ev?: Event) {
    ev?.stopPropagation()
    openHelp.value = openHelp.value === field ? null : field
  }

  function onDocPointerDown(ev: PointerEvent) {
    if (!openHelp.value) return
    const target = ev.target as HTMLElement | null
    if (target?.closest('.q-help') || target?.closest('.q-help-btn')) return
    openHelp.value = null
  }

  function openImportPicker() {
    importError.value = null
    importState.value = 'idle'
    fileInput.value?.click()
  }

  async function onImportFile(ev: Event) {
    const input = ev.target as HTMLInputElement
    const file = input.files?.[0]
    input.value = ''
    if (!file) return

    importState.value = 'importing'
    importError.value = null
    try {
      const text = await file.text()
      let parsed: unknown
      try {
        parsed = JSON.parse(text)
      } catch {
        throw new Error('Arquivo JSON inválido.')
      }
      if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
        throw new Error('O JSON deve ser um objeto aegis.swot-ia.')
      }
      const doc = parsed as SwotImportDocument
      if (doc.format && doc.format !== 'aegis.swot-ia') {
        throw new Error('Formato inválido. Esperado format=aegis.swot-ia.')
      }
      if (doc.version != null && doc.version !== 1 && doc.version !== 2 && doc.version !== 3) {
        throw new Error('Versão não suportada. Use version 1, 2 ou 3.')
      }
      const updated = await importSwotAnalysis(doc)
      applyDoc(updated)
      importState.value = 'ok'
      saveState.value = 'saved'
      window.setTimeout(() => {
        if (importState.value === 'ok') importState.value = 'idle'
        if (saveState.value === 'saved') saveState.value = 'idle'
      }, 2000)
    } catch (e) {
      importState.value = 'error'
      importError.value = e instanceof Error ? e.message : 'Falha na importação.'
    }
  }

  onMounted(() => {
    document.addEventListener('pointerdown', onDocPointerDown)
    void loadSwot()
  })

  watch(
    () => route.params.id,
    (next, prev) => {
      if (next === prev) return
      if (typeof next === 'string' && next === currentSwotId.value) return
      void loadSwot()
    }
  )

  onUnmounted(() => {
    document.removeEventListener('pointerdown', onDocPointerDown)
  })

  return {
    loading,
    error,
    form,
    saveState,
    saveError,
    importState,
    importError,
    showMethod,
    showCatalog,
    openHelp,
    addingPillarFor,
    customPillarDraft,
    fileInput,
    maturityResponseId,
    pillarsByMaturityDimension,
    CATALOG,
    QUADRANT_HINTS,
    QUADRANTS,
    TOWS,
    VEREDITO_OPTIONS,
    watchlistGroups,
    hasWatchlist,
    towsStep,
    verdictStep,
    saveSwot,
    getDraft,
    setDraft,
    itemsForPilar,
    pillarsForQuadrant,
    unassignedItems,
    availablePillarsToAdd,
    openAddPillar,
    addCanonicalPillar,
    addCustomPillar,
    addItem,
    removeItem,
    toggleItemTows,
    onItemBlur,
    onDraftKeydown,
    addInitiative,
    removeInitiative,
    onInitiativeBlur,
    setVereditoTipo,
    toggleHelp,
    openImportPicker,
    onImportFile,
    pillarLabel,
  }
}

export type SwotEditor = ReturnType<typeof useSwotEditor>
