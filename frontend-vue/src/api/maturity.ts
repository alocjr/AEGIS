import { get, post } from './client'

export interface MaturityDimension {
  id: string
  name: string
  questions: { id: string; text: string; weight?: number }[]
}

export interface MaturityModel {
  assessment_title?: string
  version?: string
  dimensions?: MaturityDimension[]
  answer_scale?: { value: number; label: string; context?: string }[]
  scoring_logic?: Record<string, { min: number; max: number; label?: string; description?: string }>
}

export interface MaturityResult {
  total_score: number
  max_score: number
  percent_score: number
  dimension_scores?: Record<string, { name: string; score: number; max: number; avg: number }>
  level?: { label?: string; description?: string }
}

export interface MaturityMyResponse {
  answers: Record<string, number>
  submitted_at: string | null
  result: MaturityResult | null
}

/** Item resumido na lista de autoavaliações */
export interface MaturityResponseListItem {
  id: string
  submitted_at: string | null
  result: {
    total_score: number
    max_score: number
    percent_score: number
    level?: { label?: string; description?: string }
    dimension_scores?: Record<string, { name: string; score: number; max: number; avg: number }>
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

export function saveMaturityResponse(answers: Record<string, number>): Promise<{ id: string; submitted_at: string; result: MaturityResult }> {
  return post<{ id: string; submitted_at: string; result: MaturityResult }>('/api/maturity/my-response', { answers })
}
