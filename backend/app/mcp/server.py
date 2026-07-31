"""Instância FastMCP AEGIS e ASGI HTTP app (OAuth Connectors + Streamable HTTP)."""

from __future__ import annotations

from fastmcp import FastMCP

from app.mcp.oauth_provider import AegisOAuthProvider, mcp_public_base
from app.mcp.prompts import register_prompts
from app.mcp.resources import register_resources
from app.mcp.tools_admin import register_admin_tools
from app.mcp.tools_learner import register_learner_tools

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


def wrap_asgi_endpoint(app, name: str = "mcp_asgi"):
    """Dá __name__ ao ASGI app para o SlowAPI não quebrar."""

    async def endpoint(scope, receive, send):
        await app(scope, receive, send)

    endpoint.__name__ = name
    endpoint.__module__ = "app.mcp"
    return endpoint


__all__ = [
    "MCP_PATH",
    "create_mcp",
    "get_auth",
    "mcp_http_app",
    "mcp_public_base",
    "mcp_well_known_routes",
    "wrap_asgi_endpoint",
]
