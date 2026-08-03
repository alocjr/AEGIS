import { del, get, post, put } from './client'

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
}

export interface CanvasProject extends CanvasProjectSummary {
  /** Justificativa de como o projeto trata as iniciativas TOWS vinculadas. */
  justificativa_tows: string
  contexto: string[]
  dores: string[]
  oportunidade: string[]
  oportunidade_tipos: string[]
  dados: string[]
  valor: string[]
  custo: string[]
  riscos: string[]
  opportunity_type_options: string[]
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

/** Documento gerado pelo prompt aegis.canvas-oportunidades. */
export type CanvasImportDocument = {
  schema?: string
  versao?: string | number
  status?: string
  gerado_por?: string
  projeto?: {
    nome?: string
    descricao?: string
    setor?: string
    porte?: string
  }
  areas?: Array<{
    area?: string
    contexto?: string
    objetivo_estrategico?: string
    oportunidades?: Array<Record<string, unknown>>
  }>
  roadmap?: Array<{ id?: string; justificativa?: string }>
}

export type CanvasImportResult = {
  created: number
  items: CanvasProjectSummary[]
}

export type CanvasImportIntoResult = {
  applied: number
  available: number
  item: CanvasProject
}

/** Cria um projeto por oportunidade a partir do JSON do prompt. */
export function importCanvasProjects(body: CanvasImportDocument): Promise<CanvasImportResult> {
  return post<CanvasImportResult>('/api/canvas-projects/import', body)
}

/** Substitui o canvas aberto com a 1ª oportunidade do JSON. */
export function importIntoCanvasProject(
  id: string,
  body: CanvasImportDocument
): Promise<CanvasImportIntoResult> {
  return post<CanvasImportIntoResult>(
    `/api/canvas-projects/${encodeURIComponent(id)}/import`,
    body
  )
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
