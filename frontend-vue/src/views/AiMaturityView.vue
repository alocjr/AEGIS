<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  fetchMaturityModel,
  saveMaturityResponse,
  type MaturityDimension,
  type MaturityModel,
  type MaturityQuestion,
  type MaturityTier,
} from '@/api/maturity'

const router = useRouter()
const loading = ref(true)
const error = ref<string | null>(null)
const model = ref<MaturityModel | null>(null)
const answers = ref<Record<string, number>>({})
const selectedTier = ref<MaturityTier>('basico')
const saving = ref(false)
const saveInfo = ref('')
const swotCreated = ref(false)

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
  if (q.originType === 'modelo_rapido') {
    return `Pergunta base do Modelo Rápido (${q.ref ?? '—'})`
  }
  return `Deriva do CSF ${q.csfId ?? '—'} · ${q.csfName ?? ''}`
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
    return `Diagnóstico ${TIER_LABEL_SHORT[selectedTier.value].toLowerCase()} completo · ${v.sum}/${v.maxScore} pts · ${v.band.label}`
  }
  return `${total - answered} pergunta(s) restante(s) no nível ${TIER_LABEL_SHORT[selectedTier.value]}`
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
  selectedTier.value = key
}

function toggleSelect(qid: string, lvl: number) {
  if (answers.value[qid] === lvl) {
    const next = { ...answers.value }
    delete next[qid]
    answers.value = next
  } else {
    answers.value = { ...answers.value, [qid]: lvl }
  }
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
    --ink:#171b20; --paper:#f4f1ea; --panel:#12181f;
    --hairline:#2c3743; --card:#fffdf8; --card-border:#e4ddc9;
    --gold:#c8963e; --gold-strong:#a8752a; --muted:#6b7280; --muted-inv:#9aa7b4;
    --lvl1:#b6543f; --lvl5:#3f8563; --dim-data:#3d6fa8; --radius:3px;
  }
  *{ box-sizing:border-box; }
  html,body{ margin:0; padding:0; }
  body{
    background:var(--paper); color:var(--ink);
    font-family:'Inter', system-ui, sans-serif;
    -webkit-font-smoothing:antialiased;
  }
  .page-header{
    background:var(--panel); color:var(--paper);
    padding:28px 18px; border-bottom:1px solid var(--hairline);
  }
  .page-header .inner{ max-width:920px; margin:0 auto; display:flex; align-items:flex-start; justify-content:space-between; gap:16px; flex-wrap:wrap; }
  .page-header .eyebrow{
    font-family:'JetBrains Mono', monospace; font-size:11px; letter-spacing:.14em;
    text-transform:uppercase; color:var(--gold); margin:0 0 8px;
  }
  .page-header h1{
    font-family:'Fraunces', serif; font-weight:600; font-size:clamp(22px,4.5vw,32px);
    margin:0 0 6px; letter-spacing:-.01em;
  }
  .page-header .meta{ font-size:12px; color:var(--muted-inv); margin:0; }
  .print-btn{
    font-family:'JetBrains Mono',monospace; font-size:11px; font-weight:600;
    letter-spacing:.04em; text-transform:uppercase;
    padding:9px 16px; border-radius:99px; border:1px solid var(--gold);
    background:transparent; color:var(--gold); cursor:pointer; flex:0 0 auto;
  }
  .print-btn:hover{ background:var(--gold); color:#1a1005; }
  main{ max-width:920px; margin:0 auto; padding:26px 18px 60px; }
  .swot-section{ margin-bottom:30px; }
  .swot-section-title{
    font-family:'JetBrains Mono', monospace; font-size:11px; letter-spacing:.08em;
    text-transform:uppercase; color:var(--gold-strong); margin:0 0 12px;
    padding-bottom:6px; border-bottom:1px solid var(--card-border);
  }
  .swot-rule{ font-size:13px; line-height:1.6; color:var(--muted); max-width:760px; margin:0 0 14px; }
  .swot-rule strong{ color:var(--ink); }
  .swot-grid{ display:grid; grid-template-columns:1fr; gap:12px; }
  .swot-quad{
    background:var(--card); border:1px solid var(--card-border); border-radius:var(--radius);
    border-top:4px solid; padding:14px 16px 16px; break-inside:avoid;
  }
  .swot-quad[data-q="s"]{ border-top-color:var(--lvl5); }
  .swot-quad[data-q="w"]{ border-top-color:var(--lvl1); }
  .swot-quad[data-q="o"]{ border-top-color:var(--dim-data); }
  .swot-quad[data-q="t"]{ border-top-color:var(--gold-strong); }
  .swot-quad h3{
    font-family:'Fraunces', serif; font-weight:600; font-size:16px; margin:0 0 10px;
    display:flex; align-items:center; gap:8px; color:var(--ink);
  }
  .swot-quad[data-q="s"] h3{ color:var(--lvl5); }
  .swot-quad[data-q="w"] h3{ color:var(--lvl1); }
  .swot-quad[data-q="o"] h3{ color:var(--dim-data); }
  .swot-quad[data-q="t"] h3{ color:var(--gold-strong); }
  .swot-count{
    font-family:'JetBrains Mono',monospace; font-size:11px; font-weight:700; color:var(--muted);
    background:var(--paper); border-radius:99px; padding:1px 8px;
  }
  .swot-quad ul{ list-style:none; margin:0; padding:0; display:flex; flex-direction:column; gap:8px; }
  .swot-quad li{ display:flex; align-items:flex-start; gap:8px; padding:9px 10px; background:var(--paper); border-radius:3px; }
  .swot-quad li .code{
    font-family:'JetBrains Mono',monospace; font-size:10.5px; font-weight:700; flex:0 0 auto;
    padding:1px 6px; border-radius:3px; background:var(--card); border:1px solid var(--card-border); margin-top:1px;
  }
  .swot-quad li .lbl{ color:var(--ink); flex:1; min-width:0; }
  .swot-quad li .lbl .item-title{ font-size:12.5px; font-weight:600; line-height:1.35; display:block; }
  .swot-quad li .lbl .pillar-tag{ display:block; font-size:10px; color:var(--muted); font-style:italic; margin-top:2px; }
  .swot-quad li .lbl .why{
    display:block; font-size:11.5px; line-height:1.45; color:var(--muted);
    margin-top:5px; padding-top:5px; border-top:1px dashed var(--card-border);
  }
  .swot-quad li .lbl .why b{ color:var(--ink); font-weight:600; }
  .swot-quad .empty{ font-size:12px; color:var(--muted); font-style:italic; }
  .tows-grid{ display:grid; grid-template-columns:1fr; gap:12px; }
  .tows-cell{ background:var(--card); border:1px solid var(--card-border); border-radius:var(--radius); padding:14px 16px 16px; break-inside:avoid; }
  .tows-cell h4{ font-family:'Fraunces', serif; font-weight:600; font-size:14.5px; margin:0 0 10px; color:var(--ink); display:flex; flex-direction:column; gap:2px; }
  .tows-cell h4 span{ font-family:'JetBrains Mono',monospace; font-size:10px; font-weight:500; text-transform:uppercase; letter-spacing:.04em; color:var(--muted); }
  .tows-cell[data-t="so"]{ border-left:4px solid var(--lvl5); }
  .tows-cell[data-t="st"]{ border-left:4px solid var(--dim-data); }
  .tows-cell[data-t="wo"]{ border-left:4px solid var(--gold-strong); }
  .tows-cell[data-t="wt"]{ border-left:4px solid var(--lvl1); }
  .tows-cell ul{ list-style:none; margin:0; padding:0; display:flex; flex-direction:column; gap:7px; }
  .tows-cell li{ font-size:12px; line-height:1.45; color:var(--ink); padding:8px 10px; background:var(--paper); border-radius:3px; }
  .tows-cell .empty{ font-size:12px; color:var(--muted); font-style:italic; }
  .verdict-card{ display:flex; flex-direction:column; gap:14px; background:var(--panel); color:var(--paper); border-radius:6px; padding:22px; break-inside:avoid; }
  .verdict-score{ display:flex; align-items:baseline; gap:4px; font-family:'Fraunces', serif; font-weight:700; }
  .verdict-number{ font-size:44px; color:var(--gold); line-height:1; }
  .verdict-max{ font-size:16px; color:var(--muted-inv); }
  .verdict-band{ font-family:'JetBrains Mono',monospace; font-size:12px; letter-spacing:.06em; text-transform:uppercase; color:var(--gold); margin:0; font-weight:700; }
  .verdict-text{ font-size:13.5px; line-height:1.6; color:var(--muted-inv); margin:0; }
  .verdict-text b{ color:var(--paper); }
  @media (min-width: 700px){
    .swot-grid{ grid-template-columns:1fr 1fr; }
    .tows-grid{ grid-template-columns:1fr 1fr; }
    .verdict-card{ flex-direction:row; align-items:center; gap:26px; }
    .verdict-score{ flex:0 0 auto; }
  }
  @media print{
    .print-btn{ display:none; }
    body{ background:#fff; }
  }
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
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600;9..144,700&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>${SWOT_PAGE_CSS}</style>
</head>
<body>
  <header class="page-header">
    <div class="inner">
      <div>
        <p class="eyebrow">Gerado a partir de ${total} respostas · nível ${TIER_LABEL_SHORT[selectedTier.value]} · ${escapeHtml(stamp)}</p>
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
        Perguntas ligadas a dimensões internas <strong>(Estratégia e Visão, Dados e Infraestrutura, Pessoas e Cultura, e a parte de Governança de Governança e Risco)</strong> com nível 4–5 viram <strong>Força</strong>, com nível 1–3 viram <strong>Fraqueza</strong>. Perguntas ligadas a requisitos regulatórios <strong>(CSFs de origem "R" dentro de Governança e Risco)</strong> com nível 4–5 viram <strong>Oportunidade</strong>, com nível 1–3 viram <strong>Ameaça</strong>. Cada item abaixo traz a evidência (sua resposta) e a regra aplicada.
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

async function saveAnswers() {
  if (!model.value || !isComplete.value) {
    alert('Responda todas as perguntas do nível selecionado antes de salvar.')
    return
  }
  saving.value = true
  try {
    const payload: Record<string, number> = {}
    for (const id of visibleQuestionIds.value) {
      const val = answers.value[id]
      if (val != null) payload[id] = val
    }
    const result = await saveMaturityResponse(payload, selectedTier.value)
    saveInfo.value = 'Salvo em ' + new Date(result.submitted_at).toLocaleString('pt-BR')
    setTimeout(() => router.push('/ai-maturity'), 1200)
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Erro ao salvar.'
  } finally {
    saving.value = false
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
  <div class="maturity">
    <div v-if="loading" class="state-card">Carregando diagnóstico…</div>
    <div v-else-if="error" class="state-card error">{{ error }}</div>

    <template v-else-if="model">
      <header class="top">
        <div class="header-flex">
          <div class="header-text">
            <p class="eyebrow">
              Diagnóstico de Maturidade em IA · Valorian 4 Future · v{{ model.version ?? '3.0' }}
            </p>
            <h1>{{ model.assessment_title || model.title || 'Diagnóstico de Maturidade em IA' }}</h1>
            <p class="lede">
              Formulário único e progressivo em 3 níveis — cada nível contém integralmente as perguntas do
              anterior. As linhas são perguntas agrupadas pelas 4 dimensões do modelo; as colunas são níveis
              de maturidade (1 a 5), com alternativas próprias por pergunta. Escolha o nível de profundidade
              abaixo e clique na célula que melhor descreve a realidade da empresa.
            </p>
          </div>
          <div class="header-chart">
            <p class="chart-title">Nível médio por dimensão</p>
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
                      background: DIMENSION_COLORS[dim.id] || '#666',
                      height: dimAvg(dim) == null ? '0%' : (dimAvg(dim)! / 5) * 100 + '%',
                    }"
                  />
                </div>
                <span class="chart-bar-label">{{ DIMENSION_ABBR[dim.id] || dim.name.slice(0, 3) }}</span>
              </div>
            </div>
          </div>
        </div>
      </header>

      <div class="toolbar">
        <div class="progress-block">
          <div class="num">{{ answeredCount }}/{{ totalVisible }}</div>
          <div>
            <div class="progress-track">
              <div class="progress-fill" :style="{ width: progressPct + '%' }" />
            </div>
            <div class="progress-label">{{ progressLabel }}</div>
          </div>
        </div>

        <div class="tier-select" role="tablist" aria-label="Profundidade do diagnóstico">
          <button
            v-for="key in TIER_KEYS"
            :key="key"
            type="button"
            class="tier-btn"
            :class="{ active: selectedTier === key }"
            @click="setTier(key)"
          >
            <span class="tier-name">{{ model.levels?.[key]?.label ?? TIER_LABEL_SHORT[key] }}</span>
            <span class="tier-count">{{ model.levels?.[key]?.question_count ?? 0 }} perguntas</span>
          </button>
        </div>

        <div class="scale-legend">
          <span>Maturidade&nbsp;</span>
          <div class="swatch">
            <span style="background: var(--lvl1)" />
            <span style="background: var(--lvl2)" />
            <span style="background: var(--lvl3)" />
            <span style="background: var(--lvl4)" />
            <span style="background: var(--lvl5)" />
          </div>
          <span>1 → 5</span>
        </div>

        <nav class="pillar-nav">
          <button
            v-for="(dim, dIdx) in model.dimensions"
            :key="'nav-' + dim.id"
            type="button"
            class="pillar-chip"
            @click="scrollToDim(dIdx)"
          >
            <span class="dot" :style="{ background: DIMENSION_COLORS[dim.id] || '#666' }" />
            {{ dim.name }}
            <span class="n">{{ dimAnswered(dim).length }}/{{ dimVisibleQuestions(dim).length }}</span>
          </button>
        </nav>

        <div class="toolbar-actions">
          <button
            v-if="isComplete"
            type="button"
            class="btn-swot"
            @click="openSwot"
          >
            {{ swotCreated ? 'SWOT' : 'Criar SWOT' }}
          </button>
          <button
            type="button"
            class="btn-save"
            :disabled="!isComplete || saving"
            @click="saveAnswers"
          >
            {{ saving ? 'Salvando…' : 'Salvar respostas' }}
          </button>
        </div>
      </div>

      <p v-if="saveInfo" class="save-banner">{{ saveInfo }}</p>

      <div class="matrix-wrap">
        <div class="matrix-scroll">
          <div class="col-legend">
            <div class="stem-head" />
            <div v-for="n in 5" :key="'lh-' + n" class="lvl-head" :data-l="n">
              <span class="tag">Nível {{ n }}</span>
            </div>
          </div>

          <div
            v-for="(dim, dIdx) in model.dimensions"
            :id="'dim-' + dIdx"
            :key="dim.id"
            class="pillar-section"
          >
            <div class="pillar-band" :style="{ background: DIMENSION_COLORS[dim.id] || '#666' }">
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
                    background: (DIMENSION_COLORS[dim.id] || '#666') + '22',
                    color: DIMENSION_COLORS[dim.id] || '#666',
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
                  dim: answers[q.id] != null && answers[q.id] !== lvl,
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
          </div>
        </div>

        <div class="footnote">
          <b>Como funciona:</b> mudar o nível de profundidade (Básico/Completo/Complementar) mostra ou
          esconde perguntas, mas não apaga respostas já dadas. Em telas estreitas, cada pergunta vira um
          cartão com os 5 níveis empilhados; em telas largas, a matriz aparece completa. Ao concluir o
          diagnóstico você pode gerar a SWOT e salvar as respostas na plataforma.
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
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600;9..144,700&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

.maturity {
  --ink: #171b20;
  --paper: #f4f1ea;
  --panel: #12181f;
  --panel-2: #1b232c;
  --hairline: #2c3743;
  --hairline-light: #ddd6c6;
  --card: #fffdf8;
  --card-border: #e4ddc9;
  --gold: #c8963e;
  --gold-strong: #a8752a;
  --muted: #6b7280;
  --muted-inv: #9aa7b4;
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
  --radius: 3px;

  margin: 0 calc(50% - 50vw);
  width: 100vw;
  min-height: calc(100vh - var(--bar-h, 56px));
  background: var(--panel);
  color: var(--ink);
  font-family: 'Inter', system-ui, sans-serif;
  -webkit-font-smoothing: antialiased;
}

.state-card {
  margin: 24px 18px;
  padding: 18px;
  background: var(--card);
  border: 1px solid var(--card-border);
  border-radius: var(--radius);
  color: var(--ink);
}
.state-card.error {
  color: #a3453f;
}

.top {
  background: var(--panel);
  color: var(--paper);
  padding: 26px 18px 22px;
  border-bottom: 1px solid var(--hairline);
}
.eyebrow {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--gold);
  margin: 0 0 8px;
}
.top h1 {
  font-family: 'Fraunces', serif;
  font-weight: 600;
  font-size: clamp(24px, 6.4vw, 42px);
  line-height: 1.08;
  margin: 0 0 10px;
  letter-spacing: -0.01em;
  color: var(--paper);
}
.lede {
  max-width: 640px;
  color: var(--muted-inv);
  font-size: 13.5px;
  line-height: 1.55;
  margin: 0;
}
.header-flex {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 22px;
}
.chart-title {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--muted-inv);
  margin: 0 0 10px;
}
.chart-bars {
  display: flex;
  align-items: flex-end;
  gap: 11px;
  height: 88px;
}
.chart-bar-col {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  width: 26px;
}
.chart-bar-value {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  font-weight: 600;
  color: var(--gold);
  min-height: 13px;
}
.chart-bar-track {
  width: 10px;
  height: 56px;
  background: var(--hairline);
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
  font-family: 'JetBrains Mono', monospace;
  font-size: 8.5px;
  letter-spacing: 0.03em;
  text-transform: uppercase;
  color: var(--muted-inv);
}

.toolbar {
  position: sticky;
  top: var(--bar-h, 56px);
  z-index: 40;
  background: rgba(18, 24, 31, 0.97);
  backdrop-filter: blur(6px);
  border-bottom: 1px solid var(--hairline);
  padding: 12px 18px;
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 12px;
}
.progress-block {
  display: flex;
  align-items: center;
  gap: 12px;
}
.progress-block .num {
  font-family: 'Fraunces', serif;
  font-size: 22px;
  color: var(--paper);
  font-weight: 600;
  min-width: 54px;
}
.progress-track {
  width: 100%;
  max-width: 220px;
  height: 6px;
  background: var(--hairline);
  border-radius: 99px;
  overflow: hidden;
}
.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--gold-strong), var(--gold));
  transition: width 0.35s ease;
}
.progress-label {
  font-family: 'JetBrains Mono', monospace;
  font-size: 9.5px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--muted-inv);
}
.tier-select {
  display: flex;
  gap: 6px;
  overflow-x: auto;
}
.tier-btn {
  font-family: 'JetBrains Mono', monospace;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 1px;
  padding: 6px 12px;
  border-radius: 8px;
  border: 1px solid var(--hairline);
  background: transparent;
  color: var(--muted-inv);
  cursor: pointer;
  flex: 0 0 auto;
  white-space: nowrap;
  transition: 0.15s;
}
.tier-btn:hover {
  border-color: var(--gold);
  color: var(--paper);
}
.tier-btn .tier-name {
  font-size: 11px;
  font-weight: 700;
}
.tier-btn .tier-count {
  font-size: 9px;
  opacity: 0.7;
}
.tier-btn.active {
  background: var(--gold);
  border-color: var(--gold);
  color: #1a1005;
}
.pillar-nav {
  display: flex;
  gap: 6px;
  overflow-x: auto;
}
.pillar-chip {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10.5px;
  letter-spacing: 0.03em;
  padding: 6px 10px;
  border-radius: 99px;
  border: 1px solid var(--hairline);
  color: var(--muted-inv);
  background: transparent;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
  flex: 0 0 auto;
  white-space: nowrap;
  transition: 0.15s;
}
.pillar-chip:hover {
  border-color: var(--gold);
  color: var(--paper);
}
.pillar-chip .dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex: 0 0 auto;
}
.pillar-chip .n {
  opacity: 0.65;
}
.scale-legend {
  display: flex;
  align-items: center;
  gap: 8px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  color: var(--muted-inv);
  order: 3;
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
.toolbar-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.btn-swot,
.btn-save {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11.5px;
  letter-spacing: 0.04em;
  font-weight: 600;
  text-transform: uppercase;
  padding: 11px 18px;
  border-radius: 99px;
  cursor: pointer;
  transition: 0.15s;
  width: 100%;
}
.btn-swot {
  border: 1px solid var(--gold);
  background: var(--gold);
  color: #1a1005;
}
.btn-swot:hover {
  background: var(--gold-strong);
  border-color: var(--gold-strong);
}
.btn-save {
  border: 1px solid var(--hairline);
  background: transparent;
  color: var(--paper);
}
.btn-save:hover:not(:disabled) {
  border-color: var(--gold);
  color: var(--gold);
}
.btn-save:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.save-banner {
  margin: 0;
  padding: 10px 18px;
  background: var(--lvl5);
  color: #fff;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  letter-spacing: 0.04em;
}

.matrix-wrap {
  background: var(--paper);
  padding: 0 18px 56px;
}
.matrix-scroll {
  overflow-x: auto;
  padding-top: 18px;
}
.col-legend {
  display: none;
}
.lvl-head {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  letter-spacing: 0.04em;
  color: #6b6250;
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  padding: 0 4px 6px;
  border-bottom: 2px solid;
}
.lvl-head .tag {
  font-weight: 700;
  font-size: 13px;
}
.lvl-head[data-l='1'] {
  border-color: var(--lvl1);
  color: var(--lvl1);
}
.lvl-head[data-l='2'] {
  border-color: var(--lvl2);
  color: var(--lvl2);
}
.lvl-head[data-l='3'] {
  border-color: var(--lvl3);
  color: var(--lvl3);
}
.lvl-head[data-l='4'] {
  border-color: var(--lvl4);
  color: var(--lvl4);
}
.lvl-head[data-l='5'] {
  border-color: var(--lvl5);
  color: var(--lvl5);
}

.pillar-section {
  margin-bottom: 4px;
}
.pillar-band {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 10px;
  padding: 12px 14px;
  margin-top: 16px;
  border-radius: var(--radius);
  color: #fff;
}
.pillar-band h2 {
  font-family: 'Fraunces', serif;
  font-weight: 600;
  font-size: 16px;
  margin: 0;
  color: #fff;
}
.pillar-meta {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 10px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
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
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.22);
  display: inline-block;
}
.bulbs i.on {
  background: #fff;
}

