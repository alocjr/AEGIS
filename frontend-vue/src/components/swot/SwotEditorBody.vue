<script setup lang="ts">
import { RouterLink } from 'vue-router'
import { QUADRANT_HINTS } from '@/lib/swotModel'
import type { SwotEditor } from '@/composables/useSwotEditor'

const props = defineProps<{ editor: SwotEditor }>()
const {
  form, showMethod, showCatalog, openHelp, addingPillarFor, customPillarDraft,  CATALOG, pillarsByMaturityDimension, QUADRANTS, TOWS, VEREDITO_OPTIONS,  watchlistGroups, hasWatchlist, towsStep, verdictStep,  saveSwot, pillarLabel, toggleHelp, unassignedItems, toggleItemTows, onItemBlur,  removeItem, pillarsForQuadrant, itemsForPilar, getDraft, setDraft, onDraftKeydown,  addItem, openAddPillar, availablePillarsToAdd, addCanonicalPillar, addCustomPillar,  onInitiativeBlur, removeInitiative, addInitiative, setVereditoTipo
} = props.editor
</script>

<template>
      <section class="card method">
        <button type="button" class="method-toggle" @click="showMethod = !showMethod">
          <span>O método em uma página</span>
          <span>{{ showMethod ? '−' : '+' }}</span>
        </button>
        <div v-if="showMethod" class="method-body">
          <p>
            Dois instrumentos, uma jornada. O
            <RouterLink class="inline-link" to="/ai-maturity">Modelo de Maturidade</RouterLink>
            diagnostica a <strong>prontidão</strong> em quatro dimensões (escala 1–5; abrangência Básico /
            Completo / Complementar). A SWOT traduz esse diagnóstico em
            <strong>FOFA estratégica</strong> sob a ótica da estratégia organizacional de IA.
          </p>
          <p>
            O objeto é a <strong>organização</strong>. A ótica é a
            <strong>estratégia organizacional de IA</strong>. Um item só entra se afeta materialmente a
            capacidade de executar essa estratégia — use as respostas e médias do diagnóstico como evidência
            quando existirem.
          </p>

          <h3>Quatro dimensões · sete pilares</h3>
          <p class="method-note">
            Os pilares da SWOT aprofundam as mesmas dimensões do Modelo de Maturidade. Cada quadrante parte de
            um subconjunto (banco de itens); você pode acrescentar pilares canônicos ou custom.
          </p>
          <div class="dim-groups">
            <div v-for="dim in pillarsByMaturityDimension" :key="dim.id" class="dim-group">
              <div class="dim-group-head">
                <strong>{{ dim.name }}</strong>
                <span>{{ dim.brief }}</span>
              </div>
              <div class="pillarq">
                <div v-for="p in dim.pillars" :key="p.id">
                  <b>{{ p.name }}.</b> <i>{{ p.q }}</i>
                </div>
              </div>
            </div>
          </div>

          <h3>Duas regras</h3>
          <ul class="bullets">
            <li>
              <strong>Locus disciplinado.</strong> Forças e Fraquezas são internas (capacidade sob controle da
              organização — tipicamente o grosso do diagnóstico de maturidade). Oportunidades e Ameaças são do
              ambiente (regulação, mercado, fornecedores, ritmo externo).
            </li>
            <li>
              <strong>Baseado em evidência.</strong> Cada item ancorado em fato, métrica ou nível observado no
              diagnóstico (escala 1–5) — priorize por impacto (ideal: 2–3 por quadrante).
            </li>
            <li>
              <strong>Nota 3 fica à parte.</strong> Respostas intermediárias do diagnóstico vão para
              <em>Pontos de Atenção</em> (watchlist) — não entram no SWOT nem no TOWS; acompanhe no próximo ciclo.
            </li>
          </ul>
          <ol class="steps">
            <li>
              <strong>Declare a ótica.</strong> Estratégia de IA em uma frase — o mesmo norte que o diagnóstico
              de maturidade avalia.
            </li>
            <li>
              <strong>Varra os quadrantes</strong> pelas quatro dimensões (pilares do banco de itens de cada
              quadrante).
            </li>
            <li><strong>Aplique o crivo.</strong> Descarte o que não afeta a estratégia.</li>
            <li>
              <strong>Priorize.</strong> Fique com os 2–3 itens mais fortes de cada quadrante (impacto ×
              viabilidade ou probabilidade, na mesma escala 1–5).
            </li>
            <li>
              <strong>Revise os Pontos de Atenção</strong> (nota 3) e cruze o TOWS → iniciativas → veredito.
            </li>
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
          @blur="saveSwot()"
        />
      </section>

      <section class="matrix-block">
        <div class="section-head">
          <div class="eyebrow">2 · Matriz</div>
          <h2>Interno × Externo</h2>
          <p class="hint">
            No interno (Forças / Fraquezas), o repertório de partida usa as quatro dimensões do Modelo de
            Maturidade. No externo, o foco é ambiente. Inclua outro pilar se precisar. Priorize 2–3 itens por
            quadrante. Marque o checkbox dos itens que entram no cruzamento TOWS. Toque no ? para o repertório.
          </p>
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
                Repertório de partida alinhado às dimensões do Modelo de Maturidade — estímulo, não checklist.
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

            <div
              v-if="unassignedItems(q.field).length"
              class="pillar-block pillar-orphan"
            >
              <div class="pillar-label">Sem pilar</div>
              <ul class="item-list">
                <li
                  v-for="{ item, index } in unassignedItems(q.field)"
                  :key="item.id || q.field + '-u-' + index"
                  class="item-row"
                  :class="{ 'tows-off': !item.tows }"
                >
                  <label class="item-tows" :title="item.tows ? 'No TOWS — clique para excluir' : 'Fora do TOWS — clique para incluir'">
                    <input
                      type="checkbox"
                      :checked="item.tows"
                      @change="toggleItemTows(q.field, index)"
                    />
                    <span class="sr-only">Incluir no TOWS</span>
                  </label>
                  <input
                    :value="item.texto"
                    class="item-input"
                    :title="item.texto || undefined"
                    maxlength="500"
                    @blur="onItemBlur(q.field, index, $event)"
                  />
                  <button type="button" class="item-remove" title="Remover" @click="removeItem(q.field, index)">
                    ×
                  </button>
                </li>
              </ul>
            </div>

            <div
              v-for="p in pillarsForQuadrant(q.field)"
              :key="q.field + p.id"
              class="pillar-block"
            >
              <div class="pillar-label" :title="p.q || undefined">{{ p.name }}</div>
              <ul class="item-list">
                <li
                  v-for="{ item, index } in itemsForPilar(q.field, p.id)"
                  :key="item.id || q.field + p.id + index"
                  class="item-row"
                  :class="{ 'tows-off': !item.tows }"
                >
                  <label class="item-tows" :title="item.tows ? 'No TOWS — clique para excluir' : 'Fora do TOWS — clique para incluir'">
                    <input
                      type="checkbox"
                      :checked="item.tows"
                      @change="toggleItemTows(q.field, index)"
                    />
                    <span class="sr-only">Incluir no TOWS</span>
                  </label>
                  <input
                    :value="item.texto"
                    class="item-input"
                    :title="item.texto || undefined"
                    maxlength="500"
                    @blur="onItemBlur(q.field, index, $event)"
                  />
                  <button type="button" class="item-remove" title="Remover" @click="removeItem(q.field, index)">
                    ×
                  </button>
                </li>
              </ul>
              <div class="item-add">
                <input
                  :value="getDraft(q.field, p.id)"
                  type="text"
                  maxlength="500"
                  :placeholder="`Adicionar em ${p.name}…`"
                  @input="setDraft(q.field, p.id, ($event.target as HTMLInputElement).value)"
                  @keydown="onDraftKeydown(q.field, p.id, $event)"
                />
                <button type="button" @click="addItem(q.field, p.id)">+</button>
              </div>
            </div>

            <div class="pillar-add">
              <button
                type="button"
                class="pillar-add-toggle"
                :aria-expanded="addingPillarFor === q.field"
                @click="openAddPillar(q.field)"
              >
                {{ addingPillarFor === q.field ? 'Cancelar' : '+ Incluir pilar' }}
              </button>
              <div v-if="addingPillarFor === q.field" class="pillar-add-panel">
                <p class="pillar-add-hint">Escolha um pilar canônico ou crie um novo para este quadrante.</p>
                <div v-if="availablePillarsToAdd(q.field).length" class="pillar-add-choices">
                  <button
                    v-for="opt in availablePillarsToAdd(q.field)"
                    :key="opt.id"
                    type="button"
                    class="pillar-choice"
                    @click="addCanonicalPillar(q.field, opt.id)"
                  >
                    {{ opt.name }}
                  </button>
                </div>
                <div class="pillar-add-custom">
                  <input
                    v-model="customPillarDraft"
                    type="text"
                    maxlength="40"
                    placeholder="Novo pilar (ex.: Mercado)"
                    @keydown.enter.prevent="addCustomPillar(q.field)"
                  />
                  <button type="button" @click="addCustomPillar(q.field)">Criar</button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section v-if="hasWatchlist" class="watchlist-block">
        <div class="section-head">
          <div class="eyebrow">3 · Pontos de Atenção</div>
          <h2>Watchlist · nota 3</h2>
          <p class="hint">
            Áreas em maturação vindas do Modelo de Maturidade. Ficam fora do SWOT e do TOWS — monitore no próximo
            ciclo; podem virar Força ou Fraqueza.
          </p>
        </div>
        <div class="watchlist">
          <div v-for="group in watchlistGroups" :key="group.dimensao" class="watchlist-group">
            <div class="watchlist-dim">{{ group.dimensao }}</div>
            <ul class="watchlist-list">
              <li v-for="item in group.items" :key="item.id || item.texto" class="watchlist-item">
                <div class="watchlist-meta">
                  <span v-if="item.id" class="watchlist-code">{{ item.id }}</span>
                  <span v-if="item.pilar" class="watchlist-pillar">{{ pillarLabel(item.pilar) }}</span>
                  <span v-if="item.nota != null" class="watchlist-nota">N{{ item.nota }}</span>
                </div>
                <p class="watchlist-text">{{ item.texto }}</p>
                <p v-if="item.evidencia" class="watchlist-evidence">{{ item.evidencia }}</p>
              </li>
            </ul>
          </div>
        </div>
      </section>

      <section class="tows-block">
        <div class="section-head">
          <div class="eyebrow">{{ towsStep }} · Cruzamento TOWS</div>
          <h2>Do diagnóstico à decisão</h2>
          <p class="hint">
            Gerado só com os itens marcados na matriz (F×O, F×A, f×O, f×A). Cada cruzamento vira uma iniciativa.
            Comece pelo f × A — é onde a estratégia pode quebrar.
          </p>
        </div>
        <div class="tows">
          <div v-for="t in TOWS" :key="t.field" class="tows-cell" :class="{ hard: t.hard }">
            <span class="k">{{ t.key }}</span>
            <span class="qz">{{ t.quest }}</span>
            <p class="thint">{{ t.hint }}</p>
            <div v-for="(row, idx) in form[t.field]" :key="row.id || t.field + idx" class="init-row">
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
        <div class="eyebrow gold">{{ verdictStep }} · Veredito</div>
        <p class="verdict-lead">
          À luz das forças/fraquezas internas (e do nível de maturidade observado), a estratégia se sustenta,
          precisa de uma fase de fundação, ou deve ser repensada?
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
          @blur="saveSwot()"
        />
        <textarea
          v-model="form.veredito_texto"
          class="verdict-text"
          rows="5"
          maxlength="8000"
          placeholder="Conclusão e recomendação…"
          @blur="saveSwot()"
        />
      </section>
