<script setup lang="ts">
import { RouterLink } from 'vue-router'
import type { CanvasEditor } from '@/composables/useCanvasEditor'

const props = defineProps<{ editor: CanvasEditor }>()
const {
  form, drafts, openHelp, originOpen, krSectionOpen, swotList, swot, swotLoading, swotError,
  okrCycle, okrLoading, okrError, typeOptions, selectedInitiatives, selectedItems, selectedKeyResults,
  EVAL_CELLS, TOWS_GROUPS, SWOT_QUADRANT_LABEL, quadrant,
  crossingLabel, isTowsSelected, isKrSelected, toggleTows, toggleKr, removeSwotItemLink,
  onSelectSwot, onDateInput, addItem, removeItem, autosizeItem, onItemBlur,
  onDraftKeydown, toggleHelp, toggleType, setScore, persist,
} = props.editor
</script>

<template>
    <div class="sheet">
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
        <label class="head-justify">
          <span>Como este projeto trata as estratégias TOWS</span>
          <textarea
            v-model="form.justificativa_tows"
            rows="3"
            maxlength="4000"
            placeholder="Ex.: executa a ofensiva F×O de usar o patrocínio executivo para lançar o copiloto de atendimento antes do concorrente; e cobre parte da fraqueza de dados dispersos ao consolidar o histórico de tickets."
            @blur="persist"
          />
          <em class="head-justify-hint">
            Justifique o vínculo: que iniciativas do bloco 00 este projeto executa, até onde ele
            entrega cada uma e o que fica de fora.
            <template v-if="form.tows_ids.length">
              {{ form.tows_ids.length }} iniciativa(s) vinculada(s).
            </template>
          </em>
        </label>
      </header>

      <section class="origin">
        <button
          type="button"
          class="origin-head"
          :aria-expanded="originOpen"
          @click="originOpen = !originOpen"
        >
          <span class="num">00</span>
          <span class="cell-title origin-title">Origem estratégica · TOWS</span>
          <span v-if="form.tows_ids.length" class="origin-count">
            {{ form.tows_ids.length }} iniciativa(s)
          </span>
          <span v-else class="origin-count muted">nenhuma iniciativa vinculada</span>
          <span class="origin-caret" aria-hidden="true">{{ originOpen ? '−' : '+' }}</span>
        </button>

        <div v-if="!originOpen && selectedInitiatives.length" class="origin-chips">
          <span v-for="init in selectedInitiatives" :key="init.id" class="origin-chip">
            <b>{{ init.groupLabel }}</b>{{ init.acao }}
          </span>
        </div>

        <div v-if="originOpen" class="origin-body">
          <p class="hint">
            Marque as iniciativas da matriz TOWS que este projeto executa. O vínculo aparece no
            Mapa Estratégico ligando maturidade → SWOT → este canvas.
          </p>

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
                    <label class="origin-item" :class="{ active: isTowsSelected(init.id) }">
                      <input
                        type="checkbox"
                        :checked="isTowsSelected(init.id)"
                        :disabled="!init.id"
                        @change="toggleTows(init.id)"
                      />
                      <span class="origin-item-body">
                        <span class="origin-acao">{{ init.acao || '—' }}</span>
                        <span v-if="crossingLabel(init)" class="origin-cross">
                          {{ crossingLabel(init) }}
                        </span>
                      </span>
                    </label>
                  </li>
                </ul>
              </div>
            </div>

            <div v-if="selectedItems.length" class="origin-items">
              <span class="origin-items-label">Itens SWOT vinculados</span>
              <span v-for="entry in selectedItems" :key="entry.id" class="origin-chip">
                <b>{{ SWOT_QUADRANT_LABEL[entry.item.quadrant] }}</b>{{ entry.item.texto }}
                <button
                  type="button"
                  class="origin-chip-x"
                  title="Remover vínculo"
                  @click="removeSwotItemLink(entry.id)"
                >×</button>
              </span>
            </div>
          </template>
        </div>
      </section>

      <section class="origin">
        <button
          type="button"
          class="origin-head"
          :aria-expanded="krSectionOpen"
          @click="krSectionOpen = !krSectionOpen"
        >
          <span class="num">00</span>
          <span class="cell-title origin-title">Key Results (OKR) endereçados</span>
          <span v-if="form.kr_ids.length" class="origin-count">
            {{ form.kr_ids.length }} resultado(s)
          </span>
          <span v-else class="origin-count muted">nenhum Key Result vinculado</span>
          <span class="origin-caret" aria-hidden="true">{{ krSectionOpen ? '−' : '+' }}</span>
        </button>

        <div v-if="!krSectionOpen && selectedKeyResults.length" class="origin-chips">
          <span v-for="entry in selectedKeyResults" :key="entry.id" class="origin-chip">
            <b>{{ entry.kr.objetivoTitulo }}</b>{{ entry.kr.titulo }}
          </span>
        </div>

        <div v-if="krSectionOpen" class="origin-body">
          <p class="hint">
            Marque os Key Results que este projeto endereça. O vínculo aparece no Mapa
            Estratégico ligando o Objective ao Key Result e a este canvas.
          </p>

          <div v-if="okrError" class="origin-err">{{ okrError }}</div>
          <p v-if="okrLoading" class="origin-none">Carregando ciclo OKR…</p>
          <p v-else-if="!okrCycle" class="origin-none">
            Nenhum ciclo OKR ativo.
            <RouterLink to="/okrs" class="origin-link">Abrir painel de OKR</RouterLink>
          </p>
          <p v-else-if="!okrCycle.objectives.length" class="origin-none">
            O ciclo ativo ({{ okrCycle.label }}) ainda não tem Objectives.
            <RouterLink :to="`/okrs/${okrCycle.id}`" class="origin-link">Editar ciclo</RouterLink>
          </p>
          <div v-else class="origin-groups">
            <div v-for="obj in okrCycle.objectives" :key="obj.id" class="origin-group">
              <div class="origin-group-head">
                <b>{{ obj.titulo }}</b>
              </div>
              <p v-if="!obj.key_results.length" class="origin-none">Sem Key Results neste objetivo.</p>
              <ul v-else class="origin-list">
                <li v-for="kr in obj.key_results" :key="kr.id">
                  <label class="origin-item" :class="{ active: isKrSelected(kr.id) }">
                    <input
                      type="checkbox"
                      :checked="isKrSelected(kr.id)"
                      @change="toggleKr(kr.id)"
                    />
                    <span class="origin-item-body">
                      <span class="origin-acao">{{ kr.titulo || '—' }}</span>
                      <span class="origin-cross">{{ kr.progress_pct.toFixed(0) }}% concluído</span>
                    </span>
                  </label>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      <div class="grid">
        <div class="cell c4 band-diag">
          <span class="num">01</span>
          <div class="cell-title">Contexto da área</div>
          <div class="hint">KPIs e processos-chave. Onde essa área cria ou destrói valor hoje?</div>
          <ul class="item-list">
            <li v-for="(item, idx) in form.contexto" :key="'c' + idx" class="item-row">
              <textarea
                :value="item"
                class="item-input"
                rows="1"
                maxlength="500"
                :ref="(el) => autosizeItem(el as HTMLTextAreaElement | null)"
                @input="autosizeItem"
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
              <textarea
                :value="item"
                class="item-input"
                rows="1"
                maxlength="500"
                :ref="(el) => autosizeItem(el as HTMLTextAreaElement | null)"
                @input="autosizeItem"
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
              <textarea
                :value="item"
                class="item-input"
                rows="1"
                maxlength="500"
                :ref="(el) => autosizeItem(el as HTMLTextAreaElement | null)"
                @input="autosizeItem"
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

        <div
          v-for="(cell, cellIdx) in EVAL_CELLS"
          :key="cell.field"
          class="cell c-eval band-eval"
          :class="{ 'cell-last': cellIdx === EVAL_CELLS.length - 1, 'help-open': openHelp === cell.field }"
        >
          <button
            type="button"
            class="cell-help-btn"
            :aria-expanded="openHelp === cell.field"
            :aria-label="`Ajuda · ${cell.title}`"
            @click="toggleHelp(cell.field, $event)"
          >
            ?
          </button>
          <div
            v-if="openHelp === cell.field"
            class="cell-help"
            role="dialog"
            :aria-label="`Banco de itens · ${cell.title}`"
          >
            <div class="cell-help-head">
              <span class="cell-help-num">{{ cell.num }}</span>
              <div>
                <strong>{{ cell.title }}</strong>
                <span class="cell-help-tag">{{ cell.tagline }}</span>
              </div>
            </div>
            <p class="cell-help-answers">{{ cell.answers }}</p>
            <p class="cell-help-pulls">{{ cell.pulls }}</p>
            <p class="cell-help-note">
              Perguntas-guia e itens de exemplo — copie, adapte à sua área e descarte o que não se aplica.
            </p>
            <div class="cell-help-section">Perguntas-guia</div>
            <ul class="cell-help-questions">
              <li v-for="(q, qi) in cell.questions" :key="'q' + qi">{{ q }}</li>
            </ul>
            <div class="cell-help-section">Itens de exemplo</div>
            <ul class="cell-help-examples">
              <li v-for="(ex, ei) in cell.examples" :key="'e' + ei">{{ ex }}</li>
            </ul>
            <p class="cell-help-alert"><strong>Sinal de alerta.</strong> {{ cell.alert }}</p>
          </div>
          <span class="num">{{ cell.num }}</span>
          <div class="cell-title">{{ cell.title }}</div>
          <div class="hint">{{ cell.hint }}</div>
          <ul class="item-list">
            <li v-for="(item, idx) in form[cell.field]" :key="cell.field + idx" class="item-row">
              <textarea
                :value="item"
                class="item-input"
                rows="1"
                maxlength="500"
                :ref="(el) => autosizeItem(el as HTMLTextAreaElement | null)"
                @input="autosizeItem"
                @blur="onItemBlur(cell.field, idx, $event)"
              />
              <button type="button" class="item-remove" title="Remover" @click="removeItem(cell.field, idx)">×</button>
            </li>
          </ul>
          <div class="item-add">
            <input
              v-model="drafts[cell.field]"
              type="text"
              maxlength="500"
              placeholder="Adicionar item…"
              @keydown="onDraftKeydown(cell.field, $event)"
            />
            <button type="button" @click="addItem(cell.field)">+</button>
          </div>
        </div>
      </div>

      <div class="decision">
        <div class="dec-left">
          <span class="num num-amber">08</span>
          <div class="cell-title">Decisão</div>
          <div class="hint">Preencha 04–07 antes de pontuar. Notas de 1 a 5 — o cruzamento define o quadrante e o próximo passo.</div>
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
</template>

