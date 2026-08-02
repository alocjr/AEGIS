import { get, patch, post } from './client'

export type RiscoNivel = 'baixo' | 'medio' | 'alto' | 'critico'
export type OrigemIA = 'interno' | 'oss_customizado' | 'api_terceiros'
export type SensibilidadeDados = 'publico' | 'interno' | 'pessoal' | 'sensivel'
export type SistemaStatus =
  | 'rascunho'
  | 'aguardando_avaliacao'
  | 'avaliado'
  | 'em_gate'
  | 'producao'
  | 'reavaliacao_pendente'
  | 'descontinuado'

// ——— Membros da organização (seletor de RACI na decisão do gate) ———

export interface OrganizationMember {
  id: string
  name: string
  is_admin: boolean
}

export function listOrganizationMembers(): Promise<{ items: OrganizationMember[] }> {
  return get<{ items: OrganizationMember[] }>('/api/governance/organization-members')
}

// ——— Sistemas de IA (inventário) ———

export interface AiSystemRisco {
  nivel: RiscoNivel | null
  fonte: 'preliminar_r3' | 'avaliacao' | null
  avaliacao_id: string | null
}

export interface AiSystem {
  id: string
  nome: string
  area_negocio: string
  finalidade: string
  descricao_dados: string
  sensibilidade_dados: SensibilidadeDados | null
  fornecedor: string
  modelo: string
  versao_pinned: string
  origem_ia: OrigemIA | null
  responsavel_negocio_user_id: string | null
  responsavel_tecnico_user_id: string | null
  hitl_obrigatorio: boolean
  hitl_descricao: string
  status: SistemaStatus
  canvas_project_id: string | null
  classificacao_risco: AiSystemRisco
  created_by_user_id: string | null
  created_at: string | null
  updated_at: string | null
}

export type AiSystemCreatePayload = {
  nome: string
  area_negocio?: string
  finalidade?: string
  descricao_dados?: string
  sensibilidade_dados?: SensibilidadeDados
  fornecedor?: string
  modelo?: string
  versao_pinned?: string
  origem_ia?: OrigemIA
  responsavel_negocio_user_id?: string
  responsavel_tecnico_user_id?: string
  hitl_obrigatorio?: boolean
  hitl_descricao?: string
}

export type AiSystemUpdatePayload = Partial<AiSystemCreatePayload> & { status?: SistemaStatus }

export function listAiSystems(): Promise<{ items: AiSystem[] }> {
  return get<{ items: AiSystem[] }>('/api/governance/systems')
}

export function createAiSystem(body: AiSystemCreatePayload): Promise<AiSystem> {
  return post<AiSystem>('/api/governance/systems', body)
}

export function getAiSystem(id: string): Promise<AiSystem> {
  return get<AiSystem>(`/api/governance/systems/${encodeURIComponent(id)}`)
}

export function updateAiSystem(id: string, body: AiSystemUpdatePayload): Promise<AiSystem> {
  return patch<AiSystem>(`/api/governance/systems/${encodeURIComponent(id)}`, body)
}

// ——— Avaliação de risco (aegis.avaliacao-risco) ———

export interface AvaliacaoRegua {
  dados: RiscoNivel
  impacto_erro: RiscoNivel
  autonomia: RiscoNivel
  exposicao_juridica: RiscoNivel
}

export interface AvaliacaoAIA {
  finalidade_base_legal: string
  titulares_afetados: string
  analise_vieses: string
  medidas_mitigadoras: string[]
  plano_incidentes: string
}

export interface AvaliacaoDueDiligence {
  dpa_assinado: boolean
  subprocessadores_conhecidos: boolean
  nao_treinamento_contratual: boolean
  regiao_processamento: string
  certificacoes: string[]
  sla: string
}

export interface RiskAssessmentPayload {
  regua: AvaliacaoRegua
  aia?: AvaliacaoAIA | null
  due_diligence_fornecedor?: AvaliacaoDueDiligence | null
  gatilhos_reavaliacao?: string[]
}

export interface RiskAssessment {
  id: string
  system_id: string
  type: string
  version: number
  revision: number
  payload: {
    regua: AvaliacaoRegua
    nivel_final: RiscoNivel
    aia: AvaliacaoAIA | null
    due_diligence_fornecedor: AvaliacaoDueDiligence | null
    gatilhos_reavaliacao: string[]
    avaliador_user_id: string
  }
  published_by_user_id: string | null
  published_at: string | null
}

export function createAssessment(systemId: string, body: RiskAssessmentPayload): Promise<RiskAssessment> {
  return post<RiskAssessment>(`/api/governance/systems/${encodeURIComponent(systemId)}/assessments`, body)
}

export function listAssessments(systemId: string): Promise<{ items: RiskAssessment[] }> {
  return get<{ items: RiskAssessment[] }>(`/api/governance/systems/${encodeURIComponent(systemId)}/assessments`)
}

// ——— Gate go/no-go (aegis.gate-governanca) ———

export type ChecklistBloco = 'A' | 'B' | 'C' | 'D' | 'E' | 'F'
export type ChecklistItemStatus = 'aprovado' | 'reprovado' | 'nao_aplicavel' | 'pendente'
export type GateResultado = 'go' | 'no_go' | 'go_condicional'

