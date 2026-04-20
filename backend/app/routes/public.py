"""Rotas públicas (sem autenticação) para showcase das trilhas e formulário de aplicação."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pymongo.database import Database
from pydantic import BaseModel, EmailStr

from app.database import get_db

router = APIRouter(prefix="/api/public", tags=["public"])


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
