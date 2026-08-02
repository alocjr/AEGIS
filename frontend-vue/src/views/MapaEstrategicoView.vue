<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import {
  fetchStrategicMap,
  type StrategicMap,
  type StrategicMapDimension,
  type StrategicMapInitiative,
  type StrategicMapItem,
  type StrategicMapQuestion,
} from '@/api/strategicMap'
import {
  createCanvasProject,
  listCanvasProjects,
  updateCanvasProject,
  type CanvasProjectPayload,
  type CanvasProjectSummary,
} from '@/api/canvasProjects'
import { createSwotFromMaturity, type SwotListField, type SwotTowsField } from '@/api/swotAnalysis'

const route = useRoute()
const router = useRouter()

const loading = ref(true)
const error = ref<string | null>(null)
const notice = ref<string | null>(null)
const busy = ref(false)
const map = ref<StrategicMap | null>(null)
const projects = ref<CanvasProjectSummary[]>([])

const openKeys = ref<Set<string>>(new Set())
const linkPanel = ref<string | null>(null)

const dimFilter = ref('')
const onlyWithTows = ref(true)
const onlyWithProjects = ref(false)
const query = ref('')
const quadOn = reactive<Record<SwotListField, boolean>>({
  forcas: true,
  oportunidades: true,
  fraquezas: true,
  ameacas: true,
})

const QUADRANTS: { field: SwotListField; label: string; letter: string; negative: boolean }[] = [
  { field: 'forcas', label: 'Forças', letter: 'F', negative: false },
  { field: 'oportunidades', label: 'Oportunidades', letter: 'O', negative: false },
  { field: 'fraquezas', label: 'Fraquezas', letter: 'f', negative: true },
  { field: 'ameacas', label: 'Ameaças', letter: 'A', negative: true },
]

const QUADRANT_LABEL: Record<SwotListField, string> = {
  forcas: 'Força',
  oportunidades: 'Oportunidade',
  fraquezas: 'Fraqueza',
  ameacas: 'Ameaça',
}

const TOWS_LABEL: Record<SwotTowsField, string> = {
  tows_fo: 'F × O · Ofensiva',
  tows_fa: 'F × A · Defesa',
  tows_fxo: 'f × O · Reforço',
  tows_fxa: 'f × A · Sobrevivência',
}

const CANVAS_QUADRANT_LABEL: Record<string, string> = {
  ganho_rapido: 'Ganho rápido',
  aposta_estrategica: 'Aposta estratégica',
  incremental: 'Incremental',
  evitar: 'Evitar',
}

const DIMENSION_ACCENT: Record<string, string> = {
  strategy: '#7a5aa3',
  data_infra: '#3d6fa8',
  people_culture: '#b9822f',
  gov_risk: '#a3453f',
}

function clip(text: string, max: number): string {
  const value = (text || '').trim()
  return value.length <= max ? value : `${value.slice(0, max - 1).trimEnd()}…`
}

function accentFor(dimId: string): string {
  return DIMENSION_ACCENT[dimId] || 'var(--gold)'
}

function formatDate(iso: string | null): string {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleDateString('pt-BR', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    })
  } catch {
    return iso
  }
}

function dimKey(dim: StrategicMapDimension): string {
  return `d:${dim.id}`
}
function questionKey(dim: StrategicMapDimension, question: StrategicMapQuestion): string {
  return `q:${dim.id}/${question.id}`
}
function itemKey(item: StrategicMapItem): string {
  return `i:${item.id}`
}
function towsKey(initiative: StrategicMapInitiative): string {
  return `t:${initiative.id}`
}

function isOpen(key: string): boolean {
  return openKeys.value.has(key)
}

function toggle(key: string) {
  const next = new Set(openKeys.value)
  if (next.has(key)) next.delete(key)
  else next.add(key)
  openKeys.value = next
}

/** Abre até o nível dos itens SWOT; estratégias TOWS ficam recolhidas. */
function openDefault(doc: StrategicMap) {
  const keys = new Set<string>()
  for (const dim of doc.dimensions) {
    keys.add(dimKey(dim))
    for (const question of dim.questions) {
      keys.add(questionKey(dim, question))
      for (const item of question.items) keys.add(itemKey(item))
    }
  }
  keys.add('x:unlinked')
  openKeys.value = keys
}

function expandAll() {
  const doc = map.value
  if (!doc) return
  const keys = new Set<string>(['x:unlinked'])
  const walkItems = (items: StrategicMapItem[]) => {
    for (const item of items) {
      keys.add(itemKey(item))
      for (const initiative of item.initiatives) keys.add(towsKey(initiative))
    }
  }
  for (const dim of doc.dimensions) {
    keys.add(dimKey(dim))
    for (const question of dim.questions) {
      keys.add(questionKey(dim, question))
      walkItems(question.items)
    }
  }
  walkItems(doc.unlinked.swot_items)
  openKeys.value = keys
}

function collapseAll() {
  openKeys.value = new Set()
}

const stats = computed(() => map.value?.stats ?? null)
const head = computed(() => map.value?.source ?? null)

const sourceOptions = computed(() =>
  (map.value?.sources ?? []).map((source) => {
    const parts = [formatDate(source.submitted_at)]
    if (source.tier_label) parts.push(source.tier_label)
    if (source.level_label) parts.push(source.level_label)
    if (!source.complete && source.maturity_response_id) parts.push('rascunho')
    return {
      value: source.swot_id ? `sw:${source.swot_id}` : `mr:${source.maturity_response_id}`,
      label: parts.filter(Boolean).join(' · '),
      hasSwot: !!source.swot_id,
    }
  })
)

