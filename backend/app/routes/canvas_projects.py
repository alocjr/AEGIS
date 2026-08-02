"""Canvas de Oportunidades de IA por área — projetos do mentorado."""

from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pymongo.database import Database

from app.database import get_db
from app.deps import get_verified_user
from app.schemas import (
    OPPORTUNITY_TYPE_OPTIONS,
    CanvasImportRequest,
    CanvasProjectCreateRequest,
    CanvasProjectUpdateRequest,
)

_TYPE_SLUG_TO_LABEL = {
    "automacao": "Automação",
    "classificacao_previsao": "Classificação/Previsão",
    "extracao_busca": "Extração/Busca",
    "geracao": "Geração",
    "copiloto": "Copiloto",
    "agente": "Agente autônomo",
    "agente_autonomo": "Agente autônomo",
}
_LABEL_TO_CANON = {label.lower(): label for label in OPPORTUNITY_TYPE_OPTIONS}
_NIVEL = {"baixo": "baixo", "baixa": "baixa", "medio": "médio", "media": "média", "alto": "alto", "alta": "alta"}
_HITL = {
    "nenhum": "nenhum",
    "sugerir": "sugerir",
    "aprovar": "aprovar",
    "supervisionar": "supervisionar",
}

router = APIRouter(prefix="/api/canvas-projects", tags=["canvas-projects"])

_LIST_FIELDS = (
    "contexto",
    "dores",
    "oportunidade",
    "dados",
    "valor",
    "custo",
    "riscos",
)

_EMPTY_FIELDS = {
    "area_negocio": "",
    "responsavel": "",
    "data": "",
    "objetivo_estrategico": "",
    "contexto": [],
    "dores": [],
    "oportunidade": [],
    "oportunidade_tipos": [],
    "dados": [],
    "valor": [],
    "custo": [],
    "riscos": [],
    "score_valor": None,
    "score_viabilidade": None,
    "proximo_passo": "",
    "swot_id": None,
    "swot_item_ids": [],
    "tows_ids": [],
    "justificativa_tows": "",
}


