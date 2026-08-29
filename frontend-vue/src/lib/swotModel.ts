/**
 * AR-02: regras e metadados do editor SWOT — extraídos de SwotAnalysisView.
 */
import {
  SWOT_PILLARS,
  SWOT_QUADRANT_DEFAULT_PILLARS,
  emptyPilares,
  type SwotInitiative,
  type SwotItem,
  type SwotListField,
  type SwotPilarId,
  type SwotPilarSlot,
  type SwotPilaresPorQuadrante,
  type SwotTowsField,
  type SwotVereditoTipo,
} from '@/api/swotAnalysis'

export type QuadrantHint = {
  letter: string
  name: string
  locus: string
  neg: boolean
  groups: { label: string; text: string; pilar: Exclude<SwotPilarId, ''> }[]
}

export type QuadrantPillar = { id: string; name: string; q: string }

export const PILLAR_BY_ID = Object.fromEntries(SWOT_PILLARS.map((p) => [p.id, p])) as Record<
  Exclude<SwotPilarId, ''>,
  (typeof SWOT_PILLARS)[number]
>

/** Repertório de partida por quadrante — estímulo, não checklist. */
export const QUADRANT_HINTS: Record<SwotListField, QuadrantHint> = {
  forcas: {
    letter: 'F',
    name: 'Forças',
    locus: 'interno · positivo',
    neg: false,
    groups: [
      {
        label: 'Estratégia e Visão',
        pilar: 'portfolio',
        text: 'visão clara de IA ligada a OKRs/receita; roadmap aprovado; framework de impacto × viabilidade; casos com ROI.',
      },
      {
        label: 'Dados e Infraestrutura',
        pilar: 'dados',
        text: 'base proprietária integrada e de qualidade; nuvem/APIs maduras para consumir IA com segurança.',
      },
      {
        label: 'Pessoas e Cultura',
        pilar: 'talento',
        text: 'time de dados/IA constituído; lideranças com letramento; cultura de experimentação e patrocínio do topo.',
      },
      {
        label: 'Governança e Risco',
        pilar: 'governanca',
        text: 'política de IA, conformidade, auditoria de viés/alucinação e validação humana no crítico.',
      },
    ],
  },
  oportunidades: {
    letter: 'O',
    name: 'Oportunidades',
    locus: 'externo · positivo',
    neg: false,
    groups: [
      {
        label: 'Tecnologia e ecossistema',
        pilar: 'ecossistema',
        text: 'barateamento e maturação dos modelos; IA generativa, RAG e agêntica; ferramentas abertas e parceiros.',
      },
      {
        label: 'Mercado e clientes',
        pilar: 'portfolio',
        text: 'demanda por experiências personalizadas; novos modelos de receita; segmentos mal atendidos; concorrentes lentos.',
      },
      {
        label: 'Ambiente regulatório',
        pilar: 'governanca',
        text: 'clareza regulatória ou janelas setoriais que favorecem quem já tem conformidade e isolamento de dados.',
      },
      {
        label: 'Talento e incentivos',
        pilar: 'talento',
        text: 'oferta crescente de talento e ecossistemas locais; editais e incentivos para acelerar a transformação.',
      },
    ],
  },
  fraquezas: {
    letter: 'f',
    name: 'Fraquezas',
    locus: 'interno · negativo',
    neg: true,
    groups: [
      {
        label: 'Estratégia e Visão',
        pilar: 'portfolio',
        text: 'só pilotos sem escala; sem dono, critério de priorização, roadmap ou business case.',
      },
      {
        label: 'Dados e Infraestrutura',
        pilar: 'dados',
        text: 'silos, baixa qualidade, legado e dívida técnica; sem propriedade clara nem rotulagem.',
      },
      {
        label: 'Pessoas e Cultura',
        pilar: 'talento',
        text: 'falta de especialistas; letramento desigual; resistência ou aversão a risco.',
      },
      {
        label: 'Governança e Risco',
        pilar: 'governanca',
        text: 'sem governança de IA, auditoria de alucinações/viés ou isolamento de dados sensíveis.',
      },
    ],
  },
  ameacas: {
    letter: 'A',
    name: 'Ameaças',
    locus: 'externo · negativo',
    neg: true,
    groups: [
      {
        label: 'Concorrência',
        pilar: 'portfolio',
        text: 'players maduros e marketplaces com IA avançada; risco de disrupção do core.',
      },
      {
        label: 'Regulação e risco',
        pilar: 'governanca',
        text: 'LGPD, marco de IA e regras setoriais elevando o custo de conformidade e o risco reputacional.',
      },
      {
        label: 'Fornecedores e modelos',
        pilar: 'ecossistema',
        text: 'lock-in, mudança de preço ou descontinuação; alucinação, viés e dependência de um único provedor.',
      },
      {
        label: 'Talento e ritmo',
        pilar: 'talento',
        text: 'guerra por talento; velocidade da mudança e obsolescência precoce das ferramentas.',
      },
    ],
  },
}

