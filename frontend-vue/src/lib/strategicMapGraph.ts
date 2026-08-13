/**
 * Deriva o mapa visual (5 colunas, fios, panorama, atos) a partir da árvore
 * maturidade → SWOT → TOWS → OKR → projetos.
 */
import type {
  StrategicMap,
  StrategicMapDimension,
  StrategicMapInitiative,
  StrategicMapItem,
  StrategicMapObjective,
  StrategicMapOrphanProject,
  StrategicMapProject,
  StrategicMapQuestion,
} from '@/api/strategicMap'
import type { SwotListField, SwotTowsField, SwotWatchlistItem } from '@/api/swotAnalysis'

export type MapLens = 'pan' | 'ges' | 'lin'
export type MapTone = 'ok' | 'warn' | 'risk' | 'neutral'
export type EdgeKind = 'main' | 'hot' | 'sec' | 'dash'
export type NodeKind = 'dim' | 'quad' | 'watch' | 'tows' | 'obj' | 'proj'

export type MapNode = {
  id: string
  kind: NodeKind
  column: 1 | 2 | 3 | 4 | 5
  title: string
  subtitle: string
  tone: MapTone
  accent: string
  labelId: string
  statusLabel: string
  body: string
  trail: string
  next: string
  ask: string
  dimId?: string
  quadrant?: SwotListField
  towsField?: SwotTowsField
  objectiveId?: string
  projectId?: string
  itemIds: string[]
  initiativeIds: string[]
}

export type MapEdge = {
  from: string
  to: string
  kind: EdgeKind
}

export type ApostaCard = {
  towsField: SwotTowsField
  prio: number
  kindLabel: string
  title: string
  blurb: string
  tone: MapTone
  meta: string
}

export type Panorama = {
  reading: string
  apostas: ApostaCard[]
  alertTitle: string
  alertBody: string
}

export type PresentAct = {
  kicker: string
  title: string
  caption: string
  focusId: string
}

export type MapColumn = {
  roman: string
  title: string
  nodes: MapNode[]
}

export type StrategicMapGraph = {
  columns: MapColumn[]
  nodes: MapNode[]
  nodeById: Map<string, MapNode>
  edges: MapEdge[]
  panorama: Panorama | null
  acts: PresentAct[]
  updatedLabel: string
}

export const QUADRANTS: { field: SwotListField; label: string; letter: string; accent: string }[] = [
  { field: 'forcas', label: 'Forças', letter: 'F', accent: 'mn-s' },
  { field: 'fraquezas', label: 'Fraquezas', letter: 'W', accent: 'mn-w' },
  { field: 'oportunidades', label: 'Oportunidade', letter: 'O', accent: 'mn-o' },
  { field: 'ameacas', label: 'Ameaças', letter: 'T', accent: 'mn-t' },
]

export const TOWS_META: Record<
  SwotTowsField,
  {
    code: string
    prio: number
    title: string
    kindLabel: string
    accent: string
    internals: SwotListField
    externals: SwotListField
  }
> = {
  tows_fxa: {
    code: 'WT',
    prio: 1,
    title: 'Proteger a operação',
    kindLabel: 'Aposta defensiva',
    accent: 'mn-t',
    internals: 'fraquezas',
    externals: 'ameacas',
  },
  tows_fxo: {
    code: 'WO',
    prio: 2,
    title: 'Construir a base',
    kindLabel: 'Aposta estrutural',
    accent: 'mn-a',
    internals: 'fraquezas',
    externals: 'oportunidades',
  },
  tows_fa: {
    code: 'ST',
    prio: 3,
    title: 'Defender a posição',
    kindLabel: 'Aposta de defesa',
    accent: 'mn-o',
    internals: 'forcas',
    externals: 'ameacas',
  },
  tows_fo: {
    code: 'SO',
    prio: 4,
    title: 'Capturar valor',
    kindLabel: 'Aposta ofensiva',
    accent: 'mn-s',
    internals: 'forcas',
    externals: 'oportunidades',
  },
}

export const TOWS_ORDER: SwotTowsField[] = ['tows_fxa', 'tows_fxo', 'tows_fa', 'tows_fo']

export const DIM_ACCENT: Record<string, string> = {
  strategy: 'mn-strategy',
  data_infra: 'mn-data',
  people_culture: 'mn-people',
  gov_risk: 'mn-gov',
}

const PILAR_TO_DIM: Record<string, string> = {
  portfolio: 'strategy',
  dados: 'data_infra',
  infraestrutura: 'data_infra',
  talento: 'people_culture',
  cultura: 'people_culture',
  governanca: 'gov_risk',
}

const ROMAN = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII']
const WATCH_ID = 'sm-watch'
const CANVAS_QUADRANT_LABEL: Record<string, string> = {
  ganho_rapido: 'ganho rápido',
  aposta_estrategica: 'aposta estratégica',
  incremental: 'incremental',
  evitar: 'evitar',
}

function clip(text: string, max: number): string {
  const value = (text || '').trim()
  if (!value) return ''
  return value.length <= max ? value : `${value.slice(0, max - 1).trimEnd()}…`
}

function avgOf(dim: StrategicMapDimension): number {
  const avg = Number(dim.score?.avg)
  if (Number.isFinite(avg) && avg > 0) return avg
  const max = Number(dim.score?.max) || 0
  const score = Number(dim.score?.score) || 0
  return max ? (score / max) * 5 : 0
}

function toneFromAvg(avg: number): MapTone {
  if (avg >= 3.5) return 'ok'
  if (avg >= 2.5) return 'warn'
  if (avg > 0) return 'risk'
  return 'neutral'
}

function toneFromProgress(pct: number | null | undefined): MapTone {
  if (pct == null || Number.isNaN(pct)) return 'neutral'
  if (pct < 25) return 'risk'
  if (pct < 50) return 'warn'
  return 'ok'
}

function progressLabel(pct: number | null | undefined): string {
  if (pct == null || Number.isNaN(pct)) return 'sem progresso'
  if (pct < 25) return 'em risco'
  if (pct < 50) return 'atenção'
  return 'no ritmo'
}

