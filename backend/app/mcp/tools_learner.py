"""Tools MCP do mentorado (JWT verificado)."""

from __future__ import annotations

from typing import Any

from app.database import get_db
from app.mcp.auth import require_verified_user
from app.mcp.util import call_route, parse_json_object, validate_model
from app.routes import canvas_projects as canvas_routes
from app.routes import course as course_routes
from app.routes import maturity as maturity_routes
from app.routes import strategic_map as strategic_map_routes
from app.routes import swot_analysis as swot_routes
from app.schemas import CanvasImportRequest, CanvasProjectUpdateRequest, SwotImportRequest

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
    @mcp.tool
    def swot_get() -> dict:
        """Retorna a SWOT de IA da organização do mentorado (cria vazia se não existir)."""
        user = require_verified_user()
        return call_route(swot_routes.get_swot, user=user, org_id=_org_id(user), db=get_db())

    @mcp.tool
    def swot_list() -> dict:
        """Lista as SWOTs da organização (resumo, com contagem de itens e estratégias TOWS)."""
        user = require_verified_user()
        return call_route(swot_routes.list_swots, user=user, org_id=_org_id(user), db=get_db())

    @mcp.tool
    def swot_import(document: dict[str, Any] | str) -> dict:
        """Importa JSON aegis.swot-ia (v1–v3) e substitui a SWOT da organização."""
        user = require_verified_user()
        raw = parse_json_object(document)
        body = validate_model(SwotImportRequest, raw)
        return call_route(
            swot_routes.import_swot, body=body, user=user, org_id=_org_id(user), db=get_db()
        )

    @mcp.tool
    def canvas_list() -> dict:
        """Lista os projetos (canvas) da organização."""
        user = require_verified_user()
        return call_route(canvas_routes.list_projects, user=user, org_id=_org_id(user), db=get_db())

    @mcp.tool
    def canvas_get(project_id: str) -> dict:
        """Retorna um projeto/canvas pelo id."""
        user = require_verified_user()
        return call_route(
            canvas_routes.get_project,
            project_id=project_id,
            user=user,
            org_id=_org_id(user),
            db=get_db(),
        )

    @mcp.tool
    def canvas_import(document: dict[str, Any] | str) -> dict:
        """Importa aegis.canvas-oportunidades e cria um projeto por oportunidade."""
        user = require_verified_user()
        raw = parse_json_object(document)
        body = validate_model(CanvasImportRequest, raw)
        return call_route(
            canvas_routes.import_projects, body=body, user=user, org_id=_org_id(user), db=get_db()
        )

    @mcp.tool
    def canvas_import_into(project_id: str, document: dict[str, Any] | str) -> dict:
        """Importa o JSON no projeto aberto (aplica a 1ª oportunidade)."""
        user = require_verified_user()
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
        user = require_verified_user()
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
    def course_get(course_slug: str | None = None) -> dict:
        """Retorna a trilha atual e o progresso do mentorado."""
        user = require_verified_user()
        return call_route(
            course_routes.get_current_course,
            user=user,
            db=get_db(),
            course_slug=course_slug,
        )

    @mcp.tool
    def maturity_model() -> dict:
        """Retorna o modelo de questionário de maturidade em IA."""
        user = require_verified_user()
        return call_route(maturity_routes.get_model, user=user, db=get_db())

    @mcp.tool
    def maturity_my_responses() -> dict:
        """Lista as autoavaliações de maturidade da organização (rascunhos, só as do próprio autor)."""
        user = require_verified_user()
        return call_route(
            maturity_routes.list_my_responses, user=user, org_id=_org_id(user), db=get_db()
        )

    @mcp.tool
    def maturity_export(response_id: str) -> dict:
        """Autoavaliação de maturidade em JSON: respostas junto do texto de cada pergunta."""
        user = require_verified_user()
        return call_route(
            maturity_routes.export_my_response,
            response_id=response_id,
            user=user,
            org_id=_org_id(user),
            db=get_db(),
        )

    @mcp.tool
    def strategic_map(
        maturity_response_id: str | None = None,
        swot_id: str | None = None,
    ) -> dict:
        """Mapa Estratégico: árvore maturidade → itens SWOT → estratégias TOWS → projetos."""
        user = require_verified_user()
        return call_route(
            strategic_map_routes.get_strategic_map,
            maturity_response_id=maturity_response_id,
            swot_id=swot_id,
            user=user,
            org_id=_org_id(user),
            db=get_db(),
        )
