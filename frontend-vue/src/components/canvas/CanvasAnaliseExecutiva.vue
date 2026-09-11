<script setup lang="ts">
import { computed, ref } from 'vue'
import {
  ANALISE_CRITERIOS,
  analisePonderada,
  formatNota,
  type CanvasAnaliseExecutiva,
  type AnaliseCriterioId,
} from '@/lib/canvasAnaliseExecutiva'

const props = defineProps<{
  modelValue: CanvasAnaliseExecutiva
}>()

const emit = defineEmits<{
  'update:modelValue': [CanvasAnaliseExecutiva]
  persist: []
}>()

const open = ref(true)
const ponderada = computed(() => analisePonderada(props.modelValue.scores))

function toggle() {
  open.value = !open.value
}

function setScore(id: AnaliseCriterioId, n: number) {
  const current = props.modelValue.scores[id]
  emit('update:modelValue', {
    ...props.modelValue,
    scores: { ...props.modelValue.scores, [id]: current === n ? null : n },
  })
  emit('persist')
}

function onObservacaoBlur(ev: Event) {
  const value = (ev.target as HTMLTextAreaElement).value
  if (value === props.modelValue.observacao) return
  emit('update:modelValue', { ...props.modelValue, observacao: value })
  emit('persist')
}
</script>

<template>
  <section class="exec" :class="{ collapsed: !open }">
    <button
      type="button"
      class="exec-head"
      :aria-expanded="open"
      aria-controls="analise-executiva-body"
      @click="toggle"
    >
      <span class="num">08</span>
      <div class="exec-copy">
        <div class="cell-title">Análise executiva</div>
        <div v-if="open" class="hint">
          Método de seleção e priorização. Note cada critério de 1 a 5; os pesos são os sugeridos para o comitê.
        </div>
      </div>
      <div class="exec-total" :class="{ empty: ponderada.value == null }">
        <template v-if="ponderada.value != null">
          <b>{{ formatNota(ponderada.value) }}</b>
          <span>/ 5</span>
          <em>{{ Math.round(ponderada.pct || 0) }}%</em>
          <small>{{ ponderada.scored }}/{{ ponderada.total }} critérios</small>
        </template>
        <template v-else>
          <small>Sem notas ainda</small>
        </template>
      </div>
      <span class="exec-caret" aria-hidden="true">{{ open ? '−' : '+' }}</span>
    </button>

    <div v-if="open" id="analise-executiva-body" class="exec-body">
      <div class="exec-table-wrap">
        <table class="exec-table">
          <thead>
            <tr>
              <th class="c-crit">Critério</th>
              <th class="c-peso">Peso</th>
              <th class="c-q">Pergunta de decisão</th>
              <th class="c-nota">Nota</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="c in ANALISE_CRITERIOS" :key="c.id">
              <td class="c-crit">{{ c.label }}</td>
              <td class="c-peso">{{ c.peso }}%</td>
              <td class="c-q">{{ c.pergunta }}</td>
              <td class="c-nota">
                <div class="dots" role="group" :aria-label="`Nota de ${c.label}`">
                  <button
                    v-for="n in 5"
                    :key="c.id + n"
                    type="button"
                    class="dot"
                    :class="{ active: modelValue.scores[c.id] === n }"
                    @click="setScore(c.id, n)"
                  >
                    {{ n }}
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <label class="exec-obs">
        <span>Observação do comitê (opcional)</span>
        <textarea
          :value="modelValue.observacao"
          class="write write-sm"
          rows="2"
          maxlength="2000"
          placeholder="Síntese da discussão, premissas ou ressalvas da priorização…"
          @blur="onObservacaoBlur"
        />
      </label>
    </div>
  </section>
</template>

