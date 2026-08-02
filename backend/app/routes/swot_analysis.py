"""SWOT de IA — documentos por mentorado (modelo v3); um SWOT por resposta de maturidade."""

from __future__ import annotations

import re
import secrets
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from pymongo.database import Database

from app.database import get_db
from app.deps import get_verified_user
from app.schemas import (
    SwotAnalysisUpdateRequest,
    SwotImportRequest,
    SwotInitiative,
    SwotItem,
    SwotPilaresPorQuadrante,
    SwotWatchlistItem,
)
from app.swot_from_maturity import build_swot_fields_from_maturity, build_tows_from_swot

router = APIRouter(prefix="/api/swot-analysis", tags=["swot-analysis"])

_LIST_FIELDS = ("forcas", "fraquezas", "oportunidades", "ameacas")
_TOWS_FIELDS = ("tows_fo", "tows_fa", "tows_fxo", "tows_fxa")
_INTERNAL_FIELDS = frozenset({"forcas", "fraquezas"})
_VEREDITO_TIPOS = frozenset({"executavel", "sustenta", "fundacao", "repensar", ""})
# Pilares canônicos + slugs custom (banco de itens / UI / import v3).
_PILLAR_RE = re.compile(r"^[a-z][a-z0-9_-]{0,39}$")
_FIELD_ID_PREFIX = {
    "forcas": "f",
    "fraquezas": "fx",
    "oportunidades": "o",
    "ameacas": "a",
}

_EMPTY_PILARES = {
    "forcas": [],
    "fraquezas": [],
    "oportunidades": [],
    "ameacas": [],
}

_EMPTY_FIELDS = {
    "optica": "",
    "pilares": {**_EMPTY_PILARES},
    "forcas": [],
    "fraquezas": [],
    "oportunidades": [],
    "ameacas": [],
    "watchlist": [],
    "tows_fo": [],
    "tows_fa": [],
    "tows_fxo": [],
    "tows_fxa": [],
    "veredito_tipo": "",
    "veredito_titulo": "",
    "veredito_texto": "",
}


def _new_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(4)}"


def _score(value) -> int | None:
    if value is None or value == "":
        return None
    try:
        n = int(value)
    except (TypeError, ValueError):
        return None
    return n if 1 <= n <= 5 else None


def _priority(value) -> int | None:
    if value is None or value == "":
        return None
    try:
        n = int(value)
    except (TypeError, ValueError):
        return None
    return n if 1 <= n <= 40 else None


def _normalize_item(raw, field: str, used_ids: set[str]) -> dict | None:
    """Aceita string (v1) ou dict/SwotItem (v2) e devolve dict limpo."""
    prefix = _FIELD_ID_PREFIX[field]
    if isinstance(raw, str):
        texto = raw.strip()[:500]
        if not texto:
            return None
        item_id = _new_id(prefix)
        used_ids.add(item_id)
        return {
            "id": item_id,
            "texto": texto,
            "pilar": "",
            "impacto": None,
            "viabilidade": None,
            "probabilidade": None,
            "evidencia": "",
            "prioridade": None,
            "tows": True,
        }

    if isinstance(raw, SwotItem):
        data = raw.model_dump()
    elif isinstance(raw, dict):
        data = raw
    else:
        return None

    texto = str(data.get("texto") or "").strip()[:500]
    if not texto:
        return None

    pilar = str(data.get("pilar") or "").strip().lower()
    if pilar and not _PILLAR_RE.fullmatch(pilar):
        pilar = ""
    # Aceita canônicos e slugs custom criados na UI.

    item_id = str(data.get("id") or "").strip()[:64]
    if not item_id or item_id in used_ids:
        item_id = _new_id(prefix)
    used_ids.add(item_id)

    evidencia = str(data.get("evidencia") or "").strip()[:1000]
    impacto = _score(data.get("impacto"))
    viabilidade = _score(data.get("viabilidade")) if field in _INTERNAL_FIELDS else None
    probabilidade = _score(data.get("probabilidade")) if field not in _INTERNAL_FIELDS else None

    tows_flag = data.get("tows")
    if tows_flag is None:
        tows_flag = True

    return {
        "id": item_id,
        "texto": texto,
        "pilar": pilar,
        "impacto": impacto,
        "viabilidade": viabilidade,
        "probabilidade": probabilidade,
        "evidencia": evidencia,
        "prioridade": _priority(data.get("prioridade")),
        "tows": bool(tows_flag),
    }


