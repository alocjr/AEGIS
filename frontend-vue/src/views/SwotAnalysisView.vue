<script setup lang="ts">
import { ref, onMounted, onUnmounted, reactive } from 'vue'
import {
  getSwotAnalysis,
  updateSwotAnalysis,
  type SwotAnalysis,
  type SwotAnalysisPayload,
  type SwotInitiative,
  type SwotListField,
  type SwotTowsField,
  type SwotVereditoTipo,
} from '@/api/swotAnalysis'

const loading = ref(true)
const error = ref<string | null>(null)
const saveState = ref<'idle' | 'saving' | 'saved' | 'error'>('idle')
const saveError = ref<string | null>(null)
const showMethod = ref(true)
const showCatalog = ref(false)
const openHelp = ref<SwotListField | null>(null)
let saving = false
let pendingSave = false

const PILLARS = [
  { name: 'Dados', q: 'Temos dados proprietários, limpos e integrados para alimentar e contextualizar modelos?' },
  { name: 'Talento', q: 'Há competência técnica e lideranças com letramento para conduzir?' },
  { name: 'Infraestrutura', q: 'A arquitetura (nuvem, APIs) consome IA com segurança, sem travar no legado?' },
  {
    name: 'Governança & Regulação',
    q: 'Temos conformidade (LGPD), auditoria de viés e alucinação, isolamento de dados sensíveis e validação humana no que é crítico?',
  },
  { name: 'Cultura & Liderança', q: 'Há patrocínio do topo e abertura à mudança — ou medo e resistência?' },
  { name: 'Portfólio de casos', q: 'Sabemos priorizar casos por valor e prontidão, com dono definido?' },
  { name: 'Ecossistema & Fornecedores', q: 'Temos flexibilidade contra o lock-in de um único fornecedor ou modelo?' },
]

type QuadrantHint = {
  letter: string
  name: string
  locus: string
  neg: boolean
  groups: { label: string; text: string }[]
}

/** Repertório de partida por quadrante — estímulo, não checklist. */
const QUADRANT_HINTS: Record<SwotListField, QuadrantHint> = {
  forcas: {
    letter: 'F',
    name: 'Forças',
    locus: 'interno · positivo',
    neg: false,
    groups: [
      {
        label: 'Dados',
        text: 'base proprietária ampla, integrada e de qualidade, com histórico longo.',
      },
      {
        label: 'Talento & cultura',
        text: 'time de dados/IA constituído; lideranças com letramento; cultura de experimentação.',
      },
      {
        label: 'Infra & governança',
        text: 'dados centralizados e isolados, nuvem madura; política de IA, auditoria de viés e validação humana (human-in-the-loop).',
      },
      {
        label: 'Portfólio & recursos',
        text: 'casos em produção com ROI comprovado; caixa e patrocínio do topo.',
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
        label: 'Tecnologia & ecossistema',
        text: 'barateamento e maturação dos modelos; IA generativa, RAG e agêntica; ferramentas abertas e parceiros.',
      },
      {
        label: 'Mercado & clientes',
        text: 'demanda por experiências personalizadas; novos modelos de receita; segmentos mal atendidos.',
      },
      {
        label: 'Concorrência',
        text: 'concorrentes lentos ou pouco maduros; janela para liderar.',
      },
      {
        label: 'Talento & incentivos',
        text: 'oferta crescente de talento e ecossistemas locais; editais e incentivos.',
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
        label: 'Dados',
        text: 'silos, baixa qualidade, sem propriedade clara nem rotulagem.',
      },
      {
        label: 'Talento & cultura',
        text: 'falta de especialistas; letramento desigual; resistência ou aversão a risco.',
      },
      {
        label: 'Infra & governança',
        text: 'legado e dívida técnica; sem governança de IA, auditoria de alucinações/viés ou isolamento de dados sensíveis.',
      },
      {
        label: 'Portfólio & recursos',
        text: 'só pilotos sem escala; sem dono, critério de priorização ou business case.',
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
        text: 'players maduros e marketplaces com IA avançada; risco de disrupção do core.',
      },
      {
        label: 'Regulação',
        text: 'LGPD, marco de IA e regras setoriais elevando o custo de conformidade; exposição de dados sensíveis a modelos públicos.',
      },
      {
        label: 'Fornecedores & modelo',
        text: 'lock-in, mudança de preço ou descontinuação; alucinação, viés e risco reputacional.',
      },
      {
        label: 'Talento & ritmo',
        text: 'guerra por talento; velocidade da mudança e obsolescência precoce das ferramentas superando a adaptação.',
      },
    ],
  },
}