def _as_item_list(value) -> list[str]:
    """Normaliza string legada ou lista para lista de itens."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()][:40]
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    return []


def _clean_item_list(value: list[str] | None) -> list[str]:
    if not value:
        return []
    return [str(x).strip() for x in value if str(x).strip()][:40]


def _clean_ref_ids(value) -> list[str]:
    """Ids de itens SWOT / iniciativas TOWS que originaram o projeto."""
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for raw in value:
        ref = str(raw or "").strip()[:64]
        if ref and ref not in out:
            out.append(ref)
        if len(out) >= 20:
            break
    return out


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
        "swot_id": str(doc["swot_id"]) if doc.get("swot_id") else None,
        "swot_item_ids": _clean_ref_ids(doc.get("swot_item_ids")),
        "tows_ids": _clean_ref_ids(doc.get("tows_ids")),
    }
    if summary:
        return {
            **base,
            "data": doc.get("data") or "",
            "objetivo_estrategico": doc.get("objetivo_estrategico") or "",
            "proximo_passo": doc.get("proximo_passo") or "",
        }
    return {
        **base,
        "data": doc.get("data") or "",
        "objetivo_estrategico": doc.get("objetivo_estrategico") or "",
        "contexto": _as_item_list(doc.get("contexto")),
        "dores": _as_item_list(doc.get("dores")),
        "oportunidade": _as_item_list(doc.get("oportunidade")),
        "oportunidade_tipos": list(doc.get("oportunidade_tipos") or []),
        "dados": _as_item_list(doc.get("dados")),
        "valor": _as_item_list(doc.get("valor")),
        "custo": _as_item_list(doc.get("custo")),
        "riscos": _as_item_list(doc.get("riscos")),
        "proximo_passo": doc.get("proximo_passo") or "",
        "justificativa_tows": doc.get("justificativa_tows") or "",
        "opportunity_type_options": list(OPPORTUNITY_TYPE_OPTIONS),
    }


def _owned_swot_id(db: Database, user_id, raw) -> str | None:
    """Valida que a SWOT de origem existe e pertence ao mentorado."""
    swot_id = str(raw or "").strip()
    if not swot_id:
        return None
    if not ObjectId.is_valid(swot_id):
        raise HTTPException(status_code=400, detail="SWOT de origem invalida")
    exists = db.swot_analyses.find_one(
        {"_id": ObjectId(swot_id), "user_id": user_id}, {"_id": 1}
    )
    if not exists:
        raise HTTPException(status_code=404, detail="SWOT de origem nao encontrada")
    return swot_id


def _get_owned(db: Database, user_id, project_id: str) -> dict:
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=400, detail="ID invalido")
    doc = db.canvas_projects.find_one({"_id": ObjectId(project_id), "user_id": user_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Projeto nao encontrado")
    return doc


def _clip(text: str, max_len: int) -> str:
    t = (text or "").strip()
    if len(t) <= max_len:
        return t
    return t[: max_len - 1].rstrip() + "…"


def _score_1_5(value) -> int | None:
    if value is None or value == "":
        return None
    try:
        n = int(value)
    except (TypeError, ValueError):
        return None
    return n if 1 <= n <= 5 else None


def _nivel(value) -> str:
    raw = str(value or "").strip().lower()
    return _NIVEL.get(raw, raw)


def _map_tipos(raw) -> list[str]:
    if not isinstance(raw, list):
        return []
    allowed = set(OPPORTUNITY_TYPE_OPTIONS)
    out: list[str] = []
    for item in raw:
        key = str(item or "").strip()
        if not key:
            continue
        label = _TYPE_SLUG_TO_LABEL.get(key.lower()) or _LABEL_TO_CANON.get(key.lower()) or key
        if label in allowed and label not in out:
            out.append(label)
    return out[:12]


def _push(items: list[str], text: str | None) -> None:
    t = (text or "").strip()
    if t and t not in items and len(items) < 40:
        items.append(t)


def _opportunity_to_fields(area: dict, opp: dict, projeto_meta: dict | None) -> dict:
    """Mapeia uma oportunidade do schema aegis.canvas-oportunidades → campos do canvas."""
    area_name = str(area.get("area") or "").strip()
    contexto: list[str] = []
    _push(contexto, area.get("contexto"))
    if isinstance(projeto_meta, dict):
        desc = str(projeto_meta.get("descricao") or "").strip()
        setor = str(projeto_meta.get("setor") or "").strip()
        porte = str(projeto_meta.get("porte") or "").strip()
        bits = [b for b in (setor, porte) if b]
        if bits:
            _push(contexto, f"Contexto do projeto: {', '.join(bits)}.")
        _push(contexto, desc)

    dores: list[str] = []
    _push(dores, opp.get("dor"))

    oportunidade: list[str] = []
    _push(oportunidade, opp.get("oportunidade"))

    dados_obj = opp.get("dados") if isinstance(opp.get("dados"), dict) else {}
    dados: list[str] = []
    _push(dados, dados_obj.get("descricao"))
    disp = _nivel(dados_obj.get("disponibilidade"))
    if disp:
        _push(dados, f"Disponibilidade: {disp}.")

    valor_obj = opp.get("valor") if isinstance(opp.get("valor"), dict) else {}
    valor: list[str] = []
    _push(valor, valor_obj.get("direto"))
    _push(valor, valor_obj.get("indireto"))
    metrica = str(valor_obj.get("metrica") or "").strip()
    if metrica:
        _push(valor, f"Métrica: {metrica}")

    custo_obj = opp.get("custo") if isinstance(opp.get("custo"), dict) else {}
    custo: list[str] = []
    for key, label in (
        ("capex", "CAPEX"),
        ("opex", "OPEX"),
        ("integracao", "Integração"),
    ):
        n = _nivel(custo_obj.get(key))
        if n:
            _push(custo, f"{label}: {n}.")
    _push(custo, custo_obj.get("mudanca"))

    riscos_obj = opp.get("riscos") if isinstance(opp.get("riscos"), dict) else {}
    riscos: list[str] = []
    _push(riscos, riscos_obj.get("descricao"))
    reg = riscos_obj.get("regulatorio")
    if isinstance(reg, list):
        regs = [str(x).strip() for x in reg if str(x).strip()]
        if regs:
            _push(riscos, f"Regulatório: {', '.join(regs)}.")
    hitl_raw = str(riscos_obj.get("human_in_the_loop") or "").strip().lower()
    hitl = _HITL.get(hitl_raw, hitl_raw)
    if hitl:
        _push(riscos, f"Human-in-the-loop: {hitl}.")

    premissa = str(opp.get("premissa") or "").strip()
    if premissa:
        _push(riscos, f"Premissa: {premissa}")

    decisao = opp.get("decisao") if isinstance(opp.get("decisao"), dict) else {}
    score_valor = _score_1_5(decisao.get("valor"))
    score_viabilidade = _score_1_5(decisao.get("viabilidade"))
    proximo = str(decisao.get("proximo_passo") or "").strip()

    opp_text = str(opp.get("oportunidade") or "").strip()
    opp_id = str(opp.get("id") or "").strip()
    if opp_text:
        title = _clip(f"{area_name} · {opp_text}" if area_name else opp_text, 200)
    elif area_name and opp_id:
        title = _clip(f"{area_name} · {opp_id}", 200)
    elif area_name:
        title = _clip(area_name, 200)
    else:
        title = "Oportunidade importada"

    return {
        "title": title,
        "area_negocio": _clip(area_name, 200),
        "responsavel": "",
        "data": "",
        "objetivo_estrategico": _clip(str(area.get("objetivo_estrategico") or ""), 2000),
        "contexto": contexto,
        "dores": dores,
        "oportunidade": oportunidade,
        "oportunidade_tipos": _map_tipos(opp.get("tipo")),
        "dados": dados,
        "valor": valor,
        "custo": custo,
        "riscos": riscos,
        "score_valor": score_valor,
        "score_viabilidade": score_viabilidade,
        "proximo_passo": _clip(proximo, 4000),
    }


def _projects_from_import(body: CanvasImportRequest) -> list[dict]:
    schema_name = (body.schema_name or "").strip()
    if schema_name and schema_name != "aegis.canvas-oportunidades":
        raise HTTPException(
            status_code=400,
            detail="Formato inválido. Esperado schema=aegis.canvas-oportunidades.",
        )
    if body.versao is not None and str(body.versao).strip() not in ("1",):
        raise HTTPException(status_code=400, detail="Versão não suportada. Use versao \"1\".")

    areas = body.areas
    if not isinstance(areas, list) or not areas:
        raise HTTPException(status_code=400, detail="JSON sem áreas/oportunidades para importar.")

    projeto_meta = body.projeto if isinstance(body.projeto, dict) else None
    mapped: list[dict] = []
    for area in areas:
        if not isinstance(area, dict):
            continue
        opps = area.get("oportunidades")
        if not isinstance(opps, list):
            continue
        for opp in opps:
            if not isinstance(opp, dict):
                continue
            if not (
                str(opp.get("oportunidade") or "").strip()
                or str(opp.get("dor") or "").strip()
                or str(opp.get("id") or "").strip()
            ):
                continue
            mapped.append(_opportunity_to_fields(area, opp, projeto_meta))

    if not mapped:
        raise HTTPException(status_code=400, detail="Nenhuma oportunidade válida encontrada no JSON.")
    if len(mapped) > 60:
        raise HTTPException(status_code=400, detail="Limite de 60 oportunidades por importação.")
    return mapped


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


@router.post("/import")
def import_projects(
    body: CanvasImportRequest,
    user=Depends(get_verified_user),
    db: Database = Depends(get_db),
):
    """Importa aegis.canvas-oportunidades e cria um projeto por oportunidade."""
    mapped = _projects_from_import(body)
    now = datetime.now(timezone.utc)
    docs = []
    for fields in mapped:
        docs.append(
            {
                "user_id": user["_id"],
                **fields,
                "created_at": now,
                "updated_at": now,
            }
        )
    result = db.canvas_projects.insert_many(docs)
    for doc, inserted_id in zip(docs, result.inserted_ids):
        doc["_id"] = inserted_id
    return {
        "created": len(docs),
        "items": [_to_item(d, summary=True) for d in docs],
    }


@router.post("/{project_id}/import")
def import_into_project(
    project_id: str,
    body: CanvasImportRequest,
    user=Depends(get_verified_user),
    db: Database = Depends(get_db),
):
    """Importa o JSON e substitui o conteúdo do projeto aberto (1ª oportunidade)."""
    _get_owned(db, user["_id"], project_id)
    mapped = _projects_from_import(body)
    fields = mapped[0]
    updates = {**fields, "updated_at": datetime.now(timezone.utc)}
    db.canvas_projects.update_one(
        {"_id": ObjectId(project_id), "user_id": user["_id"]},
        {"$set": updates},
    )
    doc = _get_owned(db, user["_id"], project_id)
    return {
        "applied": 1,
        "available": len(mapped),
        "item": _to_item(doc),
    }


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

    if "swot_id" in data:
        updates["swot_id"] = _owned_swot_id(db, user["_id"], data["swot_id"])
    for key in ("swot_item_ids", "tows_ids"):
        if key in data:
            updates[key] = _clean_ref_ids(data[key])

    for key, value in data.items():
        if key in ("oportunidade_tipos", "swot_id", "swot_item_ids", "tows_ids"):
            continue
        if key in _LIST_FIELDS:
            updates[key] = _clean_item_list(value)
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
