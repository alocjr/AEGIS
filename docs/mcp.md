# MCP Claude (remoto) — Valorian / AEGIS

Servidor [Model Context Protocol](https://modelcontextprotocol.io) em **`/mcp`** com **OAuth 2.1** (Claude Connectors) e compatibilidade com Bearer JWT legado.

## UX ideal (usuário final)

1. Você envia a URL: `https://mentoria.valorian.com.br/mcp` (ou a página [`/conectar-claude`](/conectar-claude)).
2. No Claude: **Settings → Connectors → Add custom connector** → cola a URL.
3. **Connect** → o browser abre o login Valorian (email/senha).
4. Após autorizar, as tools AEGIS ficam disponíveis no chat.

Requisitos: **HTTPS público** em produção (a nuvem da Anthropic chama o servidor). Localhost serve para Claude Code na mesma máquina.

Variável de ambiente: `MCP_PUBLIC_URL` — em produção use `https://mentoria.valorian.com.br` (não `valorian.cloud`). Default local: `http://127.0.0.1:8000`.

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

## Diagnóstico (antes de mandar a URL para alguém)

```bash
python util/aegis_mcp_check.py https://mentoria.valorian.com.br
```

O script simula o que o Claude faz ao adicionar um connector: discovery
(`/.well-known/*`), DCR (`POST /register`), `/authorize` e `POST /mcp` sem token.

## Troubleshooting

| Sintoma no check / no Claude | Causa | Correção |
|---|---|---|
| `/.well-known/*` responde `text/html` | O fallback do SPA capturou a rota — as rotas MCP não foram registradas antes dele | `install_mcp_routes(app, mcp_asgi)` em `main.py`, **depois** dos routers e **antes** do `vue_spa_fallback` |
| `POST /register` e `POST /mcp` → **405** | O build em produção não tem o código MCP | Rebuild + redeploy da imagem |
| `POST /mcp` → **500** | `route.endpoint` sem `__name__`: o SlowAPI faz `route.endpoint.__name__` ao casar a rota | Ao levantar rotas do app do FastMCP, ajustar `route.app` **e** `route.endpoint` |
| `POST /mcp` → **401** mesmo com token válido | O `AuthenticationMiddleware`/`AuthContextMiddleware` do FastMCP se perde ao levantar só as rotas; o `RequireAuthMiddleware` lê `scope["user"]` | `apply_mcp_auth_middleware()` reaplica o stack em cada rota |
| `Task group is not initialized` | Lifespan do FastMCP não repassado | `async with mcp_asgi.lifespan(app)` no lifespan do FastAPI |
| Claude conecta e cai no login errado | `MCP_PUBLIC_URL` apontando para localhost | `MCP_PUBLIC_URL=https://mentoria.valorian.com.br` no `.env` de produção |
| Claude não vê tools novas (`maturity_answer`, `okr_create_objective`, …) | Cache de `tools/list` no Claude (URL/nome do connector). `notifications/tools/list_changed` é ignorado. Settings pode listar as tools enquanto o **modelo** ainda usa o catálogo antigo. | 1. Confirme o deploy: `python util/aegis_mcp_check.py https://mentoria.valorian.com.br --email voce@empresa.com` deve listar as tools novas. 2. No connector, **Allow always** nas tools novas. 3. **Remova e recoloque** o connector (mesma URL). 4. Abra um **chat novo**. 5. Claude Code: `claude mcp remove aegis` e adicione com outro nome (`aegis-hub`), ou `MCP_DISCOVERY_CACHE=0`. |

> Discovery e DCR só funcionam sobre **HTTPS público**: a nuvem da Anthropic é
> quem chama o servidor, não o seu desktop.

## Tools (mentorado)

Cada grupo exige a ferramenta correspondente liberada na conta (`users.tools`).

Catálogo versionado em `TOOLS_CATALOG_VERSION` (`backend/app/mcp/server.py`). Bump
esse valor sempre que adicionar ou mudar tools — o Claude cacheia `tools/list`.

### Maturidade

| Tool | Descrição |
|------|-----------|
| `maturity_model` | Modelo completo (SWOT/TOWS) — prefira o questionário |
| `maturity_questionnaire` | **Entrevista** — perguntas + escalas 1–5 + progresso |
| `maturity_answer` | **Escrita** — grava 1+ notas (merge; `question_id`+`score` ou `answers`) |
| `maturity_my_responses` | Lista autoavaliações |
| `maturity_get` | Uma autoavaliação (respostas + resultado) |
| `maturity_export` | Envelope `aegis.maturidade-ia` |
| `maturity_save` | **Escrita** — substitui o mapa inteiro de answers |

### SWOT / TOWS

| Tool | Descrição |
|------|-----------|
| `swot_get` / `swot_get_by_id` / `swot_list` / `swot_by_maturity` | Leitura |
| `swot_import` | **Escrita** — substitui pela JSON `aegis.swot-ia` |
| `swot_update` | **Escrita** — atualiza quadrantes, TOWS e veredito |
| `swot_from_maturity` | **Escrita** — gera SWOT a partir da autoavaliação |
| `tows_rebuild` | **Escrita** — recalcula FO/FA/FxO/FxA a partir dos itens com `tows=true` |

### Canvas

| Tool | Descrição |
|------|-----------|
| `canvas_list` / `canvas_get` | Leitura |
| `canvas_create` | **Escrita** — projeto vazio |
| `canvas_import` / `canvas_import_into` | **Escrita** — import `aegis.canvas-oportunidades` |
| `canvas_update` | **Escrita** — campos do canvas |
| `canvas_approve_portfolio` | **Escrita** — aprova e cria sistema no inventário |

### OKR

| Tool | Descrição |
|------|-----------|
| `okr_list` / `okr_get` / `okr_active` | Leitura |
| `okr_create` | **Escrita** — ciclo (opcionalmente já com objectives) |
| `okr_create_objective` | **Escrita** — adiciona um Objective (e KRs) sem apagar os outros |
| `okr_update_objective` | **Escrita** — atualiza um Objective por id (merge) |
| `okr_create_key_result` | **Escrita** — adiciona um Key Result a um Objective |
| `okr_update_key_result` | **Escrita** — atualiza um Key Result (current, target, título…) |
| `okr_update` | **Escrita** — metadados do ciclo; `objectives` substitui a lista inteira |
| `okr_activate` / `okr_archive` | **Escrita** — ciclo ativo único / encerrar |

### Governança

| Tool | Descrição |
|------|-----------|
| `governance_org_members` | Membros da org (RACI / aprovador) |
| `governance_list_systems` / `governance_get_system` | Inventário |
| `governance_create_system` / `governance_update_system` | **Escrita** — ficha do sistema |
| `governance_create_assessment` | **Escrita** — avaliação de risco |
| `governance_create_gate` / `governance_get_gate` | Gate go/no-go |
| `governance_update_gate_item` | **Escrita** — item do checklist |
| `governance_decide_gate` | **Escrita** — go / no-go / go condicional |

### Outras

| Tool | Descrição |
|------|-----------|
| `course_get` | Trilha + progresso |
| `strategic_map` | Árvore maturidade → SWOT → TOWS → projetos |

## Tools (admin)

| Tool | Descrição |
|------|-----------|
| `admin_dashboard` | Alunos e métricas |
| `admin_list_users` | Lista resumida |
| `admin_user_progress` | Curso/progresso de um aluno |
| `admin_liberar_encontro` | Liberar encontro |

## Resources e prompts

- Resources: `aegis://prompt/swot-ia`, `aegis://prompt/canvas-oportunidades`, `aegis://schema/swot-ia`, `aegis://schema/canvas-oportunidades`, `aegis://data/swot-pillars`
- Prompts MCP: `swot_gerar_json`, `canvas_gerar_json`, `maturity_responder`

## Segurança

- Tokens OAuth em Mongo (`mcp_oauth_*`); não logar tokens.
- Connectors Claude acessam a API pela internet — use HTTPS e `MCP_PUBLIC_URL` correto.
- Tools `admin_*` exigem `is_admin` na execução.
- Rate limit SlowAPI não cobre o volume de import MCP da mesma forma que a REST.

## Desenvolvimento

Pacote: `backend/app/mcp/`. Spec: `specs/003-mcp-claude/`. Dependência: `fastmcp`.
