"""Autenticação para tools MCP: OAuth Connectors (subject) ou JWT Bearer legado."""

from __future__ import annotations

from bson import ObjectId
from fastapi import HTTPException
from jose import JWTError, jwt

from app.config import settings
from app.database import get_db
from app.deps import is_email_verified
from app.security import _jwt_key_bytes

try:
    from fastmcp.exceptions import ToolError
except ImportError:  # pragma: no cover
    class ToolError(Exception):
        pass

try:
    from fastmcp.server.dependencies import get_access_token, get_http_headers
except ImportError:  # pragma: no cover
    def get_http_headers(include_all: bool = False) -> dict[str, str]:
        return {}

    def get_access_token():
        return None


def _user_by_id(user_id: str) -> dict:
    if not user_id or not ObjectId.is_valid(user_id):
        raise ToolError("Token invalido.")
    user = get_db().users.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise ToolError("Usuario nao encontrado.")
    return {k: v for k, v in user.items() if k != "password_hash"}


def _bearer_token() -> str | None:
    headers = get_http_headers()
    auth = headers.get("authorization") or headers.get("Authorization") or ""
    if not auth.lower().startswith("bearer "):
        return None
    token = auth.split(" ", 1)[1].strip()
    return token or None


def resolve_user() -> dict:
    """Resolve o usuário: AccessToken OAuth (subject) ou JWT de /api/auth/login."""
    access = get_access_token()
    if access is not None and getattr(access, "subject", None):
        return _user_by_id(str(access.subject))

    token = _bearer_token()
    if not token:
        raise ToolError(
            "Nao autenticado. Conecte pelo Claude Connectors (OAuth) "
            "ou envie Authorization: Bearer <token>."
        )

    # Token OAuth opaco (já validado pelo middleware) sem subject no contexto
    try:
        from app.mcp.oauth_store import get_access_token_doc

        doc = get_access_token_doc(token)
        if doc and doc.get("subject"):
            return _user_by_id(str(doc["subject"]))
    except Exception:
        pass

    try:
        payload = jwt.decode(
            token,
            _jwt_key_bytes(),
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError as exc:
        raise ToolError("Token invalido ou expirado.") from exc

    return _user_by_id(str(payload.get("sub") or ""))


def require_verified_user() -> dict:
    user = resolve_user()
    if not is_email_verified(user):
        raise ToolError("Confirme seu email antes de acessar este recurso.")
    return user


def require_admin() -> dict:
    user = require_verified_user()
    if not user.get("is_admin"):
        raise ToolError("Acesso restrito a administradores.")
    return {**user, "is_admin": True}


def raise_http_as_tool(exc: HTTPException) -> None:
    detail = exc.detail
    if isinstance(detail, (list, dict)):
        detail = str(detail)
    raise ToolError(detail or f"HTTP {exc.status_code}") from exc
