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
from app.mcp.util import call_route, parse_json_object, validate_model
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
        """Retorna o modelo de questionário de maturidade em IA."""
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

    @mcp.tool
    def maturity_save(
        answers: dict[str, Any] | str,
        tier: str = "basico",
        response_id: str | None = None,
    ) -> dict:
        """Cria ou atualiza uma autoavaliação. answers: mapa pergunta_id → nota 1–5.

        Sem response_id, reutiliza o rascunho incompleto do autor ou cria um novo.
        Completa automaticamente quando todas as perguntas do tier estão respondidas.
        """
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

    @mcp.tool
    def okr_create(
        ano: int,
        tipo: str = "trimestre",
        trimestre: int | None = None,
        nome: str | None = None,
    ) -> dict:
        """Cria um ciclo OKR vazio em planejamento (não altera o ciclo ativo)."""
        user = _okr_user()
        payload: dict[str, Any] = {"ano": ano, "tipo": tipo}
        if trimestre is not None:
            payload["trimestre"] = trimestre
        if nome is not None:
            payload["nome"] = nome
        body = validate_model(OkrCycleCreateRequest, payload)
        return call_route(
            okr_routes.create_cycle, body=body, user=user, org_id=_org_id(user), db=get_db()
        )

    @mcp.tool
    def okr_update(cycle_id: str, fields: dict[str, Any] | str) -> dict:
        """Atualiza um ciclo OKR. Informe objectives para substituir a lista (full-replace).

        Campos: nome, tipo, ano, trimestre, objectives (cada um com titulo, descricao, dono,
        pilar, swot_id, swot_item_ids, tows_ids, key_results).
        Status só muda via okr_activate / okr_archive.
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
