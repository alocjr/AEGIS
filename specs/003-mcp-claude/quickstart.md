# Quickstart — MCP Claude

## Pré-requisitos

- Backend rodando (`uvicorn app.main:app --reload --port 8000`)
- Conta com email verificado (e admin para tools admin)

## 1. Obter token

```bash
curl -s -X POST http://localhost:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"SEU_EMAIL","password":"SUA_SENHA"}'
```

Copie `access_token`.

## 2. Configurar Claude (remoto)

URL: `http://localhost:8000/mcp/` (ou `https://<host>/mcp/` em produção)

Header: `Authorization: Bearer <access_token>`

Exemplos prontos: `mcp-client/` (ver `docs/mcp.md`).

```bash
python util/aegis_mcp_token.py --email SEU_EMAIL --print-env
cp mcp-client/claude-code.mcp.json.example .mcp.json
```

## 3. Fluxos

1. Mentorado: prompt `swot_gerar_json` → gerar JSON → tool `swot_import`
2. Mentorado: prompt `canvas_gerar_json` → `canvas_import`
3. Admin: `admin_dashboard` / `admin_liberar_encontro`
4. Token aluno em `admin_dashboard` → erro de permissão
5. `GET /api/health` continua `ok`
