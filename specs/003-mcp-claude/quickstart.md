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

Se o Claude não listar tools novas depois de um deploy: o cliente cacheia
`tools/list`. Confirme o catálogo com `python util/aegis_mcp_check.py … --email`,
habilite as tools no connector (**Allow always**), **remova e recoloque** o
connector e abra um **chat novo**. No Claude Code, mude o nome do servidor
(`aegis` → `aegis-hub`) ou use `MCP_DISCOVERY_CACHE=0`. Detalhes: `docs/mcp.md`.

## 3. Fluxos

1. Mentorado: prompt `swot_gerar_json` → gerar JSON → tool `swot_import` (ou `swot_update` / `tows_rebuild`)
2. Mentorado: prompt `canvas_gerar_json` → `canvas_import`
3. Mentorado: prompt `maturity_responder` → `maturity_questionnaire` → `maturity_answer` (até complete) → `swot_from_maturity`
4. Mentorado: `okr_create` → `okr_create_objective` → `okr_create_key_result` / `okr_update_key_result` → `okr_activate`
5. Mentorado: `governance_create_system` → `governance_create_assessment` → `governance_create_gate`
6. Admin: `admin_dashboard` / `admin_liberar_encontro`
7. Token aluno em `admin_dashboard` → erro de permissão
8. `GET /api/health` continua `ok`
