"""Servidor MCP remoto AEGIS (Claude / clientes HTTPS + OAuth Connectors)."""

from app.mcp.server import (
    MCP_PATH,
    apply_mcp_auth_middleware,
    create_mcp,
    get_auth,
    install_mcp_routes,
    mcp_http_app,
    mcp_public_base,
    mcp_well_known_routes,
    wrap_asgi_endpoint,
)

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
