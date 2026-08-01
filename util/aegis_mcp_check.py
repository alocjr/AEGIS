#!/usr/bin/env python3
"""
Diagnóstico do MCP remoto AEGIS — simula o que o Claude faz ao adicionar um
connector por URL (Settings → Connectors → Add custom connector).

Uso:
    python util/aegis_mcp_check.py https://mentoria.valorian.com.br
    python util/aegis_mcp_check.py http://127.0.0.1:8000

Só depende de httpx (já está em backend/requirements.txt).
"""

from __future__ import annotations

import json
import sys

import httpx

OK = "\033[32mOK  \033[0m"
FAIL = "\033[31mFALHA\033[0m"
WARN = "\033[33mAVISO\033[0m"

CLAUDE_REDIRECT = "https://claude.ai/api/mcp/auth_callback"


def _json_or_none(resp: httpx.Response) -> dict | None:
    ctype = resp.headers.get("content-type", "")
    if "application/json" not in ctype:
        return None
    try:
        return resp.json()
    except json.JSONDecodeError:
        return None


def check(base: str) -> int:
    base = base.rstrip("/")
    failures = 0
    client = httpx.Client(timeout=20, follow_redirects=False)

    print(f"\n=== Diagnóstico MCP: {base} ===\n")

    # 1. Discovery — o erro clássico é o fallback do SPA devolver text/html.
    discovery = {
        "/.well-known/oauth-protected-resource": "PRM na raiz (Claude consulta primeiro)",
        "/.well-known/oauth-protected-resource/mcp": "PRM do resource (RFC 9728)",
        "/.well-known/oauth-authorization-server": "Metadata do AS (RFC 8414)",
    }
    metadata: dict = {}
    for path, label in discovery.items():
        try:
            resp = client.get(base + path)
        except httpx.HTTPError as exc:
            print(f"{FAIL} GET {path} — {exc}")
            failures += 1
            continue
        data = _json_or_none(resp)
        if resp.status_code != 200 or data is None:
            ctype = resp.headers.get("content-type", "?")
            print(f"{FAIL} GET {path} — HTTP {resp.status_code} content-type={ctype}")
            if "html" in ctype:
                print("      → o fallback do SPA está capturando a rota; "
                      "as rotas MCP precisam vir antes (install_mcp_routes).")
            failures += 1
            continue
        print(f"{OK} GET {path} — {label}")
        if path.endswith("oauth-authorization-server"):
            metadata = data

    if not base.startswith("https://"):
        print(f"{WARN} URL não é HTTPS — Claude Desktop/claude.ai só conectam em HTTPS público.")

    # 2. O AS precisa aceitar cliente público (PKCE, sem client_secret).
    if metadata:
        methods = metadata.get("token_endpoint_auth_methods_supported") or []
        if "none" in methods:
            print(f"{OK} token_endpoint_auth_methods_supported inclui 'none' (cliente público + PKCE)")
        else:
            print(f"{FAIL} token_endpoint_auth_methods_supported = {methods} (falta 'none')")
            failures += 1
        for field in ("authorization_endpoint", "token_endpoint", "registration_endpoint"):
            if not metadata.get(field):
                print(f"{FAIL} metadata sem {field}")
                failures += 1

    # 3. Dynamic Client Registration — sem isso o Claude não consegue se registrar.
    client_id = None
    try:
        resp = client.post(
            base + "/register",
            json={
                "client_name": "aegis-mcp-check",
                "redirect_uris": [CLAUDE_REDIRECT],
                "token_endpoint_auth_method": "none",
                "grant_types": ["authorization_code", "refresh_token"],
                "response_types": ["code"],
                "scope": "mcp",
            },
        )
        if resp.status_code in (200, 201):
            client_id = resp.json().get("client_id")
            print(f"{OK} POST /register — DCR habilitado (client_id={client_id})")
        else:
            print(f"{FAIL} POST /register — HTTP {resp.status_code} {resp.text[:160]}")
            failures += 1
    except httpx.HTTPError as exc:
        print(f"{FAIL} POST /register — {exc}")
        failures += 1

    # 4. /authorize deve redirecionar para o login Valorian.
    if client_id:
        resp = client.get(
            base + "/authorize",
            params={
                "client_id": client_id,
                "response_type": "code",
                "redirect_uri": CLAUDE_REDIRECT,
                "code_challenge": "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM",
                "code_challenge_method": "S256",
                "state": "aegis-check",
                "scope": "mcp",
            },
        )
        location = resp.headers.get("location", "")
        if resp.status_code in (302, 303, 307) and "/mcp-oauth/login" in location:
            print(f"{OK} GET /authorize — redireciona para o login Valorian")
        else:
            print(f"{FAIL} GET /authorize — HTTP {resp.status_code} location={location[:120]}")
            failures += 1

    # 5. /mcp sem token: 401 + WWW-Authenticate com resource_metadata.
    #    HTTP 500 aqui é o sintoma de route.endpoint sem __name__ (SlowAPI).
    resp = client.post(
        base + "/mcp",
        headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream"},
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "aegis-mcp-check", "version": "1"},
            },
        },
    )
    www = resp.headers.get("www-authenticate", "")
    if resp.status_code == 401 and "resource_metadata=" in www:
        print(f"{OK} POST /mcp sem token — 401 com WWW-Authenticate + resource_metadata")
    elif resp.status_code == 500:
        print(f"{FAIL} POST /mcp — HTTP 500. Verifique route.endpoint/__name__ (SlowAPI) "
              "e o lifespan do FastMCP no app FastAPI.")
        failures += 1
    else:
        print(f"{FAIL} POST /mcp sem token — HTTP {resp.status_code} www-authenticate={www[:100]}")
        failures += 1

    print()
    if failures:
        print(f"{failures} verificação(ões) falharam. Veja docs/mcp.md.\n")
        return 1
    print("Tudo certo — cole a URL abaixo no Claude (Add custom connector):")
    print(f"    {base}/mcp\n")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        raise SystemExit(2)
    raise SystemExit(check(sys.argv[1]))
