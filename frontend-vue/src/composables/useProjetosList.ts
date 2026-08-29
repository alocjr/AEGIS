import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  listCanvasProjects,
  createCanvasProject,
  deleteCanvasProject,
  importCanvasProjects,
  aprovarPortfolio,
  type CanvasProjectSummary,
  type CanvasImportDocument,
} from '@/api/canvasProjects'
import { CANVAS_QUADRANT_LABEL } from '@/lib/domain/canvas'
import {
  PORTFOLIO_PLOT,
  PORTFOLIO_VIEWBOX,
  buildPortfolioPlotPoints,
  type PortfolioPlotPoint,
} from '@/lib/portfolioPlot'
import { clip } from '@/lib/mapHelpers'

function clipText(text: string, max = 180): string {
  return clip(text, max)
}

export function useProjetosList() {
  const router = useRouter()
  const loading = ref(true)
  const creating = ref(false)
  const error = ref<string | null>(null)
  const items = ref<CanvasProjectSummary[]>([])
  const deleteTarget = ref<CanvasProjectSummary | null>(null)
  const deleteError = ref<string | null>(null)
  const importState = ref<'idle' | 'importing' | 'ok' | 'error'>('idle')
  const importError = ref<string | null>(null)
  const importOkMsg = ref('')
  const fileInput = ref<HTMLInputElement | null>(null)

  const scoredItems = computed(() =>
    items.value.filter(
      (i) => i.score_valor != null && i.score_viabilidade != null && i.quadrant != null
    )
  )

  const plotPoints = computed(() => buildPortfolioPlotPoints(scoredItems.value))

  const unscoredCount = computed(() => items.value.length - scoredItems.value.length)

  function formatDate(iso: string | null): string {
    if (!iso) return '—'
    try {
      return new Date(iso).toLocaleString('pt-BR', {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      })
    } catch {
      return iso
    }
  }

  const hoverPoint = ref<PortfolioPlotPoint | null>(null)
  const tooltipPos = ref({ x: 0, y: 0 })
  const tooltipRef = ref<HTMLElement | null>(null)
  const TOOLTIP_GAP = 14

  function hideChartTooltip() {
    hoverPoint.value = null
  }

  function openProject(id: string) {
    hideChartTooltip()
    void router.push(`/projetos/${id}`)
  }

  function showChartTooltip(ev: MouseEvent, p: PortfolioPlotPoint) {
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

  async function refresh() {
    const res = await listCanvasProjects()
    items.value = res.items ?? []
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
    if (!file) return

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
      const result = await importCanvasProjects(doc)
      await refresh()
      importState.value = 'ok'
      importOkMsg.value = `${result.created} projeto${result.created === 1 ? '' : 's'} importado${result.created === 1 ? '' : 's'}.`
      window.setTimeout(() => {
        if (importState.value === 'ok') importState.value = 'idle'
      }, 3500)
    } catch (e) {
      importState.value = 'error'
      importError.value = e instanceof Error ? e.message : 'Falha na importação.'
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

  return {
    loading,
    creating,
    error,
    items,
    deleteTarget,
    deleteError,
    importState,
    importError,
    importOkMsg,
    fileInput,
    scoredItems,
    plotPoints,
    unscoredCount,
    hoverPoint,
    tooltipPos,
    tooltipRef,
    approvingId,
    approveError,
    CANVAS_QUADRANT_LABEL,
    PORTFOLIO_PLOT,
    PORTFOLIO_VIEWBOX,
    formatDate,
    clipText,
    openProject,
    showChartTooltip,
    placeChartTooltip,
    hideChartTooltip,
    onCreate,
    openImportPicker,
    onImportFile,
    askDelete,
    cancelDelete,
    onApprovePortfolio,
    confirmDelete,
  }
}

export type ProjetosListEditor = ReturnType<typeof useProjetosList>
