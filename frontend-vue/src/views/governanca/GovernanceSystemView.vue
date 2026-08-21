<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ApiError } from '@/api/client'
import { useAutosave } from '@/composables/useAutosave'
import {
  getAiSystem,
  updateAiSystem,
  listAssessments,
  createAssessment,
  listGates,
  createGate,
  getTraceability,
} from '@/api/governance'
import type {
  AiSystem,
  RiskAssessment,
  Gate,
  RiscoNivel,
  OrigemIA,
  SensibilidadeDados,
  Traceability,
} from '@/api/governance'

const route = useRoute()
const router = useRouter()
const systemId = String(route.params.id)

const loading = ref(true)
const loadError = ref<string | null>(null)
const system = ref<AiSystem | null>(null)
const assessments = ref<RiskAssessment[]>([])
const gates = ref<Gate[]>([])

const activeTab = ref<'geral' | 'avaliacao' | 'gate' | 'rastreabilidade'>('geral')
const traceability = ref<Traceability | null>(null)

const QUADRANTE_LABEL: Record<string, string> = {
  forcas: 'Força',
  fraquezas: 'Fraqueza',
  oportunidades: 'Oportunidade',
  ameacas: 'Ameaça',
}

const NIVEL_OPTIONS: RiscoNivel[] = ['baixo', 'medio', 'alto', 'critico']
const NIVEL_LABEL: Record<RiscoNivel, string> = { baixo: 'Baixo', medio: 'Médio', alto: 'Alto', critico: 'Crítico' }
const ORIGEM_OPTIONS: OrigemIA[] = ['interno', 'oss_customizado', 'api_terceiros']
const ORIGEM_LABEL: Record<OrigemIA, string> = {
  interno: 'Interno',
  oss_customizado: 'OSS customizado',
  api_terceiros: 'API de terceiros',
}
const SENSIBILIDADE_OPTIONS: SensibilidadeDados[] = ['publico', 'interno', 'pessoal', 'sensivel']

const latestGate = computed(() => (gates.value.length ? gates.value[0] : null))
const latestAssessment = computed(() => (assessments.value.length ? assessments.value[0] : null))

// ——— Visão geral ———

const form = ref({
  nome: '',
  area_negocio: '',
  finalidade: '',
  descricao_dados: '',
  sensibilidade_dados: 'interno' as SensibilidadeDados,
  fornecedor: '',
  modelo: '',
  versao_pinned: '',
  origem_ia: 'interno' as OrigemIA,
  hitl_obrigatorio: false,
  hitl_descricao: '',
})
// AR-03: antes desta extração, persist() não tinha NENHUMA guarda de
// concorrência. Os 11 campos do formulário abaixo chamam persist() no
// @blur/@change; tabular rápido por vários campos podia disparar PATCHs
// simultâneos, com a resposta mais lenta vencendo por último — bug real de
// perda de dado, não só duplicação de código. O composable compartilhado
// serializa as gravações em fila — ver src/composables/useAutosave.ts.
const autosave = useAutosave(async () => {
  const updated = await updateAiSystem(systemId, { ...form.value })
  system.value = updated
})
const saveState = autosave.saveState

function applySystem(s: AiSystem) {
  system.value = s
  form.value = {
    nome: s.nome,
    area_negocio: s.area_negocio,
    finalidade: s.finalidade,
    descricao_dados: s.descricao_dados,
    sensibilidade_dados: s.sensibilidade_dados ?? 'interno',
    fornecedor: s.fornecedor,
    modelo: s.modelo,
    versao_pinned: s.versao_pinned,
    origem_ia: s.origem_ia ?? 'interno',
    hitl_obrigatorio: s.hitl_obrigatorio,
    hitl_descricao: s.hitl_descricao,
  }
}

function persist(): void {
  void autosave.save()
}

// ——— Avaliação de risco ———

const assessmentForm = ref({
  dados: 'baixo' as RiscoNivel,
  impacto_erro: 'baixo' as RiscoNivel,
  autonomia: 'baixo' as RiscoNivel,
  exposicao_juridica: 'baixo' as RiscoNivel,
  finalidade_base_legal: '',
  titulares_afetados: '',
  analise_vieses: '',
  medidas_mitigadoras: '',
  plano_incidentes: '',
  dpa_assinado: false,
  subprocessadores_conhecidos: false,
  nao_treinamento_contratual: false,
  regiao_processamento: '',
  certificacoes: '',
  sla: '',
  gatilhos_reavaliacao: '',
})
const assessmentSaving = ref(false)
const assessmentError = ref<string | null>(null)

