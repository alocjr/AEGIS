<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import type { CanvasCronograma, CanvasCronogramaAtividade, CanvasCronogramaMarco } from '@/api/canvasProjects'

const crono = defineModel<CanvasCronograma>({ required: true })
const props = defineProps<{
  title: string
  area: string
}>()
const emit = defineEmits<{ persist: [] }>()

const HORIZONTES = [4, 6, 8, 10, 12, 16] as const
const MAX_ATIVIDADES = 30
const MAX_MARCOS = 12
const LIDER_OPTS = ['Gestor + Área', 'TI + Área', 'Consultoria', 'Comitê IA', 'Sponsor executivo']

const weeks = computed(() => Array.from({ length: crono.value.semanas }, (_, i) => i + 1))
const rangeEditing = ref<string | null>(null)

const draft = reactive({
  titulo: '',
  lideranca: '',
  semana_inicio: 1,
  semana_fim: 1,
  predecessor: '',
})
const marcoDraft = reactive({
  semana: 1,
  titulo: '',
})

const areaLabel = computed(() => {
  const area = (props.area || '').trim()
  return area ? `${area} · planejamento de projetos` : 'Planejamento de projetos'
})

function persist() {
  emit('persist')
}

function newId(prefix: string): string {
  const rand =
    typeof crypto !== 'undefined' && crypto.randomUUID
      ? crypto.randomUUID().slice(0, 8)
      : Math.random().toString(36).slice(2, 10)
  return `${prefix}_${rand}`
}

function padId(index: number): string {
  return String(index + 1).padStart(2, '0')
}

function durLabel(act: CanvasCronogramaAtividade): string {
  const n = Math.max(1, act.semana_fim - act.semana_inicio + 1)
  return `${n} sem.`
}

function barLabel(act: CanvasCronogramaAtividade): string {
  if (act.semana_inicio === act.semana_fim) return `S${act.semana_inicio}`
  return `S${act.semana_inicio}–${act.semana_fim}`
}

function barColor(start: number): string {
  const t = start / crono.value.semanas
  if (t >= 0.95) return '#BF360C'
  if (t >= 0.8) return '#2f5d4a'
  if (t >= 0.55) return '#12232e'
  return start % 2 === 0 ? '#607D8B' : '#4F868E'
}

function barStyle(act: CanvasCronogramaAtividade): Record<string, string> {
  return {
    gridColumn: `${act.semana_inicio} / ${act.semana_fim + 1}`,
    background: barColor(act.semana_inicio),
  }
}

function clampRange(act: CanvasCronogramaAtividade) {
  const max = crono.value.semanas
  act.semana_inicio = Math.min(Math.max(1, act.semana_inicio), max)
  act.semana_fim = Math.min(Math.max(1, act.semana_fim), max)
  if (act.semana_fim < act.semana_inicio) act.semana_fim = act.semana_inicio
}

function onRange(act: CanvasCronogramaAtividade) {
  clampRange(act)
  persist()
}

function setSemanas(n: number) {
  crono.value.semanas = n
  for (const act of crono.value.atividades) clampRange(act)
  for (const marco of crono.value.marcos) {
    marco.semana = Math.min(Math.max(1, marco.semana), n)
  }
  draft.semana_inicio = Math.min(draft.semana_inicio, n)
  draft.semana_fim = Math.min(draft.semana_fim, n)
  marcoDraft.semana = Math.min(marcoDraft.semana, n)
  persist()
}

function addAtividade() {
  const titulo = draft.titulo.trim()
  if (!titulo || crono.value.atividades.length >= MAX_ATIVIDADES) return
  let start = Math.min(Math.max(1, Number(draft.semana_inicio) || 1), crono.value.semanas)
  let end = Math.min(Math.max(1, Number(draft.semana_fim) || start), crono.value.semanas)
  if (end < start) [start, end] = [end, start]
  crono.value.atividades.push({
    id: newId('a'),
    titulo,
    lideranca: draft.lideranca.trim(),
    semana_inicio: start,
    semana_fim: end,
    predecessor: draft.predecessor.trim(),
  })
  draft.titulo = ''
  draft.lideranca = ''
  draft.predecessor = ''
  draft.semana_inicio = 1
  draft.semana_fim = 1
  persist()
}

