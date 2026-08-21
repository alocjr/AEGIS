<script setup lang="ts">
import { ref, onMounted, onUnmounted, reactive, computed, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import {
  getSwotAnalysis,
  getSwotAnalysisById,
  updateSwotAnalysis,
  importSwotAnalysis,
  SWOT_PILLARS,
  SWOT_QUADRANT_DEFAULT_PILLARS,
  MATURITY_DIMENSIONS,
  emptyPilares,
  type SwotAnalysis,
  type SwotAnalysisPayload,
  type SwotInitiative,
  type SwotItem,
  type SwotListField,
  type SwotTowsField,
  type SwotVereditoTipo,
  type SwotPilarId,
  type SwotPilarSlot,
  type SwotPilaresPorQuadrante,
  type SwotImportDocument,
  type SwotWatchlistItem,
} from '@/api/swotAnalysis'
import { useAutosave } from '@/composables/useAutosave'

const route = useRoute()
const router = useRouter()
const loading = ref(true)
const error = ref<string | null>(null)
let pendingRebuildTows = false
// AR-03: fila de gravação, debounce e guarda de saída vêm do composable
// compartilhado — ver src/composables/useAutosave.ts. Nesta tela, cada
// alteração salva na hora (sem debounce), como já era o caso; o composable
// só corrige a fila de concorrência e acrescenta a guarda de saída.
const autosave = useAutosave(async () => {
  const rebuildTows = pendingRebuildTows
  pendingRebuildTows = false
  const payload: SwotAnalysisPayload = { ...form.value }
  const updated = await updateSwotAnalysis(payload, currentSwotId.value, { rebuildTows })
  applyDoc(updated)
})
const saveState = autosave.saveState
const saveError = autosave.error
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
/** Pontos de Atenção (nota 3) — só leitura; fora do form de autosave. */
const watchlist = ref<SwotWatchlistItem[]>([])

const PILLARS = SWOT_PILLARS
const PILLAR_BY_ID = Object.fromEntries(PILLARS.map((p) => [p.id, p])) as Record<
  Exclude<SwotPilarId, ''>,
  (typeof PILLARS)[number]
>

type QuadrantHint = {
  letter: string
  name: string
  locus: string
  neg: boolean
  groups: { label: string; text: string; pilar: Exclude<SwotPilarId, ''> }[]
}

type QuadrantPillar = { id: string; name: string; q: string }

/** Repertório de partida por quadrante — estímulo, não checklist. Rótulos alinhados ao Modelo de Maturidade. */
const QUADRANT_HINTS: Record<SwotListField, QuadrantHint> = {
  forcas: {
    letter: 'F',
    name: 'Forças',
    locus: 'interno · positivo',
    neg: false,
    groups: [
      {
        label: 'Estratégia e Visão',
        pilar: 'portfolio',
        text: 'visão clara de IA ligada a OKRs/receita; roadmap aprovado; framework de impacto × viabilidade; casos com ROI.',
      },
      {
        label: 'Dados e Infraestrutura',
        pilar: 'dados',
        text: 'base proprietária integrada e de qualidade; nuvem/APIs maduras para consumir IA com segurança.',
      },
      {
        label: 'Pessoas e Cultura',
        pilar: 'talento',
        text: 'time de dados/IA constituído; lideranças com letramento; cultura de experimentação e patrocínio do topo.',
      },
      {
        label: 'Governança e Risco',
        pilar: 'governanca',
        text: 'política de IA, conformidade, auditoria de viés/alucinação e validação humana no crítico.',
      },
    ],
  },
  oportunidades: {
    letter: 'O',
    name: 'Oportunidades',
    locus: 'externo · positivo',
    neg: false,
    groups: [
      {
        label: 'Tecnologia e ecossistema',
        pilar: 'ecossistema',
        text: 'barateamento e maturação dos modelos; IA generativa, RAG e agêntica; ferramentas abertas e parceiros.',
      },
      {
        label: 'Mercado e clientes',
        pilar: 'portfolio',
        text: 'demanda por experiências personalizadas; novos modelos de receita; segmentos mal atendidos; concorrentes lentos.',
      },
      {
        label: 'Ambiente regulatório',
        pilar: 'governanca',
        text: 'clareza regulatória ou janelas setoriais que favorecem quem já tem conformidade e isolamento de dados.',
      },
      {
        label: 'Talento e incentivos',
        pilar: 'talento',
        text: 'oferta crescente de talento e ecossistemas locais; editais e incentivos para acelerar a transformação.',
      },
    ],
  },
  fraquezas: {
    letter: 'f',
    name: 'Fraquezas',
    locus: 'interno · negativo',
    neg: true,
    groups: [
      {
        label: 'Estratégia e Visão',
        pilar: 'portfolio',
        text: 'só pilotos sem escala; sem dono, critério de priorização, roadmap ou business case.',
      },
      {
        label: 'Dados e Infraestrutura',
        pilar: 'dados',
        text: 'silos, baixa qualidade, legado e dívida técnica; sem propriedade clara nem rotulagem.',
      },
      {
        label: 'Pessoas e Cultura',
        pilar: 'talento',
        text: 'falta de especialistas; letramento desigual; resistência ou aversão a risco.',
      },
      {
        label: 'Governança e Risco',
        pilar: 'governanca',
        text: 'sem governança de IA, auditoria de alucinações/viés ou isolamento de dados sensíveis.',
      },
    ],
  },
  ameacas: {
    letter: 'A',
    name: 'Ameaças',
    locus: 'externo · negativo',
    neg: true,
    groups: [
      {
        label: 'Concorrência',
        pilar: 'portfolio',
        text: 'players maduros e marketplaces com IA avançada; risco de disrupção do core.',
      },
      {
        label: 'Regulação e risco',
        pilar: 'governanca',
        text: 'LGPD, marco de IA e regras setoriais elevando o custo de conformidade e o risco reputacional.',
      },
      {
        label: 'Fornecedores e modelos',
        pilar: 'ecossistema',
        text: 'lock-in, mudança de preço ou descontinuação; alucinação, viés e dependência de um único provedor.',
      },
      {
        label: 'Talento e ritmo',
        pilar: 'talento',
        text: 'guerra por talento; velocidade da mudança e obsolescência precoce das ferramentas.',
      },
    ],
  },
}

const pillarsByMaturityDimension = computed(() =>
  MATURITY_DIMENSIONS.map((dim) => ({
    ...dim,
    pillars: PILLARS.filter((p) => p.maturityDimension === dim.id),
  }))
)

const CATALOG = (['forcas', 'oportunidades', 'fraquezas', 'ameacas'] as SwotListField[]).map(
  (field) => QUADRANT_HINTS[field]
)

/** Defaults do banco de itens por quadrante. */
const DEFAULT_SLOTS = SWOT_QUADRANT_DEFAULT_PILLARS

function defaultNomeFor(field: SwotListField, pilarId: string): string {
  const fromDefault = DEFAULT_SLOTS[field].find((s) => s.id === pilarId)
  if (fromDefault?.nome) return fromDefault.nome
  return PILLAR_BY_ID[pilarId as Exclude<SwotPilarId, ''>]?.name || pilarId
}

function normalizePilares(raw?: SwotPilaresPorQuadrante | null): SwotPilaresPorQuadrante {
  const base = emptyPilares()
  if (!raw) return base
  for (const field of ['forcas', 'fraquezas', 'oportunidades', 'ameacas'] as SwotListField[]) {
    const list = raw[field]
    if (!Array.isArray(list)) continue
    const seen = new Set<string>()
    base[field] = list
      .map((slot) => {
        const id = String(slot?.id || '')
          .trim()
          .toLowerCase()
        if (!id || seen.has(id)) return null
        seen.add(id)
        return { id, nome: String(slot?.nome || '').trim() }
      })
      .filter((s): s is SwotPilarSlot => !!s)
  }
  return base
}

function resolvePillar(field: SwotListField, id: string, nomeHint = ''): QuadrantPillar {
  const canonical = PILLAR_BY_ID[id as Exclude<SwotPilarId, ''>]
  const name = (nomeHint || '').trim() || defaultNomeFor(field, id)
  if (canonical) {
    return { id, name, q: canonical.q }
  }
  const pretty = id
    .split(/[-_]/)
    .filter(Boolean)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ')
  return { id, name: name || pretty || id, q: '' }
}

const QUADRANTS: {
  field: SwotListField
  letter: string
  name: string
  quest: string
  neg: boolean
  internal: boolean
}[] = [
  {
    field: 'forcas',
    letter: 'F',
    name: 'Forças',
    quest: 'O que a organização tem hoje que sustenta a estratégia de IA?',
    neg: false,
    internal: true,
  },
  {
    field: 'oportunidades',
    letter: 'O',
    name: 'Oportunidades',
    quest: 'Que condição externa a estratégia de IA pode explorar?',
    neg: false,
    internal: false,
  },
  {
    field: 'fraquezas',
    letter: 'f',
    name: 'Fraquezas',
    quest: 'O que, dentro de casa, trava a estratégia de IA?',
    neg: true,
    internal: true,
  },
  {
    field: 'ameacas',
    letter: 'A',
    name: 'Ameaças',
    quest: 'O que pode inviabilizar ou encarecer a estratégia de IA?',
    neg: true,
    internal: false,
  },
]

const TOWS: {
  field: SwotTowsField
  key: string
  quest: string
  hint: string
  hard?: boolean
}[] = [
  {
    field: 'tows_fo',
    key: 'F × O · Ofensiva',
    quest: 'Como usar nossas forças para capturar as oportunidades?',
    hint: 'As apostas de crescimento — onde investir e acelerar.',
  },
  {
    field: 'tows_fa',
    key: 'F × A · Defesa',
    quest: 'Como usar nossas forças para neutralizar as ameaças?',
    hint: 'Como proteger a posição e transformar risco em barreira de entrada.',
  },
  {
    field: 'tows_fxo',
    key: 'f × O · Reforço',
    quest: 'Que fraquezas travam a captura das oportunidades?',
    hint: 'O que consertar primeiro — a fila de capacitação.',
  },
  {
    field: 'tows_fxa',
    key: 'f × A · Sobrevivência',
    quest: 'Onde a vulnerabilidade interna encontra o risco externo?',
    hint: 'O ponto de maior perigo — mitigar ou repensar a estratégia.',
    hard: true,
  },
]

const VEREDITO_OPTIONS: { id: SwotVereditoTipo; label: string }[] = [
  { id: 'executavel', label: 'Executável como está' },
  { id: 'fundacao', label: 'Executável com fase de fundação' },
  { id: 'repensar', label: 'Repensar a estratégia' },
]

function emptyItem(pilar: string = ''): SwotItem {
  return {
    id: '',
    texto: '',
    pilar,
    question_id: '',
    impacto: null,
    viabilidade: null,
    probabilidade: null,
    evidencia: '',
    prioridade: null,
    tows: true,
  }
}

function emptyInitiative(): SwotInitiative {
  return { acao: '', dono: '', horizonte: '', itens_internos: [], itens_externos: [] }
}

function normalizeItem(raw: SwotItem | string | Partial<SwotItem>): SwotItem {
  if (typeof raw === 'string') {
    return { ...emptyItem(), texto: raw }
  }
  return {
    id: raw.id || '',
    texto: raw.texto || '',
    pilar: raw.pilar || '',
    question_id: raw.question_id || '',
    impacto: raw.impacto ?? null,
    viabilidade: raw.viabilidade ?? null,
    probabilidade: raw.probabilidade ?? null,
    evidencia: raw.evidencia || '',
    prioridade: raw.prioridade ?? null,
    tows: raw.tows !== false,
  }
}

const form = ref({
  optica: '',
  pilares: emptyPilares() as SwotPilaresPorQuadrante,
  forcas: [] as SwotItem[],
  fraquezas: [] as SwotItem[],
  oportunidades: [] as SwotItem[],
  ameacas: [] as SwotItem[],
  tows_fo: [] as SwotInitiative[],
  tows_fa: [] as SwotInitiative[],
  tows_fxo: [] as SwotInitiative[],
  tows_fxa: [] as SwotInitiative[],
  veredito_tipo: '' as SwotVereditoTipo,
  veredito_titulo: '',
  veredito_texto: '',
})

type DraftKey = `${SwotListField}:${string}`
const drafts = reactive<Record<string, string>>({})

function draftKey(field: SwotListField, pilar: string): DraftKey {
  return `${field}:${pilar || '_none'}`
}

function getDraft(field: SwotListField, pilar: string): string {
  return drafts[draftKey(field, pilar)] || ''
}

function setDraft(field: SwotListField, pilar: string, value: string) {
  drafts[draftKey(field, pilar)] = value
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

function pillarLabel(pilarId: string): string {
  const id = (pilarId || '').trim().toLowerCase()
  if (!id) return ''
  return PILLAR_BY_ID[id as Exclude<SwotPilarId, ''>]?.name || pilarId
}

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
    groups[i].items.push(item)
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

function persist(opts?: { rebuildTows?: boolean }) {
  if (opts?.rebuildTows) pendingRebuildTows = true
  void autosave.save()
}

function itemsForPilar(field: SwotListField, pilar: string): { item: SwotItem; index: number }[] {
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

function unassignedItems(field: SwotListField): { item: SwotItem; index: number }[] {
  const known = knownPillarIds(field)
  return form.value[field]
    .map((item, index) => ({ item, index }))
    .filter(({ item }) => !item.pilar || !known.has(item.pilar))
}

function availablePillarsToAdd(field: SwotListField): QuadrantPillar[] {
  const used = knownPillarIds(field)
  return PILLARS.filter((p) => !used.has(p.id)).map((p) => resolvePillar(field, p.id))
}

function slugifyPillar(raw: string): string {
  return raw
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 40)
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
  void persist()
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
  void persist()
}

function addItem(field: SwotListField, pilar: string) {
  const key = draftKey(field, pilar)
  const text = (drafts[key] || '').trim()
  if (!text) return
  if (form.value[field].length >= 40) return
  form.value[field] = [...form.value[field], { ...emptyItem(pilar), texto: text }]
  drafts[key] = ''
  void persist({ rebuildTows: true })
}

function removeItem(field: SwotListField, index: number) {
  form.value[field] = form.value[field].filter((_, i) => i !== index)
  void persist({ rebuildTows: true })
}

function toggleItemTows(field: SwotListField, index: number) {
  const list = form.value[field].map((item) => ({ ...item }))
  const current = list[index]
  if (!current) return
  list[index] = { ...current, tows: !current.tows }
  form.value[field] = list
  void persist({ rebuildTows: true })
}

function onItemBlur(field: SwotListField, index: number, ev: Event) {
  const input = ev.target as HTMLInputElement
  const next = input.value.trim()
  const list = form.value[field].map((item) => ({ ...item }))
  if (!next) {
    list.splice(index, 1)
    form.value[field] = list
    void persist({ rebuildTows: true })
    return
  }
  list[index] = { ...list[index], texto: next }
  form.value[field] = list
  void persist()
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
  void persist()
}

function onInitiativeBlur(field: SwotTowsField, index: number, key: keyof SwotInitiative, ev: Event) {
  const input = ev.target as HTMLInputElement
  const list = form.value[field].map((row) => ({ ...row }))
  const row = { ...list[index], [key]: input.value }
  if (!(row.acao || '').trim() && !(row.dono || '').trim() && !(row.horizonte || '').trim()) {
    list.splice(index, 1)
  } else {
    list[index] = row
  }
  form.value[field] = list
  void persist()
}

function setVereditoTipo(tipo: SwotVereditoTipo) {
  form.value.veredito_tipo = tipo
  void persist()
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
    // Evita reload quando só sincronizamos a URL com o id carregado
    if (typeof next === 'string' && next === currentSwotId.value) return
    void loadSwot()
  }
)

onUnmounted(() => {
  document.removeEventListener('pointerdown', onDocPointerDown)
})
</script>

<template>
  <div class="wrap">
    <div class="page-header">
      <div>
        <p class="eyebrow">Instrumento estratégico · Valorian</p>
        <h1 class="page-title">SWOT de <em>IA</em></h1>
        <p class="page-desc">
          Traduz a prontidão do
          <RouterLink class="inline-link" to="/ai-maturity">Modelo de Maturidade</RouterLink>
          em FOFA estratégica — sob a ótica da estratégia de IA, da matriz ao veredito.
        </p>
        <p v-if="maturityResponseId" class="page-desc maturity-origin">
          Gerada a partir do
          <RouterLink class="inline-link" :to="`/ai-maturity/${maturityResponseId}`">
            diagnóstico de maturidade
          </RouterLink>
          · esta é a SWOT em edição (a barra SWOT abre sempre a mais recente).
        </p>
      </div>
      <div class="header-actions">
        <input
          ref="fileInput"
          type="file"
          accept="application/json,.json"
          class="sr-only"
          @change="onImportFile"
        />
        <RouterLink class="maturity-link" to="/ai-maturity">Modelo de Maturidade</RouterLink>
        <button type="button" class="import-btn" :disabled="importState === 'importing'" @click="openImportPicker">
          {{ importState === 'importing' ? 'Importando…' : 'Importar JSON' }}
        </button>
        <div class="save-pill" :data-state="saveState">
          <span v-if="saveState === 'saving'">Salvando…</span>
          <span v-else-if="saveState === 'saved'">Salvo</span>
          <span v-else-if="saveState === 'error'">{{ saveError || 'Erro ao salvar' }}</span>
          <span v-else>Auto-salva</span>
        </div>
      </div>
    </div>

    <div v-if="importState === 'error'" class="card error-msg">{{ importError }}</div>
    <div v-else-if="importState === 'ok'" class="card import-ok">JSON importado com sucesso.</div>

    <div v-if="loading" class="card">Carregando…</div>
    <div v-else-if="error" class="card error-msg">{{ error }}</div>

    <template v-else>
      <section class="card method">
        <button type="button" class="method-toggle" @click="showMethod = !showMethod">
          <span>O método em uma página</span>
          <span>{{ showMethod ? '−' : '+' }}</span>
        </button>
        <div v-if="showMethod" class="method-body">
          <p>
            Dois instrumentos, uma jornada. O
            <RouterLink class="inline-link" to="/ai-maturity">Modelo de Maturidade</RouterLink>
            diagnostica a <strong>prontidão</strong> em quatro dimensões (escala 1–5; abrangência Básico /
            Completo / Complementar). A SWOT traduz esse diagnóstico em
            <strong>FOFA estratégica</strong> sob a ótica da estratégia organizacional de IA.
          </p>
          <p>
            O objeto é a <strong>organização</strong>. A ótica é a
            <strong>estratégia organizacional de IA</strong>. Um item só entra se afeta materialmente a
            capacidade de executar essa estratégia — use as respostas e médias do diagnóstico como evidência
            quando existirem.
          </p>

          <h3>Quatro dimensões · sete pilares</h3>
          <p class="method-note">
            Os pilares da SWOT aprofundam as mesmas dimensões do Modelo de Maturidade. Cada quadrante parte de
            um subconjunto (banco de itens); você pode acrescentar pilares canônicos ou custom.
          </p>
          <div class="dim-groups">
            <div v-for="dim in pillarsByMaturityDimension" :key="dim.id" class="dim-group">
              <div class="dim-group-head">
                <strong>{{ dim.name }}</strong>
                <span>{{ dim.brief }}</span>
              </div>
              <div class="pillarq">
                <div v-for="p in dim.pillars" :key="p.id">
                  <b>{{ p.name }}.</b> <i>{{ p.q }}</i>
                </div>
              </div>
            </div>
          </div>

          <h3>Duas regras</h3>
          <ul class="bullets">
            <li>
              <strong>Locus disciplinado.</strong> Forças e Fraquezas são internas (capacidade sob controle da
              organização — tipicamente o grosso do diagnóstico de maturidade). Oportunidades e Ameaças são do
              ambiente (regulação, mercado, fornecedores, ritmo externo).
            </li>
            <li>
              <strong>Baseado em evidência.</strong> Cada item ancorado em fato, métrica ou nível observado no
              diagnóstico (escala 1–5) — priorize por impacto (ideal: 2–3 por quadrante).
            </li>
            <li>
              <strong>Nota 3 fica à parte.</strong> Respostas intermediárias do diagnóstico vão para
              <em>Pontos de Atenção</em> (watchlist) — não entram no SWOT nem no TOWS; acompanhe no próximo ciclo.
            </li>
          </ul>
          <ol class="steps">
            <li>
              <strong>Declare a ótica.</strong> Estratégia de IA em uma frase — o mesmo norte que o diagnóstico
              de maturidade avalia.
            </li>
            <li>
              <strong>Varra os quadrantes</strong> pelas quatro dimensões (pilares do banco de itens de cada
              quadrante).
            </li>
            <li><strong>Aplique o crivo.</strong> Descarte o que não afeta a estratégia.</li>
            <li>
              <strong>Priorize.</strong> Fique com os 2–3 itens mais fortes de cada quadrante (impacto ×
              viabilidade ou probabilidade, na mesma escala 1–5).
            </li>
            <li>
              <strong>Revise os Pontos de Atenção</strong> (nota 3) e cruze o TOWS → iniciativas → veredito.
            </li>
          </ol>
          <button type="button" class="catalog-toggle" @click="showCatalog = !showCatalog">
            {{ showCatalog ? 'Ocultar banco de itens' : 'Ver banco de itens (partida)' }}
          </button>
          <div v-if="showCatalog" class="catalog">
            <div v-for="c in CATALOG" :key="c.letter" class="cat" :class="{ neg: c.neg }">
              <div class="tag">
                <span class="letter">{{ c.letter }}</span>
                <span class="name">{{ c.name }}</span>
              </div>
              <p class="cat-locus">{{ c.locus }}</p>
              <ul class="cat-groups">
                <li v-for="g in c.groups" :key="g.label">
                  <b>{{ g.label }}</b> — {{ g.text }}
                </li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      <section class="object card-object">
        <div class="eyebrow gold">1 · A ótica · estratégia organizacional de IA</div>
        <textarea
          v-model="form.optica"
          class="optica-write"
          rows="3"
          maxlength="2000"
          placeholder="Em uma frase: a ambição declarada de para onde a organização quer ir com IA…"
          @blur="persist"
        />
      </section>

      <section class="matrix-block">
        <div class="section-head">
          <div class="eyebrow">2 · Matriz</div>
          <h2>Interno × Externo</h2>
          <p class="hint">
            No interno (Forças / Fraquezas), o repertório de partida usa as quatro dimensões do Modelo de
            Maturidade. No externo, o foco é ambiente. Inclua outro pilar se precisar. Priorize 2–3 itens por
            quadrante. Marque o checkbox dos itens que entram no cruzamento TOWS. Toque no ? para o repertório.
          </p>
        </div>
        <div class="axis-top"><span>Interno</span><span>Externo</span></div>
        <div class="matrix">
          <div class="node">A<br />ORGANI-<br />ZAÇÃO</div>
          <div
            v-for="q in QUADRANTS"
            :key="q.field"
            class="q"
            :class="{ neg: q.neg, 'help-open': openHelp === q.field }"
          >
            <button
              type="button"
              class="q-help-btn"
              :aria-expanded="openHelp === q.field"
              :aria-label="`Repertório de partida · ${q.name}`"
              @click="toggleHelp(q.field, $event)"
            >
              ?
            </button>
            <div v-if="openHelp === q.field" class="q-help" role="dialog" :aria-label="`Ajuda · ${q.name}`">
              <div class="q-help-head">
                <span class="q-help-letter" :class="{ neg: q.neg }">{{ QUADRANT_HINTS[q.field].letter }}</span>
                <div>
                  <strong>{{ QUADRANT_HINTS[q.field].name }}</strong>
                  <span class="q-help-locus">{{ QUADRANT_HINTS[q.field].locus }}</span>
                </div>
              </div>
              <p class="q-help-note">
                Repertório de partida alinhado às dimensões do Modelo de Maturidade — estímulo, não checklist.
              </p>
              <ul class="q-help-list">
                <li v-for="g in QUADRANT_HINTS[q.field].groups" :key="g.label">
                  <span class="q-help-pillar">{{ g.label }}</span>
                  <span class="q-help-text">{{ g.text }}</span>
                </li>
              </ul>
            </div>
            <div class="tag">
              <span class="letter">{{ q.letter }}</span>
              <span class="name">{{ q.name }}</span>
            </div>
            <div class="quest">{{ q.quest }}</div>

            <div
              v-if="unassignedItems(q.field).length"
              class="pillar-block pillar-orphan"
            >
              <div class="pillar-label">Sem pilar</div>
              <ul class="item-list">
                <li
                  v-for="{ item, index } in unassignedItems(q.field)"
                  :key="item.id || q.field + '-u-' + index"
                  class="item-row"
                  :class="{ 'tows-off': !item.tows }"
                >
                  <label class="item-tows" :title="item.tows ? 'No TOWS — clique para excluir' : 'Fora do TOWS — clique para incluir'">
                    <input
                      type="checkbox"
                      :checked="item.tows"
                      @change="toggleItemTows(q.field, index)"
                    />
                    <span class="sr-only">Incluir no TOWS</span>
                  </label>
                  <input
                    :value="item.texto"
                    class="item-input"
                    :title="item.texto || undefined"
                    maxlength="500"
                    @blur="onItemBlur(q.field, index, $event)"
                  />
                  <button type="button" class="item-remove" title="Remover" @click="removeItem(q.field, index)">
                    ×
                  </button>
                </li>
              </ul>
            </div>

            <div
              v-for="p in pillarsForQuadrant(q.field)"
              :key="q.field + p.id"
              class="pillar-block"
            >
              <div class="pillar-label" :title="p.q || undefined">{{ p.name }}</div>
              <ul class="item-list">
                <li
                  v-for="{ item, index } in itemsForPilar(q.field, p.id)"
                  :key="item.id || q.field + p.id + index"
                  class="item-row"
                  :class="{ 'tows-off': !item.tows }"
                >
                  <label class="item-tows" :title="item.tows ? 'No TOWS — clique para excluir' : 'Fora do TOWS — clique para incluir'">
                    <input
                      type="checkbox"
                      :checked="item.tows"
                      @change="toggleItemTows(q.field, index)"
                    />
                    <span class="sr-only">Incluir no TOWS</span>
                  </label>
                  <input
                    :value="item.texto"
                    class="item-input"
                    :title="item.texto || undefined"
                    maxlength="500"
                    @blur="onItemBlur(q.field, index, $event)"
                  />
                  <button type="button" class="item-remove" title="Remover" @click="removeItem(q.field, index)">
                    ×
                  </button>
                </li>
              </ul>
              <div class="item-add">
                <input
                  :value="getDraft(q.field, p.id)"
                  type="text"
                  maxlength="500"
                  :placeholder="`Adicionar em ${p.name}…`"
                  @input="setDraft(q.field, p.id, ($event.target as HTMLInputElement).value)"
                  @keydown="onDraftKeydown(q.field, p.id, $event)"
                />
                <button type="button" @click="addItem(q.field, p.id)">+</button>
              </div>
            </div>

            <div class="pillar-add">
              <button
                type="button"
                class="pillar-add-toggle"
                :aria-expanded="addingPillarFor === q.field"
                @click="openAddPillar(q.field)"
              >
                {{ addingPillarFor === q.field ? 'Cancelar' : '+ Incluir pilar' }}
              </button>
              <div v-if="addingPillarFor === q.field" class="pillar-add-panel">
                <p class="pillar-add-hint">Escolha um pilar canônico ou crie um novo para este quadrante.</p>
                <div v-if="availablePillarsToAdd(q.field).length" class="pillar-add-choices">
                  <button
                    v-for="opt in availablePillarsToAdd(q.field)"
                    :key="opt.id"
                    type="button"
                    class="pillar-choice"
                    @click="addCanonicalPillar(q.field, opt.id)"
                  >
                    {{ opt.name }}
                  </button>
                </div>
                <div class="pillar-add-custom">
                  <input
                    v-model="customPillarDraft"
                    type="text"
                    maxlength="40"
                    placeholder="Novo pilar (ex.: Mercado)"
                    @keydown.enter.prevent="addCustomPillar(q.field)"
                  />
                  <button type="button" @click="addCustomPillar(q.field)">Criar</button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section v-if="hasWatchlist" class="watchlist-block">
        <div class="section-head">
          <div class="eyebrow">3 · Pontos de Atenção</div>
          <h2>Watchlist · nota 3</h2>
          <p class="hint">
            Áreas em maturação vindas do Modelo de Maturidade. Ficam fora do SWOT e do TOWS — monitore no próximo
            ciclo; podem virar Força ou Fraqueza.
          </p>
        </div>
        <div class="watchlist">
          <div v-for="group in watchlistGroups" :key="group.dimensao" class="watchlist-group">
            <div class="watchlist-dim">{{ group.dimensao }}</div>
            <ul class="watchlist-list">
              <li v-for="item in group.items" :key="item.id || item.texto" class="watchlist-item">
                <div class="watchlist-meta">
                  <span v-if="item.id" class="watchlist-code">{{ item.id }}</span>
                  <span v-if="item.pilar" class="watchlist-pillar">{{ pillarLabel(item.pilar) }}</span>
                  <span v-if="item.nota != null" class="watchlist-nota">N{{ item.nota }}</span>
                </div>
                <p class="watchlist-text">{{ item.texto }}</p>
                <p v-if="item.evidencia" class="watchlist-evidence">{{ item.evidencia }}</p>
              </li>
            </ul>
          </div>
        </div>
      </section>

      <section class="tows-block">
        <div class="section-head">
          <div class="eyebrow">{{ towsStep }} · Cruzamento TOWS</div>
          <h2>Do diagnóstico à decisão</h2>
          <p class="hint">
            Gerado só com os itens marcados na matriz (F×O, F×A, f×O, f×A). Cada cruzamento vira uma iniciativa.
            Comece pelo f × A — é onde a estratégia pode quebrar.
          </p>
        </div>
        <div class="tows">
          <div v-for="t in TOWS" :key="t.field" class="tows-cell" :class="{ hard: t.hard }">
            <span class="k">{{ t.key }}</span>
            <span class="qz">{{ t.quest }}</span>
            <p class="thint">{{ t.hint }}</p>
            <div v-for="(row, idx) in form[t.field]" :key="row.id || t.field + idx" class="init-row">
              <input
                :value="row.acao"
                class="init-acao"
                maxlength="1000"
                placeholder="Ação / iniciativa"
                @blur="onInitiativeBlur(t.field, idx, 'acao', $event)"
              />
              <div class="init-meta">
                <input
                  :value="row.dono"
                  maxlength="200"
                  placeholder="Dono"
                  @blur="onInitiativeBlur(t.field, idx, 'dono', $event)"
                />
                <input
                  :value="row.horizonte"
                  maxlength="120"
                  placeholder="Horizonte"
                  @blur="onInitiativeBlur(t.field, idx, 'horizonte', $event)"
                />
                <button type="button" class="item-remove" title="Remover" @click="removeInitiative(t.field, idx)">
                  ×
                </button>
              </div>
            </div>
            <button type="button" class="add-init" @click="addInitiative(t.field)">+ Iniciativa</button>
          </div>
        </div>
      </section>

      <section class="verdict">
        <div class="eyebrow gold">{{ verdictStep }} · Veredito</div>
        <p class="verdict-lead">
          À luz das forças/fraquezas internas (e do nível de maturidade observado), a estratégia se sustenta,
          precisa de uma fase de fundação, ou deve ser repensada?
        </p>
        <div class="verdict-types">
          <button
            v-for="opt in VEREDITO_OPTIONS"
            :key="opt.id"
            type="button"
            class="vtype"
            :class="{ active: form.veredito_tipo === opt.id }"
            @click="setVereditoTipo(opt.id)"
          >
            {{ opt.label }}
          </button>
        </div>
        <input
          v-model="form.veredito_titulo"
          class="verdict-title"
          maxlength="300"
          placeholder="Título do veredito (ex.: Ambição certa, organização ainda não pronta.)"
          @blur="persist"
        />
        <textarea
          v-model="form.veredito_texto"
          class="verdict-text"
          rows="5"
          maxlength="8000"
          placeholder="Conclusão e recomendação…"
          @blur="persist"
        />
      </section>
    </template>
  </div>
</template>

<style scoped>
.wrap {
  /* DS-01: --gold e --serif removidos — herdam o token global único
     (main.css), que agora tem exatamente estes valores. */
  --navy: var(--k0);
  --navy-2: #16243f;
  --ink: #242a33;
  --gold-2: #e3cb93;
  --ivory: #f6f1e7;
  --ivory-2: #fbf8f1;
  --oxblood: #7c3a3a;
  --muted: var(--k3);
  --line: rgba(198, 161, 91, 0.32);
  max-width: 920px;
  margin: 0 auto;
  padding: 28px 20px 72px;
  color: var(--ink);
}
.page-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
  margin-bottom: 22px;
}
.header-actions {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 8px;
  flex-shrink: 0;
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
.import-btn {
  border: 1px solid var(--line);
  background: #fff;
  color: var(--navy);
  font-size: 11px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  font-weight: 600;
  padding: 6px 12px;
  border-radius: var(--r-pill);
  cursor: pointer;
  font-family: inherit;
}
.import-btn:hover:not(:disabled) {
  border-color: var(--gold);
  color: var(--gold);
}
.import-btn:disabled {
  opacity: 0.6;
  cursor: wait;
}
.import-ok {
  color: #2f6e4a;
  border-color: #bbd3b7;
  background: #e8f0e7;
}
.eyebrow {
  font-size: 0.7rem;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: var(--gold);
  font-weight: 600;
  margin: 0 0 6px;
}
.eyebrow.gold {
  color: var(--gold-2);
}
.page-title {
  font-family: var(--serif);
  font-weight: 600;
  font-size: clamp(1.9rem, 5vw, 2.6rem);
  line-height: 1.05;
  color: var(--navy);
  margin: 0 0 8px;
}
.page-title em {
  font-style: italic;
  color: var(--gold);
}
.page-desc {
  margin: 0;
  color: var(--muted);
  font-size: 14px;
  line-height: 1.5;
  max-width: 52ch;
}
.page-desc.maturity-origin {
  margin-top: 8px;
  font-size: 13px;
}
.inline-link {
  color: var(--navy);
  font-weight: 600;
  text-decoration: underline;
  text-underline-offset: 2px;
}
.inline-link:hover {
  color: var(--gold);
}
.maturity-link {
  display: inline-flex;
  align-items: center;
  padding: 8px 14px;
  border: 1px solid var(--navy);
  border-radius: var(--r-xs);
  background: #fff;
  color: var(--navy);
  font-size: 13px;
  font-weight: 600;
  text-decoration: none;
  white-space: nowrap;
  transition: opacity 0.2s;
}
.maturity-link:hover {
  opacity: 0.9;
}
.save-pill {
  flex-shrink: 0;
  font-size: 11px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  padding: 6px 10px;
  border: 1px solid var(--line);
  border-radius: var(--r-pill);
  color: var(--muted);
  background: #fff;
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
  max-width: 180px;
}
.card {
  background: var(--ivory-2);
  border: 1px solid var(--line);
  border-radius: var(--r-xs);
  padding: 18px 20px;
  margin-bottom: 16px;
}
.error-msg {
  color: #8f2b2b;
}
.method-toggle,
.catalog-toggle {
  width: 100%;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: none;
  border: none;
  font: inherit;
  font-weight: 700;
  color: var(--navy);
  cursor: pointer;
  padding: 0;
  text-align: left;
}
.catalog-toggle {
  margin-top: 14px;
  font-size: 13px;
  color: var(--gold);
  font-weight: 600;
  justify-content: flex-start;
  gap: 6px;
}
.method-body {
  margin-top: 14px;
  font-size: 14px;
  line-height: 1.55;
}
.method-body h3 {
  font-size: 0.95rem;
  color: var(--navy);
  margin: 1.1em 0 0.35em;
}
.method-note {
  margin: 0 0 0.75em;
  color: var(--muted);
  font-size: 13px;
  line-height: 1.5;
}
.dim-groups {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin: 0.5em 0 1em;
}
.dim-group {
  background: #fff;
  border: 1px solid var(--line);
  border-radius: var(--r-xs);
  padding: 12px 14px;
}
.dim-group-head {
  display: flex;
  flex-direction: column;
  gap: 2px;
  margin-bottom: 4px;
}
.dim-group-head strong {
  color: var(--navy);
  font-size: 0.92rem;
}
.dim-group-head span {
  color: var(--muted);
  font-size: 12px;
  line-height: 1.4;
}
.dim-group .pillarq {
  margin: 0.2em 0 0;
}
.pillarq {
  border-top: 1px solid var(--line);
  margin: 0.4em 0 0.8em;
}
.pillarq div {
  padding: 8px 0;
  border-bottom: 1px solid var(--line);
  font-size: 0.9rem;
  line-height: 1.42;
}
.pillarq b {
  color: var(--navy);
}
.pillarq i {
  color: #3a3f49;
  font-style: italic;
}
.bullets {
  list-style: none;
  margin: 0;
  padding: 0;
}
.bullets li {
  position: relative;
  padding: 0 0 0.55em 18px;
  font-size: 0.92rem;
}
.bullets li::before {
  content: '';
  position: absolute;
  left: 2px;
  top: 0.55em;
  width: 6px;
  height: 6px;
  transform: rotate(45deg);
  background: var(--gold);
}
.steps {
  list-style: none;
  margin: 0.4em 0 0;
  padding: 0;
  counter-reset: s;
}
.steps li {
  position: relative;
  padding: 2px 0 0.75em 42px;
  counter-increment: s;
  font-size: 0.92rem;
}
.steps li::before {
  content: counter(s, decimal-leading-zero);
  position: absolute;
  left: 0;
  top: -2px;
  font-family: var(--serif);
  font-weight: 700;
  font-size: 1.15rem;
  color: var(--gold);
}
.steps li strong {
  display: block;
}
.catalog {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-top: 12px;
}
.cat {
  background: #fff;
  border: 1px solid var(--line);
  border-top: 3px solid var(--gold);
  padding: 14px 15px;
}
.cat.neg {
  border-top-color: var(--oxblood);
}
.cat .tag {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-bottom: 2px;
}
.cat .letter {
  font-family: var(--serif);
  font-weight: 700;
  font-size: 1.35rem;
  color: var(--gold);
  line-height: 1;
}
.cat.neg .letter {
  color: var(--oxblood);
}
.cat .name {
  font-weight: 700;
  color: var(--navy);
  font-size: 0.92rem;
}
.cat-locus {
  margin: 2px 0 8px;
  font-size: 0.68rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--muted);
  font-weight: 600;
}
.cat-groups {
  list-style: none;
  margin: 0;
  padding: 0;
}
.cat-groups li {
  position: relative;
  font-size: 0.84rem;
  padding: 0 0 0.55em 14px;
  line-height: 1.4;
}
.cat-groups li::before {
  content: '';
  position: absolute;
  left: 1px;
  top: 0.55em;
  width: 5px;
  height: 5px;
  transform: rotate(45deg);
  background: var(--gold);
}
.cat.neg .cat-groups li::before {
  background: var(--oxblood);
}
.cat-groups b {
  color: var(--navy);
}
.card-object {
  background: var(--navy);
  color: #f1ebdd;
  border-left: 4px solid var(--gold);
  padding: 18px 20px;
  margin-bottom: 18px;
  border-radius: 2px;
}
.optica-write {
  width: 100%;
  margin-top: 10px;
  border: none;
  outline: none;
  resize: vertical;
  background: transparent;
  color: #fbf8f1;
  font-family: var(--serif);
  font-size: 1.08rem;
  line-height: 1.45;
  padding: 0;
}
.optica-write::placeholder {
  color: #9da6b8;
}
.section-head {
  margin-bottom: 12px;
}
.section-head h2 {
  font-family: var(--serif);
  font-weight: 600;
  color: var(--navy);
  font-size: clamp(1.25rem, 3.5vw, 1.55rem);
  margin: 0.15em 0 0.3em;
}
.section-head .hint {
  margin: 0;
  color: var(--muted);
  font-size: 0.88rem;
}
.axis-top {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-bottom: 6px;
}
.axis-top span {
  text-align: center;
  font-size: 0.68rem;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: var(--muted);
  font-weight: 600;
}
.matrix {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  position: relative;
  margin-bottom: 28px;
}
.q {
  background: #fff;
  border: 1px solid var(--line);
  border-top: 3px solid var(--gold);
  padding: 14px 16px;
  min-height: 180px;
  position: relative;
}
.q.help-open {
  z-index: 5;
}
.q.neg {
  border-top-color: var(--oxblood);
}
.q-help-btn {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  border: 1px solid var(--line);
  background: #fff;
  color: var(--gold);
  font-family: var(--serif);
  font-weight: 700;
  font-size: 13px;
  line-height: 1;
  cursor: pointer;
  z-index: 3;
  display: grid;
  place-content: center;
  padding: 0;
}
.q.neg .q-help-btn {
  color: var(--oxblood);
}
.q-help-btn:hover,
.q-help-btn[aria-expanded='true'] {
  border-color: var(--gold);
  background: #fffaf0;
}
.q.neg .q-help-btn:hover,
.q.neg .q-help-btn[aria-expanded='true'] {
  border-color: var(--oxblood);
  background: #fcf6f4;
}
.q-help {
  position: absolute;
  top: 36px;
  right: 8px;
  width: min(300px, calc(100% - 16px));
  max-height: min(340px, 70vh);
  overflow: auto;
  background: #fffef9;
  border: 1px solid var(--line);
  box-shadow: 0 10px 28px rgba(14, 27, 51, 0.18);
  padding: 12px 14px;
  z-index: 6;
  border-radius: 2px;
}
.q.neg .q-help {
  border-color: rgba(124, 58, 58, 0.28);
  background: #fffaf8;
}
.q-help-head {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  margin-bottom: 8px;
}
.q-help-letter {
  font-family: var(--serif);
  font-weight: 700;
  font-size: 1.4rem;
  color: var(--gold);
  line-height: 1;
}
.q-help-letter.neg {
  color: var(--oxblood);
}
.q-help-locus {
  display: block;
  font-size: 0.68rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--muted);
  font-weight: 600;
  margin-top: 2px;
}
.q-help-note {
  margin: 0 0 10px;
  font-size: 0.78rem;
  color: var(--muted);
  line-height: 1.4;
}
.q-help-list {
  list-style: none;
  margin: 0;
  padding: 0;
}
.q-help-list li {
  padding: 8px 0;
  border-top: 1px solid var(--line);
}
.q-help-list li:first-child {
  border-top: none;
  padding-top: 0;
}
.q-help-pillar {
  display: block;
  font-size: 0.72rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  font-weight: 700;
  color: var(--navy);
  margin-bottom: 3px;
}
.q.neg .q-help-pillar {
  color: var(--oxblood);
}
.q-help-text {
  display: block;
  font-size: 0.82rem;
  line-height: 1.4;
  color: #3a3f49;
}
.q .tag {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-bottom: 6px;
  padding-right: 28px;
}
.q .letter {
  font-family: var(--serif);
  font-weight: 700;
  font-size: 1.4rem;
  color: var(--gold);
  line-height: 1;
}
.q.neg .letter {
  color: var(--oxblood);
}
.q .name {
  font-weight: 700;
  color: var(--navy);
  font-size: 0.95rem;
}
.q .quest {
  font-size: 0.8rem;
  color: var(--muted);
  font-style: italic;
  margin: 0 0 10px;
  line-height: 1.35;
}
.node {
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  width: 74px;
  height: 74px;
  border-radius: 50%;
  background: var(--navy);
  color: var(--gold-2);
  display: grid;
  place-content: center;
  text-align: center;
  font-size: 0.58rem;
  letter-spacing: 0.1em;
  font-weight: 700;
  border: 2px solid var(--gold);
  box-shadow: 0 4px 18px rgba(14, 27, 51, 0.35);
  z-index: 2;
  line-height: 1.15;
  pointer-events: none;
}
.pillar-block {
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px solid rgba(198, 161, 91, 0.18);
}
.pillar-block:first-of-type {
  margin-top: 4px;
}
.pillar-orphan {
  background: #faf7f0;
  margin: 0 -6px 4px;
  padding: 8px 6px 10px;
  border-top: none;
  border-radius: 2px;
}
.pillar-label {
  font-size: 0.66rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  font-weight: 700;
  color: var(--gold);
  margin-bottom: 5px;
}
.q.neg .pillar-label {
  color: var(--oxblood);
}
.pillar-orphan .pillar-label {
  color: var(--muted);
}
.item-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 5px;
}
.item-row {
  display: flex;
  gap: 4px;
  align-items: center;
}
.item-row.tows-off .item-input {
  color: var(--muted);
  opacity: 0.72;
}
.item-tows {
  flex-shrink: 0;
  display: grid;
  place-content: center;
  width: 22px;
  height: 22px;
  margin: 0;
  cursor: pointer;
}
.item-tows input {
  width: 14px;
  height: 14px;
  margin: 0;
  accent-color: var(--gold);
  cursor: pointer;
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
.item-input {
  flex: 1;
  min-width: 0;
  border: none;
  border-bottom: 1px dotted var(--line);
  background: transparent;
  font-size: 13px;
  color: var(--ink);
  font-family: inherit;
  padding: 4px 2px;
  outline: none;
}
.item-input:focus {
  border-bottom-color: var(--gold);
  background: #fffef9;
}
.item-remove {
  flex-shrink: 0;
  width: 24px;
  height: 24px;
  border: none;
  background: transparent;
  color: var(--muted);
  cursor: pointer;
  font-size: 16px;
  line-height: 1;
  border-radius: var(--r-xs);
}
.item-remove:hover {
  color: var(--oxblood);
  background: #f1e1dd;
}
.item-add {
  display: flex;
  gap: 6px;
  margin-top: 6px;
}
.item-add input {
  flex: 1;
  min-width: 0;
  border: 1px dashed var(--line);
  border-radius: 3px;
  background: #fff;
  font-size: 12px;
  padding: 5px 7px;
  font-family: inherit;
  color: var(--ink);
  outline: none;
}
.item-add input:focus {
  border-color: var(--gold);
  border-style: solid;
}
.item-add button,
.add-init {
  flex-shrink: 0;
  border: 1px solid var(--line);
  border-radius: 3px;
  background: #fff;
  color: var(--ink);
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
}
.item-add button {
  width: 28px;
}
.item-add button:hover,
.add-init:hover {
  border-color: var(--gold);
  color: var(--gold);
}
.pillar-add {
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px dashed var(--line);
}
.pillar-add-toggle {
  border: none;
  background: transparent;
  color: var(--gold);
  font-size: 0.78rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  cursor: pointer;
  padding: 0;
  font-family: inherit;
}
.q.neg .pillar-add-toggle {
  color: var(--oxblood);
}
.pillar-add-toggle:hover {
  text-decoration: underline;
}
.pillar-add-panel {
  margin-top: 8px;
  padding: 10px;
  background: var(--ivory-2);
  border: 1px solid var(--line);
}
.pillar-add-hint {
  margin: 0 0 8px;
  font-size: 0.75rem;
  color: var(--muted);
  line-height: 1.35;
}
.pillar-add-choices {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 8px;
}
.pillar-choice {
  border: 1px solid var(--line);
  background: #fff;
  color: var(--navy);
  font-size: 0.72rem;
  font-weight: 600;
  padding: 4px 8px;
  cursor: pointer;
  font-family: inherit;
  border-radius: 2px;
}
.pillar-choice:hover {
  border-color: var(--gold);
  color: var(--gold);
}
.pillar-add-custom {
  display: flex;
  gap: 6px;
}
.pillar-add-custom input {
  flex: 1;
  border: 1px solid var(--line);
  background: #fff;
  padding: 6px 8px;
  font-size: 0.82rem;
  font-family: inherit;
  outline: none;
}
.pillar-add-custom input:focus {
  border-color: var(--gold);
}
.pillar-add-custom button {
  border: 1px solid var(--navy);
  background: var(--navy);
  color: #fff;
  font-size: 0.72rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  padding: 0 10px;
  cursor: pointer;
  font-family: inherit;
}
.pillar-add-custom button:hover {
  background: #16243f;
}
.add-init {
  margin-top: 8px;
  width: 100%;
  padding: 7px 10px;
  font-size: 12px;
}
.watchlist-block {
  margin-bottom: 28px;
}
.watchlist {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.watchlist-group {
  border: 1px solid var(--line);
  background: #fff;
  padding: 14px 16px 12px;
}
.watchlist-dim {
  font-size: 0.68rem;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  font-weight: 700;
  color: var(--gold);
  margin-bottom: 10px;
}
.watchlist-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.watchlist-item {
  border-top: 1px solid rgba(14, 27, 51, 0.08);
  padding-top: 10px;
}
.watchlist-item:first-child {
  border-top: none;
  padding-top: 0;
}
.watchlist-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  margin-bottom: 4px;
}
.watchlist-code {
  font-family: var(--serif);
  font-weight: 700;
  font-size: 0.78rem;
  letter-spacing: 0.04em;
  color: var(--navy);
}
.watchlist-pillar,
.watchlist-nota {
  font-size: 0.68rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--muted);
  font-weight: 600;
}
.watchlist-nota {
  color: var(--oxblood);
}
.watchlist-text {
  margin: 0;
  color: var(--navy);
  font-size: 0.92rem;
  line-height: 1.4;
}
.watchlist-evidence {
  margin: 4px 0 0;
  color: var(--muted);
  font-size: 0.8rem;
  line-height: 1.4;
  font-style: italic;
}
.tows {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-bottom: 24px;
}
.tows-cell {
  border: 1px solid var(--line);
  padding: 14px 16px;
  background: #fff;
}
.tows-cell.hard {
  border-color: var(--oxblood);
  background: #fcf6f4;
}
.tows-cell .k {
  display: block;
  font-family: var(--serif);
  font-weight: 700;
  color: var(--gold);
  font-size: 0.88rem;
  letter-spacing: 0.05em;
}
.tows-cell.hard .k {
  color: var(--oxblood);
}
.tows-cell .qz {
  display: block;
  font-style: italic;
  color: var(--muted);
  font-size: 0.82rem;
  margin: 0.35em 0 0.2em;
  line-height: 1.35;
}
.thint {
  font-size: 0.85rem;
  margin: 0.2em 0 0.75em;
  line-height: 1.4;
  color: #3a3f49;
}
.init-row {
  margin-bottom: 8px;
}
.init-acao {
  width: 100%;
  border: 1px solid var(--line);
  border-radius: 3px;
  font-size: 13px;
  padding: 6px 8px;
  font-family: inherit;
  outline: none;
}
.init-acao:focus {
  border-color: var(--gold);
}
.init-meta {
  display: flex;
  gap: 6px;
  margin-top: 6px;
  align-items: center;
}
.init-meta input {
  flex: 1;
  min-width: 0;
  border: 1px solid var(--line);
  border-radius: 3px;
  font-size: 12px;
  padding: 5px 7px;
  font-family: inherit;
  outline: none;
}
.verdict {
  background: var(--navy);
  color: #efe9db;
  padding: 24px 26px;
  position: relative;
  border-radius: 2px;
}
.verdict::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  background: var(--gold);
}
.verdict-lead {
  margin: 0.4em 0 14px;
  color: #d8d2c4;
  font-size: 0.95rem;
}
.verdict-types {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 14px;
}
.vtype {
  border: 1px solid rgba(227, 203, 147, 0.35);
  background: transparent;
  color: #cfc7b6;
  font-size: 12px;
  padding: 7px 12px;
  cursor: pointer;
  border-radius: 2px;
}
.vtype.active {
  background: rgba(198, 161, 91, 0.2);
  border-color: var(--gold);
  color: var(--gold-2);
}
.verdict-title,
.verdict-text {
  width: 100%;
  border: none;
  outline: none;
  background: rgba(255, 255, 255, 0.04);
  color: #fbf8f1;
  font-family: inherit;
  padding: 10px 12px;
  margin-bottom: 10px;
  border-radius: 2px;
}
.verdict-title {
  font-size: 1.05rem;
  font-weight: 700;
}
.verdict-text {
  resize: vertical;
  font-size: 0.92rem;
  line-height: 1.5;
  min-height: 110px;
}
.verdict-title::placeholder,
.verdict-text::placeholder {
  color: #8c93a6;
}
@media (max-width: 700px) {
  .catalog,
  .matrix,
  .tows {
    grid-template-columns: 1fr;
  }
  .axis-top {
    display: none;
  }
  .node {
    position: static;
    transform: none;
    width: auto;
    height: auto;
    border-radius: 3px;
    margin: 0 0 10px;
    padding: 8px 12px;
    box-shadow: none;
    order: -1;
  }
  .matrix {
    display: flex;
    flex-direction: column;
  }
  .page-header {
    flex-direction: column;
  }
  .header-actions {
    align-items: flex-start;
    flex-direction: row;
    flex-wrap: wrap;
  }
}
</style>
