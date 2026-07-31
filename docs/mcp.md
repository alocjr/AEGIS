# MCP Claude (remoto) — Valorian / AEGIS

Servidor [Model Context Protocol](https://modelcontextprotocol.io) em **`/mcp`** com **OAuth 2.1** (Claude Connectors) e compatibilidade com Bearer JWT legado.

## UX ideal (usuário final)

1. Você envia a URL: `https://seu-dominio/mcp` (ou a página [`/conectar-claude`](/conectar-claude)).
2. No Claude: **Settings → Connectors → Add custom connector** → cola a URL.
3. **Connect** → o browser abre o login Valorian (email/senha).
4. Após autorizar, as tools AEGIS ficam disponíveis no chat.

Requisitos: **HTTPS público** em produção (a nuvem da Anthropic chama o servidor). Localhost serve para Claude Code na mesma máquina.

Variável de ambiente: `MCP_PUBLIC_URL` (URL pública da API, ex. `https://app.seudominio.com`). Default: `http://127.0.0.1:8000`.

## Autenticação

| Modo | Uso |
|------|-----|
| **OAuth Connectors** | Fluxo preferido — login no browser, DCR automático |
| **Bearer JWT** | `POST /api/auth/login` → `Authorization: Bearer <access_token>` (mcp-remote / scripts) |

Cookies da SPA **não** são usados. Email precisa estar verificado. Tools `admin_*` exigem `is_admin`.

## Endpoints OAuth

| Path | Função |
|------|--------|
| `/.well-known/oauth-authorization-server` | Metadata do AS (inclui `token_endpoint_auth_methods_supported: none`) |
| `/.well-known/oauth-protected-resource` | PRM raiz (Claude consulta sem `/mcp`) |
| `/.well-known/oauth-protected-resource/mcp` | Metadata do resource |
| `/register` | Dynamic Client Registration |
| `/authorize` | Inicia OAuth → redirect login |
| `/mcp-oauth/login` | Formulário email/senha Valorian |
| `/token` | Troca code / refresh |
| `/mcp` | MCP Streamable HTTP |
| `/conectar-claude` | Página de instruções + URL |

## Cliente Claude Desktop / Code

### Connectors (recomendado)

Só a URL `https://<host>/mcp` — sem colar JWT. Ver `/conectar-claude`.

### Claude Code (CLI)

```bash
claude mcp add --transport http aegis "https://<host>/mcp"
# Na sessão: /mcp → Authenticate (browser)
```

### Legacy (mcp-remote + JWT)

Ainda funciona: [`mcp-client/`](../mcp-client/) + `util/aegis_mcp_token.py`.

```bash
python util/aegis_mcp_token.py --email voce@empresa.com --print-env
claude mcp add --transport http aegis "${AEGIS_MCP_URL}" \
  --header "Authorization: Bearer ${AEGIS_MCP_TOKEN}"
```

## Tools (mentorado)

| Tool | Descrição |
|------|-----------|
| `swot_get` / `swot_import` | Ler / importar SWOT de IA (`aegis.swot-ia`) |
| `canvas_list` / `canvas_get` | Listar / ler projetos |
| `canvas_import` / `canvas_import_into` | Importar oportunidades (lote / projeto aberto) |
| `canvas_update` | Atualizar campos do canvas |
| `course_get` | Trilha + progresso |
| `maturity_model` / `maturity_my_responses` | Modelo e respostas (leitura) |

## Tools (admin)

| Tool | Descrição |
|------|-----------|
| `admin_dashboard` | Alunos e métricas |
| `admin_list_users` | Lista resumida |
| `admin_user_progress` | Curso/progresso de um aluno |
| `admin_liberar_encontro` | Liberar encontro |

## Resources e prompts

- Resources: `aegis://prompt/swot-ia`, `aegis://prompt/canvas-oportunidades`, `aegis://schema/swot-ia`, `aegis://schema/canvas-oportunidades`, `aegis://data/swot-pillars`
- Prompts MCP: `swot_gerar_json`, `canvas_gerar_json`

## Segurança

- Tokens OAuth em Mongo (`mcp_oauth_*`); não logar tokens.
- Connectors Claude acessam a API pela internet — use HTTPS e `MCP_PUBLIC_URL` correto.
- Tools `admin_*` exigem `is_admin` na execução.
- Rate limit SlowAPI não cobre o volume de import MCP da mesma forma que a REST.

## Desenvolvimento

Pacote: `backend/app/mcp/`. Spec: `specs/003-mcp-claude/`. Dependência: `fastmcp`.
