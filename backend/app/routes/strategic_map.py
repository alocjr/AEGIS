"""Mapa Estratégico — árvore Maturidade → SWOT → TOWS → Projetos de um mentorado."""

from __future__ import annotations

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from pymongo.database import Database

from app.database import get_db
from app.deps import get_current_organization_id, get_verified_user, require_tool
from app.routes.canvas_projects import _to_item as _project_to_item
from app.routes.okrs import _to_item as _okr_cycle_to_item
from app.routes.swot_analysis import _get_latest as _latest_swot
from app.routes.swot_analysis import _require_owned as _owned_swot
from app.routes.swot_analysis import _to_item as _swot_to_item
from app.swot_from_maturity import _DIM_TO_PILLAR
from app.tools import TOOL_STRATEGIC_MAP

router = APIRouter(
    prefix="/api/strategic-map",
    tags=["strategic-map"],
    dependencies=[Depends(require_tool(TOOL_STRATEGIC_MAP))],
)

_TIER_LABEL = {"basico": "Básico", "completo": "Completo", "complementar": "Complementar"}
_TIER_ORDER = {"basico": 0, "completo": 1, "complementar": 2}
_QUADRANT_FIELDS = ("forcas", "fraquezas", "oportunidades", "ameacas")
_TOWS_FIELDS = ("tows_fo", "tows_fa", "tows_fxo", "tows_fxa")


def _key(value) -> str:
    return str(value or "").strip().lower()


def _iso(value):
    return value.isoformat() if hasattr(value, "isoformat") else None


def _visible(question_tier: str, selected_tier: str) -> bool:
    return _TIER_ORDER.get(question_tier, 99) <= _TIER_ORDER.get(selected_tier, 0)


def _list_sources(db: Database, org_id) -> list[dict]:
    """Autoavaliações da organização (mais recentes primeiro) com a SWOT vinculada."""
    swots = list(
        db.swot_analyses.find(
            {"organization_id": org_id}, {"maturity_response_id": 1, "updated_at": 1}
        ).sort([("updated_at", -1), ("_id", -1)])
    )
    swot_by_maturity: dict[str, str] = {}
    for doc in swots:
        mid = doc.get("maturity_response_id")
        if mid:
            swot_by_maturity.setdefault(str(mid), str(doc["_id"]))

    out: list[dict] = []
    cursor = db.maturity_responses.find({"organization_id": org_id, "complete": True}).sort(
        [("submitted_at", -1), ("_id", -1)]
    )
    for doc in cursor:
        result = doc.get("result") or {}
        level = result.get("level") or {}
        tier = _key(doc.get("tier") or result.get("tier") or "basico")
        out.append(
            {
                "maturity_response_id": str(doc["_id"]),
                "swot_id": swot_by_maturity.get(str(doc["_id"])),
                "assessment_title": doc.get("assessment_title") or "",
                "tier": tier,
                "tier_label": _TIER_LABEL.get(tier, tier),
                "submitted_at": _iso(doc.get("submitted_at")),
                "complete": bool(doc.get("complete")),
                "percent_score": result.get("percent_score") or 0,
                "level_label": level.get("label") or "",
            }
        )

    # SWOTs manuais/importadas (sem autoavaliação de origem) também são navegáveis
    for doc in swots:
        if doc.get("maturity_response_id"):
            continue
        out.append(
            {
                "maturity_response_id": None,
                "swot_id": str(doc["_id"]),
                "assessment_title": "SWOT sem autoavaliação",
                "tier": None,
                "tier_label": None,
                "submitted_at": _iso(doc.get("updated_at")),
                "complete": False,
                "percent_score": 0,
                "level_label": "",
            }
        )
    return out


def _resolve_target(
    db: Database,
    org_id,
    maturity_response_id: str | None,
    swot_id: str | None,
) -> tuple[dict | None, dict | None]:
    """Resolve o par (resposta de maturidade, SWOT) a exibir no mapa."""
    if swot_id:
        swot_doc = _owned_swot(db, org_id, swot_id)
        mid = swot_doc.get("maturity_response_id")
        maturity_doc = (
            db.maturity_responses.find_one({"_id": mid, "organization_id": org_id}) if mid else None
        )
        return maturity_doc, swot_doc

    if maturity_response_id:
        if not ObjectId.is_valid(maturity_response_id):
            raise HTTPException(status_code=404, detail="Resposta de maturidade não encontrada")
        mid = ObjectId(maturity_response_id)
        maturity_doc = db.maturity_responses.find_one({"_id": mid, "organization_id": org_id})
        if not maturity_doc:
            raise HTTPException(status_code=404, detail="Resposta de maturidade não encontrada")
        swot_doc = db.swot_analyses.find_one({"organization_id": org_id, "maturity_response_id": mid})
        return maturity_doc, swot_doc

    swot_doc = _latest_swot(db, org_id)
    if swot_doc:
        mid = swot_doc.get("maturity_response_id")
        maturity_doc = (
            db.maturity_responses.find_one({"_id": mid, "organization_id": org_id}) if mid else None
        )
        return maturity_doc, swot_doc

    maturity_doc = db.maturity_responses.find_one(
        {"organization_id": org_id, "complete": True}, sort=[("submitted_at", -1), ("_id", -1)]
    )
    return maturity_doc, None