const selectedSource = computed(() => {
  const current = head.value
  if (!current) return ''
  if (current.swot_id) return `sw:${current.swot_id}`
  return current.maturity_response_id ? `mr:${current.maturity_response_id}` : ''
})

function matches(text: string | null | undefined): boolean {
  const term = query.value.trim().toLowerCase()
  if (!term) return true
  return (text || '').toLowerCase().includes(term)
}

function initiativeProjectCount(item: StrategicMapItem): number {
  return item.initiatives.reduce((total, initiative) => total + initiative.projects.length, 0)
}

function itemProjectCount(item: StrategicMapItem): number {
  return item.projects.length + initiativeProjectCount(item)
}

function itemMatchesSearch(item: StrategicMapItem): boolean {
  if (matches(item.texto) || matches(item.evidencia)) return true
  return item.initiatives.some(
    (initiative) =>
      matches(initiative.acao) ||
      initiative.projects.some((project) => matches(project.title))
  ) || item.projects.some((project) => matches(project.title))
}

/** Item entrou no TOWS como lado interno (tem estratégias) ou como contraparte externa. */
function hasTows(item: StrategicMapItem): boolean {
  return item.initiatives.length > 0 || item.used_in > 0
}

function visibleItems(question: StrategicMapQuestion, questionMatched: boolean): StrategicMapItem[] {
  return question.items.filter((item) => {
    if (!quadOn[item.quadrant]) return false
    if (onlyWithTows.value && !hasTows(item)) return false
    if (onlyWithProjects.value && itemProjectCount(item) === 0) return false
    return questionMatched || itemMatchesSearch(item)
  })
}

const filteredDimensions = computed<StrategicMapDimension[]>(() => {
  const doc = map.value
  if (!doc) return []
  return doc.dimensions
    .filter((dim) => !dimFilter.value || dim.id === dimFilter.value)
    .map((dim) => {
      const questions = dim.questions
        .map((question) => {
          const questionMatched = matches(question.text) || matches(question.id)
          const items = visibleItems(question, questionMatched)
          // Pontos de atenção (nota 3) ficam fora do SWOT/TOWS por definição
          const watchlist =
            onlyWithTows.value || onlyWithProjects.value || !questionMatched
              ? []
              : question.watchlist
          return { ...question, items, watchlist }
        })
        .filter((question) => question.items.length > 0 || question.watchlist.length > 0)
      return { ...dim, questions }
    })
    .filter((dim) => dim.questions.length > 0)
})

const hiddenCount = computed(() => {
  const doc = map.value
  if (!doc) return 0
  const shown = filteredDimensions.value.reduce(
    (total, dim) =>
      total + dim.questions.reduce((sum, question) => sum + question.items.length, 0),
    0
  )
  const linkedTotal = doc.dimensions.reduce(
    (total, dim) =>
      total + dim.questions.reduce((sum, question) => sum + question.items.length, 0),
    0
  )
  return Math.max(0, linkedTotal - shown)
})

const unlinkedItems = computed<StrategicMapItem[]>(() => {
  const items = map.value?.unlinked.swot_items ?? []
  return onlyWithTows.value ? items.filter(hasTows) : items
})

const hasUnlinked = computed(() => {
  const doc = map.value
  if (!doc) return false
  return unlinkedItems.value.length > 0 || doc.unlinked.projects.length > 0
})

function projectById(id: string): CanvasProjectSummary | undefined {
  return projects.value.find((project) => project.id === id)
}

function isLinked(project: CanvasProjectSummary, kind: 'item' | 'tows', refId: string): boolean {
  const refs = kind === 'item' ? project.swot_item_ids : project.tows_ids
  return refs.includes(refId)
}

function togglePanel(key: string) {
  linkPanel.value = linkPanel.value === key ? null : key
}

/** Mantém o mapa na mesma fonte após uma alteração de vínculo. */
function currentParams(): { maturityResponseId?: string | null; swotId?: string | null } {
  const current = head.value
  if (current?.swot_id) return { swotId: current.swot_id }
  return { maturityResponseId: current?.maturity_response_id ?? null }
}

async function reload(params?: { maturityResponseId?: string | null; swotId?: string | null }) {
  const [doc, list] = await Promise.all([fetchStrategicMap(params), listCanvasProjects()])
  map.value = doc
  projects.value = list.items
  return doc
}

async function load(params?: { maturityResponseId?: string | null; swotId?: string | null }) {
  loading.value = true
  error.value = null
  try {
    const doc = await reload(params)
    openDefault(doc)
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Falha ao carregar o mapa estratégico.'
  } finally {
    loading.value = false
  }
}

async function onSelectSource(event: Event) {
  const value = (event.target as HTMLSelectElement).value
  const [kind, id] = value.split(':')
  if (!id) return
  linkPanel.value = null
  notice.value = null
  const params =
    kind === 'sw' ? { swotId: id } : { maturityResponseId: id }
  await router.replace({
    query: kind === 'sw' ? { swot: id } : { maturidade: id },
  })
  await load(params)
}

async function generateSwot() {
  const responseId = head.value?.maturity_response_id
  if (!responseId || busy.value) return
  busy.value = true
  notice.value = null
  try {
    const created = await createSwotFromMaturity(responseId)
    const doc = await reload({ swotId: created.id })
    openDefault(doc)
    notice.value = 'SWOT gerada a partir da autoavaliação.'
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Falha ao gerar a SWOT.'
  } finally {
    busy.value = false
  }
}

