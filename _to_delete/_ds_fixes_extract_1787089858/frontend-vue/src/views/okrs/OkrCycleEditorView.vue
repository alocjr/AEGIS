<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { RouterLink, onBeforeRouteLeave, useRoute, useRouter } from 'vue-router'
import {
  getOkrCycle,
  updateOkrCycle,
  activateOkrCycle,
  archiveOkrCycle,
  type KeyResult,
  type OkrCycle,
  type OkrCyclePayload,
  type OkrCycleTipo,
  type Objective,
} from '@/api/okrs'
import {
  getSwotAnalysisById,
  listSwotAnalyses,
  type SwotAnalysis,
  type SwotAnalysisSummary,
  type SwotInitiative,
  type SwotTowsField,
} from '@/api/swotAnalysis'

const route = useRoute()
const router = useRouter()
const cycleId = computed(() => String(route.params.id || ''))

const MAX_OBJECTIVES = 20
const MAX_KRS = 20
/** Espera de digitação antes de gravar: longa o bastante para não salvar no meio de uma frase. */
const AUTOSAVE_DELAY_MS = 1200
const DRAFT_HINT = 'Salvo como rascunho — entra nos contadores e no Mapa Estratégico quando tiver um título.'

const loading = ref(true)
const error = ref<string | null>(null)
const saveState = ref<'saving' | 'saved' | 'error'>('saved')
const saveError = ref<string | null>(null)
const savedAt = ref<Date | null>(null)
const cycle = ref<OkrCycle | null>(null)

/** Identidade local estável por linha: `id` só existe depois do primeiro save, e os índices
 * mudam de lugar quando um item é removido — usar `_uid` como :key evita o Vue reciclar
 * o input de outra linha (e roubar o foco) durante a edição. */
let uidSeq = 0
type KrRow = KeyResult & { _uid: number }
type ObjRow = Omit<Objective, 'key_results'> & { _uid: number; key_results: KrRow[] }

const form = ref<{
  nome: string
  tipo: OkrCycleTipo
  ano: number
  trimestre: number | null
  objectives: ObjRow[]
}>({
  nome: '',
  tipo: 'trimestre',
  ano: new Date().getFullYear(),
  trimestre: null,
  objectives: [],
})

/** Contadores de geração: `editGen` avança a cada edição, `savedGen` guarda a geração que o
 * servidor já confirmou. Enquanto diferem, existe trabalho não gravado. */
const editGen = ref(0)
const savedGen = ref(0)
const dirty = computed(() => editGen.value !== savedGen.value)

/** Ligado enquanto o código (não o usuário) mexe no form, para não contar como edição. */
let applyingRemote = false
let autosaveTimer: number | null = null
let inFlight: Promise<void> | null = null

watch(
  form,
  () => {
    if (applyingRemote || loading.value) return
    editGen.value += 1
    scheduleSave()
  },
  { deep: true, flush: 'sync' }
)

function withRemoteChanges(fn: () => void) {
  applyingRemote = true
  try {
    fn()
  } finally {
    applyingRemote = false
  }
}

/** Metadados do ciclo (status, contadores) — nunca sobrescreve o que está sendo editado. */
function applyCycleMeta(c: OkrCycle) {
  cycle.value = c
}

function loadForm(c: OkrCycle) {
  withRemoteChanges(() => {
    form.value = {
      nome: c.nome || '',
      tipo: c.tipo,
      ano: c.ano,
      trimestre: c.trimestre,
      objectives: (c.objectives || []).map((o) => ({
        ...o,
        _uid: ++uidSeq,
        key_results: (o.key_results || []).map((kr) => ({ ...kr, _uid: ++uidSeq })),
      })),
    }
  })
  editGen.value = 0
  savedGen.value = 0
}

/** Campo numérico vazio vale 0 no payload: o backend recusa `""` com 422 e travaria o save
 * inteiro enquanto o usuário estivesse com a Base/Meta em branco. */
function toNum(value: unknown): number {
  const n = typeof value === 'number' ? value : Number(value)
  return Number.isFinite(n) ? n : 0
}

/** Ano apagado no meio da digitação (ou fora de 2020-2100) é recusado com 422 e travaria toda
 * a gravação — mantém o último ano válido até o usuário terminar de digitar. */
