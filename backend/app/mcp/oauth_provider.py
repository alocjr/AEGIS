"""OAuth 2.1 Authorization Server AEGIS para Claude Connectors (DCR + login Valorian)."""

from __future__ import annotations

import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode

from mcp.server.auth.provider import (
    AccessToken,
    AuthorizationCode,
    AuthorizationParams,
    RefreshToken,
)
from mcp.server.auth.routes import cors_middleware
from mcp.server.auth.settings import ClientRegistrationOptions, RevocationOptions
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken
from pydantic import AnyHttpUrl
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from fastmcp.server.auth import OAuthProvider

from app.config import settings
from app.database import get_db
from app.deps import is_email_verified
from app.mcp import oauth_store as store
from app.security import _jwt_key_bytes
from jose import JWTError, jwt

CODE_TTL_SECONDS = 600
ACCESS_TTL_SECONDS = 3600
REFRESH_TTL_SECONDS = 60 * 60 * 24 * 30
PENDING_TTL_SECONDS = 600
DEFAULT_SCOPES = ["mcp"]


def mcp_public_base() -> str:
    """
    URL pública onde Claude alcança /mcp e OAuth.
    Prefer MCP_PUBLIC_URL; se for localhost e APP_BASE_URL for https, use o APP
    (caso típico: .env de produção sem MCP_PUBLIC_URL).
    """
    mcp = (settings.mcp_public_url or "").strip().rstrip("/")
    app = (settings.app_base_url or "").strip().rstrip("/")
    local = ("http://127.0.0.1", "http://localhost")
    if mcp and not mcp.startswith(local):
        return mcp
    if app.startswith("https://"):
        return app
    return mcp or app or "http://127.0.0.1:8000"


def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _client_from_doc(doc: dict[str, Any]) -> OAuthClientInformationFull:
    data = {k: v for k, v in doc.items() if k not in ("_id", "updated_at", "created_at")}
    return OAuthClientInformationFull.model_validate(data)