</template>

<style scoped>
.card {
  background: var(--ivory-2);
  border: 1px solid var(--line);
  border-radius: var(--r-xs);
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
.method-note {
  margin: 0 0 0.75em;
  color: var(--muted);
  font-size: 13px;
  line-height: 1.5;
}
.dim-groups {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin: 0.5em 0 1em;
}
.dim-group {
  background: #fff;
  border: 1px solid var(--line);
  border-radius: var(--r-xs);
  padding: 12px 14px;
}
.dim-group-head {
  display: flex;
  flex-direction: column;
  gap: 2px;
  margin-bottom: 4px;
}
.dim-group-head strong {
  color: var(--navy);
  font-size: 0.92rem;
}
.dim-group-head span {
  color: var(--muted);
  font-size: 12px;
  line-height: 1.4;
}
.dim-group .pillarq {
  margin: 0.2em 0 0;
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
  font-size: 1.4rem;
  color: var(--gold);
  line-height: 1;
}
.q-help-letter.neg {
  color: var(--oxblood);
}
.q-help-locus {
  display: block;
  font-size: 0.68rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--muted);
  font-weight: 600;
  margin-top: 2px;
}
.q-help-note {
  margin: 0 0 10px;
  font-size: 0.78rem;
  color: var(--muted);
  line-height: 1.4;
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
  color: var(--gold-light);
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
.pillar-block {
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px solid rgba(198, 161, 91, 0.18);
}
.pillar-block:first-of-type {
  margin-top: 4px;
}
.pillar-orphan {
  background: #faf7f0;
  margin: 0 -6px 4px;
  padding: 8px 6px 10px;
  border-top: none;
  border-radius: 2px;
}
.pillar-label {
  font-size: 0.66rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  font-weight: 700;
  color: var(--gold);
  margin-bottom: 5px;
}
.q.neg .pillar-label {
  color: var(--oxblood);
}
.pillar-orphan .pillar-label {
  color: var(--muted);
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
.item-row.tows-off .item-input {
  color: var(--muted);
  opacity: 0.72;
}
.item-tows {
  flex-shrink: 0;
  display: grid;
  place-content: center;
  width: 22px;
  height: 22px;
  margin: 0;
  cursor: pointer;
}
.item-tows input {
  width: 14px;
  height: 14px;
  margin: 0;
  accent-color: var(--gold);
  cursor: pointer;
}
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
.item-input {
  flex: 1;
  min-width: 0;
  border: none;
  border-bottom: 1px dotted var(--line);
  background: transparent;
  font-size: 13px;
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
  border-radius: var(--r-xs);
}
.item-remove:hover {
  color: var(--oxblood);
  background: #f1e1dd;
}
.item-add {
  display: flex;
  gap: 6px;
  margin-top: 6px;
}
.item-add input {
  flex: 1;
  min-width: 0;
  border: 1px dashed var(--line);
  border-radius: 3px;
  background: #fff;
  font-size: 12px;
  padding: 5px 7px;
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
  width: 28px;
}
.item-add button:hover,
.add-init:hover {
  border-color: var(--gold);
  color: var(--gold);
}
.pillar-add {
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px dashed var(--line);
}
.pillar-add-toggle {
  border: none;
  background: transparent;
  color: var(--gold);
  font-size: 0.78rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  cursor: pointer;
  padding: 0;
  font-family: inherit;
}
.q.neg .pillar-add-toggle {
  color: var(--oxblood);
}
.pillar-add-toggle:hover {
  text-decoration: underline;
}
.pillar-add-panel {
  margin-top: 8px;
  padding: 10px;
  background: var(--ivory-2);
  border: 1px solid var(--line);
}
.pillar-add-hint {
  margin: 0 0 8px;
  font-size: 0.75rem;
  color: var(--muted);
  line-height: 1.35;
}
.pillar-add-choices {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 8px;
}
.pillar-choice {
  border: 1px solid var(--line);
  background: #fff;
  color: var(--navy);
  font-size: 0.72rem;
  font-weight: 600;
  padding: 4px 8px;
  cursor: pointer;
  font-family: inherit;
  border-radius: 2px;
}
.pillar-choice:hover {
  border-color: var(--gold);
  color: var(--gold);
}
.pillar-add-custom {
  display: flex;
  gap: 6px;
}
.pillar-add-custom input {
  flex: 1;
  border: 1px solid var(--line);
  background: #fff;
  padding: 6px 8px;
  font-size: 0.82rem;
  font-family: inherit;
  outline: none;
}
.pillar-add-custom input:focus {
  border-color: var(--gold);
}
.pillar-add-custom button {
  border: 1px solid var(--navy);
  background: var(--navy);
  color: #fff;
  font-size: 0.72rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  padding: 0 10px;
  cursor: pointer;
  font-family: inherit;
}
.pillar-add-custom button:hover {
  background: #16243f;
}
.add-init {
  margin-top: 8px;
  width: 100%;
  padding: 7px 10px;
  font-size: 12px;
}
.watchlist-block {
  margin-bottom: 28px;
}
.watchlist {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.watchlist-group {
  border: 1px solid var(--line);
  background: #fff;
  padding: 14px 16px 12px;
}
.watchlist-dim {
  font-size: 0.68rem;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  font-weight: 700;
  color: var(--gold);
  margin-bottom: 10px;
}
.watchlist-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.watchlist-item {
  border-top: 1px solid rgba(14, 27, 51, 0.08);
  padding-top: 10px;
}
.watchlist-item:first-child {
  border-top: none;
  padding-top: 0;
}
.watchlist-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  margin-bottom: 4px;
}
.watchlist-code {
  font-family: var(--serif);
  font-weight: 700;
  font-size: 0.78rem;
  letter-spacing: 0.04em;
  color: var(--navy);
}
.watchlist-pillar,
.watchlist-nota {
  font-size: 0.68rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--muted);
  font-weight: 600;
}
.watchlist-nota {
  color: var(--oxblood);
}
.watchlist-text {
  margin: 0;
  color: var(--navy);
  font-size: 0.92rem;
  line-height: 1.4;
}
.watchlist-evidence {
  margin: 4px 0 0;
  color: var(--muted);
  font-size: 0.8rem;
  line-height: 1.4;
  font-style: italic;
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
  font-size: 0.85rem;
  margin: 0.2em 0 0.75em;
  line-height: 1.4;
  color: #3a3f49;
}
.init-row {
  margin-bottom: 8px;
}
.init-acao {
  width: 100%;
  border: 1px solid var(--line);
  border-radius: 3px;
  font-size: 13px;
  padding: 6px 8px;
  font-family: inherit;
  outline: none;
}
.init-acao:focus {
  border-color: var(--gold);
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
  color: var(--gold-light);
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
  .header-actions {
    align-items: flex-start;
    flex-direction: row;
    flex-wrap: wrap;
  }
}
</style>