function safeAno(): number {
  const n = toNum(form.value.ano)
  if (n >= 2020 && n <= 2100) return n
  return cycle.value?.ano ?? new Date().getFullYear()
}

type SentRow = { uid: number; krUids: number[] }

/** Monta o PUT com tudo que está na tela — inclusive rascunho sem título, que o backend
 * guarda e mantém fora dos contadores — e devolve o mapa de linhas enviadas, para reatribuir
 * os ids gerados sem recarregar a tela. A resposta vem na mesma ordem, item a item. */
function buildPayload(): { body: OkrCyclePayload; sent: SentRow[] } {
  const objectives: Objective[] = []
  const sent: SentRow[] = []
  for (const obj of form.value.objectives) {
    if (objectives.length >= MAX_OBJECTIVES) break
    const krs: KeyResult[] = []
    const krUids: number[] = []
    for (const kr of obj.key_results) {
      if (krs.length >= MAX_KRS) break
      krs.push({
        id: kr.id,
        titulo: kr.titulo,
        descricao: kr.descricao,
        unidade: kr.unidade,
        baseline: toNum(kr.baseline),
        current: toNum(kr.current),
        target: toNum(kr.target),
        direction: kr.direction,
        dono: kr.dono,
      })
      krUids.push(kr._uid)
    }
    objectives.push({
      id: obj.id,
      titulo: obj.titulo,
      descricao: obj.descricao,
      dono: obj.dono,
      pilar: obj.pilar,
      swot_id: obj.swot_id ?? null,
      swot_item_ids: [...(obj.swot_item_ids || [])],
      tows_ids: [...(obj.tows_ids || [])],
      key_results: krs,
    })
    sent.push({ uid: obj._uid, krUids })
  }
  return {
    body: {
      nome: form.value.nome,
      tipo: form.value.tipo,
      ano: safeAno(),
      trimestre: form.value.tipo === 'trimestre' ? form.value.trimestre : null,
      objectives,
    },
    sent,
  }
}

/** Copia só os ids que o servidor gerou; o texto na tela é a fonte da verdade enquanto edita. */
function reconcileIds(updated: OkrCycle, sent: SentRow[]) {
  const objByUid = new Map(form.value.objectives.map((o) => [o._uid, o]))
  withRemoteChanges(() => {
    ;(updated.objectives || []).forEach((node, idx) => {
      const row = sent[idx]
      const local = row ? objByUid.get(row.uid) : undefined
      if (!row || !local) return
      local.id = node.id
      const krByUid = new Map(local.key_results.map((kr) => [kr._uid, kr]))
      ;(node.key_results || []).forEach((krNode, krIdx) => {
        const uid = row.krUids[krIdx]
        const localKr = uid === undefined ? undefined : krByUid.get(uid)
        if (localKr) localKr.id = krNode.id
      })
    })
  })
}

function clearAutosaveTimer() {
  if (autosaveTimer !== null) {
    window.clearTimeout(autosaveTimer)
    autosaveTimer = null
  }
}

function scheduleSave() {
  clearAutosaveTimer()
  autosaveTimer = window.setTimeout(() => {
    autosaveTimer = null
    void runSaves()
  }, AUTOSAVE_DELAY_MS)
}

async function putOnce(): Promise<boolean> {
  const gen = editGen.value
  const { body, sent } = buildPayload()
  try {
    const updated = await updateOkrCycle(cycleId.value, body)
    reconcileIds(updated, sent)
    applyCycleMeta(updated)
    savedGen.value = gen
    savedAt.value = new Date()
    return true
  } catch (e) {
    saveError.value = e instanceof Error ? e.message : 'Erro ao salvar.'
    return false
  }
}

/** Grava em série até a tela estar limpa; edições feitas durante o request entram na volta. */
function runSaves(): Promise<void> {
  if (inFlight) return inFlight
  if (!cycleId.value || loading.value || !dirty.value) return Promise.resolve()
  inFlight = (async () => {
    saveState.value = 'saving'
    saveError.value = null
    try {
      while (dirty.value) {
        if (!(await putOnce())) {
          saveState.value = 'error'
          return
        }
      }
      saveState.value = 'saved'
    } finally {
      inFlight = null
    }
  })()
  return inFlight
}

/** Grava agora (botão, atalho, ações estruturais) sem esperar o debounce. */
function saveNow(): Promise<void> {
  clearAutosaveTimer()
  return runSaves()
}

