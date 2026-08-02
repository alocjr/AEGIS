import { get, post } from './client'

export type MaturityTier = 'basico' | 'completo' | 'complementar'

export type MaturitySwotCategory =
  | 'internal_capability'
  | 'market_strategy'
  | 'risk_compliance'
  | string

export interface MaturitySwotScoreRule {
  quadrants: string[]
  opportunity_label?: string
  threat_label?: string
  threat_mitigated?: boolean
}

export interface MaturitySwotCategoryConfig {
  label?: string
  rationale?: string
  score_rules?: Record<string, MaturitySwotScoreRule>
}

export interface MaturitySwotFramework {
  description?: string
  categories?: Record<string, MaturitySwotCategoryConfig>
  aggregation_logic?: string[]
  labels_note?: string
}

export interface MaturityTowsQuadrantConfig {
  label?: string
  type?: string
  rationale?: string
  trigger?: string
}

export interface MaturityTowsFramework {
  description?: string
  quadrants?: Record<string, MaturityTowsQuadrantConfig>
  generation_logic?: string[]
  pairing_note?: string
  opportunity_sources?: string[]
  threat_sources?: string[]
}

export interface MaturityQuestion {
  id: string
  tier: MaturityTier
  text: string
  weight?: number
  originType?: string
  csfId?: string | null
  csfName?: string | null
  ref?: string | null
  /** Categoria-ponte do swotFramework (modelo v3+). */
  swotCategory?: MaturitySwotCategory | null
  /** Texto pronto por quadrante SWOT (strength, weakness, opportunity, threat, watchlist). */
  swotLabels?: Partial<Record<string, string>> | null
  /** Estratégias TOWS ancoradas na pergunta (SO, ST, WO, WT). */
  towsLabels?: Partial<Record<'SO' | 'ST' | 'WO' | 'WT' | string, string>> | null
  levels: Record<string, string>
}

export interface MaturityDimension {
  id: string
  name: string
  questions: MaturityQuestion[]
}

export interface MaturityTierConfig {
  label: string
  description?: string
  question_count: number
  max_score: number
}

export interface MaturityScoreBand {
  min: number
  max: number
  label?: string
  description?: string
}

export interface MaturityOverlap {
  pair: [string, string] | string[]
  distinction: string
}

export interface MaturityModel {
  id?: string
  assessment_title?: string
  title?: string
  version?: string
  levels?: Record<MaturityTier, MaturityTierConfig>
  dimensions?: MaturityDimension[]
  scoring?: Record<MaturityTier, Record<string, MaturityScoreBand>>
  overlaps?: MaturityOverlap[]
  /** Regras de agregação pergunta → quadrantes SWOT. */
  swotFramework?: MaturitySwotFramework
  /** Regras de geração da matriz TOWS a partir do SWOT. */
  towsFramework?: MaturityTowsFramework
}

export interface MaturityResult {
  total_score: number
  max_score: number
  percent_score: number
  dimension_scores?: Record<string, { name: string; score: number; max: number; avg: number }>
  level?: { label?: string; description?: string }
  tier?: MaturityTier | string
}

export interface MaturityMyResponse {
  answers: Record<string, number>
  model_id?: string | null
  tier?: MaturityTier | string
  submitted_at: string | null
  result: MaturityResult | null
  complete?: boolean
}

/** Item resumido na lista de autoavaliações */
export interface MaturityResponseListItem {
  id: string
  model_id?: string
  submitted_at: string | null
  tier?: MaturityTier | string
  result: {
    total_score: number
    max_score: number
    percent_score: number
    level?: { label?: string; description?: string }
    dimension_scores?: Record<string, { name: string; score: number; max: number; avg: number }>
    tier?: MaturityTier | string
  }
}

export interface MaturityResponsesList {
  items: MaturityResponseListItem[]
}

export function fetchMaturityModel(): Promise<MaturityModel> {
  return get<MaturityModel>('/api/maturity/model')
}

export function fetchMyMaturityResponses(): Promise<MaturityResponsesList> {
  return get<MaturityResponsesList>('/api/maturity/my-responses')
}

export function fetchMaturityResponseById(id: string): Promise<MaturityMyResponse & { id: string }> {
  return get<MaturityMyResponse & { id: string }>(`/api/maturity/my-responses/${encodeURIComponent(id)}`)
}

export function saveMaturityResponse(
  answers: Record<string, number>,
  tier: MaturityTier = 'basico',
  responseId?: string | null
): Promise<{
  id: string
  model_id?: string
  submitted_at: string
  result: MaturityResult
  tier?: string
  complete?: boolean
}> {
  return post<{
    id: string
    model_id?: string
    submitted_at: string
    result: MaturityResult
    tier?: string
    complete?: boolean
  }>('/api/maturity/my-response', {
    answers,
    tier,
    response_id: responseId || undefined,
  })
}
