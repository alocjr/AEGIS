#!/usr/bin/env python3
"""Obtém JWT da API AEGIS para configurar o cliente MCP (Claude Desktop / Code).

Uso:
  python util/aegis_mcp_token.py --email voce@empresa.com
  python util/aegis_mcp_token.py --email voce@empresa.com --base-url https://app.seudominio.com
  AEGIS_EMAIL=... AEGIS_PASSWORD=... python util/aegis_mcp_token.py --print-env

Não imprime a senha. O token vai para stdout (ou bloco export).
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import sys
import urllib.error
import urllib.request


def login(base_url: str, email: str, password: str) -> str:
    url = base_url.rstrip("/") + "/api/auth/login"
    body = json.dumps({"email": email, "password": password}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"Login falhou ({exc.code}): {detail}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"Nao foi possivel conectar em {url}: {exc}") from exc

    token = data.get("access_token")
    if not token:
        raise SystemExit(f"Resposta sem access_token: {data}")
    return token


def main() -> None:
    parser = argparse.ArgumentParser(description="JWT para cliente MCP AEGIS")
    parser.add_argument(
        "--base-url",
        default=os.environ.get("AEGIS_MCP_BASE_URL")
        or os.environ.get("APP_BASE_URL")
        or "http://127.0.0.1:8000",
        help="URL base da API (default: http://127.0.0.1:8000)",
    )
    parser.add_argument("--email", default=os.environ.get("AEGIS_EMAIL"), help="Email da conta")
    parser.add_argument(
        "--password",
        default=os.environ.get("AEGIS_PASSWORD"),
        help="Senha (prefira prompt interativo ou env AEGIS_PASSWORD)",
    )
    parser.add_argument(
        "--print-env",
        action="store_true",
        help="Imprime exports AEGIS_MCP_URL e AEGIS_MCP_TOKEN para shell",
    )
    args = parser.parse_args()

    email = args.email or input("Email: ").strip()
    password = args.password or getpass.getpass("Senha: ")
    if not email or not password:
        raise SystemExit("Email e senha sao obrigatorios.")

    token = login(args.base_url, email, password)
    mcp_url = args.base_url.rstrip("/") + "/mcp/"

    if args.print_env:
        # Valores entre aspas simples para o shell; token JWT nao contem '
        print(f"export AEGIS_MCP_URL='{mcp_url}'")
        print(f"export AEGIS_MCP_TOKEN='{token}'")
        print(f"export AEGIS_AUTH_HEADER='Bearer {token}'")
        print(
            f"# Claude Code: cp mcp-client/claude-code.mcp.json.example .mcp.json && claude mcp list",
            file=sys.stderr,
        )
        return

    print(token)
    print(f"# MCP URL: {mcp_url}", file=sys.stderr)
    print("# Header: Authorization: Bearer <token acima>", file=sys.stderr)


if __name__ == "__main__":
    main()