async function applyLink(
  project: CanvasProjectSummary,
  kind: 'item' | 'tows',
  refId: string,
  link: boolean
) {
  if (busy.value) return
  busy.value = true
  notice.value = null
  try {
    const itemRefs = new Set(project.swot_item_ids)
    const towsRefs = new Set(project.tows_ids)
    const target = kind === 'item' ? itemRefs : towsRefs
    if (link) target.add(refId)
    else target.delete(refId)
    const stillLinked = itemRefs.size + towsRefs.size > 0
    await updateCanvasProject(project.id, {
      swot_item_ids: [...itemRefs],
      tows_ids: [...towsRefs],
      swot_id: stillLinked ? head.value?.swot_id ?? null : null,
    })
    await reload(currentParams())
    notice.value = link ? 'Projeto vinculado ao mapa.' : 'Vínculo removido.'
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Falha ao atualizar o vínculo.'
  } finally {
    busy.value = false
  }
}

function originContext(dim: StrategicMapDimension, question: StrategicMapQuestion): string[] {
  const answer = `Resposta: nota ${question.answer}/5`
  return [
    clip(`Origem: ${dim.name} · ${question.id} — ${question.text}`, 400),
    clip(question.answer_text ? `${answer} — ${question.answer_text}` : answer, 400),
  ]
}

function itemPrefill(
  dim: StrategicMapDimension,
  question: StrategicMapQuestion,
  item: StrategicMapItem
): CanvasProjectPayload {
  const negative = item.quadrant === 'fraquezas' || item.quadrant === 'ameacas'
  return {
    title: clip(item.texto || `${QUADRANT_LABEL[item.quadrant]} · ${question.id}`, 200),
    objetivo_estrategico: clip(head.value?.optica || '', 2000),
    contexto: originContext(dim, question),
    dores: negative ? [clip(item.texto, 400)] : [],
    oportunidade: negative ? [] : [clip(item.texto, 400)],
    swot_id: head.value?.swot_id ?? null,
    swot_item_ids: [item.id],
    tows_ids: [],
  }
}

function initiativePrefill(
  dim: StrategicMapDimension,
  question: StrategicMapQuestion,
  item: StrategicMapItem,
  initiative: StrategicMapInitiative
): CanvasProjectPayload {
  const negative = item.quadrant === 'fraquezas' || item.quadrant === 'ameacas'
  const opportunities = initiative.counterparts
    .filter((counterpart) => counterpart.quadrant === 'oportunidades')
    .map((counterpart) => clip(counterpart.texto, 400))
    .filter(Boolean)
  const threats = initiative.counterparts
    .filter((counterpart) => counterpart.quadrant === 'ameacas')
    .map((counterpart) => clip(counterpart.texto, 400))
    .filter(Boolean)
  return {
    title: clip(initiative.acao || `${TOWS_LABEL[initiative.field]} · ${question.id}`, 200),
    objetivo_estrategico: clip(initiative.acao || head.value?.optica || '', 2000),
    contexto: [
      ...originContext(dim, question),
      clip(`Estratégia ${TOWS_LABEL[initiative.field]} sobre «${item.texto}»`, 400),
    ],
    dores: negative ? [clip(item.texto, 400)] : [],
    oportunidade: opportunities.length ? opportunities : [clip(item.texto, 400)],
    riscos: threats,
    proximo_passo: clip(initiative.acao, 4000),
    swot_id: head.value?.swot_id ?? null,
    swot_item_ids: [item.id],
    tows_ids: [initiative.id],
  }
}

async function createProject(prefill: CanvasProjectPayload) {
  if (busy.value) return
  busy.value = true
  notice.value = null
  try {
    const created = await createCanvasProject(prefill.title || 'Novo projeto')
    await updateCanvasProject(created.id, prefill)
    await reload(currentParams())
    linkPanel.value = null
    notice.value = 'Projeto criado a partir do mapa — complete o canvas em Projetos.'
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Falha ao criar o projeto.'
  } finally {
    busy.value = false
  }
}

onMounted(() => {
  const swot = (route.query.swot as string) || null
  const maturity = (route.query.maturidade as string) || null
  void load(swot ? { swotId: swot } : maturity ? { maturityResponseId: maturity } : undefined)
})
</script>

