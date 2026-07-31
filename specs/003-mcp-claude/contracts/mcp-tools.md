# Contract: MCP tools AEGIS

Endpoint: `POST/GET` Streamable HTTP em `/mcp`

Auth: `Authorization: Bearer <JWT>` em todas as tools autenticadas.

## Learner tools

| Name | Args | Returns |
|------|------|---------|
| `swot_get` | — | SWOT document |
| `swot_import` | `document: object` | SWOT updated |
| `canvas_list` | — | `{ items }` |
| `canvas_get` | `project_id: str` | project |
| `canvas_import` | `document: object` | `{ created, items }` |
| `canvas_import_into` | `project_id, document` | `{ applied, item }` |
| `canvas_update` | `project_id, fields: object` | project |
| `course_get` | `course_slug?: str` | course + progress |
| `maturity_model` | — | model |
| `maturity_my_responses` | — | `{ items }` |

## Admin tools

| Name | Args | Returns |
|------|------|---------|
| `admin_dashboard` | — | student rows |
| `admin_list_users` | — | users |
| `admin_user_progress` | `user_id`, `course_slug?` | course + progress |
| `admin_liberar_encontro` | `user_id`, `encontro_id` | progress update |

## Resources

- `aegis://prompt/swot-ia`
- `aegis://prompt/canvas-oportunidades`
- `aegis://schema/swot-ia`
- `aegis://schema/canvas-oportunidades`
- `aegis://data/swot-pillars`

## Prompts

- `swot_gerar_json`
- `canvas_gerar_json`
