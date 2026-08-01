"""Instância FastMCP AEGIS e ASGI HTTP app (OAuth Connectors + Streamable HTTP)."""

from __future__ import annotations

from fastmcp import FastMCP

from app.mcp.oauth_provider import AegisOAuthProvider, mcp_public_base
from app.mcp.prompts import register_prompts
from app.mcp.resources import register_resources
from app.mcp.tools_admin import register_admin_tools
from app.mcp.tools_learner import register_learner_tools

# Resetar singletons ao recarregar módulo (ex.: --reload muda MCP_PUBLIC_URL)
_mcp: FastMCP | None = None
_auth: AegisOAuthProvider | None = None
MCP_PATH = "/mcp"


def get_auth() -> AegisOAuthProvider:
    global _auth
    if _auth is None:
        _auth = AegisOAuthProvider()
    return _auth


def create_mcp() -> FastMCP:
    """Cria (ou reutiliza) o servidor MCP curado da plataforma."""
    global _mcp
    if _mcp is not None:
        return _mcp

    auth = get_auth()
    mcp = FastMCP(
        name="aegis",
        instructions=(
            "Servidor MCP da plataforma Valorian 4 Future (AEGIS). "
            "Conecte via Claude Connectors (OAuth: login Valorian no browser) "
            "ou Authorization: Bearer com JWT/OAuth token. "
            "Tools de mentorado exigem email verificado; tools admin_* exigem is_admin."
        ),
        auth=auth,
    )
    register_resources(mcp)
    register_prompts(mcp)
    register_learner_tools(mcp)
    register_admin_tools(mcp)
    _mcp = mcp
    return mcp


def mcp_http_app():
    """
    ASGI do MCP em path /mcp + rotas OAuth operacionais (/authorize, /token, …).
    Monte as rotas no FastAPI (ou Mount) e publique well-known no root.
    """
    mcp = create_mcp()
    return mcp.http_app(
        path=MCP_PATH,
        transport="streamable-http",
        stateless_http=True,
    )


def mcp_well_known_routes():
    """Discovery RFC 8414 / 9728 para o root do domínio."""
    return get_auth().get_well_known_routes(mcp_path=MCP_PATH)


def apply_mcp_auth_middleware(app):
    """
    Reaplica o middleware de auth do FastMCP.

    `mcp.http_app()` instala AuthenticationMiddleware (BearerAuthBackend) e
    AuthContextMiddleware no app Starlette do MCP. Como o main.py levanta apenas
    as *rotas* desse app para dentro do FastAPI, esse stack seria perdido — e o
    RequireAuthMiddleware que envolve /mcp lê `scope["user"]`, devolvendo 401
    "Authentication required" em toda requisição, mesmo com token válido.
    """
    for middleware in reversed(get_auth().get_middleware()):
        app = middleware.cls(app, *middleware.args, **middleware.kwargs)
    return app


def wrap_asgi_endpoint(app, name: str = "mcp_asgi"):
    """Dá __name__/__module__ ao ASGI app: o SlowAPI lê `route.endpoint.__name__`."""

    async def endpoint(scope, receive, send):
        await app(scope, receive, send)

    endpoint.__name__ = name
    endpoint.__module__ = "app.mcp"
    return endpoint


def install_mcp_routes(fastapi_app, mcp_asgi) -> None:
    """
    Insere as rotas do MCP/OAuth no FastAPI antes do fallback SPA.

    Para cada rota é preciso:
      1. reaplicar o middleware de auth (perdido ao levantar rotas soltas);
      2. dar __name__ ao ASGI e ajustar `route.app` E `route.endpoint` —
         o Starlette despacha por `route.app`, mas o SlowAPI inspeciona
         `route.endpoint.__name__` (sem isso: HTTP 500 em /mcp).
    """
    for route in reversed(list(mcp_asgi.routes)):
        asgi = getattr(route, "app", None)
        if asgi is not None:
            wrapped = wrap_asgi_endpoint(apply_mcp_auth_middleware(asgi), "mcp_http")
            route.app = wrapped  # type: ignore[attr-defined]
            route.endpoint = wrapped  # type: ignore[attr-defined]
        fastapi_app.router.routes.insert(0, route)


__all__ = [
    "MCP_PATH",
    "apply_mcp_auth_middleware",
    "create_mcp",
    "get_auth",
    "install_mcp_routes",
    "mcp_http_app",
    "mcp_public_base",
    "mcp_well_known_routes",
    "wrap_asgi_endpoint",
]
