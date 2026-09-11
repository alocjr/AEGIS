"""Tools MCP do mentorado (JWT verificado).

Leitura e escrita nas ferramentas do AI Hub: Maturidade, SWOT/TOWS, OKR, Canvas e
Governança. Domain logic reutiliza os handlers em `app.routes.*`.
"""

from __future__ import annotations

from typing import Any

from app.database import get_db
from app.governance.schemas import (
    AiSystemCreateRequest,
    AiSystemUpdateRequest,
    GateChecklistUpdateRequest,
    GateDecisionRequest,
    RiskAssessmentCreateRequest,
)
from app.mcp.auth import require_tool_access, require_verified_user
from app.mcp.util import call_route, parse_json_list, parse_json_object, validate_model
from app.orgs import org_ids_of, organizations_payload
from app.routes import auth as auth_routes
from app.routes import canvas_projects as canvas_routes
from app.routes import course as course_routes
from app.routes import governance as gov_routes
from app.routes import maturity as maturity_routes
from app.routes import okrs as okr_routes
from app.routes import strategic_map as strategic_map_routes
from app.routes import swot_analysis as swot_routes
from app.schemas import (
    CanvasAprovarProjetoRequest,
    CanvasImportRequest,
    CanvasProjectCloneRequest,
    CanvasProjectCreateRequest,
    CanvasProjectUpdateRequest,
    CanvasRoadmapMoveRequest,
    MaturityAnswersRequest,
    MaturityVisibilityRequest,
    OkrCycleCreateRequest,
    OkrCycleUpdateRequest,
    SwotAnalysisUpdateRequest,
    SwotImportRequest,
    SwitchOrganizationRequest,
)
from app.tools import (
    TOOL_CANVAS,
    TOOL_GOVERNANCE,
    TOOL_MATURITY,
    TOOL_OKR,
    TOOL_STRATEGIC_MAP,
    TOOL_SWOT,
)

try:
    from fastmcp.exceptions import ToolError
except ImportError:  # pragma: no cover
    class ToolError(Exception):
        pass


def _reload_membership(user: dict) -> dict:
    """Releia organization_id/organization_ids no Mongo — a org ativa pode ter mudado
    via org_switch (ou pelo admin) desde que o dict foi resolvido."""
    uid = user.get("_id")
    if not uid:
        return user
    fresh = get_db().users.find_one(
        {"_id": uid},
        {"organization_id": 1, "organization_ids": 1, "org_admin_ids": 1, "is_org_admin": 1},
    )
    if not fresh:
        return user
    return {**user, **fresh}


def _with_org(user: dict) -> tuple[dict, Any]:
    """Usuário com membership atual + org ativa (mesmo critério de deps.get_current_organization_id).

    Sempre consulta o documento atual: tools em paralelo com `org_switch` ainda
    podem ver a org antiga; depois do switch, a próxima tool usa a nova.
    """
    user = _reload_membership(user)
    org_id = user.get("organization_id")
    if not org_id:
        ids = org_ids_of(user)
        org_id = ids[0] if ids else None
    if not org_id:
        raise ToolError("Usuario sem organizacao atribuida. Contate o suporte.")
    return user, org_id


def _org_id(user: dict):
    """Organizacao ativa — atalho quando o caller já tem o dict fresco."""
    return _with_org(user)[1]


def build_org_context(user: dict, db) -> dict:
    """Payload de org_list / org_switch — memberships + org ativa para o modelo."""
    ids = org_ids_of(user)
    active = user.get("organization_id") or (ids[0] if ids else None)
    orgs = organizations_payload(user, db)
    for item in orgs:
        item["active"] = bool(active) and item["id"] == str(active)
    active_name = next((item["name"] for item in orgs if item.get("active")), "")
    multi = len(orgs) > 1
    return {
        "organization_id": str(active) if active else None,
        "organization_name": active_name,
        "organizations": orgs,
        "hint": (
            "Maturidade, SWOT, OKR, Canvas, Governança e Mapa Estratégico são da "
            "organização ativa. Para mudar, chame org_switch com o id e só então as "
            "demais tools — nunca no mesmo turno em paralelo. Artefatos com "
            "visibility=private só o autor vê."
            if multi
            else "Usuário com uma única organização. Artefatos com visibility=private só o autor vê."
        ),
    }


_OBJ_KEYS = (
    "id",
    "titulo",
    "descricao",
    "dono",
    "pilar",
    "swot_id",
    "swot_item_ids",
    "tows_ids",
    "key_results",
)
_KR_KEYS = (
    "id",
    "titulo",
    "descricao",
    "unidade",
    "baseline",
    "current",
    "target",
    "direction",
    "dono",
)


def _strip_kr(kr: dict) -> dict:
    return {k: kr[k] for k in _KR_KEYS if k in kr}


def _strip_objective(obj: dict) -> dict:
    out = {k: obj[k] for k in _OBJ_KEYS if k in obj and k != "key_results"}
    out["key_results"] = [_strip_kr(kr) for kr in (obj.get("key_results") or []) if isinstance(kr, dict)]
    return out


def _cycle_objectives(cycle: dict) -> list[dict]:
    return [_strip_objective(o) for o in (cycle.get("objectives") or []) if isinstance(o, dict)]


def _find_objective(objectives: list[dict], objective_id: str) -> tuple[int, dict]:
    oid = (objective_id or "").strip()
    for i, obj in enumerate(objectives):
        if str(obj.get("id") or "") == oid:
            return i, obj
    raise ToolError(f"Objective '{oid}' nao encontrado neste ciclo.")


def _find_kr(key_results: list[dict], kr_id: str) -> tuple[int, dict]:
    kid = (kr_id or "").strip()
    for i, kr in enumerate(key_results):
        if str(kr.get("id") or "") == kid:
            return i, kr
    raise ToolError(f"Key Result '{kid}' nao encontrado neste objective.")


_CRONO_META_KEYS = ("subtitulo", "pre_requisito", "criterio_aceite", "semanas")
_ATIVIDADE_KEYS = ("id", "titulo", "lideranca", "semana_inicio", "semana_fim", "predecessor")
_MARCO_KEYS = ("id", "semana", "titulo")
_MAX_ATIVIDADES = 30
_MAX_MARCOS = 12


def _empty_cronograma() -> dict:
    return canvas_routes._clean_cronograma({})


def _cronograma_of(project: dict) -> dict:
    return canvas_routes._clean_cronograma(project.get("cronograma"))


def _cronograma_pack(item: dict) -> dict:
    return {
        "id": item.get("id"),
        "title": item.get("title"),
        "cronograma": item.get("cronograma") or _empty_cronograma(),
    }


def _roadmap_semanas_of(item: dict) -> int:
    if item.get("semanas"):
        try:
            return int(item["semanas"])
        except (TypeError, ValueError):
            pass
    return _cronograma_of(item).get("semanas") or 8