/** Espera a fila esvaziar — usada antes de sair da página ou mudar o status do ciclo. */
async function flushSaves(): Promise<void> {
  clearAutosaveTimer()
  if (inFlight) await inFlight
  if (dirty.value) await runSaves()
}

const savedAtLabel = computed(() =>
  savedAt.value
    ? savedAt.value.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
    : ''
)

/** Progresso do KR calculado no cliente para feedback instantâneo — mesma fórmula do backend
 * (a direção só serve como rótulo; o cálculo se auto-inverte pelo sinal de target-baseline). */
function krProgress(kr: { baseline: number; current: number; target: number }): number {
  const denom = toNum(kr.target) - toNum(kr.baseline)
  const raw = denom === 0 ? 100 : ((toNum(kr.current) - toNum(kr.baseline)) / denom) * 100
  return Math.max(0, Math.min(100, raw))
}

function isDraftObjective(obj: ObjRow): boolean {
  return !obj.titulo.trim()
}

function addObjective() {
  if (form.value.objectives.length >= MAX_OBJECTIVES) return
  form.value.objectives.push({
    _uid: ++uidSeq,
    titulo: '',
    descricao: '',
    dono: '',
    pilar: '',
    swot_id: null,
    swot_item_ids: [],
    tows_ids: [],
    key_results: [],
  })
}

function removeObjective(idx: number) {
  const obj = form.value.objectives[idx]
  if (!obj) return
  delete originOpen.value[obj._uid]
  form.value.objectives.splice(idx, 1)
  void saveNow()
}

function addKr(obj: ObjRow) {
  if (obj.key_results.length >= MAX_KRS) return
  obj.key_results.push({
    _uid: ++uidSeq,
    titulo: '',
    descricao: '',
    unidade: '',
    baseline: 0,
    current: 0,
    target: 100,
    direction: 'increase',
    dono: '',
  })
}

function removeKr(obj: ObjRow, idx: number) {
  obj.key_results.splice(idx, 1)
  void saveNow()
}

/** Ciclo trimestral sem trimestre é rejeitado com 400 — assume o trimestre corrente. */
function onTipoChange() {
  if (form.value.tipo === 'trimestre' && !form.value.trimestre) {
    form.value.trimestre = Math.floor(new Date().getMonth() / 3) + 1
  }
}

function onSaveShortcut(ev: KeyboardEvent) {
  if (!(ev.metaKey || ev.ctrlKey) || ev.key.toLowerCase() !== 's') return
  ev.preventDefault()
  void saveNow()
}

function onBeforeUnload(ev: BeforeUnloadEvent) {
  if (!dirty.value && !inFlight) return
  ev.preventDefault()
  ev.returnValue = ''
}

/** Origem estratégica: iniciativas TOWS da SWOT vinculadas a cada Objective. */
const TOWS_GROUPS: { field: SwotTowsField; label: string; hint: string }[] = [
  { field: 'tows_fo', label: 'F × O · Ofensiva', hint: 'Forças que capturam oportunidades' },
  { field: 'tows_fa', label: 'F × A · Defesa', hint: 'Forças que neutralizam ameaças' },
  { field: 'tows_fxo', label: 'f × O · Reforço', hint: 'Fraquezas que travam oportunidades' },
  { field: 'tows_fxa', label: 'f × A · Sobrevivência', hint: 'Vulnerabilidade encontra risco' },
]

const swotList = ref<SwotAnalysisSummary[]>([])
const swot = ref<SwotAnalysis | null>(null)
const swotLoading = ref(false)
const swotError = ref<string | null>(null)
const originOpen = ref<Record<number, boolean>>({})

const swotItemsById = computed(() => {
  const map = new Map<string, { texto: string }>()
  const doc = swot.value
  if (!doc) return map
  for (const field of ['forcas', 'fraquezas', 'oportunidades', 'ameacas'] as const) {
    for (const item of doc[field] || []) {
      map.set(item.id, { texto: item.texto })
    }
  }
  return map
})

function crossingLabel(initiative: SwotInitiative): string {
  const texts = [...(initiative.itens_internos || []), ...(initiative.itens_externos || [])]
    .map((id) => swotItemsById.value.get(id)?.texto)
    .filter((text): text is string => !!text)
  return texts.join(' × ')
}

