#!/usr/bin/env python3
"""
Diagnóstico do MCP remoto AEGIS — simula o que o Claude faz ao adicionar um
connector por URL (Settings → Connectors → Add custom connector).

Uso:
    python util/aegis_mcp_check.py https://mentoria.valorian.com.br
    python util/aegis_mcp_check.py http://127.0.0.1:8000

Com --email, faz login (senha pedida via prompt, nunca fica em texto/argv) e
repete a sequência que o Claude faz DEPOIS de autorizar: initialize →
notifications/initialized → tools/list, com um token Bearer de verdade. Use
quando o Claude autoriza mas mostra "retornou um erro ao conectar" — os
checks sem --email só cobrem discovery/DCR/authorize, não uma sessão MCP real.

    python util/aegis_mcp_check.py https://mentoria.valorian.com.br --email voce@empresa.com

Só depende de httpx (já está em backend/requirements.txt).
"""

from __future__ import annotations

import argparse
import getpass
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


def _sse_json(resp: httpx.Response) -> dict | None:
    """Extrai o primeiro payload JSON de uma resposta text/event-stream ou JSON puro."""
    ctype = resp.headers.get("content-type", "")
    if "application/json" in ctype:
        try:
            return resp.json()
        except json.JSONDecodeError:
            return None
    for line in resp.text.splitlines():
        if line.startswith("data: "):
            try:
                return json.loads(line[6:])
            except json.JSONDecodeError:
                continue
    return None


def check_authenticated_session(base: str, email: str, password: str) -> int:
    """Repete initialize/tools-list com um Bearer token real — o que falha
    quando o Claude mostra 'autorizado, mas retornou um erro ao conectar'."""
    failures = 0
    client = httpx.Client(timeout=30, follow_redirects=False)

    print(f"=== Sessão MCP autenticada: {email} ===\n")

    resp = client.post(
        base + "/api/auth/login",
        json={"email": email, "password": password},
        headers={"Accept": "application/json"},
    )
    if resp.status_code != 200:
        print(f"{FAIL} POST /api/auth/login — HTTP {resp.status_code} {resp.text[:200]}")
        return 1
    token = resp.json().get("access_token")
    if not token:
        print(f"{FAIL} POST /api/auth/login — 200 mas sem access_token: {resp.text[:200]}")
        return 1
    print(f"{OK} POST /api/auth/login — token obtido")

    h = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }

    resp = client.post(
        base + "/mcp",
        headers=h,
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
    session_id = resp.headers.get("mcp-session-id")
    data = _sse_json(resp)
    if resp.status_code != 200 or not data or "error" in data:
        print(f"{FAIL} POST /mcp initialize — HTTP {resp.status_code}")
        print(f"      body: {resp.text[:500]}")
        return failures + 1
    print(f"{OK} POST /mcp initialize — servidor: {data.get('result', {}).get('serverInfo')}")
    if session_id:
        h["mcp-session-id"] = session_id

    resp = client.post(
        base + "/mcp",
        headers=h,
        json={"jsonrpc": "2.0", "method": "notifications/initialized"},
    )
    if resp.status_code not in (200, 202):
        print(f"{FAIL} POST /mcp notifications/initialized — HTTP {resp.status_code} {resp.text[:300]}")
        failures += 1
    else:
        print(f"{OK} POST /mcp notifications/initialized")

    resp = client.post(
        base + "/mcp",
        headers=h,
        json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
    )
    data = _sse_json(resp)
    if resp.status_code != 200 or not data or "error" in data:
        print(f"{FAIL} POST /mcp tools/list — HTTP {resp.status_code}")
        print(f"      body: {resp.text[:800]}")
        failures += 1
    else:
        names = [t["name"] for t in data.get("result", {}).get("tools", [])]
        print(f"{OK} POST /mcp tools/list — {len(names)} tools: {names}")

    print()
    return failures


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
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("base_url")
    parser.add_argument("--email", default=None)
    try:
        args = parser.parse_args()
    except SystemExit:
        print(__doc__)
        raise

    rc = check(args.base_url)
    if args.email:
        password = getpass.getpass(f"Senha ({args.email}): ")
        rc = check_authenticated_session(args.base_url.rstrip("/"), args.email, password) or rc
    raise SystemExit(rc)