function removeAtividade(id: string) {
  crono.value.atividades = crono.value.atividades.filter((a) => a.id !== id)
  if (rangeEditing.value === id) rangeEditing.value = null
  persist()
}

function marcosAt(week: number): CanvasCronogramaMarco[] {
  return crono.value.marcos.filter((m) => m.semana === week)
}

function marcoIndex(marco: CanvasCronogramaMarco): number {
  return crono.value.marcos.findIndex((m) => m.id === marco.id)
}

function marcoCode(marco: CanvasCronogramaMarco): string {
  const idx = marcoIndex(marco)
  return `M${idx + 1}`
}

function addMarco(semana?: number, titulo?: string) {
  if (crono.value.marcos.length >= MAX_MARCOS) return
  const week = Math.min(Math.max(1, semana ?? marcoDraft.semana), crono.value.semanas)
  const text = (titulo ?? marcoDraft.titulo).trim()
  crono.value.marcos.push({
    id: newId('m'),
    semana: week,
    titulo: text,
  })
  crono.value.marcos.sort((a, b) => a.semana - b.semana || a.id.localeCompare(b.id))
  marcoDraft.titulo = ''
  persist()
}

function addMarcoFromDraft() {
  if (!marcoDraft.titulo.trim()) return
  addMarco(marcoDraft.semana, marcoDraft.titulo)
}

function addMarcoAt(week: number) {
  addMarco(week, '')
}

function removeMarco(id: string) {
  crono.value.marcos = crono.value.marcos.filter((m) => m.id !== id)
  persist()
}

function onDraftKey(ev: KeyboardEvent) {
  if (ev.key === 'Enter') {
    ev.preventDefault()
    addAtividade()
  }
}

function onMarcoWeek() {
  crono.value.marcos.sort((a, b) => a.semana - b.semana || a.id.localeCompare(b.id))
  persist()
}

function onMarcoKey(ev: KeyboardEvent) {
  if (ev.key === 'Enter') {
    ev.preventDefault()
    addMarcoFromDraft()
  }
}

const draftRange = computed(() => {
  const max = crono.value.semanas
  let start = Math.min(Math.max(1, Number(draft.semana_inicio) || 1), max)
  let end = Math.min(Math.max(1, Number(draft.semana_fim) || start), max)
  if (end < start) [start, end] = [end, start]
  return { semana_inicio: start, semana_fim: end } as CanvasCronogramaAtividade
})
</script>

