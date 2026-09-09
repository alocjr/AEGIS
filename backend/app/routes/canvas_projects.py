"""Canvas de Oportunidades de IA por área — projetos do mentorado."""

import unicodedata
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pymongo.database import Database

from app.database import get_db
from app.deps import get_current_organization_id, get_verified_user, require_tool
from app.governance import repository as gov_repo
from app.governance.rules.r3_canvas import (
    canvas_para_risco_preliminar,
    opportunity_input_from_canvas_project,
)
from app.schemas import (
    OPPORTUNITY_TYPE_OPTIONS,
    CanvasAprovarProjetoRequest,
    CanvasImportRequest,
    CanvasProjectCreateRequest,
    CanvasProjectUpdateRequest,
)
from app.tools import TOOL_CANVAS

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

router = APIRouter(
    prefix="/api/canvas-projects",
    tags=["canvas-projects"],
    dependencies=[Depends(require_tool(TOOL_CANVAS))],
)

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
    "kr_ids": [],
    "cronograma": {
        "subtitulo": "",
        "pre_requisito": "",
        "criterio_aceite": "",
        "semanas": 8,
        "atividades": [],
        "marcos": [],
    },
    "dados_estruturado": {"descricao": "", "sensibilidade": None},
    "riscos_estruturado": {"descricao": "", "regulatorio": [], "human_in_the_loop": None},
    "status": "rascunho",
    "ai_system_id": None,
    "prioridade": "P4",
    "mes_inicio": "",
    "projeto_aprovado": False,
    "aprovacao_comentario": "",
    "data_inicio_real": "",
    "periodicidade": "",
    "aprovado_em": None,
}

_SENSIBILIDADE_OPTIONS = frozenset({"publico", "interno", "pessoal", "sensivel"})
_PRIORIDADES = ("P0", "P1", "P2", "P3", "P4")
_PRIORITY_RANK = {code: i for i, code in enumerate(_PRIORIDADES)}
_QUADRANT_RANK = {
    "ganho_rapido": 0,
    "aposta_estrategica": 1,
    "incremental": 2,
    "evitar": 3,
}
_MESES_INICIO = ("jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez")
_PERIODICIDADES = ("quinzenal", "mensal", "bimestral", "trimestral")


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


def _clip_week(value, *, lo: int = 1, hi: int = 52, default: int = 1) -> int:
    try:
        n = int(value)
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, n))


