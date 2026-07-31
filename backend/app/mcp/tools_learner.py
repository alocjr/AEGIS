"""Tools MCP do mentorado (JWT verificado)."""

from __future__ import annotations

from typing import Any

from app.database import get_db
from app.mcp.auth import require_verified_user
from app.mcp.util import call_route, parse_json_object, validate_model
from app.routes import canvas_projects as canvas_routes
from app.routes import course as course_routes
from app.routes import maturity as maturity_routes
from app.routes import swot_analysis as swot_routes
from app.schemas import CanvasImportRequest, CanvasProjectUpdateRequest, SwotImportRequest


def register_learner_tools(mcp) -> None:
    @mcp.tool
    def swot_get() -> dict:
        """Retorna a SWOT de IA do mentorado autenticado (cria vazia se não existir)."""
        user = require_verified_user()
        return call_route(swot_routes.get_swot, user=user, db=get_db())

    @mcp.tool
    def swot_import(document: dict[str, Any] | str) -> dict:
        """Importa JSON aegis.swot-ia (v1–v3) e substitui a SWOT do mentorado."""
        user = require_verified_user()
        raw = parse_json_object(document)
        body = validate_model(SwotImportRequest, raw)
        return call_route(swot_routes.import_swot, body=body, user=user, db=get_db())

    @mcp.tool
    def canvas_list() -> dict:
        """Lista os projetos (canvas) do mentorado."""
        user = require_verified_user()
        return call_route(canvas_routes.list_projects, user=user, db=get_db())

    @mcp.tool
    def canvas_get(project_id: str) -> dict:
        """Retorna um projeto/canvas pelo id."""
        user = require_verified_user()
        return call_route(
            canvas_routes.get_project,
            project_id=project_id,
            user=user,
            db=get_db(),
        )

    @mcp.tool
    def canvas_import(document: dict[str, Any] | str) -> dict:
        """Importa aegis.canvas-oportunidades e cria um projeto por oportunidade."""
        user = require_verified_user()
        raw = parse_json_object(document)
        body = validate_model(CanvasImportRequest, raw)
        return call_route(canvas_routes.import_projects, body=body, user=user, db=get_db())

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
        """Lista as autoavaliações de maturidade do mentorado."""
        user = require_verified_user()
        return call_route(maturity_routes.list_my_responses, user=user, db=get_db())
