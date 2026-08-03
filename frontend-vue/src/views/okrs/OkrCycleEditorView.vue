<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import {
  getOkrCycle,
  updateOkrCycle,
  activateOkrCycle,
  archiveOkrCycle,
  type OkrCycle,
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

const loading = ref(true)
const error = ref<string | null>(null)
const saveState = ref<'idle' | 'saving' | 'saved' | 'error'>('idle')
const saveError = ref<string | null>(null)
const cycle = ref<OkrCycle | null>(null)
let saving = false
let pendingSave = false

const form = ref<{
  nome: string
  tipo: OkrCycleTipo
  ano: number
  trimestre: number | null
  objectives: Objective[]
}>({
  nome: '',
  tipo: 'trimestre',
  ano: new Date().getFullYear(),
  trimestre: null,
  objectives: [],
})

function applyCycle(c: OkrCycle) {
  cycle.value = c
  form.value = {
    nome: c.nome || '',
    tipo: c.tipo,
    ano: c.ano,
    trimestre: c.trimestre,
    objectives: c.objectives.map((o) => ({
      ...o,
      key_results: o.key_results.map((kr) => ({ ...kr })),
    })),
  }
}

async function persist() {
  if (!cycleId.value) return
  if (saving) {
    pendingSave = true
    return
  }
  saving = true
  saveState.value = 'saving'
  saveError.value = null
  try {
    const updated = await updateOkrCycle(cycleId.value, {
      nome: form.value.nome,
      tipo: form.value.tipo,
      ano: form.value.ano,
      trimestre: form.value.trimestre,
      objectives: form.value.objectives,
    })
    applyCycle(updated)
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

/** Progresso do KR calculado no cliente para feedback instantâneo — mesma fórmula do backend
 * (a direção só serve como rótulo; o cálculo se auto-inverte pelo sinal de target-baseline). */
function krProgress(kr: { baseline: number; current: number; target: number }): number {
  const denom = kr.target - kr.baseline
  const raw = denom === 0 ? 100 : ((kr.current - kr.baseline) / denom) * 100
  return Math.max(0, Math.min(100, raw))
}

function addObjective() {
  form.value.objectives.push({
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
  form.value.objectives.splice(idx, 1)
  void persist()
}

function onObjectiveFieldBlur() {
  void persist()
}

function addKr(obj: Objective) {
  obj.key_results.push({
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

function removeKr(obj: Objective, idx: number) {
  obj.key_results.splice(idx, 1)
  void persist()
}

function onKrFieldBlur() {
  void persist()
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

function selectedInitiatives(obj: Objective) {
  const doc = swot.value
  if (!doc) return []
  const chosen = new Set(obj.tows_ids || [])
  return TOWS_GROUPS.flatMap((group) =>
    (doc[group.field] || [])
      .filter((initiative) => initiative.id && chosen.has(initiative.id))
      .map((initiative) => ({ ...initiative, groupLabel: group.label }))
  )
}

function isTowsSelected(obj: Objective, initiativeId?: string): boolean {
  return !!initiativeId && (obj.tows_ids || []).includes(initiativeId)
}

async function toggleTows(obj: Objective, initiativeId?: string) {
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
  await persist()
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
    applyCycle(await activateOkrCycle(cycleId.value))
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
    applyCycle(await archiveOkrCycle(cycleId.value))
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
  try {
    applyCycle(await getOkrCycle(cycleId.value))
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
</script>

<template>
  <div class="page">
    <div class="toolbar">
      <RouterLink to="/okrs" class="back">← OKR</RouterLink>
      <div class="save-status">
        <span v-if="saveState === 'saving'">Salvando…</span>
        <span v-else-if="saveState === 'saved'" class="ok">Salvo</span>
        <span v-else-if="saveState === 'error'" class="err">{{ saveError || 'Erro ao salvar' }}</span>
        <span v-else class="muted">Salva ao sair do campo</span>
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
            @blur="persist"
          />
          <span class="status-badge" :data-status="cycle.status">{{ STATUS_LABEL[cycle.status] }}</span>
        </div>
        <div class="head-row head-meta">
          <label class="head-field">
            <span>Tipo</span>
            <select v-model="form.tipo" @change="persist">
              <option value="trimestre">Trimestre</option>
              <option value="ano">Ano</option>
            </select>
          </label>
          <label class="head-field">
            <span>Ano</span>
            <input v-model.number="form.ano" type="number" min="2020" max="2100" @blur="persist" />
          </label>
          <label v-if="form.tipo === 'trimestre'" class="head-field">
            <span>Trimestre</span>
            <select v-model.number="form.trimestre" @change="persist">
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

      <section v-for="(obj, objIdx) in form.objectives" :key="objIdx" class="card objective-card">
        <div class="objective-head">
          <input
            v-model="obj.titulo"
            class="objective-titulo"
            placeholder="Título do objetivo"
            maxlength="300"
            @blur="onObjectiveFieldBlur"
          />
          <button type="button" class="btn-remove" title="Remover objetivo" @click="removeObjective(objIdx)">×</button>
        </div>
        <div class="objective-fields">
          <textarea
            v-model="obj.descricao"
            class="objective-descricao"
            rows="2"
            maxlength="2000"
            placeholder="Descrição (opcional)"
            @blur="onObjectiveFieldBlur"
          />
          <div class="objective-meta-row">
            <input v-model="obj.dono" placeholder="Dono" maxlength="200" @blur="onObjectiveFieldBlur" />
            <input v-model="obj.pilar" placeholder="Pilar (opcional)" maxlength="40" @blur="onObjectiveFieldBlur" />
          </div>
        </div>

        <p v-if="!obj.titulo.trim()" class="obj-hint">
          Digite o título do objetivo para habilitar os Key Results e a origem estratégica (TOWS).
        </p>

        <template v-else>
          <section class="origin">
            <button
              type="button"
              class="origin-head"
              :aria-expanded="!!originOpen[objIdx]"
              @click="originOpen[objIdx] = !originOpen[objIdx]"
            >
              <span class="origin-title">Origem estratégica · TOWS</span>
              <span v-if="(obj.tows_ids || []).length" class="origin-count">
                {{ (obj.tows_ids || []).length }} iniciativa(s)
              </span>
              <span v-else class="origin-count muted">nenhuma iniciativa vinculada</span>
              <span class="origin-caret" aria-hidden="true">{{ originOpen[objIdx] ? '−' : '+' }}</span>
            </button>

            <div v-if="!originOpen[objIdx] && selectedInitiatives(obj).length" class="origin-chips">
              <span v-for="init in selectedInitiatives(obj)" :key="init.id" class="origin-chip">
                <b>{{ init.groupLabel }}</b>{{ init.acao }}
              </span>
            </div>

            <div v-if="originOpen[objIdx]" class="origin-body">
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
            <div v-for="(kr, krIdx) in obj.key_results" :key="krIdx" class="kr-row">
              <input
                v-model="kr.titulo"
                class="kr-titulo"
                placeholder="Resultado-chave"
                maxlength="300"
                @blur="onKrFieldBlur"
              />
              <div class="kr-fields">
                <input v-model="kr.unidade" class="kr-unidade" placeholder="Unidade" maxlength="40" @blur="onKrFieldBlur" />
                <label class="kr-num">
                  <span>Base</span>
                  <input v-model.number="kr.baseline" type="number" step="any" @blur="onKrFieldBlur" />
                </label>
                <label class="kr-num">
                  <span>Atual</span>
                  <input v-model.number="kr.current" type="number" step="any" @blur="onKrFieldBlur" />
                </label>
                <label class="kr-num">
                  <span>Meta</span>
                  <input v-model.number="kr.target" type="number" step="any" @blur="onKrFieldBlur" />
                </label>
                <select v-model="kr.direction" class="kr-direction" @change="onKrFieldBlur">
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
            <button type="button" class="btn-add-kr" @click="addKr(obj)">+ Resultado-chave</button>
          </div>
        </template>
      </section>

      <button type="button" class="btn-add-objective" @click="addObjective">+ Objetivo</button>
    </template>
  </div>
</template>

<style scoped>
.page {
  max-width: 860px;
  margin: 0 auto;
  padding: 20px 20px 60px;
}
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
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
  font-size: 12px;
  color: var(--k5);
}
.save-status .ok {
  color: #2f6e4a;
}
.save-status .err {
  color: #8f2b2b;
}
.card {
  background: var(--wh);
  border: 1px solid var(--bd);
  border-radius: 12px;
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
  border-radius: 999px;
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
  border-radius: 6px;
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
  border-radius: 6px;
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
.objective-head {
  display: flex;
  align-items: center;
  gap: 8px;
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
  border-radius: 6px;
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
  border-radius: 6px;
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
  border-radius: 8px;
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
  border-radius: 999px;
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
  border-radius: 6px;
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
  border-radius: 6px;
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
  border-radius: 8px;
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.kr-titulo {
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
  border-radius: 6px;
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
  border-radius: 6px;
  padding: 6px 8px;
  font-size: 12px;
}
.kr-direction {
  border: 1px solid var(--bd);
  border-radius: 6px;
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
  border-radius: 999px;
  overflow: hidden;
  margin-top: 2px;
}
.progress-fill {
  height: 100%;
  background: var(--gold, #c48a26);
  border-radius: 999px;
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
  border-radius: 6px;
  padding: 6px 12px;
  font-size: 12px;
  color: var(--k5);
  cursor: pointer;
}
.btn-add-kr:hover {
  color: var(--k0);
  border-color: var(--k0);
}
.btn-add-objective {
  width: 100%;
  border: 1px dashed var(--bd);
  background: transparent;
  border-radius: 8px;
  padding: 12px;
  font-size: 14px;
  color: var(--k5);
  cursor: pointer;
}
.btn-add-objective:hover {
  color: var(--k0);
  border-color: var(--k0);
}
</style>