<style scoped>
.sheet {
  background: var(--canvas-paper);
  border: 1px solid var(--canvas-line);
  box-shadow: 0 18px 50px -28px rgba(18, 35, 46, 0.45);
}
.sheet-header {
  padding: 26px 30px 22px;
  border-bottom: 3px solid var(--canvas-ink);
  display: flex;
  flex-wrap: wrap;
  gap: 22px;
  align-items: flex-end;
  justify-content: space-between;
}
.brand {
  font-family: var(--sans);
  font-weight: 700;
  font-size: 11px;
  letter-spacing: 0.32em;
  text-transform: uppercase;
  color: var(--warn-text);
  margin-bottom: 8px;
}
h1 {
  font-family: var(--serif);
  font-weight: 700;
  font-size: 27px;
  line-height: 1.08;
  margin: 0;
  max-width: 22ch;
}
h1 span {
  color: var(--canvas-slate);
}
.subtitle {
  font-size: 13px;
  color: var(--canvas-ink-soft);
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
.head-justify > span,
.next label {
  display: block;
  font-size: 10px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--canvas-ink-soft);
  font-weight: 600;
  margin-bottom: 2px;
}
.title-field input,
.meta input {
  width: 100%;
  border: none;
  border-bottom: 1.5px dotted var(--canvas-slate);
  min-height: 28px;
  font-size: 13px;
  color: var(--canvas-ink);
  padding: 2px;
  background: transparent;
  font-family: inherit;
  outline: none;
}
.title-field input:focus,
.meta input:focus,
.write:focus {
  border-bottom-color: var(--warn-text);
  background: #fffef9;
}
.meta {
  display: grid;
  grid-template-columns: repeat(2, minmax(150px, 1fr));
  gap: 10px 20px;
  min-width: min(320px, 100%);
}
.head-justify {
  flex-basis: 100%;
  display: block;
  padding-top: 14px;
  border-top: 1px dotted var(--canvas-line);
}
.head-justify textarea {
  width: 100%;
  min-height: 56px;
  resize: vertical;
  border: 1px solid var(--canvas-line);
  border-radius: var(--r-xs);
  background: #fff;
  font-family: inherit;
  font-size: 13px;
  line-height: 1.45;
  color: var(--canvas-ink);
  padding: 7px 9px;
  outline: none;
}
.head-justify textarea:focus {
  border-color: var(--warn-text);
  background: #fffef9;
}
.head-justify-hint {
  display: block;
  margin-top: 4px;
  font-size: 11px;
  line-height: 1.35;
  color: var(--canvas-ink-soft);
  font-style: normal;
}

