/**
 * AR-04: acentos visuais das dimensões de maturidade — tokens CSS de main.css.
 */
import type { MaturityDimensionId } from '@/api/swotAnalysis'

export const MATURITY_DIMENSION_ACCENT: Record<MaturityDimensionId, string> = {
  strategy: 'var(--dim-strategy)',
  data_infra: 'var(--dim-data)',
  people_culture: 'var(--dim-people)',
  gov_risk: 'var(--dim-gov)',
}

/** Resolve acento de dimensão por id (fallback dourado editorial). */
export function maturityDimensionAccent(dimensionId: string): string {
  return MATURITY_DIMENSION_ACCENT[dimensionId as MaturityDimensionId] ?? 'var(--gold)'
}
