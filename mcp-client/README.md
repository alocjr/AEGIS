# Cliente MCP — Claude Desktop / Claude Code

## Preferido: só a URL (OAuth)

Envie ao usuário: **`https://seu-dominio/mcp`** ou a página **`/conectar-claude`**.

No Claude: Settings → Connectors → Add custom connector → cole a URL → Connect → login Valorian.

Não é necessário JWT manual.

## Legacy (JWT + mcp-remote)

| Arquivo | Uso |
|---------|-----|
| [`claude-code.mcp.json.example`](claude-code.mcp.json.example) | Claude Code HTTP (OAuth no `/mcp` ou Bearer) |
| [`claude-desktop.config.example.json`](claude-desktop.config.example.json) | Desktop via `mcp-remote` + Bearer |

```bash
python util/aegis_mcp_token.py --email voce@empresa.com --print-env
```

Guia: [`docs/mcp.md`](../docs/mcp.md).
