<script setup lang="ts">
import { ref, computed, onMounted, reactive } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import {
  getCanvasProject,
  updateCanvasProject,
  type CanvasProject,
  type CanvasProjectPayload,
  type CanvasListField,
  type CanvasQuadrant,
} from '@/api/canvasProjects'

const route = useRoute()
const router = useRouter()
const projectId = computed(() => String(route.params.id || ''))

const loading = ref(true)
const error = ref<string | null>(null)
const saveState = ref<'idle' | 'saving' | 'saved' | 'error'>('idle')
const saveError = ref<string | null>(null)
const project = ref<CanvasProject | null>(null)
let saving = false
let pendingSave = false

const drafts = reactive<Record<CanvasListField, string>>({
  contexto: '',
  dores: '',
  oportunidade: '',
  dados: '',
  valor: '',
  custo: '',
  riscos: '',
})

const form = ref({
  title: '',
  area_negocio: '',
  responsavel: '',
  data: '',
  objetivo_estrategico: '',
  contexto: [] as string[],
  dores: [] as string[],
  oportunidade: [] as string[],
  oportunidade_tipos: [] as string[],
  dados: [] as string[],
  valor: [] as string[],
  custo: [] as string[],
  riscos: [] as string[],
  score_valor: null as number | null,
  score_viabilidade: null as number | null,
  proximo_passo: '',
})

const typeOptions = ref<string[]>([
  'Automação',
  'Classificação/Previsão',
  'Extração/Busca',
  'Geração',
  'Copiloto',
  'Agente autônomo',
])

const quadrant = computed<CanvasQuadrant>(() => {
  const v = form.value.score_valor
  const f = form.value.score_viabilidade
  if (v == null || f == null) return null
  const highV = v >= 4
  const highF = f >= 4
  if (highV && highF) return 'ganho_rapido'
  if (highV && !highF) return 'aposta_estrategica'
  if (!highV && highF) return 'incremental'
  return 'evitar'
})

function asList(value: unknown): string[] {
  if (Array.isArray(value)) return value.map(String).map((s) => s.trim()).filter(Boolean)
  if (typeof value === 'string' && value.trim()) return [value.trim()]
  return []
}

function maskDate(raw: string): string {
  const digits = raw.replace(/\D/g, '').slice(0, 8)
  const parts: string[] = []
  if (digits.length > 0) parts.push(digits.slice(0, 2))
  if (digits.length > 2) parts.push(digits.slice(2, 4))
  if (digits.length > 4) parts.push(digits.slice(4, 8))
  return parts.join('/')
}

function onDateInput(ev: Event) {
  const input = ev.target as HTMLInputElement
  const masked = maskDate(input.value)
  form.value.data = masked
  input.value = masked
}

function applyProject(p: CanvasProject) {
  project.value = p
  form.value = {
    title: p.title || 'Novo projeto',
    area_negocio: p.area_negocio || '',
    responsavel: p.responsavel || '',
    data: maskDate(p.data || ''),
    objetivo_estrategico: p.objetivo_estrategico || '',
    contexto: asList(p.contexto),
    dores: asList(p.dores),
    oportunidade: asList(p.oportunidade),
    oportunidade_tipos: [...(p.oportunidade_tipos || [])],
    dados: asList(p.dados),
    valor: asList(p.valor),
    custo: asList(p.custo),
    riscos: asList(p.riscos),
    score_valor: p.score_valor,
    score_viabilidade: p.score_viabilidade,
    proximo_passo: p.proximo_passo || '',
  }
  if (p.opportunity_type_options?.length) {
    typeOptions.value = p.opportunity_type_options
  }
}

function addItem(field: CanvasListField) {
  const text = drafts[field].trim()
  if (!text) return
  if (form.value[field].length >= 40) return
  form.value[field] = [...form.value[field], text]
  drafts[field] = ''
  void persist()
}

function removeItem(field: CanvasListField, index: number) {
  form.value[field] = form.value[field].filter((_, i) => i !== index)
  void persist()
}

function onItemBlur(field: CanvasListField, index: number, ev: Event) {
  const input = ev.target as HTMLInputElement
  const next = input.value.trim()
  const list = [...form.value[field]]
  if (!next) {
    list.splice(index, 1)
  } else {
    list[index] = next
  }
  form.value[field] = list
  void persist()
}

function onDraftKeydown(field: CanvasListField, ev: KeyboardEvent) {
  if (ev.key === 'Enter') {
    ev.preventDefault()
    addItem(field)
  }
}

