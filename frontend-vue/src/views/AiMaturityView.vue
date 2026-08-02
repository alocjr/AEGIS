<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import {
  fetchMaturityModel,
  saveMaturityResponse,
  type MaturityDimension,
  type MaturityModel,
  type MaturityQuestion,
  type MaturityTier,
} from '@/api/maturity'

const loading = ref(true)
const error = ref<string | null>(null)
const model = ref<MaturityModel | null>(null)
const answers = ref<Record<string, number>>({})
const selectedTier = ref<MaturityTier>('basico')
const responseId = ref<string | null>(null)
const saveState = ref<'idle' | 'saving' | 'saved' | 'error'>('idle')
const saveError = ref<string | null>(null)
const swotCreated = ref(false)
let persistTimer: ReturnType<typeof setTimeout> | null = null
let persistSeq = 0

const TIER_KEYS: MaturityTier[] = ['basico', 'completo', 'complementar']
const TIER_ORDER: Record<MaturityTier, number> = { basico: 0, completo: 1, complementar: 2 }
const TIER_LABEL_SHORT: Record<MaturityTier, string> = {
  basico: 'Básico',
  completo: 'Completo',
  complementar: 'Complementar',
}
const DIMENSION_COLORS: Record<string, string> = {
  strategy: 'var(--dim-strategy)',
  data_infra: 'var(--dim-data)',
  people_culture: 'var(--dim-people)',
  gov_risk: 'var(--dim-gov)',
}
const DIMENSION_ABBR: Record<string, string> = {
  strategy: 'Est',
  data_infra: 'Dad',
  people_culture: 'Pes',
  gov_risk: 'Gov',
}
const QUAD_LABEL = { s: 'Força', w: 'Fraqueza', o: 'Oportunidade', t: 'Ameaça' } as const

type EnrichedQuestion = MaturityQuestion & { dimId: string; dimName: string }

const questionIndex = computed(() => {
  const idx: Record<string, EnrichedQuestion> = {}
  for (const dim of model.value?.dimensions ?? []) {
    for (const q of dim.questions ?? []) {
      idx[q.id] = { ...q, dimId: dim.id, dimName: dim.name }
    }
  }
  return idx
})

function tierIndexOf(tier: string): number {
  return TIER_ORDER[tier as MaturityTier] ?? 99
}

function isVisibleTier(tier: string): boolean {
  return tierIndexOf(tier) <= tierIndexOf(selectedTier.value)
}

function totalForTier(tier: MaturityTier): number {
  return model.value?.levels?.[tier]?.question_count ?? 0
}

function naturalCompare(a: string, b: string): number {
  const ma = a.match(/^([A-Za-z]+)(\d+)$/)
  const mb = b.match(/^([A-Za-z]+)(\d+)$/)
  const la = ma?.[1] ?? a
  const lb = mb?.[1] ?? b
  const na = Number(ma?.[2] ?? 0)
  const nb = Number(mb?.[2] ?? 0)
  if (la !== lb) return la < lb ? -1 : 1
  return na - nb
}

function sortedQuestions(dim: MaturityDimension): MaturityQuestion[] {
  return [...(dim.questions ?? [])].sort((a, b) => naturalCompare(a.id, b.id))
}

function originLine(q: MaturityQuestion): string {
  if (q.originType === 'modelo_rapido' || q.tier === 'basico') {
    return `Abrangência Básico${q.ref ? ` · ${q.ref}` : ''}`
  }
  if (q.csfId) {
    return `Abrangência ${TIER_LABEL_SHORT[q.tier]} · CSF ${q.csfId}${q.csfName ? ` · ${q.csfName}` : ''}`
  }
  return `Abrangência ${TIER_LABEL_SHORT[q.tier]}`
}

const visibleQuestionIds = computed(() =>
  Object.keys(questionIndex.value).filter((id) => {
    const q = questionIndex.value[id]
    return !!q && isVisibleTier(q.tier)
  })
)

const answeredCount = computed(
  () => visibleQuestionIds.value.filter((id) => answers.value[id] != null).length
)

const totalVisible = computed(() => totalForTier(selectedTier.value))

const isComplete = computed(
  () => totalVisible.value > 0 && answeredCount.value === totalVisible.value
)

const progressPct = computed(() =>
  totalVisible.value ? (answeredCount.value / totalVisible.value) * 100 : 0
)

const progressLabel = computed(() => {
  const answered = answeredCount.value
  const total = totalVisible.value
  if (answered === 0) return 'Nenhuma pergunta respondida ainda'
  if (answered === total) {
    const v = computeVerdict()
    return `Abrangência ${TIER_LABEL_SHORT[selectedTier.value]} concluída · ${v.sum}/${v.maxScore} pts · ${v.band.label}`
  }
  return `${total - answered} pergunta(s) restante(s) na abrangência ${TIER_LABEL_SHORT[selectedTier.value]}`
})

const selectedTierDescription = computed(() => {
  return model.value?.levels?.[selectedTier.value]?.description ?? ''
})

function dimVisibleQuestions(dim: MaturityDimension): MaturityQuestion[] {
  return (dim.questions ?? []).filter((q) => isVisibleTier(q.tier))
}

function dimAnswered(dim: MaturityDimension): MaturityQuestion[] {
  return dimVisibleQuestions(dim).filter((q) => answers.value[q.id] != null)
}

function dimAvg(dim: MaturityDimension): number | null {
  const answered = dimAnswered(dim)
  if (!answered.length) return null
  return answered.reduce((acc, q) => acc + Number(answers.value[q.id]), 0) / answered.length
}

function setTier(key: MaturityTier) {
  if (key === selectedTier.value) return
  selectedTier.value = key
  if (responseId.value || Object.keys(answers.value).length) {
    schedulePersist()
  }
}

function toggleSelect(qid: string, lvl: number) {
  if (answers.value[qid] === lvl) {
    const next = { ...answers.value }
    delete next[qid]
    answers.value = next
  } else {
    answers.value = { ...answers.value, [qid]: lvl }
  }
  schedulePersist()
}