.csf-row {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 14px 0;
  border-bottom: 1px solid var(--hairline-light);
}
.stem .code {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10.5px;
  font-weight: 700;
  letter-spacing: 0.03em;
  display: inline-block;
  padding: 1px 6px;
  border-radius: 3px;
  margin-bottom: 6px;
}
.stem .tier-pill {
  font-family: 'JetBrains Mono', monospace;
  font-size: 9px;
  font-weight: 600;
  letter-spacing: 0.03em;
  text-transform: uppercase;
  display: inline-block;
  padding: 1px 7px;
  border-radius: 99px;
  margin: 0 0 6px 6px;
  color: #fff;
}
.stem .tier-pill[data-tier='basico'] {
  background: var(--tier-basico);
}
.stem .tier-pill[data-tier='completo'] {
  background: var(--tier-completo);
  color: #1a1005;
}
.stem .tier-pill[data-tier='complementar'] {
  background: var(--tier-complementar);
}
.stem .title {
  font-weight: 600;
  font-size: 14px;
  line-height: 1.3;
  margin: 0 0 4px;
  color: var(--ink);
}
.stem .q {
  font-size: 12.5px;
  line-height: 1.45;
  color: var(--muted);
  font-style: italic;
  margin: 0;
}
.cell {
  background: var(--card);
  border: 1px solid var(--card-border);
  border-radius: var(--radius);
  padding: 11px 12px;
  font-size: 13px;
  line-height: 1.42;
  cursor: pointer;
  position: relative;
  min-height: 44px;
  transition: transform 0.12s ease, box-shadow 0.12s ease, border-color 0.12s ease, background 0.12s ease;
  display: flex;
  align-items: center;
  gap: 10px;
}
.cell::before {
  content: attr(data-l);
  font-family: 'JetBrains Mono', monospace;
  font-weight: 700;
  font-size: 11px;
  line-height: 1;
  flex: 0 0 auto;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
}
.cell[data-l='1']::before {
  background: var(--lvl1);
}
.cell[data-l='2']::before {
  background: var(--lvl2);
}
.cell[data-l='3']::before {
  background: var(--lvl3);
}
.cell[data-l='4']::before {
  background: var(--lvl4);
}
.cell[data-l='5']::before {
  background: var(--lvl5);
}
.cell:hover {
  border-color: var(--gold);
  box-shadow: 0 3px 10px rgba(0, 0, 0, 0.08);
}
.cell:focus-visible {
  outline: 2px solid var(--gold-strong);
  outline-offset: 1px;
}
.cell.dim {
  opacity: 0.42;
}
.cell.selected {
  background: #20262d;
  border-color: #20262d;
  color: #f4f1ea;
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.18);
}
.cell.selected::before {
  background: var(--gold);
  color: #20262d;
}
.cell .txt {
  flex: 1;
}