function itemCode(item: StrategicMapItem): string {
  const id = (item.id || '').trim()
  if (!id) return '—'
  if (id.startsWith('fx_')) return `W-${id.slice(3).toUpperCase()}`
  if (id.startsWith('f_')) return `F-${id.slice(2).toUpperCase()}`
  if (id.startsWith('o_')) return `O-${id.slice(2).toUpperCase()}`
  if (id.startsWith('a_')) return `A-${id.slice(2).toUpperCase()}`
  return id.toUpperCase()
}

function joinTrail(parts: string[], max = 6): string {
  const clean = parts.map((p) => p.trim()).filter(Boolean)
  if (!clean.length) return '—'
  if (clean.length <= max) return clean.join(' · ')
  return `${clean.slice(0, max).join(' · ')} · +${clean.length - max}`
}

function unique<T>(items: T[], key: (item: T) => string): T[] {
  const seen = new Set<string>()
  const out: T[] = []
  for (const item of items) {
    const id = key(item)
    if (!id || seen.has(id)) continue
    seen.add(id)
    out.push(item)
  }
  return out
}

type Flat = {
  items: StrategicMapItem[]
  itemsById: Map<string, StrategicMapItem>
  itemsByQuad: Record<SwotListField, StrategicMapItem[]>
  itemsByDim: Map<string, StrategicMapItem[]>
  watchlist: SwotWatchlistItem[]
  watchByDim: Map<string, SwotWatchlistItem[]>
  initiatives: StrategicMapInitiative[]
  initiativesByField: Record<SwotTowsField, StrategicMapInitiative[]>
  objectives: StrategicMapObjective[]
  projects: Array<StrategicMapProject | StrategicMapOrphanProject>
  linkedProjectIds: Set<string>
  questionsById: Map<string, { dim: StrategicMapDimension; question: StrategicMapQuestion }>
}

function flatten(doc: StrategicMap): Flat {
  const items: StrategicMapItem[] = []
  const itemsById = new Map<string, StrategicMapItem>()
  const itemsByQuad: Record<SwotListField, StrategicMapItem[]> = {
    forcas: [],
    fraquezas: [],
    oportunidades: [],
    ameacas: [],
  }
  const itemsByDim = new Map<string, StrategicMapItem[]>()
  const watchlist: SwotWatchlistItem[] = []
  const watchByDim = new Map<string, SwotWatchlistItem[]>()
  const initiativeMap = new Map<string, StrategicMapInitiative>()
  const objectiveMap = new Map<string, StrategicMapObjective>()
  const projectMap = new Map<string, StrategicMapProject | StrategicMapOrphanProject>()
  const linkedProjectIds = new Set<string>()
  const questionsById = new Map<string, { dim: StrategicMapDimension; question: StrategicMapQuestion }>()

  const pushItem = (item: StrategicMapItem, dimId?: string) => {
    if (!item?.id || itemsById.has(item.id)) {
      if (dimId && item?.id) {
        const bucket = itemsByDim.get(dimId) ?? []
        if (!bucket.some((it) => it.id === item.id)) {
          bucket.push(item)
          itemsByDim.set(dimId, bucket)
        }
      }
      return
    }
    itemsById.set(item.id, item)
    items.push(item)
    if (item.quadrant) itemsByQuad[item.quadrant]?.push(item)
    const targetDim = dimId || PILAR_TO_DIM[item.pilar]
    if (targetDim) {
      const bucket = itemsByDim.get(targetDim) ?? []
      bucket.push(item)
      itemsByDim.set(targetDim, bucket)
    }
  }

  const pushInit = (initiative: StrategicMapInitiative) => {
    if (!initiative?.id || initiativeMap.has(initiative.id)) return
    initiativeMap.set(initiative.id, initiative)
  }

  const pushObj = (objective: StrategicMapObjective) => {
    if (!objective?.id || objectiveMap.has(objective.id)) return
    objectiveMap.set(objective.id, objective)
  }

  const pushProject = (project: StrategicMapProject | StrategicMapOrphanProject, linked: boolean) => {
    if (!project?.id) return
    if (!projectMap.has(project.id)) projectMap.set(project.id, project)
    if (linked) linkedProjectIds.add(project.id)
  }

  const walkObjective = (objective: StrategicMapObjective, linkedProjects: boolean) => {
    pushObj(objective)
    for (const kr of objective.key_results) {
      for (const project of kr.projects) pushProject(project, linkedProjects)
    }
  }

  const walkItem = (item: StrategicMapItem, dimId?: string) => {
    pushItem(item, dimId)
    for (const initiative of item.initiatives) {
      pushInit(initiative)
      for (const objective of initiative.objectives) walkObjective(objective, true)
      for (const project of initiative.projects) pushProject(project, true)
    }
    for (const objective of item.objectives) walkObjective(objective, true)
    for (const project of item.projects) pushProject(project, true)
  }

  for (const dim of doc.dimensions) {
    for (const question of dim.questions) {
      questionsById.set(question.id.toLowerCase(), { dim, question })
      watchlist.push(...question.watchlist)
      if (question.watchlist.length) {
        const bucket = watchByDim.get(dim.id) ?? []
        bucket.push(...question.watchlist)
        watchByDim.set(dim.id, bucket)
      }
      for (const item of question.items) walkItem(item, dim.id)
    }
  }

  for (const item of doc.unlinked.swot_items) walkItem(item)
  for (const initiative of doc.unlinked.initiatives) {
    pushInit(initiative)
    for (const objective of initiative.objectives) walkObjective(objective, true)
    for (const project of initiative.projects) pushProject(project, true)
  }
  for (const entry of doc.unlinked.watchlist) {
    watchlist.push(entry)
    const dimId = PILAR_TO_DIM[entry.pilar]
    if (dimId) {
      const bucket = watchByDim.get(dimId) ?? []
      bucket.push(entry)
      watchByDim.set(dimId, bucket)
    }
  }
  for (const objective of doc.unlinked.objectives) walkObjective(objective, false)
  for (const project of doc.unlinked.projects) pushProject(project, false)

  const initiatives = [...initiativeMap.values()]
  const initiativesByField = {
    tows_fo: [] as StrategicMapInitiative[],
    tows_fa: [] as StrategicMapInitiative[],
    tows_fxo: [] as StrategicMapInitiative[],
    tows_fxa: [] as StrategicMapInitiative[],
  }
  for (const initiative of initiatives) {
    if (initiative.field in initiativesByField) initiativesByField[initiative.field].push(initiative)
  }

  return {
    items,
    itemsById,
    itemsByQuad,
    itemsByDim,
    watchlist: unique(watchlist, (w) => w.id || w.texto),
    watchByDim,
    initiatives,
    initiativesByField,
    objectives: [...objectiveMap.values()],
    projects: [...projectMap.values()],
    linkedProjectIds,
    questionsById,
  }
}

