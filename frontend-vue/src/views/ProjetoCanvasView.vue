<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import {
  getCanvasProject,
  updateCanvasProject,
  type CanvasProject,
  type CanvasProjectPayload,
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

const form = ref({
  title: '',
  area_negocio: '',
  responsavel: '',
  data: '',
  objetivo_estrategico: '',
  contexto: '',
  dores: '',
  oportunidade: '',
  oportunidade_tipos: [] as string[],
  dados: '',
  valor: '',
  custo: '',
  riscos: '',
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

let saveTimer: ReturnType<typeof setTimeout> | null = null
let skipWatch = true

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

function applyProject(p: CanvasProject) {
  skipWatch = true
  project.value = p
  form.value = {
    title: p.title || 'Novo projeto',
    area_negocio: p.area_negocio || '',
    responsavel: p.responsavel || '',
    data: p.data || '',
    objetivo_estrategico: p.objetivo_estrategico || '',
    contexto: p.contexto || '',
    dores: p.dores || '',
    oportunidade: p.oportunidade || '',
    oportunidade_tipos: [...(p.oportunidade_tipos || [])],
    dados: p.dados || '',
    valor: p.valor || '',
    custo: p.custo || '',
    riscos: p.riscos || '',
    score_valor: p.score_valor,
    score_viabilidade: p.score_viabilidade,
    proximo_passo: p.proximo_passo || '',
  }
  if (p.opportunity_type_options?.length) {
    typeOptions.value = p.opportunity_type_options
  }
  queueMicrotask(() => {
    skipWatch = false
  })
}

function toggleType(t: string) {
  const set = new Set(form.value.oportunidade_tipos)
  if (set.has(t)) set.delete(t)
  else set.add(t)
  form.value.oportunidade_tipos = [...set]
}

function setScore(field: 'score_valor' | 'score_viabilidade', n: number) {
  form.value[field] = form.value[field] === n ? null : n
}

function scheduleSave() {
  if (skipWatch || !projectId.value) return
  saveState.value = 'idle'
  if (saveTimer) clearTimeout(saveTimer)
  saveTimer = setTimeout(() => {
    void persist()
  }, 700)
}

async function persist() {
  if (!projectId.value) return
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
  }
}

watch(form, scheduleSave, { deep: true })

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

onUnmounted(() => {
  if (saveTimer) clearTimeout(saveTimer)
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
        <span v-else class="muted">Alterações salvam automaticamente</span>
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
            <input v-model="form.title" type="text" maxlength="200" />
          </label>
        </div>
        <div class="meta">
          <label>
            <span>Área de negócio</span>
            <input v-model="form.area_negocio" type="text" placeholder="Ex.: Comercial" maxlength="200" />
          </label>
          <label>
            <span>Responsável</span>
            <input v-model="form.responsavel" type="text" placeholder="Nome" maxlength="200" />
          </label>
          <label>
            <span>Data</span>
            <input v-model="form.data" type="text" placeholder="__/__/____" maxlength="40" />
          </label>
          <label>
            <span>Objetivo estratégico da área</span>
            <input
              v-model="form.objetivo_estrategico"
              type="text"
              placeholder="O que essa área precisa entregar"
              maxlength="2000"
            />
          </label>
        </div>
      </header>

      <div class="grid">
        <div class="cell c4 band-diag">
          <span class="num">01</span>
          <div class="cell-title">Contexto da área</div>
          <div class="hint">KPIs e processos-chave. Onde essa área cria ou destrói valor hoje?</div>
          <textarea v-model="form.contexto" class="write" rows="4" placeholder="Processos, indicadores, volume de trabalho…" />
        </div>
        <div class="cell c4 band-diag">
          <span class="num">02</span>
          <div class="cell-title">Dores &amp; gargalos</div>
          <div class="hint">Atrito, retrabalho, erro, custo, lentidão. <strong>Descreva a dor — não a solução.</strong></div>
          <textarea v-model="form.dores" class="write" rows="4" placeholder="O que trava, custa ou falha hoje…" />
        </div>
        <div class="cell c4 band-diag cell-last">
          <span class="num">03</span>
          <div class="cell-title">Oportunidade de IA</div>
          <div class="hint">Em uma frase: o que a IA faria e qual dor do bloco 02 ela ataca.</div>
          <textarea v-model="form.oportunidade" class="write write-sm" rows="2" placeholder="A IA faria…" />
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
          <div class="cell-title">Dados &amp; insumos</div>
          <div class="hint">Combustível: volume, qualidade, acesso, formato. Sem dado, não sai do papel.</div>
          <textarea v-model="form.dados" class="write" rows="4" placeholder="Que dados existem? Onde? Em que estado?" />
        </div>
        <div class="cell c-eval band-eval">
          <span class="num">05</span>
          <div class="cell-title">Valor esperado</div>
          <div class="hint">Ganho direto (tempo/custo/receita) + indireto (qualidade/risco). Como medir?</div>
          <textarea v-model="form.valor" class="write" rows="4" placeholder="Ganho + métrica de sucesso" />
        </div>
        <div class="cell c-eval band-eval">
          <span class="num">06</span>
          <div class="cell-title">Custo &amp; complexidade</div>
          <div class="hint">CapEx (construir) × OpEx (operar: inferência/tokens + manutenção) + integração.</div>
          <textarea v-model="form.custo" class="write" rows="4" placeholder="Construir, operar e integrar custa…" />
        </div>
        <div class="cell c-eval band-eval cell-last">
          <span class="num">07</span>
          <div class="cell-title">Riscos &amp; governança</div>
          <div class="hint">LGPD e regras do setor, alucinação, dependência. Que supervisão humana é obrigatória?</div>
          <textarea v-model="form.riscos" class="write" rows="4" placeholder="Riscos e nível de human-in-the-loop" />
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