const CATALOG = (['forcas', 'oportunidades', 'fraquezas', 'ameacas'] as SwotListField[]).map(
  (field) => QUADRANT_HINTS[field]
)

const QUADRANTS: {
  field: SwotListField
  letter: string
  name: string
  quest: string
  neg: boolean
}[] = [
  {
    field: 'forcas',
    letter: 'F',
    name: 'Forças',
    quest: 'O que a organização tem hoje que sustenta a estratégia de IA?',
    neg: false,
  },
  {
    field: 'oportunidades',
    letter: 'O',
    name: 'Oportunidades',
    quest: 'Que condição externa a estratégia de IA pode explorar?',
    neg: false,
  },
  {
    field: 'fraquezas',
    letter: 'f',
    name: 'Fraquezas',
    quest: 'O que, dentro de casa, trava a estratégia de IA?',
    neg: true,
  },
  {
    field: 'ameacas',
    letter: 'A',
    name: 'Ameaças',
    quest: 'O que pode inviabilizar ou encarecer a estratégia de IA?',
    neg: true,
  },
]

const TOWS: {
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

const VEREDITO_OPTIONS: { id: SwotVereditoTipo; label: string }[] = [
  { id: 'executavel', label: 'Executável como está' },
  { id: 'fundacao', label: 'Executável com fase de fundação' },
  { id: 'repensar', label: 'Repensar a estratégia' },
]

const form = ref({
  optica: '',
  forcas: [] as string[],
  fraquezas: [] as string[],
  oportunidades: [] as string[],
  ameacas: [] as string[],
  tows_fo: [] as SwotInitiative[],
  tows_fa: [] as SwotInitiative[],
  tows_fxo: [] as SwotInitiative[],
  tows_fxa: [] as SwotInitiative[],
  veredito_tipo: '' as SwotVereditoTipo,
  veredito_titulo: '',
  veredito_texto: '',
})

const drafts = reactive<Record<SwotListField, string>>({
  forcas: '',
  fraquezas: '',
  oportunidades: '',
  ameacas: '',
})

function emptyInitiative(): SwotInitiative {
  return { acao: '', dono: '', horizonte: '' }
}

function applyDoc(doc: SwotAnalysis) {
  form.value = {
    optica: doc.optica || '',
    forcas: [...(doc.forcas || [])],
    fraquezas: [...(doc.fraquezas || [])],
    oportunidades: [...(doc.oportunidades || [])],
    ameacas: [...(doc.ameacas || [])],
    tows_fo: (doc.tows_fo || []).map((i) => ({ ...i })),
    tows_fa: (doc.tows_fa || []).map((i) => ({ ...i })),
    tows_fxo: (doc.tows_fxo || []).map((i) => ({ ...i })),
    tows_fxa: (doc.tows_fxa || []).map((i) => ({ ...i })),
    veredito_tipo: (doc.veredito_tipo || '') as SwotVereditoTipo,
    veredito_titulo: doc.veredito_titulo || '',
    veredito_texto: doc.veredito_texto || '',
  }
}

async function persist() {
  if (saving) {
    pendingSave = true
    return
  }
  saving = true
  saveState.value = 'saving'
  saveError.value = null
  const payload: SwotAnalysisPayload = { ...form.value }
  try {
    const updated = await updateSwotAnalysis(payload)
    applyDoc(updated)
    saveState.value = 'saved'
    window.setTimeout(() => {
      if (saveState.value === 'saved') saveState.value = 'idle'
    }, 1600)
  } catch (e) {
    saveState.value = 'error'
    saveError.value = e instanceof Error ? e.message : 'Erro ao salvar.'
  } finally {
    saving = false
    if (pendingSave) {
      pendingSave = false
      void persist()
    }
  }
}

function addItem(field: SwotListField) {
  const text = drafts[field].trim()
  if (!text) return
  if (form.value[field].length >= 40) return
  form.value[field] = [...form.value[field], text]
  drafts[field] = ''
  void persist()
}

function removeItem(field: SwotListField, index: number) {
  form.value[field] = form.value[field].filter((_, i) => i !== index)
  void persist()
}

function onItemBlur(field: SwotListField, index: number, ev: Event) {
  const input = ev.target as HTMLInputElement
  const next = input.value.trim()
  const list = [...form.value[field]]
  if (!next) list.splice(index, 1)
  else list[index] = next
  form.value[field] = list
  void persist()
}

function onDraftKeydown(field: SwotListField, ev: KeyboardEvent) {
  if (ev.key === 'Enter') {
    ev.preventDefault()
    addItem(field)
  }
}

function addInitiative(field: SwotTowsField) {
  if (form.value[field].length >= 20) return
  form.value[field] = [...form.value[field], emptyInitiative()]
}

function removeInitiative(field: SwotTowsField, index: number) {
  form.value[field] = form.value[field].filter((_, i) => i !== index)
  void persist()
}

function onInitiativeBlur(field: SwotTowsField, index: number, key: keyof SwotInitiative, ev: Event) {
  const input = ev.target as HTMLInputElement
  const list = form.value[field].map((row, i) =>
    i === index ? { ...row, [key]: input.value } : row
  )
  const row = list[index]
  if (row && !row.acao.trim() && !row.dono.trim() && !row.horizonte.trim()) {
    list.splice(index, 1)
  }
  form.value[field] = list
  void persist()
}

function setVereditoTipo(tipo: SwotVereditoTipo) {
  form.value.veredito_tipo = form.value.veredito_tipo === tipo ? '' : tipo
  void persist()
}

function toggleHelp(field: SwotListField, ev?: Event) {
  ev?.stopPropagation()
  openHelp.value = openHelp.value === field ? null : field
}

function onDocPointerDown(ev: Event) {
  const target = ev.target as HTMLElement | null
  if (!target) return
  if (target.closest('.q-help') || target.closest('.q-help-btn')) return
  openHelp.value = null
}

onMounted(async () => {
  document.addEventListener('pointerdown', onDocPointerDown)
  try {
    const doc = await getSwotAnalysis()
    applyDoc(doc)
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Erro ao carregar SWOT.'
  } finally {
    loading.value = false
  }
})

onUnmounted(() => {
  document.removeEventListener('pointerdown', onDocPointerDown)
})
</script>

<template>
  <div class="wrap">
    <div class="page-header">
      <div>
        <p class="eyebrow">Instrumento estratégico · Valorian</p>
        <h1 class="page-title">SWOT de <em>IA</em></h1>
        <p class="page-desc">
          Diagnosticar a organização sob a ótica da estratégia de IA — da matriz ao veredito.
        </p>
      </div>
      <div class="save-pill" :data-state="saveState">
        <span v-if="saveState === 'saving'">Salvando…</span>
        <span v-else-if="saveState === 'saved'">Salvo</span>
        <span v-else-if="saveState === 'error'">{{ saveError || 'Erro ao salvar' }}</span>
        <span v-else>Auto-salva</span>
      </div>
    </div>

    <div v-if="loading" class="card">Carregando…</div>
    <div v-else-if="error" class="card error-msg">{{ error }}</div>

    <template v-else>
      <section class="card method">
        <button type="button" class="method-toggle" @click="showMethod = !showMethod">
          <span>O método em uma página</span>
          <span>{{ showMethod ? '−' : '+' }}</span>
        </button>
        <div v-if="showMethod" class="method-body">
          <p>
            O objeto é a <strong>organização</strong>. A ótica é a <strong>estratégia organizacional de IA</strong>.
            Um item só entra se afeta materialmente a capacidade de executar essa estratégia.
          </p>
          <h3>Sete pilares</h3>
          <div class="pillarq">
            <div v-for="p in PILLARS" :key="p.name">
              <b>{{ p.name }}.</b> <i>{{ p.q }}</i>
            </div>
          </div>
          <h3>Duas regras</h3>
          <ul class="bullets">
            <li>
              <strong>Locus disciplinado.</strong> Forças e Fraquezas são internas. Oportunidades e Ameaças são do
              ambiente.
            </li>
            <li>
              <strong>Baseado em evidência.</strong> Cada item ancorado em fato ou métrica — priorize por impacto
              (ideal: 2–3 por quadrante).
            </li>
          </ul>
          <ol class="steps">
            <li><strong>Declare a ótica.</strong> Estratégia de IA em uma frase.</li>
            <li><strong>Varra os quadrantes</strong> pelos sete pilares.</li>
            <li><strong>Aplique o crivo.</strong> Descarte o que não afeta a estratégia.</li>
            <li><strong>Priorize.</strong> Fique com os 2–3 itens mais fortes de cada quadrante.</li>
            <li><strong>Cruze e conclua.</strong> TOWS → iniciativas → veredito.</li>
          </ol>
          <button type="button" class="catalog-toggle" @click="showCatalog = !showCatalog">
            {{ showCatalog ? 'Ocultar banco de itens' : 'Ver banco de itens (partida)' }}
          </button>
          <div v-if="showCatalog" class="catalog">
            <div v-for="c in CATALOG" :key="c.letter" class="cat" :class="{ neg: c.neg }">
              <div class="tag">
                <span class="letter">{{ c.letter }}</span>
                <span class="name">{{ c.name }}</span>
              </div>
              <p class="cat-locus">{{ c.locus }}</p>
              <ul class="cat-groups">
                <li v-for="g in c.groups" :key="g.label">
                  <b>{{ g.label }}</b> — {{ g.text }}
                </li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      <section class="object card-object">
        <div class="eyebrow gold">1 · A ótica · estratégia organizacional de IA</div>
        <textarea
          v-model="form.optica"
          class="optica-write"
          rows="3"
          maxlength="2000"
          placeholder="Em uma frase: a ambição declarada de para onde a organização quer ir com IA…"
          @blur="persist"
        />
      </section>

      <section class="matrix-block">
        <div class="section-head">
          <div class="eyebrow">2 · Matriz</div>
          <h2>Interno × Externo</h2>
          <p class="hint">Adicione itens em lista. Priorize 2–3 por quadrante. Toque no ? para ver o repertório de partida.</p>
        </div>
        <div class="axis-top"><span>Interno</span><span>Externo</span></div>
        <div class="matrix">
          <div class="node">A<br />ORGANI-<br />ZAÇÃO</div>
          <div
            v-for="q in QUADRANTS"
            :key="q.field"
            class="q"
            :class="{ neg: q.neg, 'help-open': openHelp === q.field }"
          >
            <button
              type="button"
              class="q-help-btn"
              :aria-expanded="openHelp === q.field"
              :aria-label="`Repertório de partida · ${q.name}`"
              @click="toggleHelp(q.field, $event)"
            >
              ?
            </button>
            <div v-if="openHelp === q.field" class="q-help" role="dialog" :aria-label="`Ajuda · ${q.name}`">
              <div class="q-help-head">
                <span class="q-help-letter" :class="{ neg: q.neg }">{{ QUADRANT_HINTS[q.field].letter }}</span>
                <div>
                  <strong>{{ QUADRANT_HINTS[q.field].name }}</strong>
                  <span class="q-help-locus">{{ QUADRANT_HINTS[q.field].locus }}</span>
                </div>
              </div>
              <p class="q-help-note">
                Repertório de partida, organizado pelos pilares — estímulo, não checklist a preencher inteiro.
              </p>
              <ul class="q-help-list">
                <li v-for="g in QUADRANT_HINTS[q.field].groups" :key="g.label">
                  <span class="q-help-pillar">{{ g.label }}</span>
                  <span class="q-help-text">{{ g.text }}</span>
                </li>
              </ul>
            </div>
            <div class="tag">
              <span class="letter">{{ q.letter }}</span>
              <span class="name">{{ q.name }}</span>
            </div>
            <div class="quest">{{ q.quest }}</div>
            <ul class="item-list">
              <li v-for="(item, idx) in form[q.field]" :key="q.field + idx" class="item-row">
                <input
                  :value="item"
                  class="item-input"
                  maxlength="500"
                  @blur="onItemBlur(q.field, idx, $event)"
                />
                <button type="button" class="item-remove" title="Remover" @click="removeItem(q.field, idx)">
                  ×
                </button>
              </li>
            </ul>
            <div class="item-add">
              <input
                v-model="drafts[q.field]"
                type="text"
                maxlength="500"
                placeholder="Adicionar item…"
                @keydown="onDraftKeydown(q.field, $event)"
              />
              <button type="button" @click="addItem(q.field)">+</button>
            </div>
          </div>
        </div>
      </section>

      <section class="tows-block">
        <div class="section-head">
          <div class="eyebrow">3 · Cruzamento TOWS</div>
          <h2>Do diagnóstico à decisão</h2>
          <p class="hint">
            Cada cruzamento vira uma iniciativa (ação, dono, horizonte). Comece pelo f × A — é onde a estratégia pode
            quebrar.
          </p>
        </div>
        <div class="tows">
          <div v-for="t in TOWS" :key="t.field" class="tows-cell" :class="{ hard: t.hard }">
            <span class="k">{{ t.key }}</span>
            <span class="qz">{{ t.quest }}</span>
            <p class="thint">{{ t.hint }}</p>
            <div v-for="(row, idx) in form[t.field]" :key="t.field + idx" class="init-row">
              <input
                :value="row.acao"
                class="init-acao"
                maxlength="1000"
                placeholder="Ação / iniciativa"
                @blur="onInitiativeBlur(t.field, idx, 'acao', $event)"
              />
              <div class="init-meta">
                <input
                  :value="row.dono"
                  maxlength="200"
                  placeholder="Dono"
                  @blur="onInitiativeBlur(t.field, idx, 'dono', $event)"
                />
                <input
                  :value="row.horizonte"
                  maxlength="120"
                  placeholder="Horizonte"
                  @blur="onInitiativeBlur(t.field, idx, 'horizonte', $event)"
                />
                <button type="button" class="item-remove" title="Remover" @click="removeInitiative(t.field, idx)">
                  ×
                </button>
              </div>
            </div>
            <button type="button" class="add-init" @click="addInitiative(t.field)">+ Iniciativa</button>
          </div>
        </div>
      </section>

      <section class="verdict">
        <div class="eyebrow gold">4 · Veredito</div>
        <p class="verdict-lead">
          A estratégia se sustenta, precisa de uma fase de fundação, ou deve ser repensada?
        </p>
        <div class="verdict-types">
          <button
            v-for="opt in VEREDITO_OPTIONS"
            :key="opt.id"
            type="button"
            class="vtype"
            :class="{ active: form.veredito_tipo === opt.id }"
            @click="setVereditoTipo(opt.id)"
          >
            {{ opt.label }}
          </button>
        </div>
        <input
          v-model="form.veredito_titulo"
          class="verdict-title"
          maxlength="300"
          placeholder="Título do veredito (ex.: Ambição certa, organização ainda não pronta.)"
          @blur="persist"
        />
        <textarea
          v-model="form.veredito_texto"
          class="verdict-text"
          rows="5"
          maxlength="8000"
          placeholder="Conclusão e recomendação…"
          @blur="persist"
        />
      </section>
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
  max-width: 920px;
  margin: 0 auto;
  padding: 28px 20px 72px;
  color: var(--ink);
}
.page-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
  margin-bottom: 22px;
}
.eyebrow {
  font-size: 0.7rem;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: var(--gold);
  font-weight: 600;
  margin: 0 0 6px;
}
.eyebrow.gold {
  color: var(--gold-2);
}
.page-title {
  font-family: var(--serif);
  font-weight: 600;
  font-size: clamp(1.9rem, 5vw, 2.6rem);
  line-height: 1.05;
  color: var(--navy);
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
  line-height: 1.5;
  max-width: 48ch;
}
.save-pill {
  flex-shrink: 0;
  font-size: 11px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  padding: 6px 10px;
  border: 1px solid var(--line);
  border-radius: 999px;
  color: var(--muted);
  background: #fff;
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
  max-width: 180px;
}
.card {
  background: var(--ivory-2);
  border: 1px solid var(--line);
  border-radius: 4px;
  padding: 18px 20px;
  margin-bottom: 16px;
}
.error-msg {
  color: #8f2b2b;
}
.method-toggle,
.catalog-toggle {
  width: 100%;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: none;
  border: none;
  font: inherit;
  font-weight: 700;
  color: var(--navy);
  cursor: pointer;
  padding: 0;
  text-align: left;
}
.catalog-toggle {
  margin-top: 14px;
  font-size: 13px;
  color: var(--gold);
  font-weight: 600;
  justify-content: flex-start;
  gap: 6px;
}
.method-body {
  margin-top: 14px;
  font-size: 14px;
  line-height: 1.55;
}
.method-body h3 {
  font-size: 0.95rem;
  color: var(--navy);
  margin: 1.1em 0 0.35em;
}
.pillarq {
  border-top: 1px solid var(--line);
  margin: 0.4em 0 0.8em;
}
.pillarq div {
  padding: 8px 0;
  border-bottom: 1px solid var(--line);
  font-size: 0.9rem;
  line-height: 1.42;
}
.pillarq b {
  color: var(--navy);
}
.pillarq i {
  color: #3a3f49;
  font-style: italic;
}
.bullets {
  list-style: none;
  margin: 0;
  padding: 0;
}
.bullets li {
  position: relative;
  padding: 0 0 0.55em 18px;
  font-size: 0.92rem;
}
.bullets li::before {
  content: '';
  position: absolute;
  left: 2px;
  top: 0.55em;
  width: 6px;
  height: 6px;
  transform: rotate(45deg);
  background: var(--gold);
}
.steps {
  list-style: none;
  margin: 0.4em 0 0;
  padding: 0;
  counter-reset: s;
}
.steps li {
  position: relative;
  padding: 2px 0 0.75em 42px;
  counter-increment: s;
  font-size: 0.92rem;
}
.steps li::before {
  content: counter(s, decimal-leading-zero);
  position: absolute;
  left: 0;
  top: -2px;
  font-family: var(--serif);
  font-weight: 700;
  font-size: 1.15rem;
  color: var(--gold);
}
.steps li strong {
  display: block;
}
.catalog {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-top: 12px;
}
.cat {
  background: #fff;
  border: 1px solid var(--line);
  border-top: 3px solid var(--gold);
  padding: 14px 15px;
}
.cat.neg {
  border-top-color: var(--oxblood);
}
.cat .tag {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-bottom: 2px;
}
.cat .letter {
  font-family: var(--serif);
  font-weight: 700;
  font-size: 1.35rem;
  color: var(--gold);
  line-height: 1;
}
.cat.neg .letter {
  color: var(--oxblood);
}
.cat .name {
  font-weight: 700;
  color: var(--navy);
  font-size: 0.92rem;
}
.cat-locus {
  margin: 2px 0 8px;
  font-size: 0.68rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--muted);
  font-weight: 600;
}
.cat-groups {
  list-style: none;
  margin: 0;
  padding: 0;
}
.cat-groups li {
  position: relative;
  font-size: 0.84rem;
  padding: 0 0 0.55em 14px;
  line-height: 1.4;
}
.cat-groups li::before {
  content: '';
  position: absolute;
  left: 1px;
  top: 0.55em;
  width: 5px;
  height: 5px;
  transform: rotate(45deg);
  background: var(--gold);
}
.cat.neg .cat-groups li::before {
  background: var(--oxblood);
}
.cat-groups b {
  color: var(--navy);
}
.card-object {
  background: var(--navy);
  color: #f1ebdd;
  border-left: 4px solid var(--gold);
  padding: 18px 20px;
  margin-bottom: 18px;
  border-radius: 2px;
}
.optica-write {
  width: 100%;
  margin-top: 10px;
  border: none;
  outline: none;
  resize: vertical;
  background: transparent;
  color: #fbf8f1;
  font-family: var(--serif);
  font-size: 1.08rem;
  line-height: 1.45;
  padding: 0;
}
.optica-write::placeholder {
  color: #9da6b8;
}
.section-head {
  margin-bottom: 12px;
}
.section-head h2 {
  font-family: var(--serif);
  font-weight: 600;
  color: var(--navy);
  font-size: clamp(1.25rem, 3.5vw, 1.55rem);
  margin: 0.15em 0 0.3em;
}
.section-head .hint {
  margin: 0;
  color: var(--muted);
  font-size: 0.88rem;
}
.axis-top {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-bottom: 6px;
}
.axis-top span {
  text-align: center;
  font-size: 0.68rem;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: var(--muted);
  font-weight: 600;
}
.matrix {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  position: relative;
  margin-bottom: 28px;
}
.q {
  background: #fff;
  border: 1px solid var(--line);
  border-top: 3px solid var(--gold);
  padding: 14px 16px;
  min-height: 180px;
  position: relative;
}
.q.help-open {
  z-index: 5;
}
.q.neg {
  border-top-color: var(--oxblood);
}
.q-help-btn {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  border: 1px solid var(--line);
  background: #fff;
  color: var(--gold);
  font-family: var(--serif);
  font-weight: 700;
  font-size: 13px;
  line-height: 1;
  cursor: pointer;
  z-index: 3;
  display: grid;
  place-content: center;
  padding: 0;
}
.q.neg .q-help-btn {
  color: var(--oxblood);
}
.q-help-btn:hover,
.q-help-btn[aria-expanded='true'] {
  border-color: var(--gold);
  background: #fffaf0;
}
.q.neg .q-help-btn:hover,
.q.neg .q-help-btn[aria-expanded='true'] {
  border-color: var(--oxblood);
  background: #fcf6f4;
}
.q-help {
  position: absolute;
  top: 36px;
  right: 8px;
  width: min(300px, calc(100% - 16px));
  max-height: min(340px, 70vh);
  overflow: auto;
  background: #fffef9;
  border: 1px solid var(--line);
  box-shadow: 0 10px 28px rgba(14, 27, 51, 0.18);
  padding: 12px 14px;
  z-index: 6;
  border-radius: 2px;
}
.q.neg .q-help {
  border-color: rgba(124, 58, 58, 0.28);
  background: #fffaf8;
}
.q-help-head {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  margin-bottom: 8px;
}
.q-help-letter {
  font-family: var(--serif);
  font-weight: 700;
  font-size: 1.35rem;
  color: var(--gold);
  line-height: 1;
}
.q-help-letter.neg {
  color: var(--oxblood);
}
.q-help-head strong {
  display: block;
  color: var(--navy);
  font-size: 0.95rem;
}
.q-help-locus {
  display: block;
  margin-top: 2px;
  font-size: 0.66rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--muted);
  font-weight: 600;
}
.q-help-note {
  margin: 0 0 10px;
  font-size: 0.78rem;
  line-height: 1.4;
  color: var(--muted);
  font-style: italic;
}
.q-help-list {
  list-style: none;
  margin: 0;
  padding: 0;
}
.q-help-list li {
  padding: 8px 0;
  border-top: 1px solid var(--line);
}
.q-help-list li:first-child {
  border-top: none;
  padding-top: 0;
}
.q-help-pillar {
  display: block;
  font-size: 0.72rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  font-weight: 700;
  color: var(--navy);
  margin-bottom: 3px;
}
.q.neg .q-help-pillar {
  color: var(--oxblood);
}
.q-help-text {
  display: block;
  font-size: 0.82rem;
  line-height: 1.4;
  color: #3a3f49;
}
.q .tag {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-bottom: 6px;
  padding-right: 28px;
}
.q .letter {
  font-family: var(--serif);
  font-weight: 700;
  font-size: 1.4rem;
  color: var(--gold);
  line-height: 1;
}
.q.neg .letter {
  color: var(--oxblood);
}
.q .name {
  font-weight: 700;
  color: var(--navy);
  font-size: 0.95rem;
}
.q .quest {
  font-size: 0.8rem;
  color: var(--muted);
  font-style: italic;
  margin: 0 0 10px;
  line-height: 1.35;
}
.node {
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  width: 74px;
  height: 74px;
  border-radius: 50%;
  background: var(--navy);
  color: var(--gold-2);
  display: grid;
  place-content: center;
  text-align: center;
  font-size: 0.58rem;
  letter-spacing: 0.1em;
  font-weight: 700;
  border: 2px solid var(--gold);
  box-shadow: 0 4px 18px rgba(14, 27, 51, 0.35);
  z-index: 2;
  line-height: 1.15;
  pointer-events: none;
}
.item-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 5px;
}
.item-row {
  display: flex;
  gap: 4px;
  align-items: center;
}
.item-input {
  flex: 1;
  min-width: 0;
  border: none;
  border-bottom: 1px dotted var(--line);
  background: transparent;
  font-size: 12.5px;
  color: var(--ink);
  font-family: inherit;
  padding: 4px 2px;
  outline: none;
}
.item-input:focus {
  border-bottom-color: var(--gold);
  background: #fffef9;
}
.item-remove {
  flex-shrink: 0;
  width: 24px;
  height: 24px;
  border: none;
  background: transparent;
  color: var(--muted);
  cursor: pointer;
  font-size: 16px;
  line-height: 1;
  border-radius: 4px;
}
.item-remove:hover {
  color: var(--oxblood);
  background: #f1e1dd;
}
.item-add {
  display: flex;
  gap: 6px;
  margin-top: 8px;
}
.item-add input {
  flex: 1;
  min-width: 0;
  border: 1px dashed var(--line);
  border-radius: 3px;
  background: #fff;
  font-size: 12px;
  padding: 6px 8px;
  font-family: inherit;
  color: var(--ink);
  outline: none;
}
.item-add input:focus {
  border-color: var(--gold);
  border-style: solid;
}
.item-add button,
.add-init {
  flex-shrink: 0;
  border: 1px solid var(--line);
  border-radius: 3px;
  background: #fff;
  color: var(--ink);
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
}
.item-add button {
  width: 30px;
}
.item-add button:hover,
.add-init:hover {
  border-color: var(--gold);
  color: var(--gold);
}
.add-init {
  margin-top: 8px;
  width: 100%;
  padding: 7px 10px;
  font-size: 12px;
}
.tows {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-bottom: 24px;
}
.tows-cell {
  border: 1px solid var(--line);
  padding: 14px 16px;
  background: #fff;
}
.tows-cell.hard {
  border-color: var(--oxblood);
  background: #fcf6f4;
}
.tows-cell .k {
  display: block;
  font-family: var(--serif);
  font-weight: 700;
  color: var(--gold);
  font-size: 0.88rem;
  letter-spacing: 0.05em;
}
.tows-cell.hard .k {
  color: var(--oxblood);
}
.tows-cell .qz {
  display: block;
  font-style: italic;
  color: var(--muted);
  font-size: 0.82rem;
  margin: 0.35em 0 0.2em;
  line-height: 1.35;
}
.thint {
  font-size: 0.88rem;
  margin: 0 0 10px;
  line-height: 1.4;
  color: var(--ink);
}
.init-row {
  border-top: 1px solid var(--line);
  padding: 8px 0;
}
.init-acao {
  width: 100%;
  border: none;
  border-bottom: 1px dotted var(--line);
  background: transparent;
  font-size: 13px;
  padding: 4px 2px;
  font-family: inherit;
  outline: none;
  color: var(--ink);
}
.init-meta {
  display: flex;
  gap: 6px;
  margin-top: 6px;
  align-items: center;
}
.init-meta input {
  flex: 1;
  min-width: 0;
  border: 1px solid var(--line);
  border-radius: 3px;
  font-size: 12px;
  padding: 5px 7px;
  font-family: inherit;
  outline: none;
}
.verdict {
  background: var(--navy);
  color: #efe9db;
  padding: 24px 26px;
  position: relative;
  border-radius: 2px;
}
.verdict::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  background: var(--gold);
}
.verdict-lead {
  margin: 0.4em 0 14px;
  color: #d8d2c4;
  font-size: 0.95rem;
}
.verdict-types {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 14px;
}
.vtype {
  border: 1px solid rgba(227, 203, 147, 0.35);
  background: transparent;
  color: #cfc7b6;
  font-size: 12px;
  padding: 7px 12px;
  cursor: pointer;
  border-radius: 2px;
}
.vtype.active {
  background: rgba(198, 161, 91, 0.2);
  border-color: var(--gold);
  color: var(--gold-2);
}
.verdict-title,
.verdict-text {
  width: 100%;
  border: none;
  outline: none;
  background: rgba(255, 255, 255, 0.04);
  color: #fbf8f1;
  font-family: inherit;
  padding: 10px 12px;
  margin-bottom: 10px;
  border-radius: 2px;
}
.verdict-title {
  font-size: 1.05rem;
  font-weight: 700;
}
.verdict-text {
  resize: vertical;
  font-size: 0.92rem;
  line-height: 1.5;
  min-height: 110px;
}
.verdict-title::placeholder,
.verdict-text::placeholder {
  color: #8c93a6;
}
@media (max-width: 700px) {
  .catalog,
  .matrix,
  .tows {
    grid-template-columns: 1fr;
  }
  .axis-top {
    display: none;
  }
  .node {
    position: static;
    transform: none;
    width: auto;
    height: auto;
    border-radius: 3px;
    margin: 0 0 10px;
    padding: 8px 12px;
    box-shadow: none;
    order: -1;
  }
  .matrix {
    display: flex;
    flex-direction: column;
  }
  .page-header {
    flex-direction: column;
  }
}
</style>