<template>
  <div class="wrap">
    <header class="page-header">
      <p class="eyebrow">Rastreabilidade da estratégia</p>
      <h1 class="page-title">Mapa Estratégico</h1>
      <p class="page-lead">
        Cada resposta do Modelo de Maturidade virou item da SWOT, cada item virou estratégia TOWS
        e cada estratégia pode virar projeto. Esta é a árvore que liga as três camadas.
      </p>
    </header>

    <div v-if="loading" class="state-card">Carregando o mapa…</div>

    <template v-else>
      <div v-if="error" class="state-card error">{{ error }}</div>

      <div v-if="!head?.maturity_response_id && !head?.swot_id" class="state-card">
        <p class="empty-title">Ainda não há o que mapear</p>
        <p class="empty-text">
          Responda o Modelo de Maturidade e gere a SWOT para ver a árvore de rastreabilidade.
        </p>
        <RouterLink to="/ai-maturity" class="btn-primary">Abrir Modelo de Maturidade</RouterLink>
      </div>

      <template v-else>
        <!-- Cabeçalho da fonte -->
        <section class="card source-card">
          <div class="source-main">
            <div class="source-field">
              <label class="field-label" for="source-select">Autoavaliação de origem</label>
              <select
                id="source-select"
                class="select"
                :value="selectedSource"
                @change="onSelectSource"
              >
                <option v-for="option in sourceOptions" :key="option.value" :value="option.value">
                  {{ option.label }}{{ option.hasSwot ? '' : ' · sem SWOT' }}
                </option>
              </select>
            </div>
            <div class="source-meta">
              <span v-if="head?.tier_label" class="meta-pill">{{ head.tier_label }}</span>
              <span v-if="head?.result?.level_label" class="meta-pill">
                {{ head.result.level_label }}
              </span>
              <span v-if="head?.result" class="meta-item">
                {{ head.result.total_score }}/{{ head.result.max_score }} pts ·
                {{ Math.round(head.result.percent_score) }}%
              </span>
            </div>
          </div>
          <p v-if="head?.optica" class="source-optica">{{ head.optica }}</p>
          <div class="source-actions">
            <RouterLink
              v-if="head?.maturity_response_id"
              :to="`/ai-maturity/${head.maturity_response_id}`"
              class="btn-ghost"
            >Ver autoavaliação</RouterLink>
            <RouterLink v-if="head?.swot_id" :to="`/swot/${head.swot_id}`" class="btn-ghost">
              Abrir SWOT
            </RouterLink>
            <button
              v-else-if="head?.maturity_response_id"
              type="button"
              class="btn-primary"
              :disabled="busy"
              @click="generateSwot"
            >{{ busy ? 'Gerando…' : 'Gerar SWOT' }}</button>
            <RouterLink to="/projetos" class="btn-ghost">Projetos</RouterLink>
          </div>
          <p v-if="notice" class="notice">{{ notice }}</p>
        </section>

        <!-- Indicadores -->
        <section v-if="stats" class="kpi-grid">
          <div class="kpi-card">
            <div class="kpi-label">Perguntas</div>
            <div class="kpi-value">{{ stats.questions }}</div>
            <div class="kpi-sub">respondidas na abrangência</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-label">Itens SWOT</div>
            <div class="kpi-value">{{ stats.swot_items }}</div>
            <div class="kpi-sub">{{ stats.watchlist }} ponto(s) de atenção</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-label">Estratégias TOWS</div>
            <div class="kpi-value">{{ stats.initiatives }}</div>
            <div class="kpi-sub">cruzamentos gerados</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-label">Projetos</div>
            <div class="kpi-value gold">{{ stats.projects_linked }}</div>
            <div class="kpi-sub">de {{ stats.projects_total }} vinculados à árvore</div>
          </div>
        </section>

        <!-- Controles -->
        <section class="card toolbar">
          <div class="toolbar-row">
            <input
              v-model="query"
              type="search"
              class="input"
              placeholder="Buscar pergunta, item, estratégia ou projeto…"
            />
            <select v-model="dimFilter" class="select select--dim">
              <option value="">Todas as dimensões</option>
              <option v-for="dim in map?.dimensions ?? []" :key="dim.id" :value="dim.id">
                {{ dim.name }}
              </option>
            </select>
          </div>
          <div class="toolbar-row">
            <div class="quad-chips">
              <button
                v-for="quadrant in QUADRANTS"
                :key="quadrant.field"
                type="button"
                class="quad-chip"
                :class="[`quad-chip--${quadrant.field}`, { 'is-off': !quadOn[quadrant.field] }]"
                :aria-pressed="quadOn[quadrant.field]"
                @click="quadOn[quadrant.field] = !quadOn[quadrant.field]"
              >
                <span class="quad-letter">{{ quadrant.letter }}</span>
                {{ quadrant.label }}
              </button>
            </div>
            <label class="check">
              <input v-model="onlyWithTows" type="checkbox" />
              Só com estratégia TOWS
            </label>
            <label class="check">
              <input v-model="onlyWithProjects" type="checkbox" />
              Só ramos com projeto
            </label>
            <div class="toolbar-actions">
              <button type="button" class="btn-mini" @click="expandAll">Expandir tudo</button>
              <button type="button" class="btn-mini" @click="collapseAll">Recolher tudo</button>
            </div>
          </div>
        </section>

        <!-- Árvore -->
        <section class="card tree-card">
          <div class="tree-root">
            <span class="root-badge">Maturidade</span>
            <span class="root-title">
              {{ head?.assessment_title || 'Diagnóstico de Maturidade em IA' }}
            </span>
            <span v-if="head?.veredito_titulo" class="root-veredito">
              {{ head.veredito_titulo }}
            </span>
          </div>

          <p v-if="!filteredDimensions.length" class="tree-empty">
            Nenhum ramo corresponde aos filtros atuais.
          </p>

          <ul v-else class="tree">
            <li v-for="dim in filteredDimensions" :key="dim.id" class="node">
              <div class="row row--dim" :style="{ '--accent': accentFor(dim.id) }">
                <button
                  type="button"
                  class="twist"
                  :aria-expanded="isOpen(dimKey(dim))"
                  @click="toggle(dimKey(dim))"
                >{{ isOpen(dimKey(dim)) ? '−' : '+' }}</button>
                <span class="row-accent" aria-hidden="true" />
                <span class="row-title">{{ dim.name }}</span>
                <span class="row-tags">
                  <span class="tag">{{ dim.score.pct }}%</span>
                  <span class="tag muted">{{ dim.score.score }}/{{ dim.score.max }} pts</span>
                  <span class="tag muted">{{ dim.questions.length }} pergunta(s)</span>
                </span>
              </div>

              <ul v-if="isOpen(dimKey(dim))" class="branch">
                <li v-for="question in dim.questions" :key="question.id" class="node">
                  <div class="row row--question">
                    <button
                      type="button"
                      class="twist"
                      :aria-expanded="isOpen(questionKey(dim, question))"
                      @click="toggle(questionKey(dim, question))"
                    >{{ isOpen(questionKey(dim, question)) ? '−' : '+' }}</button>
                    <span class="code">{{ question.id }}</span>
                    <span class="score-pill" :class="`score-pill--${question.answer}`">
                      {{ question.answer }}/5
                    </span>
                    <span class="row-title">{{ question.text }}</span>
                  </div>

                  <ul v-if="isOpen(questionKey(dim, question))" class="branch">
                    <li v-if="question.answer_text" class="node">
                      <p class="answer-note">
                        <span class="answer-label">Resposta</span>{{ question.answer_text }}
                      </p>
                    </li>

                    <li v-for="item in question.items" :key="item.id" class="node">
                      <div class="row row--item" :class="`row--${item.quadrant}`">
                        <button
                          type="button"
                          class="twist"
                          :aria-expanded="isOpen(itemKey(item))"
                          @click="toggle(itemKey(item))"
                        >{{ isOpen(itemKey(item)) ? '−' : '+' }}</button>
                        <span class="quad-badge" :class="`quad-badge--${item.quadrant}`">
                          {{ QUADRANT_LABEL[item.quadrant] }}
                        </span>
                        <span class="row-title">{{ item.texto }}</span>
                        <span class="row-tags">
                          <span v-if="item.pilar" class="tag muted">{{ item.pilar }}</span>
                          <span v-if="item.impacto" class="tag">impacto {{ item.impacto }}</span>
                          <span v-if="item.initiatives.length" class="tag">
                            {{ item.initiatives.length }} estratégia(s)
                          </span>
                          <span v-else-if="item.used_in" class="tag">
                            em {{ item.used_in }} estratégia(s)
                          </span>
                          <span v-if="itemProjectCount(item)" class="tag tag--proj">
                            {{ itemProjectCount(item) }} projeto(s)
                          </span>
                        </span>
                      </div>

                      <ul v-if="isOpen(itemKey(item))" class="branch">
                        <li v-for="initiative in item.initiatives" :key="initiative.id" class="node">
                          <div class="row row--tows">
                            <button
                              type="button"
                              class="twist"
                              :aria-expanded="isOpen(towsKey(initiative))"
                              @click="toggle(towsKey(initiative))"
                            >{{ isOpen(towsKey(initiative)) ? '−' : '+' }}</button>
                            <span class="tows-badge">{{ TOWS_LABEL[initiative.field] }}</span>
                            <span class="row-title">{{ initiative.acao || '—' }}</span>
                            <span class="row-tags">
                              <span v-if="initiative.projects.length" class="tag tag--proj">
                                {{ initiative.projects.length }} projeto(s)
                              </span>
                            </span>
                          </div>

                          <ul v-if="isOpen(towsKey(initiative))" class="branch">
                            <li v-if="initiative.counterparts.length" class="node">
                              <p class="counterparts">
                                <span class="answer-label">Cruza com</span>
                                <span
                                  v-for="counterpart in initiative.counterparts"
                                  :key="counterpart.id"
                                  class="counterpart"
                                  :class="counterpart.quadrant ? `quad-badge--${counterpart.quadrant}` : ''"
                                >{{ counterpart.texto || counterpart.id }}</span>
                              </p>
                            </li>
                            <li
                              v-for="project in initiative.projects"
                              :key="project.id"
                              class="node"
                            >
                              <div class="row row--project">
                                <span class="proj-badge">Projeto</span>
                                <RouterLink :to="`/projetos/${project.id}`" class="row-title link">
                                  {{ project.title }}
                                </RouterLink>
                                <span class="row-tags">
                                  <span v-if="project.quadrant" class="tag">
                                    {{ CANVAS_QUADRANT_LABEL[project.quadrant] }}
                                  </span>
                                  <button
                                    v-if="projectById(project.id)"
                                    type="button"
                                    class="btn-mini btn-mini--danger"
                                    :disabled="busy"
                                    @click="applyLink(projectById(project.id)!, 'tows', initiative.id, false)"
                                  >Desvincular</button>
                                </span>
                              </div>
                            </li>
                            <li class="node">
                              <button
                                type="button"
                                class="btn-mini btn-mini--add"
                                @click="togglePanel(towsKey(initiative))"
                              >+ projeto desta estratégia</button>
                              <div v-if="linkPanel === towsKey(initiative)" class="link-panel">
                                <button
                                  type="button"
                                  class="btn-mini"
                                  :disabled="busy"
                                  @click="createProject(initiativePrefill(dim, question, item, initiative))"
                                >Criar projeto pré-preenchido</button>
                                <p class="panel-label">ou vincular um projeto existente</p>
                                <p v-if="!projects.length" class="panel-empty">
                                  Nenhum projeto criado ainda.
                                </p>
                                <ul v-else class="panel-list">
                                  <li v-for="project in projects" :key="project.id">
                                    <button
                                      type="button"
                                      class="panel-item"
                                      :class="{ 'is-linked': isLinked(project, 'tows', initiative.id) }"
                                      :disabled="busy"
                                      @click="applyLink(project, 'tows', initiative.id, !isLinked(project, 'tows', initiative.id))"
                                    >
                                      <span class="panel-check" aria-hidden="true">
                                        {{ isLinked(project, 'tows', initiative.id) ? '✓' : '+' }}
                                      </span>
                                      {{ project.title }}
                                    </button>
                                  </li>
                                </ul>
                              </div>
                            </li>
                          </ul>
                        </li>

                        <li v-for="project in item.projects" :key="project.id" class="node">
                          <div class="row row--project">
                            <span class="proj-badge">Projeto</span>
                            <RouterLink :to="`/projetos/${project.id}`" class="row-title link">
                              {{ project.title }}
                            </RouterLink>
                            <span class="row-tags">
                              <span v-if="project.quadrant" class="tag">
                                {{ CANVAS_QUADRANT_LABEL[project.quadrant] }}
                              </span>
                              <button
                                v-if="projectById(project.id)"
                                type="button"
                                class="btn-mini btn-mini--danger"
                                :disabled="busy"
                                @click="applyLink(projectById(project.id)!, 'item', item.id, false)"
                              >Desvincular</button>
                            </span>
                          </div>
                        </li>

                        <li class="node">
                          <button
                            type="button"
                            class="btn-mini btn-mini--add"
                            @click="togglePanel(itemKey(item))"
                          >+ projeto deste item</button>
                          <div v-if="linkPanel === itemKey(item)" class="link-panel">
                            <button
                              type="button"
                              class="btn-mini"
                              :disabled="busy"
                              @click="createProject(itemPrefill(dim, question, item))"
                            >Criar projeto pré-preenchido</button>
                            <p class="panel-label">ou vincular um projeto existente</p>
                            <p v-if="!projects.length" class="panel-empty">
                              Nenhum projeto criado ainda.
                            </p>
                            <ul v-else class="panel-list">
                              <li v-for="project in projects" :key="project.id">
                                <button
                                  type="button"
                                  class="panel-item"
                                  :class="{ 'is-linked': isLinked(project, 'item', item.id) }"
                                  :disabled="busy"
                                  @click="applyLink(project, 'item', item.id, !isLinked(project, 'item', item.id))"
                                >
                                  <span class="panel-check" aria-hidden="true">
                                    {{ isLinked(project, 'item', item.id) ? '✓' : '+' }}
                                  </span>
                                  {{ project.title }}
                                </button>
                              </li>
                            </ul>
                          </div>
                        </li>
                      </ul>
                    </li>

                    <li v-for="entry in question.watchlist" :key="`w-${entry.id}`" class="node">
                      <div class="row row--watch">
                        <span class="quad-badge quad-badge--watch">Ponto de atenção</span>
                        <span class="row-title">{{ entry.texto }}</span>
                        <span class="row-tags">
                          <span v-if="entry.nota" class="tag muted">nota {{ entry.nota }}</span>
                        </span>
                      </div>
                    </li>
                  </ul>
                </li>
              </ul>
            </li>
          </ul>

          <p v-if="hiddenCount" class="tree-hint">
            {{ hiddenCount }} item(ns) oculto(s) pelos filtros.
          </p>
        </section>

        <!-- Fora da árvore -->
        <section v-if="hasUnlinked" class="card">
          <button
            type="button"
            class="unlinked-toggle"
            :aria-expanded="isOpen('x:unlinked')"
            @click="toggle('x:unlinked')"
          >
            <span class="sec-title">Fora da árvore</span>
            <span class="tag muted">
              {{ unlinkedItems.length }} item(ns) ·
              {{ map?.unlinked.projects.length ?? 0 }} projeto(s)
            </span>
          </button>
          <div v-if="isOpen('x:unlinked')" class="unlinked-body">
            <p class="panel-label">
              Itens sem pergunta de origem (criados à mão ou importados) e projetos sem vínculo.
            </p>
            <ul v-if="unlinkedItems.length" class="plain-list">
              <li v-for="item in unlinkedItems" :key="item.id">
                <span class="quad-badge" :class="`quad-badge--${item.quadrant}`">
                  {{ QUADRANT_LABEL[item.quadrant] }}
                </span>
                {{ item.texto }}
              </li>
            </ul>
            <ul v-if="map?.unlinked.projects.length" class="plain-list">
              <li v-for="project in map.unlinked.projects" :key="project.id">
                <RouterLink :to="`/projetos/${project.id}`" class="link">
                  {{ project.title }}
                </RouterLink>
                <span class="tag muted">
                  {{ project.linked_to_swot ? 'sem item de origem' : 'sem SWOT de origem' }}
                </span>
              </li>
            </ul>
          </div>
        </section>
      </template>
    </template>
  </div>