async function persistAnswers() {
  if (!model.value) return
  // Ainda sem respostas e sem documento: não cria registro vazio
  if (!responseId.value && Object.keys(answers.value).length === 0) {
    saveState.value = 'idle'
    return
  }

  const seq = ++persistSeq
  saveState.value = 'saving'
  saveError.value = null
  try {
    const payload: Record<string, number> = { ...answers.value }
    const result = await saveMaturityResponse(payload, selectedTier.value, responseId.value)
    if (seq !== persistSeq) return
    responseId.value = result.id
    saveState.value = 'saved'
  } catch (e) {
    if (seq !== persistSeq) return
    saveState.value = 'error'
    saveError.value = e instanceof Error ? e.message : 'Erro ao salvar.'
  }
}

function schedulePersist() {
  if (persistTimer) clearTimeout(persistTimer)
  persistTimer = setTimeout(() => {
    persistTimer = null
    void persistAnswers()
  }, 280)
}

onMounted(async () => {
  try {
    model.value = await fetchMaturityModel()
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Erro ao carregar modelo.'
  } finally {
    loading.value = false
  }
})

onUnmounted(() => {
  if (persistTimer) clearTimeout(persistTimer)
})

/* ---------- SWOT / verdict ---------- */
type BucketItem = {
  code: string
  lvl: number
  title: string
  dimLabel: string
  evidence: string
  why: string
}
type Buckets = Record<'s' | 'w' | 'o' | 't', BucketItem[]>

function buildBuckets(): Buckets {
  const buckets: Buckets = { s: [], w: [], o: [], t: [] }
  for (const code of Object.keys(answers.value)) {
    const q = questionIndex.value[code]
    if (!q || !isVisibleTier(q.tier)) continue
    const lvl = Number(answers.value[code])
    const evidence = q.levels[String(lvl)] ?? ''
    const isExternal = !!(q.csfId && q.csfId.startsWith('R'))
    let quad: keyof Buckets
    let why: string
    if (isExternal) {
      quad = lvl >= 4 ? 'o' : 't'
      why =
        quad === 'o'
          ? `Requisito regulatório (${q.dimName}) em nível ${lvl}: cenário já favorável — dá para explorar essa vantagem.`
          : `Requisito regulatório (${q.dimName}) em nível ${lvl}: exposição a risco externo — precisa de plano de mitigação.`
    } else {
      quad = lvl >= 4 ? 's' : 'w'
      why =
        quad === 's'
          ? `Dimensão interna (${q.dimName}) em nível ${lvl}: capacidade já madura e controlável pela empresa — pode virar alavanca.`
          : `Dimensão interna (${q.dimName}) em nível ${lvl}: capacidade ainda imatura, mas está sob controle da empresa corrigir.`
    }
    buckets[quad].push({ code, lvl, title: q.text, dimLabel: q.dimName, evidence, why })
  }
  ;(['s', 'w', 'o', 't'] as const).forEach((k) =>
    buckets[k].sort((a, b) => naturalCompare(a.code, b.code))
  )
  return buckets
}

function computeVerdict() {
  const visibleAnswered = Object.keys(answers.value).filter((id) => {
    const q = questionIndex.value[id]
    return !!q && isVisibleTier(q.tier)
  })
  const sum = visibleAnswered.reduce((acc, c) => {
    const q = questionIndex.value[c]
    return acc + Number(answers.value[c]) * (q?.weight || 1)
  }, 0)
  const maxScore = model.value?.levels?.[selectedTier.value]?.max_score ?? totalVisible.value * 5
  const tierScoring = model.value?.scoring?.[selectedTier.value] ?? {}
  let band = { label: '—', description: '' }
  for (const key of ['level_1', 'level_2', 'level_3', 'level_4', 'level_5']) {
    const b = tierScoring[key]
    if (b && sum >= b.min && sum <= b.max) {
      band = { label: b.label ?? key, description: b.description ?? '' }
      break
    }
  }
  const dimAverages = (model.value?.dimensions ?? [])
    .map((dim) => {
      const answered = dimAnswered(dim)
      const avg = answered.length
        ? answered.reduce((a, q) => a + Number(answers.value[q.id]), 0) / answered.length
        : 0
      return { label: dim.name, avg, answeredCount: answered.length }
    })
    .filter((d) => d.answeredCount > 0)
  const strongest = dimAverages.length
    ? dimAverages.reduce((a, b) => (b.avg > a.avg ? b : a))
    : null
  const weakest = dimAverages.length
    ? dimAverages.reduce((a, b) => (b.avg < a.avg ? b : a))
    : null
  return { sum, maxScore, band, strongest, weakest }
}

function escapeHtml(str: string): string {
  return String(str).replace(
    /[&<>"']/g,
    (c) =>
      ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c] as string
  )
}

function pairSentences(
  listA: BucketItem[],
  listB: BucketItem[],
  template: (a: BucketItem, b: BucketItem) => string,
  capacity: number
): string[] {
  if (!listA.length || !listB.length) return []
  const n = Math.min(capacity, Math.max(listA.length, listB.length))
  const out: string[] = []
  for (let i = 0; i < n; i++) {
    const a = listA[i % listA.length]!
    const b = listB[i % listB.length]!
    out.push(template(a, b))
  }
  return [...new Set(out)]
}

function buildTowsCells(buckets: Buckets) {
  return {
    so: pairSentences(
      buckets.s,
      buckets.o,
      (a, b) =>
        `Usar «${a.title}» (força ${a.code}) para aproveitar «${b.title}» (oportunidade ${b.code}).`,
      4
    ),
    st: pairSentences(
      buckets.s,
      buckets.t,
      (a, b) =>
        `Usar «${a.title}» (força ${a.code}) para conter o risco de «${b.title}» (ameaça ${b.code}).`,
      4
    ),
    wo: pairSentences(
      buckets.w,
      buckets.o,
      (a, b) =>
        `Aproveitar «${b.title}» (oportunidade ${b.code}) como janela para corrigir «${a.title}» (fraqueza ${a.code}).`,
      4
    ),
    wt: pairSentences(
      buckets.w,
      buckets.t,
      (a, b) =>
        `Plano defensivo: tratar «${a.title}» (fraqueza ${a.code}) antes que «${b.title}» (ameaça ${b.code}) vire problema real.`,
      4
    ),
  }
}