<template>
  <div class="crono" :style="{ '--weeks': String(crono.semanas) }">
    <div class="topbar">
      <span>Valorian 4 Future</span>
      <span>{{ areaLabel }}</span>
    </div>

    <header class="head">
      <div class="head-row">
        <h2>{{ title || 'Novo projeto' }}</h2>
        <label class="horizonte">
          <span>Horizonte</span>
          <select :value="crono.semanas" @change="setSemanas(Number(($event.target as HTMLSelectElement).value))">
            <option v-for="n in HORIZONTES" :key="n" :value="n">{{ n }} semanas</option>
          </select>
        </label>
      </div>
      <input
        v-model="crono.subtitulo"
        class="sub"
        type="text"
        maxlength="400"
        placeholder="Estratégia, dados e governança / Proposta de execução em 8 semanas"
        @blur="persist"
      />
      <label class="pre">
        <span>Pré-requisito de início</span>
        <input
          v-model="crono.pre_requisito"
          type="text"
          maxlength="500"
          placeholder="Agenda das diretorias confirmada e pacote mínimo de dados solicitado."
          @blur="persist"
        />
      </label>
    </header>

    <div class="gantt-wrap">
      <div class="gantt">
        <div class="gantt-head">
          <div class="c-id">ID</div>
          <div class="c-act">Atividade / entrega</div>
          <div class="c-lead">Liderança¹</div>
          <div class="c-dur">Dur.</div>
          <div class="c-pred">Predec.</div>
          <div class="c-weeks">
            <span v-for="w in weeks" :key="'h' + w">S{{ w }}</span>
          </div>
        </div>

        <div
          v-for="(act, idx) in crono.atividades"
          :key="act.id"
          class="gantt-row"
          :class="{ zebra: idx % 2 === 1 }"
        >
          <div class="c-id">{{ padId(idx) }}</div>
          <input
            v-model="act.titulo"
            class="c-act ghost"
            type="text"
            maxlength="400"
            placeholder="Atividade ou entrega"
            @blur="persist"
          />
          <input
            v-model="act.lideranca"
            class="c-lead ghost"
            type="text"
            maxlength="120"
            list="crono-lider"
            placeholder="Papel"
            @blur="persist"
          />
          <div class="c-dur">
            <button
              v-if="rangeEditing !== act.id"
              type="button"
              class="dur-btn"
              :title="'Ajustar semanas ' + barLabel(act)"
              @click="rangeEditing = act.id"
            >
              {{ durLabel(act) }}
            </button>
            <div v-else class="range-picks">
              <select
                v-model.number="act.semana_inicio"
                :aria-label="'Semana de início da atividade ' + padId(idx)"
                @change="onRange(act)"
              >
                <option v-for="w in weeks" :key="'s' + w" :value="w">S{{ w }}</option>
              </select>
              <select
                v-model.number="act.semana_fim"
                :aria-label="'Semana de fim da atividade ' + padId(idx)"
                @change="onRange(act)"
              >
                <option v-for="w in weeks" :key="'e' + w" :value="w">S{{ w }}</option>
              </select>
            </div>
          </div>
          <input
            v-model="act.predecessor"
            class="c-pred ghost"
            type="text"
            maxlength="40"
            placeholder="—"
            @blur="persist"
          />
          <div class="c-weeks" @click="rangeEditing = act.id">
            <span v-for="w in weeks" :key="act.id + 'w' + w" class="week-cell" :style="{ gridColumn: String(w) }" />
            <div class="bar" :style="barStyle(act)">{{ barLabel(act) }}</div>
            <button
              type="button"
              class="row-x"
              title="Remover atividade"
              @click.stop="removeAtividade(act.id)"
            >
              ×
            </button>
          </div>
        </div>

        <p v-if="!crono.atividades.length" class="empty">
          Nenhuma atividade ainda. Informe o nome, a semana de início e a de fim.
        </p>

        <form class="add-form" @submit.prevent="addAtividade">
          <div class="add-row">
          <div class="c-id muted">+</div>
          <input
            v-model="draft.titulo"
            class="c-act"
            type="text"
            maxlength="400"
            placeholder="Nova atividade / entrega"
            @keydown="onDraftKey"
          />
          <input
            v-model="draft.lideranca"
            class="c-lead"
            type="text"
            maxlength="120"
            list="crono-lider"
            placeholder="Liderança"
            @keydown="onDraftKey"
          />
          <div class="c-dur range-picks">
            <select v-model.number="draft.semana_inicio" aria-label="Semana de início">
              <option v-for="w in weeks" :key="'ds' + w" :value="w">S{{ w }}</option>
            </select>
            <select v-model.number="draft.semana_fim" aria-label="Semana de fim">
              <option v-for="w in weeks" :key="'de' + w" :value="w">S{{ w }}</option>
            </select>
          </div>
          <input
            v-model="draft.predecessor"
            class="c-pred"
            type="text"
            maxlength="40"
            placeholder="01 FS"
            @keydown="onDraftKey"
          />
          <div class="c-weeks">
            <span v-for="w in weeks" :key="'dw' + w" class="week-cell" :style="{ gridColumn: String(w) }" />
            <div class="bar bar-draft" :style="barStyle(draftRange)">{{ barLabel(draftRange) }}</div>
          </div>
          </div>
          <div class="add-footer">
            <button type="submit" :disabled="!draft.titulo.trim() || crono.atividades.length >= MAX_ATIVIDADES">
              Adicionar atividade
            </button>
          </div>
        </form>

        <div class="marco-row">
          <div class="marco-label">Marcos de decisão</div>
          <div class="c-weeks">
            <div v-for="w in weeks" :key="'mw' + w" class="week-cell marco-cell">
              <template v-if="marcosAt(w).length">
                <button
                  v-for="marco in marcosAt(w)"
                  :key="marco.id"
                  type="button"
                  class="diamond-btn"
                  :title="marco.titulo || marcoCode(marco)"
                  @click="removeMarco(marco.id)"
                >
                  <span class="diamond" aria-hidden="true" />
                  <span class="diamond-code">{{ marcoCode(marco) }}</span>
                </button>
              </template>
              <button
                v-else
                type="button"
                class="marco-slot"
                :disabled="crono.marcos.length >= MAX_MARCOS"
                :title="'Adicionar marco na semana ' + w"
                @click="addMarcoAt(w)"
              >
                +
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="marcos-detail">
      <div v-for="marco in crono.marcos" :key="marco.id" class="marco-col">
        <div class="marco-col-head">
          <span>{{ marcoCode(marco) }} · final da semana {{ marco.semana }}</span>
          <button type="button" class="row-x" title="Remover marco" @click="removeMarco(marco.id)">×</button>
        </div>
        <input
          v-model="marco.titulo"
          type="text"
          maxlength="200"
          placeholder="Ex.: Dores validadas"
          @blur="persist"
        />
        <label class="marco-week">
          Semana
          <select v-model.number="marco.semana" @change="onMarcoWeek">
            <option v-for="w in weeks" :key="'ms' + marco.id + w" :value="w">S{{ w }}</option>
          </select>
        </label>
      </div>
      <form v-if="crono.marcos.length < MAX_MARCOS" class="marco-col marco-add" @submit.prevent="addMarcoFromDraft">
        <div class="marco-col-head"><span>Novo marco</span></div>
        <input
          v-model="marcoDraft.titulo"
          type="text"
          maxlength="200"
          placeholder="Nome do marco"
          @keydown="onMarcoKey"
        />
        <label class="marco-week">
          Semana
          <select v-model.number="marcoDraft.semana">
            <option v-for="w in weeks" :key="'md' + w" :value="w">S{{ w }}</option>
          </select>
        </label>
        <button type="submit" :disabled="!marcoDraft.titulo.trim()">Adicionar marco</button>
      </form>
    </div>

    <label class="aceite">
      <span>Critério de aceite proposto</span>
      <textarea
        v-model="crono.criterio_aceite"
        rows="2"
        maxlength="1000"
        placeholder="Ex.: Comitê aprova o recorte de 3–5 casos e o pacote de dados mínimo para a onda 1."
        @blur="persist"
      />
    </label>

    <footer class="legend">
      <span>S = semana a partir do início autorizado.</span>
      <span>Duração = tempo decorrido, não esforço em pessoa-semana.</span>
      <span>FS = iniciar após a conclusão da predecessora.</span>
      <span>SS = iniciar em paralelo.</span>
      <span>¹ Papéis sugeridos — ajuste conforme o cliente. Clique no losango para remover o marco.</span>
    </footer>

    <datalist id="crono-lider">
      <option v-for="opt in LIDER_OPTS" :key="opt" :value="opt" />
    </datalist>
  </div>
