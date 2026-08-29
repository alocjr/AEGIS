import { ref, computed, onMounted } from 'vue'
import { fetchCurrentCourse } from '@/api/course'
import { updateMaterialCheck, completeEncontro } from '@/api/progress'
import { useAuthStore } from '@/stores/auth'
import { ApiError } from '@/api/client'
import type { CurrentCourseResponse } from '@/api/course'
import type {
  Encontro,
  ProgramaFormacaoExecutiva,
} from '@/api/courses'
import { romano, isExternalUrl, parseMatItem } from '@/lib/programaHelpers'

export function usePrograma() {
  const auth = useAuthStore()
  const loading = ref(true)
  const error = ref<string | null>(null)
  const noTrilha = ref(false)
  const data = ref<CurrentCourseResponse | null>(null)
  const expandedId = ref<number | null>(null)
  const expandedSemana = ref<number | null>(null)
  const completingId = ref<number | null>(null)
  const materialToggling = ref<string | null>(null)
  const selectingAllId = ref<number | null>(null)
  const hoverStep = ref<{ enc: Encontro; semana: number } | null>(null)

  const programa = computed<ProgramaFormacaoExecutiva | undefined>(() => {
    const p = data.value?.programa_formacao_executiva
    return p as ProgramaFormacaoExecutiva | undefined
  })

  const progress = computed(() => data.value?.progress ?? null)

  const liberados = computed(() => progress.value?.encontros_liberados ?? [1])

  const concluidosEfetivos = computed(() => progress.value?.concluidos_efetivos ?? [])

  const ativoEfetivo = computed(() => progress.value?.ativo_efetivo ?? 1)

  const materialChecks = computed(
    () => (progress.value?.material_checks ?? {}) as Record<string, Record<string, boolean>>
  )

  const jornada = computed(() => programa.value?.jornada_aprendizagem ?? [])

  const totalEncontros = computed(() =>
    jornada.value.reduce((acc, sem) => acc + (sem.encontros?.length ?? 0), 0)
  )

  const numSemanas = computed(() => jornada.value.length)

  const metodologia = computed(() => programa.value?.metodologia_detalhada)

  const entregaveisResumo = computed(() => programa.value?.entregaveis_resumo ?? [])

  type EncStatus = 'done' | 'active' | 'locked'

  const instSteps = computed(() =>
    (jornada.value ?? []).flatMap((sem) =>
      (sem.encontros ?? []).map((enc) => ({ semana: sem.semana, enc }))
    )
  )

  /** Status do encontro: usa encontros_liberados para definir o que está acessível (check de materiais e Quiz). */
  function statusEnc(enc: Encontro): EncStatus {
    if (concluidosEfetivos.value.includes(enc.id)) return 'done'
    if (liberados.value.includes(enc.id)) return 'active'
    return 'locked'
  }

  function podeClicarConcluir(enc: Encontro): boolean {
    const materiaisOk = (enc.material_suporte ?? []).length <= Object.keys(materialChecks.value[String(enc.id)] ?? {}).length
    return materiaisOk
  }

  /** Apenas o encontro ativo é editável (marcar/desmarcar materiais, concluir). */
  function isEncontroEditavel(enc: Encontro): boolean {
    return statusEnc(enc) === 'active'
  }

  /** Encontros ativo ou concluído: mesma aparência (fundo claro) e permitem abrir links e quiz. */
  function isEncontroAcessivel(enc: Encontro): boolean {
    return statusEnc(enc) === 'active' || statusEnc(enc) === 'done'
  }

  const progressPct = computed(() => {
    const done = concluidosEfetivos.value.length
    const tot = (progress.value?.total ?? totalEncontros.value) || 1
    return tot ? Math.round((done / tot) * 100) : 0
  })

  const sidebarFacts = computed(() => {
    const done = concluidosEfetivos.value.length
    const tot = progress.value?.total ?? totalEncontros.value
    return [
      [numSemanas.value + ' sem.', 'Duração', ''],
      ['2x/sem.', 'Frequência', ''],
      [done + '/' + tot, 'Progresso', 'g'],
      [entregaveisResumo.value.length, 'Entregáveis', ''],
    ]
  })

  const nextEncontro = computed(() => {
    let found: { enc: Encontro; sem: number } | null = null
    for (const sem of jornada.value) {
      for (const enc of sem.encontros ?? []) {
        if (enc.id === ativoEfetivo.value) {
          found = { enc, sem: sem.semana }
          break
        }
      }
      if (found) break
    }
    return found
  })

  const metricsRows = computed(() => {
    const done = concluidosEfetivos.value.length
    const tot = (progress.value?.total ?? totalEncontros.value) || 1
    const pctAll = Math.round((done / tot) * 100)
    const semAtual = Math.ceil(ativoEfetivo.value / 2)
    let pctSem = 0
    const sem = jornada.value.find((s) => s.semana === semAtual)
    if (sem?.encontros) {
      let totalMat = 0
      let doneMat = 0
      for (const enc of sem.encontros) {
        const n = (enc.material_suporte ?? []).length
        totalMat += n
        const encChecks = materialChecks.value[String(enc.id)] ?? {}
        for (let i = 0; i < n; i++) if (encChecks[String(i)]) doneMat += 1
      }
      pctSem = totalMat > 0 ? Math.round((doneMat / totalMat) * 100) : 0
    }
    return [
      { lbl: 'Programa', pct: pctAll, color: 'var(--gold)' },
      { lbl: 'Semana ' + semAtual, pct: pctSem, color: 'rgba(255,255,255,.45)' },
    ]
  })

  const ribbonShow = ref(false)
  const ribbonMsg = ref('')

  function jumpTo(encId: number) {
    const el = document.getElementById(`enc${encId}`)
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  /** Apenas uma semana pode estar aberta no menu; ao abrir outra, esta fecha. */
  function toggleNavCh(semana: number) {
    expandedSemana.value = expandedSemana.value === semana ? null : semana
  }

  function isMaterialChecked(encId: number, matIndex: number): boolean {
    const enc = materialChecks.value[String(encId)]
    return enc ? Object.prototype.hasOwnProperty.call(enc, String(matIndex)) : false
  }

  function allMateriaisChecked(enc: Encontro): boolean {
    const total = (enc.material_suporte ?? []).length
    if (total === 0) return false
    const checks = materialChecks.value[String(enc.id)] ?? {}
    return Object.keys(checks).length >= total
  }

  async function onSelectAllMateriais(enc: Encontro) {
    const materials = enc.material_suporte ?? []
    if (materials.length === 0) return
    selectingAllId.value = enc.id
    const checkAll = !allMateriaisChecked(enc)
    const slug = auth.currentCourseSlug ?? undefined
    try {
      for (let i = 0; i < materials.length; i++) {
        await updateMaterialCheck({ encontro_id: enc.id, material_index: i, checked: checkAll, course_slug: slug })
      }
      await loadProgram()
    } catch {
      await loadProgram()
    } finally {
      selectingAllId.value = null
    }
  }

  function entregavelParaEncontro(encId: number) {
    return entregaveisResumo.value.find((e) => e.origem === `Encontro ${encId}`)
  }

  function toggleExpand(enc: Encontro) {
    expandedId.value = expandedId.value === enc.id ? null : enc.id
  }

  async function onMaterialToggle(encId: number, matIndex: number, checked: boolean) {
    const key = `${encId}-${matIndex}`
    materialToggling.value = key
    const slug = auth.currentCourseSlug ?? undefined
    try {
      await updateMaterialCheck({ encontro_id: encId, material_index: matIndex, checked, course_slug: slug })
      await loadProgram()
    } catch {
      // revert would need local state; on next load it will be correct
    } finally {
      materialToggling.value = null
    }
  }

  async function onCompleteEncontro(encId: number) {
    completingId.value = encId
    try {
      await completeEncontro(encId, auth.currentCourseSlug ?? undefined)
      await loadProgram()
      expandedId.value = null
      ribbonMsg.value = 'Encontro concluído com sucesso. Progresso atualizado.'
      ribbonShow.value = true
      window.scrollTo({ top: 0, behavior: 'smooth' })
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Erro ao concluir encontro.'
    } finally {
      completingId.value = null
    }
  }

  async function loadProgram() {
    loading.value = true
    error.value = null
    noTrilha.value = false
    try {
      data.value = await fetchCurrentCourse(auth.currentCourseSlug ?? undefined)
      if (expandedId.value === null && progress.value?.ativo_efetivo) {
        expandedId.value = progress.value.ativo_efetivo
      }
    } catch (e) {
      if (e instanceof ApiError && e.code === 'NO_TRILHA_ASSIGNED') {
        noTrilha.value = true
      } else {
        error.value = e instanceof Error ? e.message : 'Erro ao carregar programa.'
      }
      data.value = null
    } finally {
      loading.value = false
    }
  }

  onMounted(() => loadProgram())
  return {
    loading, error, noTrilha, data, expandedId, expandedSemana, completingId,
    materialToggling, selectingAllId, hoverStep, programa, progress, liberados,
    concluidosEfetivos, ativoEfetivo, materialChecks, jornada, totalEncontros,
    numSemanas, metodologia, entregaveisResumo, instSteps, progressPct, sidebarFacts,
    nextEncontro, metricsRows, ribbonShow, ribbonMsg,
    statusEnc, podeClicarConcluir, isEncontroEditavel, isEncontroAcessivel,
    jumpTo, toggleNavCh, isMaterialChecked, allMateriaisChecked, onSelectAllMateriais,
    entregavelParaEncontro, toggleExpand, onMaterialToggle, onCompleteEncontro,
    romano, isExternalUrl, parseMatItem,
  }
}

export type ProgramaEditor = ReturnType<typeof usePrograma>
