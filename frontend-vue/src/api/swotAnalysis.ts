import { get, put } from './client'

export type SwotVereditoTipo = 'executavel' | 'fundacao' | 'repensar' | ''

export type SwotListField = 'forcas' | 'fraquezas' | 'oportunidades' | 'ameacas'

export type SwotTowsField = 'tows_fo' | 'tows_fa' | 'tows_fxo' | 'tows_fxa'

export interface SwotInitiative {
  acao: string
  dono: string
  horizonte: string
}

export interface SwotAnalysis {
  id: string
  optica: string
  forcas: string[]
  fraquezas: string[]
  oportunidades: string[]
  ameacas: string[]
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
  forcas: string[]
  fraquezas: string[]
  oportunidades: string[]
  ameacas: string[]
  tows_fo: SwotInitiative[]
  tows_fa: SwotInitiative[]
  tows_fxo: SwotInitiative[]
  tows_fxa: SwotInitiative[]
  veredito_tipo: SwotVereditoTipo
  veredito_titulo: string
  veredito_texto: string
}>

export function getSwotAnalysis(): Promise<SwotAnalysis> {
  return get<SwotAnalysis>('/api/swot-analysis')
}

export function updateSwotAnalysis(body: SwotAnalysisPayload): Promise<SwotAnalysis> {
  return put<SwotAnalysis>('/api/swot-analysis', body)
}
