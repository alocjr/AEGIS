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
from app.routes import canvas_projects as canvas_routes
from app.routes import course as course_routes
from app.routes import governance as gov_routes
from app.routes import maturity as maturity_routes
from app.routes import okrs as okr_routes
from app.routes import strategic_map as strategic_map_routes
from app.routes import swot_analysis as swot_routes
from app.schemas import (
    CanvasImportRequest,
    CanvasProjectCreateRequest,
    CanvasProjectUpdateRequest,
    MaturityAnswersRequest,
    OkrCycleCreateRequest,
    OkrCycleUpdateRequest,
    SwotAnalysisUpdateRequest,
    SwotImportRequest,
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


def _org_id(user: dict):
    """Organizacao do usuario MCP — mesma regra de `deps.get_current_organization_id`."""
    org_id = user.get("organization_id")
    if not org_id:
        raise ToolError("Usuario sem organizacao atribuida. Contate o suporte.")
    return org_id


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
        return user

    def _canvas_user() -> dict:
        user = require_verified_user()
        require_tool_access(user, TOOL_CANVAS)
        return user

    def _maturity_user() -> dict:
        user = require_verified_user()
        require_tool_access(user, TOOL_MATURITY)
        return user

    def _map_user() -> dict:
        user = require_verified_user()
        require_tool_access(user, TOOL_STRATEGIC_MAP)
        return user

    def _okr_user() -> dict:
        user = require_verified_user()
        require_tool_access(user, TOOL_OKR)
        return user

    def _gov_user() -> dict:
        user = require_verified_user()
        require_tool_access(user, TOOL_GOVERNANCE)
        return user

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
        """Lista as SWOTs da organização (resumo, com contagem de itens e estratégias TOWS)."""
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
        """Atualiza a SWOT (ótica, quadrantes, TOWS, veredito). Sem swot_id, usa a mais recente.

        Campos: optica, pilares, forcas, fraquezas, oportunidades, ameacas, watchlist,
        tows_fo, tows_fa, tows_fxo, tows_fxa, veredito_tipo, veredito_titulo, veredito_texto.
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
    def canvas_list() -> dict:
        """Lista os projetos (canvas) da organização."""
        user = _canvas_user()
        return call_route(canvas_routes.list_projects, user=user, org_id=_org_id(user), db=get_db())

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
        """Atualiza campos de um projeto/canvas existente."""
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

    # ── Curso ────────────────────────────────────────────────────────────────

    @mcp.tool
    def course_get(course_slug: str | None = None) -> dict:
        """Retorna a trilha atual e o progresso do mentorado."""
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
        """Lista as autoavaliações de maturidade da organização (rascunhos, só as do próprio autor)."""
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
        org_id = _org_id(user)
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
        """Lista os ciclos OKR da organização (resumo)."""
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
        org_id = _org_id(user)
        db = get_db()
        if cycle_id:
            cycle = call_route(
                okr_routes.get_cycle, cycle_id=cycle_id, user=user, org_id=org_id, db=db
            )
            return cycle_id, cycle
        cycle = call_route(okr_routes.get_active_cycle, user=user, org_id=org_id, db=db)
        return str(cycle["id"]), cycle

    def _okr_put_objectives(user: dict, cycle_id: str, objectives: list[dict]) -> dict:
        body = validate_model(OkrCycleUpdateRequest, {"objectives": objectives})
        return call_route(
            okr_routes.update_cycle,
            cycle_id=cycle_id,
            body=body,
            user=user,
            org_id=_org_id(user),
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
        Campos de ciclo: nome, tipo, ano, trimestre.
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
        """Atualiza ficha de um sistema de IA (nome, finalidade, responsáveis, HITL, status…)."""
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