</template>

<style scoped>
.crono {
  --navy: #12232e;
  --teal: #2f6e6a;
  --rust: #9a4a1a;
  --orange: #bf360c;
  --beige: #fff8e1;
  --line: #d8d2c6;
  --ink: #12232e;
  --muted: #5c6b73;
  background: #f7f5ef;
  border-top: 1px solid var(--line);
}
.topbar {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
  background: var(--navy);
  color: #fff;
  padding: 8px 18px;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.22em;
  text-transform: uppercase;
}
.head {
  padding: 18px 18px 14px;
}
.head-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
  flex-wrap: wrap;
}
h2 {
  margin: 0;
  font-family: var(--sans);
  font-size: 22px;
  font-weight: 700;
  line-height: 1.15;
  color: var(--navy);
  max-width: 52ch;
}
.horizonte {
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--muted);
}
.horizonte select,
.marco-week select,
.range-picks select {
  font-family: inherit;
  font-size: 12px;
  letter-spacing: 0;
  text-transform: none;
  font-weight: 600;
  color: var(--navy);
  border: 1px solid var(--line);
  background: #fff;
  padding: 3px 6px;
  border-radius: 2px;
}
.sub {
  display: block;
  width: 100%;
  margin-top: 8px;
  border: none;
  border-bottom: 1px dotted transparent;
  background: transparent;
  font-family: inherit;
  font-size: 14px;
  font-weight: 600;
  color: var(--teal);
  padding: 2px 0;
  outline: none;
}
.sub:focus {
  border-bottom-color: var(--teal);
}
.pre {
  display: block;
  margin-top: 10px;
}
.pre span,
.aceite > span {
  display: block;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--muted);
  margin-bottom: 2px;
}
.pre input {
  width: 100%;
  border: none;
  border-bottom: 1px dotted #c9c3b8;
  background: transparent;
  font-family: inherit;
  font-size: 13px;
  color: var(--muted);
  padding: 2px 0;
  outline: none;
}
.pre input:focus {
  border-bottom-color: var(--teal);
  color: var(--navy);
}