function dimStatusLabel(dim: StrategicMapDimension, all: StrategicMapDimension[]): string {
  const avg = avgOf(dim)
  const avgs = all.map(avgOf).filter((n) => n > 0)
  const maxAvg = avgs.length ? Math.max(...avgs) : 0
  const minAvg = avgs.length ? Math.min(...avgs) : 0
  if (avg >= 3 && avg === maxAvg) return 'Melhor pilar'
  if (avg > 0 && avg === minAvg && avg < 2.5) return 'Ponto crítico'
  if (avg >= 3.5) return 'Acima da média'
  if (avg >= 2.5) return 'Limita a escala'
  if (avg > 0) return 'Crítico'
  return 'Sem nota'
}

function projectTone(project: StrategicMapProject, objectives: StrategicMapObjective[]): MapTone {
  const krs = objectives.flatMap((obj) => obj.key_results).filter((kr) => kr.projects.some((p) => p.id === project.id))
  if (krs.length) {
    const worst = Math.min(...krs.map((kr) => kr.progress_pct))
    return toneFromProgress(worst)
  }
  if (project.quadrant === 'evitar') return 'warn'
  return 'ok'
}

function projectProgressHint(project: StrategicMapProject, objectives: StrategicMapObjective[]): string {
  const krs = objectives.flatMap((obj) => obj.key_results).filter((kr) => kr.projects.some((p) => p.id === project.id))
  if (krs.length) {
    const avg = krs.reduce((sum, kr) => sum + kr.progress_pct, 0) / krs.length
    return `${Math.round(avg)}% · ${progressLabel(avg)}`
  }
  if (project.quadrant) {
    const label = CANVAS_QUADRANT_LABEL[project.quadrant]
    if (label) return label
  }
  return project.area_negocio || 'canvas'
}

function objectiveTone(objective: StrategicMapObjective): MapTone {
  if (objective.progress_pct != null) return toneFromProgress(objective.progress_pct)
  if (!objective.key_results.length) return 'neutral'
  const worst = Math.min(...objective.key_results.map((kr) => kr.progress_pct))
  return toneFromProgress(worst)
}

function towsTone(field: SwotTowsField, objectives: StrategicMapObjective[]): MapTone {
  if (objectives.length) {
    const worst = objectives.reduce<MapTone>((acc, obj) => {
      const tone = objectiveTone(obj)
      if (tone === 'risk' || acc === 'risk') return 'risk'
      if (tone === 'warn' || acc === 'warn') return 'warn'
      if (tone === 'ok' || acc === 'ok') return 'ok'
      return acc
    }, 'neutral')
    if (worst !== 'neutral') return worst
  }
  if (field === 'tows_fxa') return 'risk'
  if (field === 'tows_fxo') return 'warn'
  return 'ok'
}

function dimBody(dim: StrategicMapDimension): string {
  const lines = dim.questions.slice(0, 4).map((q) => {
    const hint = clip(q.answer_text || q.text, 90)
    return `${q.id}·${q.answer}${hint ? ` — ${hint}` : ''}`
  })
  const extra = dim.questions.length > 4 ? ` (+${dim.questions.length - 4} pergunta(s))` : ''
  return lines.length ? `${lines.join(' ')}${extra}` : `${dim.name} sem perguntas visíveis nesta abrangência.`
}

function dimTrail(dim: StrategicMapDimension, watch: SwotWatchlistItem[]): string {
  const parts: string[] = []
  for (const question of dim.questions) {
    const codes = question.items.map(itemCode)
    const watchHit = watch.some((w) => w.id?.toLowerCase() === question.id.toLowerCase())
    if (codes.length) parts.push(`${question.id}·${question.answer} → ${codes.join('/')}`)
    else if (watchHit) parts.push(`${question.id}·${question.answer} → atenção`)
  }
  return joinTrail(parts, 5)
}

function dimNext(dim: StrategicMapDimension, towsHits: SwotTowsField[], objectives: StrategicMapObjective[]): string {
  if (towsHits.length) {
    const names = towsHits.map((field) => TOWS_META[field].title)
    const obj = objectives[0]
    const lead = names[0] || names.join(', ')
    return obj
      ? `Converge para ${lead} → ${clip(obj.titulo, 80)}.`
      : `Converge para ${names.join(', ')}.`
  }
  const avg = avgOf(dim)
  if (avg > 0 && avg < 2.5) return 'Este pilar ainda não virou aposta TOWS — priorize o cruzamento na SWOT.'
  return 'Acompanhe no próximo ciclo se o pilar se mantém como força.'
}

function dimAsk(dim: StrategicMapDimension): string {
  const avg = avgOf(dim)
  if (avg > 0 && avg < 2.5) return `Quem responde por «${dim.name}» perante a liderança hoje?`
  if (avg >= 3.5) return `Estamos usando «${dim.name}» — ou apenas celebrando o score?`
  return `Qual movimento neste pilar destrava mais valor neste ciclo?`
}

function quadBody(items: StrategicMapItem[]): string {
  if (!items.length) return 'Nenhum item neste quadrante.'
  const lines = items.slice(0, 4).map((item) => `${itemCode(item)} · ${clip(item.texto, 110)}`)
  const extra = items.length > 4 ? ` (+${items.length - 4})` : ''
  return `${lines.join(' ')}${extra}`
}

function quadTrail(items: StrategicMapItem[], questionsById: Flat['questionsById']): string {
  const parts = items.slice(0, 8).map((item) => {
    const origin = questionsById.get((item.question_id || '').toLowerCase())
    return origin ? `${origin.question.id}·${origin.question.answer} → ${itemCode(item)}` : itemCode(item)
  })
  return joinTrail(parts, 6)
}

