"""Schemas do módulo de Governança de IA.

Convenções desta feature (ver plano salvo em ~/.claude/plans/smooth-baking-nebula.md):
- `ai_systems` é estado operacional mutável (repository.py grava audit log a cada mutação).
- `ai_risk_assessments` / `ai_governance_gates` / `ai_governance_evidence` são imutáveis por
  versão: "publicar" sempre insere um novo documento (nunca edita um payload já publicado).
  `type`/`version` identificam o formato (equivalentes a um `aegis.*` versionado); `revision`
  é o número da publicação para a mesma entidade (system_id), incrementado a cada correção.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# ---- tipos de artefato (formato + versão do schema) ----

ARTIFACT_TYPE_AVALIACAO_RISCO = "aegis.avaliacao-risco"
ARTIFACT_VERSION_AVALIACAO_RISCO = 1
ARTIFACT_TYPE_GATE_GOVERNANCA = "aegis.gate-governanca"
ARTIFACT_VERSION_GATE_GOVERNANCA = 1
ARTIFACT_TYPE_EVIDENCIA_GOVERNANCA = "aegis.evidencia-governanca"
ARTIFACT_VERSION_EVIDENCIA_GOVERNANCA = 1


# ---- ai_systems (registro vivo, mutável) ----

RiscoNivel = Literal["baixo", "medio", "alto", "critico"]
OrigemIA = Literal["interno", "oss_customizado", "api_terceiros"]
SistemaStatus = Literal[
    "rascunho",
    "aguardando_avaliacao",
    "avaliado",
    "em_gate",
    "producao",
    "reavaliacao_pendente",
    "descontinuado",
]
DadosSensibilidade = Literal["publico", "interno", "pessoal", "sensivel"]

_RISCO_NIVEIS: tuple[RiscoNivel, ...] = ("baixo", "medio", "alto", "critico")


class AiSystemCreateRequest(BaseModel):
    nome: str = Field(min_length=2, max_length=200)
    area_negocio: str = Field(default="", max_length=200)
    finalidade: str = Field(default="", max_length=2000)
    descricao_dados: str = Field(default="", max_length=2000)
    sensibilidade_dados: DadosSensibilidade = "interno"
    fornecedor: str = Field(default="", max_length=200)
    modelo: str = Field(default="", max_length=200)
    versao_pinned: str = Field(default="", max_length=100)
    origem_ia: OrigemIA = "interno"
    responsavel_negocio_user_id: str | None = Field(None, max_length=24)
    responsavel_tecnico_user_id: str | None = Field(None, max_length=24)
    hitl_obrigatorio: bool = False
    hitl_descricao: str = Field(default="", max_length=1000)
    # Origem no portfólio (Seção 5, hook Canvas → Inventário) — omitido em cadastro manual.
    canvas_project_id: str | None = Field(None, max_length=24)


class AiSystemUpdateRequest(BaseModel):
    nome: str | None = Field(None, min_length=2, max_length=200)
    area_negocio: str | None = Field(None, max_length=200)
    finalidade: str | None = Field(None, max_length=2000)
    descricao_dados: str | None = Field(None, max_length=2000)
    sensibilidade_dados: DadosSensibilidade | None = None
    fornecedor: str | None = Field(None, max_length=200)
    modelo: str | None = Field(None, max_length=200)
    versao_pinned: str | None = Field(None, max_length=100)
    origem_ia: OrigemIA | None = None
    responsavel_negocio_user_id: str | None = Field(None, max_length=24)
    responsavel_tecnico_user_id: str | None = Field(None, max_length=24)
    hitl_obrigatorio: bool | None = None
    hitl_descricao: str | None = Field(None, max_length=1000)
    status: SistemaStatus | None = None


# ---- aegis.avaliacao-risco v1 ----


class AvaliacaoRegua(BaseModel):
    """Os 4 critérios da régua de risco — nível final = o pior deles (elo mais fraco)."""

    dados: RiscoNivel
    impacto_erro: RiscoNivel
    autonomia: RiscoNivel
    exposicao_juridica: RiscoNivel


def nivel_final_da_regua(regua: AvaliacaoRegua) -> RiscoNivel:
    pior_indice = max(_RISCO_NIVEIS.index(v) for v in regua.model_dump().values())
    return _RISCO_NIVEIS[pior_indice]


class AvaliacaoAIA(BaseModel):
    """Obrigatória quando `nivel_final` ∈ {alto, critico}."""

    finalidade_base_legal: str = Field(default="", max_length=2000)
    titulares_afetados: str = Field(default="", max_length=2000)
    analise_vieses: str = Field(default="", max_length=2000)
    medidas_mitigadoras: list[str] = Field(default_factory=list, max_length=20)
    plano_incidentes: str = Field(default="", max_length=2000)


class AvaliacaoDueDiligence(BaseModel):
    """Obrigatória quando `origem_ia == api_terceiros`."""

    dpa_assinado: bool = False
    subprocessadores_conhecidos: bool = False
    nao_treinamento_contratual: bool = False
    regiao_processamento: str = Field(default="", max_length=200)
    certificacoes: list[str] = Field(default_factory=list, max_length=20)
    sla: str = Field(default="", max_length=500)


class RiskAssessmentCreateRequest(BaseModel):
    regua: AvaliacaoRegua
    aia: AvaliacaoAIA | None = None
    due_diligence_fornecedor: AvaliacaoDueDiligence | None = None
    gatilhos_reavaliacao: list[str] = Field(default_factory=list, max_length=10)


# ---- aegis.gate-governanca v1 ----

BlocoChecklist = Literal["A", "B", "C", "D", "E", "F"]
ChecklistItemStatus = Literal["aprovado", "reprovado", "nao_aplicavel", "pendente"]
GateResultado = Literal["go", "no_go", "go_condicional"]


class ChecklistEvidencia(BaseModel):
    descricao: str = Field(default="", max_length=2000)
    link_ou_artifact_id: str = Field(default="", max_length=500)


class ChecklistItemOrigem(BaseModel):
    tipo: Literal["template", "swot"] = "template"
    swot_item_id: str | None = Field(None, max_length=64)
    rule: str | None = Field(None, max_length=60)


class ChecklistItem(BaseModel):
    bloco: BlocoChecklist
    item_id: str = Field(max_length=40)
    texto: str = Field(max_length=1000)
    critico: bool = False
    status: ChecklistItemStatus = "pendente"
    evidencia: ChecklistEvidencia = Field(default_factory=ChecklistEvidencia)
    origem: ChecklistItemOrigem = Field(default_factory=ChecklistItemOrigem)


class GateChecklistUpdateRequest(BaseModel):
    """PATCH de um item do checklist — status/evidência (Seção 6)."""

    status: ChecklistItemStatus | None = None
    evidencia: ChecklistEvidencia | None = None


class GateCondicao(BaseModel):
    texto: str = Field(max_length=1000)
    prazo: str = Field(default="", max_length=40)
    dono_user_id: str = Field(max_length=24)


class GateDecisao(BaseModel):
    resultado: GateResultado
    condicoes: list[GateCondicao] = Field(default_factory=list, max_length=20)
    aprovador_user_id: str = Field(max_length=24)
    consultados_user_ids: list[str] = Field(default_factory=list, max_length=20)
    justificativa: str = Field(default="", max_length=4000)


class GateDecisionRequest(BaseModel):
    decisao: GateDecisao


# ---- aegis.evidencia-governanca v1 (snapshot periódico) ----


class EvidenciaPeriodo(BaseModel):
    inicio: str = Field(max_length=10)  # YYYY-MM-DD
    fim: str = Field(max_length=10)


class EvidenceSnapshotCreateRequest(BaseModel):
    pct_sistemas_inventariados: float = Field(default=0, ge=0, le=1)
    tempo_medio_registro_dias: float = Field(default=0, ge=0)
    pct_sistemas_classificados: float = Field(default=0, ge=0, le=1)
    lead_time_avaliacao_dias: float = Field(default=0, ge=0)
    pct_acoes_criticas_com_hitl: float = Field(default=0, ge=0, le=1)
    tempo_reconstrucao_decisao_horas: float = Field(default=0, ge=0)
    pct_fichas_atualizadas_6m: float = Field(default=0, ge=0, le=1)
    bloqueios_guardrail_periodo: int = Field(default=0, ge=0)
    periodo: EvidenciaPeriodo
