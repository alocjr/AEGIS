from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=20, max_length=512)
    new_password: str = Field(min_length=6, max_length=128)


class VerifyEmailRequest(BaseModel):
    token: str = Field(min_length=20, max_length=512)


class GenericMessageResponse(BaseModel):
    message: str


class CompleteProgressResponse(BaseModel):
    concluidos: list[int]
    ativo: int
    total: int
    material_checks: dict[str, dict[str, str]]
    encontro_conclusoes: dict[str, str]


class MaterialCheckRequest(BaseModel):
    encontro_id: int
    material_index: int
    checked: bool
    course_slug: str | None = None  # trilha a usar; se omitido, usa a trilha principal do usuário


class MaturityAnswersRequest(BaseModel):
    answers: dict[str, int]
    tier: str = "basico"
    response_id: str | None = None


OPPORTUNITY_TYPE_OPTIONS = (
    "Automação",
    "Classificação/Previsão",
    "Extração/Busca",
    "Geração",
    "Copiloto",
    "Agente autônomo",
)


class CanvasProjectCreateRequest(BaseModel):
    title: str = Field(default="Novo projeto", min_length=1, max_length=200)


class CanvasDadosEstruturado(BaseModel):
    """Campo aditivo — preserva a estrutura de `dados` do aegis.canvas-oportunidades
    (perdida ao virar texto livre) para a regra R3 (canvas_para_risco_preliminar)."""

    descricao: str = Field(default="", max_length=1000)
    sensibilidade: Literal["publico", "interno", "pessoal", "sensivel"] | None = None


class CanvasRiscosEstruturado(BaseModel):
    """Campo aditivo — idem para `riscos` (regulatorio[] / human_in_the_loop)."""

    descricao: str = Field(default="", max_length=1000)
    regulatorio: list[str] = Field(default_factory=list, max_length=20)
    human_in_the_loop: Literal["nenhum", "sugerir", "aprovar", "supervisionar"] | None = None


class CanvasProjectUpdateRequest(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=200)
    area_negocio: str | None = Field(None, max_length=200)
    responsavel: str | None = Field(None, max_length=200)
    data: str | None = Field(None, max_length=40)
    objetivo_estrategico: str | None = Field(None, max_length=2000)
    contexto: list[str] | None = Field(None, max_length=40)
    dores: list[str] | None = Field(None, max_length=40)
    oportunidade: list[str] | None = Field(None, max_length=40)
    oportunidade_tipos: list[str] | None = Field(None, max_length=12)
    dados: list[str] | None = Field(None, max_length=40)
    valor: list[str] | None = Field(None, max_length=40)
    custo: list[str] | None = Field(None, max_length=40)
    riscos: list[str] | None = Field(None, max_length=40)
    score_valor: int | None = Field(None, ge=1, le=5)
    score_viabilidade: int | None = Field(None, ge=1, le=5)
    proximo_passo: str | None = Field(None, max_length=4000)
    dados_estruturado: CanvasDadosEstruturado | None = None
    riscos_estruturado: CanvasRiscosEstruturado | None = None
    # Origem estratégica: SWOT (e itens/iniciativas TOWS) que motivou o projeto
    swot_id: str | None = Field(None, max_length=24)
    swot_item_ids: list[str] | None = Field(None, max_length=20)
    tows_ids: list[str] | None = Field(None, max_length=20)
    justificativa_tows: str | None = Field(None, max_length=4000)
    # Key Results (OKR) que este projeto endereça
    kr_ids: list[str] | None = Field(None, max_length=20)


