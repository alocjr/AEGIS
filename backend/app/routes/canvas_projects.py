"""Canvas de Oportunidades de IA por área — projetos do mentorado."""

from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pymongo.database import Database

from app.database import get_db
from app.deps import get_verified_user
from app.schemas import (
    OPPORTUNITY_TYPE_OPTIONS,
    CanvasProjectCreateRequest,
    CanvasProjectUpdateRequest,
)

router = APIRouter(prefix="/api/canvas-projects", tags=["canvas-projects"])

_EMPTY_FIELDS = {
    "area_negocio": "",
    "responsavel": "",
    "data": "",
    "objetivo_estrategico": "",
    "contexto": "",
    "dores": "",
    "oportunidade": "",
    "oportunidade_tipos": [],
    "dados": "",
    "valor": "",
    "custo": "",
    "riscos": "",
    "score_valor": None,
    "score_viabilidade": None,
    "proximo_passo": "",
}


def _quadrant(score_valor: int | None, score_viabilidade: int | None) -> str | None:
    if score_valor is None or score_viabilidade is None:
        return None
    high_v = score_valor >= 4
    high_f = score_viabilidade >= 4
    if high_v and high_f:
        return "ganho_rapido"
    if high_v and not high_f:
        return "aposta_estrategica"
    if not high_v and high_f:
        return "incremental"
    return "evitar"


def _to_item(doc: dict, *, summary: bool = False) -> dict:
    score_valor = doc.get("score_valor")
    score_viabilidade = doc.get("score_viabilidade")
    created_at = doc.get("created_at")
    updated_at = doc.get("updated_at")
    base = {
        "id": str(doc["_id"]),
        "title": doc.get("title") or "Novo projeto",
        "area_negocio": doc.get("area_negocio") or "",
        "responsavel": doc.get("responsavel") or "",
        "updated_at": updated_at.isoformat() if updated_at else None,
        "created_at": created_at.isoformat() if created_at else None,
        "quadrant": _quadrant(
            int(score_valor) if score_valor is not None else None,
            int(score_viabilidade) if score_viabilidade is not None else None,
        ),
        "score_valor": score_valor,
        "score_viabilidade": score_viabilidade,
    }
    if summary:
        return base
    return {
        **base,
        "data": doc.get("data") or "",
        "objetivo_estrategico": doc.get("objetivo_estrategico") or "",
        "contexto": doc.get("contexto") or "",
        "dores": doc.get("dores") or "",
        "oportunidade": doc.get("oportunidade") or "",
        "oportunidade_tipos": list(doc.get("oportunidade_tipos") or []),
        "dados": doc.get("dados") or "",
        "valor": doc.get("valor") or "",
        "custo": doc.get("custo") or "",
        "riscos": doc.get("riscos") or "",
        "proximo_passo": doc.get("proximo_passo") or "",
        "opportunity_type_options": list(OPPORTUNITY_TYPE_OPTIONS),
    }


def _get_owned(db: Database, user_id, project_id: str) -> dict:
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=400, detail="ID invalido")
    doc = db.canvas_projects.find_one({"_id": ObjectId(project_id), "user_id": user_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Projeto nao encontrado")
    return doc


@router.get("")
def list_projects(user=Depends(get_verified_user), db: Database = Depends(get_db)):
    """Lista projetos (canvas) do mentorado — mais recentes primeiro."""
    cursor = db.canvas_projects.find({"user_id": user["_id"]}).sort("updated_at", -1)
    return {"items": [_to_item(d, summary=True) for d in cursor]}


@router.post("")
def create_project(
    body: CanvasProjectCreateRequest,
    user=Depends(get_verified_user),
    db: Database = Depends(get_db),
):
    """Cria um novo projeto/canvas vazio."""
    now = datetime.now(timezone.utc)
    title = (body.title or "Novo projeto").strip() or "Novo projeto"
    doc = {
        "user_id": user["_id"],
        "title": title,
        **_EMPTY_FIELDS,
        "created_at": now,
        "updated_at": now,
    }
    result = db.canvas_projects.insert_one(doc)
    doc["_id"] = result.inserted_id
    return _to_item(doc)


@router.get("/{project_id}")
def get_project(
    project_id: str,
    user=Depends(get_verified_user),
    db: Database = Depends(get_db),
):
    doc = _get_owned(db, user["_id"], project_id)
    return _to_item(doc)


@router.put("/{project_id}")
def update_project(
    project_id: str,
    body: CanvasProjectUpdateRequest,
    user=Depends(get_verified_user),
    db: Database = Depends(get_db),
):
    """Salva preenchimento do canvas."""
    _get_owned(db, user["_id"], project_id)
    updates: dict = {"updated_at": datetime.now(timezone.utc)}
    data = body.model_dump(exclude_unset=True)

    if "oportunidade_tipos" in data and data["oportunidade_tipos"] is not None:
        allowed = set(OPPORTUNITY_TYPE_OPTIONS)
        cleaned = [t for t in data["oportunidade_tipos"] if t in allowed]
        updates["oportunidade_tipos"] = cleaned

    for key, value in data.items():
        if key == "oportunidade_tipos":
            continue
        if value is None and key in ("score_valor", "score_viabilidade"):
            updates[key] = None
        elif isinstance(value, str):
            updates[key] = value.strip() if key == "title" else value
        elif value is not None:
            updates[key] = value

    # Título automático a partir da área, se o título ainda for o padrão
    if "area_negocio" in updates:
        area = (updates.get("area_negocio") or "").strip()
        existing = db.canvas_projects.find_one(
            {"_id": ObjectId(project_id)}, {"title": 1}
        )
        current_title = (existing or {}).get("title") or ""
        if area and (not current_title or current_title == "Novo projeto") and "title" not in data:
            updates["title"] = area[:200]

    db.canvas_projects.update_one(
        {"_id": ObjectId(project_id), "user_id": user["_id"]},
        {"$set": updates},
    )
    doc = _get_owned(db, user["_id"], project_id)
    return _to_item(doc)


@router.delete("/{project_id}")
def delete_project(
    project_id: str,
    user=Depends(get_verified_user),
    db: Database = Depends(get_db),
):
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=400, detail="ID invalido")
    result = db.canvas_projects.delete_one(
        {"_id": ObjectId(project_id), "user_id": user["_id"]}
    )
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Projeto nao encontrado")
    return {"message": "Projeto removido", "id": project_id}