function selectedInitiatives(obj: ObjRow) {
  const doc = swot.value
  if (!doc) return []
  const chosen = new Set(obj.tows_ids || [])
  return TOWS_GROUPS.flatMap((group) =>
    (doc[group.field] || [])
      .filter((initiative) => initiative.id && chosen.has(initiative.id))
      .map((initiative) => ({ ...initiative, groupLabel: group.label }))
  )
}

function isTowsSelected(obj: ObjRow, initiativeId?: string): boolean {
  return !!initiativeId && (obj.tows_ids || []).includes(initiativeId)
}

async function toggleTows(obj: ObjRow, initiativeId?: string) {
  if (!initiativeId || !swot.value) return
  const chosen = new Set(obj.tows_ids || [])
  if (chosen.has(initiativeId)) {
    chosen.delete(initiativeId)
  } else {
    if (chosen.size >= 20) {
      swotError.value = 'Máximo de 20 iniciativas por objetivo.'
      return
    }
    chosen.add(initiativeId)
  }
  swotError.value = null
  obj.tows_ids = [...chosen]
  obj.swot_id = obj.tows_ids.length ? swot.value.id : null
  await saveNow()
}

async function loadSwotDoc(id: string) {
  swotLoading.value = true
  try {
    swot.value = await getSwotAnalysisById(id)
  } catch (e) {
    swot.value = null
    swotError.value = e instanceof Error ? e.message : 'Falha ao carregar a SWOT.'
  } finally {
    swotLoading.value = false
  }
}

async function loadSwotList() {
  try {
    const list = await listSwotAnalyses()
    swotList.value = list.items
    const first = list.items[0]
    if (first) await loadSwotDoc(first.id)
  } catch (e) {
    swotError.value = e instanceof Error ? e.message : 'Falha ao listar as SWOTs.'
  }
}

async function onSelectSwot(event: Event) {
  const nextId = (event.target as HTMLSelectElement).value
  if (!nextId || nextId === swot.value?.id) return
  await loadSwotDoc(nextId)
}

const activating = ref(false)
const archiving = ref(false)
const lifecycleError = ref<string | null>(null)

async function onActivate() {
  activating.value = true
  lifecycleError.value = null
  try {
    await flushSaves()
    applyCycleMeta(await activateOkrCycle(cycleId.value))
  } catch (e) {
    lifecycleError.value = e instanceof Error ? e.message : 'Erro ao ativar ciclo.'
  } finally {
    activating.value = false
  }
}

async function onArchive() {
  archiving.value = true
  lifecycleError.value = null
  try {
    await flushSaves()
    applyCycleMeta(await archiveOkrCycle(cycleId.value))
  } catch (e) {
    lifecycleError.value = e instanceof Error ? e.message : 'Erro ao arquivar ciclo.'
  } finally {
    archiving.value = false
  }
}

const STATUS_LABEL: Record<string, string> = {
  planejamento: 'Em planejamento',
  ativo: 'Ativo',
  encerrado: 'Encerrado',
}

onMounted(async () => {
  window.addEventListener('keydown', onSaveShortcut)
  window.addEventListener('beforeunload', onBeforeUnload)
  try {
    const c = await getOkrCycle(cycleId.value)
    applyCycleMeta(c)
    loadForm(c)
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Erro ao carregar ciclo.'
    if (String(error.value).includes('não encontrado')) {
      setTimeout(() => router.push('/okrs'), 1500)
    }
  } finally {
    loading.value = false
  }
  void loadSwotList()
})

onBeforeRouteLeave(async () => {
  await flushSaves()
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onSaveShortcut)
  window.removeEventListener('beforeunload', onBeforeUnload)
  clearAutosaveTimer()
  if (dirty.value) void runSaves()
})
</script>

