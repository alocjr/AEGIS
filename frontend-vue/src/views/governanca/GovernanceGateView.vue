<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ApiError } from '@/api/client'
import { getGate, updateGateItem, decideGate, listOrganizationMembers } from '@/api/governance'
import type { Gate, ChecklistItem, ChecklistBloco, ChecklistItemStatus, GateResultado, OrganizationMember } from '@/api/governance'

const route = useRoute()
const gateId = String(route.params.id)

const loading = ref(true)
const loadError = ref<string | null>(null)
const gate = ref<Gate | null>(null)
const members = ref<OrganizationMember[]>([])

const BLOCO_LABEL: Record<ChecklistBloco, string> = {
  A: 'A · Dados/LGPD',
  B: 'B · Fornecedor',
  C: 'C · Segurança/Agente',
  D: 'D · Equidade/AIA',
  E: 'E · Valor/Operação',
  F: 'F · Derivados da SWOT',
}
const BLOCO_ORDER: ChecklistBloco[] = ['A', 'B', 'C', 'D', 'E', 'F']
const STATUS_OPTIONS: ChecklistItemStatus[] = ['pendente', 'aprovado', 'reprovado', 'nao_aplicavel']

const isDecided = computed(() => !!gate.value?.decisao)

const groupedChecklist = computed(() => {
  const groups = new Map<ChecklistBloco, ChecklistItem[]>()
  for (const item of gate.value?.checklist ?? []) {
    const list = groups.get(item.bloco) ?? []
    list.push(item)
    groups.set(item.bloco, list)
  }
  return BLOCO_ORDER.filter((b) => groups.has(b)).map((b) => ({ bloco: b, items: groups.get(b)! }))
})

const openCriticalItems = computed(() =>
  (gate.value?.checklist ?? []).filter(
    (item) => item.critico && item.status !== 'aprovado' && item.status !== 'nao_aplicavel'
  )
)

const admins = computed(() => members.value.filter((m) => m.is_admin))

// ——— edição de item ———

const itemSaving = ref<string | null>(null)
const itemError = ref<string | null>(null)

async function saveItem(item: ChecklistItem, status: ChecklistItemStatus) {
  if (!gate.value || isDecided.value) return
  if (status === 'nao_aplicavel' && item.critico && !item.evidencia.descricao.trim()) {
    itemError.value = `Item crítico ${item.item_id}: marque "não aplicável" só depois de preencher a justificativa na evidência.`
    return
  }
  itemSaving.value = item.item_id
  itemError.value = null
  try {
    gate.value = await updateGateItem(gateId, item.item_id, { status, evidencia: item.evidencia })
  } catch (e) {
    itemError.value = e instanceof ApiError ? e.message : e instanceof Error ? e.message : 'Erro ao salvar item.'
  } finally {
    itemSaving.value = null
  }
}

async function saveEvidencia(item: ChecklistItem) {
  if (!gate.value || isDecided.value) return
  itemSaving.value = item.item_id
  itemError.value = null
  try {
    gate.value = await updateGateItem(gateId, item.item_id, { evidencia: item.evidencia })
  } catch (e) {
    itemError.value = e instanceof ApiError ? e.message : e instanceof Error ? e.message : 'Erro ao salvar evidência.'
  } finally {
    itemSaving.value = null
  }
}

// ——— decisão ———

const decisionForm = ref({
  resultado: 'go' as GateResultado,
  aprovador_user_id: '',
  consultados_user_ids: [] as string[],
  justificativa: '',
  condicoes: [] as { texto: string; prazo: string; dono_user_id: string }[],
})
const decisionSaving = ref(false)
const decisionError = ref<string | null>(null)

function addCondicao() {
  decisionForm.value.condicoes.push({ texto: '', prazo: '', dono_user_id: '' })
}
function removeCondicao(idx: number) {
  decisionForm.value.condicoes.splice(idx, 1)
}

const goBlockedReason = computed(() => {
  if (decisionForm.value.resultado !== 'go') return null
  if (openCriticalItems.value.length > 0) {
    return `${openCriticalItems.value.length} item(ns) crítico(s) ainda não aprovado(s)/marcado(s) como não aplicável: ${openCriticalItems.value.map((i) => i.item_id).join(', ')}.`
  }
  return null
})

async function submitDecision() {
  if (!gate.value) return
  decisionSaving.value = true
  decisionError.value = null
  try {
    const f = decisionForm.value
    gate.value = await decideGate(gateId, {
      decisao: {
        resultado: f.resultado,
        aprovador_user_id: f.aprovador_user_id,
        consultados_user_ids: f.consultados_user_ids,
        justificativa: f.justificativa,
        condicoes: f.resultado === 'go_condicional' ? f.condicoes : [],
      },
    })
  } catch (e) {
    decisionError.value = e instanceof ApiError ? e.message : e instanceof Error ? e.message : 'Erro ao registrar decisão.'
  } finally {
    decisionSaving.value = false
  }
}