def _roadmap_pack_item(item: dict) -> dict:
    """Recorte estável do Gantt de 18 meses (MCP)."""
    return {
        "id": item.get("id"),
        "title": item.get("title"),
        "area_negocio": item.get("area_negocio") or "",
        "prioridade": item.get("prioridade") or "P4",
        "data_inicio_real": item.get("data_inicio_real") or "",
        "mes_inicio": item.get("mes_inicio") or "",
        "semanas": _roadmap_semanas_of(item),
        "periodicidade": item.get("periodicidade") or "",
        "projeto_aprovado": bool(item.get("projeto_aprovado")),
    }


def _validate_roadmap_semanas(semanas: int) -> int:
    try:
        n = int(semanas)
    except (TypeError, ValueError) as exc:
        raise ToolError("semanas deve ser um inteiro de 4 a 52 (4 semanas ≈ 1 mês no Gantt).") from exc
    if n < 4 or n > 52:
        raise ToolError("semanas deve ser um inteiro de 4 a 52 (4 semanas ≈ 1 mês no Gantt).")
    return n


def _find_crono_item(items: list[dict], item_id: str, label: str) -> tuple[int, dict]:
    iid = (item_id or "").strip()
    for i, item in enumerate(items):
        if str(item.get("id") or "") == iid:
            return i, dict(item)
    raise ToolError(f"{label} '{iid}' nao encontrado neste cronograma.")


def _merge_cronograma(current: dict, patch: dict) -> dict:
    """Mescla metadados; `atividades`/`marcos` substituem a lista se enviados."""
    out = canvas_routes._clean_cronograma(current)
    for key in _CRONO_META_KEYS:
        if key in patch:
            out[key] = patch[key]
    if "atividades" in patch:
        atividades = patch["atividades"]
        if not isinstance(atividades, list):
            raise ToolError("atividades deve ser um array.")
        out["atividades"] = [a for a in atividades if isinstance(a, dict)]
    if "marcos" in patch:
        marcos = patch["marcos"]
        if not isinstance(marcos, list):
            raise ToolError("marcos deve ser um array.")
        out["marcos"] = [m for m in marcos if isinstance(m, dict)]
    return canvas_routes._clean_cronograma(out)


def _add_cronograma_atividade(current: dict, atividade: dict) -> dict:
    out = canvas_routes._clean_cronograma(current)
    if len(out["atividades"]) >= _MAX_ATIVIDADES:
        raise ToolError(f"Limite de {_MAX_ATIVIDADES} atividades por cronograma.")
    if not str(atividade.get("titulo") or "").strip():
        raise ToolError("Informe titulo da atividade.")
    out["atividades"].append({k: atividade[k] for k in _ATIVIDADE_KEYS if k in atividade})
    return canvas_routes._clean_cronograma(out)


def _update_cronograma_atividade(current: dict, atividade_id: str, fields: dict) -> dict:
    out = canvas_routes._clean_cronograma(current)
    idx, item = _find_crono_item(out["atividades"], atividade_id, "Atividade")
    patch = {k: v for k, v in fields.items() if k in _ATIVIDADE_KEYS and k != "id"}
    item.update(patch)
    out["atividades"][idx] = item
    return canvas_routes._clean_cronograma(out)


def _delete_cronograma_atividade(current: dict, atividade_id: str) -> dict:
    out = canvas_routes._clean_cronograma(current)
    _find_crono_item(out["atividades"], atividade_id, "Atividade")
    out["atividades"] = [a for a in out["atividades"] if str(a.get("id") or "") != atividade_id.strip()]
    return canvas_routes._clean_cronograma(out)


def _add_cronograma_marco(current: dict, marco: dict) -> dict:
    out = canvas_routes._clean_cronograma(current)
    if len(out["marcos"]) >= _MAX_MARCOS:
        raise ToolError(f"Limite de {_MAX_MARCOS} marcos por cronograma.")
    out["marcos"].append({k: marco[k] for k in _MARCO_KEYS if k in marco})
    return canvas_routes._clean_cronograma(out)


def _update_cronograma_marco(current: dict, marco_id: str, fields: dict) -> dict:
    out = canvas_routes._clean_cronograma(current)
    idx, item = _find_crono_item(out["marcos"], marco_id, "Marco")
    patch = {k: v for k, v in fields.items() if k in _MARCO_KEYS and k != "id"}
    item.update(patch)
    out["marcos"][idx] = item
    return canvas_routes._clean_cronograma(out)


def _delete_cronograma_marco(current: dict, marco_id: str) -> dict:
    out = canvas_routes._clean_cronograma(current)
    _find_crono_item(out["marcos"], marco_id, "Marco")
    out["marcos"] = [m for m in out["marcos"] if str(m.get("id") or "") != marco_id.strip()]
    return canvas_routes._clean_cronograma(out)


def _maturity_levels(question: dict) -> dict[str, str]:
    raw = question.get("levels") or {}
    out: dict[str, str] = {}
    for n in ("1", "2", "3", "4", "5"):
        val = raw.get(n)
        if val:
            out[n] = str(val)
    return out


def _maturity_questions(model: dict, tier: str) -> list[dict]:
    rows: list[dict] = []
    for dim in model.get("dimensions") or []:
        dim_id = str(dim.get("id") or "")
        dim_name = str(dim.get("name") or dim_id)
        for q in dim.get("questions") or []:
            q_tier = str(q.get("tier") or "basico")
            if not maturity_routes._is_visible_tier(q_tier, tier):
                continue
            qid = str(q.get("id") or "")
            if not qid:
                continue
            rows.append(
                {
                    "id": qid,
                    "dimension_id": dim_id,
                    "dimension": dim_name,
                    "text": str(q.get("text") or ""),
                    "levels": _maturity_levels(q),
                }
            )
    return rows


def _coerce_maturity_answers(raw: dict, *, known: set[str]) -> dict[str, int]:
    out: dict[str, int] = {}
    unknown: list[str] = []
    for key, value in raw.items():
        qid = str(key or "").strip()
        if qid not in known:
            unknown.append(qid)
            continue
        try:
            score = int(value)
        except (TypeError, ValueError) as exc:
            raise ToolError(f"Nota invalida para {qid}: {value}") from exc
        if score < 1 or score > 5:
            raise ToolError(f"Nota de {qid} deve ser um inteiro de 1 a 5.")
        out[qid] = score
    if unknown:
        raise ToolError(f"Perguntas desconhecidas neste modelo: {', '.join(unknown)}.")
    if not out:
        raise ToolError("Informe ao menos uma resposta (question_id + score, ou answers).")
    return out