function quadNext(field: SwotListField, towsHits: SwotTowsField[]): string {
  if (!towsHits.length) {
    return field === 'fraquezas' || field === 'ameacas'
      ? 'Ainda não entra em cruzamento TOWS — revise o editor da SWOT.'
      : 'Ainda não alimenta uma aposta TOWS.'
  }
  return `Alimenta ${towsHits.map((f) => TOWS_META[f].title).join(', ')}.`
}

function quadAsk(field: SwotListField): string {
  if (field === 'fraquezas') return 'Qual fraqueza, se nada for feito, custa mais caro em 12 meses?'
  if (field === 'ameacas') return 'Qual dessas ameaças a companhia menos toleraria ver no noticiário?'
  if (field === 'forcas') return 'Estamos usando as forças — ou apenas as celebrando?'
  return 'Quanto vale essa janela — e por quanto tempo fica aberta?'
}

function towsBody(initiatives: StrategicMapInitiative[]): string {
  if (!initiatives.length) return 'Nenhuma estratégia neste quadrante TOWS.'
  const lines = initiatives.slice(0, 4).map((init, i) => `${i + 1}. ${clip(init.acao, 120)}`)
  const extra = initiatives.length > 4 ? ` (+${initiatives.length - 4})` : ''
  return `${lines.join(' ')}${extra}`
}

function towsTrail(
  field: SwotTowsField,
  initiatives: StrategicMapInitiative[],
  itemsById: Map<string, StrategicMapItem>,
  objectives: StrategicMapObjective[],
): string {
  const meta = TOWS_META[field]
  const parts = initiatives.slice(0, 4).map((init, i) => {
    const internals = init.itens_internos
      .map((id) => itemsById.get(id))
      .filter(Boolean)
      .map((item) => itemCode(item!))
    const externals = init.counterparts.map((c) => {
      const item = itemsById.get(c.id)
      return item ? itemCode(item) : clip(c.texto, 24)
    })
    const left = internals[0] || meta.internals[0]?.toUpperCase()
    const right = externals[0] || meta.externals[0]?.toUpperCase()
    return `${left}×${right} → ${meta.code}-${i + 1}`
  })
  if (objectives.length) parts.push(`→ ${objectives.map((o) => clip(o.titulo, 40)).join(' / ')}`)
  return joinTrail(parts, 5)
}

function towsNext(objectives: StrategicMapObjective[], projects: StrategicMapProject[]): string {
  if (objectives.length) {
    const names = objectives.map((o) => clip(o.titulo, 60)).join(', ')
    return projects.length
      ? `Promovida a ${names}, com ${projects.length} projeto(s) em entrega.`
      : `Promovida a ${names} — ainda sem projeto de entrega.`
  }
  if (projects.length) return `${projects.length} projeto(s) já nascem daqui, sem Objective vinculado.`
  return 'Sem Objective nem projeto — abra OKR ou o canvas para promover esta aposta.'
}

function towsAsk(field: SwotTowsField): string {
  if (field === 'tows_fxa') return 'O que precisa ser verdade neste ciclo para este risco sair de crítico?'
  if (field === 'tows_fxo') return 'A base que estamos construindo serve ao caso de uso nº 1?'
  if (field === 'tows_fa') return 'A experimentação da ponta já tem para onde ir com segurança?'
  return 'Qual caso de uso conta a melhor história de valor até o fim do ciclo?'
}

function objBody(objective: StrategicMapObjective): string {
  const dono = objective.dono ? `Dono: ${objective.dono}. ` : ''
  if (!objective.key_results.length) {
    return `${dono}${clip(objective.descricao, 220) || 'Sem Key Results ainda.'}`
  }
  const krs = objective.key_results
    .slice(0, 4)
    .map((kr, i) => `KR-${i + 1} ${clip(kr.titulo, 50)} (${Math.round(kr.progress_pct)}%)`)
  return `${dono}${krs.join('; ')}.`
}

function objTrail(objective: StrategicMapObjective, towsHits: SwotTowsField[], projects: StrategicMapProject[]): string {
  const left = towsHits.length ? towsHits.map((f) => TOWS_META[f].code).join('/') : 'origem SWOT'
  const right = projects.length ? projects.map((p) => clip(p.title, 28)).join(' · ') : 'sem projeto'
  return `${left} → ${clip(objective.titulo, 40)} → ${right}`
}

function objNext(objective: StrategicMapObjective): string {
  const lagging = [...objective.key_results].sort((a, b) => a.progress_pct - b.progress_pct)[0]
  const project = lagging?.projects[0]
  if (lagging && project) {
    return project.proximo_passo
      ? `Destravar «${clip(project.title, 40)}»: ${clip(project.proximo_passo, 120)}`
      : `O KR mais atrasado (${clip(lagging.titulo, 40)}) depende de «${clip(project.title, 40)}».`
  }
  if (lagging) return `O KR mais atrasado é «${clip(lagging.titulo, 80)}» (${Math.round(lagging.progress_pct)}%).`
  return 'Inclua Key Results para este Objective entrar na gestão do ciclo.'
}

function objAsk(objective: StrategicMapObjective): string {
  const lagging = [...objective.key_results].sort((a, b) => a.progress_pct - b.progress_pct)[0]
  if (lagging && lagging.progress_pct < 30) {
    return `O que destrava «${clip(lagging.titulo, 60)}» nesta reunião?`
  }
  return `O ritmo de «${clip(objective.titulo, 60)}» ainda é o compromisso certo?`
}

function projBody(project: StrategicMapProject, objectives: StrategicMapObjective[]): string {
  const krs = objectives.flatMap((obj) =>
    obj.key_results.filter((kr) => kr.projects.some((p) => p.id === project.id)).map((kr) => clip(kr.titulo, 40)),
  )
  const bits = [
    project.area_negocio && `Área: ${project.area_negocio}`,
    project.quadrant && CANVAS_QUADRANT_LABEL[project.quadrant]
      ? `Matriz: ${CANVAS_QUADRANT_LABEL[project.quadrant]}`
      : '',
    krs.length ? `Entrega: ${krs.join(', ')}` : '',
    project.proximo_passo ? `Próximo passo: ${clip(project.proximo_passo, 140)}` : '',
  ].filter(Boolean)
  return bits.join('. ') || 'Projeto no canvas, ainda sem detalhe operacional.'
}