def _load_model_for(db: Database, maturity_doc: dict | None) -> dict | None:
    """Modelo com o qual a resposta foi gravada; senão o ativo."""
    from app.routes.maturity import _load_model, _serialize_model

    model_id = (maturity_doc or {}).get("model_id")
    if model_id:
        doc = db.ai_maturity_model.find_one({"_id": model_id})
        if doc and doc.get("dimensions"):
            return _serialize_model(doc)
    try:
        return _load_model(db)
    except HTTPException:
        return None


def _project_ref(project: dict) -> dict:
    return {
        "id": project["id"],
        "title": project["title"],
        "area_negocio": project["area_negocio"],
        "quadrant": project["quadrant"],
        "score_valor": project["score_valor"],
        "score_viabilidade": project["score_viabilidade"],
        "proximo_passo": project.get("proximo_passo") or "",
        "updated_at": project["updated_at"],
    }


def _kr_ref(kr: dict, projects_by_kr: dict[str, list[dict]]) -> dict:
    return {**kr, "projects": [_project_ref(p) for p in projects_by_kr.get(kr.get("id") or "", [])]}


def _objective_with_projects(obj: dict, projects_by_kr: dict[str, list[dict]]) -> dict:
    return {**obj, "key_results": [_kr_ref(kr, projects_by_kr) for kr in obj.get("key_results") or []]}


def _initiative_node(
    field: str,
    raw: dict,
    items_by_id: dict[str, dict],
    projects_by_tows: dict[str, list[dict]],
    objectives_by_tows: dict[str, list[dict]],
) -> dict:
    counterparts = []
    for ref in raw.get("itens_externos") or []:
        item = items_by_id.get(ref)
        counterparts.append(
            {
                "id": ref,
                "quadrant": item.get("quadrant") if item else None,
                "texto": item.get("texto") if item else "",
            }
        )
    return {
        "id": raw.get("id") or "",
        "field": field,
        "acao": raw.get("acao") or "",
        "dono": raw.get("dono") or "",
        "horizonte": raw.get("horizonte") or "",
        "itens_internos": list(raw.get("itens_internos") or []),
        "counterparts": counterparts,
        "projects": [_project_ref(p) for p in projects_by_tows.get(raw.get("id") or "", [])],
        "objectives": objectives_by_tows.get(raw.get("id") or "", []),
    }


def _item_node(
    item: dict,
    initiatives_by_item: dict[str, list[dict]],
    projects_by_item: dict[str, list[dict]],
    external_usage: dict[str, int],
    objectives_by_item: dict[str, list[dict]],
) -> dict:
    item_id = item.get("id") or ""
    return {
        "id": item_id,
        "quadrant": item.get("quadrant"),
        "texto": item.get("texto") or "",
        "pilar": item.get("pilar") or "",
        "question_id": item.get("question_id") or "",
        "impacto": item.get("impacto"),
        "viabilidade": item.get("viabilidade"),
        "probabilidade": item.get("probabilidade"),
        "evidencia": item.get("evidencia") or "",
        "prioridade": item.get("prioridade"),
        "tows": bool(item.get("tows", True)),
        "initiatives": initiatives_by_item.get(item_id, []),
        # Quantas estratégias TOWS usam este item como contraparte externa
        "used_in": external_usage.get(item_id, 0),
        "projects": [_project_ref(p) for p in projects_by_item.get(item_id, [])],
        "objectives": objectives_by_item.get(item_id, []),
    }


