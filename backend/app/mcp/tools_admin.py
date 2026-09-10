"""Tools MCP de administrador (JWT + is_admin)."""

from __future__ import annotations

from app.database import get_db
from app.mcp.auth import require_admin
from app.mcp.util import call_route, validate_model
from app.routes import admin as admin_routes
from app.schemas import AdminUpdateUserRequest, LiberarEncontroRequest


def register_admin_tools(mcp) -> None:
    @mcp.tool
    def admin_dashboard() -> list:
        """Lista alunos com métricas de progresso (apenas admin)."""
        admin = require_admin()
        return call_route(admin_routes.get_dashboard, admin=admin, db=get_db())

    @mcp.tool
    def admin_list_users() -> list:
        """Lista usuários (resumo, com organizations[]) — apenas admin."""
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

    @mcp.tool
    def admin_list_organizations() -> list:
        """Lista organizações da plataforma (id, nome, member_count) — apenas admin."""
        admin = require_admin()
        return call_route(admin_routes.list_organizations, admin=admin, db=get_db())

    @mcp.tool
    def admin_set_user_organizations(
        user_id: str,
        organization_ids: list[str],
        org_admin_ids: list[str] | None = None,
        organization_id: str | None = None,
    ) -> dict:
        """Define as organizações de um usuário. Precisa de pelo menos uma.

        organization_ids: memberships. org_admin_ids: orgs em que é admin de organização
        (subconjunto). organization_id: org ativa (opcional; senão permanece a atual se
        ainda for membro, ou a primeira da lista).
        """
        admin = require_admin()
        payload: dict = {"organization_ids": organization_ids}
        if org_admin_ids is not None:
            payload["org_admin_ids"] = org_admin_ids
        if organization_id:
            payload["organization_id"] = organization_id
        body = validate_model(AdminUpdateUserRequest, payload)
        return call_route(
            admin_routes.update_user,
            user_id=user_id,
            payload=body,
            admin=admin,
            db=get_db(),
        )
