<script setup lang="ts">
import { RouterLink } from 'vue-router'
import type { OkrCycleEditor } from '@/composables/useOkrCycleEditor'

const props = defineProps<{ editor: OkrCycleEditor }>()
const {
  cycle, form, MAX_OBJECTIVES, MAX_KRS, DRAFT_HINT, TOWS_GROUPS, STATUS_LABEL,
  swotList, swot, swotLoading, swotError, originOpen,
  onTipoChange, addObjective, removeObjective, addKr, removeKr,
  toggleTows, isTowsSelected, onSelectSwot, onActivate, onArchive,
  krProgress, isDraftObjective, crossingLabel, selectedInitiatives,
  activating, archiving, lifecycleError,
} = props.editor
</script>

<template>
  <div v-if="cycle">
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
  </div>
</template>

<style scoped>
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
  color: var(--k3);
}
.head-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
  color: var(--k3);
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
  color: var(--warn-text);
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
  color: var(--k3);
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
  color: var(--k3);
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
  color: var(--k3);
}
.origin-count.muted {
  color: var(--k3);
}
.origin-caret {
  margin-left: auto;
  font-size: 16px;
  color: var(--k3);
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
  color: var(--k3);
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
  color: var(--k3);
}
.origin-link {
  color: var(--k0);
}
.origin-select {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
  color: var(--k3);
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
  color: var(--k3);
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
  color: var(--k3);
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
  color: var(--k3);
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
  color: var(--k3);
}
.btn-add-kr {
  align-self: flex-start;
  border: 1px dashed var(--bd);
  background: transparent;
  border-radius: var(--r-sm);
  padding: 6px 12px;
  font-size: 12px;
  color: var(--k3);
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
  color: var(--k3);
  cursor: pointer;
}
.btn-add-objective:hover:not(:disabled) {
  color: var(--k0);
  border-color: var(--k0);
}
</style>