def _as_item_list(value, field: str) -> list[dict]:
    if value is None:
        return []
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return []
    out: list[dict] = []
    used_ids: set[str] = set()
    for raw in value:
        item = _normalize_item(raw, field, used_ids)
        if item:
            out.append(item)
        if len(out) >= 40:
            break
    return out


def _clean_item_list(value: list[SwotItem | str] | None, field: str) -> list[dict]:
    if not value:
        return []
    out: list[dict] = []
    used_ids: set[str] = set()
    for raw in value:
        item = _normalize_item(raw, field, used_ids)
        if item:
            out.append(item)
        if len(out) >= 40:
            break
    return out


def _id_list(value, max_items: int = 10) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for raw in value:
        text = str(raw or "").strip()[:64]
        if text and text not in out:
            out.append(text)
        if len(out) >= max_items:
            break
    return out


def _as_initiatives(value) -> list[dict]:
    if not isinstance(value, list):
        return []
    out: list[dict] = []
    used_ids: set[str] = set()
    for raw in value:
        if isinstance(raw, SwotInitiative):
            data = raw.model_dump()
        elif isinstance(raw, dict):
            data = raw
        else:
            continue
        acao = str(data.get("acao") or "").strip()[:1000]
        dono = str(data.get("dono") or "").strip()[:200]
        horizonte = str(data.get("horizonte") or "").strip()[:120]
        if not (acao or dono or horizonte):
            continue
        init_id = str(data.get("id") or "").strip()[:64]
        if not init_id or init_id in used_ids:
            init_id = _new_id("t")
        used_ids.add(init_id)
        out.append(
            {
                "id": init_id,
                "acao": acao,
                "dono": dono,
                "horizonte": horizonte,
                "itens_internos": _id_list(data.get("itens_internos")),
                "itens_externos": _id_list(data.get("itens_externos")),
            }
        )
        if len(out) >= 20:
            break
    return out


def _clean_initiatives(value: list[SwotInitiative] | None) -> list[dict]:
    if not value:
        return []
    return _as_initiatives(value)


def _clean_pillar_slots(value) -> list[dict]:
    if not isinstance(value, list):
        return []
    out: list[dict] = []
    seen: set[str] = set()
    for raw in value:
        if isinstance(raw, str):
            pilar_id = raw.strip().lower()
            nome = ""
        elif isinstance(raw, dict):
            pilar_id = str(raw.get("id") or "").strip().lower()
            nome = str(raw.get("nome") or "").strip()[:80]
        else:
            continue
        if not _PILLAR_RE.fullmatch(pilar_id) or pilar_id in seen:
            continue
        seen.add(pilar_id)
        out.append({"id": pilar_id, "nome": nome})
        if len(out) >= 12:
            break
    return out


def _clean_pilares(value: SwotPilaresPorQuadrante | dict | None) -> dict:
    if value is None:
        return {field: [] for field in _LIST_FIELDS}
    if isinstance(value, SwotPilaresPorQuadrante):
        data = value.model_dump(exclude_unset=False)
    elif isinstance(value, dict):
        data = value
    else:
        return {field: [] for field in _LIST_FIELDS}
    return {field: _clean_pillar_slots(data.get(field)) for field in _LIST_FIELDS}