@router.get("")
def get_strategic_map(
    maturity_response_id: str | None = Query(None),
    swot_id: str | None = Query(None),
    user=Depends(get_verified_user),
    org_id=Depends(get_current_organization_id),
    db: Database = Depends(get_db),
):
    """Árvore de rastreabilidade: resposta de maturidade → itens SWOT → TOWS → projetos."""
    maturity_doc, swot_doc = _resolve_target(db, org_id, maturity_response_id, swot_id)
    sources = _list_sources(db, org_id)

    swot = _swot_to_item(swot_doc) if swot_doc else None
    result = (maturity_doc or {}).get("result") or {}
    tier = _key((maturity_doc or {}).get("tier") or result.get("tier") or "basico")
    answers_raw = (maturity_doc or {}).get("answers") or {}
    answers: dict[str, int] = {}
    for qid, raw in answers_raw.items():
        try:
            answers[str(qid)] = int(raw)
        except (TypeError, ValueError):
            continue

    projects = [
        _project_to_item(doc, summary=True)
        for doc in db.canvas_projects.find({"organization_id": org_id}).sort([("updated_at", -1)])
    ]
    items_by_id: dict[str, dict] = {}
    items_by_question: dict[str, list[dict]] = {}
    initiative_ids: set[str] = set()
    if swot:
        for field in _QUADRANT_FIELDS:
            for raw in swot.get(field) or []:
                item = {**raw, "quadrant": field}
                items_by_id[item["id"]] = item
                qkey = _key(item.get("question_id"))
                if qkey:
                    items_by_question.setdefault(qkey, []).append(item)
        for field in _TOWS_FIELDS:
            for raw in swot.get(field) or []:
                if raw.get("id"):
                    initiative_ids.add(str(raw["id"]))

    # Só conta vínculo cujo alvo existe na SWOT exibida (referências órfãs ficam de fora)
    projects_by_item: dict[str, list[dict]] = {}
    projects_by_tows: dict[str, list[dict]] = {}
    for project in projects:
        for ref in project["swot_item_ids"]:
            if ref in items_by_id:
                projects_by_item.setdefault(ref, []).append(project)
        for ref in project["tows_ids"]:
            if ref in initiative_ids:
                projects_by_tows.setdefault(ref, []).append(project)

    # Ciclo OKR ativo da organização (nenhum = camada de OKR fica vazia, sem erro)
    active_cycle_doc = db.okr_cycles.find_one({"organization_id": org_id, "status": "ativo"})
    active_cycle = (
        _okr_cycle_to_item(active_cycle_doc, include_drafts=False) if active_cycle_doc else None
    )
    all_objectives: list[dict] = active_cycle["objectives"] if active_cycle else []

    kr_ids_all: set[str] = {
        kr["id"] for obj in all_objectives for kr in obj["key_results"] if kr.get("id")
    }
    projects_by_kr: dict[str, list[dict]] = {}
    for project in projects:
        for ref in project.get("kr_ids") or []:
            if ref in kr_ids_all:
                projects_by_kr.setdefault(ref, []).append(project)

    # Só conta vínculo cujo alvo (item SWOT ou iniciativa TOWS) existe na SWOT exibida
    objectives_by_item: dict[str, list[dict]] = {}
    objectives_by_tows: dict[str, list[dict]] = {}
    used_objective_ids: set[str] = set()
    for obj in all_objectives:
        node = _objective_with_projects(obj, projects_by_kr)
        valid_items = [ref for ref in obj["swot_item_ids"] if ref in items_by_id]
        valid_tows = [ref for ref in obj["tows_ids"] if ref in initiative_ids]
        if not valid_items and not valid_tows:
            continue
        used_objective_ids.add(obj["id"])
        for ref in valid_items:
            objectives_by_item.setdefault(ref, []).append(node)
        for ref in valid_tows:
            objectives_by_tows.setdefault(ref, []).append(node)

    orphan_objectives = [
        _objective_with_projects(obj, projects_by_kr)
        for obj in all_objectives
        if obj["id"] not in used_objective_ids
    ]
    linked_kr_ids = set(projects_by_kr.keys())
    orphan_key_results = [
        {**kr, "objective_titulo": obj["titulo"]}
        for obj in all_objectives
        for kr in obj["key_results"]
        if kr["id"] not in linked_kr_ids
    ]

    initiatives_by_item: dict[str, list[dict]] = {}
    external_usage: dict[str, int] = {}
    orphan_initiatives: list[dict] = []
    initiative_count = 0
    if swot:
        for field in _TOWS_FIELDS:
            for raw in swot.get(field) or []:
                node = _initiative_node(field, raw, items_by_id, projects_by_tows, objectives_by_tows)
                initiative_count += 1
                for counterpart in node["counterparts"]:
                    ref = counterpart["id"]
                    if ref in items_by_id:
                        external_usage[ref] = external_usage.get(ref, 0) + 1
                internos = [ref for ref in node["itens_internos"] if ref in items_by_id]
                if not internos:
                    orphan_initiatives.append(node)
                    continue
                for ref in internos:
                    initiatives_by_item.setdefault(ref, []).append(node)

    watchlist_by_question: dict[str, list[dict]] = {}
    for entry in (swot or {}).get("watchlist") or []:
        watchlist_by_question.setdefault(_key(entry.get("id")), []).append(entry)

    model = _load_model_for(db, maturity_doc)
    dimension_scores = result.get("dimension_scores") or {}
    used_item_ids: set[str] = set()
    used_watchlist_ids: set[str] = set()
    dimensions: list[dict] = []
    question_count = 0

    for dimension in (model or {}).get("dimensions") or []:
        dim_id = str(dimension.get("id") or "")
        score = dimension_scores.get(dim_id) or {}
        dim_max = int(score.get("max") or 0)
        dim_score = int(score.get("score") or 0)
        questions: list[dict] = []
        for question in dimension.get("questions") or []:
            qid = str(question.get("id") or "")
            if not qid or qid not in answers:
                continue
            if not _visible(str(question.get("tier") or "basico"), tier):
                continue
            level = int(answers[qid])
            levels = question.get("levels") or {}
            qkey = _key(qid)
            item_nodes = [
                _item_node(item, initiatives_by_item, projects_by_item, external_usage, objectives_by_item)
                for item in items_by_question.get(qkey, [])
            ]
            used_item_ids.update(node["id"] for node in item_nodes)
            watch_nodes = watchlist_by_question.get(qkey, [])
            used_watchlist_ids.update(_key(w.get("id")) for w in watch_nodes)
            question_count += 1
            questions.append(
                {
                    "id": qid,
                    "text": str(question.get("text") or ""),
                    "tier": str(question.get("tier") or "basico"),
                    "answer": level,
                    "answer_text": str(levels.get(str(level)) or levels.get(level) or ""),
                    "swot_category": question.get("swotCategory")
                    or question.get("swot_category")
                    or None,
                    "items": item_nodes,
                    "watchlist": watch_nodes,
                }
            )
        if not questions:
            continue
        dimensions.append(
            {
                "id": dim_id,
                "name": str(dimension.get("name") or dim_id),
                "pilar": _DIM_TO_PILLAR.get(dim_id, ""),
                "score": {
                    "score": dim_score,
                    "max": dim_max,
                    "avg": score.get("avg") or 0,
                    "pct": round((dim_score / dim_max) * 100) if dim_max else 0,
                },
                "questions": questions,
            }
        )

    orphan_items = [
        _item_node(item, initiatives_by_item, projects_by_item, external_usage, objectives_by_item)
        for item_id, item in items_by_id.items()
        if item_id not in used_item_ids
    ]
    orphan_watchlist = [
        entry
        for entry in (swot or {}).get("watchlist") or []
        if _key(entry.get("id")) not in used_watchlist_ids
    ]

    linked_project_ids = {
        ref["id"]
        for bucket in (projects_by_item, projects_by_tows)
        for group in bucket.values()
        for ref in group
    }
    swot_id_value = swot["id"] if swot else None
    orphan_projects = [
        {
            **_project_ref(project),
            "linked_to_swot": bool(swot_id_value and project.get("swot_id") == swot_id_value),
        }
        for project in projects
        if project["id"] not in linked_project_ids
    ]

    level_info = result.get("level") or {}
    source = {
        "maturity_response_id": str(maturity_doc["_id"]) if maturity_doc else None,
        "swot_id": swot_id_value,
        "assessment_title": (maturity_doc or {}).get("assessment_title") or "",
        "tier": tier if maturity_doc else None,
        "tier_label": _TIER_LABEL.get(tier, tier) if maturity_doc else None,
        "submitted_at": _iso((maturity_doc or {}).get("submitted_at")),
        "complete": bool((maturity_doc or {}).get("complete")),
        "result": {
            "total_score": result.get("total_score") or 0,
            "max_score": result.get("max_score") or 0,
            "percent_score": result.get("percent_score") or 0,
            "level_label": level_info.get("label") or "",
            "level_description": level_info.get("description") or "",
        }
        if maturity_doc
        else None,
        "optica": (swot or {}).get("optica") or "",
        "veredito_tipo": (swot or {}).get("veredito_tipo") or "",
        "veredito_titulo": (swot or {}).get("veredito_titulo") or "",
        "veredito_texto": (swot or {}).get("veredito_texto") or "",
        "swot_updated_at": (swot or {}).get("updated_at"),
    }

    return {
        "source": source,
        "sources": sources,
        "okr_cycle": (
            {"id": active_cycle["id"], "label": active_cycle["label"], "status": active_cycle["status"]}
            if active_cycle
            else None
        ),
        "dimensions": dimensions,
        "unlinked": {
            "swot_items": orphan_items,
            "initiatives": orphan_initiatives,
            "watchlist": orphan_watchlist,
            "projects": orphan_projects,
            "objectives": orphan_objectives,
            "key_results": orphan_key_results,
        },
        "stats": {
            "dimensions": len(dimensions),
            "questions": question_count,
            "swot_items": len(items_by_id),
            "watchlist": len((swot or {}).get("watchlist") or []),
            "initiatives": initiative_count,
            "projects_total": len(projects),
            "projects_linked": len(linked_project_ids),
            "objectives": len(all_objectives),
            "objectives_linked": len(used_objective_ids),
            "key_results": len(kr_ids_all),
            "key_results_linked": len(linked_kr_ids),
        },
    }