.footnote {
  margin: 22px 0 0;
  padding: 12px 14px;
  background: #eee7d3;
  border: 1px dashed #c9bd9a;
  border-radius: var(--radius);
  font-size: 11.5px;
  color: #5c5340;
  line-height: 1.55;
}
.footnote b {
  color: #3d3627;
}
.overlap-notes {
  margin: 14px 0 0;
  padding: 12px 14px;
  background: var(--card);
  border: 1px solid var(--card-border);
  border-radius: var(--radius);
  font-size: 12px;
  color: var(--muted);
}
.overlap-notes summary {
  cursor: pointer;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--gold-strong);
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
  background: var(--paper);
  border-radius: 3px;
}
.overlap-pair {
  font-family: 'JetBrains Mono', monospace;
  font-weight: 700;
  color: var(--ink);
  margin-right: 2px;
}

@media (min-width: 700px) {
  .top {
    padding: 38px 40px 26px;
  }
  .header-flex {
    flex-direction: row;
    align-items: flex-end;
    justify-content: space-between;
    gap: 48px;
  }
  .chart-bars {
    gap: 16px;
    height: 112px;
  }
  .chart-bar-col {
    width: 30px;
    gap: 8px;
  }
  .chart-bar-track {
    width: 12px;
    height: 70px;
  }
  .toolbar {
    flex-direction: row;
    align-items: center;
    flex-wrap: wrap;
    gap: 20px 28px;
    padding: 14px 40px;
  }
  .progress-track {
    width: 180px;
  }
  .pillar-nav {
    margin-left: auto;
    overflow-x: visible;
    flex-wrap: wrap;
  }
  .scale-legend {
    order: 0;
  }
  .toolbar-actions {
    width: auto;
  }
  .btn-swot,
  .btn-save {
    width: auto;
    padding: 9px 18px;
  }
}

