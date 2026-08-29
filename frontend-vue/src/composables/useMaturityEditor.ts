import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  fetchMaturityModel,
  fetchMaturityResponseById,
  saveMaturityResponse,
  type MaturityDimension,
  type MaturityModel,
  type MaturityQuestion,
  type MaturityTier,
} from '@/api/maturity'
import { createSwotFromMaturity, getSwotByMaturityResponse } from '@/api/swotAnalysis'
import { useAutosave } from '@/composables/useAutosave'
import { MATURITY_DIMENSION_ACCENT, maturityDimensionAccent } from '@/lib/domain/maturity'
import {
  MATURITY_TIER_KEYS,
  MATURITY_TIER_LABEL_SHORT,
  MATURITY_DIMENSION_ABBR,
  tierIndexOf,
  naturalCompare,
  maturityOriginLine,
} from '@/lib/maturityModel'


export function useMaturityEditor() {
  const route = useRoute()
  const router = useRouter()
  const loading = ref(true)
  const error = ref<string | null>(null)
  const model = ref<MaturityModel | null>(null)
  const answers = ref<Record<string, number>>({})
  const selectedTier = ref<MaturityTier>('basico')
  const responseId = ref<string | null>(null)
  const isEditingExisting = computed(() => route.name === 'AiMaturityEdit')
  const editResponseId = computed(() =>
    isEditingExisting.value && typeof route.params.id === 'string' ? route.params.id : null
  )
  // AR-03: fila de gravação, debounce e guarda de saída vêm do composable
  // compartilhado — ver src/composables/useAutosave.ts.
  const autosave = useAutosave(async () => {
    const payload: Record<string, number> = { ...answers.value }
    const result = await saveMaturityResponse(payload, selectedTier.value, responseId.value)
    responseId.value = result.id
    // Nova avaliação: após o 1º save, passa a editar o mesmo registro na URL
    if (route.name === 'AiMaturityNew' && result.id) {
      await router.replace({ name: 'AiMaturityEdit', params: { id: result.id } })
    }
  })
  const saveState = autosave.saveState
  const saveError = autosave.error
  const swotId = ref<string | null>(null)
  const swotBusy = ref(false)
  const swotError = ref<string | null>(null)

  type EnrichedQuestion = MaturityQuestion & { dimId: string; dimName: string }

  const questionIndex = computed(() => {
    const idx: Record<string, EnrichedQuestion> = {}
    for (const dim of model.value?.dimensions ?? []) {
      for (const q of dim.questions ?? []) {
        idx[q.id] = { ...q, dimId: dim.id, dimName: dim.name }
      }
    }
    return idx
  })

  function isVisibleTier(tier: string): boolean {
    return tierIndexOf(tier) <= tierIndexOf(selectedTier.value)
  }

  function totalForTier(tier: MaturityTier): number {
    return model.value?.levels?.[tier]?.question_count ?? 0
  }

  function sortedQuestions(dim: MaturityDimension): MaturityQuestion[] {
    return [...(dim.questions ?? [])].sort((a, b) => naturalCompare(a.id, b.id))
  }

  const visibleQuestionIds = computed(() =>
    Object.keys(questionIndex.value).filter((id) => {
      const q = questionIndex.value[id]
      return !!q && isVisibleTier(q.tier)
    })
  )

  const answeredCount = computed(
    () => visibleQuestionIds.value.filter((id) => answers.value[id] != null).length
  )

  const totalVisible = computed(() => totalForTier(selectedTier.value))

  const isComplete = computed(
    () => totalVisible.value > 0 && answeredCount.value === totalVisible.value
  )

  const progressPct = computed(() =>
    totalVisible.value ? (answeredCount.value / totalVisible.value) * 100 : 0
  )

  const progressLabel = computed(() => {
    const answered = answeredCount.value
    const total = totalVisible.value
    if (answered === 0) return 'Nenhuma pergunta respondida ainda'
    if (answered === total) {
      const v = computeVerdict()
      return `Abrangência ${MATURITY_TIER_LABEL_SHORT[selectedTier.value]} concluída · ${v.sum}/${v.maxScore} pts · ${v.band.label}`
    }
    return `${total - answered} pergunta(s) restante(s) na abrangência ${MATURITY_TIER_LABEL_SHORT[selectedTier.value]}`
  })

  const selectedTierDescription = computed(() => {
    return model.value?.levels?.[selectedTier.value]?.description ?? ''
  })

  function dimVisibleQuestions(dim: MaturityDimension): MaturityQuestion[] {
    return (dim.questions ?? []).filter((q) => isVisibleTier(q.tier))
  }

  function dimAnswered(dim: MaturityDimension): MaturityQuestion[] {
    return dimVisibleQuestions(dim).filter((q) => answers.value[q.id] != null)
  }

  function dimAvg(dim: MaturityDimension): number | null {
    const answered = dimAnswered(dim)
    if (!answered.length) return null
    return answered.reduce((acc, q) => acc + Number(answers.value[q.id]), 0) / answered.length
  }

  function setTier(key: MaturityTier) {
    if (key === selectedTier.value) return
    selectedTier.value = key
    if (responseId.value || Object.keys(answers.value).length) {
      schedulePersist()
    }
  }

  function toggleSelect(qid: string, lvl: number) {
    if (answers.value[qid] === lvl) {
      const next = { ...answers.value }
      delete next[qid]
      answers.value = next
    } else {
      answers.value = { ...answers.value, [qid]: lvl }
    }
    schedulePersist()
  }

  /** Agenda a gravação (debounce de 280ms, como antes). Não cria registro
   * vazio: só entra na fila quando há modelo carregado e ao menos 1 resposta
   * (ou já existe um registro salvo para atualizar). */
  function schedulePersist() {
    if (!model.value) return
    if (!responseId.value && Object.keys(answers.value).length === 0) {
      saveState.value = 'idle'
      return
    }
    autosave.scheduleSave(280)
  }

  onMounted(async () => {
    try {
      model.value = await fetchMaturityModel()
      const existingId = editResponseId.value
      if (existingId) {
        const resp = await fetchMaturityResponseById(existingId)
        responseId.value = resp.id
        const tier = (resp.tier || 'basico') as MaturityTier
        selectedTier.value = MATURITY_TIER_KEYS.includes(tier) ? tier : 'basico'
        const loaded: Record<string, number> = {}
        for (const [qid, raw] of Object.entries(resp.answers || {})) {
          const n = Number(raw)
          if (Number.isFinite(n) && n >= 1 && n <= 5) loaded[qid] = n
        }
        answers.value = loaded
        await refreshSwotLink()
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Erro ao carregar modelo.'
    } finally {
      loading.value = false
    }
  })

  function computeVerdict() {
    const visibleAnswered = Object.keys(answers.value).filter((id) => {
      const q = questionIndex.value[id]
      return !!q && isVisibleTier(q.tier)
    })
    const sum = visibleAnswered.reduce((acc, c) => {
      const q = questionIndex.value[c]
      return acc + Number(answers.value[c]) * (q?.weight || 1)
    }, 0)
    const maxScore = model.value?.levels?.[selectedTier.value]?.max_score ?? totalVisible.value * 5
    const tierScoring = model.value?.scoring?.[selectedTier.value] ?? {}
    let band = { label: '—', description: '' }
    for (const key of ['level_1', 'level_2', 'level_3', 'level_4', 'level_5']) {
      const b = tierScoring[key]
      if (b && sum >= b.min && sum <= b.max) {
        band = { label: b.label ?? key, description: b.description ?? '' }
        break
      }
    }
    return { sum, maxScore, band }
  }

  async function refreshSwotLink() {
    swotError.value = null
    if (!responseId.value || !isComplete.value) {
      swotId.value = null
      return
    }
    try {
      const existing = await getSwotByMaturityResponse(responseId.value)
      swotId.value = existing.id
    } catch {
      swotId.value = null
    }
  }

  async function openSwot() {
    if (!isComplete.value || !responseId.value || swotBusy.value) return
    swotBusy.value = true
    swotError.value = null
    try {
      // Garante o rascunho salvo antes de gerar a SWOT
      await autosave.flush()
      if (!responseId.value) {
        throw new Error('Salve as respostas antes de criar a SWOT.')
      }
      // Cria ou regenera a partir das respostas atuais (upsert no backend)
      const created = await createSwotFromMaturity(responseId.value)
      swotId.value = created.id
      await router.push({ name: 'SwotAnalysis', params: { id: created.id } })
    } catch (e) {
      swotError.value = e instanceof Error ? e.message : 'Falha ao criar SWOT.'
    } finally {
      swotBusy.value = false
    }
  }

  watch([isComplete, responseId], () => {
    void refreshSwotLink()
  })

  function scrollToDim(idx: number) {
    document.getElementById(`dim-${idx}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  function onCellKeydown(e: KeyboardEvent, qid: string, lvl: number) {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      toggleSelect(qid, lvl)
    }
  }
  return {
    loading, error, model, answers, selectedTier, responseId, isEditingExisting,
    saveState, saveError, swotId, swotBusy, swotError,
    questionIndex, visibleQuestionIds, answeredCount, totalVisible, isComplete,
    progressPct, progressLabel, selectedTierDescription,
  MATURITY_TIER_KEYS, MATURITY_TIER_LABEL_SHORT, MATURITY_DIMENSION_ACCENT, MATURITY_DIMENSION_ABBR,
  isVisibleTier, sortedQuestions, maturityOriginLine, maturityDimensionAccent,
  dimVisibleQuestions, dimAnswered, dimAvg, setTier, toggleSelect,
  openSwot, scrollToDim, onCellKeydown,

  }
}

export type MaturityEditor = ReturnType<typeof useMaturityEditor>
