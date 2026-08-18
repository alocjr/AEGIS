import { del, get, post, put } from './client'

export type OkrCycleTipo = 'trimestre' | 'ano'
export type OkrCycleStatus = 'planejamento' | 'ativo' | 'encerrado'
export type OkrDirection = 'increase' | 'decrease'

export interface KeyResult {
  id?: string
  titulo: string
  descricao: string
  unidade: string
  baseline: number
  current: number
  target: number
  direction: OkrDirection
  dono: string
}

/** KeyResult com progresso calculado pelo backend (nunca editar estes dois campos). */
export interface KeyResultNode extends KeyResult {
  id: string
  progress_pct: number
  progress_pct_raw: number
}

export interface Objective {
  id?: string
  titulo: string
  descricao: string
  dono: string
  pilar: string
  /** Origem estratégica: mesmo shape do Canvas (swot_id/swot_item_ids/tows_ids). */
  swot_id?: string | null
  swot_item_ids?: string[]
  tows_ids?: string[]
  key_results: KeyResult[]
}

export interface ObjectiveNode extends Omit<Objective, 'key_results'> {
  id: string
  swot_id: string | null
  swot_item_ids: string[]
  tows_ids: string[]
  key_results: KeyResultNode[]
  /** Média dos progress_pct dos KRs; null se o Objective não tem KR. */
  progress_pct: number | null
}

export interface OkrCycleSummary {
  id: string
  tipo: OkrCycleTipo
  ano: number
  trimestre: number | null
  nome: string
  label: string
  status: OkrCycleStatus
  /** Contagens só do que está publicado (com título); rascunhos ficam em `drafts_count`. */
  objectives_count: number
  key_results_count: number
  drafts_count: number
  progress_pct: number | null
  created_at: string | null
  updated_at: string | null
}

export interface OkrCycle extends OkrCycleSummary {
  objectives: ObjectiveNode[]
}

export type OkrCycleCreatePayload = {
  tipo: OkrCycleTipo
  ano: number
  trimestre?: number | null
  nome?: string | null
}

export type OkrCyclePayload = Partial<{
  nome: string
  tipo: OkrCycleTipo
  ano: number
  trimestre: number | null
  objectives: Objective[]
}>

export function listOkrCycles(): Promise<{ items: OkrCycleSummary[] }> {
  return get<{ items: OkrCycleSummary[] }>('/api/okrs/cycles')
}

export function createOkrCycle(body: OkrCycleCreatePayload): Promise<OkrCycle> {
  return post<OkrCycle>('/api/okrs/cycles', body)
}

/** 404 (ApiError) se não houver ciclo ativo. */
export function getActiveOkrCycle(): Promise<OkrCycle> {
  return get<OkrCycle>('/api/okrs/cycles/active')
}

export function getOkrCycle(id: string): Promise<OkrCycle> {
  return get<OkrCycle>(`/api/okrs/cycles/${encodeURIComponent(id)}`)
}

export function updateOkrCycle(id: string, body: OkrCyclePayload): Promise<OkrCycle> {
  return put<OkrCycle>(`/api/okrs/cycles/${encodeURIComponent(id)}`, body)
}

export function activateOkrCycle(id: string): Promise<OkrCycle> {
  return post<OkrCycle>(`/api/okrs/cycles/${encodeURIComponent(id)}/activate`)
}

export function archiveOkrCycle(id: string): Promise<OkrCycle> {
  return post<OkrCycle>(`/api/okrs/cycles/${encodeURIComponent(id)}/archive`)
}

export function deleteOkrCycle(id: string): Promise<{ message: string; id: string }> {
  return del<{ message: string; id: string }>(`/api/okrs/cycles/${encodeURIComponent(id)}`)
}