export const SWOT_QUADRANTS: {
  field: SwotListField
  letter: string
  name: string
  quest: string
  neg: boolean
  internal: boolean
}[] = [
  {
    field: 'forcas',
    letter: 'F',
    name: 'Forças',
    quest: 'O que a organização tem hoje que sustenta a estratégia de IA?',
    neg: false,
    internal: true,
  },
  {
    field: 'oportunidades',
    letter: 'O',
    name: 'Oportunidades',
    quest: 'Que condição externa a estratégia de IA pode explorar?',
    neg: false,
    internal: false,
  },
  {
    field: 'fraquezas',
    letter: 'f',
    name: 'Fraquezas',
    quest: 'O que, dentro de casa, trava a estratégia de IA?',
    neg: true,
    internal: true,
  },
  {
    field: 'ameacas',
    letter: 'A',
    name: 'Ameaças',
    quest: 'O que pode inviabilizar ou encarecer a estratégia de IA?',
    neg: true,
    internal: false,
  },
]

export const SWOT_TOWS_SECTIONS: {
  field: SwotTowsField
  key: string
  quest: string
  hint: string
  hard?: boolean
}[] = [
  {
    field: 'tows_fo',
    key: 'F × O · Ofensiva',
    quest: 'Como usar nossas forças para capturar as oportunidades?',
    hint: 'As apostas de crescimento — onde investir e acelerar.',
  },
  {
    field: 'tows_fa',
    key: 'F × A · Defesa',
    quest: 'Como usar nossas forças para neutralizar as ameaças?',
    hint: 'Como proteger a posição e transformar risco em barreira de entrada.',
  },
  {
    field: 'tows_fxo',
    key: 'f × O · Reforço',
    quest: 'Que fraquezas travam a captura das oportunidades?',
    hint: 'O que consertar primeiro — a fila de capacitação.',
  },
  {
    field: 'tows_fxa',
    key: 'f × A · Sobrevivência',
    quest: 'Onde a vulnerabilidade interna encontra o risco externo?',
    hint: 'O ponto de maior perigo — mitigar ou repensar a estratégia.',
    hard: true,
  },
]

export const SWOT_VEREDITO_OPTIONS: { id: SwotVereditoTipo; label: string }[] = [
  { id: 'executavel', label: 'Executável como está' },
  { id: 'fundacao', label: 'Executável com fase de fundação' },
  { id: 'repensar', label: 'Repensar a estratégia' },
]

export const SWOT_DEFAULT_SLOTS = SWOT_QUADRANT_DEFAULT_PILLARS

export function buildSwotCatalog(hints: Record<SwotListField, QuadrantHint> = QUADRANT_HINTS) {
  return (['forcas', 'oportunidades', 'fraquezas', 'ameacas'] as SwotListField[]).map(
    (field) => hints[field]
  )
}

export function defaultNomeFor(field: SwotListField, pilarId: string): string {
  const fromDefault = SWOT_DEFAULT_SLOTS[field].find((s) => s.id === pilarId)
  if (fromDefault?.nome) return fromDefault.nome
  return PILLAR_BY_ID[pilarId as Exclude<SwotPilarId, ''>]?.name || pilarId
}

export function normalizePilares(raw?: SwotPilaresPorQuadrante | null): SwotPilaresPorQuadrante {
  const base = emptyPilares()
  if (!raw) return base
  for (const field of ['forcas', 'fraquezas', 'oportunidades', 'ameacas'] as SwotListField[]) {
    const list = raw[field]
    if (!Array.isArray(list)) continue
    const seen = new Set<string>()
    base[field] = list
      .map((slot) => {
        const id = String(slot?.id || '')
          .trim()
          .toLowerCase()
        if (!id || seen.has(id)) return null
        seen.add(id)
        return { id, nome: String(slot?.nome || '').trim() }
      })
      .filter((s): s is SwotPilarSlot => !!s)
  }
  return base
}

export function resolvePillar(field: SwotListField, id: string, nomeHint = ''): QuadrantPillar {
  const canonical = PILLAR_BY_ID[id as Exclude<SwotPilarId, ''>]
  const name = (nomeHint || '').trim() || defaultNomeFor(field, id)
  if (canonical) {
    return { id, name, q: canonical.q }
  }
  const pretty = id
    .split(/[-_]/)
    .filter(Boolean)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ')
  return { id, name: name || pretty || id, q: '' }
}

export function emptySwotItem(pilar: string = ''): SwotItem {
  return {
    id: '',
    texto: '',
    pilar,
    question_id: '',
    impacto: null,
    viabilidade: null,
    probabilidade: null,
    evidencia: '',
    prioridade: null,
    tows: true,
  }
}

export function emptySwotInitiative(): SwotInitiative {
  return { acao: '', dono: '', horizonte: '', itens_internos: [], itens_externos: [] }
}

export function normalizeSwotItem(raw: SwotItem | string | Partial<SwotItem>): SwotItem {
  if (typeof raw === 'string') {
    return { ...emptySwotItem(), texto: raw }
  }
  return {
    id: raw.id || '',
    texto: raw.texto || '',
    pilar: raw.pilar || '',
    question_id: raw.question_id || '',
    impacto: raw.impacto ?? null,
    viabilidade: raw.viabilidade ?? null,
    probabilidade: raw.probabilidade ?? null,
    evidencia: raw.evidencia || '',
    prioridade: raw.prioridade ?? null,
    tows: raw.tows !== false,
  }
}

export function slugifyPillar(raw: string): string {
  return raw
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 40)
}

export function pillarLabel(pilarId: string): string {
  const id = (pilarId || '').trim().toLowerCase()
  if (!id) return ''
  return PILLAR_BY_ID[id as Exclude<SwotPilarId, ''>]?.name || pilarId
}