function projTrail(
  project: StrategicMapProject,
  towsHits: SwotTowsField[],
  objectives: StrategicMapObjective[],
): string {
  const left = towsHits.length ? towsHits.map((f) => TOWS_META[f].code).join('/') : 'fora do TOWS'
  const mid = objectives.length ? objectives.map((o) => clip(o.titulo, 36)).join(' / ') : 'sem Objective'
  return `${left} → ${mid} → ${clip(project.title, 40)}`
}

function projNext(project: StrategicMapProject): string {
  return project.proximo_passo
    ? clip(project.proximo_passo, 200)
    : 'Complete o próximo passo no canvas para este nó virar gestão.'
}

function projAsk(project: StrategicMapProject, tone: MapTone): string {
  if (tone === 'risk') return `Assumimos um plano B para «${clip(project.title, 50)}» ou destravamos agora?`
  if (project.proximo_passo) return `O próximo passo ainda é o movimento certo?`
  return `Este projeto entra no portfólio — ou fica só no canvas?`
}

function formatUpdated(iso: string | null | undefined): string {
  if (!iso) return 'atualizado · —'
  try {
    const date = new Date(iso)
    return `atualizado · ${date.toLocaleDateString('pt-BR', { day: '2-digit', month: 'short' })} ${date.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}`
  } catch {
    return 'atualizado · —'
  }
}

function maturityLine(doc: StrategicMap): string {
  const result = doc.source.result
  if (!result) return ''
  const avg5 = result.max_score ? (result.total_score / result.max_score) * 5 : 0
  const score = avg5 ? avg5.toFixed(1).replace('.', ',') : `${Math.round(result.percent_score)}%`
  return `maturidade ${score}${result.level_label ? ` · ${result.level_label}` : ''}`
}

export function lineageOf(id: string, edges: MapEdge[]): Set<string> {
  const anc = new Set<string>([id])
  const des = new Set<string>([id])
  let changed = true
  while (changed) {
    changed = false
    for (const edge of edges) {
      if (anc.has(edge.to) && !anc.has(edge.from)) {
        anc.add(edge.from)
        changed = true
      }
    }
  }
  changed = true
  while (changed) {
    changed = false
    for (const edge of edges) {
      if (des.has(edge.from) && !des.has(edge.to)) {
        des.add(edge.to)
        changed = true
      }
    }
  }
  return new Set([...anc, ...des])
}

export function visibleEdges(edges: MapEdge[], lens: MapLens, watchId = WATCH_ID): MapEdge[] {
  return edges.filter((edge) => {
    if (lens === 'pan') return false
    if (lens === 'ges' && edge.kind === 'sec') return false
    if (lens !== 'lin' && (edge.from === watchId || edge.to === watchId)) return false
    return true
  })
}

export function emptyGraph(): StrategicMapGraph {
  return {
    columns: [
      { roman: 'I', title: 'Diagnóstico', nodes: [] },
      { roman: 'II', title: 'Posições', nodes: [] },
      { roman: 'III', title: 'Estratégias', nodes: [] },
      { roman: 'IV', title: 'Compromissos', nodes: [] },
      { roman: 'V', title: 'Entrega', nodes: [] },
    ],
    nodes: [],
    nodeById: new Map(),
    edges: [],
    panorama: null,
    acts: [],
    updatedLabel: '',
  }
}