const NIVEL_ORDER: RiscoNivel[] = ['baixo', 'medio', 'alto', 'critico']
const previewNivelFinal = computed<RiscoNivel>(() => {
  const criterios = [
    assessmentForm.value.dados,
    assessmentForm.value.impacto_erro,
    assessmentForm.value.autonomia,
    assessmentForm.value.exposicao_juridica,
  ]
  return criterios.reduce((pior, atual) =>
    NIVEL_ORDER.indexOf(atual) > NIVEL_ORDER.indexOf(pior) ? atual : pior
  )
})
const showAia = computed(() => previewNivelFinal.value === 'alto' || previewNivelFinal.value === 'critico')
const showDueDiligence = computed(() => system.value?.origem_ia === 'api_terceiros')

function splitLines(text: string): string[] {
  return text.split('\n').map((l) => l.trim()).filter(Boolean)
}

async function submitAssessment() {
  assessmentSaving.value = true
  assessmentError.value = null
  try {
    const f = assessmentForm.value
    const created = await createAssessment(systemId, {
      regua: {
        dados: f.dados,
        impacto_erro: f.impacto_erro,
        autonomia: f.autonomia,
        exposicao_juridica: f.exposicao_juridica,
      },
      aia: showAia.value
        ? {
            finalidade_base_legal: f.finalidade_base_legal,
            titulares_afetados: f.titulares_afetados,
            analise_vieses: f.analise_vieses,
            medidas_mitigadoras: splitLines(f.medidas_mitigadoras),
            plano_incidentes: f.plano_incidentes,
          }
        : null,
      due_diligence_fornecedor: showDueDiligence.value
        ? {
            dpa_assinado: f.dpa_assinado,
            subprocessadores_conhecidos: f.subprocessadores_conhecidos,
            nao_treinamento_contratual: f.nao_treinamento_contratual,
            regiao_processamento: f.regiao_processamento,
            certificacoes: splitLines(f.certificacoes),
            sla: f.sla,
          }
        : null,
      gatilhos_reavaliacao: splitLines(f.gatilhos_reavaliacao),
    })
    assessments.value = [created, ...assessments.value]
    const refreshed = await getAiSystem(systemId)
    applySystem(refreshed)
  } catch (e) {
    assessmentError.value = e instanceof ApiError ? e.message : e instanceof Error ? e.message : 'Erro ao publicar avaliação.'
  } finally {
    assessmentSaving.value = false
  }
}

// ——— Gate ———

const gateCreating = ref(false)
const gateError = ref<string | null>(null)

async function startGate() {
  gateCreating.value = true
  gateError.value = null
  try {
    const gate = await createGate(systemId)
    router.push(`/governanca/gate/${gate.id}`)
  } catch (e) {
    gateError.value = e instanceof ApiError ? e.message : e instanceof Error ? e.message : 'Erro ao montar gate.'
  } finally {
    gateCreating.value = false
  }
}