function quadItemsHtml(items: BucketItem[], q: keyof typeof QUAD_LABEL): string {
  if (!items.length) return `<li class="empty">Nenhuma pergunta classificada aqui.</li>`
  return items
    .map(
      (item) => `
      <li>
        <span class="code">${item.code} · N${item.lvl}</span>
        <span class="lbl">
          <span class="item-title">${escapeHtml(item.title)}</span>
          <span class="pillar-tag">${escapeHtml(item.dimLabel)}</span>
          <span class="why"><b>Por quê ${QUAD_LABEL[q].toLowerCase()}:</b> "${escapeHtml(item.evidence)}" — ${escapeHtml(item.why)}</span>
        </span>
      </li>`
    )
    .join('')
}

function towsItemsHtml(sentences: string[]): string {
  if (!sentences.length) return `<li class="empty">Sem itens suficientes para cruzar nesta combinação.</li>`
  return sentences.map((s) => `<li>${escapeHtml(s)}</li>`).join('')
}

const SWOT_PAGE_CSS = `
  :root{
    --navy:#0e1b33; --ink:#242a33; --gold:#c6a15b; --gold-2:#e3cb93;
    --ivory:#f6f1e7; --ivory-2:#fbf8f1; --muted:#6e6a60;
    --line:rgba(198,161,91,.32); --serif:Cambria,'Hoefler Text',Georgia,'Times New Roman',serif;
    --lvl1:#b6543f; --lvl5:#3f8563; --dim-data:#3d6fa8; --radius:4px;
  }
  *{ box-sizing:border-box; }
  html,body{ margin:0; padding:0; }
  body{
    background:#f8f8f6; color:var(--ink);
    font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','Helvetica Neue',Arial,sans-serif;
    -webkit-font-smoothing:antialiased;
  }
  .page-header{ background:var(--ivory-2); border-bottom:1px solid var(--line); padding:28px 18px; }
  .page-header .inner{ max-width:920px; margin:0 auto; display:flex; align-items:flex-start; justify-content:space-between; gap:16px; flex-wrap:wrap; }
  .page-header .eyebrow{
    font-size:.7rem; letter-spacing:.22em; text-transform:uppercase; color:var(--gold);
    font-weight:600; margin:0 0 6px;
  }
  .page-header h1{
    font-family:var(--serif); font-weight:600; font-size:clamp(22px,4.5vw,32px);
    margin:0 0 6px; color:var(--navy);
  }
  .page-header .meta{ font-size:13px; color:var(--muted); margin:0; }
  .print-btn{
    font-size:11px; font-weight:600; letter-spacing:.06em; text-transform:uppercase;
    padding:9px 16px; border-radius:99px; border:1px solid var(--line);
    background:#fff; color:var(--navy); cursor:pointer; flex:0 0 auto;
  }
  .print-btn:hover{ border-color:var(--gold); color:var(--gold); }
  main{ max-width:920px; margin:0 auto; padding:26px 18px 60px; }
  .swot-section{ margin-bottom:30px; }
  .swot-section-title{
    font-size:.7rem; letter-spacing:.14em; text-transform:uppercase; color:var(--gold);
    font-weight:600; margin:0 0 12px; padding-bottom:6px; border-bottom:1px solid var(--line);
  }
  .swot-rule{ font-size:13px; line-height:1.6; color:var(--muted); max-width:760px; margin:0 0 14px; }
  .swot-rule strong{ color:var(--navy); }
  .swot-grid{ display:grid; grid-template-columns:1fr; gap:12px; }
  .swot-quad{
    background:var(--ivory-2); border:1px solid var(--line); border-radius:var(--radius);
    border-top:4px solid; padding:14px 16px 16px; break-inside:avoid;
  }
  .swot-quad[data-q="s"]{ border-top-color:var(--lvl5); }
  .swot-quad[data-q="w"]{ border-top-color:var(--lvl1); }
  .swot-quad[data-q="o"]{ border-top-color:var(--dim-data); }
  .swot-quad[data-q="t"]{ border-top-color:var(--gold); }
  .swot-quad h3{
    font-family:var(--serif); font-weight:600; font-size:16px; margin:0 0 10px;
    display:flex; align-items:center; gap:8px; color:var(--navy);
  }
  .swot-quad[data-q="s"] h3{ color:var(--lvl5); }
  .swot-quad[data-q="w"] h3{ color:var(--lvl1); }
  .swot-quad[data-q="o"] h3{ color:var(--dim-data); }
  .swot-quad[data-q="t"] h3{ color:var(--gold); }
  .swot-count{
    font-size:11px; font-weight:700; color:var(--muted);
    background:#fff; border:1px solid var(--line); border-radius:99px; padding:1px 8px;
  }
  .swot-quad ul{ list-style:none; margin:0; padding:0; display:flex; flex-direction:column; gap:8px; }
  .swot-quad li{ display:flex; align-items:flex-start; gap:8px; padding:9px 10px; background:#fff; border-radius:3px; border:1px solid rgba(14,27,51,.06); }
  .swot-quad li .code{
    font-size:10.5px; font-weight:700; flex:0 0 auto;
    padding:1px 6px; border-radius:3px; background:var(--ivory); border:1px solid var(--line); margin-top:1px; color:var(--navy);
  }
  .swot-quad li .lbl{ color:var(--ink); flex:1; min-width:0; }
  .swot-quad li .lbl .item-title{ font-size:12.5px; font-weight:600; line-height:1.35; display:block; }
  .swot-quad li .lbl .pillar-tag{ display:block; font-size:10px; color:var(--muted); font-style:italic; margin-top:2px; }
  .swot-quad li .lbl .why{
    display:block; font-size:11.5px; line-height:1.45; color:var(--muted);
    margin-top:5px; padding-top:5px; border-top:1px dashed var(--line);
  }
  .swot-quad li .lbl .why b{ color:var(--navy); font-weight:600; }
  .swot-quad .empty{ font-size:12px; color:var(--muted); font-style:italic; }
  .tows-grid{ display:grid; grid-template-columns:1fr; gap:12px; }
  .tows-cell{ background:var(--ivory-2); border:1px solid var(--line); border-radius:var(--radius); padding:14px 16px 16px; break-inside:avoid; }
  .tows-cell h4{ font-family:var(--serif); font-weight:600; font-size:14.5px; margin:0 0 10px; color:var(--navy); display:flex; flex-direction:column; gap:2px; }
  .tows-cell h4 span{ font-size:10px; font-weight:600; text-transform:uppercase; letter-spacing:.08em; color:var(--muted); }
  .tows-cell[data-t="so"]{ border-left:4px solid var(--lvl5); }
  .tows-cell[data-t="st"]{ border-left:4px solid var(--dim-data); }
  .tows-cell[data-t="wo"]{ border-left:4px solid var(--gold); }
  .tows-cell[data-t="wt"]{ border-left:4px solid var(--lvl1); }
  .tows-cell ul{ list-style:none; margin:0; padding:0; display:flex; flex-direction:column; gap:7px; }
  .tows-cell li{ font-size:12px; line-height:1.45; color:var(--ink); padding:8px 10px; background:#fff; border-radius:3px; }
  .tows-cell .empty{ font-size:12px; color:var(--muted); font-style:italic; }
  .verdict-card{ display:flex; flex-direction:column; gap:14px; background:var(--navy); color:#fff; border-radius:6px; padding:22px; break-inside:avoid; }
  .verdict-score{ display:flex; align-items:baseline; gap:4px; font-family:var(--serif); font-weight:700; }
  .verdict-number{ font-size:44px; color:var(--gold); line-height:1; }
  .verdict-max{ font-size:16px; color:rgba(255,255,255,.65); }
  .verdict-band{ font-size:12px; letter-spacing:.08em; text-transform:uppercase; color:var(--gold-2); margin:0; font-weight:700; }
  .verdict-text{ font-size:13.5px; line-height:1.6; color:rgba(255,255,255,.78); margin:0; }
  .verdict-text b{ color:#fff; }
  @media (min-width: 700px){
    .swot-grid{ grid-template-columns:1fr 1fr; }
    .tows-grid{ grid-template-columns:1fr 1fr; }
    .verdict-card{ flex-direction:row; align-items:center; gap:26px; }
    .verdict-score{ flex:0 0 auto; }
  }
  @media print{ .print-btn{ display:none; } body{ background:#fff; } }
`