export function buildStrategicMapGraph(doc: StrategicMap | null): StrategicMapGraph {
  if (!doc) return emptyGraph()
  const flat = flatten(doc)
  const nodes: MapNode[] = []
  const edges: MapEdge[] = []

  const dimNodes: MapNode[] = doc.dimensions.map((dim, index) => {
    const avg = avgOf(dim)
    const items = flat.itemsByDim.get(dim.id) ?? []
    const watch = flat.watchByDim.get(dim.id) ?? []
    const towsHits = TOWS_ORDER.filter((field) => {
      const meta = TOWS_META[field]
      return items.some(
        (item) =>
          item.quadrant === meta.internals ||
          item.quadrant === meta.externals ||
          item.initiatives.some((init) => init.field === field) ||
          item.used_in > 0,
      )
    })
    const objectives = unique(
      items.flatMap((item) => [
        ...item.objectives,
        ...item.initiatives.flatMap((init) => init.objectives),
      ]),
      (o) => o.id,
    )
    const tone = toneFromAvg(avg)
    const scoreLabel = avg ? `${avg.toFixed(1).replace('.', ',')} / 5,0` : `${dim.score.pct}%`
    return {
      id: `sm-dim-${dim.id}`,
      kind: 'dim' as const,
      column: 1 as const,
      title: dim.name,
      subtitle: `${scoreLabel} · ${dimStatusLabel(dim, doc.dimensions).toLowerCase()}`,
      tone,
      accent: DIM_ACCENT[dim.id] || '',
      labelId: `PILAR ${ROMAN[index] || index + 1}`,
      statusLabel: dimStatusLabel(dim, doc.dimensions),
      body: dimBody(dim),
      trail: dimTrail(dim, watch),
      next: dimNext(dim, towsHits, objectives),
      ask: dimAsk(dim),
      dimId: dim.id,
      itemIds: items.map((i) => i.id),
      initiativeIds: unique(
        items.flatMap((i) => i.initiatives),
        (init) => init.id,
      ).map((init) => init.id),
    }
  })
  nodes.push(...dimNodes)

  const quadNodes: MapNode[] = QUADRANTS.map((quad) => {
    const items = flat.itemsByQuad[quad.field]
    const towsHits = TOWS_ORDER.filter((field) => {
      const meta = TOWS_META[field]
      if (quad.field === meta.internals) {
        return items.some((item) => item.initiatives.some((init) => init.field === field))
      }
      if (quad.field === meta.externals) {
        return flat.initiativesByField[field].some((init) =>
          init.counterparts.some((c) => items.some((item) => item.id === c.id)),
        )
      }
      return false
    })
    const negative = quad.field === 'fraquezas' || quad.field === 'ameacas'
    const tone: MapTone = !items.length ? 'neutral' : negative ? 'risk' : 'ok'
    const codes = items.slice(0, 3).map(itemCode).join(', ')
    return {
      id: `sm-quad-${quad.field}`,
      kind: 'quad' as const,
      column: 2 as const,
      title: quad.label,
      subtitle: items.length
        ? `${items.length} ${items.length === 1 ? 'item' : 'itens'}${codes ? ` · ${codes}` : ''}`
        : 'sem itens',
      tone,
      accent: quad.accent,
      labelId: quad.label.toUpperCase(),
      statusLabel: !items.length ? 'Vazio' : negative ? `${items.length} em jogo` : 'Ativos do ciclo',
      body: quadBody(items),
      trail: quadTrail(items, flat.questionsById),
      next: quadNext(quad.field, towsHits),
      ask: quadAsk(quad.field),
      quadrant: quad.field,
      itemIds: items.map((i) => i.id),
      initiativeIds: unique(
        items.flatMap((i) => i.initiatives),
        (init) => init.id,
      ).map((init) => init.id),
    }
  }).filter((node) => node.itemIds.length > 0)
  nodes.push(...quadNodes)

  if (flat.watchlist.length) {
    const dimHits = [...flat.watchByDim.entries()].filter(([, list]) => list.length).map(([id]) => id)
    nodes.push({
      id: WATCH_ID,
      kind: 'watch',
      column: 2,
      title: 'Em atenção',
      subtitle: `${flat.watchlist.length} ${flat.watchlist.length === 1 ? 'item' : 'itens'} · notas 3`,
      tone: 'warn',
      accent: 'mn-a',
      labelId: 'ATENÇÃO',
      statusLabel: 'Notas 3',
      body: flat.watchlist
        .slice(0, 4)
        .map((w) => `${w.id || '·'} · ${clip(w.texto, 110)}`)
        .join(' ') + (flat.watchlist.length > 4 ? ` (+${flat.watchlist.length - 4})` : ''),
      trail: joinTrail(
        flat.watchlist.slice(0, 8).map((w) => `${w.id || 'nota 3'} → atenção`),
        6,
      ),
      next: 'Reavaliar na reaplicação do diagnóstico — podem virar força ou fraqueza.',
      ask: 'Qual destes pontos merece virar meta já neste ciclo?',
      itemIds: flat.watchlist.map((w) => w.id).filter(Boolean),
      initiativeIds: [],
    })
    for (const dimId of dimHits) {
      edges.push({ from: `sm-dim-${dimId}`, to: WATCH_ID, kind: 'sec' })
    }
  }

  const towsNodes: MapNode[] = TOWS_ORDER.flatMap((field) => {
    const initiatives = flat.initiativesByField[field]
    if (!initiatives.length) return []
    const meta = TOWS_META[field]
    const objectives = unique(
      initiatives.flatMap((init) => init.objectives),
      (o) => o.id,
    )
    const projects = unique(
      [
        ...initiatives.flatMap((init) => init.projects),
        ...objectives.flatMap((o) => o.key_results.flatMap((kr) => kr.projects)),
      ],
      (p) => p.id,
    )
    const tone = towsTone(field, objectives)
    const objHint = objectives.length
      ? `${Math.round(
          objectives.reduce((sum, o) => sum + (o.progress_pct ?? 0), 0) / objectives.length,
        )}%`
      : `${initiatives.length} estratégia(s)`
    return [
      {
        id: `sm-tows-${field}`,
        kind: 'tows' as const,
        column: 3 as const,
        title: meta.title,
        subtitle: `${meta.code} · ${initiatives.length} estratégia(s) · prio ${meta.prio}${objectives.length ? ` · ${objHint}` : ''}`,
        tone,
        accent: meta.accent,
        labelId: `${meta.code} · PRIO ${meta.prio}`,
        statusLabel:
          tone === 'risk' ? 'Urgência máxima' : tone === 'warn' ? 'Estrutural' : 'Em curso',
        body: towsBody(initiatives),
        trail: towsTrail(field, initiatives, flat.itemsById, objectives),
        next: towsNext(objectives, projects),
        ask: towsAsk(field),
        towsField: field,
        itemIds: unique(
          initiatives.flatMap((init) => [...init.itens_internos, ...init.counterparts.map((c) => c.id)]),
          (id) => id,
        ),
        initiativeIds: initiatives.map((init) => init.id),
      },
    ]
  })
  nodes.push(...towsNodes)

  const linkedObjectives = flat.objectives.filter(
    (obj) => obj.tows_ids.length > 0 || obj.swot_item_ids.length > 0,
  )
  const showObjectives = linkedObjectives.length ? linkedObjectives : flat.objectives
  const objNodes: MapNode[] = showObjectives.map((objective, index) => {
    const towsHits = TOWS_ORDER.filter(
      (field) =>
        objective.tows_ids.some((id) => flat.initiativesByField[field].some((init) => init.id === id)) ||
        flat.initiativesByField[field].some((init) => init.objectives.some((o) => o.id === objective.id)),
    )
    const projects = unique(
      objective.key_results.flatMap((kr) => kr.projects),
      (p) => p.id,
    )
    const tone = objectiveTone(objective)
    const pct = objective.progress_pct
    const riskKrs = objective.key_results.filter((kr) => kr.progress_pct < 25).length
    return {
      id: `sm-obj-${objective.id}`,
      kind: 'obj' as const,
      column: 4 as const,
      title: objective.titulo || `Objective ${index + 1}`,
      subtitle: `${objective.key_results.length} KR(s)${pct != null ? ` · ${Math.round(pct)}%` : ''}${
        riskKrs ? ` · ${riskKrs} em risco` : ` · ${progressLabel(pct)}`
      }`,
      tone,
      accent: '',
      labelId: `OBJ-${String(index + 1).padStart(2, '0')}`,
      statusLabel: pct != null ? `${Math.round(pct)}% · ${progressLabel(pct)}` : 'Sem KR',
      body: objBody(objective),
      trail: objTrail(objective, towsHits, projects),
      next: objNext(objective),
      ask: objAsk(objective),
      objectiveId: objective.id,
      itemIds: objective.swot_item_ids,
      initiativeIds: objective.tows_ids,
    }
  })
  nodes.push(...objNodes)

  const linkedProjects = flat.projects.filter((p) => flat.linkedProjectIds.has(p.id))
  const showProjects = linkedProjects.length ? linkedProjects : flat.projects
  const projNodes: MapNode[] = showProjects.map((project, index) => {
    const relatedObjectives = flat.objectives.filter((obj) =>
      obj.key_results.some((kr) => kr.projects.some((p) => p.id === project.id)),
    )
    const towsHits = TOWS_ORDER.filter((field) =>
      flat.initiativesByField[field].some(
        (init) =>
          init.projects.some((p) => p.id === project.id) ||
          init.objectives.some((o) => relatedObjectives.some((ro) => ro.id === o.id)),
      ),
    )
    const tone = projectTone(project, relatedObjectives)
    return {
      id: `sm-proj-${project.id}`,
      kind: 'proj' as const,
      column: 5 as const,
      title: project.title || `Projeto ${index + 1}`,
      subtitle: projectProgressHint(project, relatedObjectives),
      tone,
      accent: tone === 'risk' ? 'mn-w' : tone === 'warn' ? 'mn-a' : '',
      labelId: `P-${String(index + 1).padStart(2, '0')}`,
      statusLabel: projectProgressHint(project, relatedObjectives),
      body: projBody(project, relatedObjectives),
      trail: projTrail(project, towsHits, relatedObjectives),
      next: projNext(project),
      ask: projAsk(project, tone),
      projectId: project.id,
      itemIds: [],
      initiativeIds: [],
    }
  })
  nodes.push(...projNodes)

  const nodeIds = new Set(nodes.map((n) => n.id))
  const addEdge = (from: string, to: string, kind: EdgeKind = 'main') => {
    if (!nodeIds.has(from) || !nodeIds.has(to)) return
    if (edges.some((e) => e.from === from && e.to === to)) return
    edges.push({ from, to, kind })
  }

  for (const dim of doc.dimensions) {
    const dimId = `sm-dim-${dim.id}`
    const items = flat.itemsByDim.get(dim.id) ?? []
    const quads = new Set(items.map((item) => item.quadrant).filter(Boolean) as SwotListField[])
    const avg = avgOf(dim)
    for (const quad of quads) {
      const kind: EdgeKind =
        avg < 2.5 && (quad === 'fraquezas' || quad === 'ameacas') ? 'hot' : 'sec'
      addEdge(dimId, `sm-quad-${quad}`, kind)
    }
  }

  for (const field of TOWS_ORDER) {
    const meta = TOWS_META[field]
    const towsId = `sm-tows-${field}`
    if (!nodeIds.has(towsId)) continue
    const internalsUsed = flat.initiativesByField[field].some((init) =>
      init.itens_internos.some((id) => flat.itemsByQuad[meta.internals].some((item) => item.id === id)),
    )
    const externalsUsed = flat.initiativesByField[field].some((init) =>
      init.counterparts.some((c) => flat.itemsByQuad[meta.externals].some((item) => item.id === c.id)),
    )
    if (internalsUsed) addEdge(`sm-quad-${meta.internals}`, towsId, field === 'tows_fxa' ? 'hot' : 'main')
    if (externalsUsed) {
      addEdge(
        `sm-quad-${meta.externals}`,
        towsId,
        field === 'tows_fxa' ? 'hot' : field === 'tows_fa' ? 'sec' : 'main',
      )
    }
  }

  const objOwners = new Map<string, SwotTowsField[]>()
  for (const objective of showObjectives) {
    const objId = `sm-obj-${objective.id}`
    const owners = TOWS_ORDER.filter(
      (field) =>
        nodeIds.has(`sm-tows-${field}`) &&
        (objective.tows_ids.some((id) => flat.initiativesByField[field].some((init) => init.id === id)) ||
          flat.initiativesByField[field].some((init) => init.objectives.some((o) => o.id === objective.id))),
    )
    objOwners.set(objective.id, owners)
    const primary = owners[0]
    for (const field of owners) {
      const kind: EdgeKind =
        field === 'tows_fxa' ? 'hot' : primary && field !== primary ? 'dash' : 'main'
      addEdge(`sm-tows-${field}`, objId, kind)
    }
  }

  for (const project of showProjects) {
    const projId = `sm-proj-${project.id}`
    const relatedObjectives = showObjectives.filter((obj) =>
      obj.key_results.some((kr) => kr.projects.some((p) => p.id === project.id)),
    )
    if (relatedObjectives.length) {
      for (const objective of relatedObjectives) {
        const risk = objective.key_results.some(
          (kr) => kr.progress_pct < 25 && kr.projects.some((p) => p.id === project.id),
        )
        addEdge(`sm-obj-${objective.id}`, projId, risk ? 'hot' : 'main')
      }
      continue
    }
    for (const field of TOWS_ORDER) {
      if (flat.initiativesByField[field].some((init) => init.projects.some((p) => p.id === project.id))) {
        addEdge(`sm-tows-${field}`, projId, field === 'tows_fxa' ? 'hot' : 'main')
      }
    }
    for (const item of flat.items) {
      if (item.projects.some((p) => p.id === project.id) && item.quadrant) {
        addEdge(`sm-quad-${item.quadrant}`, projId, 'dash')
      }
    }
  }

  const weakest = [...doc.dimensions].sort((a, b) => avgOf(a) - avgOf(b))[0]
  const criticalTows = towsNodes[0]
  const criticalObj = [...objNodes].sort((a, b) => {
    const rank = (tone: MapTone) => (tone === 'risk' ? 0 : tone === 'warn' ? 1 : 2)
    return rank(a.tone) - rank(b.tone)
  })[0]
  const criticalProj = [...projNodes].sort((a, b) => {
    const rank = (tone: MapTone) => (tone === 'risk' ? 0 : tone === 'warn' ? 1 : 2)
    return rank(a.tone) - rank(b.tone)
  })[0]

  const apostas: ApostaCard[] = towsNodes.slice(0, 3).map((node) => {
    const field = node.towsField!
    const meta = TOWS_META[field]
    const objectives = unique(
      flat.initiativesByField[field].flatMap((init) => init.objectives),
      (o) => o.id,
    )
    const dono = objectives.map((o) => o.dono).filter(Boolean)[0]
    const pct =
      objectives.length && objectives.some((o) => o.progress_pct != null)
        ? Math.round(
            objectives.reduce((sum, o) => sum + (o.progress_pct ?? 0), 0) / objectives.length,
          )
        : null
    const riskKrs = objectives.reduce(
      (n, o) => n + o.key_results.filter((kr) => kr.progress_pct < 25).length,
      0,
    )
    const firstAction = flat.initiativesByField[field][0]?.acao || ''
    return {
      towsField: field,
      prio: meta.prio,
      kindLabel: `${meta.kindLabel} · prio ${meta.prio}`,
      title: node.title,
      blurb: clip(firstAction || node.body, 160),
      tone: node.tone,
      meta: [
        pct != null ? `${pct}%` : `${flat.initiativesByField[field].length} estratégia(s)`,
        riskKrs ? `${riskKrs} KR em risco` : progressLabel(pct),
        dono,
      ]
        .filter(Boolean)
        .join(' · '),
    }
  })

  const maturity = maturityLine(doc)
  const weakLabel = weakest ? `${weakest.name} em ${avgOf(weakest).toFixed(1).replace('.', ',')}` : ''
  const readingParts = [
    maturity ? `Onde estamos: ${maturity}${weakLabel ? ` — ${weakLabel} é o ponto de atenção` : ''}.` : '',
    apostas.length
      ? `O que decidimos: ${apostas.length} aposta(s) em execução${
          apostas[0] ? `, lideradas por «${apostas[0].title}»` : ''
        }.`
      : doc.source.swot_id
        ? 'O que decidimos: a SWOT existe, mas ainda não há cruzamento TOWS promovido.'
        : 'O que decidimos: ainda não há SWOT para virar aposta.',
    criticalProj
      ? `O alerta: «${criticalProj.title}» está ${criticalProj.statusLabel.toLowerCase()}.`
      : criticalObj
        ? `O alerta: «${criticalObj.title}» está ${criticalObj.statusLabel.toLowerCase()}.`
        : weakLabel
          ? `O alerta: ${weakLabel} ainda não virou entrega.`
          : '',
  ].filter(Boolean)

  const panorama: Panorama | null =
    dimNodes.length || apostas.length
      ? {
          reading:
            clip(doc.source.veredito_texto, 360) ||
            readingParts.join(' ') ||
            clip(doc.source.optica, 360) ||
            'O mapa ainda não tem leitura executiva — complete diagnóstico, SWOT e apostas.',
          apostas,
          alertTitle: criticalTows
            ? 'O fio crítico do ciclo'
            : weakLabel
              ? 'O ponto frágil do diagnóstico'
              : 'Sem fio crítico ainda',
          alertBody: criticalTows
            ? [
                weakLabel ? `A nota em ${weakLabel} virou a aposta «${criticalTows.title}»` : `A aposta «${criticalTows.title}»`,
                criticalObj ? `e o compromisso «${criticalObj.title}»` : '',
                criticalProj ? `depende de «${criticalProj.title}» (${criticalProj.statusLabel.toLowerCase()}).` : '.',
              ]
                .filter(Boolean)
                .join(' ')
            : weakLabel
              ? `${weakLabel}. Sem aposta TOWS vinculada, o diagnóstico ainda não virou decisão.`
              : 'Gere a SWOT e o cruzamento TOWS para o mapa ter um fio crítico.',
        }
      : null

  const acts: PresentAct[] = []
  if (weakest && dimNodes.length) {
    const node = dimNodes.find((n) => n.dimId === weakest.id) ?? dimNodes[0]
    if (node) {
      acts.push({
        kicker: 'Ato I',
        title: 'O ponto de partida',
        caption: `${maturity ? `Maturidade em leitura executiva — ` : ''}${node.title}: ${node.subtitle}.`,
        focusId: node.id,
      })
    }
  }
  const negativeQuad = quadNodes.find((n) => n.quadrant === 'fraquezas') || quadNodes.find((n) => n.quadrant === 'ameacas')
  if (negativeQuad) {
    acts.push({
      kicker: 'Ato II',
      title: 'O que o diagnóstico revelou',
      caption: `${negativeQuad.title}: ${negativeQuad.subtitle}. ${clip(negativeQuad.body, 180)}`,
      focusId: negativeQuad.id,
    })
  }
  if (criticalTows) {
    acts.push({
      kicker: 'Ato III',
      title: 'A decisão',
      caption: `A aposta «${criticalTows.title}» (${criticalTows.subtitle}).`,
      focusId: criticalTows.id,
    })
  }
  if (criticalObj) {
    acts.push({
      kicker: 'Ato IV',
      title: 'Os compromissos',
      caption: `${criticalObj.labelId} · ${criticalObj.title} — ${criticalObj.subtitle}.`,
      focusId: criticalObj.id,
    })
  }
  if (criticalProj) {
    acts.push({
      kicker: 'Ato V',
      title: 'A pergunta desta sala',
      caption: criticalProj.ask,
      focusId: criticalProj.id,
    })
  }

  const columns: MapColumn[] = [
    { roman: 'I', title: 'Diagnóstico', nodes: dimNodes },
    { roman: 'II', title: 'Posições', nodes: nodes.filter((n) => n.column === 2) },
    { roman: 'III', title: 'Estratégias', nodes: towsNodes },
    { roman: 'IV', title: 'Compromissos', nodes: objNodes },
    { roman: 'V', title: 'Entrega', nodes: projNodes },
  ]

  return {
    columns,
    nodes,
    nodeById: new Map(nodes.map((n) => [n.id, n])),
    edges,
    panorama,
    acts,
    updatedLabel: formatUpdated(doc.source.swot_updated_at || doc.source.submitted_at),
  }
}
