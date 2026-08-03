"""OKR — ciclos (trimestre/ano) por organização; Objectives vinculados a SWOT/TOWS,
Key Results com meta numérica (baseline → current → target)."""

from __future__ import annotations

import secrets
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pymongo.database import Database

from app.database import get_db
from app.deps import get_current_organization_id, get_verified_user, require_tool
from app.schemas import KeyResult, Objective, OkrCycleCreateRequest, OkrCycleUpdateRequest
from app.tools import TOOL_OKR

router = APIRouter(
    prefix="/api/okrs",
    tags=["okrs"],
    dependencies=[Depends(require_tool(TOOL_OKR))],
)


def _new_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(4)}"


def _float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _kr_progress(baseline: float, current: float, target: float) -> tuple[float, float]:
    """Retorna (progress_pct clamped 0-100, progress_pct_raw sem clamp).

    `denom` já inverte de sinal quando a meta é reduzir o valor (`target < baseline`),
    então a mesma fórmula serve para as duas direções sem precisar de um `if`.
    """
    denom = target - baseline
    raw = 100.0 if denom == 0 else (current - baseline) / denom * 100.0
    return max(0.0, min(100.0, raw)), raw


def _id_list(value, max_items: int = 20) -> list[str]:
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


def _normalize_key_result(raw, used_ids: set[str]) -> dict | None:
    """Normaliza sem descartar quem ainda não tem título: o editor grava sozinho a cada pausa
    de digitação, então perder o item sem título significaria apagar o preenchimento em curso.
    Item sem título é rascunho — persiste, mas fica fora dos contadores, do ciclo ativo e do
    Mapa Estratégico (ver `_published_objectives`)."""
    if isinstance(raw, KeyResult):
        data = raw.model_dump()
    elif isinstance(raw, dict):
        data = raw
    else:
        return None
    titulo = str(data.get("titulo") or "").strip()[:300]
    kr_id = str(data.get("id") or "").strip()[:64]
    if not kr_id or kr_id in used_ids:
        kr_id = _new_id("kr")
    used_ids.add(kr_id)
    direction = str(data.get("direction") or "increase").strip()
    if direction not in ("increase", "decrease"):
        direction = "increase"
    return {
        "id": kr_id,
        "titulo": titulo,
        "descricao": str(data.get("descricao") or "").strip()[:1000],
        "unidade": str(data.get("unidade") or "").strip()[:40],
        "baseline": _float(data.get("baseline")),
        "current": _float(data.get("current")),
        "target": _float(data.get("target")),
        "direction": direction,
        "dono": str(data.get("dono") or "").strip()[:200],
    }


def _as_key_results(value) -> list[dict]:
    if not isinstance(value, list):
        return []
    out: list[dict] = []
    used_ids: set[str] = set()
    for raw in value:
        item = _normalize_key_result(raw, used_ids)
        if item is None:
            continue
        out.append(item)
        if len(out) >= 20:
            break
    return out


def _clean_key_results(value: list[KeyResult] | None) -> list[dict]:
    if not value:
        return []
    return _as_key_results(value)


def _collect_swot_ids(value) -> set[str]:
    ids: set[str] = set()
    if not isinstance(value, list):
        return ids
    for raw in value:
        if isinstance(raw, Objective):
            sid = raw.swot_id
        elif isinstance(raw, dict):
            sid = raw.get("swot_id")
        else:
            continue
        sid = str(sid or "").strip()
        if sid:
            ids.add(sid)
    return ids


def _validate_swot_ids(db: Database, org_id, ids: set[str]) -> set[str]:
    """Valida em lote (uma query) quais swot_id referenciados existem na organização."""
    object_ids = [ObjectId(i) for i in ids if ObjectId.is_valid(i)]
    if not object_ids:
        return set()
    found = db.swot_analyses.find({"_id": {"$in": object_ids}, "organization_id": org_id}, {"_id": 1})
    return {str(doc["_id"]) for doc in found}


def _normalize_objective(raw, used_ids: set[str], valid_swot_ids: set[str]) -> dict | None:
    if isinstance(raw, Objective):
        data = raw.model_dump()
    elif isinstance(raw, dict):
        data = raw
    else:
        return None
    titulo = str(data.get("titulo") or "").strip()[:300]
    obj_id = str(data.get("id") or "").strip()[:64]
    if not obj_id or obj_id in used_ids:
        obj_id = _new_id("obj")
    used_ids.add(obj_id)
    swot_id = str(data.get("swot_id") or "").strip()[:24] or None
    if swot_id and swot_id not in valid_swot_ids:
        swot_id = None
    return {
        "id": obj_id,
        "titulo": titulo,
        "descricao": str(data.get("descricao") or "").strip()[:2000],
        "dono": str(data.get("dono") or "").strip()[:200],
        "pilar": str(data.get("pilar") or "").strip().lower()[:40],
        "swot_id": swot_id,
        "swot_item_ids": _id_list(data.get("swot_item_ids")),
        "tows_ids": _id_list(data.get("tows_ids")),
        "key_results": _clean_key_results(data.get("key_results")),
    }