.gantt-wrap {
  overflow-x: auto;
  padding: 0 12px 8px;
}
.gantt {
  min-width: 860px;
  border: 1px solid var(--navy);
}
.gantt-head,
.gantt-row,
.add-row,
.marco-row {
  display: grid;
  grid-template-columns:
    40px minmax(150px, 1.7fr) minmax(92px, 0.9fr) 90px 64px minmax(260px, 1.9fr);
  align-items: stretch;
}
.gantt-head {
  background: var(--navy);
  color: #fff;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
.gantt-head > div,
.gantt-head .c-weeks span {
  padding: 8px 6px;
}
.c-id {
  display: flex;
  align-items: center;
  justify-content: center;
  font-variant-numeric: tabular-nums;
  font-weight: 700;
  font-size: 12px;
  color: var(--navy);
}
.gantt-head .c-id {
  color: #fff;
}
.c-act,
.c-lead,
.c-pred,
.c-dur {
  display: flex;
  align-items: center;
  min-width: 0;
  padding: 4px 6px;
  font-size: 12px;
  color: var(--navy);
}
.ghost {
  width: 100%;
  border: none;
  background: transparent;
  font-family: inherit;
  font-size: 12px;
  color: var(--navy);
  outline: none;
  padding: 4px 2px;
}
.ghost:focus {
  background: #fffef9;
}
.c-dur {
  justify-content: center;
  color: var(--muted);
  font-variant-numeric: tabular-nums;
  font-size: 11px;
}
.dur-btn {
  border: none;
  background: transparent;
  color: inherit;
  font: inherit;
  cursor: pointer;
  padding: 0;
}
.dur-btn:hover {
  color: var(--teal);
  text-decoration: underline;
}
.range-picks {
  display: flex;
  gap: 2px;
  justify-content: center;
}
.range-picks select {
  padding: 1px 2px;
  font-size: 10px;
  max-width: 48px;
}
.gantt-row .c-weeks {
  cursor: pointer;
}
.gantt-row {
  background: #fff;
  border-top: 1px solid #ece8df;
  min-height: 36px;
}
.gantt-row.zebra {
  background: #f3f1eb;
}
.c-weeks {
  display: grid;
  grid-template-columns: repeat(var(--weeks, 8), minmax(28px, 1fr));
  position: relative;
  background: repeating-linear-gradient(
    90deg,
    transparent 0,
    transparent calc(100% / var(--weeks) - 1px),
    #e6e1d6 calc(100% / var(--weeks) - 1px),
    #e6e1d6 calc(100% / var(--weeks))
  );
}
.gantt-head .c-weeks {
  background: transparent;
  text-align: center;
}
.gantt-head .c-weeks span {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 8px 0;
  border-left: 1px solid rgba(255, 255, 255, 0.18);
}
.week-cell {
  grid-row: 1;
  border-left: 1px solid #ece8df;
  min-height: 34px;
}
.bar {
  grid-row: 1;
  z-index: 1;
  align-self: center;
  height: 24px;
  margin: 4px 2px;
  border-radius: 1px;
  color: #fff;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.04em;
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;
}
.bar-draft {
  opacity: 0.55;
}
.row-x {
  position: absolute;
  right: 2px;
  top: 50%;
  transform: translateY(-50%);
  z-index: 2;
  width: 20px;
  height: 20px;
  border: none;
  background: transparent;
  color: var(--muted);
  cursor: pointer;
  opacity: 0;
  font-size: 14px;
  line-height: 1;
}
.gantt-row:hover .row-x,
.marco-col-head .row-x {
  opacity: 1;
}
.row-x:hover {
  color: var(--orange);
}

.empty {
  margin: 0;
  padding: 12px 16px;
  font-size: 12px;
  color: var(--muted);
  border-top: 1px solid #ece8df;
  background: #fff;
}
.add-form {
  border-top: 1px dashed #c9c3b8;
  background: #fbfaf6;
}
.add-row {
  padding: 4px 0;
}
.add-row input {
  width: 100%;
  border: 1px dashed var(--line);
  border-radius: 2px;
  background: #fff;
  font-family: inherit;
  font-size: 12px;
  padding: 5px 6px;
  outline: none;
  color: var(--navy);
}
.add-row input:focus {
  border-style: solid;
  border-color: var(--teal);
}
.add-row .c-id.muted {
  color: var(--teal);
  font-size: 16px;
}
.add-footer {
  display: flex;
  justify-content: flex-end;
  padding: 4px 10px 8px;
}
.add-footer button,
.marco-add button,
.aceite textarea {
  font-family: inherit;
}
.add-footer button,
.marco-add button {
  border: 1px solid var(--navy);
  background: var(--navy);
  color: #fff;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  padding: 6px 10px;
  cursor: pointer;
}
.add-footer button:disabled,
.marco-add button:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.marco-row {
  background: var(--beige);
  border-top: 1px solid #e6d7a8;
  min-height: 52px;
}
.marco-label {
  grid-column: 1 / 6;
  display: flex;
  align-items: center;
  padding: 0 12px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--teal);
}
.marco-row .c-weeks {
  background: transparent;
}
.marco-cell {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  min-height: 52px;
}
.diamond-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
  border: none;
  background: transparent;
  cursor: pointer;
  padding: 2px;
}
.diamond {
  width: 11px;
  height: 11px;
  background: #8d4b1f;
  transform: rotate(45deg);
}
.diamond-code {
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.04em;
  color: var(--rust);
}
.marco-slot {
  width: 18px;
  height: 18px;
  border: 1px dashed #cbb98a;
  background: transparent;
  color: #cbb98a;
  font-size: 12px;
  line-height: 1;
  cursor: pointer;
  opacity: 0;
}
.marco-row:hover .marco-slot {
  opacity: 1;
}
.marco-slot:hover:not(:disabled) {
  border-color: var(--rust);
  color: var(--rust);
}