function buildSwotPageHtml(
  buckets: Buckets,
  cells: ReturnType<typeof buildTowsCells>,
  verdict: ReturnType<typeof computeVerdict>
): string {
  const stamp = new Date().toLocaleString('pt-BR', { dateStyle: 'long', timeStyle: 'short' })
  const title = model.value?.assessment_title || model.value?.title || 'Diagnóstico de Maturidade em IA'
  const total = totalForTier(selectedTier.value)
  return `<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Matriz SWOT — ${escapeHtml(title)}</title>
<style>${SWOT_PAGE_CSS}</style>
</head>
<body>
  <header class="page-header">
    <div class="inner">
      <div>
        <p class="eyebrow">Gerado a partir de ${total} respostas · abrangência ${TIER_LABEL_SHORT[selectedTier.value]} · ${escapeHtml(stamp)}</p>
        <h1>Matriz SWOT — ${escapeHtml(title)}</h1>
        <p class="meta">Página independente — pode ser impressa, salva ou compartilhada separadamente do formulário.</p>
      </div>
      <button type="button" class="print-btn" onclick="window.print()">Imprimir / salvar PDF</button>
    </div>
  </header>
  <main>
    <section class="swot-section">
      <h2 class="swot-section-title">1 · Como lemos suas respostas</h2>
      <p class="swot-rule">
        Perguntas das dimensões internas <strong>(Estratégia e Visão, Dados e Infraestrutura, Pessoas e Cultura, e Governança e Risco — exceto requisitos regulatórios)</strong> com maturidade 4–5 viram <strong>Força</strong>; com 1–3, <strong>Fraqueza</strong>. Perguntas ligadas a requisitos regulatórios <strong>(CSFs de origem "R")</strong> com maturidade 4–5 viram <strong>Oportunidade</strong>; com 1–3, <strong>Ameaça</strong>. Cada item traz a evidência (sua resposta) e a regra aplicada.
      </p>
    </section>
    <section class="swot-section">
      <h2 class="swot-section-title">2 · Matriz SWOT</h2>
      <div class="swot-grid">
        <div class="swot-quad" data-q="s"><h3>Forças <span class="swot-count">${buckets.s.length}</span></h3><ul>${quadItemsHtml(buckets.s, 's')}</ul></div>
        <div class="swot-quad" data-q="o"><h3>Oportunidades <span class="swot-count">${buckets.o.length}</span></h3><ul>${quadItemsHtml(buckets.o, 'o')}</ul></div>
        <div class="swot-quad" data-q="w"><h3>Fraquezas <span class="swot-count">${buckets.w.length}</span></h3><ul>${quadItemsHtml(buckets.w, 'w')}</ul></div>
        <div class="swot-quad" data-q="t"><h3>Ameaças <span class="swot-count">${buckets.t.length}</span></h3><ul>${quadItemsHtml(buckets.t, 't')}</ul></div>
      </div>
    </section>
    <section class="swot-section">
      <h2 class="swot-section-title">3 · Cruzamento TOWS</h2>
      <p class="swot-rule">Combina os quadrantes para sugerir movimentos: usar forças para capturar oportunidades ou conter ameaças, e decidir o que fazer com as fraquezas.</p>
      <div class="tows-grid">
        <div class="tows-cell" data-t="so"><h4>SO — Ofensiva <span>Força + Oportunidade</span></h4><ul>${towsItemsHtml(cells.so)}</ul></div>
        <div class="tows-cell" data-t="st"><h4>ST — Confronto <span>Força + Ameaça</span></h4><ul>${towsItemsHtml(cells.st)}</ul></div>
        <div class="tows-cell" data-t="wo"><h4>WO — Reforço <span>Fraqueza + Oportunidade</span></h4><ul>${towsItemsHtml(cells.wo)}</ul></div>
        <div class="tows-cell" data-t="wt"><h4>WT — Defesa <span>Fraqueza + Ameaça</span></h4><ul>${towsItemsHtml(cells.wt)}</ul></div>
      </div>
    </section>
    <section class="swot-section">
      <h2 class="swot-section-title">4 · Veredito</h2>
      <div class="verdict-card">
        <div class="verdict-score">
          <span class="verdict-number">${verdict.sum}</span>
          <span class="verdict-max">/${verdict.maxScore} pts</span>
        </div>
        <div class="verdict-body">
          <p class="verdict-band">${escapeHtml(verdict.band.label)}</p>
          <p class="verdict-text">
            ${escapeHtml(verdict.band.description)}
            ${
              verdict.strongest && verdict.weakest
                ? ` A dimensão mais madura é <b>${escapeHtml(verdict.strongest.label)}</b> (média ${verdict.strongest.avg.toFixed(1)}) — é aí que a empresa tem mais margem para alavancar resultado agora. A dimensão mais frágil é <b>${escapeHtml(verdict.weakest.label)}</b> (média ${verdict.weakest.avg.toFixed(1)}) — é a primeira candidata a plano de ação, antes que vire gargalo para as demais.`
                : ''
            }
            No total: <b>${buckets.s.length} força(s)</b>, <b>${buckets.w.length} fraqueza(s)</b>, <b>${buckets.o.length} oportunidade(s)</b> e <b>${buckets.t.length} ameaça(s)</b>.
          </p>
        </div>
      </div>
    </section>
  </main>
</body>
</html>`
}

