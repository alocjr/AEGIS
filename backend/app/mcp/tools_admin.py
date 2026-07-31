"""Tools MCP de administrador (JWT + is_admin)."""

from __future__ import annotations

from app.database import get_db
from app.mcp.auth import require_admin
from app.mcp.util import call_route, validate_model
from app.routes import admin as admin_routes
from app.schemas import LiberarEncontroRequest


def register_admin_tools(mcp) -> None:
    @mcp.tool
    def admin_dashboard() -> list:
        """Lista alunos com métricas de progresso (apenas admin)."""
        admin = require_admin()
        return call_route(admin_routes.get_dashboard, admin=admin, db=get_db())

    @mcp.tool
    def admin_list_users() -> list:
        """Lista usuários (resumo) — apenas admin."""
        admin = require_admin()
        return call_route(admin_routes.list_users, admin=admin, db=get_db())

    @mcp.tool
    def admin_user_progress(user_id: str, course_slug: str | None = None) -> dict:
        """Retorna curso e progresso de um aluno — apenas admin."""
        admin = require_admin()
        return call_route(
            admin_routes.get_user_course_and_progress,
            user_id=user_id,
            admin=admin,
            db=get_db(),
            course_slug=course_slug,
        )

    @mcp.tool
    def admin_liberar_encontro(user_id: str, encontro_id: int) -> dict:
        """Libera um encontro para o aluno — apenas admin."""
        admin = require_admin()
        body = validate_model(LiberarEncontroRequest, {"encontro_id": encontro_id})
        return call_route(
            admin_routes.liberar_encontro,
            user_id=user_id,
            body=body,
            admin=admin,
            db=get_db(),
        )