class CanvasImportRequest(BaseModel):
    """Envelope aegis.canvas-oportunidades (prompt → JSON importável)."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    schema_name: str | None = Field(None, alias="schema", max_length=80)
    versao: str | int | None = None
    status: str | None = Field(None, max_length=40)
    gerado_por: str | None = Field(None, max_length=80)
    projeto: dict[str, Any] | None = None
    areas: list[dict[str, Any]] | None = None
    roadmap: list[dict[str, Any]] | None = None


class SwotItem(BaseModel):
    """Item da matriz SWOT — amarrado a um pilar do quadrante (canônico ou custom)."""

    id: str = Field(default="", max_length=64)
    texto: str = Field(default="", max_length=500)
    pilar: str = Field(default="", max_length=40)
    # Pergunta do Modelo de Maturidade que originou o item (rastreabilidade)
    question_id: str = Field(default="", max_length=40)
    impacto: int | None = Field(None, ge=1, le=5)
    viabilidade: int | None = Field(None, ge=1, le=5)
    probabilidade: int | None = Field(None, ge=1, le=5)
    evidencia: str | None = Field(None, max_length=1000)
    prioridade: int | None = Field(None, ge=1, le=40)
    # Incluir este item no cruzamento TOWS
    tows: bool = True


class SwotPilarSlot(BaseModel):
    """Slot de pilar ativo em um quadrante (banco de itens + extras)."""

    id: str = Field(min_length=1, max_length=40)
    nome: str = Field(default="", max_length=80)


class SwotPilaresPorQuadrante(BaseModel):
    forcas: list[SwotPilarSlot] | None = Field(None, max_length=12)
    fraquezas: list[SwotPilarSlot] | None = Field(None, max_length=12)
    oportunidades: list[SwotPilarSlot] | None = Field(None, max_length=12)
    ameacas: list[SwotPilarSlot] | None = Field(None, max_length=12)


class SwotInitiative(BaseModel):
    id: str | None = Field(None, max_length=64)
    acao: str = Field(default="", max_length=1000)
    dono: str = Field(default="", max_length=200)
    horizonte: str = Field(default="", max_length=120)
    itens_internos: list[str] = Field(default_factory=list, max_length=10)
    itens_externos: list[str] = Field(default_factory=list, max_length=10)


class SwotWatchlistItem(BaseModel):
    """Ponto de Atenção (nota 3) — fora do SWOT/TOWS, gerado pelo Modelo de Maturidade."""

    id: str = Field(default="", max_length=64)
    texto: str = Field(default="", max_length=500)
    pilar: str = Field(default="", max_length=40)
    dimensao: str = Field(default="", max_length=120)
    nota: int | None = Field(None, ge=1, le=5)
    evidencia: str = Field(default="", max_length=1000)
    swotCategory: str | None = Field(None, max_length=40)


class SwotAnalysisUpdateRequest(BaseModel):
    optica: str | None = Field(None, max_length=2000)
    pilares: SwotPilaresPorQuadrante | None = None
    forcas: list[SwotItem | str] | None = Field(None, max_length=40)
    fraquezas: list[SwotItem | str] | None = Field(None, max_length=40)
    oportunidades: list[SwotItem | str] | None = Field(None, max_length=40)
    ameacas: list[SwotItem | str] | None = Field(None, max_length=40)
    watchlist: list[SwotWatchlistItem] | None = Field(None, max_length=48)
    tows_fo: list[SwotInitiative] | None = Field(None, max_length=20)
    tows_fa: list[SwotInitiative] | None = Field(None, max_length=20)
    tows_fxo: list[SwotInitiative] | None = Field(None, max_length=20)
    tows_fxa: list[SwotInitiative] | None = Field(None, max_length=20)
    veredito_tipo: str | None = Field(None, max_length=40)
    veredito_titulo: str | None = Field(None, max_length=300)
    veredito_texto: str | None = Field(None, max_length=8000)


class SwotImportRequest(BaseModel):
    """Envelope aegis.swot-ia (v1–v3) ou payload direto."""

    format: str | None = None
    version: int | None = None
    payload: SwotAnalysisUpdateRequest | None = None
    # Campos do payload também aceitos no root (import sem envelope)
    optica: str | None = Field(None, max_length=2000)
    pilares: SwotPilaresPorQuadrante | None = None
    forcas: list[SwotItem | str] | None = Field(None, max_length=40)
    fraquezas: list[SwotItem | str] | None = Field(None, max_length=40)
    oportunidades: list[SwotItem | str] | None = Field(None, max_length=40)
    ameacas: list[SwotItem | str] | None = Field(None, max_length=40)
    watchlist: list[SwotWatchlistItem] | None = Field(None, max_length=48)
    tows_fo: list[SwotInitiative] | None = Field(None, max_length=20)
    tows_fa: list[SwotInitiative] | None = Field(None, max_length=20)
    tows_fxo: list[SwotInitiative] | None = Field(None, max_length=20)
    tows_fxa: list[SwotInitiative] | None = Field(None, max_length=20)
    veredito_tipo: str | None = Field(None, max_length=40)
    veredito_titulo: str | None = Field(None, max_length=300)
    veredito_texto: str | None = Field(None, max_length=8000)


class KeyResult(BaseModel):
    """Resultado-chave de um Objective — meta numérica baseline → current → target."""

    id: str | None = Field(None, max_length=64)
    titulo: str = Field(default="", max_length=300)
    descricao: str = Field(default="", max_length=1000)
    unidade: str = Field(default="", max_length=40)
    baseline: float = 0.0
    current: float = 0.0
    target: float = 0.0
    direction: Literal["increase", "decrease"] = "increase"
    dono: str = Field(default="", max_length=200)


class Objective(BaseModel):
    """Objetivo de um ciclo OKR — vinculado à SWOT/TOWS que o originou."""

    id: str | None = Field(None, max_length=64)
    titulo: str = Field(default="", max_length=300)
    descricao: str = Field(default="", max_length=2000)
    dono: str = Field(default="", max_length=200)
    pilar: str = Field(default="", max_length=40)
    # Origem estratégica: mesmo shape de CanvasProjectUpdateRequest.swot_id/swot_item_ids/tows_ids
    swot_id: str | None = Field(None, max_length=24)
    swot_item_ids: list[str] = Field(default_factory=list, max_length=20)
    tows_ids: list[str] = Field(default_factory=list, max_length=20)
    key_results: list[KeyResult] = Field(default_factory=list, max_length=20)


class OkrCycleCreateRequest(BaseModel):
    tipo: Literal["trimestre", "ano"] = "trimestre"
    ano: int = Field(ge=2020, le=2100)
    trimestre: int | None = Field(None, ge=1, le=4)
    nome: str | None = Field(None, max_length=120)


class OkrCycleUpdateRequest(BaseModel):
    """Full-replace do ciclo (objectives inteiro) — mesmo padrão de SwotAnalysisUpdateRequest.

    `status` fica de fora de propósito: só muda via /activate e /archive, protegendo o
    invariante "um único ciclo ativo por organização" de ser burlado por um PUT genérico.
    """

    nome: str | None = Field(None, max_length=120)
    tipo: Literal["trimestre", "ano"] | None = None
    ano: int | None = Field(None, ge=2020, le=2100)
    trimestre: int | None = Field(None, ge=1, le=4)
    objectives: list[Objective] | None = Field(None, max_length=20)


class QuizSubmitRequest(BaseModel):
    answers: dict[str, int]


class AdminCreateUserRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    course_slugs: list[str] = Field(default_factory=list, max_length=50)  # vazio = sem trilha (ex.: membro de organização)
    phone: str | None = Field(None, max_length=30)  # telefone completo para WhatsApp (ex.: 5511987654321)
    encontro_agendas: dict[str, str] | None = None  # encontro_id -> ISO datetime string (aplica à primeira trilha)
    organization_id: str | None = Field(None, max_length=24)  # se omitido, cria organização solo


class AdminUpdateUserRequest(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=120)
    email: EmailStr | None = None
    password: str | None = Field(None, min_length=6, max_length=128)
    course_slugs: list[str] | None = Field(None, max_length=50)  # None = não altera; [] = remove trilha
    phone: str | None = Field(None, max_length=30)
    is_admin: bool | None = None
    is_org_admin: bool | None = None
    encontro_agendas: dict[str, str] | None = None
    organization_id: str | None = Field(None, max_length=24)  # move o usuário para outra organização


class OrgMemberCreateRequest(BaseModel):
    """Usuário criado por um admin de organização — nunca ganha trilha (só o admin da
    plataforma atribui mentoria)."""

    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    phone: str | None = Field(None, max_length=30)


class OrgMemberUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=120)
    email: EmailStr | None = None
    password: str | None = Field(None, min_length=6, max_length=128)
    phone: str | None = Field(None, max_length=30)


class OrganizationCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=200)


# Limite razoável para payload de curso (evita DoS por body gigante)
_MAX_COURSE_PAYLOAD_JSON_SIZE = 2 * 1024 * 1024  # 2 MiB


def _check_payload_size(v: dict[str, Any], max_bytes: int = _MAX_COURSE_PAYLOAD_JSON_SIZE) -> dict[str, Any]:
    import json
    raw = json.dumps(v)
    if len(raw.encode("utf-8")) > max_bytes:
        raise ValueError("Payload excede tamanho máximo permitido")
    return v


class AdminCreateCourseRequest(BaseModel):
    slug: str = Field(min_length=1, max_length=200)
    programa_formacao_executiva: dict[str, Any] = Field(default_factory=dict)

    @field_validator("programa_formacao_executiva")
    @classmethod
    def validate_pfe_size(cls, v: dict[str, Any]) -> dict[str, Any]:
        return _check_payload_size(v)


class AdminUpdateCourseRequest(BaseModel):
    programa_formacao_executiva: dict[str, Any]

    @field_validator("programa_formacao_executiva")
    @classmethod
    def validate_pfe_size(cls, v: dict[str, Any]) -> dict[str, Any]:
        return _check_payload_size(v)


class LiberarEncontroRequest(BaseModel):
    encontro_id: int


class AdminUpdateProgressRequest(BaseModel):
    """Atualiza progresso do aluno (ex.: agendas dos encontros) para uma trilha específica."""
    course_slug: str = Field(min_length=1, max_length=200)
    encontro_agendas: dict[str, str] = Field(default_factory=dict)  # encontro_id -> ISO datetime string


class AdminQuizCreateUpdateRequest(BaseModel):
    encontro: int
    titulo: str | None = Field(None, max_length=300)
    questoes: list[dict[str, Any]] = Field(default_factory=list, max_length=100)


class AdminLandingMaterialCreateRequest(BaseModel):
    """Card de material gratuito exibido na landing."""
    title: str = Field(min_length=2, max_length=200)
    description: str = Field(min_length=1, max_length=2000)
    material_url: str = Field(min_length=1, max_length=2000)
    summary_url: str = Field(min_length=1, max_length=2000)
    audio_url: str | None = Field(None, max_length=2000)
    order: int = Field(default=0, ge=0, le=9999)
    active: bool = True


class AdminLandingMaterialUpdateRequest(BaseModel):
    title: str | None = Field(None, min_length=2, max_length=200)
    description: str | None = Field(None, min_length=1, max_length=2000)
    material_url: str | None = Field(None, min_length=1, max_length=2000)
    summary_url: str | None = Field(None, min_length=1, max_length=2000)
    audio_url: str | None = Field(None, max_length=2000)
    order: int | None = Field(None, ge=0, le=9999)
    active: bool | None = None


class AdminLandingPromptCreateRequest(BaseModel):
    """Prompt MD exibido na landing."""
    title: str = Field(min_length=2, max_length=200)
    description: str = Field(min_length=1, max_length=2000)
    meta_label: str = Field(default="", max_length=200)
    prompt_url: str = Field(min_length=1, max_length=2000)
    order: int = Field(default=0, ge=0, le=9999)
    active: bool = True


class AdminLandingPromptUpdateRequest(BaseModel):
    title: str | None = Field(None, min_length=2, max_length=200)
    description: str | None = Field(None, min_length=1, max_length=2000)
    meta_label: str | None = Field(None, max_length=200)
    prompt_url: str | None = Field(None, min_length=1, max_length=2000)
    order: int | None = Field(None, ge=0, le=9999)
    active: bool | None = None