def _clean_objectives(value: list[Objective] | None, db: Database, org_id) -> list[dict]:
    if not value:
        return []
    valid_swot_ids = _validate_swot_ids(db, org_id, _collect_swot_ids(value))
    out: list[dict] = []
    used_ids: set[str] = set()
    for raw in value:
        item = _normalize_objective(raw, used_ids, valid_swot_ids)
        if item is None:
            continue
        out.append(item)
        if len(out) >= 20:
            break
    return out


def _kr_node(kr: dict) -> dict:
    pct, raw = _kr_progress(kr.get("baseline") or 0, kr.get("current") or 0, kr.get("target") or 0)
    return {**kr, "progress_pct": round(pct, 1), "progress_pct_raw": round(raw, 1)}


def _objective_node(obj: dict) -> dict:
    """Devolve todos os KRs (o editor precisa dos rascunhos) mas mede o progresso só nos
    publicados, para um KR ainda sem nome não puxar a média do objetivo."""
    krs = [_kr_node(kr) for kr in obj.get("key_results") or []]
    published = [kr for kr in krs if _is_published(kr)]
    progress = (
        round(sum(k["progress_pct"] for k in published) / len(published), 1) if published else None
    )
    return {**obj, "key_results": krs, "progress_pct": progress}


def _is_published(node: dict) -> bool:
    """Publicado = tem título. Sem título é rascunho: guardado, mas invisível para o resto."""
    return bool(str(node.get("titulo") or "").strip())


def _published_objectives(objectives: list[dict]) -> list[dict]:
    """Objectives publicados, cada um só com os KRs publicados — a visão que o Mapa
    Estratégico, o ciclo ativo e os contadores usam."""
    return [
        {**obj, "key_results": [kr for kr in obj.get("key_results") or [] if _is_published(kr)]}
        for obj in objectives
        if _is_published(obj)
    ]


def _drafts_count(objectives: list[dict]) -> int:
    objs = sum(1 for obj in objectives if not _is_published(obj))
    krs = sum(
        1
        for obj in objectives
        for kr in obj.get("key_results") or []
        if not _is_published(kr)
    )
    return objs + krs


def _label(doc: dict) -> str:
    nome = str(doc.get("nome") or "").strip()
    if nome:
        return nome
    if doc.get("tipo") == "trimestre" and doc.get("trimestre"):
        return f"Q{doc['trimestre']} {doc.get('ano')}"
    return str(doc.get("ano") or "")


def _to_item(doc: dict, *, summary: bool = False, include_drafts: bool = True) -> dict:
    """Serializa o ciclo. `include_drafts=False` entrega só o que está publicado — use nos
    consumidores (ciclo ativo, Mapa Estratégico); o editor precisa do documento completo.
    Contadores e progresso ignoram rascunhos nas duas formas."""
    objectives = [_objective_node(o) for o in doc.get("objectives") or []]
    published = _published_objectives(objectives)
    kr_pcts = [kr["progress_pct"] for o in published for kr in o["key_results"]]
    created_at = doc.get("created_at")
    updated_at = doc.get("updated_at")
    base = {
        "id": str(doc["_id"]),
        "tipo": doc.get("tipo") or "trimestre",
        "ano": doc.get("ano"),
        "trimestre": doc.get("trimestre"),
        "nome": doc.get("nome") or "",
        "label": _label(doc),
        "status": doc.get("status") or "planejamento",
        "objectives_count": len(published),
        "key_results_count": len(kr_pcts),
        "drafts_count": _drafts_count(objectives),
        "progress_pct": round(sum(kr_pcts) / len(kr_pcts), 1) if kr_pcts else None,
        "created_at": created_at.isoformat() if created_at else None,
        "updated_at": updated_at.isoformat() if updated_at else None,
    }
    if summary:
        return base
    return {**base, "objectives": objectives if include_drafts else published}


def _get_active(db: Database, org_id) -> dict | None:
    return db.okr_cycles.find_one({"organization_id": org_id, "status": "ativo"})


