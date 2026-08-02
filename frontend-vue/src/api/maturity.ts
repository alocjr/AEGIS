import { get, post } from './client'

export type MaturityTier = 'basico' | 'completo' | 'complementar'

export interface MaturityQuestion {
  id: string
  tier: MaturityTier
  text: string
  weight?: number
  originType?: string
  csfId?: string | null
  csfName?: string | null
  ref?: string | null
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