</template>

<style scoped>
.wrap {
  max-width: 1080px;
  margin: 0 auto;
  padding: 16px 16px 56px;
}

.page-header {
  margin-bottom: 18px;
}
.eyebrow {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--gold);
  margin: 0 0 8px;
}
.page-title {
  font-family: var(--serif);
  font-size: clamp(22px, 5.5vw, 30px);
  font-weight: 400;
  color: var(--k0);
  margin: 0 0 10px;
  line-height: 1.2;
}
.page-lead {
  margin: 0;
  max-width: 60em;
  font-size: 14px;
  line-height: 1.6;
  color: var(--k3);
}

.card {
  background: var(--wh);
  border: 1px solid var(--bd);
  border-radius: 6px;
  padding: 16px;
  margin-bottom: 14px;
}

.state-card {
  background: var(--wh);
  border: 1px solid var(--bd);
  border-radius: 6px;
  padding: 24px 20px;
  margin-bottom: 14px;
  color: var(--k3);
}
.state-card.error {
  color: var(--low);
  background: var(--lowBg);
  border-color: rgba(182, 55, 55, 0.2);
}
.empty-title {
  font-family: var(--serif);
  font-size: 18px;
  color: var(--k0);
  margin: 0 0 6px;
}
.empty-text {
  margin: 0 0 14px;
  font-size: 14px;
}

