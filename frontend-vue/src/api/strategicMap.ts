import { get } from './client'
import type { SwotListField, SwotTowsField, SwotWatchlistItem } from './swotAnalysis'
import type { CanvasQuadrant } from './canvasProjects'

/** Projeto (canvas) pendurado em um item SWOT ou em uma iniciativa TOWS. */
export interface StrategicMapProject {
  id: string
  title: string
  area_negocio: string
  quadrant: CanvasQuadrant
  score_valor: number | null
  score_viabilidade: number | null
  proximo_passo: string
  updated_at: string | null
}

export interface StrategicMapOrphanProject extends StrategicMapProject {
  /** Aponta para a SWOT exibida, mas sem item/iniciativa de origem. */
  linked_to_swot: boolean
}

export interface StrategicMapCounterpart {
  id: string
  quadrant: SwotListField | null
  texto: string
}

export interface StrategicMapInitiative {
  id: string
  field: SwotTowsField
  acao: string
  dono: string
  horizonte: string
  itens_internos: string[]
  counterparts: StrategicMapCounterpart[]
  projects: StrategicMapProject[]
}

export interface StrategicMapItem {
  id: string
  quadrant: SwotListField
  texto: string
  pilar: string
  question_id: string
  impacto: number | null
  viabilidade: number | null
  probabilidade: number | null
  evidencia: string
  prioridade: number | null
  tows: boolean
  initiatives: StrategicMapInitiative[]
  /** Quantas estratégias TOWS usam este item como contraparte externa. */
  used_in: number
  projects: StrategicMapProject[]
}

export interface StrategicMapQuestion {
  id: string
  text: string
  tier: string
  answer: number
  answer_text: string
  swot_category: string | null
  items: StrategicMapItem[]
  watchlist: SwotWatchlistItem[]
}

export interface StrategicMapDimension {
  id: string
  name: string
  pilar: string
  score: { score: number; max: number; avg: number; pct: number }
  questions: StrategicMapQuestion[]
}

/** Autoavaliação disponível para navegar no mapa. */
export interface StrategicMapSource {
  maturity_response_id: string | null
  swot_id: string | null
  assessment_title: string
  tier: string | null
  tier_label: string | null
  submitted_at: string | null
  complete: boolean
  percent_score: number
  level_label: string
}

export interface StrategicMapHead {
  maturity_response_id: string | null
  swot_id: string | null
  assessment_title: string
  tier: string | null
  tier_label: string | null
  submitted_at: string | null
  complete: boolean
  result: {
    total_score: number
    max_score: number
    percent_score: number
    level_label: string
    level_description: string
  } | null
  optica: string
  veredito_tipo: string
  veredito_titulo: string
  veredito_texto: string
  swot_updated_at: string | null
}

export interface StrategicMap {
  source: StrategicMapHead
  sources: StrategicMapSource[]
  dimensions: StrategicMapDimension[]
  unlinked: {
    swot_items: StrategicMapItem[]
    initiatives: StrategicMapInitiative[]
    watchlist: SwotWatchlistItem[]
    projects: StrategicMapOrphanProject[]
  }
  stats: {
    dimensions: number
    questions: number
    swot_items: number
    watchlist: number
    initiatives: number
    projects_total: number
    projects_linked: number
  }
}

/** Árvore de rastreabilidade maturidade → SWOT → TOWS → projetos. */
export function fetchStrategicMap(params?: {
  maturityResponseId?: string | null
  swotId?: string | null
}): Promise<StrategicMap> {
  const query = new URLSearchParams()
  if (params?.swotId) query.set('swot_id', params.swotId)
  else if (params?.maturityResponseId) query.set('maturity_response_id', params.maturityResponseId)
  const suffix = query.toString() ? `?${query.toString()}` : ''
  return get<StrategicMap>(`/api/strategic-map${suffix}`)
}