def _clean_cronograma(value) -> dict:
    """Normaliza o Gantt persistido no canvas (horizonte 4–52 semanas)."""
    if hasattr(value, "model_dump"):
        value = value.model_dump()
    raw = value if isinstance(value, dict) else {}
    semanas = _clip_week(raw.get("semanas"), lo=4, hi=52, default=8)

    atividades: list[dict] = []
    seen_ids: set[str] = set()
    for i, item in enumerate((raw.get("atividades") or [])[:30]):
        if not isinstance(item, dict):
            continue
        start = _clip_week(item.get("semana_inicio"), hi=semanas)
        end = _clip_week(item.get("semana_fim"), hi=semanas)
        if end < start:
            start, end = end, start
        aid = str(item.get("id") or "").strip()[:64]
        if not aid or aid in seen_ids:
            aid = f"a{i + 1:02d}"
            suffix = 2
            while aid in seen_ids:
                aid = f"a{i + 1:02d}_{suffix}"
                suffix += 1
        seen_ids.add(aid)
        atividades.append(
            {
                "id": aid,
                "titulo": str(item.get("titulo") or "").strip()[:400],
                "lideranca": str(item.get("lideranca") or "").strip()[:120],
                "semana_inicio": start,
                "semana_fim": end,
                "predecessor": str(item.get("predecessor") or "").strip()[:40],
            }
        )

    marcos: list[dict] = []
    seen_marco: set[str] = set()
    for i, item in enumerate((raw.get("marcos") or [])[:12]):
        if not isinstance(item, dict):
            continue
        mid = str(item.get("id") or "").strip()[:64]
        if not mid or mid in seen_marco:
            mid = f"m{i + 1:02d}"
            suffix = 2
            while mid in seen_marco:
                mid = f"m{i + 1:02d}_{suffix}"
                suffix += 1
        seen_marco.add(mid)
        marcos.append(
            {
                "id": mid,
                "semana": _clip_week(item.get("semana"), hi=semanas),
                "titulo": str(item.get("titulo") or "").strip()[:200],
            }
        )
    marcos.sort(key=lambda m: (m["semana"], m["id"]))

    return {
        "subtitulo": str(raw.get("subtitulo") or "").strip()[:400],
        "pre_requisito": str(raw.get("pre_requisito") or "").strip()[:500],
        "criterio_aceite": str(raw.get("criterio_aceite") or "").strip()[:1000],
        "semanas": semanas,
        "atividades": atividades,
        "marcos": marcos,
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
        "swot_id": str(doc["swot_id"]) if doc.get("swot_id") else None,
        "swot_item_ids": _clean_ref_ids(doc.get("swot_item_ids")),
        "tows_ids": _clean_ref_ids(doc.get("tows_ids")),
        "kr_ids": _clean_ref_ids(doc.get("kr_ids")),
        "status": doc.get("status") or "rascunho",
        "ai_system_id": str(doc["ai_system_id"]) if doc.get("ai_system_id") else None,
        "prioridade": _clean_prioridade(doc.get("prioridade")),
        "mes_inicio": _clean_mes_inicio(doc.get("mes_inicio")),
        "projeto_aprovado": bool(doc.get("projeto_aprovado")),
        "aprovacao_comentario": str(doc.get("aprovacao_comentario") or "").strip(),
        "data_inicio_real": str(doc.get("data_inicio_real") or "").strip(),
        "periodicidade": _clean_periodicidade(doc.get("periodicidade")),
        "aprovado_em": _iso_ts(doc.get("aprovado_em")),
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
        "cronograma": _clean_cronograma(doc.get("cronograma")),
        "opportunity_type_options": list(OPPORTUNITY_TYPE_OPTIONS),
        "dados_estruturado": doc.get("dados_estruturado")
        or {"descricao": "", "sensibilidade": None},
        "riscos_estruturado": doc.get("riscos_estruturado")
        or {"descricao": "", "regulatorio": [], "human_in_the_loop": None},
    }


_SEARCH_SKIP_KEYS = frozenset(
    {
        "_id",
        "organization_id",
        "created_by_user_id",
        "swot_id",
        "ai_system_id",
        "swot_item_ids",
        "tows_ids",
        "kr_ids",
    }
)
_SEARCH_MAX_CHARS = 200
_SEARCH_MAX_WORDS = 12


def _fold_text(value: str) -> str:
    """Minúsculas sem acento — 'gestao' encontra 'gestão'."""
    stripped = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in stripped if not unicodedata.combining(ch)).casefold()


def _query_words(q: str) -> list[str]:
    raw = (q or "").strip()[:_SEARCH_MAX_CHARS]
    words = [w for w in _fold_text(raw).split() if w]
    return words[:_SEARCH_MAX_WORDS]


def _walk_text(value) -> list[str]:
    """Recolhe strings do documento do canvas (listas, cronograma, campos livres)."""
    out: list[str] = []

    def walk(node) -> None:
        if isinstance(node, str):
            text = node.strip()
            if text:
                out.append(text)
            return
        if isinstance(node, dict):
            for key, child in node.items():
                if key in _SEARCH_SKIP_KEYS:
                    continue
                walk(child)
            return
        if isinstance(node, (list, tuple)):
            for child in node:
                walk(child)

    walk(value)
    return out


def _matches_canvas_query(doc: dict, q: str) -> bool:
    """True se todas as palavras de `q` aparecem em algum texto do canvas."""
    words = _query_words(q)
    if not words:
        return True
    blob = _fold_text(" ".join(_walk_text(doc)))
    return all(word in blob for word in words)


def _clean_prioridade(value) -> str:
    raw = str(value or "").strip().upper()
    return raw if raw in _PRIORIDADES else "P4"


def _clean_mes_inicio(value) -> str:
    raw = str(value or "").strip().lower()
    return raw if raw in _MESES_INICIO else ""


def _clean_periodicidade(value) -> str:
    raw = str(value or "").strip().lower()
    return raw if raw in _PERIODICIDADES else ""