class AegisOAuthProvider(OAuthProvider):
    """AS OAuth próprio: DCR para Claude + login email/senha Valorian."""

    def __init__(self) -> None:
        base = mcp_public_base()
        super().__init__(
            base_url=base,
            issuer_url=base,
            service_documentation_url=f"{base}/conectar-claude",
            client_registration_options=ClientRegistrationOptions(
                enabled=True,
                valid_scopes=DEFAULT_SCOPES + ["admin"],
                default_scopes=DEFAULT_SCOPES,
            ),
            revocation_options=RevocationOptions(enabled=True),
            required_scopes=DEFAULT_SCOPES,
        )

    def get_routes(self, mcp_path: str | None = None) -> list[Route]:
        """Ajustes exigidos pelo Claude Connectors (PRM raiz + auth method none + OIDC alias)."""
        routes = super().get_routes(mcp_path)
        base = mcp_public_base()
        resource = f"{base}/mcp"
        prm_body = {
            "resource": resource,
            "authorization_servers": [f"{base}/"],
            "scopes_supported": DEFAULT_SCOPES + ["admin"],
            "bearer_methods_supported": ["header"],
        }

        # Claude consulta /.well-known/oauth-protected-resource (sem /mcp) — sem isso cai no SPA HTML.
        async def prm_root(_request: Request) -> JSONResponse:
            return JSONResponse(prm_body, headers={"Cache-Control": "public, max-age=3600"})

        routes.insert(
            0,
            Route(
                "/.well-known/oauth-protected-resource",
                endpoint=cors_middleware(prm_root, ["GET", "OPTIONS"]),
                methods=["GET", "OPTIONS"],
            ),
        )

        # Patch metadata AS: incluir "none" (cliente público + PKCE) e alias OIDC Discovery.
        # Não mutar route.endpoint — o Starlette usa route.app criado no __init__.
        as_endpoint = cors_middleware(self._as_metadata_endpoint, ["GET", "OPTIONS"])
        for i, route in enumerate(list(routes)):
            if not isinstance(route, Route):
                continue
            if route.path == "/.well-known/oauth-authorization-server":
                methods = list(route.methods or ["GET", "OPTIONS"])
                routes[i] = Route(
                    "/.well-known/oauth-authorization-server",
                    endpoint=as_endpoint,
                    methods=methods,
                )
                routes.append(
                    Route(
                        "/.well-known/openid-configuration",
                        endpoint=as_endpoint,
                        methods=methods,
                    )
                )
                break

        return routes

    async def _as_metadata_endpoint(self, request: Request) -> JSONResponse:
        """Metadata AS com token_endpoint_auth_methods_supported incluindo none (PKCE público)."""
        from mcp.server.auth.routes import build_metadata

        assert self.base_url is not None
        metadata = build_metadata(
            self.base_url,
            self.service_documentation_url,
            self.client_registration_options or ClientRegistrationOptions(),
            self.revocation_options or RevocationOptions(),
        )
        methods = list(metadata.token_endpoint_auth_methods_supported or [])
        if "none" not in methods:
            methods.append("none")
        metadata.token_endpoint_auth_methods_supported = methods
        return JSONResponse(
            metadata.model_dump(mode="json", exclude_none=True),
            headers={"Cache-Control": "public, max-age=3600"},
        )

    async def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        doc = store.get_client(client_id)
        if not doc:
            return None
        return _client_from_doc(doc)

    async def register_client(self, client_info: OAuthClientInformationFull) -> None:
        payload = client_info.model_dump(mode="json")
        payload["created_at"] = datetime.now(timezone.utc)
        store.save_client(payload)

    async def authorize(
        self, client: OAuthClientInformationFull, params: AuthorizationParams
    ) -> str:
        sid = secrets.token_urlsafe(24)
        expires = datetime.now(timezone.utc) + timedelta(seconds=PENDING_TTL_SECONDS)
        store.save_pending(
            sid,
            {
                "client_id": client.client_id,
                "redirect_uri": str(params.redirect_uri),
                "redirect_uri_provided_explicitly": params.redirect_uri_provided_explicitly,
                "code_challenge": params.code_challenge,
                "state": params.state,
                "scopes": list(params.scopes or DEFAULT_SCOPES),
                "resource": str(params.resource) if params.resource else None,
            },
            expires_at=expires,
        )
        return f"{mcp_public_base()}/mcp-oauth/login?{urlencode({'sid': sid})}"

    async def load_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: str
    ) -> AuthorizationCode | None:
        doc = store.get_code(authorization_code)
        if not doc or doc.get("client_id") != client.client_id:
            return None
        exp = _aware(doc.get("expires_at"))
        if exp and exp.timestamp() < time.time():
            store.delete_code(authorization_code)
            return None
        return AuthorizationCode(
            code=doc["code"],
            client_id=doc["client_id"],
            scopes=doc.get("scopes") or DEFAULT_SCOPES,
            expires_at=exp.timestamp() if exp else time.time() + CODE_TTL_SECONDS,
            redirect_uri=AnyHttpUrl(doc["redirect_uri"]),
            redirect_uri_provided_explicitly=bool(
                doc.get("redirect_uri_provided_explicitly", True)
            ),
            code_challenge=doc["code_challenge"],
            resource=doc.get("resource"),
            subject=doc.get("subject"),
        )

    async def exchange_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: AuthorizationCode
    ) -> OAuthToken:
        store.delete_code(authorization_code.code)
        return self._issue_tokens(
            client_id=client.client_id,
            scopes=list(authorization_code.scopes or DEFAULT_SCOPES),
            subject=authorization_code.subject or "",
            resource=authorization_code.resource,
        )

    async def load_refresh_token(
        self, client: OAuthClientInformationFull, refresh_token: str
    ) -> RefreshToken | None:
        doc = store.get_refresh_token_doc(refresh_token)
        if not doc or doc.get("client_id") != client.client_id:
            return None
        exp = _aware(doc.get("expires_at"))
        if exp and exp.timestamp() < time.time():
            return None
        return RefreshToken(
            token=doc["token"],
            client_id=doc["client_id"],
            scopes=doc.get("scopes") or DEFAULT_SCOPES,
            expires_at=exp.timestamp() if exp else None,
            subject=doc.get("subject"),
        )

    async def exchange_refresh_token(
        self,
        client: OAuthClientInformationFull,
        refresh_token: RefreshToken,
        scopes: list[str],
    ) -> OAuthToken:
        store.revoke_token_string(refresh_token.token)
        use_scopes = scopes or list(refresh_token.scopes or DEFAULT_SCOPES)
        return self._issue_tokens(
            client_id=client.client_id,
            scopes=use_scopes,
            subject=refresh_token.subject or "",
            resource=None,
        )

    async def load_access_token(self, token: str) -> AccessToken | None:
        doc = store.get_access_token_doc(token)
        if doc:
            exp = _aware(doc.get("expires_at"))
            if exp and exp.timestamp() < time.time():
                return None
            return AccessToken(
                token=doc["token"],
                client_id=doc.get("client_id") or "aegis",
                scopes=doc.get("scopes") or DEFAULT_SCOPES,
                expires_at=exp.timestamp() if exp else None,
                resource=doc.get("resource"),
                subject=doc.get("subject"),
                claims=doc.get("claims") or {},
            )
        # Compat: JWT legado da API (POST /api/auth/login)
        try:
            payload = jwt.decode(
                token,
                _jwt_key_bytes(),
                algorithms=[settings.jwt_algorithm],
            )
        except JWTError:
            return None
        sub = payload.get("sub")
        if not sub:
            return None
        return AccessToken(
            token=token,
            client_id="aegis-jwt",
            scopes=DEFAULT_SCOPES,
            expires_at=payload.get("exp"),
            subject=str(sub),
            claims={"legacy_jwt": True},
        )

    async def revoke_token(self, token: AccessToken | RefreshToken) -> None:
        store.revoke_token_string(token.token)

    def _issue_tokens(
        self,
        *,
        client_id: str,
        scopes: list[str],
        subject: str,
        resource: str | None,
    ) -> OAuthToken:
        now = datetime.now(timezone.utc)
        access = secrets.token_urlsafe(32)
        refresh = secrets.token_urlsafe(32)
        access_exp = now + timedelta(seconds=ACCESS_TTL_SECONDS)
        refresh_exp = now + timedelta(seconds=REFRESH_TTL_SECONDS)
        store.save_access_token(
            {
                "token": access,
                "client_id": client_id,
                "scopes": scopes,
                "subject": subject,
                "resource": resource,
                "expires_at": access_exp,
                "revoked": False,
            }
        )
        store.save_refresh_token(
            {
                "token": refresh,
                "client_id": client_id,
                "scopes": scopes,
                "subject": subject,
                "expires_at": refresh_exp,
                "revoked": False,
            }
        )
        return OAuthToken(
            access_token=access,
            token_type="Bearer",
            expires_in=ACCESS_TTL_SECONDS,
            scope=" ".join(scopes),
            refresh_token=refresh,
        )