.source-card {
  border-top: 3px solid var(--gold);
}
.source-main {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.field-label {
  display: block;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--k5);
  margin-bottom: 6px;
}
.select,
.input {
  width: 100%;
  min-height: 40px;
  padding: 8px 10px;
  border: 1px solid var(--k7);
  border-radius: 6px;
  background: var(--wh);
  color: var(--k0);
  font-family: inherit;
  font-size: 14px;
}
.select:focus,
.input:focus {
  outline: none;
  border-color: var(--goldbd);
}
.source-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}
.meta-item {
  font-size: 13px;
  color: var(--k3);
}
.meta-pill {
  display: inline-flex;
  align-items: center;
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  background: var(--golddim);
  border: 1px solid var(--goldbd);
  color: var(--gold2);
}
.source-optica {
  margin: 12px 0 0;
  font-size: 14px;
  line-height: 1.6;
  color: var(--k3);
}
.source-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 14px;
}
.notice {
  margin: 12px 0 0;
  font-size: 13px;
  color: var(--success);
}

.btn-primary,
.btn-ghost {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 40px;
  padding: 10px 16px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 600;
  text-decoration: none;
  transition: opacity 0.15s, background 0.15s, border-color 0.15s;
}
.btn-primary {
  background: var(--k0);
  color: var(--wh);
  border: 1px solid var(--k0);
}
.btn-primary:hover:not(:disabled) {
  opacity: 0.92;
}
.btn-ghost {
  background: var(--wh);
  color: var(--k0);
  border: 1px solid var(--bd);
}
.btn-ghost:hover {
  border-color: var(--goldbd);
  background: var(--k9);
}
.btn-primary:disabled {
  opacity: 0.6;
  cursor: wait;
}

