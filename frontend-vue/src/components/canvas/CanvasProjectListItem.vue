<script setup lang="ts">
import { RouterLink } from 'vue-router'
import {
  CANVAS_PRIORIDADES,
  CANVAS_MESES,
  periodicidadeLabel,
  type CanvasProjectSummary,
  type CanvasQuadrant,
} from '@/api/canvasProjects'

defineProps<{
  item: CanvasProjectSummary
  approvingPortfolio?: boolean
}>()

defineEmits<{
  prioridade: [ev: Event]
  mes: [ev: Event]
  approve: [ev: Event]
  approvePortfolio: [ev: Event]
  delete: [ev: Event]
}>()

const QUADRANT_LABEL: Record<Exclude<CanvasQuadrant, null>, string> = {
  ganho_rapido: 'Ganho rápido',
  aposta_estrategica: 'Aposta estratégica',
  incremental: 'Incremental',
  evitar: 'Evitar · vaidade',
}

function formatDate(iso: string | null): string {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString('pt-BR', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return iso
  }
}

function formatInicioReal(iso: string): string {
  if (!iso) return ''
  const [y, m, d] = iso.split('-')
  if (!y || !m || !d) return iso
  return `${d}/${m}/${y}`
}
</script>

<template>
  <li class="list-item">
    <RouterLink :to="`/projetos/${item.id}`" class="list-link">
      <div class="list-main">
        <span class="list-title">{{ item.title || 'Novo projeto' }}</span>
        <dl class="list-fields">
          <div class="list-field">
            <dt>Área de negócio</dt>
            <dd>{{ item.area_negocio || '—' }}</dd>
          </div>
          <div class="list-field">
            <dt>Responsável</dt>
            <dd>{{ item.responsavel || '—' }}</dd>
          </div>
          <div class="list-field">
            <dt>Data</dt>
            <dd>{{ item.data || '—' }}</dd>
          </div>
          <div class="list-field list-field-wide">
            <dt>Objetivo estratégico da área</dt>
            <dd>{{ item.objetivo_estrategico || '—' }}</dd>
          </div>
          <div class="list-field list-field-wide">
            <dt>Próximo passo concreto</dt>
            <dd>{{ item.proximo_passo || '—' }}</dd>
          </div>
        </dl>
        <div class="list-foot">
          <span v-if="item.quadrant" class="list-quad" :data-q="item.quadrant">
            {{ QUADRANT_LABEL[item.quadrant] }}
          </span>
          <span class="list-meta">Atualizado {{ formatDate(item.updated_at) }}</span>
        </div>
      </div>
      <span class="list-arrow">Abrir canvas →</span>
    </RouterLink>
    <div class="list-exec" @click.stop>
      <label>
        <span>Prioridade</span>
        <select
          :value="item.prioridade || 'P4'"
          :aria-label="'Prioridade de ' + (item.title || 'projeto')"
          @change="$emit('prioridade', $event)"
        >
          <option v-for="p in CANVAS_PRIORIDADES" :key="p.id" :value="p.id">{{ p.label }}</option>
        </select>
      </label>
      <label>
        <span>Início</span>
        <select
          :value="item.mes_inicio || ''"
          :aria-label="'Mês de início de ' + (item.title || 'projeto')"
          @change="$emit('mes', $event)"
        >
          <option value="">Mês</option>
          <option v-for="m in CANVAS_MESES" :key="m.id" :value="m.id">{{ m.label }}</option>
        </select>
      </label>
      <button
        v-if="!item.projeto_aprovado"
        type="button"
        class="btn-approve-proj"
        @click="$emit('approve', $event)"
      >
        Aprovar projeto
      </button>
      <div v-else class="approved-meta">
        <span class="approved-flag">Aprovado</span>
        <span>
          {{ periodicidadeLabel(item.periodicidade) }}
          <template v-if="item.data_inicio_real"> · {{ formatInicioReal(item.data_inicio_real) }}</template>
        </span>
        <span v-if="item.aprovacao_comentario" class="approved-who" :title="item.aprovacao_comentario">
          {{ item.aprovacao_comentario }}
        </span>
        <button type="button" class="link-edit" @click="$emit('approve', $event)">Editar</button>
      </div>
    </div>
    <div class="list-actions">
      <RouterLink
        v-if="item.status === 'aprovado_portfolio' && item.ai_system_id"
        :to="`/governanca/sistemas/${item.ai_system_id}`"
        class="badge-portfolio"
        title="Ver na Governança de IA"
        @click.stop
      >
        No portfólio ✓
      </RouterLink>
      <button
        v-else
        type="button"
        class="btn-approve"
        :disabled="approvingPortfolio"
        @click="$emit('approvePortfolio', $event)"
      >
        {{ approvingPortfolio ? 'Aprovando…' : 'Aprovar para portfólio' }}
      </button>
      <button type="button" class="btn-del" title="Excluir projeto" @click="$emit('delete', $event)">
        Excluir
      </button>
    </div>
  </li>
