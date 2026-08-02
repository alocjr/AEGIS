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

/** Dimensões do Diagnóstico de Maturidade em IA (modelo v3). */
export type MaturityDimensionId = 'strategy' | 'data_infra' | 'people_culture' | 'gov_risk'

export interface SwotPilarSlot {
  id: string
  nome: string
}

export type SwotPilaresPorQuadrante = Record<SwotListField, SwotPilarSlot[]>

export interface SwotItem {
  id: string
  texto: string
  pilar: SwotPilarId | string
  impacto: number | null
  viabilidade: number | null
  probabilidade: number | null
  evidencia: string
  prioridade: number | null
  /** Incluir este item no cruzamento TOWS. */
  tows: boolean
}

export interface SwotInitiative {
  id?: string
  acao: string
  dono: string
  horizonte: string
  itens_internos?: string[]
  itens_externos?: string[]
}

/** Pontos de Atenção (nota 3) — fora do SWOT/TOWS. */
export interface SwotWatchlistItem {
  id: string
  texto: string
  pilar: string
  dimensao: string
  nota: number | null
  evidencia: string
  swotCategory?: string | null
}

export interface SwotAnalysis {
  id: string
  maturity_response_id?: string | null
  optica: string
  pilares: SwotPilaresPorQuadrante
  forcas: SwotItem[]
  fraquezas: SwotItem[]
  oportunidades: SwotItem[]
  ameacas: SwotItem[]
  watchlist?: SwotWatchlistItem[]
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
  pilares: SwotPilaresPorQuadrante
  forcas: SwotItem[]
  fraquezas: SwotItem[]
  oportunidades: SwotItem[]
  ameacas: SwotItem[]
  watchlist: SwotWatchlistItem[]
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

export type SwotPillar = {
  id: Exclude<SwotPilarId, ''>
  name: string
  q: string
  /** Dimensão do Modelo de Maturidade que este pilar aprofunda. */
  maturityDimension: MaturityDimensionId
}

export const MATURITY_DIMENSIONS: {
  id: MaturityDimensionId
  name: string
  brief: string
}[] = [
  {
    id: 'strategy',
    name: 'Estratégia e Visão',
    brief: 'Ambição, roadmap, priorização e patrocínio que ligam IA a resultado.',
  },
  {
    id: 'data_infra',
    name: 'Dados e Infraestrutura',
    brief: 'Base de dados, arquitetura e capacidade de consumir IA com segurança.',
  },
  {
    id: 'people_culture',
    name: 'Pessoas e Cultura',
    brief: 'Talento, letramento, liderança e abertura à mudança.',
  },
  {
    id: 'gov_risk',
    name: 'Governança e Risco',
    brief: 'Conformidade, risco, fornecedores e controle do que é crítico.',
  },
]

/**
 * Sete pilares canônicos da SWOT — aprofundam as quatro dimensões do
 * Diagnóstico de Maturidade em IA (mesmo vocabulário do modelo v3).
 */
export const SWOT_PILLARS: SwotPillar[] = [
  {
    id: 'portfolio',
    name: 'Estratégia e Portfólio',
    maturityDimension: 'strategy',
    q: 'Há visão, roadmap e critérios de priorização (impacto × viabilidade) que conectam IA a OKRs e receita?',
  },
  {
    id: 'dados',
    name: 'Dados',
    maturityDimension: 'data_infra',
    q: 'Temos dados proprietários, limpos e integrados para alimentar e contextualizar modelos?',
  },
  {
    id: 'infraestrutura',
    name: 'Infraestrutura',
    maturityDimension: 'data_infra',
    q: 'A arquitetura (nuvem, APIs) consome IA com segurança, sem travar no legado?',
  },
  {
    id: 'talento',
    name: 'Talento',
    maturityDimension: 'people_culture',
    q: 'Há competência técnica e lideranças com letramento para conduzir a transformação?',
  },
  {
    id: 'cultura',
    name: 'Cultura e Liderança',
    maturityDimension: 'people_culture',
    q: 'Há patrocínio do topo e abertura à mudança — ou medo e resistência?',
  },
  {
    id: 'governanca',
    name: 'Governança e Risco',
    maturityDimension: 'gov_risk',
    q: 'Há conformidade (LGPD), gestão de risco, auditoria de viés/alucinação e validação humana no crítico?',
  },
  {
    id: 'ecossistema',
    name: 'Ecossistema e Fornecedores',
    maturityDimension: 'gov_risk',
    q: 'Temos flexibilidade contra o lock-in de um único fornecedor ou modelo?',
  },
]

/** Defaults do banco de itens por quadrante — rótulos alinhados às dimensões de maturidade. */
export const SWOT_QUADRANT_DEFAULT_PILLARS: SwotPilaresPorQuadrante = {
  forcas: [
    { id: 'portfolio', nome: 'Estratégia e Visão' },
    { id: 'dados', nome: 'Dados e Infraestrutura' },
    { id: 'talento', nome: 'Pessoas e Cultura' },
    { id: 'governanca', nome: 'Governança e Risco' },
  ],
  oportunidades: [
    { id: 'ecossistema', nome: 'Tecnologia e ecossistema' },
    { id: 'portfolio', nome: 'Mercado e clientes' },
    { id: 'governanca', nome: 'Ambiente regulatório' },
    { id: 'talento', nome: 'Talento e incentivos' },
  ],
  fraquezas: [
    { id: 'portfolio', nome: 'Estratégia e Visão' },
    { id: 'dados', nome: 'Dados e Infraestrutura' },
    { id: 'talento', nome: 'Pessoas e Cultura' },
    { id: 'governanca', nome: 'Governança e Risco' },
  ],
  ameacas: [
    { id: 'portfolio', nome: 'Concorrência' },
    { id: 'governanca', nome: 'Regulação e risco' },
    { id: 'ecossistema', nome: 'Fornecedores e modelos' },
    { id: 'talento', nome: 'Talento e ritmo' },
  ],
}

export function emptyPilares(): SwotPilaresPorQuadrante {
  return {
    forcas: [],
    fraquezas: [],
    oportunidades: [],
    ameacas: [],
  }
}

/** SWOT mais recente (cria vazia se não houver). */
export function getSwotAnalysis(): Promise<SwotAnalysis> {
  return get<SwotAnalysis>('/api/swot-analysis')
}

export function getSwotAnalysisById(id: string): Promise<SwotAnalysis> {
  return get<SwotAnalysis>(`/api/swot-analysis/${encodeURIComponent(id)}`)
}

export function getSwotByMaturityResponse(maturityResponseId: string): Promise<SwotAnalysis> {
  return get<SwotAnalysis>(
    `/api/swot-analysis/by-maturity/${encodeURIComponent(maturityResponseId)}`
  )
}

export function createSwotFromMaturity(maturityResponseId: string): Promise<SwotAnalysis> {
  return post<SwotAnalysis>(
    `/api/swot-analysis/from-maturity/${encodeURIComponent(maturityResponseId)}`,
    {}
  )
}

export function updateSwotAnalysis(
  body: SwotAnalysisPayload,
  swotId?: string | null,
  opts?: { rebuildTows?: boolean }
): Promise<SwotAnalysis> {
  const q = opts?.rebuildTows ? '?rebuild_tows=true' : ''
  if (swotId) {
    return put<SwotAnalysis>(`/api/swot-analysis/${encodeURIComponent(swotId)}${q}`, body)
  }
  return put<SwotAnalysis>(`/api/swot-analysis${q}`, body)
}

export function importSwotAnalysis(body: SwotImportDocument): Promise<SwotAnalysis> {
  return post<SwotAnalysis>('/api/swot-analysis/import', body)
}