def register_learner_tools(mcp) -> None:
    def _swot_user() -> dict:
        user = require_verified_user()
        require_tool_access(user, TOOL_SWOT)
        return _reload_membership(user)

    def _canvas_user() -> dict:
        user = require_verified_user()
        require_tool_access(user, TOOL_CANVAS)
        return _reload_membership(user)

    def _maturity_user() -> dict:
        user = require_verified_user()
        require_tool_access(user, TOOL_MATURITY)
        return _reload_membership(user)

    def _map_user() -> dict:
        user = require_verified_user()
        require_tool_access(user, TOOL_STRATEGIC_MAP)
        return _reload_membership(user)

    def _okr_user() -> dict:
        user = require_verified_user()
        require_tool_access(user, TOOL_OKR)
        return _reload_membership(user)

    def _gov_user() -> dict:
        user = require_verified_user()
        require_tool_access(user, TOOL_GOVERNANCE)
        return _reload_membership(user)

    # ── Organizações (sem gate de ferramenta) ────────────────────────────────

    @mcp.tool
    def org_list() -> dict:
        """Lista as organizações do usuário e qual está ativa.

        Mentoria (progresso/quiz) é por pessoa. Maturidade, SWOT, OKR, Canvas,
        Governança e Mapa Estratégico são da organização ativa. Se houver mais
        de uma, chame org_switch antes de trabalhar na outra — nunca em paralelo
        com outras tools no mesmo turno.
        """
        user = _reload_membership(require_verified_user())
        return build_org_context(user, get_db())

    @mcp.tool
    def org_switch(organization_id: str) -> dict:
        """Troca a organização ativa. Só aceita orgs das quais o usuário já é membro.

        Depois desta tool, as demais (swot_*, canvas_*, okr_*, maturity_*,
        governance_*, strategic_map) passam a ler/gravar nesta org. Não chame
        essas tools no mesmo turno em paralelo — espere o resultado do switch.
        """
        user = require_verified_user()
        body = validate_model(SwitchOrganizationRequest, {"organization_id": organization_id})
        updated = call_route(auth_routes.switch_organization, payload=body, user=user, db=get_db())
        # Recarrega o doc: switch reescreve organization_id / is_org_admin no Mongo.
        fresh = get_db().users.find_one({"_id": user["_id"]}) or {**user}
        ctx = build_org_context(fresh, get_db())
        ctx["user"] = {
            "id": updated.get("id"),
            "is_org_admin": updated.get("is_org_admin"),
            "organization_id": updated.get("organization_id"),
            "organization_name": updated.get("organization_name"),
        }
        return ctx

    # ── SWOT / TOWS ──────────────────────────────────────────────────────────

    @mcp.tool
    def swot_get() -> dict:
        """Retorna a SWOT de IA da organização do mentorado (cria vazia se não existir)."""
        user = _swot_user()
        return call_route(swot_routes.get_swot, user=user, org_id=_org_id(user), db=get_db())

    @mcp.tool
    def swot_get_by_id(swot_id: str) -> dict:
        """Retorna uma SWOT específica da organização pelo id."""
        user = _swot_user()
        return call_route(
            swot_routes.get_swot_by_id,
            swot_id=swot_id,
            user=user,
            org_id=_org_id(user),
            db=get_db(),
        )

    @mcp.tool
    def swot_list() -> dict:
        """Lista as SWOTs da organização ativa (privadas de outros membros ficam ocultas)."""
        user = _swot_user()
        return call_route(swot_routes.list_swots, user=user, org_id=_org_id(user), db=get_db())

    @mcp.tool
    def swot_by_maturity(maturity_response_id: str) -> dict:
        """Retorna a SWOT vinculada a uma autoavaliação de maturidade (404 se não existir)."""
        user = _swot_user()
        return call_route(
            swot_routes.get_swot_by_maturity,
            maturity_response_id=maturity_response_id,
            user=user,
            org_id=_org_id(user),
            db=get_db(),
        )

    @mcp.tool
    def swot_import(document: dict[str, Any] | str) -> dict:
        """Importa JSON aegis.swot-ia (v1–v3) e substitui a SWOT da organização."""
        user = _swot_user()
        raw = parse_json_object(document)
        body = validate_model(SwotImportRequest, raw)
        return call_route(
            swot_routes.import_swot, body=body, user=user, org_id=_org_id(user), db=get_db()
        )

    @mcp.tool
    def swot_update(
        fields: dict[str, Any] | str,
        swot_id: str | None = None,
        rebuild_tows: bool = False,
    ) -> dict:
        """Atualiza a SWOT (ótica, quadrantes, TOWS, veredito, visibilidade). Sem swot_id, usa a mais recente.

        Campos: optica, pilares, forcas, fraquezas, oportunidades, ameacas, watchlist,
        tows_fo, tows_fa, tows_fxo, tows_fxa, veredito_tipo, veredito_titulo, veredito_texto,
        visibility (shared|private). Escopo: organização ativa.
        rebuild_tows=true recalcula as iniciativas TOWS a partir dos itens marcados (tows=true).
        """
        user = _swot_user()
        raw = parse_json_object(fields, label="fields")
        body = validate_model(SwotAnalysisUpdateRequest, raw)
        kwargs = {
            "body": body,
            "rebuild_tows": rebuild_tows,
            "user": user,
            "org_id": _org_id(user),
            "db": get_db(),
        }
        if swot_id:
            return call_route(swot_routes.update_swot_by_id, swot_id=swot_id, **kwargs)
        return call_route(swot_routes.update_swot, **kwargs)

    @mcp.tool
    def swot_from_maturity(maturity_response_id: str) -> dict:
        """Cria ou atualiza a SWOT a partir de uma autoavaliação de maturidade completa."""
        user = _swot_user()
        return call_route(
            swot_routes.create_swot_from_maturity,
            maturity_response_id=maturity_response_id,
            user=user,
            org_id=_org_id(user),
            db=get_db(),
        )

    @mcp.tool
    def tows_rebuild(swot_id: str | None = None) -> dict:
        """Recalcula as iniciativas TOWS (FO, FA, FxO, FxA) a partir dos itens SWOT com tows=true."""
        user = _swot_user()
        body = validate_model(SwotAnalysisUpdateRequest, {})
        kwargs = {
            "body": body,
            "rebuild_tows": True,
            "user": user,
            "org_id": _org_id(user),
            "db": get_db(),
        }
        if swot_id:
            return call_route(swot_routes.update_swot_by_id, swot_id=swot_id, **kwargs)
        return call_route(swot_routes.update_swot, **kwargs)

    # ── Canvas ───────────────────────────────────────────────────────────────

    @mcp.tool
    def canvas_list(q: str = "") -> dict:
        """Lista os projetos (canvas) da organização ativa, ordenados de P0 a P4.

        `q` (opcional): busca por palavras em qualquer texto do canvas
        (título, área, dores, cronograma, etc.). Todas as palavras precisam aparecer.
        """
        user = _canvas_user()
        return call_route(
            canvas_routes.list_projects,
            q=q or "",
            user=user,
            org_id=_org_id(user),
            db=get_db(),
        )

    @mcp.tool
    def canvas_get(project_id: str) -> dict:
        """Retorna um projeto/canvas pelo id."""
        user = _canvas_user()
        return call_route(
            canvas_routes.get_project,
            project_id=project_id,
            user=user,
            org_id=_org_id(user),
            db=get_db(),
        )

    @mcp.tool
    def canvas_create(title: str = "Novo projeto") -> dict:
        """Cria um projeto/canvas vazio."""
        user = _canvas_user()
        body = validate_model(CanvasProjectCreateRequest, {"title": title})
        return call_route(
            canvas_routes.create_project, body=body, user=user, org_id=_org_id(user), db=get_db()
        )

    @mcp.tool
    def canvas_clone(
        project_id: str,
        organization_id: str,
        title: str | None = None,
    ) -> dict:
        """Clona o canvas (com cronograma) para uma organização da qual o usuário já é membro.

        Aprovação e portfólio não são copiados. Vínculos SWOT/OKR só se o destino
        for a mesma org. Depois, se o destino não for a org ativa, chame org_switch.
        """
        user = _canvas_user()
        payload: dict = {"organization_id": organization_id}
        if title:
            payload["title"] = title
        body = validate_model(CanvasProjectCloneRequest, payload)
        return call_route(
            canvas_routes.clone_project,
            project_id=project_id,
            body=body,
            user=user,
            org_id=_org_id(user),
            db=get_db(),
        )

    @mcp.tool
    def canvas_import(document: dict[str, Any] | str) -> dict:
        """Importa aegis.canvas-oportunidades e cria um projeto por oportunidade."""
        user = _canvas_user()
        raw = parse_json_object(document)
        body = validate_model(CanvasImportRequest, raw)
        return call_route(
            canvas_routes.import_projects, body=body, user=user, org_id=_org_id(user), db=get_db()
        )

    @mcp.tool
    def canvas_import_into(project_id: str, document: dict[str, Any] | str) -> dict:
        """Importa o JSON no projeto aberto (aplica a 1ª oportunidade)."""
        user = _canvas_user()
        raw = parse_json_object(document)
        body = validate_model(CanvasImportRequest, raw)
        return call_route(
            canvas_routes.import_into_project,
            project_id=project_id,
            body=body,
            user=user,
            org_id=_org_id(user),
            db=get_db(),
        )

    @mcp.tool
    def canvas_update(project_id: str, fields: dict[str, Any] | str) -> dict:
        """Atualiza campos de um projeto/canvas existente. Escopo: organização ativa.

        `fields.cronograma` substitui o Gantt inteiro. Para criar/editar/excluir o
        cronograma sem apagar atividades, use canvas_cronograma_create,
        canvas_cronograma_update, canvas_cronograma_delete e as tools de atividade/marco.
        Prioridade C-level: `prioridade` (P0–P4) e `mes_inicio` (jan–dez).
        Visibilidade: `visibility` (`shared` | `private`).
        """
        user = _canvas_user()
        raw = parse_json_object(fields, label="fields")
        body = validate_model(CanvasProjectUpdateRequest, raw)
        return call_route(
            canvas_routes.update_project,
            project_id=project_id,
            body=body,
            user=user,
            org_id=_org_id(user),
            db=get_db(),
        )

    def _canvas_load(user: dict, project_id: str) -> dict:
        return call_route(
            canvas_routes.get_project,
            project_id=project_id,
            user=user,
            org_id=_org_id(user),
            db=get_db(),
        )

    def _canvas_save_cronograma(user: dict, project_id: str, cronograma: dict) -> dict:
        body = validate_model(CanvasProjectUpdateRequest, {"cronograma": cronograma})
        item = call_route(
            canvas_routes.update_project,
            project_id=project_id,
            body=body,
            user=user,
            org_id=_org_id(user),
            db=get_db(),
        )
        return _cronograma_pack(item)

    @mcp.tool
    def canvas_cronograma_get(project_id: str) -> dict:
        """Retorna o cronograma (Gantt de semanas + marcos) do projeto."""
        user = _canvas_user()
        return _cronograma_pack(_canvas_load(user, project_id))

    @mcp.tool
    def canvas_cronograma_create(project_id: str, cronograma: dict[str, Any] | str) -> dict:
        """Cria ou substitui o cronograma (Gantt) do projeto.

        Campos: subtitulo?, pre_requisito?, criterio_aceite?, semanas (4–52, padrão 8),
        atividades[] (id?, titulo, lideranca?, semana_inicio, semana_fim, predecessor?),
        marcos[] (id?, semana, titulo). Para acrescentar um item sem apagar os outros,
        use canvas_cronograma_add_atividade ou canvas_cronograma_add_marco.
        """
        user = _canvas_user()
        _canvas_load(user, project_id)
        raw = parse_json_object(cronograma, label="cronograma")
        return _canvas_save_cronograma(user, project_id, canvas_routes._clean_cronograma(raw))

    @mcp.tool
    def canvas_cronograma_update(project_id: str, fields: dict[str, Any] | str) -> dict:
        """Atualiza o cronograma (merge). Metadados mesclam; atividades/marcos, se enviados, substituem a lista.

        Campos: subtitulo, pre_requisito, criterio_aceite, semanas, atividades, marcos.
        """
        user = _canvas_user()
        current = _cronograma_of(_canvas_load(user, project_id))
        patch = parse_json_object(fields, label="fields")
        return _canvas_save_cronograma(user, project_id, _merge_cronograma(current, patch))

    @mcp.tool
    def canvas_cronograma_delete(project_id: str) -> dict:
        """Exclui o cronograma do projeto (zera atividades, marcos e textos; horizonte volta a 8 semanas)."""
        user = _canvas_user()
        _canvas_load(user, project_id)
        return _canvas_save_cronograma(user, project_id, _empty_cronograma())

    @mcp.tool
    def canvas_cronograma_add_atividade(project_id: str, atividade: dict[str, Any] | str) -> dict:
        """Adiciona uma atividade ao Gantt sem apagar as outras. Obrigatório: titulo."""
        user = _canvas_user()
        current = _cronograma_of(_canvas_load(user, project_id))
        raw = parse_json_object(atividade, label="atividade")
        return _canvas_save_cronograma(user, project_id, _add_cronograma_atividade(current, raw))

    @mcp.tool
    def canvas_cronograma_update_atividade(
        project_id: str,
        atividade_id: str,
        fields: dict[str, Any] | str,
    ) -> dict:
        """Atualiza uma atividade do Gantt (merge: titulo, lideranca, semana_inicio, semana_fim, predecessor)."""
        user = _canvas_user()
        current = _cronograma_of(_canvas_load(user, project_id))
        patch = parse_json_object(fields, label="fields")
        return _canvas_save_cronograma(
            user, project_id, _update_cronograma_atividade(current, atividade_id, patch)
        )

    @mcp.tool
    def canvas_cronograma_delete_atividade(project_id: str, atividade_id: str) -> dict:
        """Remove uma atividade do Gantt pelo id."""
        user = _canvas_user()
        current = _cronograma_of(_canvas_load(user, project_id))
        return _canvas_save_cronograma(
            user, project_id, _delete_cronograma_atividade(current, atividade_id)
        )

    @mcp.tool
    def canvas_cronograma_add_marco(project_id: str, marco: dict[str, Any] | str) -> dict:
        """Adiciona um marco de decisão ao Gantt sem apagar os outros. Campos: semana, titulo."""
        user = _canvas_user()
        current = _cronograma_of(_canvas_load(user, project_id))
        raw = parse_json_object(marco, label="marco")
        return _canvas_save_cronograma(user, project_id, _add_cronograma_marco(current, raw))

    @mcp.tool
    def canvas_cronograma_update_marco(
        project_id: str,
        marco_id: str,
        fields: dict[str, Any] | str,
    ) -> dict:
        """Atualiza um marco do Gantt (merge: semana, titulo)."""
        user = _canvas_user()
        current = _cronograma_of(_canvas_load(user, project_id))
        patch = parse_json_object(fields, label="fields")
        return _canvas_save_cronograma(
            user, project_id, _update_cronograma_marco(current, marco_id, patch)
        )

    @mcp.tool
    def canvas_cronograma_delete_marco(project_id: str, marco_id: str) -> dict:
        """Remove um marco do Gantt pelo id."""
        user = _canvas_user()
        current = _cronograma_of(_canvas_load(user, project_id))
        return _canvas_save_cronograma(user, project_id, _delete_cronograma_marco(current, marco_id))

    @mcp.tool
    def canvas_approve_portfolio(project_id: str) -> dict:
        """Aprova o canvas para o portfólio e cria (ou reaproveita) o sistema no inventário de Governança."""
        user = _canvas_user()
        return call_route(
            canvas_routes.aprovar_portfolio,
            project_id=project_id,
            user=user,
            org_id=_org_id(user),
            db=get_db(),
        )

    @mcp.tool
    def canvas_aprovar_projeto(
        project_id: str,
        comentario: str,
        data_inicio_real: str,
        periodicidade: str,
    ) -> dict:
        """Aprovação executiva do projeto (C-level). Coloca o canvas no Roadmap (Gantt de 18 meses).

        comentario: pessoas que aprovaram (ex.: 'Ana CEO, Bruno CFO').
        data_inicio_real: data real de início no formato AAAA-MM-DD.
        periodicidade: quinzenal, mensal, bimestral ou trimestral.
        Para só reagendar um projeto já aprovado, use canvas_roadmap_update.
        """
        user = _canvas_user()
        body = validate_model(
            CanvasAprovarProjetoRequest,
            {
                "comentario": comentario,
                "data_inicio_real": data_inicio_real,
                "periodicidade": periodicidade,
            },
        )
        return call_route(
            canvas_routes.aprovar_projeto,
            project_id=project_id,
            body=body,
            user=user,
            org_id=_org_id(user),
            db=get_db(),
        )

    def _roadmap_apply_semanas(user: dict, project_id: str, semanas: int) -> dict:
        n = _validate_roadmap_semanas(semanas)
        current = _cronograma_of(_canvas_load(user, project_id))
        packed = _canvas_save_cronograma(user, project_id, _merge_cronograma(current, {"semanas": n}))
        return packed

    def _roadmap_current(user: dict, project_id: str) -> dict:
        item = _canvas_load(user, project_id)
        item["semanas"] = _cronograma_of(item).get("semanas") or 8
        return item

    @mcp.tool
    def canvas_roadmap_list() -> dict:
        """Lista o Roadmap da org ativa: projetos aprovados com data de início, no Gantt de 18 meses.

        A largura da barra no Gantt é `semanas` (4 semanas ≈ 1 mês). Use canvas_roadmap_add
        para incluir um canvas e canvas_roadmap_update para mudar a data ou a duração.
        """
        user = _canvas_user()
        listed = call_route(
            canvas_routes.list_roadmap,
            user=user,
            org_id=_org_id(user),
            db=get_db(),
        )
        items = [_roadmap_pack_item(i) for i in (listed.get("items") or [])]
        return {"items": items}

    @mcp.tool
    def canvas_roadmap_add(
        project_id: str,
        data_inicio_real: str,
        comentario: str | None = None,
        periodicidade: str | None = None,
        semanas: int | None = None,
    ) -> dict:
        """Inclui um canvas no Roadmap (Gantt de 18 meses) na org ativa.

        Se o projeto ainda não foi aprovado, informe `comentario` (quem aprovou) e
        `periodicidade` (`quinzenal` | `mensal` | `bimestral` | `trimestral`) — equivale
        a canvas_aprovar_projeto. Se já estiver aprovado, só agenda `data_inicio_real`
        (AAAA-MM-DD). `semanas` (4–52, opcional) define a duração da barra (4 ≈ 1 mês).
        """
        user = _canvas_user()
        current = _roadmap_current(user, project_id)
        start = (data_inicio_real or "").strip()
        if current.get("projeto_aprovado"):
            body = validate_model(CanvasRoadmapMoveRequest, {"data_inicio_real": start})
            item = call_route(
                canvas_routes.move_roadmap_project,
                project_id=project_id,
                body=body,
                user=user,
                org_id=_org_id(user),
                db=get_db(),
            )
        else:
            comment = (comentario or "").strip()
            period = (periodicidade or "").strip()
            if not comment or not period:
                raise ToolError(
                    "Projeto nao aprovado: informe comentario (quem aprovou) e "
                    "periodicidade (quinzenal, mensal, bimestral ou trimestral) "
                    "para inclui-lo no roadmap."
                )
            body = validate_model(
                CanvasAprovarProjetoRequest,
                {
                    "comentario": comment,
                    "data_inicio_real": start,
                    "periodicidade": period,
                },
            )
            item = call_route(
                canvas_routes.aprovar_projeto,
                project_id=project_id,
                body=body,
                user=user,
                org_id=_org_id(user),
                db=get_db(),
            )
        if semanas is not None:
            packed = _roadmap_apply_semanas(user, project_id, semanas)
            item["semanas"] = packed["cronograma"]["semanas"]
        else:
            item["semanas"] = _roadmap_semanas_of(item)
        return _roadmap_pack_item(item)

    @mcp.tool
    def canvas_roadmap_update(
        project_id: str,
        data_inicio_real: str | None = None,
        semanas: int | None = None,
    ) -> dict:
        """Edita um projeto no Roadmap: reagenda a data de início e/ou a duração em semanas.

        `data_inicio_real`: AAAA-MM-DD (a duração não muda). `semanas`: 4–52 (4 ≈ 1 mês no Gantt).
        Informe ao menos um dos dois. Só projetos já aprovados.
        """
        user = _canvas_user()
        start = (data_inicio_real or "").strip()
        if not start and semanas is None:
            raise ToolError("Informe data_inicio_real e/ou semanas.")
        current = _roadmap_current(user, project_id)
        if not current.get("projeto_aprovado"):
            raise ToolError(
                "So projetos aprovados entram no roadmap. Use canvas_roadmap_add "
                "(comentario + periodicidade) ou canvas_aprovar_projeto."
            )
        item = current
        if start:
            body = validate_model(CanvasRoadmapMoveRequest, {"data_inicio_real": start})
            item = call_route(
                canvas_routes.move_roadmap_project,
                project_id=project_id,
                body=body,
                user=user,
                org_id=_org_id(user),
                db=get_db(),
            )
        if semanas is not None:
            packed = _roadmap_apply_semanas(user, project_id, semanas)
            item["semanas"] = packed["cronograma"]["semanas"]
        else:
            item["semanas"] = _roadmap_semanas_of(item)
        return _roadmap_pack_item(item)

    # ── Curso ────────────────────────────────────────────────────────────────

    @mcp.tool
    def course_get(course_slug: str | None = None) -> dict:
        """Retorna a trilha atual e o progresso do mentorado (por pessoa, não por organização)."""
        user = require_verified_user()
        return call_route(
            course_routes.get_current_course,
            user=user,
            db=get_db(),
            course_slug=course_slug,
        )

    # ── Maturidade ───────────────────────────────────────────────────────────

    @mcp.tool
    def maturity_model() -> dict:
        """Modelo completo (inclui SWOT/TOWS). Para entrevistar o mentorado use maturity_questionnaire."""
        user = _maturity_user()
        return call_route(maturity_routes.get_model, user=user, db=get_db())

    @mcp.tool
    def maturity_my_responses() -> dict:
        """Lista as autoavaliações da organização ativa (rascunhos e privados, só os do autor)."""
        user = _maturity_user()
        return call_route(
            maturity_routes.list_my_responses, user=user, org_id=_org_id(user), db=get_db()
        )

    @mcp.tool
    def maturity_get(response_id: str) -> dict:
        """Retorna uma autoavaliação de maturidade (respostas, tier, resultado)."""
        user = _maturity_user()
        return call_route(
            maturity_routes.get_my_response_by_id,
            response_id=response_id,
            user=user,
            org_id=_org_id(user),
            db=get_db(),
        )

    @mcp.tool
    def maturity_export(response_id: str) -> dict:
        """Autoavaliação de maturidade em JSON: respostas junto do texto de cada pergunta."""
        user = _maturity_user()
        return call_route(
            maturity_routes.export_my_response,
            response_id=response_id,
            user=user,
            org_id=_org_id(user),
            db=get_db(),
        )

    def _maturity_load_draft(user: dict, response_id: str | None, tier: str) -> tuple[str | None, dict[str, int], str, dict]:
        user, org_id = _with_org(user)
        db = get_db()

        def _answers_of(doc: dict) -> dict[str, int]:
            out: dict[str, int] = {}
            for k, v in (doc.get("answers") or {}).items():
                try:
                    out[str(k)] = int(v)
                except (TypeError, ValueError):
                    continue
            return out

        if response_id:
            doc = call_route(
                maturity_routes.get_my_response_by_id,
                response_id=response_id,
                user=user,
                org_id=org_id,
                db=db,
            )
            return str(doc["id"]), _answers_of(doc), str(doc.get("tier") or tier), doc
        listed = call_route(
            maturity_routes.list_my_responses, user=user, org_id=org_id, db=db
        )
        draft = next((item for item in listed.get("items") or [] if not item.get("complete")), None)
        if not draft:
            return None, {}, tier, {"id": None, "complete": False, "result": None, "tier": tier}
        doc = call_route(
            maturity_routes.get_my_response_by_id,
            response_id=str(draft["id"]),
            user=user,
            org_id=org_id,
            db=db,
        )
        return str(doc["id"]), _answers_of(doc), str(doc.get("tier") or tier), doc

    def _maturity_pack(model: dict, tier: str, answers: dict[str, int], saved: dict, *, include_questions: bool) -> dict:
        questions = _maturity_questions(model, tier)
        unanswered = [q for q in questions if q["id"] not in answers]
        levels = (model.get("levels") or {}).get(tier) or {}
        pack = {
            "id": saved.get("id"),
            "title": model.get("assessment_title") or model.get("title") or "Diagnóstico de Maturidade em IA",
            "tier": tier,
            "tier_label": levels.get("label") or tier,
            "complete": bool(saved.get("complete")),
            "answered": len(questions) - len(unanswered),
            "total": len(questions),
            "answers": answers,
            "result": saved.get("result"),
            "next": unanswered[:3],
            "unanswered_ids": [q["id"] for q in unanswered],
        }
        if include_questions:
            annotated = []
            for q in questions:
                annotated.append({**q, "answer": answers.get(q["id"])})
            pack["questions"] = annotated
        return pack

    @mcp.tool
    def maturity_questionnaire(tier: str | None = None, response_id: str | None = None) -> dict:
        """Questionário enxuto para responder via chat: perguntas, escalas 1–5 e progresso.

        tier: basico (12), completo (32) ou complementar (48). Omitido: usa o do rascunho, senão basico.
        Sem response_id, continua o rascunho incompleto do autor se existir.
        """
        user = _maturity_user()
        model = call_route(maturity_routes.get_model, user=user, db=get_db())
        requested = (tier or "").strip().lower() or None
        if requested and requested not in ("basico", "completo", "complementar"):
            raise ToolError("Tier invalido. Use basico, completo ou complementar.")
        _rid, answers, draft_tier, saved = _maturity_load_draft(
            user, response_id, requested or "basico"
        )
        selected = maturity_routes._normalize_tier(requested or draft_tier or "basico")
        return _maturity_pack(model, selected, answers, saved, include_questions=True)

    @mcp.tool
    def maturity_answer(
        answers: dict[str, Any] | str | None = None,
        question_id: str | None = None,
        score: int | None = None,
        response_id: str | None = None,
        tier: str | None = None,
    ) -> dict:
        """Registra respostas do diagnóstico (merge — não apaga as já dadas).

        Use question_id + score (1–5) para uma pergunta, ou answers {EV1: 4, EV2: 3, …} em lote.
        Sem response_id, continua o rascunho do autor ou cria um novo.
        Devolve progresso e as próximas perguntas em `next`. Quando complete=true, pode chamar swot_from_maturity.
        """
        user = _maturity_user()
        model = call_route(maturity_routes.get_model, user=user, db=get_db())
        requested = (tier or "").strip().lower() or None
        if requested and requested not in ("basico", "completo", "complementar"):
            raise ToolError("Tier invalido. Use basico, completo ou complementar.")
        rid, existing, draft_tier, _saved = _maturity_load_draft(
            user, response_id, requested or "basico"
        )
        selected = maturity_routes._normalize_tier(requested or draft_tier or "basico")
        known = {q["id"] for q in _maturity_questions(model, selected)}
        incoming: dict[str, Any] = {}
        if answers is not None:
            incoming.update(
                parse_json_object(answers, label="answers") if not isinstance(answers, dict) else answers
            )
        if question_id:
            if score is None:
                raise ToolError("Informe score (1–5) junto com question_id.")
            incoming[question_id] = score
        patch = _coerce_maturity_answers(incoming, known=known)
        merged = {**existing, **patch}
        payload: dict[str, Any] = {"answers": merged, "tier": selected}
        if rid:
            payload["response_id"] = rid
        body = validate_model(MaturityAnswersRequest, payload)
        saved = call_route(
            maturity_routes.save_my_response,
            payload=body,
            user=user,
            org_id=_org_id(user),
            db=get_db(),
        )
        final_answers = {str(k): int(v) for k, v in (saved.get("answers") or merged).items()}
        return _maturity_pack(model, str(saved.get("tier") or selected), final_answers, saved, include_questions=False)

    @mcp.tool
    def maturity_save(
        answers: dict[str, Any] | str,
        tier: str = "basico",
        response_id: str | None = None,
    ) -> dict:
        """Substitui o mapa inteiro de respostas. Para responder no chat, prefira maturity_answer."""
        user = _maturity_user()
        raw_answers = parse_json_object(answers, label="answers") if not isinstance(answers, dict) else answers
        payload = {"answers": raw_answers, "tier": tier}
        if response_id:
            payload["response_id"] = response_id
        body = validate_model(MaturityAnswersRequest, payload)
        return call_route(
            maturity_routes.save_my_response,
            payload=body,
            user=user,
            org_id=_org_id(user),
            db=get_db(),
        )

    @mcp.tool
    def maturity_set_visibility(response_id: str, visibility: str) -> dict:
        """Define se a autoavaliação é compartilhada com a org (`shared`) ou só do autor (`private`)."""
        user = _maturity_user()
        body = validate_model(MaturityVisibilityRequest, {"visibility": visibility})
        return call_route(
            maturity_routes.patch_my_response_visibility,
            response_id=response_id,
            body=body,
            user=user,
            org_id=_org_id(user),
            db=get_db(),
        )

    # ── Mapa estratégico ─────────────────────────────────────────────────────

    @mcp.tool
    def strategic_map(
        maturity_response_id: str | None = None,
        swot_id: str | None = None,
    ) -> dict:
        """Mapa Estratégico: árvore maturidade → itens SWOT → estratégias TOWS → projetos."""
        user = _map_user()
        return call_route(
            strategic_map_routes.get_strategic_map,
            maturity_response_id=maturity_response_id,
            swot_id=swot_id,
            user=user,
            org_id=_org_id(user),
            db=get_db(),
        )

    # ── OKR ──────────────────────────────────────────────────────────────────

    @mcp.tool
    def okr_list() -> dict:
        """Lista os ciclos OKR da organização ativa (privados de outros membros ficam ocultos)."""
        user = _okr_user()
        return call_route(okr_routes.list_cycles, user=user, org_id=_org_id(user), db=get_db())

    @mcp.tool
    def okr_active() -> dict:
        """Retorna o ciclo OKR ativo (só objectives/KRs publicados). 404 se nenhum estiver ativo."""
        user = _okr_user()
        return call_route(okr_routes.get_active_cycle, user=user, org_id=_org_id(user), db=get_db())

    @mcp.tool
    def okr_get(cycle_id: str) -> dict:
        """Retorna um ciclo OKR pelo id (inclui rascunhos de objectives)."""
        user = _okr_user()
        return call_route(
            okr_routes.get_cycle,
            cycle_id=cycle_id,
            user=user,
            org_id=_org_id(user),
            db=get_db(),
        )

    def _okr_load(user: dict, cycle_id: str | None) -> tuple[str, dict]:
        user, org_id = _with_org(user)
        db = get_db()
        if cycle_id:
            cycle = call_route(
                okr_routes.get_cycle, cycle_id=cycle_id, user=user, org_id=org_id, db=db
            )
            return cycle_id, cycle
        cycle = call_route(okr_routes.get_active_cycle, user=user, org_id=org_id, db=db)
        return str(cycle["id"]), cycle

    def _okr_put_objectives(user: dict, cycle_id: str, objectives: list[dict]) -> dict:
        user, org_id = _with_org(user)
        body = validate_model(OkrCycleUpdateRequest, {"objectives": objectives})
        return call_route(
            okr_routes.update_cycle,
            cycle_id=cycle_id,
            body=body,
            user=user,
            org_id=org_id,
            db=get_db(),
        )

    @mcp.tool
    def okr_create(
        ano: int,
        tipo: str = "trimestre",
        trimestre: int | None = None,
        nome: str | None = None,
        objectives: list[dict[str, Any]] | str | None = None,
    ) -> dict:
        """Cria um ciclo OKR em planejamento. Opcional: já incluir objectives (com key_results).

        Cada objective: titulo, descricao?, dono?, pilar?, swot_id?, swot_item_ids?, tows_ids?,
        key_results? (titulo, unidade?, baseline?, current?, target?, direction?, dono?).
        """
        user = _okr_user()
        payload: dict[str, Any] = {"ano": ano, "tipo": tipo}
        if trimestre is not None:
            payload["trimestre"] = trimestre
        if nome is not None:
            payload["nome"] = nome
        body = validate_model(OkrCycleCreateRequest, payload)
        created = call_route(
            okr_routes.create_cycle, body=body, user=user, org_id=_org_id(user), db=get_db()
        )
        if objectives is None:
            return created
        raw = parse_json_list(objectives, label="objectives")
        return _okr_put_objectives(user, str(created["id"]), raw)

    @mcp.tool
    def okr_update(cycle_id: str, fields: dict[str, Any] | str) -> dict:
        """Atualiza metadados do ciclo. Se enviar `objectives`, substitui a lista inteira.

        Para criar/editar um Objective ou KR sem apagar os outros, use okr_create_objective,
        okr_update_objective, okr_create_key_result ou okr_update_key_result.
        Campos de ciclo: nome, tipo, ano, trimestre, visibility (shared|private).
        Escopo: organização ativa.
        """
        user = _okr_user()
        raw = parse_json_object(fields, label="fields")
        body = validate_model(OkrCycleUpdateRequest, raw)
        return call_route(
            okr_routes.update_cycle,
            cycle_id=cycle_id,
            body=body,
            user=user,
            org_id=_org_id(user),
            db=get_db(),
        )

    @mcp.tool
    def okr_create_objective(
        objective: dict[str, Any] | str,
        cycle_id: str | None = None,
    ) -> dict:
        """Cria um Objective (e KRs opcionais) no ciclo. Sem cycle_id, usa o ciclo ativo."""
        user = _okr_user()
        cid, cycle = _okr_load(user, cycle_id)
        objectives = _cycle_objectives(cycle)
        if len(objectives) >= 20:
            raise ToolError("Limite de 20 objectives por ciclo.")
        objectives.append(parse_json_object(objective, label="objective"))
        return _okr_put_objectives(user, cid, objectives)

    @mcp.tool
    def okr_update_objective(
        objective_id: str,
        fields: dict[str, Any] | str,
        cycle_id: str | None = None,
    ) -> dict:
        """Atualiza um Objective existente (merge). Sem cycle_id, usa o ciclo ativo.

        Campos: titulo, descricao, dono, pilar, swot_id, swot_item_ids, tows_ids.
        Se enviar key_results, substitui só os KRs deste objective.
        """
        user = _okr_user()
        cid, cycle = _okr_load(user, cycle_id)
        objectives = _cycle_objectives(cycle)
        idx, current = _find_objective(objectives, objective_id)
        patch = parse_json_object(fields, label="fields")
        patch.pop("id", None)
        if "key_results" in patch:
            krs = patch["key_results"]
            if not isinstance(krs, list):
                raise ToolError("key_results deve ser um array.")
            current["key_results"] = [_strip_kr(kr) if isinstance(kr, dict) else kr for kr in krs]
            patch = {k: v for k, v in patch.items() if k != "key_results"}
        current.update({k: v for k, v in patch.items() if k in _OBJ_KEYS})
        objectives[idx] = current
        return _okr_put_objectives(user, cid, objectives)

    @mcp.tool
    def okr_create_key_result(
        objective_id: str,
        key_result: dict[str, Any] | str,
        cycle_id: str | None = None,
    ) -> dict:
        """Cria um Key Result em um Objective. Sem cycle_id, usa o ciclo ativo."""
        user = _okr_user()
        cid, cycle = _okr_load(user, cycle_id)
        objectives = _cycle_objectives(cycle)
        idx, obj = _find_objective(objectives, objective_id)
        krs = list(obj.get("key_results") or [])
        if len(krs) >= 20:
            raise ToolError("Limite de 20 key results por objective.")
        krs.append(parse_json_object(key_result, label="key_result"))
        obj["key_results"] = krs
        objectives[idx] = obj
        return _okr_put_objectives(user, cid, objectives)

    @mcp.tool
    def okr_update_key_result(
        objective_id: str,
        kr_id: str,
        fields: dict[str, Any] | str,
        cycle_id: str | None = None,
    ) -> dict:
        """Atualiza um Key Result (merge: current, target, titulo…). Sem cycle_id, usa o ciclo ativo."""
        user = _okr_user()
        cid, cycle = _okr_load(user, cycle_id)
        objectives = _cycle_objectives(cycle)
        obj_idx, obj = _find_objective(objectives, objective_id)
        krs = list(obj.get("key_results") or [])
        kr_idx, kr = _find_kr(krs, kr_id)
        patch = parse_json_object(fields, label="fields")
        patch.pop("id", None)
        kr.update({k: v for k, v in patch.items() if k in _KR_KEYS})
        krs[kr_idx] = kr
        obj["key_results"] = krs
        objectives[obj_idx] = obj
        return _okr_put_objectives(user, cid, objectives)

    @mcp.tool
    def okr_activate(cycle_id: str) -> dict:
        """Ativa este ciclo e encerra qualquer outro ciclo ativo da organização."""
        user = _okr_user()
        return call_route(
            okr_routes.activate_cycle,
            cycle_id=cycle_id,
            user=user,
            org_id=_org_id(user),
            db=get_db(),
        )

    @mcp.tool
    def okr_archive(cycle_id: str) -> dict:
        """Encerra (arquiva) um ciclo OKR."""
        user = _okr_user()
        return call_route(
            okr_routes.archive_cycle,
            cycle_id=cycle_id,
            user=user,
            org_id=_org_id(user),
            db=get_db(),
        )

    # ── Governança ───────────────────────────────────────────────────────────

    @mcp.tool
    def governance_org_members() -> dict:
        """Lista membros da organização (para RACI / aprovador do gate)."""
        user = _gov_user()
        return call_route(
            gov_routes.list_organization_members,
            user=user,
            org_id=_org_id(user),
            db=get_db(),
        )

    @mcp.tool
    def governance_list_systems() -> dict:
        """Lista os sistemas de IA do inventário da organização."""
        user = _gov_user()
        return call_route(gov_routes.list_systems, user=user, org_id=_org_id(user), db=get_db())

    @mcp.tool
    def governance_get_system(system_id: str) -> dict:
        """Retorna um sistema de IA do inventário."""
        user = _gov_user()
        return call_route(
            gov_routes.get_system,
            system_id=system_id,
            user=user,
            org_id=_org_id(user),
            db=get_db(),
        )

    @mcp.tool
    def governance_create_system(fields: dict[str, Any] | str) -> dict:
        """Registra um sistema de IA no inventário. Obrigatório: nome (2+ caracteres)."""
        user = _gov_user()
        raw = parse_json_object(fields, label="fields")
        body = validate_model(AiSystemCreateRequest, raw)
        return call_route(
            gov_routes.create_system, body=body, user=user, org_id=_org_id(user), db=get_db()
        )

    @mcp.tool
    def governance_update_system(system_id: str, fields: dict[str, Any] | str) -> dict:
        """Atualiza ficha de um sistema de IA (nome, finalidade, responsáveis, HITL, status, visibility). Escopo: organização ativa."""
        user = _gov_user()
        raw = parse_json_object(fields, label="fields")
        body = validate_model(AiSystemUpdateRequest, raw)
        return call_route(
            gov_routes.update_system,
            system_id=system_id,
            body=body,
            user=user,
            org_id=_org_id(user),
            db=get_db(),
        )

    @mcp.tool
    def governance_create_assessment(system_id: str, fields: dict[str, Any] | str) -> dict:
        """Publica avaliação de risco. fields.regua: dados, impacto_erro, autonomia, exposicao_juridica
        (baixo|medio|alto|critico). AIA obrigatória se o nível final for alto/crítico.
        """
        user = _gov_user()
        raw = parse_json_object(fields, label="fields")
        body = validate_model(RiskAssessmentCreateRequest, raw)
        return call_route(
            gov_routes.create_assessment,
            system_id=system_id,
            body=body,
            user=user,
            org_id=_org_id(user),
            db=get_db(),
        )

    @mcp.tool
    def governance_create_gate(system_id: str) -> dict:
        """Abre um gate go/no-go para o sistema (checklist + itens derivados da SWOT)."""
        user = _gov_user()
        return call_route(
            gov_routes.create_gate,
            system_id=system_id,
            user=user,
            org_id=_org_id(user),
            db=get_db(),
        )

    @mcp.tool
    def governance_get_gate(gate_id: str) -> dict:
        """Retorna um gate de governança (checklist e decisão)."""
        user = _gov_user()
        return call_route(
            gov_routes.get_gate,
            gate_id=gate_id,
            user=user,
            org_id=_org_id(user),
            db=get_db(),
        )

    @mcp.tool
    def governance_update_gate_item(
        gate_id: str,
        item_id: str,
        fields: dict[str, Any] | str,
    ) -> dict:
        """Atualiza um item do checklist do gate (status: aprovado|reprovado|nao_aplicavel|pendente, evidencia)."""
        user = _gov_user()
        raw = parse_json_object(fields, label="fields")
        body = validate_model(GateChecklistUpdateRequest, raw)
        return call_route(
            gov_routes.update_gate_item,
            gate_id=gate_id,
            item_id=item_id,
            body=body,
            user=user,
            org_id=_org_id(user),
            db=get_db(),
        )

    @mcp.tool
    def governance_decide_gate(gate_id: str, decisao: dict[str, Any] | str) -> dict:
        """Registra a decisão do gate. decisao: resultado (go|no_go|go_condicional),
        aprovador_user_id (admin da org), justificativa, condicoes[], consultados_user_ids[].
        """
        user = _gov_user()
        raw = parse_json_object(decisao, label="decisao")
        wrapped = raw if "decisao" in raw and isinstance(raw.get("decisao"), dict) else {"decisao": raw}
        body = validate_model(GateDecisionRequest, wrapped)
        return call_route(
            gov_routes.decide_gate,
            gate_id=gate_id,
            body=body,
            user=user,
            org_id=_org_id(user),
            db=get_db(),
        )
