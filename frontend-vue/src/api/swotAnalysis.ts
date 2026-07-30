import { get, put, post } from './client'

export type SwotVereditoTipo = 'executavel' | 'fundacao' | 'repensar' | ''

export type SwotListField = 'forcas' | 'fraquezas' | 'oportunidades' | 'ameacas'

export type SwotTowsField = 'tows_fo' | 'tows_fa' | 'tows_fxo' | 'tows_fxa'

export type SwotPilarId =
  | 'dados'
  | 'talento'
  | 'infraestrutura'
  | 'governanca'
  | 'cultura'
  | 'portfolio'
  | 'ecossistema'
  | ''

export interface SwotItem {
  id: string
  texto: string
  pilar: SwotPilarId | string
  impacto: number | null
  viabilidade: number | null
  probabilidade: number | null
  evidencia: string
  prioridade: number | null
}

export interface SwotInitiative {
  id?: string
  acao: string
  dono: string
  horizonte: string
  itens_internos?: string[]
  itens_externos?: string[]
}

export interface SwotAnalysis {
  id: string
  optica: string
  forcas: SwotItem[]
  fraquezas: SwotItem[]
  oportunidades: SwotItem[]
  ameacas: SwotItem[]
  tows_fo: SwotInitiative[]
  tows_fa: SwotInitiative[]
  tows_fxo: SwotInitiative[]
  tows_fxa: SwotInitiative[]
  veredito_tipo: SwotVereditoTipo
  veredito_titulo: string
  veredito_texto: string
  created_at: string | null
  updated_at: string | null
}

export type SwotAnalysisPayload = Partial<{
  optica: string
  forcas: SwotItem[]
  fraquezas: SwotItem[]
  oportunidades: SwotItem[]
  ameacas: SwotItem[]
  tows_fo: SwotInitiative[]
  tows_fa: SwotInitiative[]
  tows_fxo: SwotInitiative[]
  tows_fxa: SwotInitiative[]
  veredito_tipo: SwotVereditoTipo
  veredito_titulo: string
  veredito_texto: string
}>

/** Envelope aegis.swot-ia ou payload direto. */
export type SwotImportDocument = {
  format?: string
  version?: number
  exported_at?: string
  locale?: string
  meta?: Record<string, unknown>
  payload?: SwotAnalysisPayload
} & SwotAnalysisPayload

export const SWOT_PILLARS: { id: Exclude<SwotPilarId, ''>; name: string; q: string }[] = [
  {
    id: 'dados',
    name: 'Dados',
    q: 'Temos dados proprietários, limpos e integrados para alimentar e contextualizar modelos?',
  },
  {
    id: 'talento',
    name: 'Talento',
    q: 'Há competência técnica e lideranças com letramento para conduzir?',
  },
  {
    id: 'infraestrutura',
    name: 'Infraestrutura',
    q: 'A arquitetura (nuvem, APIs) consome IA com segurança, sem travar no legado?',
  },
  {
    id: 'governanca',
    name: 'Governança & Regulação',
    q: 'Temos conformidade (LGPD), auditoria de viés e alucinação, isolamento de dados sensíveis e validação humana no que é crítico?',
  },
  {
    id: 'cultura',
    name: 'Cultura & Liderança',
    q: 'Há patrocínio do topo e abertura à mudança — ou medo e resistência?',
  },
  {
    id: 'portfolio',
    name: 'Portfólio de casos',
    q: 'Sabemos priorizar casos por valor e prontidão, com dono definido?',
  },
  {
    id: 'ecossistema',
    name: 'Ecossistema & Fornecedores',
    q: 'Temos flexibilidade contra o lock-in de um único fornecedor ou modelo?',
  },
]

export function getSwotAnalysis(): Promise<SwotAnalysis> {
  return get<SwotAnalysis>('/api/swot-analysis')
}

export function updateSwotAnalysis(body: SwotAnalysisPayload): Promise<SwotAnalysis> {
  return put<SwotAnalysis>('/api/swot-analysis', body)
}

export function importSwotAnalysis(body: SwotImportDocument): Promise<SwotAnalysis> {
  return post<SwotAnalysis>('/api/swot-analysis/import', body)
}
