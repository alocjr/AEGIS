# Contract: MCP tools AEGIS

Endpoint: `POST/GET` Streamable HTTP em `/mcp`

Auth: `Authorization: Bearer <JWT>` em todas as tools autenticadas.

## Learner tools

Cada tool de ferramenta exige o id correspondente em `users.tools` (`maturity`, `swot`, `canvas`, `okr`, `governance`, `strategic_map`).

| Name | Args | Returns |
|------|------|---------|
| `swot_get` | — | SWOT document |
| `swot_get_by_id` | `swot_id` | SWOT document |
| `swot_list` | — | `{ items }` |
| `swot_by_maturity` | `maturity_response_id` | SWOT document |
| `swot_import` | `document: object` | SWOT updated |
| `swot_update` | `fields`, `swot_id?`, `rebuild_tows?` | SWOT updated |
| `swot_from_maturity` | `maturity_response_id` | SWOT created/updated |
| `tows_rebuild` | `swot_id?` | SWOT with TOWS rebuilt |
| `canvas_list` | — | `{ items }` |
| `canvas_get` | `project_id: str` | project |
| `canvas_create` | `title?` | project |
| `canvas_import` | `document: object` | `{ created, items }` |
| `canvas_import_into` | `project_id, document` | `{ applied, item }` |
| `canvas_update` | `project_id, fields: object` | project |
| `canvas_approve_portfolio` | `project_id` | `{ ai_system_id, status, … }` |
| `course_get` | `course_slug?: str` | course + progress |
| `maturity_model` | — | model |
| `maturity_my_responses` | — | `{ items }` |
| `maturity_get` | `response_id` | response |
| `maturity_export` | `response_id` | envelope `aegis.maturidade-ia` |
| `maturity_save` | `answers`, `tier?`, `response_id?` | saved response |
| `strategic_map` | `maturity_response_id?`, `swot_id?` | tree |
| `okr_list` | — | `{ items }` |
| `okr_get` | `cycle_id` | cycle |
| `okr_active` | — | active cycle |
| `okr_create` | `ano`, `tipo?`, `trimestre?`, `nome?` | cycle |
| `okr_update` | `cycle_id`, `fields` | cycle |
| `okr_activate` | `cycle_id` | cycle |
| `okr_archive` | `cycle_id` | cycle |
| `governance_org_members` | — | `{ items }` |
| `governance_list_systems` | — | `{ items }` |
| `governance_get_system` | `system_id` | system |
| `governance_create_system` | `fields` | system |
| `governance_update_system` | `system_id`, `fields` | system |
| `governance_create_assessment` | `system_id`, `fields` | assessment |
| `governance_create_gate` | `system_id` | gate |
| `governance_get_gate` | `gate_id` | gate |
| `governance_update_gate_item` | `gate_id`, `item_id`, `fields` | gate |
| `governance_decide_gate` | `gate_id`, `decisao` | gate |

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