@media (min-width: 860px) {
  .matrix-wrap {
    padding: 0 40px 80px;
  }
  .matrix-scroll {
    padding-top: 28px;
  }
  .col-legend {
    display: grid;
    grid-template-columns: 300px repeat(5, minmax(210px, 1fr));
    gap: 10px;
    padding: 0 0 10px;
    min-width: 1360px;
  }
  .pillar-section {
    min-width: 1360px;
    margin-bottom: 6px;
  }
  .pillar-band {
    flex-wrap: nowrap;
    gap: 14px;
    padding: 14px 16px;
    margin-top: 22px;
    position: sticky;
    top: calc(var(--bar-h, 56px) + 64px);
    z-index: 20;
  }
  .pillar-band h2 {
    font-size: 19px;
  }
  .csf-row {
    display: grid;
    grid-template-columns: 300px repeat(5, minmax(210px, 1fr));
    gap: 10px;
    padding: 10px 0;
  }
  .stem {
    padding: 6px 14px 6px 0;
    position: sticky;
    left: 0;
  }
  .cell {
    padding: 10px 12px;
    font-size: 12.5px;
    align-items: flex-start;
    min-height: auto;
  }
  .cell:hover {
    transform: translateY(-1px);
  }
  .footnote,
  .overlap-notes {
    max-width: 1360px;
    margin-left: auto;
    margin-right: auto;
  }
}
</style>
