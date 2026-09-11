import { del, get, patch, post, put } from './client'
import type { CanvasAnaliseExecutiva } from '@/lib/canvasAnaliseExecutiva'

export type { CanvasAnaliseExecutiva } from '@/lib/canvasAnaliseExecutiva'

export type CanvasQuadrant =
  | 'ganho_rapido'
  | 'aposta_estrategica'
  | 'incremental'
  | 'evitar'
  | null

export type CanvasListField =
  | 'contexto'
  | 'dores'
  | 'oportunidade'
  | 'dados'
  | 'valor'
  | 'custo'
  | 'riscos'

export type CanvasPrioridade = 'P0' | 'P1' | 'P2' | 'P3' | 'P4'

export type CanvasMesInicio =
  | 'jan'
  | 'fev'
  | 'mar'
  | 'abr'
  | 'mai'
  | 'jun'
  | 'jul'
  | 'ago'
  | 'set'
  | 'out'
  | 'nov'
  | 'dez'
  | ''

export const CANVAS_PRIORIDADES: { id: CanvasPrioridade; label: string }[] = [
  { id: 'P0', label: 'P0 — Imediato' },
  { id: 'P1', label: 'P1 — O mais cedo possível' },
  { id: 'P2', label: 'P2 — Planejado' },
  { id: 'P3', label: 'P3 — Quando possível' },
  { id: 'P4', label: 'P4 — Não importante' },
]

export const CANVAS_MESES: { id: Exclude<CanvasMesInicio, ''>; label: string }[] = [
  { id: 'jan', label: 'Jan' },
  { id: 'fev', label: 'Fev' },
  { id: 'mar', label: 'Mar' },
  { id: 'abr', label: 'Abr' },
  { id: 'mai', label: 'Mai' },
  { id: 'jun', label: 'Jun' },
  { id: 'jul', label: 'Jul' },
  { id: 'ago', label: 'Ago' },
  { id: 'set', label: 'Set' },
  { id: 'out', label: 'Out' },
  { id: 'nov', label: 'Nov' },
  { id: 'dez', label: 'Dez' },
]

export type CanvasPeriodicidade = 'quinzenal' | 'mensal' | 'bimestral' | 'trimestral'

export const CANVAS_PERIODICIDADES: { id: CanvasPeriodicidade; label: string }[] = [
  { id: 'quinzenal', label: 'Quinzenal' },
  { id: 'mensal', label: 'Mensal' },
  { id: 'bimestral', label: 'Bimestral' },
  { id: 'trimestral', label: 'Trimestral' },
]

export function periodicidadeLabel(id: string): string {
  return CANVAS_PERIODICIDADES.find((p) => p.id === id)?.label || id
}

export interface CanvasProjectSummary {
  id: string
  title: string
  area_negocio: string
  responsavel: string
  data: string
  objetivo_estrategico: string
  proximo_passo: string
  updated_at: string | null
  created_at: string | null
  quadrant: CanvasQuadrant
  score_valor: number | null
  score_viabilidade: number | null
  /** SWOT de origem do projeto (rastreabilidade no Mapa Estratégico). */
  swot_id: string | null
  /** Itens SWOT que motivaram o projeto. */
  swot_item_ids: string[]
  /** Iniciativas TOWS que motivaram o projeto. */
  tows_ids: string[]
  /** Key Results (OKR) que este projeto endereça. */
  kr_ids: string[]
  /** `aprovado_portfolio` após o hook de Governança (ver aprovarPortfolio). */
  status: 'rascunho' | 'aprovado_portfolio'
  /** Sistema de IA criado no módulo de Governança, se aprovado para o portfólio. */
  ai_system_id: string | null
  /** Prioridade de investimento definida pelo C-level. */
  prioridade: CanvasPrioridade
  /** Mês em que o projeto deve iniciar. */
  mes_inicio: CanvasMesInicio
  visibility?: 'shared' | 'private'
  created_by_user_id?: string | null
  /** Aprovação executiva (C-level). Só projetos aprovados entram no Mapa Estratégico. */
  projeto_aprovado: boolean
  aprovacao_comentario: string
  data_inicio_real: string
  periodicidade: CanvasPeriodicidade | ''
  aprovado_em: string | null
}