<style scoped>
.exec {
  border-bottom: 1px solid var(--line);
  padding: 4px 18px 8px;
  position: relative;
  background: var(--paper);
}
.exec:not(.collapsed) {
  padding-bottom: 18px;
}
.exec::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  background: var(--teal);
}
.exec-head {
  display: flex;
  align-items: flex-start;
  gap: 12px 18px;
  width: 100%;
  margin: 0;
  padding: 12px 0 8px 8px;
  border: none;
  background: transparent;
  text-align: left;
  font-family: inherit;
  color: inherit;
  cursor: pointer;
}
.exec.collapsed .exec-head {
  align-items: center;
  padding-bottom: 12px;
}
.exec.collapsed .exec-caret,
.exec.collapsed .num {
  margin-top: 0;
  padding-top: 0;
}
.exec.collapsed .exec-total {
  padding-top: 0;
}
.exec.collapsed .exec-total b {
  font-size: 22px;
}
.exec-copy {
  flex: 1;
  min-width: 0;
}
.exec-caret {
  flex-shrink: 0;
  margin-top: 2px;
  font-size: 16px;
  line-height: 1;
  color: var(--ink-soft);
}
.exec-total {
  margin-left: auto;
  text-align: right;
  white-space: nowrap;
  padding-top: 2px;
}
.exec-total b {
  font-family: var(--serif);
  font-size: 28px;
  font-weight: 600;
  line-height: 1;
  color: var(--k0);
}
.exec-total span {
  font-size: 13px;
  color: var(--ink-soft);
  margin-left: 2px;
}
.exec-total em {
  display: inline-block;
  margin-left: 10px;
  font-style: normal;
  font-size: 13px;
  font-weight: 700;
  color: var(--teal);
}
.exec-total small {
  display: block;
  margin-top: 4px;
  font-size: 11px;
  color: var(--ink-soft);
}
.exec-total.empty small {
  font-size: 12px;
}
.exec-body {
  padding-left: 8px;
}
.num {
  font-family: var(--sans);
  font-weight: 700;
  font-size: 12px;
  color: var(--teal);
  padding-top: 3px;
}
.cell-title {
  font-family: var(--sans);
  font-weight: 600;
  font-size: 14px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin: 2px 0 5px;
}
.hint {
  font-size: 12px;
  color: var(--ink-soft);
  line-height: 1.4;
}
.exec-table-wrap {
  overflow-x: auto;
}
.exec-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.exec-table th {
  text-align: left;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--ink-soft);
  padding: 6px 10px 8px;
  border-bottom: 1px solid var(--line);
}
.exec-table td {
  padding: 8px 10px;
  border-bottom: 1px solid var(--bd2, var(--line));
  vertical-align: middle;
  color: var(--k0);
}
.exec-table tbody tr:last-child td {
  border-bottom: none;
}
.c-peso {
  width: 4.5rem;
  font-variant-numeric: tabular-nums;
  font-weight: 600;
  color: var(--ink-soft);
}
.c-q {
  color: var(--ink);
}
.c-nota {
  width: 168px;
}
.dots {
  display: flex;
  gap: 5px;
}
.dot {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  border: 1.5px solid var(--slate);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  color: var(--ink-soft);
  font-family: var(--sans);
  font-weight: 600;
  background: #fff;
  cursor: pointer;
}
.dot.active {
  background: var(--teal);
  border-color: var(--teal);
  color: #fff;
}
.exec-obs {
  display: block;
  margin-top: 12px;
  padding-left: 8px;
}
.exec-obs span {
  display: block;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--ink-soft);
  margin-bottom: 6px;
}
.write {
  width: 100%;
  font: inherit;
  padding: 8px 10px;
  border: 1px solid var(--line);
  border-radius: var(--r-sm);
  background: #fff;
  resize: vertical;
}
.write-sm {
  min-height: 52px;
}

@media (max-width: 820px) {
  .exec-head {
    flex-wrap: wrap;
  }
  .exec-total {
    margin-left: 28px;
    text-align: left;
  }
  .c-q {
    min-width: 18ch;
  }
}
</style>