def _as_pilares(doc: dict) -> dict:
    raw = doc.get("pilares")
    if not isinstance(raw, dict):
        return {field: [] for field in _LIST_FIELDS}
    return _clean_pilares(raw)


def _clean_watchlist(value) -> list[dict]:
    if not isinstance(value, list):
        return []
    out: list[dict] = []
    seen: set[str] = set()
    for raw in value:
        if isinstance(raw, SwotWatchlistItem):
            data = raw.model_dump()
        elif isinstance(raw, dict):
            data = raw
        else:
            continue
        item_id = str(data.get("id") or "").strip()[:64]
        texto = str(data.get("texto") or "").strip()[:500]
        if not texto:
            continue
        if item_id and item_id in seen:
            continue
        if item_id:
            seen.add(item_id)
        nota = data.get("nota")
        try:
            nota_n = int(nota) if nota is not None and nota != "" else None
        except (TypeError, ValueError):
            nota_n = None
        if nota_n is not None and (nota_n < 1 or nota_n > 5):
            nota_n = None
        cat = str(data.get("swotCategory") or data.get("swot_category") or "").strip()[:40]
        out.append(
            {
                "id": item_id,
                "texto": texto,
                "pilar": str(data.get("pilar") or "").strip().lower()[:40],
                "dimensao": str(data.get("dimensao") or "").strip()[:120],
                "nota": nota_n,
                "evidencia": str(data.get("evidencia") or "").strip()[:1000],
                "swotCategory": cat or None,
            }
        )
        if len(out) >= 48:
            break
    return out