def _clean_iso_date(value) -> str:
    raw = str(value or "").strip()[:10]
    try:
        datetime.strptime(raw, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Data de início real inválida. Use AAAA-MM-DD.")
    return raw


def _iso_ts(value) -> str | None:
    if not value:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _list_sort_key(doc: dict) -> tuple[int, int]:
    """P0→P4, depois Ganho rápido → Aposta estratégica → Incremental → Evitar."""
    prioridade = _PRIORITY_RANK.get(_clean_prioridade(doc.get("prioridade")), 4)
    score_valor = doc.get("score_valor")
    score_viabilidade = doc.get("score_viabilidade")
    try:
        valor = int(score_valor) if score_valor is not None else None
        viab = int(score_viabilidade) if score_viabilidade is not None else None
    except (TypeError, ValueError):
        valor, viab = None, None
    quadrant = _quadrant(valor, viab)
    tipo = _QUADRANT_RANK.get(quadrant, 4) if quadrant else 4
    return (prioridade, tipo)


def _owned_swot_id(db: Database, org_id, raw) -> str | None:
    """Valida que a SWOT de origem existe e pertence a organizacao."""
    swot_id = str(raw or "").strip()
    if not swot_id:
        return None
    if not ObjectId.is_valid(swot_id):
        raise HTTPException(status_code=400, detail="SWOT de origem invalida")
    exists = db.swot_analyses.find_one(
        {"_id": ObjectId(swot_id), "organization_id": org_id}, {"_id": 1}
    )
    if not exists:
        raise HTTPException(status_code=404, detail="SWOT de origem nao encontrada")
    return swot_id


def _get_owned(db: Database, org_id, project_id: str) -> dict:
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=400, detail="ID invalido")
    doc = db.canvas_projects.find_one({"_id": ObjectId(project_id), "organization_id": org_id})
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
    regs_estruturado: list[str] = []
    if isinstance(reg, list):
        regs_estruturado = [str(x).strip() for x in reg if str(x).strip()][:20]
        if regs_estruturado:
            _push(riscos, f"Regulatório: {', '.join(regs_estruturado)}.")
    hitl_raw = str(riscos_obj.get("human_in_the_loop") or "").strip().lower()
    hitl = _HITL.get(hitl_raw, hitl_raw)
    if hitl:
        _push(riscos, f"Human-in-the-loop: {hitl}.")
    hitl_estruturado = hitl_raw if hitl_raw in _HITL else None

    # Campos estruturados aditivos — preservam o que o texto livre acima perde, para a R3
    # (canvas_para_risco_preliminar). `sensibilidade` é aditivo no próprio JSON de origem.
    sensibilidade_raw = str(dados_obj.get("sensibilidade") or "").strip().lower()
    dados_estruturado = {
        "descricao": _clip(str(dados_obj.get("descricao") or ""), 1000),
        "sensibilidade": sensibilidade_raw if sensibilidade_raw in _SENSIBILIDADE_OPTIONS else None,
    }
    riscos_estruturado = {
        "descricao": _clip(str(riscos_obj.get("descricao") or ""), 1000),
        "regulatorio": regs_estruturado,
        "human_in_the_loop": hitl_estruturado,
    }

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
        "dados_estruturado": dados_estruturado,
        "riscos_estruturado": riscos_estruturado,
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
def list_projects(
    q: str = "",
    user=Depends(get_verified_user),
    org_id=Depends(get_current_organization_id),
    db: Database = Depends(get_db),
):
    """Lista projetos (canvas) da organização — P0→P4, depois tipo de quadrante.

    `q` filtra por palavras em qualquer texto do canvas (AND, sem acento).
    """
    cursor = db.canvas_projects.find({"organization_id": org_id}).sort("updated_at", -1)
    docs = [doc for doc in cursor if _matches_canvas_query(doc, q)]
    docs.sort(key=_list_sort_key)
    return {"items": [_to_item(doc, summary=True) for doc in docs]}


@router.post("")
def create_project(
    body: CanvasProjectCreateRequest,
    user=Depends(get_verified_user),
    org_id=Depends(get_current_organization_id),
    db: Database = Depends(get_db),
):
    """Cria um novo projeto/canvas vazio."""
    now = datetime.now(timezone.utc)
    title = (body.title or "Novo projeto").strip() or "Novo projeto"
    doc = {
        "organization_id": org_id,
        "created_by_user_id": user["_id"],
        "title": title,
        **_EMPTY_FIELDS,
        "created_at": now,
        "updated_at": now,
    }
    result = db.canvas_projects.insert_one(doc)
    doc["_id"] = result.inserted_id
    return _to_item(doc)