onMounted(async () => {
  try {
    const [s, a, g, t] = await Promise.all([
      getAiSystem(systemId),
      listAssessments(systemId),
      listGates(systemId),
      getTraceability(systemId),
    ])
    applySystem(s)
    assessments.value = a.items
    gates.value = g.items
    traceability.value = t
  } catch (e) {
    loadError.value = e instanceof ApiError ? e.message : e instanceof Error ? e.message : 'Erro ao carregar sistema.'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="system-page">
    <div v-if="loading" class="loading">Carregando...</div>
    <div v-else-if="loadError" class="error-msg">{{ loadError }}</div>
    <template v-else-if="system">
      <header class="page-header">
        <RouterLink to="/governanca/inventario" class="back-link">← Inventário</RouterLink>
        <h1 class="page-title">{{ system.nome || 'Sistema sem nome' }}</h1>
        <p class="page-sub">{{ system.area_negocio || 'Área não definida' }} · Status: {{ system.status }}</p>
      </header>

      <nav class="tabs">
        <button type="button" class="tab" :class="{ active: activeTab === 'geral' }" @click="activeTab = 'geral'">
          Visão geral
        </button>
        <button type="button" class="tab" :class="{ active: activeTab === 'avaliacao' }" @click="activeTab = 'avaliacao'">
          Avaliação
        </button>
        <button type="button" class="tab" :class="{ active: activeTab === 'gate' }" @click="activeTab = 'gate'">
          Gate
        </button>
        <button
          type="button"
          class="tab"
          :class="{ active: activeTab === 'rastreabilidade' }"
          @click="activeTab = 'rastreabilidade'"
        >
          Rastreabilidade
        </button>
      </nav>

      <section v-if="activeTab === 'geral'" class="tab-panel">
        <div class="save-indicator" :class="saveState">
          <span v-if="saveState === 'saving'">Salvando…</span>
          <span v-else-if="saveState === 'saved'">Salvo</span>
          <span v-else-if="saveState === 'error'">Erro ao salvar</span>
        </div>
        <div class="form-grid">
          <div class="form-group">
            <label>Nome</label>
            <input v-model="form.nome" type="text" class="input" @blur="persist" />
          </div>
          <div class="form-group">
            <label>Área de negócio</label>
            <input v-model="form.area_negocio" type="text" class="input" @blur="persist" />
          </div>
          <div class="form-group form-group-wide">
            <label>Finalidade</label>
            <textarea v-model="form.finalidade" rows="2" class="input" @blur="persist" />
          </div>
          <div class="form-group form-group-wide">
            <label>Descrição dos dados usados</label>
            <textarea v-model="form.descricao_dados" rows="2" class="input" @blur="persist" />
          </div>
          <div class="form-group">
            <label>Sensibilidade dos dados</label>
            <select v-model="form.sensibilidade_dados" class="input" @change="persist">
              <option v-for="opt in SENSIBILIDADE_OPTIONS" :key="opt" :value="opt">{{ opt }}</option>
            </select>
          </div>
          <div class="form-group">
            <label>Origem da IA</label>
            <select v-model="form.origem_ia" class="input" @change="persist">
              <option v-for="opt in ORIGEM_OPTIONS" :key="opt" :value="opt">{{ ORIGEM_LABEL[opt] }}</option>
            </select>
          </div>
          <div class="form-group">
            <label>Fornecedor</label>
            <input v-model="form.fornecedor" type="text" class="input" @blur="persist" />
          </div>
          <div class="form-group">
            <label>Modelo</label>
            <input v-model="form.modelo" type="text" class="input" @blur="persist" />
          </div>
          <div class="form-group">
            <label>Versão (pinned)</label>
            <input v-model="form.versao_pinned" type="text" class="input" @blur="persist" />
          </div>
          <div class="form-group form-group-check">
            <label><input v-model="form.hitl_obrigatorio" type="checkbox" @change="persist" /> Human-in-the-loop obrigatório</label>
          </div>
          <div class="form-group form-group-wide">
            <label>Descrição do ponto humano</label>
            <textarea v-model="form.hitl_descricao" rows="2" class="input" @blur="persist" />
          </div>
        </div>

        <div class="risk-summary">
          <span class="risk-label">Classificação de risco atual:</span>
          <span v-if="system.classificacao_risco.nivel" class="badge-risco" :data-nivel="system.classificacao_risco.nivel">
            {{ NIVEL_LABEL[system.classificacao_risco.nivel] }}
          </span>
          <span v-else class="muted">Não classificado</span>
          <span v-if="system.classificacao_risco.fonte" class="muted">
            (fonte: {{ system.classificacao_risco.fonte === 'avaliacao' ? 'avaliação publicada' : 'preliminar R3' }})
          </span>
        </div>
      </section>

      <section v-else-if="activeTab === 'avaliacao'" class="tab-panel">
        <div v-if="latestAssessment" class="assessment-history">
          <h2 class="section-title">Última avaliação publicada</h2>
          <p class="muted">
            Revisão {{ latestAssessment.revision }} · Nível final:
            <span class="badge-risco" :data-nivel="latestAssessment.payload.nivel_final">{{ NIVEL_LABEL[latestAssessment.payload.nivel_final] }}</span>
          </p>
        </div>

        <h2 class="section-title">Nova avaliação</h2>
        <div v-if="assessmentError" class="error-msg">{{ assessmentError }}</div>
        <div class="form-grid">
          <div class="form-group">
            <label>Dados</label>
            <select v-model="assessmentForm.dados" class="input">
              <option v-for="opt in NIVEL_OPTIONS" :key="opt" :value="opt">{{ NIVEL_LABEL[opt] }}</option>
            </select>
          </div>
          <div class="form-group">
            <label>Impacto de erro</label>
            <select v-model="assessmentForm.impacto_erro" class="input">
              <option v-for="opt in NIVEL_OPTIONS" :key="opt" :value="opt">{{ NIVEL_LABEL[opt] }}</option>
            </select>
          </div>
          <div class="form-group">
            <label>Autonomia</label>
            <select v-model="assessmentForm.autonomia" class="input">
              <option v-for="opt in NIVEL_OPTIONS" :key="opt" :value="opt">{{ NIVEL_LABEL[opt] }}</option>
            </select>
          </div>
          <div class="form-group">
            <label>Exposição jurídica</label>
            <select v-model="assessmentForm.exposicao_juridica" class="input">
              <option v-for="opt in NIVEL_OPTIONS" :key="opt" :value="opt">{{ NIVEL_LABEL[opt] }}</option>
            </select>
          </div>
        </div>

        <p class="preview-nivel">
          Nível final calculado: <span class="badge-risco" :data-nivel="previewNivelFinal">{{ NIVEL_LABEL[previewNivelFinal] }}</span>
        </p>

        <div v-if="showAia" class="form-grid aia-block">
          <h3 class="section-subtitle">Avaliação de Impacto Algorítmico (AIA) — obrigatória para risco alto/crítico</h3>
          <div class="form-group form-group-wide">
            <label>Finalidade e base legal</label>
            <textarea v-model="assessmentForm.finalidade_base_legal" rows="2" class="input" />
          </div>
          <div class="form-group form-group-wide">
            <label>Titulares afetados</label>
            <textarea v-model="assessmentForm.titulares_afetados" rows="2" class="input" />
          </div>
          <div class="form-group form-group-wide">
            <label>Análise de vieses</label>
            <textarea v-model="assessmentForm.analise_vieses" rows="2" class="input" />
          </div>
          <div class="form-group form-group-wide">
            <label>Medidas de mitigação (uma por linha)</label>
            <textarea v-model="assessmentForm.medidas_mitigadoras" rows="3" class="input" />
          </div>
          <div class="form-group form-group-wide">
            <label>Plano de incidentes</label>
            <textarea v-model="assessmentForm.plano_incidentes" rows="2" class="input" />
          </div>
        </div>

        <div v-if="showDueDiligence" class="form-grid dd-block">
          <h3 class="section-subtitle">Due diligence do fornecedor — obrigatória para API de terceiros</h3>
          <div class="form-group form-group-check">
            <label><input v-model="assessmentForm.dpa_assinado" type="checkbox" /> DPA assinado</label>
          </div>
          <div class="form-group form-group-check">
            <label><input v-model="assessmentForm.subprocessadores_conhecidos" type="checkbox" /> Subprocessadores conhecidos</label>
          </div>
          <div class="form-group form-group-check">
            <label><input v-model="assessmentForm.nao_treinamento_contratual" type="checkbox" /> Cláusula de não-treinamento</label>
          </div>
          <div class="form-group">
            <label>Região de processamento</label>
            <input v-model="assessmentForm.regiao_processamento" type="text" class="input" />
          </div>
          <div class="form-group form-group-wide">
            <label>Certificações (uma por linha)</label>
            <textarea v-model="assessmentForm.certificacoes" rows="2" class="input" />
          </div>
          <div class="form-group">
            <label>SLA</label>
            <input v-model="assessmentForm.sla" type="text" class="input" />
          </div>
        </div>

        <div class="form-group form-group-wide">
          <label>Gatilhos de reavaliação (um por linha)</label>
          <textarea v-model="assessmentForm.gatilhos_reavaliacao" rows="2" class="input" placeholder="ex.: troca_modelo, novo_tipo_dado, incidente" />
        </div>

        <button type="button" class="btn-primary" :disabled="assessmentSaving" @click="submitAssessment">
          {{ assessmentSaving ? 'Publicando…' : 'Publicar avaliação' }}
        </button>
      </section>

      <section v-else-if="activeTab === 'gate'" class="tab-panel">
        <div v-if="gateError" class="error-msg">{{ gateError }}</div>
        <div v-if="latestGate" class="gate-summary">
          <p>
            Gate atual (ciclo {{ latestGate.revision }}):
            <strong v-if="latestGate.decisao">{{ latestGate.decisao.resultado }}</strong>
            <span v-else class="muted">em andamento</span>
          </p>
          <RouterLink :to="`/governanca/gate/${latestGate.id}`" class="btn-secondary">Abrir checklist</RouterLink>
          <button
            v-if="latestGate.decisao"
            type="button"
            class="btn-primary"
            :disabled="gateCreating"
            @click="startGate"
          >
            {{ gateCreating ? 'Abrindo…' : 'Abrir novo ciclo' }}
          </button>
        </div>
        <div v-else>
          <p class="muted">Nenhum gate iniciado para este sistema ainda.</p>
          <button type="button" class="btn-primary" :disabled="gateCreating" @click="startGate">
            {{ gateCreating ? 'Montando…' : 'Iniciar gate' }}
          </button>
        </div>

        <div v-if="gates.length > 1" class="gate-history">
          <h2 class="section-title">Ciclos anteriores</h2>
          <ul>
            <li v-for="g in gates.slice(1)" :key="g.id">
              <RouterLink :to="`/governanca/gate/${g.id}`">Ciclo {{ g.revision }}</RouterLink>
              — {{ g.decisao ? g.decisao.resultado : 'em andamento' }}
            </li>
          </ul>
        </div>
      </section>

      <section v-else-if="activeTab === 'rastreabilidade'" class="tab-panel">
        <p v-if="!traceability" class="muted">Sem dados de rastreabilidade.</p>
        <ol v-else class="timeline">
          <li v-if="traceability.csf_ids.length" class="timeline-node">
            <span class="timeline-dot" />
            <div class="timeline-content">
              <h3 class="timeline-title">CSFs de origem</h3>
              <div class="chip-row">
                <RouterLink
                  v-for="csf in traceability.csf_ids"
                  :key="csf"
                  :to="traceability.maturity_response_id ? `/ai-maturity/${traceability.maturity_response_id}` : ''"
                  class="chip"
                >
                  {{ csf }}
                </RouterLink>
              </div>
            </div>
          </li>

          <li v-if="traceability.swot_items.length" class="timeline-node">
            <span class="timeline-dot" />
            <div class="timeline-content">
              <h3 class="timeline-title">Itens SWOT</h3>
              <ul class="timeline-list">
                <li v-for="item in traceability.swot_items" :key="item.id">
                  <RouterLink v-if="traceability.canvas?.swot_id" :to="`/swot/${traceability.canvas.swot_id}`">
                    [{{ QUADRANTE_LABEL[item.quadrante] || item.quadrante }}] {{ item.texto }}
                  </RouterLink>
                  <span v-else>[{{ QUADRANTE_LABEL[item.quadrante] || item.quadrante }}] {{ item.texto }}</span>
                </li>
              </ul>
            </div>
          </li>

          <li v-if="traceability.canvas" class="timeline-node">
            <span class="timeline-dot" />
            <div class="timeline-content">
              <h3 class="timeline-title">Canvas de oportunidades</h3>
              <RouterLink :to="`/projetos/${traceability.canvas.canvas_project_id}`">
                {{ traceability.canvas.title }} — {{ traceability.canvas.area_negocio }}
              </RouterLink>
            </div>
          </li>

          <li class="timeline-node">
            <span class="timeline-dot" />
            <div class="timeline-content">
              <h3 class="timeline-title">Sistema de IA</h3>
              <span>{{ system.nome }}</span>
            </div>
          </li>

          <li v-if="traceability.assessments.length" class="timeline-node">
            <span class="timeline-dot" />
            <div class="timeline-content">
              <h3 class="timeline-title">Avaliações de risco</h3>
              <ul class="timeline-list">
                <li v-for="a in traceability.assessments" :key="a.id">
                  <button type="button" class="link-btn" @click="activeTab = 'avaliacao'">
                    Revisão {{ a.revision }} — {{ a.payload.nivel_final }}
                  </button>
                </li>
              </ul>
            </div>
          </li>

          <li v-if="traceability.gates.length" class="timeline-node">
            <span class="timeline-dot" />
            <div class="timeline-content">
              <h3 class="timeline-title">Gates</h3>
              <ul class="timeline-list">
                <li v-for="g in traceability.gates" :key="g.id">
                  <RouterLink :to="`/governanca/gate/${g.id}`">
                    Ciclo {{ g.revision }} — {{ g.decisao ? g.decisao.resultado : 'em andamento' }}
                  </RouterLink>
                </li>
              </ul>
            </div>
          </li>
        </ol>
      </section>
    </template>
  </div>
</template>

<style scoped>
.system-page {
  max-width: 900px;
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

.tabs {
  display: flex;
  gap: 4px;
  border-bottom: 1px solid var(--bd);
  margin-bottom: 24px;
}

.tab {
  padding: 10px 18px;
  font-size: 14px;
  font-weight: 500;
  color: var(--k5);
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  cursor: pointer;
}

.tab.active {
  color: var(--k0);
  border-bottom-color: var(--gold);
}

.tab-panel {
  background: var(--wh);
  border: 1px solid var(--bd);
  border-radius: var(--r-lg);
  padding: 24px;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  margin-bottom: 16px;
}

.form-group-wide {
  grid-column: 1 / -1;
}

.form-group label {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: var(--k0);
  margin-bottom: 6px;
}

.form-group-check label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 400;
  cursor: pointer;
}

.input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--bd);
  border-radius: var(--r-md);
  font-size: 14px;
  font-family: inherit;
}

select.input {
  cursor: pointer;
}

.save-indicator {
  height: 18px;
  font-size: 12px;
  margin-bottom: 8px;
  color: var(--k5);
}

.save-indicator.error {
  color: #8f2b2b;
}

.risk-summary {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-top: 16px;
  border-top: 1px solid var(--bd2);
  font-size: 14px;
}

.risk-label {
  font-weight: 600;
  color: var(--k0);
}

.section-title {
  font-family: var(--serif);
  font-size: 18px;
  color: var(--k0);
  margin: 0 0 12px;
}

.section-subtitle {
  grid-column: 1 / -1;
  font-size: 14px;
  font-weight: 600;
  color: var(--k0);
  margin: 8px 0 0;
}

.assessment-history {
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--bd2);
}

