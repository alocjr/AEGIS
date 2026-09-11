/** Critérios de seleção e priorização da Análise executiva (bloco 08 do canvas). */

export const ANALISE_CRITERIO_IDS = [
  'valor_economico',
  'urgencia_risco',
  'viabilidade_dados',
  'capacidade_adocao',
  'tempo_evidencia',
  'reutilizacao',
  'risco_residual',
] as const

export type AnaliseCriterioId = (typeof ANALISE_CRITERIO_IDS)[number]

export interface AnaliseCriterioDef {
  id: AnaliseCriterioId
  label: string
  peso: number
  pergunta: string
}

export const ANALISE_CRITERIOS: AnaliseCriterioDef[] = [
  {
    id: 'valor_economico',
    label: 'Valor econômico ou estratégico',
    peso: 25,
    pergunta: 'O resultado é material e ligado a uma prioridade real?',
  },
  {
    id: 'urgencia_risco',
    label: 'Urgência e risco evitado',
    peso: 15,
    pergunta: 'O custo de não agir é crescente ou crítico?',
  },
  {
    id: 'viabilidade_dados',
    label: 'Viabilidade de dados e integração',
    peso: 15,
    pergunta: 'Existem dados suficientes, acesso e caminho técnico razoável?',
  },
  {
    id: 'capacidade_adocao',
    label: 'Capacidade de adoção',
    peso: 15,
    pergunta: 'Há dono, usuários, tempo de revisão e mudança de processo possível?',
  },
  {
    id: 'tempo_evidencia',
    label: 'Tempo até evidência',
    peso: 10,
    pergunta: 'É possível testar a hipótese sem construir a solução completa?',
  },
  {
    id: 'reutilizacao',
    label: 'Reutilização e efeito habilitador',
    peso: 10,
    pergunta: 'O projeto desbloqueia ou reduz custo de outros casos?',
  },
  {
    id: 'risco_residual',
    label: 'Risco residual',
    peso: 10,
    pergunta: 'O uso pode operar dentro do apetite de risco da empresa?',
  },
]

export type CanvasAnaliseScores = Record<AnaliseCriterioId, number | null>

export interface CanvasAnaliseExecutiva {
  scores: CanvasAnaliseScores
  observacao: string
}

export function emptyAnaliseExecutiva(): CanvasAnaliseExecutiva {
  return {
    scores: {
      valor_economico: null,
      urgencia_risco: null,
      viabilidade_dados: null,
      capacidade_adocao: null,
      tempo_evidencia: null,
      reutilizacao: null,
      risco_residual: null,
    },
    observacao: '',
  }
}

export function mergeAnaliseExecutiva(raw?: CanvasAnaliseExecutiva | null): CanvasAnaliseExecutiva {
  const base = emptyAnaliseExecutiva()
  const scores = raw?.scores
  if (scores) {
    for (const id of ANALISE_CRITERIO_IDS) {
      const n = scores[id]
      base.scores[id] = typeof n === 'number' && n >= 1 && n <= 5 ? n : null
    }
  }
  base.observacao = raw?.observacao || ''
  return base
}

export interface AnalisePonderada {
  scored: number
  total: number
  value: number | null
  pct: number | null
}

export function analisePonderada(scores?: Partial<CanvasAnaliseScores> | null): AnalisePonderada {
  let weight = 0
  let acc = 0
  let scored = 0
  for (const c of ANALISE_CRITERIOS) {
    const n = scores?.[c.id]
    if (typeof n === 'number' && n >= 1 && n <= 5) {
      acc += n * c.peso
      weight += c.peso
      scored += 1
    }
  }
  if (!weight) return { scored: 0, total: ANALISE_CRITERIOS.length, value: null, pct: null }
  const value = acc / weight
  return {
    scored,
    total: ANALISE_CRITERIOS.length,
    value,
    pct: (value / 5) * 100,
  }
}

export function formatNota(n: number, digits = 1): string {
  return n.toFixed(digits).replace('.', ',')
}