export interface CanvasProject extends CanvasProjectSummary {
  /** Justificativa de como o projeto trata as iniciativas TOWS vinculadas. */
  justificativa_tows: string
  analise_executiva: CanvasAnaliseExecutiva
  contexto: string[]
  dores: string[]
  oportunidade: string[]
  oportunidade_tipos: string[]
  dados: string[]
  valor: string[]
  custo: string[]
  riscos: string[]
  opportunity_type_options: string[]
  cronograma: CanvasCronograma
}

export interface CanvasCronogramaAtividade {
  id: string
  titulo: string
  lideranca: string
  semana_inicio: number
  semana_fim: number
  predecessor: string
}

export interface CanvasCronogramaMarco {
  id: string
  semana: number
  titulo: string
}

export interface CanvasCronograma {
  subtitulo: string
  pre_requisito: string
  criterio_aceite: string
  semanas: number
  atividades: CanvasCronogramaAtividade[]
  marcos: CanvasCronogramaMarco[]
}

export function emptyCronograma(): CanvasCronograma {
  return {
    subtitulo: '',
    pre_requisito: '',
    criterio_aceite: '',
    semanas: 8,
    atividades: [],
    marcos: [],
  }
}

export type CanvasProjectPayload = Partial<{
  title: string
  area_negocio: string
  responsavel: string
  data: string
  objetivo_estrategico: string
  contexto: string[]
  dores: string[]
  oportunidade: string[]
  oportunidade_tipos: string[]
  dados: string[]
  valor: string[]
  custo: string[]
  riscos: string[]
  score_valor: number | null
  score_viabilidade: number | null
  proximo_passo: string
  swot_id: string | null
  swot_item_ids: string[]
  tows_ids: string[]
  justificativa_tows: string
  kr_ids: string[]
  cronograma: CanvasCronograma
  analise_executiva: CanvasAnaliseExecutiva
  prioridade: CanvasPrioridade
  mes_inicio: CanvasMesInicio
  visibility?: 'shared' | 'private'
}>

export function listCanvasProjects(q?: string): Promise<{ items: CanvasProjectSummary[] }> {
  const query = (q || '').trim()
  const suffix = query ? `?q=${encodeURIComponent(query)}` : ''
  return get<{ items: CanvasProjectSummary[] }>(`/api/canvas-projects${suffix}`)
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

export function cloneCanvasProject(
  id: string,
  body: { organization_id: string; title?: string }
): Promise<CanvasProject> {
  return post<CanvasProject>(`/api/canvas-projects/${encodeURIComponent(id)}/clone`, body)
}

export interface CanvasRoadmapItem extends CanvasProjectSummary {
  semanas: number
}

export function listRoadmapProjects(): Promise<{ items: CanvasRoadmapItem[] }> {
  return get<{ items: CanvasRoadmapItem[] }>('/api/canvas-projects/roadmap')
}

export function moveRoadmapProject(
  id: string,
  dataInicioReal: string
): Promise<CanvasRoadmapItem> {
  return patch<CanvasRoadmapItem>(`/api/canvas-projects/${encodeURIComponent(id)}/inicio`, {
    data_inicio_real: dataInicioReal,
  })
}

export interface AprovarPortfolioResult {
  ai_system_id: string
  status: string
  risco_preliminar: 'baixo' | 'medio' | 'alto' | 'critico' | null
  created: boolean
}

/** Hook Canvas → Inventário: aprova a oportunidade e cria o sistema de IA correspondente
 * no módulo de Governança (idempotente — reexecutar não duplica). */
export function aprovarPortfolio(id: string): Promise<AprovarPortfolioResult> {
  return post<AprovarPortfolioResult>(`/api/canvas-projects/${encodeURIComponent(id)}/aprovar-portfolio`)
}

export type CanvasAprovarProjetoPayload = {
  comentario: string
  data_inicio_real: string
  periodicidade: CanvasPeriodicidade
}

export function aprovarProjeto(
  id: string,
  body: CanvasAprovarProjetoPayload
): Promise<CanvasProject> {
  return post<CanvasProject>(`/api/canvas-projects/${encodeURIComponent(id)}/aprovar`, body)
}
