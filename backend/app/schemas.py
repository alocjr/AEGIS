from typing import Any

from pydantic import BaseModel, EmailStr, Field, field_validator


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


class SwotInitiative(BaseModel):
    acao: str = Field(default="", max_length=1000)
    dono: str = Field(default="", max_length=200)
    horizonte: str = Field(default="", max_length=120)


class SwotAnalysisUpdateRequest(BaseModel):
    optica: str | None = Field(None, max_length=2000)
    forcas: list[str] | None = Field(None, max_length=40)
    fraquezas: list[str] | None = Field(None, max_length=40)
    oportunidades: list[str] | None = Field(None, max_length=40)
    ameacas: list[str] | None = Field(None, max_length=40)
    tows_fo: list[SwotInitiative] | None = Field(None, max_length=20)
    tows_fa: list[SwotInitiative] | None = Field(None, max_length=20)
    tows_fxo: list[SwotInitiative] | None = Field(None, max_length=20)
    tows_fxa: list[SwotInitiative] | None = Field(None, max_length=20)
    veredito_tipo: str | None = Field(None, max_length=40)
    veredito_titulo: str | None = Field(None, max_length=300)
    veredito_texto: str | None = Field(None, max_length=8000)


class QuizSubmitRequest(BaseModel):
    answers: dict[str, int]


class AdminCreateUserRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    course_slugs: list[str] = Field(min_length=1, max_length=50)  # uma ou mais trilhas
    phone: str | None = Field(None, max_length=30)  # telefone completo para WhatsApp (ex.: 5511987654321)
    encontro_agendas: dict[str, str] | None = None  # encontro_id -> ISO datetime string (aplica à primeira trilha)


class AdminUpdateUserRequest(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=120)
    email: EmailStr | None = None
    password: str | None = Field(None, min_length=6, max_length=128)
    course_slugs: list[str] | None = Field(None, min_length=1, max_length=50)  # uma ou mais trilhas
    phone: str | None = Field(None, max_length=30)
    is_admin: bool | None = None
    encontro_agendas: dict[str, str] | None = None


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