function openSwot() {
  if (!isComplete.value) return
  swotCreated.value = true
  const buckets = buildBuckets()
  const cells = buildTowsCells(buckets)
  const verdict = computeVerdict()
  const html = buildSwotPageHtml(buckets, cells, verdict)
  const blob = new Blob([html], { type: 'text/html' })
  const url = URL.createObjectURL(blob)
  const win = window.open(url, '_blank')
  if (!win) {
    alert('O navegador bloqueou a abertura da nova aba. Permita pop-ups para este site e tente novamente.')
  } else {
    setTimeout(() => URL.revokeObjectURL(url), 30000)
  }
}

function scrollToDim(idx: number) {
  document.getElementById(`dim-${idx}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

function onCellKeydown(e: KeyboardEvent, qid: string, lvl: number) {
  if (e.key === 'Enter' || e.key === ' ') {
    e.preventDefault()
    toggleSelect(qid, lvl)
  }
}
</script>

<template>
  <div class="wrap">
    <div v-if="loading" class="state-card">Carregando diagnóstico…</div>
    <div v-else-if="error" class="state-card error">{{ error }}</div>

    <template v-else-if="model">
      <header class="page-header">
        <div class="header-main">
          <p class="eyebrow">Instrumento diagnóstico · Valorian</p>
          <h1 class="page-title">Maturidade em <em>IA</em></h1>
          <p class="page-desc">
            Avalie a organização em quatro dimensões. Escolha a abrangência do diagnóstico
            (Básico, Completo ou Complementar) e, em cada pergunta, selecione a alternativa
            na escala de maturidade de 1 a 5 que melhor descreve a realidade da empresa.
          </p>
        </div>
        <div class="header-chart" aria-label="Média por dimensão">
          <p class="chart-title">Média por dimensão</p>
          <div class="chart-bars">
            <div
              v-for="dim in model.dimensions"
              :key="'bar-' + dim.id"
              class="chart-bar-col"
            >
              <span class="chart-bar-value">
                {{ dimAvg(dim) == null ? '–' : dimAvg(dim)!.toFixed(1) }}
              </span>
              <div class="chart-bar-track">
                <div
                  class="chart-bar-fill"
                  :style="{
                    background: DIMENSION_COLORS[dim.id] || 'var(--gold)',
                    height: dimAvg(dim) == null ? '0%' : (dimAvg(dim)! / 5) * 100 + '%',
                  }"
                />
              </div>
              <span class="chart-bar-label">{{ DIMENSION_ABBR[dim.id] || dim.name.slice(0, 3) }}</span>
            </div>
          </div>
        </div>
      </header>

      <div class="toolbar">
        <div class="progress-block">
          <div class="num">{{ answeredCount }}/{{ totalVisible }}</div>
          <div class="progress-meta">
            <div class="progress-track">
              <div class="progress-fill" :style="{ width: progressPct + '%' }" />
            </div>
            <div class="progress-label">{{ progressLabel }}</div>
          </div>
        </div>

        <div class="tier-block">
          <p class="tier-label">Abrangência do diagnóstico</p>
          <div class="tier-select" role="tablist" aria-label="Abrangência do diagnóstico">
            <button
              v-for="key in TIER_KEYS"
              :key="key"
              type="button"
              class="tier-btn"
              :class="{ active: selectedTier === key }"
              :title="model.levels?.[key]?.description || ''"
              @click="setTier(key)"
            >
              <span class="tier-name">{{ model.levels?.[key]?.label ?? TIER_LABEL_SHORT[key] }}</span>
              <span class="tier-count">{{ model.levels?.[key]?.question_count ?? 0 }} perguntas</span>
            </button>
            <span
              class="save-pill"
              :data-state="saveState"
              :title="saveError || undefined"
            >
              <template v-if="saveState === 'saving'">Salvando…</template>
              <template v-else-if="saveState === 'saved'">Salvo</template>
              <template v-else-if="saveState === 'error'">Falha ao salvar</template>
              <template v-else>Respostas salvas ao clicar</template>
            </span>
          </div>
          <p v-if="selectedTierDescription" class="tier-hint">{{ selectedTierDescription }}</p>
        </div>

        <div class="scale-legend" title="Escala de resposta por pergunta">
          <span>Escala&nbsp;</span>
          <div class="swatch">
            <span style="background: var(--lvl1)" />
            <span style="background: var(--lvl2)" />
            <span style="background: var(--lvl3)" />
            <span style="background: var(--lvl4)" />
            <span style="background: var(--lvl5)" />
          </div>
          <span>1 → 5</span>
        </div>

        <nav class="pillar-nav" aria-label="Dimensões">
          <button
            v-for="(dim, dIdx) in model.dimensions"
            :key="'nav-' + dim.id"
            type="button"
            class="pillar-chip"
            @click="scrollToDim(dIdx)"
          >
            <span class="dot" :style="{ background: DIMENSION_COLORS[dim.id] || 'var(--gold)' }" />
            {{ dim.name }}
            <span class="n">{{ dimAnswered(dim).length }}/{{ dimVisibleQuestions(dim).length }}</span>
          </button>
        </nav>

        <div v-if="isComplete" class="toolbar-actions">
          <button
            type="button"
            class="btn-swot"
            @click="openSwot"
          >
            {{ swotCreated ? 'Abrir SWOT' : 'Criar SWOT' }}
          </button>
        </div>
      </div>

      <div class="matrix-wrap">
        <div class="matrix-scroll">
          <div class="col-legend" aria-hidden="true">
            <div class="stem-head" />
            <div v-for="n in 5" :key="'lh-' + n" class="lvl-head" :data-l="n">
              <span class="tag">{{ n }}</span>
              <span class="word">Maturidade</span>
            </div>
          </div>

          <section
            v-for="(dim, dIdx) in model.dimensions"
            :id="'dim-' + dIdx"
            :key="dim.id"
            class="pillar-section"
          >
            <div
              class="pillar-band"
              :style="{ '--dim-color': DIMENSION_COLORS[dim.id] || 'var(--gold)' }"
            >
              <h2>{{ dim.name }}</h2>
              <div class="pillar-meta">
                <span class="avg">
                  Média
                  <span class="bulbs">
                    <i
                      v-for="n in 5"
                      :key="'b-' + dim.id + '-' + n"
                      :class="{ on: dimAvg(dim) != null && n <= Math.round(dimAvg(dim)!) }"
                    />
                  </span>
                </span>
                <span>{{ dimAnswered(dim).length }}/{{ dimVisibleQuestions(dim).length }}</span>
              </div>
            </div>

            <div
              v-for="q in sortedQuestions(dim)"
              v-show="isVisibleTier(q.tier)"
              :key="q.id"
              class="csf-row"
            >
              <div class="stem">
                <span
                  class="code"
                  :style="{
                    background: 'color-mix(in srgb, ' + (DIMENSION_COLORS[dim.id] || 'var(--gold)') + ' 18%, transparent)',
                    color: DIMENSION_COLORS[dim.id] || 'var(--gold)',
                  }"
                >{{ q.id }}</span>
                <span class="tier-pill" :data-tier="q.tier">{{ TIER_LABEL_SHORT[q.tier] }}</span>
                <p class="title">{{ q.text }}</p>
                <p class="q">{{ originLine(q) }}</p>
              </div>

              <div
                v-for="lvl in 5"
                :key="q.id + '-' + lvl"
                class="cell"
                :class="{
                  selected: answers[q.id] === lvl,
                  faded: answers[q.id] != null && answers[q.id] !== lvl,
                }"
                :data-l="lvl"
                tabindex="0"
                role="button"
                :aria-pressed="answers[q.id] === lvl"
                @click="toggleSelect(q.id, lvl)"
                @keydown="onCellKeydown($event, q.id, lvl)"
              >
                <span class="txt">{{ q.levels[String(lvl)] }}</span>
              </div>
            </div>
          </section>
        </div>

        <div class="footnote">
          <b>Como funciona:</b> a abrangência (Básico → Completo → Complementar) é progressiva —
          cada opção inclui todas as perguntas da anterior. Trocar a abrangência só mostra ou
          esconde perguntas; as respostas já dadas permanecem e são salvas automaticamente a cada
          clique. Em cada pergunta, escolha uma alternativa na escala de maturidade 1–5. No celular,
          as alternativas aparecem empilhadas; em telas largas, em matriz. Ao concluir, você pode
          gerar a SWOT.
        </div>

        <details v-if="model.overlaps?.length" class="overlap-notes">
          <summary>
            Notas de sobreposição entre perguntas ({{ model.overlaps.length }})
          </summary>
          <ul>
            <li v-for="(o, i) in model.overlaps" :key="'ov-' + i">
              <span class="overlap-pair">{{ o.pair.join(' × ') }}</span>
              — {{ o.distinction }}
            </li>
          </ul>
        </details>
      </div>
    </template>
  </div>
</template>

<style scoped>
.wrap {
  --navy: #0e1b33;
  --navy-2: #16243f;
  --ink: #242a33;
  --gold: #c6a15b;
  --gold-2: #e3cb93;
  --ivory: #f6f1e7;
  --ivory-2: #fbf8f1;
  --oxblood: #7c3a3a;
  --muted: #6e6a60;
  --line: rgba(198, 161, 91, 0.32);
  --serif: Cambria, 'Hoefler Text', Georgia, 'Times New Roman', serif;
  --lvl1: #b6543f;
  --lvl2: #c07a44;
  --lvl3: #b79a3e;
  --lvl4: #6f9457;
  --lvl5: #3f8563;
  --dim-strategy: #7a5aa3;
  --dim-data: #3d6fa8;
  --dim-people: #b9822f;
  --dim-gov: #a3453f;
  --tier-basico: #6f9457;
  --tier-completo: #b79a3e;
  --tier-complementar: #3d6fa8;

  max-width: 1440px;
  margin: 0 auto;
  padding: 20px 16px 64px;
  color: var(--ink);
}

.state-card {
  background: var(--ivory-2);
  border: 1px solid var(--line);
  border-radius: 4px;
  padding: 24px 18px;
  text-align: center;
  color: var(--muted);
}
.state-card.error {
  color: var(--oxblood);
  text-align: left;
}

.page-header {
  display: flex;
  flex-direction: column;
  gap: 20px;
  margin-bottom: 18px;
}
.eyebrow {
  font-size: 0.7rem;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: var(--gold);
  font-weight: 600;
  margin: 0 0 6px;
}
.page-title {
  font-family: var(--serif);
  font-weight: 600;
  font-size: clamp(1.9rem, 5.5vw, 2.6rem);
  line-height: 1.05;
  color: var(--ink);
  margin: 0 0 8px;
}
.page-title em {
  font-style: italic;
  color: var(--gold);
}
.page-desc {
  margin: 0;
  color: var(--muted);
  font-size: 14px;
  line-height: 1.55;
  max-width: 52ch;
}
.header-chart {
  background: var(--ivory-2);
  border: 1px solid var(--line);
  border-radius: 4px;
  padding: 14px 16px;
}
.chart-title {
  font-size: 0.7rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--muted);
  font-weight: 600;
  margin: 0 0 10px;
}
.chart-bars {
  display: flex;
  align-items: flex-end;
  gap: 14px;
  height: 88px;
}
.chart-bar-col {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  width: 28px;
}
.chart-bar-value {
  font-family: var(--serif);
  font-size: 12px;
  font-weight: 600;
  color: var(--ink);
  min-height: 14px;
}
.chart-bar-track {
  width: 10px;
  height: 52px;
  background: rgba(198, 161, 91, 0.16);
  border-radius: 99px;
  display: flex;
  align-items: flex-end;
  overflow: hidden;
}
.chart-bar-fill {
  width: 100%;
  border-radius: 99px;
  transition: height 0.4s ease;
}
.chart-bar-label {
  font-size: 9px;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--muted);
  font-weight: 600;
}

.toolbar {
  position: sticky;
  top: var(--bar-h, 64px);
  z-index: 40;
  background: rgba(251, 248, 241, 0.96);
  backdrop-filter: blur(8px);
  border: 1px solid var(--line);
  border-radius: 4px;
  padding: 14px;
  margin-bottom: 14px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.progress-block {
  display: flex;
  align-items: center;
  gap: 12px;
}
.progress-block .num {
  font-family: var(--serif);
  font-size: 22px;
  color: var(--navy);
  font-weight: 600;
  min-width: 52px;
}
.progress-meta {
  flex: 1;
  min-width: 0;
}
.progress-track {
  width: 100%;
  max-width: 240px;
  height: 6px;
  background: rgba(14, 27, 51, 0.08);
  border-radius: 99px;
  overflow: hidden;
}
.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--navy), var(--gold));
  transition: width 0.35s ease;
}
.progress-label {
  margin-top: 4px;
  font-size: 11px;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--muted);
  line-height: 1.35;
}

.tier-block {
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex: 1 1 auto;
  min-width: 0;
}
.tier-label {
  margin: 0;
  font-size: 0.7rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--muted);
  font-weight: 600;
}
.tier-select {
  display: flex;
  align-items: stretch;
  gap: 6px;
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
  padding-bottom: 2px;
}
.tier-btn {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  justify-content: center;
  gap: 2px;
  padding: 8px 12px;
  border-radius: 999px;
  border: 1px solid var(--line);
  background: #fff;
  color: var(--muted);
  cursor: pointer;
  flex: 0 0 auto;
  white-space: nowrap;
  font-family: inherit;
  transition: 0.15s;
}
.tier-btn:hover {
  border-color: var(--gold);
  color: var(--navy);
}
.tier-btn .tier-name {
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.02em;
}
.tier-btn .tier-count {
  font-size: 10px;
  opacity: 0.75;
}
.tier-btn.active {
  background: var(--navy);
  border-color: var(--navy);
  color: #fff;
}
.tier-hint {
  margin: 0;
  font-size: 12px;
  line-height: 1.45;
  color: var(--muted);
}

.scale-legend {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
  color: var(--muted);
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}
.scale-legend .swatch {
  display: flex;
  gap: 3px;
}
.scale-legend .swatch span {
  width: 14px;
  height: 14px;
  border-radius: 2px;
  display: block;
}

.pillar-nav {
  display: flex;
  gap: 6px;
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}
.pillar-chip {
  font-size: 11px;
  letter-spacing: 0.02em;
  padding: 7px 11px;
  border-radius: 999px;
  border: 1px solid var(--line);
  color: var(--muted);
  background: #fff;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
  flex: 0 0 auto;
  white-space: nowrap;
  font-family: inherit;
  transition: 0.15s;
}
.pillar-chip:hover {
  border-color: var(--gold);
  color: var(--navy);
}
.pillar-chip .dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex: 0 0 auto;
}
.pillar-chip .n {
  opacity: 0.7;
}

.toolbar-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.btn-swot {
  min-height: 44px;
  padding: 10px 16px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  cursor: pointer;
  font-family: inherit;
  transition: 0.15s;
  width: 100%;
  border: 1px solid var(--gold);
  background: var(--gold);
  color: var(--navy);
}
.btn-swot:hover {
  background: var(--gold-2);
  border-color: var(--gold-2);
}
.save-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  box-sizing: border-box;
  padding: 8px 14px;
  border-radius: 999px;
  border: 1px solid var(--line);
  background: #fff;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--muted);
  flex: 0 0 auto;
  white-space: nowrap;
  line-height: 1.2;
}
.save-pill[data-state='saving'] {
  color: var(--navy);
}
.save-pill[data-state='saved'] {
  color: #2f6e4a;
  border-color: #bbd3b7;
  background: #e8f0e7;
}
.save-pill[data-state='error'] {
  color: var(--oxblood);
  border-color: #ddbcb4;
  background: #f1e1dd;
  text-transform: none;
  letter-spacing: 0;
  white-space: normal;
}

.matrix-wrap {
  margin-top: 4px;
}
.matrix-scroll {
  overflow-x: visible;
}
.col-legend {
  display: none;
}
.lvl-head {
  font-size: 11px;
  letter-spacing: 0.04em;
  color: var(--muted);
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 6px;
  padding: 0 4px 6px;
  border-bottom: 2px solid;
}
.lvl-head .tag {
  font-weight: 700;
  font-size: 13px;
  font-family: var(--serif);
}
.lvl-head .word {
  text-transform: uppercase;
  font-size: 9px;
  letter-spacing: 0.08em;
  opacity: 0.75;
}
.lvl-head[data-l='1'] { border-color: var(--lvl1); color: var(--lvl1); }
.lvl-head[data-l='2'] { border-color: var(--lvl2); color: var(--lvl2); }
.lvl-head[data-l='3'] { border-color: var(--lvl3); color: var(--lvl3); }
.lvl-head[data-l='4'] { border-color: var(--lvl4); color: var(--lvl4); }
.lvl-head[data-l='5'] { border-color: var(--lvl5); color: var(--lvl5); }

.pillar-section {
  margin-bottom: 8px;
}
.pillar-band {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 12px;
  padding: 12px 14px;
  margin-top: 14px;
  border-radius: 4px;
  background: var(--ivory-2);
  border: 1px solid var(--line);
  border-left: 4px solid var(--dim-color, var(--gold));
  color: var(--navy);
}
.pillar-band h2 {
  font-family: var(--serif);
  font-weight: 600;
  font-size: 17px;
  margin: 0;
  color: var(--navy);
}
.pillar-meta {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 11px;
  color: var(--muted);
  font-weight: 600;
  letter-spacing: 0.03em;
  text-transform: uppercase;
  flex-wrap: wrap;
}
.avg {
  display: flex;
  align-items: center;
  gap: 6px;
}
.bulbs {
  display: flex;
  gap: 3px;
}
.bulbs i {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: rgba(14, 27, 51, 0.12);
  display: inline-block;
}
.bulbs i.on {
  background: var(--gold);
}

.csf-row {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 14px 0;
  border-bottom: 1px solid rgba(14, 27, 51, 0.08);
}
.stem .code {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.03em;
  display: inline-block;
  padding: 2px 7px;
  border-radius: 3px;
  margin-bottom: 6px;
}
.stem .tier-pill {
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  display: inline-block;
  padding: 2px 8px;
  border-radius: 999px;
  margin: 0 0 6px 6px;
  color: #fff;
}
.stem .tier-pill[data-tier='basico'] { background: var(--tier-basico); }
.stem .tier-pill[data-tier='completo'] { background: var(--tier-completo); color: var(--navy); }
.stem .tier-pill[data-tier='complementar'] { background: var(--tier-complementar); }
.stem .title {
  font-weight: 600;
  font-size: 14px;
  line-height: 1.35;
  margin: 0 0 4px;
  color: var(--navy);
}
.stem .q {
  font-size: 12px;
  line-height: 1.45;
  color: var(--muted);
  font-style: italic;
  margin: 0;
}

.cell {
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 4px;
  padding: 11px 12px;
  font-size: 13px;
  line-height: 1.42;
  cursor: pointer;
  min-height: 44px;
  transition: transform 0.12s ease, box-shadow 0.12s ease, border-color 0.12s ease, background 0.12s ease;
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--ink);
}
.cell::before {
  content: attr(data-l);
  font-family: var(--serif);
  font-weight: 700;
  font-size: 12px;
  line-height: 1;
  flex: 0 0 auto;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
}
.cell[data-l='1']::before { background: var(--lvl1); }
.cell[data-l='2']::before { background: var(--lvl2); }
.cell[data-l='3']::before { background: var(--lvl3); }
.cell[data-l='4']::before { background: var(--lvl4); }
.cell[data-l='5']::before { background: var(--lvl5); }
.cell:hover {
  border-color: var(--gold);
  box-shadow: 0 2px 10px rgba(14, 27, 51, 0.06);
}
.cell:focus-visible {
  outline: 2px solid var(--gold);
  outline-offset: 1px;
}
.cell.faded {
  opacity: 0.42;
}
.cell.selected {
  background: var(--navy);
  border-color: var(--navy);
  color: var(--ivory);
  box-shadow: 0 4px 14px rgba(14, 27, 51, 0.16);
}
.cell.selected::before {
  background: var(--gold);
  color: var(--navy);
}
.cell .txt {
  flex: 1;
  min-width: 0;
  overflow-wrap: anywhere;
  word-break: break-word;
}

.footnote {
  margin: 18px 0 0;
  padding: 12px 14px;
  background: var(--ivory);
  border: 1px dashed var(--line);
  border-radius: 4px;
  font-size: 12px;
  color: var(--muted);
  line-height: 1.55;
}
.footnote b {
  color: var(--navy);
}
.overlap-notes {
  margin: 12px 0 0;
  padding: 12px 14px;
  background: var(--ivory-2);
  border: 1px solid var(--line);
  border-radius: 4px;
  font-size: 12px;
  color: var(--muted);
}
.overlap-notes summary {
  cursor: pointer;
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--gold);
  font-weight: 700;
}
.overlap-notes ul {
  list-style: none;
  margin: 12px 0 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.overlap-notes li {
  line-height: 1.5;
  padding: 8px 10px;
  background: #fff;
  border-radius: 3px;
  border: 1px solid rgba(14, 27, 51, 0.06);
}
.overlap-pair {
  font-weight: 700;
  color: var(--navy);
  margin-right: 2px;
}

@media (min-width: 640px) {
  .wrap {
    padding: 28px 20px 72px;
  }
  .page-header {
    flex-direction: row;
    align-items: flex-end;
    justify-content: space-between;
    gap: 28px;
  }
  .header-chart {
    flex: 0 0 auto;
  }
  .chart-bars {
    height: 100px;
    gap: 16px;
  }
  .toolbar-actions {
    flex-direction: row;
    flex-wrap: wrap;
  }
  .btn-swot {
    width: auto;
    min-width: 150px;
  }
}

@media (min-width: 860px) {
  .toolbar {
    flex-direction: row;
    flex-wrap: wrap;
    align-items: center;
    gap: 16px 20px;
    padding: 14px 18px;
  }
  .tier-block {
    flex: 1 1 280px;
  }
  .pillar-nav {
    flex: 1 1 100%;
    overflow-x: visible;
    flex-wrap: wrap;
  }
  .scale-legend {
    margin-left: auto;
  }
}

/* Matriz lado a lado só quando há largura suficiente — sem min-width forçado */
@media (min-width: 1100px) {
  .wrap {
    padding-left: 24px;
    padding-right: 24px;
  }
  .col-legend {
    display: grid;
    grid-template-columns: minmax(200px, 1.15fr) repeat(5, minmax(0, 1fr));
    gap: 8px;
    padding: 0 0 10px;
    width: 100%;
  }
  .pillar-band {
    position: sticky;
    top: calc(var(--bar-h, 64px) + 12px);
    z-index: 20;
  }
  .csf-row {
    display: grid;
    grid-template-columns: minmax(200px, 1.15fr) repeat(5, minmax(0, 1fr));
    gap: 8px;
    padding: 10px 0;
    width: 100%;
  }
  .stem {
    padding: 4px 8px 4px 0;
    min-width: 0;
  }
  .cell {
    align-items: flex-start;
    font-size: 12px;
    min-height: auto;
    min-width: 0;
    padding: 10px;
  }
  .cell:hover {
    transform: translateY(-1px);
  }
}
</style>

