import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { onBeforeRouteLeave, useRoute, useRouter } from 'vue-router'
import {
  getOkrCycle,
  updateOkrCycle,
  activateOkrCycle,
  archiveOkrCycle,
  type KeyResult,
  type OkrCycle,
  type OkrCyclePayload,
  type OkrCycleTipo,
  type Objective,
} from '@/api/okrs'
import {
  getSwotAnalysisById,
  listSwotAnalyses,
  type SwotAnalysis,
  type SwotAnalysisSummary,
  type SwotInitiative,
  type SwotTowsField,
} from '@/api/swotAnalysis'


export function useOkrCycleEditor() {
  const route = useRoute()
  const router = useRouter()
  const cycleId = computed(() => String(route.params.id || ''))

  const MAX_OBJECTIVES = 20
  const MAX_KRS = 20
  /** Espera de digitação antes de gravar: longa o bastante para não salvar no meio de uma frase. */
  const AUTOSAVE_DELAY_MS = 1200
  const DRAFT_HINT = 'Salvo como rascunho — entra nos contadores e no Mapa Estratégico quando tiver um título.'

  const loading = ref(true)
  const error = ref<string | null>(null)
  const saveState = ref<'saving' | 'saved' | 'error'>('saved')
  const saveError = ref<string | null>(null)
  const savedAt = ref<Date | null>(null)
  const cycle = ref<OkrCycle | null>(null)

  /** Identidade local estável por linha: `id` só existe depois do primeiro save, e os índices
   * mudam de lugar quando um item é removido — usar `_uid` como :key evita o Vue reciclar
   * o input de outra linha (e roubar o foco) durante a edição. */
  let uidSeq = 0
  type KrRow = KeyResult & { _uid: number }
  type ObjRow = Omit<Objective, 'key_results'> & { _uid: number; key_results: KrRow[] }

  const form = ref<{
    nome: string
    tipo: OkrCycleTipo
    ano: number
    trimestre: number | null
    objectives: ObjRow[]
  }>({
    nome: '',
    tipo: 'trimestre',
    ano: new Date().getFullYear(),
    trimestre: null,
    objectives: [],
  })

  /** Contadores de geração: `editGen` avança a cada edição, `savedGen` guarda a geração que o
   * servidor já confirmou. Enquanto diferem, existe trabalho não gravado. */
  const editGen = ref(0)
  const savedGen = ref(0)
  const dirty = computed(() => editGen.value !== savedGen.value)

  /** Ligado enquanto o código (não o usuário) mexe no form, para não contar como edição. */
  let applyingRemote = false
  let autosaveTimer: number | null = null
  let inFlight: Promise<void> | null = null

  watch(
    form,
    () => {
      if (applyingRemote || loading.value) return
      editGen.value += 1
      scheduleSave()
    },
    { deep: true, flush: 'sync' }
  )

  function withRemoteChanges(fn: () => void) {
    applyingRemote = true
    try {
      fn()
    } finally {
      applyingRemote = false
    }
  }

  /** Metadados do ciclo (status, contadores) — nunca sobrescreve o que está sendo editado. */
  function applyCycleMeta(c: OkrCycle) {
    cycle.value = c
  }

  function loadForm(c: OkrCycle) {
    withRemoteChanges(() => {
      form.value = {
        nome: c.nome || '',
        tipo: c.tipo,
        ano: c.ano,
        trimestre: c.trimestre,
        objectives: (c.objectives || []).map((o) => ({
          ...o,
          _uid: ++uidSeq,
          key_results: (o.key_results || []).map((kr) => ({ ...kr, _uid: ++uidSeq })),
        })),
      }
    })
    editGen.value = 0
    savedGen.value = 0
  }

  /** Campo numérico vazio vale 0 no payload: o backend recusa `""` com 422 e travaria o save
   * inteiro enquanto o usuário estivesse com a Base/Meta em branco. */
  function toNum(value: unknown): number {
    const n = typeof value === 'number' ? value : Number(value)
    return Number.isFinite(n) ? n : 0
  }

  /** Ano apagado no meio da digitação (ou fora de 2020-2100) é recusado com 422 e travaria toda
   * a gravação — mantém o último ano válido até o usuário terminar de digitar. */
  function safeAno(): number {
    const n = toNum(form.value.ano)
    if (n >= 2020 && n <= 2100) return n
    return cycle.value?.ano ?? new Date().getFullYear()
  }

  type SentRow = { uid: number; krUids: number[] }

  /** Monta o PUT com tudo que está na tela — inclusive rascunho sem título, que o backend
   * guarda e mantém fora dos contadores — e devolve o mapa de linhas enviadas, para reatribuir
   * os ids gerados sem recarregar a tela. A resposta vem na mesma ordem, item a item. */
  function buildPayload(): { body: OkrCyclePayload; sent: SentRow[] } {
    const objectives: Objective[] = []
    const sent: SentRow[] = []
    for (const obj of form.value.objectives) {
      if (objectives.length >= MAX_OBJECTIVES) break
      const krs: KeyResult[] = []
      const krUids: number[] = []
      for (const kr of obj.key_results) {
        if (krs.length >= MAX_KRS) break
        krs.push({
          id: kr.id,
          titulo: kr.titulo,
          descricao: kr.descricao,
          unidade: kr.unidade,
          baseline: toNum(kr.baseline),
          current: toNum(kr.current),
          target: toNum(kr.target),
          direction: kr.direction,
          dono: kr.dono,
        })
        krUids.push(kr._uid)
      }
      objectives.push({
        id: obj.id,
        titulo: obj.titulo,
        descricao: obj.descricao,
        dono: obj.dono,
        pilar: obj.pilar,
        swot_id: obj.swot_id ?? null,
        swot_item_ids: [...(obj.swot_item_ids || [])],
        tows_ids: [...(obj.tows_ids || [])],
        key_results: krs,
      })
      sent.push({ uid: obj._uid, krUids })
    }
    return {
      body: {
        nome: form.value.nome,
        tipo: form.value.tipo,
        ano: safeAno(),
        trimestre: form.value.tipo === 'trimestre' ? form.value.trimestre : null,
        objectives,
      },
      sent,
    }
  }

  /** Copia só os ids que o servidor gerou; o texto na tela é a fonte da verdade enquanto edita. */
  function reconcileIds(updated: OkrCycle, sent: SentRow[]) {
    const objByUid = new Map(form.value.objectives.map((o) => [o._uid, o]))
    withRemoteChanges(() => {
      ;(updated.objectives || []).forEach((node, idx) => {
        const row = sent[idx]
        const local = row ? objByUid.get(row.uid) : undefined
        if (!row || !local) return
        local.id = node.id
        const krByUid = new Map(local.key_results.map((kr) => [kr._uid, kr]))
        ;(node.key_results || []).forEach((krNode, krIdx) => {
          const uid = row.krUids[krIdx]
          const localKr = uid === undefined ? undefined : krByUid.get(uid)
          if (localKr) localKr.id = krNode.id
        })
      })
    })
  }

  function clearAutosaveTimer() {
    if (autosaveTimer !== null) {
      window.clearTimeout(autosaveTimer)
      autosaveTimer = null
    }
  }

  function scheduleSave() {
    clearAutosaveTimer()
    autosaveTimer = window.setTimeout(() => {
      autosaveTimer = null
      void runSaves()
    }, AUTOSAVE_DELAY_MS)
  }

  async function putOnce(): Promise<boolean> {
    const gen = editGen.value
    const { body, sent } = buildPayload()
    try {
      const updated = await updateOkrCycle(cycleId.value, body)
      reconcileIds(updated, sent)
      applyCycleMeta(updated)
      savedGen.value = gen
      savedAt.value = new Date()
      return true
    } catch (e) {
      saveError.value = e instanceof Error ? e.message : 'Erro ao salvar.'
      return false
    }
  }

  /** Grava em série até a tela estar limpa; edições feitas durante o request entram na volta. */
  function runSaves(): Promise<void> {
    if (inFlight) return inFlight
    if (!cycleId.value || loading.value || !dirty.value) return Promise.resolve()
    inFlight = (async () => {
      saveState.value = 'saving'
      saveError.value = null
      try {
        while (dirty.value) {
          if (!(await putOnce())) {
            saveState.value = 'error'
            return
          }
        }
        saveState.value = 'saved'
      } finally {
        inFlight = null
      }
    })()
    return inFlight
  }

  /** Grava agora (botão, atalho, ações estruturais) sem esperar o debounce. */
  function saveNow(): Promise<void> {
    clearAutosaveTimer()
    return runSaves()
  }

  /** Espera a fila esvaziar — usada antes de sair da página ou mudar o status do ciclo. */
  async function flushSaves(): Promise<void> {
    clearAutosaveTimer()
    if (inFlight) await inFlight
    if (dirty.value) await runSaves()
  }

  const savedAtLabel = computed(() =>
    savedAt.value
      ? savedAt.value.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
      : ''
  )

  /** Progresso do KR calculado no cliente para feedback instantâneo — mesma fórmula do backend
   * (a direção só serve como rótulo; o cálculo se auto-inverte pelo sinal de target-baseline). */
  function krProgress(kr: { baseline: number; current: number; target: number }): number {
    const denom = toNum(kr.target) - toNum(kr.baseline)
    const raw = denom === 0 ? 100 : ((toNum(kr.current) - toNum(kr.baseline)) / denom) * 100
    return Math.max(0, Math.min(100, raw))
  }

  function isDraftObjective(obj: ObjRow): boolean {
    return !obj.titulo.trim()
  }

  function addObjective() {
    if (form.value.objectives.length >= MAX_OBJECTIVES) return
    form.value.objectives.push({
      _uid: ++uidSeq,
      titulo: '',
      descricao: '',
      dono: '',
      pilar: '',
      swot_id: null,
      swot_item_ids: [],
      tows_ids: [],
      key_results: [],
    })
  }

  function removeObjective(idx: number) {
    const obj = form.value.objectives[idx]
    if (!obj) return
    delete originOpen.value[obj._uid]
    form.value.objectives.splice(idx, 1)
    void saveNow()
  }

  function addKr(obj: ObjRow) {
    if (obj.key_results.length >= MAX_KRS) return
    obj.key_results.push({
      _uid: ++uidSeq,
      titulo: '',
      descricao: '',
      unidade: '',
      baseline: 0,
      current: 0,
      target: 100,
      direction: 'increase',
      dono: '',
    })
  }

  function removeKr(obj: ObjRow, idx: number) {
    obj.key_results.splice(idx, 1)
    void saveNow()
  }

  /** Ciclo trimestral sem trimestre é rejeitado com 400 — assume o trimestre corrente. */
  function onTipoChange() {
    if (form.value.tipo === 'trimestre' && !form.value.trimestre) {
      form.value.trimestre = Math.floor(new Date().getMonth() / 3) + 1
    }
  }

  function onSaveShortcut(ev: KeyboardEvent) {
    if (!(ev.metaKey || ev.ctrlKey) || ev.key.toLowerCase() !== 's') return
    ev.preventDefault()
    void saveNow()
  }

  function onBeforeUnload(ev: BeforeUnloadEvent) {
    if (!dirty.value && !inFlight) return
    ev.preventDefault()
    ev.returnValue = ''
  }

  /** Origem estratégica: iniciativas TOWS da SWOT vinculadas a cada Objective. */
  const TOWS_GROUPS: { field: SwotTowsField; label: string; hint: string }[] = [
    { field: 'tows_fo', label: 'F × O · Ofensiva', hint: 'Forças que capturam oportunidades' },
    { field: 'tows_fa', label: 'F × A · Defesa', hint: 'Forças que neutralizam ameaças' },
    { field: 'tows_fxo', label: 'f × O · Reforço', hint: 'Fraquezas que travam oportunidades' },
    { field: 'tows_fxa', label: 'f × A · Sobrevivência', hint: 'Vulnerabilidade encontra risco' },
  ]

  const swotList = ref<SwotAnalysisSummary[]>([])
  const swot = ref<SwotAnalysis | null>(null)
  const swotLoading = ref(false)
  const swotError = ref<string | null>(null)
  const originOpen = ref<Record<number, boolean>>({})

  const swotItemsById = computed(() => {
    const map = new Map<string, { texto: string }>()
    const doc = swot.value
    if (!doc) return map
    for (const field of ['forcas', 'fraquezas', 'oportunidades', 'ameacas'] as const) {
      for (const item of doc[field] || []) {
        map.set(item.id, { texto: item.texto })
      }
    }
    return map
  })

  function crossingLabel(initiative: SwotInitiative): string {
    const texts = [...(initiative.itens_internos || []), ...(initiative.itens_externos || [])]
      .map((id) => swotItemsById.value.get(id)?.texto)
      .filter((text): text is string => !!text)
    return texts.join(' × ')
  }

  function selectedInitiatives(obj: ObjRow) {
    const doc = swot.value
    if (!doc) return []
    const chosen = new Set(obj.tows_ids || [])
    return TOWS_GROUPS.flatMap((group) =>
      (doc[group.field] || [])
        .filter((initiative) => initiative.id && chosen.has(initiative.id))
        .map((initiative) => ({ ...initiative, groupLabel: group.label }))
    )
  }

  function isTowsSelected(obj: ObjRow, initiativeId?: string): boolean {
    return !!initiativeId && (obj.tows_ids || []).includes(initiativeId)
  }

  async function toggleTows(obj: ObjRow, initiativeId?: string) {
    if (!initiativeId || !swot.value) return
    const chosen = new Set(obj.tows_ids || [])
    if (chosen.has(initiativeId)) {
      chosen.delete(initiativeId)
    } else {
      if (chosen.size >= 20) {
        swotError.value = 'Máximo de 20 iniciativas por objetivo.'
        return
      }
      chosen.add(initiativeId)
    }
    swotError.value = null
    obj.tows_ids = [...chosen]
    obj.swot_id = obj.tows_ids.length ? swot.value.id : null
    await saveNow()
  }

  async function loadSwotDoc(id: string) {
    swotLoading.value = true
    try {
      swot.value = await getSwotAnalysisById(id)
    } catch (e) {
      swot.value = null
      swotError.value = e instanceof Error ? e.message : 'Falha ao carregar a SWOT.'
    } finally {
      swotLoading.value = false
    }
  }

  async function loadSwotList() {
    try {
      const list = await listSwotAnalyses()
      swotList.value = list.items
      const first = list.items[0]
      if (first) await loadSwotDoc(first.id)
    } catch (e) {
      swotError.value = e instanceof Error ? e.message : 'Falha ao listar as SWOTs.'
    }
  }

  async function onSelectSwot(event: Event) {
    const nextId = (event.target as HTMLSelectElement).value
    if (!nextId || nextId === swot.value?.id) return
    await loadSwotDoc(nextId)
  }

  const activating = ref(false)
  const archiving = ref(false)
  const lifecycleError = ref<string | null>(null)

  async function onActivate() {
    activating.value = true
    lifecycleError.value = null
    try {
      await flushSaves()
      applyCycleMeta(await activateOkrCycle(cycleId.value))
    } catch (e) {
      lifecycleError.value = e instanceof Error ? e.message : 'Erro ao ativar ciclo.'
    } finally {
      activating.value = false
    }
  }

  async function onArchive() {
    archiving.value = true
    lifecycleError.value = null
    try {
      await flushSaves()
      applyCycleMeta(await archiveOkrCycle(cycleId.value))
    } catch (e) {
      lifecycleError.value = e instanceof Error ? e.message : 'Erro ao arquivar ciclo.'
    } finally {
      archiving.value = false
    }
  }

  const STATUS_LABEL: Record<string, string> = {
    planejamento: 'Em planejamento',
    ativo: 'Ativo',
    encerrado: 'Encerrado',
  }

  onMounted(async () => {
    window.addEventListener('keydown', onSaveShortcut)
    window.addEventListener('beforeunload', onBeforeUnload)
    try {
      const c = await getOkrCycle(cycleId.value)
      applyCycleMeta(c)
      loadForm(c)
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Erro ao carregar ciclo.'
      if (String(error.value).includes('não encontrado')) {
        setTimeout(() => router.push('/okrs'), 1500)
      }
    } finally {
      loading.value = false
    }
    void loadSwotList()
  })

  onBeforeRouteLeave(async () => {
    await flushSaves()
  })

  onBeforeUnmount(() => {
    window.removeEventListener('keydown', onSaveShortcut)
    window.removeEventListener('beforeunload', onBeforeUnload)
    clearAutosaveTimer()
    if (dirty.value) void runSaves()
  })
  return {
    cycleId, loading, error, saveState, saveError, savedAtLabel, cycle, form, dirty,
    MAX_OBJECTIVES, MAX_KRS, DRAFT_HINT, TOWS_GROUPS, STATUS_LABEL,
    swotList, swot, swotLoading, swotError, originOpen,
    onTipoChange, addObjective, removeObjective, addKr, removeKr,
    toggleTows, isTowsSelected, onSelectSwot, saveNow, onActivate, onArchive,
    krProgress, isDraftObjective, crossingLabel, selectedInitiatives,
    activating, archiving, lifecycleError,
  }
}

export type OkrCycleEditor = ReturnType<typeof useOkrCycleEditor>