</template>

<style scoped>
.list-item {
  display: flex;
  align-items: stretch;
  gap: 0;
  background: var(--wh);
  border: 1px solid var(--bd);
  border-radius: var(--r-lg);
  overflow: visible;
}
.list-exec {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 8px;
  padding: 12px 14px;
  border-left: 1px solid var(--bd);
  background: #faf9f6;
  min-width: 196px;
}
.list-exec label {
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--k5);
}
.list-exec select {
  font-family: inherit;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0;
  text-transform: none;
  color: var(--k0);
  border: 1px solid var(--bd);
  border-radius: var(--r-md);
  padding: 5px 6px;
  background: #fff;
  max-width: 200px;
}
.btn-approve-proj {
  border: 1px solid var(--k0);
  background: var(--k0);
  color: var(--wh);
  font-family: inherit;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  padding: 7px 8px;
  border-radius: var(--r-md);
  cursor: pointer;
}
.btn-approve-proj:hover {
  opacity: 0.92;
}
.approved-meta {
  display: flex;
  flex-direction: column;
  gap: 3px;
  font-size: 11px;
  color: var(--k4);
  line-height: 1.35;
  max-width: 200px;
}
.approved-flag {
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #2f6e4a;
}
.approved-who {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  color: var(--k5);
}
.link-edit {
  align-self: flex-start;
  border: none;
  background: none;
  padding: 0;
  font: inherit;
  font-size: 11px;
  color: var(--k0);
  text-decoration: underline;
  cursor: pointer;
}
.list-link {
  flex: 1;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 16px 18px;
  text-decoration: none;
  color: inherit;
  min-width: 0;
}
.list-link:hover {
  background: rgba(0, 0, 0, 0.02);
}
.list-main {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-width: 0;
  flex: 1;
}
.list-title {
  font-weight: 600;
  font-size: 16px;
  color: var(--k0);
}
.list-fields {
  margin: 0;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px 14px;
}
.list-field {
  min-width: 0;
}
.list-field-wide {
  grid-column: 1 / -1;
}
.list-field dt {
  margin: 0;
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--k5);
}
.list-field dd {
  margin: 3px 0 0;
  font-size: 13px;
  color: var(--k0);
  line-height: 1.4;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
.list-foot {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 12px;
}
.list-meta {
  font-size: 12px;
  color: var(--k5);
}
.list-quad {
  display: inline-flex;
  width: fit-content;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  padding: 3px 8px;
  border-radius: var(--r-pill);
  border: 1px solid var(--bd);
  color: var(--k3);
}
.list-quad[data-q='ganho_rapido'] {
  background: #e8f0e7;
  border-color: #bbd3b7;
  color: #2f6e4a;
}
.list-quad[data-q='aposta_estrategica'] {
  background: #f3e7cc;
  border-color: #e3ce9c;
  color: #c48a26;
}
.list-quad[data-q='incremental'] {
  background: #e4ecee;
  border-color: #cbd8db;
  color: #5b7a86;
}
.list-quad[data-q='evitar'] {
  background: #f1e1dd;
  border-color: #ddbcb4;
  color: #9c3b2e;
}
.list-arrow {
  font-size: 13px;
  color: var(--k5);
  white-space: nowrap;
  margin-top: 2px;
}
.list-actions {
  display: flex;
  align-items: center;
}
.btn-del {
  border: none;
  background: transparent;
  color: #8f2b2b;
  padding: 0 14px;
  font-size: 12px;
  cursor: pointer;
  border-left: 1px solid var(--bd);
}
.btn-del:hover {
  background: #faf2f1;
}
.btn-approve {
  border: none;
  background: transparent;
  color: var(--k4);
  padding: 0 14px;
  font-size: 12px;
  cursor: pointer;
  border-left: 1px solid var(--bd);
  white-space: nowrap;
}
.btn-approve:hover:not(:disabled) {
  background: var(--k9);
}
.btn-approve:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}
.badge-portfolio {
  padding: 4px 14px;
  font-size: 12px;
  font-weight: 600;
  color: var(--k0);
  background: var(--golddim);
  border-left: 1px solid var(--bd);
  text-decoration: none;
  white-space: nowrap;
  display: flex;
  align-items: center;
}
.badge-portfolio:hover {
  background: var(--goldbd);
}
@media (max-width: 640px) {
  .list-fields {
    grid-template-columns: 1fr;
  }
  .list-arrow {
    display: none;
  }
  .list-item {
    flex-wrap: wrap;
  }
  .list-exec {
    flex-direction: row;
    flex: 1 1 100%;
    border-left: none;
    border-top: 1px solid var(--bd);
    min-width: 0;
  }
  .list-exec select {
    max-width: none;
    width: 100%;
  }
}
</style>