def _require_owned(db: Database, org_id, cycle_id: str) -> dict:
    if not ObjectId.is_valid(cycle_id):
        raise HTTPException(status_code=404, detail="Ciclo OKR não encontrado")
    doc = db.okr_cycles.find_one({"_id": ObjectId(cycle_id), "organization_id": org_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Ciclo OKR não encontrado")
    return doc


@router.get("/cycles")
def list_cycles(
    user=Depends(get_verified_user),
    org_id=Depends(get_current_organization_id),
    db: Database = Depends(get_db),
):
    """Resumo dos ciclos OKR da organização, mais recentes primeiro."""
    cursor = db.okr_cycles.find({"organization_id": org_id}).sort(
        [("ano", -1), ("trimestre", -1), ("updated_at", -1)]
    )
    return {"items": [_to_item(doc, summary=True) for doc in cursor]}


@router.post("/cycles")
def create_cycle(
    body: OkrCycleCreateRequest,
    user=Depends(get_verified_user),
    org_id=Depends(get_current_organization_id),
    db: Database = Depends(get_db),
):
    """Cria um novo ciclo OKR vazio (rascunho, não afeta o ciclo ativo)."""
    if body.tipo == "trimestre" and not body.trimestre:
        raise HTTPException(status_code=400, detail="Informe o trimestre (1-4) para ciclos trimestrais.")
    now = datetime.now(timezone.utc)
    doc = {
        "organization_id": org_id,
        "created_by_user_id": user["_id"],
        "tipo": body.tipo,
        "ano": body.ano,
        "trimestre": body.trimestre if body.tipo == "trimestre" else None,
        "nome": (body.nome or "").strip()[:120],
        "status": "planejamento",
        "objectives": [],
        "created_at": now,
        "updated_at": now,
    }
    result = db.okr_cycles.insert_one(doc)
    doc["_id"] = result.inserted_id
    return _to_item(doc)


@router.get("/cycles/active")
def get_active_cycle(
    user=Depends(get_verified_user),
    org_id=Depends(get_current_organization_id),
    db: Database = Depends(get_db),
):
    """Ciclo OKR ativo da organização, só com Objectives/KRs publicados — é a fonte para
    vincular KRs no Canvas (404 se nenhum ciclo estiver ativo)."""
    doc = _get_active(db, org_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Nenhum ciclo OKR ativo")
    return _to_item(doc, include_drafts=False)


@router.get("/cycles/{cycle_id}")
def get_cycle(
    cycle_id: str,
    user=Depends(get_verified_user),
    org_id=Depends(get_current_organization_id),
    db: Database = Depends(get_db),
):
    return _to_item(_require_owned(db, org_id, cycle_id))


@router.put("/cycles/{cycle_id}")
def update_cycle(
    cycle_id: str,
    body: OkrCycleUpdateRequest,
    user=Depends(get_verified_user),
    org_id=Depends(get_current_organization_id),
    db: Database = Depends(get_db),
):
    """Atualiza um ciclo OKR (full-replace de objectives quando informado)."""
    doc = _require_owned(db, org_id, cycle_id)
    updates = body.model_dump(exclude_unset=True)

    tipo = updates.get("tipo", doc.get("tipo"))
    if tipo == "trimestre" and not updates.get("trimestre", doc.get("trimestre")):
        raise HTTPException(status_code=400, detail="Informe o trimestre (1-4) para ciclos trimestrais.")

    if "objectives" in updates:
        updates["objectives"] = _clean_objectives(body.objectives, db, org_id)
    if "nome" in updates:
        updates["nome"] = (updates.get("nome") or "").strip()[:120]

    updates["updated_at"] = datetime.now(timezone.utc)
    db.okr_cycles.update_one({"_id": doc["_id"]}, {"$set": updates})
    return _to_item(db.okr_cycles.find_one({"_id": doc["_id"]}) or doc)


@router.post("/cycles/{cycle_id}/activate")
def activate_cycle(
    cycle_id: str,
    user=Depends(get_verified_user),
    org_id=Depends(get_current_organization_id),
    db: Database = Depends(get_db),
):
    """Ativa este ciclo, encerrando qualquer outro ciclo ativo da organização. Idempotente."""
    doc = _require_owned(db, org_id, cycle_id)
    now = datetime.now(timezone.utc)
    db.okr_cycles.update_one(
        {"organization_id": org_id, "status": "ativo", "_id": {"$ne": doc["_id"]}},
        {"$set": {"status": "encerrado", "updated_at": now}},
    )
    db.okr_cycles.update_one({"_id": doc["_id"]}, {"$set": {"status": "ativo", "updated_at": now}})
    return _to_item(db.okr_cycles.find_one({"_id": doc["_id"]}) or doc)


@router.post("/cycles/{cycle_id}/archive")
def archive_cycle(
    cycle_id: str,
    user=Depends(get_verified_user),
    org_id=Depends(get_current_organization_id),
    db: Database = Depends(get_db),
):
    doc = _require_owned(db, org_id, cycle_id)
    db.okr_cycles.update_one(
        {"_id": doc["_id"]}, {"$set": {"status": "encerrado", "updated_at": datetime.now(timezone.utc)}}
    )
    return _to_item(db.okr_cycles.find_one({"_id": doc["_id"]}) or doc)


@router.delete("/cycles/{cycle_id}")
def delete_cycle(
    cycle_id: str,
    user=Depends(get_verified_user),
    org_id=Depends(get_current_organization_id),
    db: Database = Depends(get_db),
):
    doc = _require_owned(db, org_id, cycle_id)
    db.okr_cycles.delete_one({"_id": doc["_id"]})
    return {"message": "Ciclo OKR removido", "id": str(doc["_id"])}