export interface ChecklistEvidencia {
  descricao: string
  link_ou_artifact_id: string
}

export interface ChecklistItemOrigem {
  tipo: 'template' | 'swot'
  swot_item_id: string | null
  rule: string | null
}

export interface ChecklistItem {
  bloco: ChecklistBloco
  item_id: string
  texto: string
  critico: boolean
  status: ChecklistItemStatus
  evidencia: ChecklistEvidencia
  origem: ChecklistItemOrigem
}

export interface GateCondicao {
  texto: string
  prazo: string
  dono_user_id: string
}

export interface GateDecisao {
  resultado: GateResultado
  condicoes: GateCondicao[]
  aprovador_user_id: string
  consultados_user_ids: string[]
  justificativa: string
}

export interface Gate {
  id: string
  system_id: string
  type: string
  version: number
  revision: number
  template_version: string
  rules_applied: { rule_id: string; rule_version: string }[]
  checklist: ChecklistItem[]
  decisao: GateDecisao | null
  created_by_user_id: string | null
  created_at: string | null
  updated_at: string | null
  decided_by_user_id: string | null
  decided_at: string | null
}

export function createGate(systemId: string): Promise<Gate> {
  return post<Gate>(`/api/governance/systems/${encodeURIComponent(systemId)}/gates`)
}

export function listGates(systemId: string): Promise<{ items: Gate[] }> {
  return get<{ items: Gate[] }>(`/api/governance/systems/${encodeURIComponent(systemId)}/gates`)
}

export function getGate(id: string): Promise<Gate> {
  return get<Gate>(`/api/governance/gates/${encodeURIComponent(id)}`)
}

export function updateGateItem(
  gateId: string,
  itemId: string,
  body: { status?: ChecklistItemStatus; evidencia?: ChecklistEvidencia }
): Promise<Gate> {
  return patch<Gate>(
    `/api/governance/gates/${encodeURIComponent(gateId)}/items/${encodeURIComponent(itemId)}`,
    body
  )
}

export interface GateDecisionPayload {
  decisao: {
    resultado: GateResultado
    condicoes?: { texto: string; prazo?: string; dono_user_id: string }[]
    aprovador_user_id: string
    consultados_user_ids?: string[]
    justificativa?: string
  }
}

export function decideGate(gateId: string, body: GateDecisionPayload): Promise<Gate> {
  return post<Gate>(`/api/governance/gates/${encodeURIComponent(gateId)}/decision`, body)
}

// ——— Rastreabilidade ———

export interface TraceabilitySwotItem {
  id: string
  texto: string
  quadrante: string
  question_id: string
}

export interface TraceabilityCanvas {
  canvas_project_id: string
  title: string
  area_negocio: string
  swot_id: string | null
}

export interface Traceability {
  system_id: string
  csf_ids: string[]
  maturity_response_id: string | null
  swot_items: TraceabilitySwotItem[]
  canvas: TraceabilityCanvas | null
  assessments: RiskAssessment[]
  gates: Gate[]
}

export function getTraceability(systemId: string): Promise<Traceability> {
  return get<Traceability>(`/api/governance/systems/${encodeURIComponent(systemId)}/traceability`)
}

// ——— Evidências e métricas ———

export interface EvidenciaPeriodo {
  inicio: string
  fim: string
}

export interface EvidenceMetrics {
  pct_sistemas_inventariados: number
  tempo_medio_registro_dias: number
  pct_sistemas_classificados: number
  lead_time_avaliacao_dias: number
  pct_acoes_criticas_com_hitl: number
  tempo_reconstrucao_decisao_horas: number
  pct_fichas_atualizadas_6m: number
  bloqueios_guardrail_periodo: number
  periodo: EvidenciaPeriodo
}

export interface MetricsResponse {
  published: boolean
  metrics: EvidenceMetrics | null
  published_at: string | null
}

export function getMetrics(): Promise<MetricsResponse> {
  return get<MetricsResponse>('/api/governance/metrics')
}

export function createEvidenceSnapshot(body: EvidenceMetrics): Promise<{ id: string; payload: EvidenceMetrics }> {
  return post('/api/governance/evidence-snapshots', body)
}

// ——— Profundidade de implantação (R1) ———

export type Profundidade = 'fundacao' | 'intermediario' | 'completo'

export interface ProfundidadeSettings {
  value: Profundidade
  suggested_value: Profundidade | null
  suggested_at: string | null
  confirmed_by_user_id: string | null
  confirmed_at: string | null
}

export function getProfundidade(): Promise<ProfundidadeSettings> {
  return get<ProfundidadeSettings>('/api/governance/settings/profundidade')
}

export function recalcularProfundidade(): Promise<ProfundidadeSettings> {
  return post<ProfundidadeSettings>('/api/governance/settings/profundidade/recalcular')
}

export function confirmarProfundidade(): Promise<ProfundidadeSettings> {
  return post<ProfundidadeSettings>('/api/governance/settings/profundidade/confirmar')
}