function toggleType(t: string) {
  const set = new Set(form.value.oportunidade_tipos)
  if (set.has(t)) set.delete(t)
  else set.add(t)
  form.value.oportunidade_tipos = [...set]
  void persist()
}

function setScore(field: 'score_valor' | 'score_viabilidade', n: number) {
  form.value[field] = form.value[field] === n ? null : n
  void persist()
}

async function persist() {
  if (!projectId.value) return
  if (saving) {
    pendingSave = true
    return
  }
  saving = true
  saveState.value = 'saving'
  saveError.value = null
  const payload: CanvasProjectPayload = { ...form.value }
  try {
    const updated = await updateCanvasProject(projectId.value, payload)
    applyProject(updated)
    saveState.value = 'saved'
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

onMounted(async () => {
  try {
    const p = await getCanvasProject(projectId.value)
    applyProject(p)
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Erro ao carregar projeto.'
    if (String(error.value).includes('nao encontrado') || String(error.value).includes('não encontrado')) {
      setTimeout(() => router.push('/projetos'), 1500)
    }
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="page">
    <div class="toolbar">
      <RouterLink to="/projetos" class="back">← Projetos</RouterLink>
      <div class="save-status">
        <span v-if="saveState === 'saving'">Salvando…</span>
        <span v-else-if="saveState === 'saved'" class="ok">Salvo</span>
        <span v-else-if="saveState === 'error'" class="err">{{ saveError || 'Erro ao salvar' }}</span>
        <span v-else class="muted">Salva ao sair do campo</span>
      </div>
    </div>

    <div v-if="loading" class="state">Carregando canvas…</div>
    <div v-else-if="error" class="state err">{{ error }}</div>

    <div v-else class="sheet">
      <header class="sheet-header">
        <div>
          <div class="brand">Valorian · Instrumento estratégico</div>
          <h1>
            Canvas de Oportunidades de IA
            <span>por área de negócio</span>
          </h1>
          <p class="subtitle">Um canvas por área. Preencha na ordem 01 → 08: da dor real à decisão de investir.</p>
          <label class="title-field">
            <span>Nome do projeto</span>
            <input v-model="form.title" type="text" maxlength="200" @blur="persist" />
          </label>
        </div>
        <div class="meta">
          <label>
            <span>Área de negócio</span>
            <input v-model="form.area_negocio" type="text" placeholder="Ex.: Comercial" maxlength="200" @blur="persist" />
          </label>
          <label>
            <span>Responsável</span>
            <input v-model="form.responsavel" type="text" placeholder="Nome" maxlength="200" @blur="persist" />
          </label>
          <label>
            <span>Data</span>
            <input
              :value="form.data"
              type="text"
              inputmode="numeric"
              placeholder="dd/mm/aaaa"
              maxlength="10"
              autocomplete="off"
              @input="onDateInput"
              @blur="persist"
            />
          </label>
          <label>
            <span>Objetivo estratégico da área</span>
            <input
              v-model="form.objetivo_estrategico"
              type="text"
              placeholder="O que essa área precisa entregar"
              maxlength="2000"
              @blur="persist"
            />
          </label>
        </div>
      </header>

      <div class="grid">
        <div class="cell c4 band-diag">
          <span class="num">01</span>
          <div class="cell-title">Contexto da área</div>
          <div class="hint">KPIs e processos-chave. Onde essa área cria ou destrói valor hoje?</div>
          <ul class="item-list">
            <li v-for="(item, idx) in form.contexto" :key="'c' + idx" class="item-row">
              <input
                :value="item"
                class="item-input"
                maxlength="500"
                @blur="onItemBlur('contexto', idx, $event)"
              />
              <button type="button" class="item-remove" title="Remover" @click="removeItem('contexto', idx)">×</button>
            </li>
          </ul>
          <div class="item-add">
            <input
              v-model="drafts.contexto"
              type="text"
              maxlength="500"
              placeholder="Adicionar item…"
              @keydown="onDraftKeydown('contexto', $event)"
            />
            <button type="button" @click="addItem('contexto')">+</button>
          </div>
        </div>
        <div class="cell c4 band-diag">
          <span class="num">02</span>
          <div class="cell-title">Dores &amp; gargalos</div>
          <div class="hint">Atrito, retrabalho, erro, custo, lentidão. <strong>Descreva a dor — não a solução.</strong></div>
          <ul class="item-list">
            <li v-for="(item, idx) in form.dores" :key="'d' + idx" class="item-row">
              <input
                :value="item"
                class="item-input"
                maxlength="500"
                @blur="onItemBlur('dores', idx, $event)"
              />
              <button type="button" class="item-remove" title="Remover" @click="removeItem('dores', idx)">×</button>
            </li>
          </ul>
          <div class="item-add">
            <input
              v-model="drafts.dores"
              type="text"
              maxlength="500"
              placeholder="Adicionar item…"
              @keydown="onDraftKeydown('dores', $event)"
            />
            <button type="button" @click="addItem('dores')">+</button>
          </div>
        </div>
        <div class="cell c4 band-diag cell-last">
          <span class="num">03</span>
          <div class="cell-title">Oportunidade de IA</div>
          <div class="hint">Em uma frase: o que a IA faria e qual dor do bloco 02 ela ataca.</div>
          <ul class="item-list">
            <li v-for="(item, idx) in form.oportunidade" :key="'o' + idx" class="item-row">
              <input
                :value="item"
                class="item-input"
                maxlength="500"
                @blur="onItemBlur('oportunidade', idx, $event)"
              />
              <button type="button" class="item-remove" title="Remover" @click="removeItem('oportunidade', idx)">×</button>
            </li>
          </ul>
          <div class="item-add">
            <input
              v-model="drafts.oportunidade"
              type="text"
              maxlength="500"
              placeholder="Adicionar item…"
              @keydown="onDraftKeydown('oportunidade', $event)"
            />
            <button type="button" @click="addItem('oportunidade')">+</button>
          </div>
          <div class="chips">
            <button
              v-for="t in typeOptions"
              :key="t"
              type="button"
              class="chip"
              :class="{ active: form.oportunidade_tipos.includes(t) }"
              @click="toggleType(t)"
            >
              {{ t }}
            </button>
          </div>
        </div>

        <div class="cell c-eval band-eval">
          <span class="num">04</span>
          <div class="cell-title">Valor esperado</div>
          <div class="hint">Ganho direto (tempo/custo/receita) + indireto (qualidade/risco). Como medir?</div>
          <ul class="item-list">
            <li v-for="(item, idx) in form.valor" :key="'va' + idx" class="item-row">
              <input
                :value="item"
                class="item-input"
                maxlength="500"
                @blur="onItemBlur('valor', idx, $event)"
              />
              <button type="button" class="item-remove" title="Remover" @click="removeItem('valor', idx)">×</button>
            </li>
          </ul>
          <div class="item-add">
            <input
              v-model="drafts.valor"
              type="text"
              maxlength="500"
              placeholder="Adicionar item…"
              @keydown="onDraftKeydown('valor', $event)"
            />
            <button type="button" @click="addItem('valor')">+</button>
          </div>
        </div>
        <div class="cell c-eval band-eval">
          <span class="num">05</span>
          <div class="cell-title">Dados &amp; insumos</div>
          <div class="hint">Combustível: volume, qualidade, acesso, formato. Sem dado, não sai do papel.</div>
          <ul class="item-list">
            <li v-for="(item, idx) in form.dados" :key="'da' + idx" class="item-row">
              <input
                :value="item"
                class="item-input"
                maxlength="500"
                @blur="onItemBlur('dados', idx, $event)"
              />
              <button type="button" class="item-remove" title="Remover" @click="removeItem('dados', idx)">×</button>
            </li>
          </ul>
          <div class="item-add">
            <input
              v-model="drafts.dados"
              type="text"
              maxlength="500"
              placeholder="Adicionar item…"
              @keydown="onDraftKeydown('dados', $event)"
            />
            <button type="button" @click="addItem('dados')">+</button>
          </div>
        </div>
        <div class="cell c-eval band-eval">
          <span class="num">06</span>
          <div class="cell-title">Custo &amp; complexidade</div>
          <div class="hint">CapEx (construir) × OpEx (operar: inferência/tokens + manutenção) + integração.</div>
          <ul class="item-list">
            <li v-for="(item, idx) in form.custo" :key="'cu' + idx" class="item-row">
              <input
                :value="item"
                class="item-input"
                maxlength="500"
                @blur="onItemBlur('custo', idx, $event)"
              />
              <button type="button" class="item-remove" title="Remover" @click="removeItem('custo', idx)">×</button>
            </li>
          </ul>
          <div class="item-add">
            <input
              v-model="drafts.custo"
              type="text"
              maxlength="500"
              placeholder="Adicionar item…"
              @keydown="onDraftKeydown('custo', $event)"
            />
            <button type="button" @click="addItem('custo')">+</button>
          </div>
        </div>
        <div class="cell c-eval band-eval cell-last">
          <span class="num">07</span>
          <div class="cell-title">Riscos &amp; governança</div>
          <div class="hint">LGPD e regras do setor, alucinação, dependência. Que supervisão humana é obrigatória?</div>
          <ul class="item-list">
            <li v-for="(item, idx) in form.riscos" :key="'ri' + idx" class="item-row">
              <input
                :value="item"
                class="item-input"
                maxlength="500"
                @blur="onItemBlur('riscos', idx, $event)"
              />
              <button type="button" class="item-remove" title="Remover" @click="removeItem('riscos', idx)">×</button>
            </li>
          </ul>
          <div class="item-add">
            <input
              v-model="drafts.riscos"
              type="text"
              maxlength="500"
              placeholder="Adicionar item…"
              @keydown="onDraftKeydown('riscos', $event)"
            />
            <button type="button" @click="addItem('riscos')">+</button>
          </div>
        </div>
      </div>

      <div class="decision">
        <div class="dec-left">
          <span class="num num-amber">08</span>
          <div class="cell-title">Decisão</div>
          <div class="hint">Pontue de 1 a 5. O cruzamento define o quadrante e o próximo passo.</div>
          <div class="scores">
            <div class="score">
              <b>Valor</b>
              <div class="dots">
                <button
                  v-for="n in 5"
                  :key="'v' + n"
                  type="button"
                  class="dot"
                  :class="{ active: form.score_valor === n }"
                  @click="setScore('score_valor', n)"
                >
                  {{ n }}
                </button>
              </div>
            </div>
            <div class="score">
              <b>Viabilidade</b>
              <div class="dots">
                <button
                  v-for="n in 5"
                  :key="'f' + n"
                  type="button"
                  class="dot"
                  :class="{ active: form.score_viabilidade === n }"
                  @click="setScore('score_viabilidade', n)"
                >
                  {{ n }}
                </button>
              </div>
            </div>
          </div>
          <div class="next">
            <label>Próximo passo concreto</label>
            <textarea
              v-model="form.proximo_passo"
              class="write write-sm"
              rows="2"
              placeholder="Ex.: PoC de 3 semanas com dados de faturamento…"
              @blur="persist"
            />
          </div>
        </div>
        <div class="matrix-wrap">
          <div class="matrix-cap">Onde essa oportunidade cai</div>
          <div class="matrix">
            <div class="qy">Valor →</div>
            <div class="q q-bet" :class="{ active: quadrant === 'aposta_estrategica' }">
              <b>Aposta estratégica</b>Alto valor, baixa viab. — planeje e destrave.
            </div>
            <div class="q q-go" :class="{ active: quadrant === 'ganho_rapido' }">
              <b>Ganho rápido</b>Alto valor, alta viab. — faça já.
            </div>
            <div class="q q-avoid" :class="{ active: quadrant === 'evitar' }">
              <b>Evitar · vaidade</b>Baixo valor, baixa viab. — só hype.
            </div>
            <div class="q q-inc" :class="{ active: quadrant === 'incremental' }">
              <b>Incremental</b>Baixo valor, alta viab. — encaixe quando sobrar.
            </div>
            <div /><div class="qx">Viabilidade →</div>
          </div>
        </div>
      </div>

      <footer class="sheet-footer">
        <span>Complementar à <b>SWOT de IA</b> — a SWOT olha a organização; este canvas desce à área.</span>
        <span>Consolide um canvas por área numa <b>matriz de portfólio</b> para priorizar o roadmap.</span>
      </footer>
    </div>
  </div>
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&display=swap');

.page {
  --ink: #12232e;
  --ink-soft: #3c525f;
  --paper: #f7f5ef;
  --line: #d8d2c6;
  --amber: #c48a26;
  --amber-tint: #f3e7cc;
  --slate: #5b7a86;
  --slate-tint: #e4ecee;
  --teal: #2f6e6a;
  --danger: #9c3b2e;
  --ok: #2f6e4a;
  max-width: 1180px;
  margin: 0 auto;
  padding: 20px 16px 48px;
  color: var(--ink);
}
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
  flex-wrap: wrap;
}
.back {
  color: var(--k0, var(--ink));
  text-decoration: none;
  font-size: 14px;
}
.back:hover {
  text-decoration: underline;
}
.save-status {
  font-size: 12px;
  color: var(--ink-soft);
}
.save-status .ok {
  color: var(--ok);
}
.save-status .err,
.state.err {
  color: var(--danger);
}
.state {
  padding: 40px 0;
  color: var(--ink-soft);
}
.sheet {
  background: var(--paper);
  border: 1px solid var(--line);
  box-shadow: 0 18px 50px -28px rgba(18, 35, 46, 0.45);
}
.sheet-header {
  padding: 26px 30px 22px;
  border-bottom: 3px solid var(--ink);
  display: flex;
  flex-wrap: wrap;
  gap: 22px;
  align-items: flex-end;
  justify-content: space-between;
}
.brand {
  font-family: 'Space Grotesk', var(--sans, system-ui), sans-serif;
  font-weight: 700;
  font-size: 11px;
  letter-spacing: 0.32em;
  text-transform: uppercase;
  color: var(--amber);
  margin-bottom: 8px;
}
h1 {
  font-family: 'Space Grotesk', var(--serif, Georgia), serif;
  font-weight: 700;
  font-size: 27px;
  line-height: 1.08;
  margin: 0;
  max-width: 22ch;
}
h1 span {
  color: var(--slate);
}
.subtitle {
  font-size: 12.5px;
  color: var(--ink-soft);
  margin-top: 8px;
  max-width: 46ch;
}
.title-field {
  display: block;
  margin-top: 14px;
  max-width: 360px;
}
.title-field span,
.meta label span,
.next label {
  display: block;
  font-size: 9.5px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--ink-soft);
  font-weight: 600;
  margin-bottom: 2px;
}
.title-field input,
.meta input {
  width: 100%;
  border: none;
  border-bottom: 1.5px dotted var(--slate);
  min-height: 28px;
  font-size: 13px;
  color: var(--ink);
  padding: 2px;
  background: transparent;
  font-family: inherit;
  outline: none;
}
.title-field input:focus,
.meta input:focus,
.write:focus {
  border-bottom-color: var(--amber);
  background: #fffef9;
}
.meta {
  display: grid;
  grid-template-columns: repeat(2, minmax(150px, 1fr));
  gap: 10px 20px;
  min-width: min(320px, 100%);
}
.grid {
  display: grid;
  grid-template-columns: repeat(12, 1fr);
}
.cell {
  border-right: 1px solid var(--line);
  border-bottom: 1px solid var(--line);
  padding: 14px 16px 16px;
  min-height: 132px;
  position: relative;
  background: var(--paper);
}
.cell::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  background: var(--stage, var(--slate));
}
.band-diag {
  --stage: var(--slate);
}
.band-eval {
  --stage: var(--teal);
}
.cell-last {
  border-right: none;
}
.num {
  font-family: 'Space Grotesk', sans-serif;
  font-weight: 700;
  font-size: 12px;
  color: var(--stage, var(--slate));
}
.num-amber {
  color: var(--amber);
}
.cell-title {
  font-family: 'Space Grotesk', sans-serif;
  font-weight: 600;
  font-size: 13.5px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin: 2px 0 5px;
}
.hint {
  font-size: 11px;
  color: var(--ink-soft);
  line-height: 1.35;
}
.write {
  margin-top: 9px;
  width: 100%;
  min-height: 72px;
  border: none;
  outline: none;
  resize: vertical;
  font-size: 12.5px;
  color: var(--ink);
  font-family: inherit;
  background: transparent;
  line-height: 1.45;
}
.write-sm {
  min-height: 44px;
}
.item-list {
  list-style: none;
  margin: 10px 0 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
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
  border-bottom-color: var(--amber);
  background: #fffef9;
}
.item-remove {
  flex-shrink: 0;
  width: 24px;
  height: 24px;
  border: none;
  background: transparent;
  color: var(--ink-soft);
  cursor: pointer;
  font-size: 16px;
  line-height: 1;
  border-radius: 4px;
}
.item-remove:hover {
  color: var(--danger);
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
  border-radius: 4px;
  background: #fff;
  font-size: 12px;
  padding: 6px 8px;
  font-family: inherit;
  color: var(--ink);
  outline: none;
}
.item-add input:focus {
  border-color: var(--amber);
  border-style: solid;
}
.item-add button {
  flex-shrink: 0;
  width: 30px;
  border: 1px solid var(--line);
  border-radius: 4px;
  background: #fff;
  color: var(--ink);
  cursor: pointer;
  font-size: 16px;
  font-weight: 600;
}
.item-add button:hover {
  border-color: var(--amber);
  color: var(--amber);
}
.c4 {
  grid-column: span 4;
}
.c-eval {
  grid-column: span 3;
}
.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  margin-top: 8px;
}
.chip {
  font-size: 10px;
  border: 1px solid var(--line);
  border-radius: 20px;
  padding: 3px 9px;
  color: var(--ink-soft);
  background: #fff;
  cursor: pointer;
  font-family: inherit;
}
.chip.active {
  border-color: var(--teal);
  background: #e1ebe9;
  color: var(--teal);
  font-weight: 600;
}
.decision {
  display: grid;
  grid-template-columns: 1.15fr 1fr;
}
.dec-left {
  padding: 16px 18px;
  border-right: 1px solid var(--line);
  border-bottom: 1px solid var(--line);
  position: relative;
}
.dec-left::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  background: var(--amber);
}
.scores {
  display: flex;
  gap: 26px;
  margin: 12px 0 6px;
  flex-wrap: wrap;
}
.score b {
  font-family: 'Space Grotesk', sans-serif;
  font-size: 11px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--ink-soft);
  display: block;
  margin-bottom: 5px;
}
.dots {
  display: flex;
  gap: 6px;
}
.dot {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: 1.5px solid var(--slate);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: var(--ink-soft);
  font-family: 'Space Grotesk', sans-serif;
  font-weight: 600;
  background: #fff;
  cursor: pointer;
}
.dot.active {
  background: var(--amber);
  border-color: var(--amber);
  color: #fff;
}
.next {
  margin-top: 12px;
}
.matrix-wrap {
  padding: 16px 18px;
  border-bottom: 1px solid var(--line);
  display: flex;
  flex-direction: column;
}
.matrix-cap {
  font-family: 'Space Grotesk', sans-serif;
  font-weight: 600;
  font-size: 11px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--ink-soft);
  margin-bottom: 9px;
}
.matrix {
  display: grid;
  grid-template-columns: 16px 1fr 1fr;
  grid-template-rows: 1fr 1fr 16px;
  gap: 5px;
  flex: 1;
  min-height: 150px;
}
.qy {
  writing-mode: vertical-rl;
  transform: rotate(180deg);
  font-size: 9px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--ink-soft);
  text-align: center;
  grid-row: span 2;
  align-self: center;
}
.qx {
  font-size: 9px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--ink-soft);
  text-align: center;
  grid-column: 2 / 4;
}
.q {
  border-radius: 6px;
  padding: 8px 9px;
  font-size: 10.5px;
  line-height: 1.25;
  border: 1px solid var(--line);
  opacity: 0.72;
  transition: opacity 0.2s, box-shadow 0.2s;
}
.q.active {
  opacity: 1;
  box-shadow: 0 0 0 2px var(--ink);
}
.q b {
  display: block;
  font-family: 'Space Grotesk', sans-serif;
  font-size: 11px;
  margin-bottom: 2px;
}
.q-go {
  background: #e8f0e7;
  border-color: #bbd3b7;
}
.q-go b {
  color: var(--ok);
}
.q-bet {
  background: var(--amber-tint);
  border-color: #e3ce9c;
}
.q-bet b {
  color: var(--amber);
}
.q-inc {
  background: var(--slate-tint);
  border-color: #cbd8db;
}
.q-inc b {
  color: var(--slate);
}
.q-avoid {
  background: #f1e1dd;
  border-color: #ddbcb4;
}
.q-avoid b {
  color: var(--danger);
}
.sheet-footer {
  padding: 12px 30px 18px;
  display: flex;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px;
  font-size: 10.5px;
  color: var(--ink-soft);
}
.sheet-footer b {
  color: var(--amber);
  font-family: 'Space Grotesk', sans-serif;
}

@media (max-width: 820px) {
  h1 {
    font-size: 22px;
  }
  .c4,
  .c-eval {
    grid-column: span 12;
  }
  .cell-last {
    border-right: 1px solid var(--line);
  }
  .decision {
    grid-template-columns: 1fr;
  }
  .dec-left {
    border-right: none;
  }
  .meta {
    grid-template-columns: 1fr;
    width: 100%;
  }
  .sheet-header {
    padding: 20px 16px;
  }
}
</style>
