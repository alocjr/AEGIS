"""SWOT de IA — um documento de análise por mentorado."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pymongo.database import Database

from app.database import get_db
from app.deps import get_verified_user
from app.schemas import SwotAnalysisUpdateRequest, SwotInitiative

router = APIRouter(prefix="/api/swot-analysis", tags=["swot-analysis"])

_LIST_FIELDS = ("forcas", "fraquezas", "oportunidades", "ameacas")
_TOWS_FIELDS = ("tows_fo", "tows_fa", "tows_fxo", "tows_fxa")
_VEREDITO_TIPOS = frozenset({"executavel", "fundacao", "repensar", ""})

_EMPTY_FIELDS = {
    "optica": "",
    "forcas": [],
    "fraquezas": [],
    "oportunidades": [],
    "ameacas": [],
    "tows_fo": [],
    "tows_fa": [],
    "tows_fxo": [],
    "tows_fxa": [],
    "veredito_tipo": "",
    "veredito_titulo": "",
    "veredito_texto": "",
}


def _as_item_list(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if isinstance(value, list):
        out: list[str] = []
        for item in value:
            text = str(item or "").strip()
            if text:
                out.append(text[:500])
            if len(out) >= 40:
                break
        return out
    return []


def _clean_item_list(value: list[str] | None) -> list[str]:
    if not value:
        return []
    out: list[str] = []
    for item in value:
        text = (item or "").strip()[:500]
        if text:
            out.append(text)
        if len(out) >= 40:
            break
    return out


def _as_initiatives(value) -> list[dict]:
    if not isinstance(value, list):
        return []
    out: list[dict] = []
    for raw in value:
        if not isinstance(raw, dict):
            continue
        acao = str(raw.get("acao") or "").strip()[:1000]
        dono = str(raw.get("dono") or "").strip()[:200]
        horizonte = str(raw.get("horizonte") or "").strip()[:120]
        if not (acao or dono or horizonte):
            continue
        out.append({"acao": acao, "dono": dono, "horizonte": horizonte})
        if len(out) >= 20:
            break
    return out


def _clean_initiatives(value: list[SwotInitiative] | None) -> list[dict]:
    if not value:
        return []
    out: list[dict] = []
    for raw in value:
        acao = (raw.acao or "").strip()[:1000]
        dono = (raw.dono or "").strip()[:200]
        horizonte = (raw.horizonte or "").strip()[:120]
        if not (acao or dono or horizonte):
            continue
        out.append({"acao": acao, "dono": dono, "horizonte": horizonte})
        if len(out) >= 20:
            break
    return out


def _to_item(doc: dict) -> dict:
    created_at = doc.get("created_at")
    updated_at = doc.get("updated_at")
    return {
        "id": str(doc["_id"]),
        "optica": doc.get("optica") or "",
        "forcas": _as_item_list(doc.get("forcas")),
        "fraquezas": _as_item_list(doc.get("fraquezas")),
        "oportunidades": _as_item_list(doc.get("oportunidades")),
        "ameacas": _as_item_list(doc.get("ameacas")),
        "tows_fo": _as_initiatives(doc.get("tows_fo")),
        "tows_fa": _as_initiatives(doc.get("tows_fa")),
        "tows_fxo": _as_initiatives(doc.get("tows_fxo")),
        "tows_fxa": _as_initiatives(doc.get("tows_fxa")),
        "veredito_tipo": doc.get("veredito_tipo") or "",
        "veredito_titulo": doc.get("veredito_titulo") or "",
        "veredito_texto": doc.get("veredito_texto") or "",
        "created_at": created_at.isoformat() if created_at else None,
        "updated_at": updated_at.isoformat() if updated_at else None,
    }


def _get_or_create(db: Database, user_id) -> dict:
    doc = db.swot_analyses.find_one({"user_id": user_id})
    if doc:
        return doc
    now = datetime.now(timezone.utc)
    doc = {
        "user_id": user_id,
        **_EMPTY_FIELDS,
        "created_at": now,
        "updated_at": now,
    }
    result = db.swot_analyses.insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc


@router.get("")
def get_swot(user=Depends(get_verified_user), db: Database = Depends(get_db)):
    """Retorna a SWOT de IA do mentorado (cria vazia se ainda não existir)."""
    doc = _get_or_create(db, user["_id"])
    return _to_item(doc)


@router.put("")
def update_swot(
    body: SwotAnalysisUpdateRequest,
    user=Depends(get_verified_user),
    db: Database = Depends(get_db),
):
    """Atualiza a SWOT de IA do mentorado."""
    doc = _get_or_create(db, user["_id"])
    updates = body.model_dump(exclude_unset=True)

    for key in _LIST_FIELDS:
        if key in updates:
            updates[key] = _clean_item_list(updates.get(key))

    for key in _TOWS_FIELDS:
        if key in updates:
            updates[key] = _clean_initiatives(getattr(body, key))

    if "optica" in updates:
        updates["optica"] = (updates.get("optica") or "").strip()[:2000]
    if "veredito_titulo" in updates:
        updates["veredito_titulo"] = (updates.get("veredito_titulo") or "").strip()[:300]
    if "veredito_texto" in updates:
        updates["veredito_texto"] = (updates.get("veredito_texto") or "").strip()[:8000]
    if "veredito_tipo" in updates:
        tipo = (updates.get("veredito_tipo") or "").strip()
        updates["veredito_tipo"] = tipo if tipo in _VEREDITO_TIPOS else ""

    updates["updated_at"] = datetime.now(timezone.utc)
    db.swot_analyses.update_one({"_id": doc["_id"]}, {"$set": updates})
    refreshed = db.swot_analyses.find_one({"_id": doc["_id"]})
    return _to_item(refreshed or doc)