.preview-nivel {
  font-size: 14px;
  margin-bottom: 16px;
}

.aia-block,
.dd-block {
  padding: 16px;
  background: var(--k9);
  border-radius: var(--r-md);
  margin-bottom: 16px;
}

.muted {
  color: var(--k5);
}

.badge-risco {
  display: inline-block;
  padding: 2px 10px;
  font-size: 12px;
  font-weight: 600;
  border-radius: var(--r-pill);
  border: 1px solid transparent;
}

.badge-risco[data-nivel='baixo'] {
  background: #e8f0e7;
  border-color: #bbd3b7;
  color: #2f6e4a;
}

.badge-risco[data-nivel='medio'] {
  background: #fbf3e1;
  border-color: #e8cf9a;
  color: #c48a26;
}

.badge-risco[data-nivel='alto'] {
  background: #fdecec;
  border-color: #f3b8b8;
  color: #8f2b2b;
}

.badge-risco[data-nivel='critico'] {
  background: #8f2b2b;
  border-color: #6e1f1f;
  color: #fff;
}

.gate-summary {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.gate-history {
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid var(--bd2);
}

.gate-history ul {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 14px;
}

.btn-primary,
.btn-secondary {
  padding: 10px 18px;
  border-radius: var(--r-md);
  font-size: 14px;
  font-weight: 500;
  border: 1px solid transparent;
  cursor: pointer;
  text-decoration: none;
  display: inline-block;
}

.btn-primary {
  background: var(--k0);
  color: var(--wh);
}

.btn-primary:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.btn-secondary {
  background: var(--wh);
  color: var(--k0);
  border-color: var(--bd);
}

.timeline {
  list-style: none;
  margin: 0;
  padding: 0;
  position: relative;
}

.timeline-node {
  position: relative;
  padding: 0 0 28px 28px;
  border-left: 2px solid var(--bd2);
}

.timeline-node:last-child {
  border-left-color: transparent;
  padding-bottom: 0;
}

.timeline-dot {
  position: absolute;
  left: -7px;
  top: 2px;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--gold);
  border: 2px solid var(--wh);
  box-shadow: 0 0 0 1px var(--goldbd);
}

.timeline-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--k0);
  margin: 0 0 8px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.timeline-content a {
  color: var(--k0);
}

.timeline-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 14px;
}

.chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.chip {
  display: inline-block;
  padding: 3px 10px;
  font-size: 12px;
  font-weight: 600;
  color: var(--k0);
  background: var(--k9);
  border: 1px solid var(--bd2);
  border-radius: var(--r-pill);
  text-decoration: none;
}

.link-btn {
  background: none;
  border: none;
  color: var(--k0);
  text-decoration: underline;
  cursor: pointer;
  font: inherit;
  padding: 0;
}
</style>
