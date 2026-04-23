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


class GenericMessageResponse(BaseModel):
    message: str
    reset_token: str | None = None


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