<template>
  <div class="page">
    <div class="toolbar">
      <RouterLink to="/okrs" class="back">← OKR</RouterLink>
      <div class="save-status">
        <span v-if="saveState === 'error'" class="err">{{ saveError || 'Erro ao salvar' }}</span>
        <span v-else-if="saveState === 'saving'">Salvando…</span>
        <span v-else-if="dirty" class="pending">Alterações não salvas</span>
        <span v-else-if="savedAtLabel" class="ok">Salvo às {{ savedAtLabel }}</span>
        <span v-else class="muted">Salva automaticamente enquanto você escreve</span>
        <button
          v-if="dirty || saveState === 'error'"
          type="button"
          class="btn-save"
          title="Salvar agora (⌘S / Ctrl+S)"
          :disabled="saveState === 'saving'"
          @click="saveNow()"
        >
          {{ saveState === 'error' ? 'Tentar novamente' : 'Salvar agora' }}
        </button>
      </div>
    </div>

    <div v-if="loading" class="card">Carregando...</div>
    <div v-else-if="error" class="card error-msg">{{ error }}</div>

    <template v-else-if="cycle">
      <header class="head card">
        <div class="head-row">
          <input
            v-model="form.nome"
            class="head-nome"
            placeholder="Nome do ciclo (opcional)"
            maxlength="120"
          />
          <span class="status-badge" :data-status="cycle.status">{{ STATUS_LABEL[cycle.status] }}</span>
        </div>
        <div class="head-row head-meta">
          <label class="head-field">
            <span>Tipo</span>
            <select v-model="form.tipo" @change="onTipoChange">
              <option value="trimestre">Trimestre</option>
              <option value="ano">Ano</option>
            </select>
          </label>
          <label class="head-field">
            <span>Ano</span>
            <input v-model.number="form.ano" type="number" min="2020" max="2100" />
          </label>
          <label v-if="form.tipo === 'trimestre'" class="head-field">
            <span>Trimestre</span>
            <select v-model.number="form.trimestre">
              <option :value="1">Q1</option>
              <option :value="2">Q2</option>
              <option :value="3">Q3</option>
              <option :value="4">Q4</option>
            </select>
          </label>
          <div class="head-actions">
            <button
              v-if="cycle.status !== 'ativo'"
              type="button"
              class="btn-activate"
              :disabled="activating"
              @click="onActivate"
            >
              {{ activating ? 'Ativando…' : 'Ativar ciclo' }}
            </button>
            <button
              v-if="cycle.status !== 'encerrado'"
              type="button"
              class="btn-archive"
              :disabled="archiving"
              @click="onArchive"
            >
              {{ archiving ? 'Arquivando…' : 'Arquivar' }}
            </button>
          </div>
        </div>
        <p v-if="lifecycleError" class="error-msg">{{ lifecycleError }}</p>
        <p v-if="cycle.status === 'ativo'" class="head-hint">
          Ciclo ativo — Objectives e Key Results aparecem no Mapa Estratégico.
        </p>
      </header>

      <section
        v-for="(obj, objIdx) in form.objectives"
        :key="obj._uid"
        class="card objective-card"
        :class="{ draft: isDraftObjective(obj) }"
      >
        <div class="objective-head">
          <input
            v-model="obj.titulo"
            class="objective-titulo"
            placeholder="Título do objetivo"
            maxlength="300"
          />
          <span v-if="isDraftObjective(obj)" class="draft-badge" :title="DRAFT_HINT">Rascunho</span>
          <button type="button" class="btn-remove" title="Remover objetivo" @click="removeObjective(objIdx)">×</button>
        </div>
        <div class="objective-fields">
          <textarea
            v-model="obj.descricao"
            class="objective-descricao"
            rows="2"
            maxlength="2000"
            placeholder="Descrição (opcional)"
          />
          <div class="objective-meta-row">
            <input v-model="obj.dono" placeholder="Dono" maxlength="200" />
            <input v-model="obj.pilar" placeholder="Pilar (opcional)" maxlength="40" />
          </div>
        </div>

        <p v-if="isDraftObjective(obj)" class="obj-hint">
          Rascunho: já está salvo, mas só entra nos contadores e no Mapa Estratégico depois de
          ganhar um título.
        </p>

        <section class="origin">
          <button
            type="button"
            class="origin-head"
            :aria-expanded="!!originOpen[obj._uid]"
            @click="originOpen[obj._uid] = !originOpen[obj._uid]"
          >
            <span class="origin-title">Origem estratégica · TOWS</span>
            <span v-if="(obj.tows_ids || []).length" class="origin-count">
              {{ (obj.tows_ids || []).length }} iniciativa(s)
            </span>
            <span v-else class="origin-count muted">nenhuma iniciativa vinculada</span>
            <span class="origin-caret" aria-hidden="true">{{ originOpen[obj._uid] ? '−' : '+' }}</span>
          </button>

          <div v-if="!originOpen[obj._uid] && selectedInitiatives(obj).length" class="origin-chips">
            <span v-for="init in selectedInitiatives(obj)" :key="init.id" class="origin-chip">
              <b>{{ init.groupLabel }}</b>{{ init.acao }}
            </span>
          </div>

          <div v-if="originOpen[obj._uid]" class="origin-body">
            <div v-if="swotError" class="origin-err">{{ swotError }}</div>
            <p v-if="swotLoading" class="origin-none">Carregando estratégias…</p>
            <p v-else-if="!swotList.length" class="origin-none">
              Nenhuma SWOT criada ainda.
              <RouterLink to="/swot" class="origin-link">Abrir SWOT de IA</RouterLink>
            </p>
            <template v-else-if="swot">
              <label v-if="swotList.length > 1" class="origin-select">
                <span>SWOT de origem</span>
                <select :value="swot.id" @change="onSelectSwot">
                  <option v-for="s in swotList" :key="s.id" :value="s.id">
                    {{ s.veredito_titulo || 'SWOT sem veredito' }} · {{ s.tows_count }} estratégia(s)
                  </option>
                </select>
              </label>
              <div class="origin-groups">
                <div v-for="group in TOWS_GROUPS" :key="group.field" class="origin-group">
                  <div class="origin-group-head">
                    <b>{{ group.label }}</b>
                    <span>{{ group.hint }}</span>
                  </div>
                  <p v-if="!(swot[group.field] || []).length" class="origin-none">
                    Sem estratégias neste cruzamento.
                  </p>
                  <ul v-else class="origin-list">
                    <li v-for="(init, initIdx) in swot[group.field]" :key="init.id || initIdx">
                      <label class="origin-item" :class="{ active: isTowsSelected(obj, init.id) }">
                        <input
                          type="checkbox"
                          :checked="isTowsSelected(obj, init.id)"
                          :disabled="!init.id"
                          @change="toggleTows(obj, init.id)"
                        />
                        <span class="origin-item-body">
                          <span class="origin-acao">{{ init.acao || '—' }}</span>
                          <span v-if="crossingLabel(init)" class="origin-cross">{{ crossingLabel(init) }}</span>
                        </span>
                      </label>
                    </li>
                  </ul>
                </div>
              </div>
            </template>
          </div>
        </section>

        <div class="kr-list">
          <div
            v-for="(kr, krIdx) in obj.key_results"
            :key="kr._uid"
            class="kr-row"
            :class="{ draft: !kr.titulo.trim() }"
          >
            <div class="kr-head">
              <input
                v-model="kr.titulo"
                class="kr-titulo"
                placeholder="Resultado-chave (ex.: reduzir tempo de resposta de 8h para 5h)"
                maxlength="300"
              />
              <span v-if="!kr.titulo.trim()" class="draft-badge" :title="DRAFT_HINT">Rascunho</span>
            </div>
            <div class="kr-fields">
              <input v-model="kr.unidade" class="kr-unidade" placeholder="Unidade" maxlength="40" />
              <label class="kr-num">
                <span>Base</span>
                <input v-model.number="kr.baseline" type="number" step="any" />
              </label>
              <label class="kr-num">
                <span>Atual</span>
                <input v-model.number="kr.current" type="number" step="any" />
              </label>
              <label class="kr-num">
                <span>Meta</span>
                <input v-model.number="kr.target" type="number" step="any" />
              </label>
              <select v-model="kr.direction" class="kr-direction">
                <option value="increase">↑ Aumentar</option>
                <option value="decrease">↓ Reduzir</option>
              </select>
              <button type="button" class="btn-remove" title="Remover Key Result" @click="removeKr(obj, krIdx)">×</button>
            </div>
            <div class="progress-bar">
              <div class="progress-fill" :style="{ width: `${krProgress(kr)}%` }" />
              <span class="progress-label">{{ krProgress(kr).toFixed(0) }}%</span>
            </div>
          </div>
          <button
            type="button"
            class="btn-add-kr"
            :disabled="obj.key_results.length >= MAX_KRS"
            @click="addKr(obj)"
          >
            + Resultado-chave
          </button>
        </div>
      </section>

      <button
        type="button"
        class="btn-add-objective"
        :disabled="form.objectives.length >= MAX_OBJECTIVES"
        @click="addObjective"
      >
        + Objetivo
      </button>
    </template>
  </div>
