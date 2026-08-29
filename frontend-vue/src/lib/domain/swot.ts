/**
 * AR-04: rótulos e metadados de domínio SWOT/TOWS — fonte única para views e gráficos.
 * Tipos e constantes de API permanecem em `@/api/swotAnalysis`.
 */
export type {
  MaturityDimensionId,
  SwotListField,
  SwotTowsField,
} from '@/api/swotAnalysis'

export {
  MATURITY_DIMENSIONS,
  SWOT_PILLARS,
  SWOT_QUADRANT_DEFAULT_PILLARS,
} from '@/api/swotAnalysis'

import type { SwotListField, SwotTowsField } from '@/api/swotAnalysis'

/** Rótulo singular de quadrante (ex.: «Força» em vez de «Forças»). */
export const SWOT_QUADRANT_LABEL: Record<SwotListField, string> = {
  forcas: 'Força',
  fraquezas: 'Fraqueza',
  oportunidades: 'Oportunidade',
  ameacas: 'Ameaça',
}

/** Rótulo curto de estratégia TOWS (mapa, canvas, listagens). */
export const TOWS_LABEL: Record<SwotTowsField, string> = {
  tows_fo: 'F × O · Ofensiva',
  tows_fa: 'F × A · Defesa',
  tows_fxo: 'f × O · Reforço',
  tows_fxa: 'f × A · Sobrevivência',
}

/** Grupos TOWS com dica contextual (editor de canvas). */
export const TOWS_GROUPS: { field: SwotTowsField; label: string; hint: string }[] = [
  { field: 'tows_fo', label: TOWS_LABEL.tows_fo, hint: 'Forças que capturam oportunidades' },
  { field: 'tows_fa', label: TOWS_LABEL.tows_fa, hint: 'Forças que neutralizam ameaças' },
  { field: 'tows_fxo', label: TOWS_LABEL.tows_fxo, hint: 'Fraquezas que travam oportunidades' },
  { field: 'tows_fxa', label: TOWS_LABEL.tows_fxa, hint: 'Vulnerabilidade encontra risco' },
]