.kpi-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
  margin-bottom: 14px;
}
.kpi-card {
  background: var(--wh);
  border: 1px solid var(--bd);
  border-radius: 6px;
  padding: 14px;
}
.kpi-label {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--k5);
  margin-bottom: 4px;
}
.kpi-value {
  font-family: var(--serif);
  font-size: 24px;
  color: var(--k0);
  line-height: 1.1;
}
.kpi-value.gold {
  color: var(--gold);
}
.kpi-sub {
  font-size: 12px;
  color: var(--k5);
  margin-top: 2px;
}

.toolbar-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}
.toolbar-row + .toolbar-row {
  margin-top: 10px;
}
.select--dim {
  max-width: 260px;
}
.quad-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.quad-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 10px;
  border-radius: 999px;
  border: 1px solid currentColor;
  background: var(--wh);
  font-size: 12px;
  font-weight: 600;
  transition: opacity 0.15s;
}
.quad-chip .quad-letter {
  font-family: var(--serif);
  font-size: 13px;
}
.quad-chip.is-off {
  color: var(--k5);
  opacity: 0.55;
}
.quad-chip--forcas {
  color: var(--success);
}
.quad-chip--oportunidades {
  color: #3d6fa8;
}
.quad-chip--fraquezas {
  color: var(--warn);
}
.quad-chip--ameacas {
  color: var(--low);
}
.check {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--k3);
}
.toolbar-actions {
  display: flex;
  gap: 6px;
  margin-left: auto;
}
.btn-mini {
  padding: 5px 10px;
  border: 1px solid var(--bd);
  border-radius: 6px;
  background: var(--wh);
  color: var(--k0);
  font-size: 12px;
  font-weight: 600;
}
.btn-mini:hover:not(:disabled) {
  border-color: var(--goldbd);
  background: var(--k9);
}
.btn-mini:disabled {
  opacity: 0.6;
  cursor: wait;
}
.btn-mini--danger {
  color: var(--low);
}
.btn-mini--add {
  color: var(--gold2);
  border-color: var(--goldbd);
  border-style: dashed;
}

.tree-card {
  padding: 16px 12px;
}
.tree-root {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 6px;
  background: var(--k0);
  color: var(--wh);
}
.root-badge {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  padding: 3px 8px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.14);
}
.root-title {
  font-family: var(--serif);
  font-size: 15px;
}
.root-veredito {
  font-size: 12px;
  color: var(--gold2);
}
.tree-empty,
.tree-hint {
  margin: 14px 4px 0;
  font-size: 13px;
  color: var(--k5);
}

.tree,
.branch {
  list-style: none;
  margin: 0;
  padding: 0;
}
.tree {
  margin-top: 8px;
}
.branch {
  margin-left: 10px;
  padding-left: 14px;
}
.branch > .node {
  position: relative;
  padding-left: 14px;
}
.branch > .node::before {
  content: '';
  position: absolute;
  left: 0;
  top: 17px;
  width: 12px;
  height: 1px;
  background: var(--k7);
}
.branch > .node::after {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 1px;
  background: var(--k7);
}
.branch > .node:last-child::after {
  bottom: auto;
  height: 17px;
}