.origin {
  position: relative;
  border-bottom: 1px solid var(--canvas-line);
  background: #fffdf8;
}
.origin::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  background: var(--warn);
}
.origin-head {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 12px 16px;
  border: none;
  background: transparent;
  text-align: left;
  font-family: inherit;
  color: var(--canvas-ink);
  cursor: pointer;
}
.origin-head .num {
  color: var(--warn-text);
}
.origin-title {
  margin: 0;
  padding: 0;
}
.origin-count {
  font-size: 11px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  font-weight: 600;
  color: var(--warn-text);
}
.origin-count.muted {
  color: var(--canvas-ink-soft);
  font-weight: 500;
}
.origin-caret {
  margin-left: auto;
  font-size: 16px;
  line-height: 1;
  color: var(--canvas-ink-soft);
}
.origin-chips,
.origin-items {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  padding: 0 16px 12px;
}
.origin-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  max-width: 100%;
  padding: 3px 9px;
  border: 1px solid #e3ce9c;
  border-radius: 20px;
  background: var(--canvas-amber-tint);
  font-size: 11px;
  line-height: 1.3;
  color: var(--canvas-ink);
}
.origin-chip b {
  font-family: var(--sans);
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--warn-text);
}
.origin-chip-x {
  border: none;
  background: transparent;
  color: var(--canvas-ink-soft);
  font-size: 13px;
  line-height: 1;
  padding: 0;
}
.origin-chip-x:hover {
  color: var(--low);
}
.origin-body {
  padding: 0 16px 16px;
}
.origin-body .hint {
  max-width: 70ch;
  margin-bottom: 10px;
}
.origin-err {
  margin-bottom: 10px;
  padding: 8px 10px;
  border-left: 3px solid var(--low);
  background: #f8eee8;
  font-size: 12px;
  color: var(--canvas-ink);
}
.origin-none {
  font-size: 12px;
  color: var(--canvas-ink-soft);
  margin: 4px 0;
}
.origin-link {
  color: var(--warn-text);
  text-decoration: underline;
}
.origin-select {
  display: block;
  max-width: 420px;
  margin-bottom: 12px;
}
.origin-select span {
  display: block;
  font-size: 10px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--canvas-ink-soft);
  font-weight: 600;
  margin-bottom: 3px;
}
.origin-select select {
  width: 100%;
  border: 1px solid var(--canvas-line);
  border-radius: var(--r-xs);
  background: #fff;
  font-family: inherit;
  font-size: 13px;
  color: var(--canvas-ink);
  padding: 6px 8px;
}
.origin-groups {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 12px;
}
.origin-group {
  border: 1px solid var(--canvas-line);
  border-radius: var(--r-xs);
  background: #fff;
  padding: 10px;
}
.origin-group-head b {
  display: block;
  font-family: var(--sans);
  font-size: 11px;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--canvas-teal);
}
.origin-group-head span {
  display: block;
  font-size: 11px;
  color: var(--canvas-ink-soft);
  margin-bottom: 6px;
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
  gap: 8px;
  align-items: flex-start;
  padding: 6px 8px;
  border: 1px solid transparent;
  border-radius: var(--r-xs);
  cursor: pointer;
}
.origin-item:hover {
  background: #faf8f2;
}
.origin-item.active {
  border-color: #e3ce9c;
  background: var(--canvas-amber-tint);
}
.origin-item input {
  margin-top: 2px;
  flex-shrink: 0;
  accent-color: var(--warn-text);
}
.origin-item-body {
  min-width: 0;
}
.origin-acao {
  display: block;
  font-size: 12px;
  line-height: 1.35;
  color: var(--canvas-ink);
}
.origin-cross {
  display: block;
  margin-top: 2px;
  font-size: 11px;
  line-height: 1.3;
  color: var(--canvas-ink-soft);
  font-style: italic;
}
.origin-items {
  padding: 12px 0 0;
}
.origin-items-label {
  font-size: 10px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--canvas-ink-soft);
  font-weight: 600;
}