</template>

<style scoped>
.page {
  max-width: var(--w-read);
  margin: 0 auto;
  padding: 20px 20px 60px;
}
.toolbar {
  position: sticky;
  top: var(--bar-h, 64px);
  z-index: 20;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 0;
  margin-bottom: 6px;
  background: var(--k9);
  border-bottom: 1px solid var(--bd);
}
.back {
  font-size: 13px;
  color: var(--k5);
  text-decoration: none;
}
.back:hover {
  color: var(--k0);
}
.save-status {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 12px;
  color: var(--k5);
}
.save-status .ok {
  color: #2f6e4a;
}
.save-status .err {
  color: #8f2b2b;
}
.save-status .pending {
  color: var(--warn);
}
.btn-save {
  font-size: 12px;
  padding: 5px 12px;
  border-radius: var(--r-sm);
  border: 1px solid var(--k0);
  background: var(--k0);
  color: var(--wh);
  cursor: pointer;
}
.btn-save:disabled {
  opacity: 0.6;
  cursor: wait;
}
.card {
  background: var(--wh);
  border: 1px solid var(--bd);
  border-radius: var(--r-lg);
  padding: 18px 20px;
  margin-bottom: 16px;
}
.error-msg {
  color: #8f2b2b;
}
.head-row {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
.head-row + .head-row {
  margin-top: 10px;
}
.head-nome {
  flex: 1;
  min-width: 200px;
  font-family: var(--serif);
  font-size: 22px;
  color: var(--k0);
  border: none;
  outline: none;
  background: transparent;
}
.status-badge {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  padding: 4px 10px;
  border-radius: var(--r-pill);
  border: 1px solid var(--bd);
  color: var(--k4);
  white-space: nowrap;
}
.status-badge[data-status='ativo'] {
  background: #e8f0e7;
  border-color: #bbd3b7;
  color: #2f6e4a;
}
.status-badge[data-status='encerrado'] {
  background: var(--k9);
  color: var(--k5);
}
.head-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
  color: var(--k5);
}
.head-field select,
.head-field input {
  padding: 6px 8px;
  border: 1px solid var(--bd);
  border-radius: var(--r-sm);
  font-size: 13px;
  color: var(--k0);
  min-width: 90px;
}
.head-actions {
  margin-left: auto;
  display: flex;
  gap: 8px;
}
.btn-activate,
.btn-archive {
  font-size: 13px;
  padding: 8px 14px;
  border-radius: var(--r-sm);
  cursor: pointer;
  border: 1px solid var(--bd);
  background: var(--wh);
  color: var(--k0);
}
.btn-activate {
  background: var(--k0);
  color: var(--wh);
  border-color: var(--k0);
}
.btn-activate:disabled,
.btn-archive:disabled {
  opacity: 0.6;
  cursor: wait;
}
.head-hint {
  margin-top: 10px;
  font-size: 12px;
  color: #2f6e4a;
}
.objective-card {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.objective-card.draft {
  border-style: dashed;
}
.objective-head {
  display: flex;
  align-items: center;
  gap: 8px;
}
.draft-badge {
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  padding: 3px 8px;
  border-radius: var(--r-pill);
  background: var(--warnBg);
  color: var(--warn);
  white-space: nowrap;
}
.objective-titulo {
  flex: 1;
  font-size: 16px;
  font-weight: 600;
  color: var(--k0);
  border: none;
  border-bottom: 1px solid transparent;
  outline: none;
  padding: 2px 0;
}
.objective-titulo:focus {
  border-bottom-color: var(--bd);
}
.btn-remove {
  border: none;
  background: transparent;
  color: var(--k5);
  font-size: 18px;
  line-height: 1;
  cursor: pointer;
  padding: 2px 6px;
}
.btn-remove:hover {
  color: #8f2b2b;
}
.objective-fields {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.objective-descricao {
  width: 100%;
  border: 1px solid var(--bd);
  border-radius: var(--r-sm);
  padding: 8px 10px;
  font-size: 13px;
  color: var(--k0);
  resize: vertical;
}
.objective-meta-row {
  display: flex;
  gap: 8px;
}
.objective-meta-row input {
  flex: 1;
  border: 1px solid var(--bd);
  border-radius: var(--r-sm);
  padding: 6px 10px;
  font-size: 13px;
  color: var(--k0);
}
.obj-hint {
  font-size: 12px;
  color: var(--k5);
  font-style: italic;
}
.origin {
  border: 1px solid var(--bd);
  border-radius: var(--r-md);
  overflow: hidden;
}
.origin-head {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  background: var(--k9);
  border: none;
  cursor: pointer;
  text-align: left;
  font-family: inherit;
}
.origin-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--k0);
}
.origin-count {
  font-size: 12px;
  color: var(--k5);
}
.origin-count.muted {
  color: var(--k5);
}
.origin-caret {
  margin-left: auto;
  font-size: 16px;
  color: var(--k5);
}
.origin-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 10px 12px;
}
.origin-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  background: var(--k9);
  border-radius: var(--r-pill);
  padding: 4px 10px;
  color: var(--k3);
}
.origin-chip b {
  color: var(--k5);
  font-weight: 600;
}
.origin-body {
  padding: 12px;
  border-top: 1px solid var(--bd);
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.origin-err {
  color: #8f2b2b;
  font-size: 12px;
}
.origin-none {
  font-size: 12px;
  color: var(--k5);
}
.origin-link {
  color: var(--k0);
}
.origin-select {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
  color: var(--k5);
}
.origin-select select {
  padding: 6px 8px;
  border: 1px solid var(--bd);
  border-radius: var(--r-sm);
}
.origin-groups {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.origin-group-head {
  display: flex;
  flex-direction: column;
  gap: 2px;
  margin-bottom: 4px;
}
.origin-group-head b {
  font-size: 12px;
  color: var(--k0);
}
.origin-group-head span {
  font-size: 11px;
  color: var(--k5);
}
.origin-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.origin-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 6px 8px;
  border-radius: var(--r-sm);
  cursor: pointer;
}
.origin-item.active {
  background: var(--golddim, #f3e7cc);
}
.origin-item-body {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.origin-acao {
  font-size: 12px;
  color: var(--k0);
}
.origin-cross {
  font-size: 11px;
  color: var(--k5);
}
.kr-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.kr-row {
  border: 1px solid var(--bd);
  border-radius: var(--r-md);
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.kr-row.draft {
  border-style: dashed;
}
.kr-head {
  display: flex;
  align-items: center;
  gap: 8px;
}
.kr-titulo {
  flex: 1;
  min-width: 0;
  border: none;
  outline: none;
  font-size: 14px;
  font-weight: 500;
  color: var(--k0);
}
.kr-fields {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: 8px;
}
.kr-unidade {
  width: 90px;
  border: 1px solid var(--bd);
  border-radius: var(--r-sm);
  padding: 6px 8px;
  font-size: 12px;
}
.kr-num {
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-size: 11px;
  color: var(--k5);
}
.kr-num input {
  width: 80px;
  border: 1px solid var(--bd);
  border-radius: var(--r-sm);
  padding: 6px 8px;
  font-size: 12px;
}
.kr-direction {
  border: 1px solid var(--bd);
  border-radius: var(--r-sm);
  padding: 6px 8px;
  font-size: 12px;
}
.kr-fields .btn-remove {
  margin-left: auto;
}
.progress-bar {
  position: relative;
  height: 8px;
  background: var(--k9);
  border-radius: var(--r-pill);
  overflow: hidden;
  margin-top: 2px;
}
.progress-fill {
  height: 100%;
  background: var(--gold, #c48a26);
  border-radius: var(--r-pill);
  transition: width 0.2s ease;
}
.progress-label {
  position: absolute;
  right: 0;
  top: -16px;
  font-size: 10px;
  color: var(--k5);
}
.btn-add-kr {
  align-self: flex-start;
  border: 1px dashed var(--bd);
  background: transparent;
  border-radius: var(--r-sm);
  padding: 6px 12px;
  font-size: 12px;
  color: var(--k5);
  cursor: pointer;
}
.btn-add-kr:hover:not(:disabled) {
  color: var(--k0);
  border-color: var(--k0);
}
.btn-add-kr:disabled,
.btn-add-objective:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.btn-add-objective {
  width: 100%;
  border: 1px dashed var(--bd);
  background: transparent;
  border-radius: var(--r-md);
  padding: 12px;
  font-size: 14px;
  color: var(--k5);
  cursor: pointer;
}
.btn-add-objective:hover:not(:disabled) {
  color: var(--k0);
  border-color: var(--k0);
}
</style>