.row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  margin: 3px 0;
  border-radius: 6px;
  border: 1px solid transparent;
  font-size: 14px;
  line-height: 1.4;
}
.row:hover {
  background: var(--k9);
}
.row--dim {
  background: var(--k8);
  border-color: var(--bd);
}
.row--dim .row-title {
  font-family: var(--serif);
  font-size: 16px;
}
.row-accent {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--accent);
  flex-shrink: 0;
}
.row--question .row-title {
  color: var(--k1);
}
.row--item {
  border-left: 3px solid var(--k7);
}
.row--forcas {
  border-left-color: var(--success);
}
.row--oportunidades {
  border-left-color: #3d6fa8;
}
.row--fraquezas {
  border-left-color: var(--warn);
}
.row--ameacas {
  border-left-color: var(--low);
}
.row--tows {
  background: var(--beige-bg);
  border-color: var(--beige-bd);
}
.row--project {
  background: var(--k0);
  color: var(--wh);
}
.row--project .row-title {
  color: var(--wh);
}
.row--watch {
  color: var(--k3);
}
.row-title {
  flex: 1 1 220px;
  min-width: 0;
}
.row-title.link:hover {
  text-decoration: underline;
}
.row-tags {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
}

.twist {
  width: 22px;
  height: 22px;
  flex-shrink: 0;
  border: 1px solid var(--k7);
  border-radius: 4px;
  background: var(--wh);
  color: var(--k3);
  font-size: 13px;
  line-height: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.twist:hover {
  border-color: var(--gold2);
  color: var(--k0);
}

.tag {
  display: inline-flex;
  align-items: center;
  padding: 2px 7px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
  background: var(--golddim);
  border: 1px solid var(--goldbd);
  color: var(--gold2);
  white-space: nowrap;
}
.tag.muted {
  background: var(--k8);
  border-color: var(--bd);
  color: var(--k4);
}
.tag--proj {
  background: rgba(12, 35, 64, 0.08);
  border-color: rgba(12, 35, 64, 0.18);
  color: var(--k0);
}
.code {
  font-family: var(--serif);
  font-size: 12px;
  font-weight: 700;
  color: var(--k4);
  letter-spacing: 0.04em;
}
.score-pill {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
  background: var(--k8);
  color: var(--k3);
  white-space: nowrap;
}
.score-pill--1,
.score-pill--2 {
  background: var(--lowBg);
  color: var(--low);
}
.score-pill--3 {
  background: var(--warnBg);
  color: var(--warn);
}
.score-pill--4,
.score-pill--5 {
  background: var(--successBg);
  color: var(--success);
}

.quad-badge,
.tows-badge,
.proj-badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  white-space: nowrap;
  flex-shrink: 0;
}
.quad-badge--forcas {
  background: var(--successBg);
  color: var(--success);
}
.quad-badge--oportunidades {
  background: #eaf1f8;
  color: #3d6fa8;
}
.quad-badge--fraquezas {
  background: var(--warnBg);
  color: var(--warn);
}
.quad-badge--ameacas {
  background: var(--lowBg);
  color: var(--low);
}
.quad-badge--watch {
  background: var(--k8);
  color: var(--k4);
}
.tows-badge {
  background: var(--wh);
  border: 1px solid var(--beige-bd);
  color: var(--gold2);
}
.proj-badge {
  background: rgba(255, 255, 255, 0.16);
  color: var(--wh);
}

.answer-note,
.counterparts {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  margin: 4px 0 6px 8px;
  font-size: 13px;
  color: var(--k3);
}
.answer-label {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--k5);
}
.counterpart {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  background: var(--k8);
  color: var(--k3);
}

.link-panel {
  margin: 6px 0 10px 8px;
  padding: 10px;
  border: 1px dashed var(--goldbd);
  border-radius: 6px;
  background: var(--k9);
}
.panel-label {
  margin: 10px 0 6px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--k5);
}
.panel-empty {
  margin: 0;
  font-size: 13px;
  color: var(--k4);
}
.panel-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-height: 220px;
  overflow-y: auto;
}
.panel-item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 6px 8px;
  border: 1px solid var(--bd);
  border-radius: 6px;
  background: var(--wh);
  font-size: 13px;
  text-align: left;
  color: var(--k0);
}
.panel-item:hover:not(:disabled) {
  border-color: var(--goldbd);
}
.panel-item.is-linked {
  border-color: var(--success);
  color: var(--success);
}
.panel-check {
  width: 16px;
  flex-shrink: 0;
  font-weight: 700;
}

.unlinked-toggle {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 0;
  border: none;
  background: transparent;
  text-align: left;
}
.sec-title {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--k5);
}
.unlinked-body {
  margin-top: 10px;
}
.plain-list {
  list-style: none;
  margin: 0 0 10px;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 13px;
  color: var(--k3);
}
.plain-list li {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}
.link {
  color: var(--k0);
  font-weight: 600;
}
.link:hover {
  text-decoration: underline;
}

@media (min-width: 760px) {
  .wrap {
    padding: 22px 20px 64px;
  }
  .card {
    padding: 20px;
  }
  .kpi-grid {
    grid-template-columns: repeat(4, 1fr);
  }
  .source-main {
    flex-direction: row;
    align-items: flex-end;
    justify-content: space-between;
  }
  .source-field {
    min-width: 320px;
  }
  .branch {
    margin-left: 14px;
    padding-left: 18px;
  }
  .tree-card {
    padding: 20px;
  }
}
</style>
