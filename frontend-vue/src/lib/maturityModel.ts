import type { MaturityQuestion, MaturityTier } from '@/api/maturity'

export const MATURITY_TIER_KEYS: MaturityTier[] = ['basico', 'completo', 'complementar']
export const MATURITY_TIER_ORDER: Record<MaturityTier, number> = {
  basico: 0,
  completo: 1,
  complementar: 2,
}
export const MATURITY_TIER_LABEL_SHORT: Record<MaturityTier, string> = {
  basico: 'Básico',
  completo: 'Completo',
  complementar: 'Complementar',
}
export const MATURITY_DIMENSION_ABBR: Record<string, string> = {
  strategy: 'Est',
  data_infra: 'Dad',
  people_culture: 'Pes',
  gov_risk: 'Gov',
}

export function tierIndexOf(tier: string): number {
  return MATURITY_TIER_ORDER[tier as MaturityTier] ?? 99
}

export function naturalCompare(a: string, b: string): number {
  const ma = a.match(/^([A-Za-z]+)(\d+)$/)
  const mb = b.match(/^([A-Za-z]+)(\d+)$/)
  const la = ma?.[1] ?? a
  const lb = mb?.[1] ?? b
  const na = Number(ma?.[2] ?? 0)
  const nb = Number(mb?.[2] ?? 0)
  if (la !== lb) return la < lb ? -1 : 1
  return na - nb
}

export function maturityOriginLine(q: MaturityQuestion): string {
  if (q.originType === 'modelo_rapido' || q.tier === 'basico') {
    return `Abrangência Básico${q.ref ? ` · ${q.ref}` : ''}`
  }
  if (q.csfId) {
    return `Abrangência ${MATURITY_TIER_LABEL_SHORT[q.tier]} · CSF ${q.csfId}${q.csfName ? ` · ${q.csfName}` : ''}`
  }
  return `Abrangência ${MATURITY_TIER_LABEL_SHORT[q.tier]}`
}