def _to_item(doc: dict) -> dict:
    created_at = doc.get("created_at")
    updated_at = doc.get("updated_at")
    mid = doc.get("maturity_response_id")
    return {
        "id": str(doc["_id"]),
        "maturity_response_id": str(mid) if mid else None,
        "optica": doc.get("optica") or "",
        "pilares": _as_pilares(doc),
        "forcas": _as_item_list(doc.get("forcas"), "forcas"),
        "fraquezas": _as_item_list(doc.get("fraquezas"), "fraquezas"),
        "oportunidades": _as_item_list(doc.get("oportunidades"), "oportunidades"),
        "ameacas": _as_item_list(doc.get("ameacas"), "ameacas"),
        "watchlist": _clean_watchlist(doc.get("watchlist")),
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


def _get_latest(db: Database, user_id) -> dict | None:
    return db.swot_analyses.find_one({"user_id": user_id}, sort=[("updated_at", -1), ("_id", -1)])


def _get_or_create_latest(db: Database, user_id) -> dict:
    """SWOT mais recente do usuário; cria documento vazio se não houver nenhum."""
    doc = _get_latest(db, user_id)
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


def _require_owned(db: Database, user_id, swot_id: str) -> dict:
    if not ObjectId.is_valid(swot_id):
        raise HTTPException(status_code=404, detail="SWOT não encontrada")
    doc = db.swot_analyses.find_one({"_id": ObjectId(swot_id), "user_id": user_id})
    if not doc:
        raise HTTPException(status_code=404, detail="SWOT não encontrada")
    return doc


def _get_by_maturity(db: Database, user_id, maturity_response_id: ObjectId) -> dict | None:
    return db.swot_analyses.find_one(
        {"user_id": user_id, "maturity_response_id": maturity_response_id}
    )


def _model_for_swot(db: Database, doc: dict, user_id) -> dict | None:
    """Modelo de maturidade ligado à SWOT (via maturity_response), senão o ativo."""
    from app.routes.maturity import _load_model, _serialize_model

    mid = doc.get("maturity_response_id")
    if mid:
        mat = db.maturity_responses.find_one({"_id": mid, "user_id": user_id})
        if mat and mat.get("model_id"):
            model_doc = db.ai_maturity_model.find_one({"_id": mat["model_id"]})
            if model_doc and model_doc.get("dimensions"):
                return _serialize_model(model_doc)
    try:
        return _load_model(db)
    except HTTPException:
        return None


def _rebuild_tows_on_doc(doc: dict, db: Database, user_id) -> dict:
    """Recalcula TOWS a partir dos itens SWOT com tows=True e persiste."""
    model = _model_for_swot(db, doc, user_id)
    tows = build_tows_from_swot(
        forcas=doc.get("forcas") or [],
        fraquezas=doc.get("fraquezas") or [],
        oportunidades=doc.get("oportunidades") or [],
        ameacas=doc.get("ameacas") or [],
        model=model,
    )
    now = datetime.now(timezone.utc)
    db.swot_analyses.update_one(
        {"_id": doc["_id"]},
        {"$set": {**tows, "updated_at": now}},
    )
    doc.update(tows)
    doc["updated_at"] = now
    return doc


def _apply_updates(doc: dict, body: SwotAnalysisUpdateRequest, db: Database) -> dict:
    updates = body.model_dump(exclude_unset=True)

    for key in _LIST_FIELDS:
        if key in updates:
            updates[key] = _clean_item_list(getattr(body, key), key)

    for key in _TOWS_FIELDS:
        if key in updates:
            updates[key] = _clean_initiatives(getattr(body, key))

    if "pilares" in updates:
        updates["pilares"] = _clean_pilares(getattr(body, "pilares", None))

    if "watchlist" in updates:
        updates["watchlist"] = _clean_watchlist(getattr(body, "watchlist", None))

    if "optica" in updates:
        updates["optica"] = (updates.get("optica") or "").strip()[:2000]
    if "veredito_titulo" in updates:
        updates["veredito_titulo"] = (updates.get("veredito_titulo") or "").strip()[:300]
    if "veredito_texto" in updates:
        updates["veredito_texto"] = (updates.get("veredito_texto") or "").strip()[:8000]
    if "veredito_tipo" in updates:
        tipo = (updates.get("veredito_tipo") or "").strip()
        # Alias do prompt/método Valorian
        if tipo == "sustenta":
            tipo = "executavel"
        updates["veredito_tipo"] = tipo if tipo in _VEREDITO_TIPOS else ""

    updates["updated_at"] = datetime.now(timezone.utc)
    db.swot_analyses.update_one({"_id": doc["_id"]}, {"$set": updates})
    return db.swot_analyses.find_one({"_id": doc["_id"]}) or doc


def _payload_from_import(body: SwotImportRequest) -> SwotAnalysisUpdateRequest:
    fmt = (body.format or "").strip()
    if fmt and fmt != "aegis.swot-ia":
        raise HTTPException(status_code=400, detail="Formato inválido. Esperado format=aegis.swot-ia.")
    if body.version is not None and body.version not in (1, 2, 3):
        raise HTTPException(status_code=400, detail="Versão não suportada. Use version 1, 2 ou 3.")

    if body.payload is not None:
        return body.payload

    data = body.model_dump(
        exclude_unset=True,
        exclude={"format", "version", "payload"},
    )
    if not data:
        raise HTTPException(status_code=400, detail="JSON sem payload SWOT.")
    return SwotAnalysisUpdateRequest(**data)


def _needs_v2_migration(doc: dict) -> bool:
    for field in _LIST_FIELDS:
        raw = doc.get(field)
        if isinstance(raw, str):
            return True
        if isinstance(raw, list):
            for item in raw:
                if isinstance(item, str):
                    return True
                if isinstance(item, dict) and not item.get("id"):
                    return True
    for field in _TOWS_FIELDS:
        raw = doc.get(field)
        if isinstance(raw, list):
            for item in raw:
                if isinstance(item, dict) and not item.get("id") and (
                    item.get("acao") or item.get("dono") or item.get("horizonte")
                ):
                    return True
    return False


def _migrate_doc_to_v2(doc: dict, db: Database) -> dict:
    """Persiste itens/iniciativas no formato v2 na primeira leitura pós-upgrade."""
    if not _needs_v2_migration(doc):
        return doc
    updates = {
        "forcas": _as_item_list(doc.get("forcas"), "forcas"),
        "fraquezas": _as_item_list(doc.get("fraquezas"), "fraquezas"),
        "oportunidades": _as_item_list(doc.get("oportunidades"), "oportunidades"),
        "ameacas": _as_item_list(doc.get("ameacas"), "ameacas"),
        "tows_fo": _as_initiatives(doc.get("tows_fo")),
        "tows_fa": _as_initiatives(doc.get("tows_fa")),
        "tows_fxo": _as_initiatives(doc.get("tows_fxo")),
        "tows_fxa": _as_initiatives(doc.get("tows_fxa")),
        "updated_at": datetime.now(timezone.utc),
    }
    db.swot_analyses.update_one({"_id": doc["_id"]}, {"$set": updates})
    return db.swot_analyses.find_one({"_id": doc["_id"]}) or {**doc, **updates}


@router.get("")
def get_swot(user=Depends(get_verified_user), db: Database = Depends(get_db)):
    """Retorna a SWOT mais recente do mentorado (cria vazia se ainda não existir)."""
    doc = _migrate_doc_to_v2(_get_or_create_latest(db, user["_id"]), db)
    return _to_item(doc)


@router.get("/by-maturity/{maturity_response_id}")
def get_swot_by_maturity(
    maturity_response_id: str,
    user=Depends(get_verified_user),
    db: Database = Depends(get_db),
):
    """Retorna a SWOT vinculada a uma resposta de maturidade (404 se não existir)."""
    if not ObjectId.is_valid(maturity_response_id):
        raise HTTPException(status_code=404, detail="SWOT não encontrada")
    doc = _get_by_maturity(db, user["_id"], ObjectId(maturity_response_id))
    if not doc:
        raise HTTPException(status_code=404, detail="SWOT não encontrada")
    return _to_item(_migrate_doc_to_v2(doc, db))


@router.post("/from-maturity/{maturity_response_id}")
def create_swot_from_maturity(
    maturity_response_id: str,
    user=Depends(get_verified_user),
    db: Database = Depends(get_db),
):
    """Cria ou atualiza a SWOT gerada a partir de uma resposta do Modelo de Maturidade."""
    if not ObjectId.is_valid(maturity_response_id):
        raise HTTPException(status_code=404, detail="Resposta de maturidade não encontrada")
    mid = ObjectId(maturity_response_id)
    maturity = db.maturity_responses.find_one({"_id": mid, "user_id": user["_id"]})
    if not maturity:
        raise HTTPException(status_code=404, detail="Resposta de maturidade não encontrada")

    from app.routes.maturity import (
        _load_model,
        _normalize_tier,
        _questions_for_tier,
        _serialize_model,
    )

    # Preferir o modelo com o qual a resposta foi gravada (labels swotLabels/towsLabels)
    model_doc = None
    model_id = maturity.get("model_id")
    if model_id:
        model_doc = db.ai_maturity_model.find_one({"_id": model_id})
    model = _serialize_model(model_doc) if model_doc else _load_model(db)
    if not model.get("dimensions"):
        model = _load_model(db)
    tier = _normalize_tier(maturity.get("tier") or "basico")
    answers_raw = maturity.get("answers") or {}
    answers: dict[str, int] = {}
    for qid, raw in answers_raw.items():
        try:
            answers[str(qid)] = int(raw)
        except (TypeError, ValueError):
            continue

    required = {q["id"] for q in _questions_for_tier(model, tier)}
    if not required or not required.issubset(answers.keys()):
        raise HTTPException(
            status_code=400,
            detail="Conclua todas as perguntas da abrangência antes de criar a SWOT.",
        )

    fields = build_swot_fields_from_maturity(
        model=model,
        answers=answers,
        tier=tier,
        result=maturity.get("result") if isinstance(maturity.get("result"), dict) else None,
    )
    full = SwotAnalysisUpdateRequest(**fields)
    now = datetime.now(timezone.utc)
    existing = _get_by_maturity(db, user["_id"], mid)
    if existing:
        refreshed = _apply_updates(existing, full, db)
        return _to_item(refreshed)

    doc = {
        "user_id": user["_id"],
        "maturity_response_id": mid,
        **_EMPTY_FIELDS,
        "created_at": now,
        "updated_at": now,
    }
    result = db.swot_analyses.insert_one(doc)
    doc["_id"] = result.inserted_id
    refreshed = _apply_updates(doc, full, db)
    return _to_item(refreshed)


@router.get("/{swot_id}")
def get_swot_by_id(
    swot_id: str,
    user=Depends(get_verified_user),
    db: Database = Depends(get_db),
):
    """Retorna uma SWOT específica do mentorado."""
    doc = _migrate_doc_to_v2(_require_owned(db, user["_id"], swot_id), db)
    return _to_item(doc)


@router.put("")
def update_swot(
    body: SwotAnalysisUpdateRequest,
    rebuild_tows: bool = Query(False, description="Recalcular TOWS a partir dos itens marcados"),
    user=Depends(get_verified_user),
    db: Database = Depends(get_db),
):
    """Atualiza a SWOT mais recente do mentorado."""
    doc = _get_or_create_latest(db, user["_id"])
    refreshed = _apply_updates(doc, body, db)
    if rebuild_tows:
        refreshed = _rebuild_tows_on_doc(refreshed, db, user["_id"])
    return _to_item(refreshed)


@router.put("/{swot_id}")
def update_swot_by_id(
    swot_id: str,
    body: SwotAnalysisUpdateRequest,
    rebuild_tows: bool = Query(False, description="Recalcular TOWS a partir dos itens marcados"),
    user=Depends(get_verified_user),
    db: Database = Depends(get_db),
):
    """Atualiza uma SWOT específica."""
    doc = _require_owned(db, user["_id"], swot_id)
    refreshed = _apply_updates(doc, body, db)
    if rebuild_tows:
        refreshed = _rebuild_tows_on_doc(refreshed, db, user["_id"])
    return _to_item(refreshed)


@router.post("/import")
def import_swot(
    body: SwotImportRequest,
    user=Depends(get_verified_user),
    db: Database = Depends(get_db),
):
    """Importa um documento aegis.swot-ia (v1–v3) e substitui o conteúdo da SWOT mais recente."""
    payload = _payload_from_import(body)
    # Importação é substituição completa dos campos do payload presentes
    full = SwotAnalysisUpdateRequest(
        optica=payload.optica if payload.optica is not None else "",
        pilares=payload.pilares if payload.pilares is not None else SwotPilaresPorQuadrante(),
        forcas=payload.forcas if payload.forcas is not None else [],
        fraquezas=payload.fraquezas if payload.fraquezas is not None else [],
        oportunidades=payload.oportunidades if payload.oportunidades is not None else [],
        ameacas=payload.ameacas if payload.ameacas is not None else [],
        watchlist=payload.watchlist if payload.watchlist is not None else [],
        tows_fo=payload.tows_fo if payload.tows_fo is not None else [],
        tows_fa=payload.tows_fa if payload.tows_fa is not None else [],
        tows_fxo=payload.tows_fxo if payload.tows_fxo is not None else [],
        tows_fxa=payload.tows_fxa if payload.tows_fxa is not None else [],
        veredito_tipo=payload.veredito_tipo if payload.veredito_tipo is not None else "",
        veredito_titulo=payload.veredito_titulo if payload.veredito_titulo is not None else "",
        veredito_texto=payload.veredito_texto if payload.veredito_texto is not None else "",
    )
    doc = _get_or_create_latest(db, user["_id"])
    refreshed = _apply_updates(doc, full, db)
    return _to_item(refreshed)
