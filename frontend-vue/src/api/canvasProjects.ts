import { del, get, post, put } from './client'

export type CanvasQuadrant =
  | 'ganho_rapido'
  | 'aposta_estrategica'
  | 'incremental'
  | 'evitar'
  | null

export interface CanvasProjectSummary {
  id: string
  title: string
  area_negocio: string
  responsavel: string
  updated_at: string | null
  created_at: string | null
  quadrant: CanvasQuadrant
  score_valor: number | null
  score_viabilidade: number | null
}

export interface CanvasProject extends CanvasProjectSummary {
  data: string
  objetivo_estrategico: string
  contexto: string
  dores: string
  oportunidade: string
  oportunidade_tipos: string[]
  dados: string
  valor: string
  custo: string
  riscos: string
  proximo_passo: string
  opportunity_type_options: string[]
}

export type CanvasProjectPayload = Partial<{
  title: string
  area_negocio: string
  responsavel: string
  data: string
  objetivo_estrategico: string
  contexto: string
  dores: string
  oportunidade: string
  oportunidade_tipos: string[]
  dados: string
  valor: string
  custo: string
  riscos: string
  score_valor: number | null
  score_viabilidade: number | null
  proximo_passo: string
}>

export function listCanvasProjects(): Promise<{ items: CanvasProjectSummary[] }> {
  return get<{ items: CanvasProjectSummary[] }>('/api/canvas-projects')
}

export function createCanvasProject(title = 'Novo projeto'): Promise<CanvasProject> {
  return post<CanvasProject>('/api/canvas-projects', { title })
}

export function getCanvasProject(id: string): Promise<CanvasProject> {
  return get<CanvasProject>(`/api/canvas-projects/${encodeURIComponent(id)}`)
}

export function updateCanvasProject(
  id: string,
  body: CanvasProjectPayload
): Promise<CanvasProject> {
  return put<CanvasProject>(`/api/canvas-projects/${encodeURIComponent(id)}`, body)
}

export function deleteCanvasProject(id: string): Promise<{ message: string; id: string }> {
  return del<{ message: string; id: string }>(
    `/api/canvas-projects/${encodeURIComponent(id)}`
  )
}