.marcos-detail {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px 20px;
  padding: 16px 18px 8px;
}
.marco-col-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--rust);
  padding-bottom: 6px;
  border-bottom: 1px solid #e4d3c4;
  margin-bottom: 8px;
}
.marco-col-head .row-x {
  position: static;
  transform: none;
  opacity: 0.7;
}
.marco-col input {
  width: 100%;
  border: none;
  background: transparent;
  font-family: inherit;
  font-size: 14px;
  font-weight: 700;
  color: var(--navy);
  padding: 0;
  outline: none;
}
.marco-week {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 8px;
  font-size: 10px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--muted);
  font-weight: 600;
}
.marco-add button {
  margin-top: 10px;
}

.aceite {
  display: block;
  padding: 8px 18px 12px;
  border-top: 1px solid var(--line);
}
.aceite span {
  color: var(--teal);
}
.aceite textarea {
  width: 100%;
  margin-top: 4px;
  border: none;
  background: transparent;
  font-size: 13px;
  color: var(--navy);
  resize: vertical;
  outline: none;
  line-height: 1.45;
  padding: 0;
}

.legend {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 16px;
  padding: 4px 18px 16px;
  font-size: 10px;
  color: var(--muted);
  line-height: 1.4;
}

@media (max-width: 820px) {
  h2 {
    font-size: 18px;
  }
  .gantt {
    min-width: 760px;
  }
}
</style>