onMounted(async () => {
  try {
    const [g, m] = await Promise.all([getGate(gateId), listOrganizationMembers()])
    gate.value = g
    members.value = m.items
  } catch (e) {
    loadError.value = e instanceof ApiError ? e.message : e instanceof Error ? e.message : 'Erro ao carregar gate.'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="gate-page">
    <div v-if="loading" class="loading">Carregando...</div>
    <div v-else-if="loadError" class="error-msg">{{ loadError }}</div>
    <template v-else-if="gate">
      <header class="page-header">
        <RouterLink :to="`/governanca/sistemas/${gate.system_id}`" class="back-link">← Sistema</RouterLink>
        <h1 class="page-title">Gate — ciclo {{ gate.revision }}</h1>
        <p v-if="isDecided" class="page-sub decided">
          Decidido: <strong>{{ gate.decisao?.resultado }}</strong>
        </p>
        <p v-else class="page-sub">Em andamento — preencha o checklist e registre a decisão.</p>
      </header>

      <div class="gate-layout">
        <div class="checklist-col">
          <div v-if="itemError" class="error-msg">{{ itemError }}</div>
          <section v-for="group in groupedChecklist" :key="group.bloco" class="bloco-group">
            <h2 class="bloco-title">{{ BLOCO_LABEL[group.bloco] }}</h2>
            <article v-for="item in group.items" :key="item.item_id" class="checklist-item">
              <div class="item-head">
                <span class="item-id">{{ item.item_id }}</span>
                <span class="item-texto">{{ item.texto }}</span>
                <span v-if="item.critico" class="badge-critico">Crítico</span>
                <span class="badge-origem" :class="item.origem.tipo">
                  {{ item.origem.tipo === 'swot' ? 'Derivado da SWOT' : 'Template' }}
                </span>
              </div>
              <div class="item-body">
                <select
                  :value="item.status"
                  class="input status-select"
                  :disabled="isDecided || itemSaving === item.item_id"
                  @change="saveItem(item, ($event.target as HTMLSelectElement).value as ChecklistItemStatus)"
                >
                  <option v-for="opt in STATUS_OPTIONS" :key="opt" :value="opt">{{ opt }}</option>
                </select>
                <textarea
                  v-model="item.evidencia.descricao"
                  class="input evidencia-input"
                  rows="1"
                  placeholder="Evidência / justificativa"
                  :disabled="isDecided"
                  @blur="saveEvidencia(item)"
                />
              </div>
            </article>
          </section>
        </div>

        <aside class="decision-col">
          <h2 class="section-title">Decisão</h2>
          <div v-if="isDecided" class="decision-readonly">
            <p><strong>Resultado:</strong> {{ gate.decisao?.resultado }}</p>
            <p><strong>Justificativa:</strong> {{ gate.decisao?.justificativa || '—' }}</p>
            <p v-if="gate.decisao?.condicoes.length">
              <strong>Condições:</strong>
              <ul>
                <li v-for="(c, i) in gate.decisao?.condicoes" :key="i">{{ c.texto }} (prazo: {{ c.prazo || '—' }})</li>
              </ul>
            </p>
          </div>
          <div v-else>
            <div v-if="decisionError" class="error-msg">{{ decisionError }}</div>
            <div class="form-group">
              <label>Resultado</label>
              <select v-model="decisionForm.resultado" class="input">
                <option value="go">Go</option>
                <option value="go_condicional">Go condicional</option>
                <option value="no_go">No-Go</option>
              </select>
            </div>
            <div class="form-group">
              <label>Aprovador (precisa ser admin)</label>
              <select v-model="decisionForm.aprovador_user_id" class="input">
                <option value="">Selecione…</option>
                <option v-for="m in admins" :key="m.id" :value="m.id">{{ m.name }}</option>
              </select>
            </div>
            <div class="form-group">
              <label>Consultados</label>
              <select v-model="decisionForm.consultados_user_ids" class="input" multiple size="4">
                <option v-for="m in members" :key="m.id" :value="m.id">{{ m.name }}</option>
              </select>
            </div>
            <div v-if="decisionForm.resultado === 'go_condicional'" class="condicoes-block">
              <label>Condições</label>
              <div v-for="(c, idx) in decisionForm.condicoes" :key="idx" class="condicao-row">
                <input v-model="c.texto" type="text" class="input" placeholder="Condição" />
                <input v-model="c.prazo" type="text" class="input condicao-prazo" placeholder="Prazo" />
                <select v-model="c.dono_user_id" class="input condicao-dono">
                  <option value="">Dono…</option>
                  <option v-for="m in members" :key="m.id" :value="m.id">{{ m.name }}</option>
                </select>
                <button type="button" class="remove-btn" @click="removeCondicao(idx)">×</button>
              </div>
              <button type="button" class="link-btn" @click="addCondicao">+ Adicionar condição</button>
            </div>
            <div class="form-group">
              <label>Justificativa</label>
              <textarea v-model="decisionForm.justificativa" rows="3" class="input" />
            </div>

            <div v-if="goBlockedReason" class="go-blocked-reason">{{ goBlockedReason }}</div>

            <button
              type="button"
              class="btn-primary"
              :disabled="decisionSaving || !decisionForm.aprovador_user_id"
              @click="submitDecision"
            >
              {{ decisionSaving ? 'Registrando…' : 'Registrar decisão' }}
            </button>
          </div>
        </aside>
      </div>
    </template>
  </div>
</template>

<style scoped>
.gate-page {
  max-width: 1200px;
  margin: 0 auto;
}

.loading,
.error-msg {
  padding: 40px 0;
  color: var(--k5);
}

.error-msg {
  color: #8f2b2b;
}

.back-link {
  display: inline-block;
  font-size: 13px;
  color: var(--k5);
  text-decoration: none;
  margin-bottom: 8px;
}

.page-title {
  font-family: var(--serif);
  font-size: 26px;
  color: var(--k0);
  margin-bottom: 4px;
}

.page-sub {
  font-size: 14px;
  color: var(--k5);
  margin-bottom: 20px;
}

.page-sub.decided {
  color: var(--k0);
}

.gate-layout {
  display: grid;
  grid-template-columns: 1fr 340px;
  gap: 24px;
  align-items: start;
}

.checklist-col {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.bloco-group {
  background: var(--wh);
  border: 1px solid var(--bd);
  border-radius: 12px;
  padding: 16px 20px;
}

.bloco-title {
  font-family: var(--serif);
  font-size: 15px;
  color: var(--k0);
  margin: 0 0 12px;
}

.checklist-item {
  padding: 12px 0;
  border-top: 1px solid var(--bd2);
}

.checklist-item:first-of-type {
  border-top: none;
  padding-top: 0;
}

.item-head {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}

.item-id {
  font-size: 12px;
  font-weight: 700;
  color: var(--k5);
}

.item-texto {
  font-size: 14px;
  color: var(--k0);
  flex: 1;
  min-width: 200px;
}

.badge-critico {
  padding: 2px 8px;
  font-size: 11px;
  font-weight: 600;
  color: #8f2b2b;
  background: #fdecec;
  border: 1px solid #f3b8b8;
  border-radius: 6px;
}

.badge-origem {
  padding: 2px 8px;
  font-size: 11px;
  font-weight: 600;
  border-radius: 6px;
  border: 1px solid var(--bd2);
  color: var(--k5);
  background: var(--k9);
}

.badge-origem.swot {
  color: var(--k0);
  background: var(--golddim);
  border-color: var(--goldbd);
}

.item-body {
  display: flex;
  gap: 8px;
  align-items: flex-start;
}

.status-select {
  width: auto;
  min-width: 140px;
}

.evidencia-input {
  flex: 1;
}

.decision-col {
  background: var(--wh);
  border: 1px solid var(--bd);
  border-radius: 12px;
  padding: 20px;
  position: sticky;
  top: 20px;
}

.section-title {
  font-family: var(--serif);
  font-size: 16px;
  color: var(--k0);
  margin: 0 0 16px;
}

.form-group {
  margin-bottom: 14px;
}

.form-group label {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: var(--k0);
  margin-bottom: 6px;
}

.input {
  width: 100%;
  padding: 8px 10px;
  border: 1px solid var(--bd);
  border-radius: 8px;
  font-size: 13px;
  font-family: inherit;
}

select.input {
  cursor: pointer;
}

.condicoes-block {
  margin-bottom: 14px;
}

.condicao-row {
  display: flex;
  gap: 6px;
  margin-bottom: 6px;
  align-items: center;
}

.condicao-prazo {
  max-width: 90px;
}

.condicao-dono {
  max-width: 120px;
}

.remove-btn {
  background: none;
  border: none;
  color: #8f2b2b;
  font-size: 18px;
  cursor: pointer;
  padding: 0 4px;
}

.link-btn {
  background: none;
  border: none;
  color: var(--gold);
  cursor: pointer;
  font-size: 13px;
  padding: 0;
}

.go-blocked-reason {
  padding: 10px 12px;
  margin-bottom: 12px;
  background: #fdecec;
  color: #8f2b2b;
  border-radius: 8px;
  font-size: 12px;
}

.decision-readonly {
  font-size: 14px;
  color: var(--k3);
}

.decision-readonly ul {
  margin: 4px 0 0;
  padding-left: 18px;
}

.btn-primary {
  width: 100%;
  padding: 10px 18px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  border: 1px solid transparent;
  background: var(--k0);
  color: var(--wh);
  cursor: pointer;
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