def import_projects(
    body: CanvasImportRequest,
    user=Depends(get_verified_user),
    org_id=Depends(get_current_organization_id),
    db: Database = Depends(get_db),
):
    """Importa aegis.canvas-oportunidades e cria um projeto por oportunidade (MCP)."""
    mapped = _projects_from_import(body)
    now = datetime.now(timezone.utc)
    docs = []
    for fields in mapped:
        docs.append(
            {
                "organization_id": org_id,
                "created_by_user_id": user["_id"],
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


def import_into_project(
    project_id: str,
    body: CanvasImportRequest,
    user=Depends(get_verified_user),
    org_id=Depends(get_current_organization_id),
    db: Database = Depends(get_db),
):
    """Importa o JSON e substitui o conteúdo do projeto aberto (1ª oportunidade, MCP)."""
    _get_owned(db, org_id, project_id)
    mapped = _projects_from_import(body)
    fields = mapped[0]
    updates = {**fields, "updated_at": datetime.now(timezone.utc)}
    db.canvas_projects.update_one(
        {"_id": ObjectId(project_id), "organization_id": org_id},
        {"$set": updates},
    )
    doc = _get_owned(db, org_id, project_id)
    return {
        "applied": 1,
        "available": len(mapped),
        "item": _to_item(doc),
    }


@router.post("/{project_id}/aprovar")
def aprovar_projeto(
    project_id: str,
    body: CanvasAprovarProjetoRequest,
    user=Depends(get_verified_user),
    org_id=Depends(get_current_organization_id),
    db: Database = Depends(get_db),
):
    """Aprovação executiva (C-level): quem aprovou, data real de início e periodicidade de acompanhamento."""
    doc = _get_owned(db, org_id, project_id)
    now = datetime.now(timezone.utc)
    comentario = (body.comentario or "").strip()
    if not comentario:
        raise HTTPException(status_code=400, detail="Informe as pessoas que aprovaram o projeto.")
    updates = {
        "projeto_aprovado": True,
        "aprovacao_comentario": comentario[:1000],
        "data_inicio_real": _clean_iso_date(body.data_inicio_real),
        "periodicidade": body.periodicidade,
        "updated_at": now,
    }
    if not doc.get("aprovado_em"):
        updates["aprovado_em"] = now
    db.canvas_projects.update_one(
        {"_id": ObjectId(project_id), "organization_id": org_id},
        {"$set": updates},
    )
    return _to_item(_get_owned(db, org_id, project_id))


@router.post("/{project_id}/aprovar-portfolio")
def aprovar_portfolio(
    project_id: str,
    user=Depends(get_verified_user),
    org_id=Depends(get_current_organization_id),
    db: Database = Depends(get_db),
):
    """Hook Canvas → Inventário (Seção 5.1 do plano): aprova a oportunidade para o
    portfólio, cria (ou reaproveita, se já existir) o sistema de IA correspondente no
    módulo de Governança e roda a R3 para uma classificação de risco preliminar.
    Idempotente — reexecutar não duplica o sistema de IA."""
    project = _get_owned(db, org_id, project_id)
    project_oid = ObjectId(project_id)
    now = datetime.now(timezone.utc)

    existing_system = gov_repo.find_ai_system_by_canvas_project(
        db, org_id=org_id, canvas_project_id=project_oid
    )
    if existing_system:
        if project.get("status") != "aprovado_portfolio" or not project.get("ai_system_id"):
            db.canvas_projects.update_one(
                {"_id": project_oid},
                {
                    "$set": {
                        "status": "aprovado_portfolio",
                        "ai_system_id": existing_system["_id"],
                        "updated_at": now,
                    }
                },
            )
        return {
            "ai_system_id": str(existing_system["_id"]),
            "status": existing_system.get("status"),
            "risco_preliminar": (existing_system.get("classificacao_risco") or {}).get("nivel"),
            "created": False,
        }

    dados_estruturado = project.get("dados_estruturado") or {}
    riscos_estruturado = project.get("riscos_estruturado") or {}
    risco = canvas_para_risco_preliminar(opportunity_input_from_canvas_project(project))

    finalidade = project.get("objetivo_estrategico") or ""
    if not finalidade:
        oportunidade = project.get("oportunidade") or []
        finalidade = oportunidade[0] if oportunidade else ""

    hitl_valor = riscos_estruturado.get("human_in_the_loop")
    hitl_obrigatorio = bool(hitl_valor) and hitl_valor != "nenhum"

    system = gov_repo.create_ai_system(
        db,
        org_id=org_id,
        actor_user_id=user["_id"],
        data={
            "nome": project.get("title") or "Sistema sem nome",
            "area_negocio": project.get("area_negocio") or "",
            "finalidade": finalidade,
            "descricao_dados": dados_estruturado.get("descricao") or "",
            "sensibilidade_dados": dados_estruturado.get("sensibilidade") or "interno",
            "origem_ia": "interno",
            "hitl_obrigatorio": hitl_obrigatorio,
            "hitl_descricao": "",
            "canvas_project_id": str(project_oid),
        },
    )
    gov_repo.set_ai_system_risk(
        db,
        org_id=org_id,
        system_id=system["_id"],
        nivel=risco["nivel_preliminar"],
        fonte="preliminar_r3",
    )
    system = gov_repo.update_ai_system(
        db,
        org_id=org_id,
        actor_user_id=user["_id"],
        system_id=str(system["_id"]),
        updates={"status": "aguardando_avaliacao"},
    )

    db.canvas_projects.update_one(
        {"_id": project_oid},
        {
            "$set": {
                "status": "aprovado_portfolio",
                "ai_system_id": system["_id"],
                "updated_at": now,
            }
        },
    )

    return {
        "ai_system_id": str(system["_id"]),
        "status": system.get("status"),
        "risco_preliminar": risco["nivel_preliminar"],
        "created": True,
    }


@router.get("/{project_id}")
def get_project(
    project_id: str,
    user=Depends(get_verified_user),
    org_id=Depends(get_current_organization_id),
    db: Database = Depends(get_db),
):
    doc = _get_owned(db, org_id, project_id)
    return _to_item(doc)


@router.put("/{project_id}")
def update_project(
    project_id: str,
    body: CanvasProjectUpdateRequest,
    user=Depends(get_verified_user),
    org_id=Depends(get_current_organization_id),
    db: Database = Depends(get_db),
):
    """Salva preenchimento do canvas."""
    _get_owned(db, org_id, project_id)
    updates: dict = {"updated_at": datetime.now(timezone.utc)}
    data = body.model_dump(exclude_unset=True)

    if "oportunidade_tipos" in data and data["oportunidade_tipos"] is not None:
        allowed = set(OPPORTUNITY_TYPE_OPTIONS)
        cleaned = [t for t in data["oportunidade_tipos"] if t in allowed]
        updates["oportunidade_tipos"] = cleaned

    if "swot_id" in data:
        updates["swot_id"] = _owned_swot_id(db, org_id, data["swot_id"])
    for key in ("swot_item_ids", "tows_ids", "kr_ids"):
        if key in data:
            updates[key] = _clean_ref_ids(data[key])
    if "cronograma" in data and data["cronograma"] is not None:
        updates["cronograma"] = _clean_cronograma(data["cronograma"])
    if "prioridade" in data:
        updates["prioridade"] = _clean_prioridade(data["prioridade"])
    if "mes_inicio" in data:
        updates["mes_inicio"] = _clean_mes_inicio(data["mes_inicio"])

    for key, value in data.items():
        if key in (
            "oportunidade_tipos",
            "swot_id",
            "swot_item_ids",
            "tows_ids",
            "kr_ids",
            "cronograma",
            "prioridade",
            "mes_inicio",
        ):
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
        {"_id": ObjectId(project_id), "organization_id": org_id},
        {"$set": updates},
    )
    doc = _get_owned(db, org_id, project_id)
    return _to_item(doc)


@router.delete("/{project_id}")
def delete_project(
    project_id: str,
    user=Depends(get_verified_user),
    org_id=Depends(get_current_organization_id),
    db: Database = Depends(get_db),
):
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=400, detail="ID invalido")
    result = db.canvas_projects.delete_one(
        {"_id": ObjectId(project_id), "organization_id": org_id}
    )
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Projeto nao encontrado")
    return {"message": "Projeto removido", "id": project_id}
