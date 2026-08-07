"""Rotas públicas (sem autenticação) para showcase das trilhas e formulário de aplicação."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pymongo.database import Database
from pydantic import BaseModel, EmailStr, Field

from app import analytics
from app.database import get_db
from app.deps import get_optional_user
from app.limiter import limiter

router = APIRouter(prefix="/api/public", tags=["public"])


class TrackAccessRequest(BaseModel):
    """Chave do recurso aberto. O catálogo em `app.analytics` decide se ela vale."""

    resource_key: str = Field(min_length=1, max_length=80)


class LeadCreate(BaseModel):
    """Dados do formulário de solicitação de aplicação (landing)."""
    nome_completo: str
    cargo: str
    empresa: str
    faturamento_anual: str
    email: EmailStr
    contexto_ia: str | None = None
    num1: int  # número 1 da soma anti-robô (0–9)
    num2: int  # número 2 da soma anti-robô (0–9)
    captcha_answer: int  # resposta do usuário (deve ser num1 + num2)


def _course_summary(course: dict) -> dict:
    cab = (course.get("programa_formacao_executiva") or {}).get("cabecalho") or {}
    vg = (course.get("programa_formacao_executiva") or {}).get("visao_geral") or {}
    j = (course.get("programa_formacao_executiva") or {}).get("jornada_aprendizagem") or []
    total_enc = sum(len(s.get("encontros") or []) for s in j)
    return {
        "slug": course.get("slug"),
        "titulo": cab.get("titulo", course.get("slug", "")),
        "tema": cab.get("tema", ""),
        "trilha": cab.get("trilha", ""),
        "publico": cab.get("publico", ""),
        "objetivo": vg.get("objetivo", ""),
        "num_semanas": len(j),
        "num_encontros": total_enc,
    }


@router.get("/courses")
def list_courses_public(db: Database = Depends(get_db)):
    """Lista todas as trilhas com resumo para showcase. Público."""
    courses = list(db.courses.find({}))
    return [_course_summary(c) for c in courses]


@router.get("/courses/{slug}")
def get_course_public(slug: str, db: Database = Depends(get_db)):
    """Retorna uma trilha completa para exibição no showcase. Público."""
    course = db.courses.find_one({"slug": slug})
    if not course:
        raise HTTPException(status_code=404, detail="Trilha nao encontrada")
    payload = course.get("programa_formacao_executiva") or {}
    return {"slug": course["slug"], "programa_formacao_executiva": payload}


@router.get("/landing-materials")
def list_landing_materials_public(db: Database = Depends(get_db)):
    """Lista cards ativos de materiais gratuitos para a landing. Público."""
    docs = list(
        db.landing_materials.find({"active": True}).sort([("order", 1), ("created_at", 1)])
    )
    return [
        {
            "id": str(d["_id"]),
            "title": d.get("title", ""),
            "description": d.get("description", ""),
            "material_url": d.get("material_url", ""),
            "summary_url": d.get("summary_url", ""),
            "audio_url": d.get("audio_url") or None,
            "order": int(d.get("order") or 0),
        }
        for d in docs
    ]


@router.get("/landing-prompts")
def list_landing_prompts_public(db: Database = Depends(get_db)):
    """Lista prompts MD ativos para a landing. Público."""
    docs = list(
        db.landing_prompts.find({"active": True}).sort([("order", 1), ("created_at", 1)])
    )
    return [
        {
            "id": str(d["_id"]),
            "title": d.get("title", ""),
            "description": d.get("description", ""),
            "meta_label": d.get("meta_label") or "",
            "prompt_url": d.get("prompt_url", ""),
            "order": int(d.get("order") or 0),
        }
        for d in docs
    ]


@router.post("/track", status_code=204)
@limiter.limit("120/minute")
def track_resource_access(
    request: Request,
    payload: TrackAccessRequest,
    db: Database = Depends(get_db),
    user=Depends(get_optional_user),
) -> Response:
    """Registra a abertura de um recurso. Público: a calculadora e a landing não têm sessão.

    Chave desconhecida e visitante acima do teto do minuto também respondem 204: telemetria não
    pode virar erro para quem só está usando a plataforma, e distinguir "chave inválida" de
    "registrado" entregaria a um scanner quais chaves existem. O `@limiter` acima é a barreira
    externa contra enxurrada — o teto por visitante, em `analytics`, é o que protege a contagem.
    """
    resource_key = payload.resource_key.strip()
    category = analytics.resolve_category(db, resource_key)
    if category is not None:
        analytics.record_access(
            db,
            resource_key=resource_key,
            category=category,
            user=user,
            ip=request.client.host if request.client else "",
            user_agent=request.headers.get("user-agent", ""),
        )
    return Response(status_code=204)


@router.post("/leads")
def create_lead(payload: LeadCreate, db: Database = Depends(get_db)):
    """Recebe os dados do formulário de aplicação da landing e persiste como lead."""
    if payload.num1 + payload.num2 != payload.captcha_answer:
        raise HTTPException(
            status_code=400,
            detail="Resposta da verificação incorreta. Calcule a soma e tente novamente.",
        )
    doc = {
        "nome_completo": payload.nome_completo.strip(),
        "cargo": payload.cargo.strip(),
        "empresa": payload.empresa.strip(),
        "faturamento_anual": payload.faturamento_anual.strip(),
        "email": payload.email.strip().lower(),
        "contexto_ia": (payload.contexto_ia or "").strip() or None,
        "created_at": datetime.now(timezone.utc),
    }
    db.leads.insert_one(doc)
    return {"ok": True, "message": "Aplicação recebida. Entraremos em contato em até 24 horas úteis."}
