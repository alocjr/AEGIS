# Implementation Plan: MCP Claude Remoto

**Branch**: `003-mcp-claude` | **Date**: 2026-07-30 | **Spec**: [spec.md](./spec.md)

## Summary

Montar FastMCP no FastAPI existente em `/mcp` (Streamable HTTP), com tools curadas para mentorado e admin. Auth via JWT Bearer; domain logic reutiliza handlers em `backend/app/routes/*`.

## Technical Context

**Language/Version**: Python 3.11+ (backend)

**Primary Dependencies**: FastAPI, FastMCP, PyMongo, python-jose

**Storage**: MongoDB (inalterado)

**Testing**: Validação manual ([quickstart.md](./quickstart.md))

**Target Platform**: HTTPS remoto (Claude Desktop/Code)

**Project Type**: Extensão brownfield do backend

**Constraints**: Diff mínimo; deploy unificado; sem auto-expor OpenAPI

## Constitution Check

| Princípio | Status | Notas |
|-----------|--------|-------|
| I. Brownfield First | PASS | Estende FastAPI |
| II. Mudanças Mínimas | PASS | Pacote `app/mcp/` + mount |
| III. Segurança | PASS | JWT Bearer; admin gated |
| IV. API e Contratos | PASS | Tools documentadas em contracts |
| V. MongoDB | PASS | Sem novas coleções |
| VI. Deploy Unificado | PASS | Mesmo container `/mcp` |
| VII. Qualidade Pragmática | PASS | quickstart manual |

## Project Structure

```text
specs/003-mcp-claude/
backend/app/mcp/
  __init__.py
  server.py
  auth.py
  tools_learner.py
  tools_admin.py
  resources.py
  prompts.py
  util.py
docs/mcp.md
backend/requirements.txt  # + fastmcp
backend/app/main.py       # lifespan + mount /mcp
```

## Architecture

Tools chamam funções de rota com `user`/`admin` + `db` resolvidos em `auth.py` via `get_http_headers()`. Resources leem arquivos de `frontend-vue/public|dist` e `backend/data/`.
