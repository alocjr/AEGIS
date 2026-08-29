import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  fetchMaturityModel,
  fetchMaturityResponseById,
  fetchMaturityResponseExport,
  type MaturityModel,
  type MaturityResult,
  type MaturityTier,
} from '@/api/maturity'
import {
  createSwotFromMaturity,
  getSwotByMaturityResponse,
} from '@/api/swotAnalysis'
import { maturityDimensionAccent } from '@/lib/domain/maturity'
import { MATURITY_TIER_LABEL_SHORT } from '@/lib/maturityModel'

type DimRow = {
  id: string
  name: string
  score: number
  max: number
  avg: number
  pct: number
  accent: string
  initials: string
}

export function useMaturityDetail() {
const route = useRoute()
const router = useRouter()
const responseId = route.params.id as string

const loading = ref(true)
const error = ref<string | null>(null)
const model = ref<MaturityModel | null>(null)
const displayedResult = ref<MaturityResult | null>(null)
const submittedAt = ref<string | null>(null)
const swotId = ref<string | null>(null)
const swotBusy = ref(false)
const swotError = ref<string | null>(null)
const isComplete = ref(false)
const exportBusy = ref(false)
const exportError = ref<string | null>(null)

const RADAR_CX = 100
const RADAR_CY = 100
const RADAR_R = 68
const RADAR_LABEL_R = 88

function getInitials(name: string): string {
  const words = name.trim().split(/\s+/).filter(Boolean)
  if (!words.length) return '?'
  const a = words[0]?.[0] ?? ''
  const b = words[1]?.[0] ?? ''
  return (a + b).toUpperCase().slice(0, 2) || '?'
}

function getLevelByScore(score: number): { label?: string; description?: string } | null {
  const m = model.value
  const tier = displayedResult.value?.tier
  const bands =
    (tier && m?.scoring?.[tier as MaturityTier]) || m?.scoring?.basico
  if (!bands) return null
  for (const k of Object.keys(bands)) {
    const it = bands[k]
    if (it && score >= it.min && score <= it.max) return it
  }
  return null
}

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

const levelInfo = computed(() => {
  const result = displayedResult.value
  if (!result) return { label: '—', description: '' }
  return (
    result.level ??
    getLevelByScore(result.total_score) ?? { label: '—', description: '' }
  )
})

const tierLabel = computed(() => {
  const tier = displayedResult.value?.tier
  if (!tier) return null
  return MATURITY_TIER_LABEL_SHORT[tier as MaturityTier] || tier
})

const dimRows = computed<DimRow[]>(() => {
  const result = displayedResult.value
  const dims = model.value?.dimensions ?? []
  if (!result || !dims.length) return []
  return dims.map((dim) => {
    const ds = result.dimension_scores?.[dim.id] || {
      name: dim.name,
      score: 0,
      max: 0,
      avg: 0,
    }
    const max = ds.max || 0
    const score = ds.score || 0
    const pct = max ? Math.round((score / max) * 100) : 0
    return {
      id: dim.id,
      name: ds.name || dim.name,
      score,
      max,
      avg: ds.avg ?? 0,
      pct,
      accent: maturityDimensionAccent(dim.id),
      initials: getInitials(ds.name || dim.name),
    }
  })
})

const strongest = computed(() => {
  if (!dimRows.value.length) return null
  return dimRows.value.reduce((a, b) => (b.avg > a.avg ? b : a))
})

const weakest = computed(() => {
  if (!dimRows.value.length) return null
  return dimRows.value.reduce((a, b) => (b.avg < a.avg ? b : a))
})

/** Anel SVG: circunferência com r=54 */
const RING_R = 54
const RING_C = 2 * Math.PI * RING_R
const ringOffset = computed(() => {
  const pct = Math.min(100, Math.max(0, displayedResult.value?.percent_score ?? 0))
  return RING_C * (1 - pct / 100)
})

function radarPoint(i: number, n: number, pct: number): { x: number; y: number } {
  const angle = -Math.PI / 2 + (2 * Math.PI * i) / n
  const r = (pct / 100) * RADAR_R
  return {
    x: RADAR_CX + r * Math.cos(angle),
    y: RADAR_CY + r * Math.sin(angle),
  }
}

function radarAxisEnd(i: number, n: number): { x: number; y: number } {
  const angle = -Math.PI / 2 + (2 * Math.PI * i) / n
  return {
    x: RADAR_CX + RADAR_R * Math.cos(angle),
    y: RADAR_CY + RADAR_R * Math.sin(angle),
  }
}

function radarLabelPos(i: number, n: number): { x: number; y: number } {
  const angle = -Math.PI / 2 + (2 * Math.PI * i) / n
  return {
    x: RADAR_CX + RADAR_LABEL_R * Math.cos(angle),
    y: RADAR_CY + RADAR_LABEL_R * Math.sin(angle),
  }
}

const radarPolygon = computed(() => {
  const rows = dimRows.value
  if (!rows.length) return ''
  return rows
    .map((d, i) => {
      const p = radarPoint(i, rows.length, d.pct)
      return `${p.x},${p.y}`
    })
    .join(' ')
})

const gridRings = [0.2, 0.4, 0.6, 0.8, 1]

async function openSwot() {
  if (!responseId || swotBusy.value) return
  swotBusy.value = true
  swotError.value = null
  try {
    if (swotId.value) {
      await router.push({ name: 'SwotAnalysis', params: { id: swotId.value } })
      return
    }
    const created = await createSwotFromMaturity(responseId)
    swotId.value = created.id
    await router.push({ name: 'SwotAnalysis', params: { id: created.id } })
  } catch (e) {
    swotError.value = e instanceof Error ? e.message : 'Falha ao criar SWOT.'
  } finally {
    swotBusy.value = false
  }
}

/** Baixa a autoavaliação como JSON (envelope aegis.maturidade-ia). */
async function exportJson() {
  if (!responseId || exportBusy.value) return
  exportBusy.value = true
  exportError.value = null
  try {
    const doc = await fetchMaturityResponseExport(responseId)
    const stamp = (doc.payload.respondido_em || doc.exported_at || '').slice(0, 10)
    const blob = new Blob([JSON.stringify(doc, null, 2)], {
      type: 'application/json;charset=utf-8',
    })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `maturidade-ia${stamp ? `-${stamp}` : ''}.json`
    a.click()
    URL.revokeObjectURL(url)
  } catch (e) {
    exportError.value = e instanceof Error ? e.message : 'Falha ao exportar JSON.'
  } finally {
    exportBusy.value = false
  }
}

onMounted(async () => {
  if (!responseId) {
    error.value = 'Resposta não encontrada.'
    loading.value = false
    return
  }
  try {
    const [mod, resp] = await Promise.all([
      fetchMaturityModel(),
      fetchMaturityResponseById(responseId),
    ])
    model.value = mod
    displayedResult.value = resp.result ?? null
    submittedAt.value = resp.submitted_at ?? null
    isComplete.value = resp.complete === true
    error.value = null
    if (isComplete.value) {
      try {
        const existing = await getSwotByMaturityResponse(responseId)
        swotId.value = existing.id
      } catch {
        swotId.value = null
      }
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Resposta não encontrada.'
  } finally {
    loading.value = false
  }
})

  return {
    responseId,
    loading,
    error,
    model,
    displayedResult,
    submittedAt,
    swotId,
    swotBusy,
    swotError,
    isComplete,
    exportBusy,
    exportError,
    levelInfo,
    tierLabel,
    dimRows,
    strongest,
    weakest,
    RING_R,
    RING_C,
    ringOffset,
    RADAR_CX,
    RADAR_CY,
    RADAR_R,
    RADAR_LABEL_R,
    gridRings,
    radarPolygon,
    formatDate,
    radarPoint,
    radarAxisEnd,
    radarLabelPos,
    openSwot,
    exportJson,
  }
}

export type MaturityDetailEditor = ReturnType<typeof useMaturityDetail>