def complete_login_with_code(*, sid: str, user_id: str) -> str:
    """Após login Valorian: emite authorization code e devolve URL de redirect do cliente."""
    pending = store.pop_pending(sid)
    if not pending:
        raise ValueError("Sessao OAuth expirada ou invalida. Tente conectar de novo no Claude.")

    code = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(seconds=CODE_TTL_SECONDS)
    store.save_code(
        {
            "code": code,
            "client_id": pending["client_id"],
            "scopes": pending.get("scopes") or DEFAULT_SCOPES,
            "expires_at": expires,
            "redirect_uri": pending["redirect_uri"],
            "redirect_uri_provided_explicitly": pending.get(
                "redirect_uri_provided_explicitly", True
            ),
            "code_challenge": pending["code_challenge"],
            "resource": pending.get("resource"),
            "subject": user_id,
            "state": pending.get("state"),
        }
    )
    q: dict[str, str] = {"code": code}
    if pending.get("state"):
        q["state"] = pending["state"]
    return f"{pending['redirect_uri']}?{urlencode(q)}"


def authenticate_user_for_oauth(email: str, password: str) -> dict:
    """Login Valorian com as mesmas regras da API; exige email verificado."""
    from app.utils.login_lockout import authenticate_login
    from fastapi import HTTPException

    user = authenticate_login(get_db(), email, password)
    if not is_email_verified(user):
        raise HTTPException(
            status_code=403,
            detail="Confirme seu email antes de conectar o Claude.",
        )
    return user