.grid {
  display: grid;
  grid-template-columns: repeat(12, 1fr);
}
.cell {
  border-right: 1px solid var(--canvas-line);
  border-bottom: 1px solid var(--canvas-line);
  padding: 14px 16px 16px;
  min-height: 132px;
  position: relative;
  background: var(--canvas-paper);
}
.cell::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  background: var(--stage, var(--canvas-slate));
}
.band-diag {
  --stage: var(--canvas-slate);
}
.band-eval {
  --stage: var(--canvas-teal);
}
.cell-last {
  border-right: none;
}
.cell.help-open {
  z-index: 8;
}
.cell-help-btn {
  position: absolute;
  top: 10px;
  right: 10px;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  border: 1px solid var(--canvas-line);
  background: #fff;
  color: var(--canvas-teal);
  font-family: var(--sans);
  font-weight: 700;
  font-size: 13px;
  line-height: 1;
  cursor: pointer;
  z-index: 3;
  display: grid;
  place-content: center;
  padding: 0;
}
.cell-help-btn:hover,
.cell-help-btn[aria-expanded='true'] {
  border-color: var(--canvas-teal);
  background: #eef6f5;
}
.cell-help {
  position: absolute;
  top: 38px;
  right: 8px;
  width: min(340px, calc(100vw - 48px));
  max-height: min(420px, 70vh);
  overflow: auto;
  background: #fffcf7;
  border: 1px solid var(--canvas-line);
  box-shadow: 0 12px 28px rgba(18, 35, 46, 0.18);
  padding: 12px 14px;
  z-index: 9;
  border-radius: var(--r-xs);
}
.cell-help-head {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  margin-bottom: 8px;
}
.cell-help-num {
  font-family: var(--sans);
  font-weight: 700;
  font-size: 14px;
  color: var(--canvas-teal);
  line-height: 1.2;
}
.cell-help-head strong {
  display: block;
  font-size: 13px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--canvas-ink);
}
.cell-help-tag {
  display: block;
  margin-top: 2px;
  font-size: 11px;
  font-style: italic;
  color: var(--canvas-ink-soft);
}
.cell-help-answers {
  margin: 0 0 6px;
  font-size: 12px;
  line-height: 1.4;
  color: var(--canvas-ink);
}
.cell-help-pulls {
  margin: 0 0 8px;
  font-size: 11px;
  font-weight: 600;
  color: var(--canvas-teal);
}
.cell-help-note {
  margin: 0 0 10px;
  font-size: 11px;
  line-height: 1.4;
  color: var(--canvas-ink-soft);
  font-style: italic;
}
.cell-help-section {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--canvas-ink-soft);
  margin: 8px 0 4px;
}
.cell-help-questions,
.cell-help-examples {
  list-style: none;
  margin: 0;
  padding: 0;
}
.cell-help-questions li,
.cell-help-examples li {
  position: relative;
  padding: 0 0 6px 12px;
  font-size: 12px;
  line-height: 1.4;
  color: var(--canvas-ink);
}
.cell-help-questions li::before,
.cell-help-examples li::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0.45em;
  width: 5px;
  height: 5px;
  border-radius: 1px;
  background: var(--canvas-teal);
  transform: rotate(45deg);
}
.cell-help-alert {
  margin: 10px 0 0;
  padding: 8px 10px;
  background: #f8eee8;
  border-left: 3px solid var(--danger, #9c3b2e);
  font-size: 12px;
  line-height: 1.4;
  color: var(--canvas-ink);
}
.cell-help-alert strong {
  color: var(--danger, #9c3b2e);
}
.num {
  font-family: var(--sans);
  font-weight: 700;
  font-size: 12px;
  color: var(--stage, var(--canvas-slate));
}
.num-amber {
  color: var(--warn-text);
}
.cell-title {
  font-family: var(--sans);
  font-weight: 600;
  font-size: 14px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin: 2px 0 5px;
  padding-right: 28px;
}
.hint {
  font-size: 11px;
  color: var(--canvas-ink-soft);
  line-height: 1.35;
}
.write {
  margin-top: 9px;
  width: 100%;
  min-height: 72px;
  border: none;
  outline: none;
  resize: vertical;
  font-size: 13px;
  color: var(--canvas-ink);
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
  align-items: flex-start;
}
.item-input {
  flex: 1;
  min-width: 0;
  border: none;
  border-bottom: 1px dotted var(--canvas-line);
  background: transparent;
  font-size: 13px;
  color: var(--canvas-ink);
  font-family: inherit;
  padding: 4px 2px;
  outline: none;
  resize: none;
  overflow: hidden;
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.4;
  min-height: calc(1.4em + 8px);
  field-sizing: content;
}
.item-input:focus {
  border-bottom-color: var(--warn-text);
  background: #fffef9;
}
.item-row .item-remove {
  margin-top: 2px;
}
.item-remove {
  flex-shrink: 0;
  width: 24px;
  height: 24px;
  border: none;
  background: transparent;
  color: var(--canvas-ink-soft);
  cursor: pointer;
  font-size: 16px;
  line-height: 1;
  border-radius: var(--r-xs);
}
.item-remove:hover {
  color: var(--low);
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
  border: 1px dashed var(--canvas-line);
  border-radius: var(--r-xs);
  background: #fff;
  font-size: 12px;
  padding: 6px 8px;
  font-family: inherit;
  color: var(--canvas-ink);
  outline: none;
}
.item-add input:focus {
  border-color: var(--warn-text);
  border-style: solid;
}
.item-add button {
  flex-shrink: 0;
  width: 30px;
  border: 1px solid var(--canvas-line);
  border-radius: var(--r-xs);
  background: #fff;
  color: var(--canvas-ink);
  cursor: pointer;
  font-size: 16px;
  font-weight: 600;
}
.item-add button:hover {
  border-color: var(--warn-text);
  color: var(--warn-text);
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
  border: 1px solid var(--canvas-line);
  border-radius: 20px;
  padding: 3px 9px;
  color: var(--canvas-ink-soft);
  background: #fff;
  cursor: pointer;
  font-family: inherit;
}
.chip.active {
  border-color: var(--canvas-teal);
  background: #e1ebe9;
  color: var(--canvas-teal);
  font-weight: 600;
}
.decision {
  display: grid;
  grid-template-columns: 1.15fr 1fr;
}
.dec-left {
  padding: 16px 18px;
  border-right: 1px solid var(--canvas-line);
  border-bottom: 1px solid var(--canvas-line);
  position: relative;
}
.dec-left::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  background: var(--warn);
}
.scores {
  display: flex;
  gap: 26px;
  margin: 12px 0 6px;
  flex-wrap: wrap;
}
.score b {
  font-family: var(--sans);
  font-size: 11px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--canvas-ink-soft);
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
  border: 1.5px solid var(--canvas-slate);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: var(--canvas-ink-soft);
  font-family: var(--sans);
  font-weight: 600;
  background: #fff;
  cursor: pointer;
}
.dot.active {
  background: var(--warn);
  border-color: var(--warn-text);
  color: #fff;
}
.next {
  margin-top: 12px;
}
.matrix-wrap {
  padding: 16px 18px;
  border-bottom: 1px solid var(--canvas-line);
  display: flex;
  flex-direction: column;
}
.matrix-cap {
  font-family: var(--sans);
  font-weight: 600;
  font-size: 11px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--canvas-ink-soft);
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
  color: var(--canvas-ink-soft);
  text-align: center;
  grid-row: span 2;
  align-self: center;
}
.qx {
  font-size: 9px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--canvas-ink-soft);
  text-align: center;
  grid-column: 2 / 4;
}
.q {
  border-radius: var(--r-sm);
  padding: 8px 9px;
  font-size: 11px;
  line-height: 1.25;
  border: 1px solid var(--canvas-line);
  opacity: 0.72;
  transition: opacity 0.2s, box-shadow 0.2s;
}
.q.active {
  opacity: 1;
  box-shadow: 0 0 0 2px var(--canvas-ink);
}
.q b {
  display: block;
  font-family: var(--sans);
  font-size: 11px;
  margin-bottom: 2px;
}
.q-go {
  background: #e8f0e7;
  border-color: #bbd3b7;
}
.q-go b {
  color: var(--success-text);
}
.q-bet {
  background: var(--canvas-amber-tint);
  border-color: #e3ce9c;
}
.q-bet b {
  color: var(--warn-text);
}
.q-inc {
  background: var(--canvas-slate-tint);
  border-color: #cbd8db;
}
.q-inc b {
  color: var(--canvas-slate);
}
.q-avoid {
  background: #f1e1dd;
  border-color: #ddbcb4;
}
.q-avoid b {
  color: var(--low);
}
.sheet-footer {
  padding: 12px 30px 18px;
  display: flex;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px;
  font-size: 11px;
  color: var(--canvas-ink-soft);
}
.sheet-footer b {
  color: var(--warn-text);
  font-family: var(--sans);
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
    border-right: 1px solid var(--canvas-line);
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
