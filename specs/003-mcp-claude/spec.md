# Feature Specification: MCP Claude Remoto

**Feature Branch**: `003-mcp-claude`

**Created**: 2026-07-30

**Status**: Active

**Input**: Servidor MCP remoto (HTTPS) para Claude, com tools de mentorado e admin autenticados via JWT Bearer.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Mentorado importa SWOT via Claude (Priority: P1)

O mentorado autentica-se na API, configura o Claude com a URL MCP e o Bearer token, carrega o prompt SWOT, gera o JSON e importa na conta com uma tool MCP.

**Why this priority**: Fecha o loop prompt → JSON → plataforma, valor principal do MCP.

**Independent Test**: Login → Bearer → `swot_import` → SWOT visível em `/swot`.

**Acceptance Scenarios**:

1. **Given** token de mentorado verificado, **When** Claude chama `swot_get`, **Then** recebe a SWOT da conta (vazia ou preenchida).
2. **Given** JSON válido `aegis.swot-ia`, **When** chama `swot_import`, **Then** a SWOT na plataforma é atualizada.
3. **Given** sem Bearer, **When** chama qualquer tool autenticada, **Then** recebe erro de autenticação.
4. **Given** SWOT existente, **When** chama `swot_update` ou `tows_rebuild`, **Then** a SWOT/TOWS é persistida sem passar pela UI.

---

### User Story 1b - Mentorado escreve Maturidade, OKR e Governança via Claude (Priority: P1)

O mentorado usa tools MCP para gravar autoavaliação, ciclos OKR e inventário/gates de governança — o mesmo contrato das rotas REST, com a ferramenta do AI Hub liberada na conta.

**Why this priority**: Fecha o loop do workspace (maturidade → SWOT/TOWS → canvas/OKR → governança) sem a UI.

**Independent Test**: `maturity_save` persiste respostas; `okr_create`+`okr_update` grava ciclo; `governance_create_system` aparece em `/governanca/inventario`.

**Acceptance Scenarios**:

1. **Given** token com ferramenta `maturity`, **When** `maturity_save` com answers 1–5, **Then** a autoavaliação é criada ou atualizada.
2. **Given** token com ferramenta `okr`, **When** `okr_create` e `okr_update`, **Then** o ciclo e os objectives ficam visíveis em `/okrs`.
3. **Given** token com ferramenta `governance`, **When** `governance_create_system`, **Then** o sistema entra no inventário.
4. **Given** ferramenta não liberada, **When** chama a tool correspondente, **Then** recebe erro de acesso.

---

### User Story 2 - Mentorado importa Canvas via Claude (Priority: P1)

Mesmo fluxo para Canvas de Oportunidades: prompt → JSON → import (lote ou em projeto aberto).

**Why this priority**: Paridade com SWOT; segundo artefato AI-assisted da mentoria.

**Independent Test**: `canvas_import` cria projetos; SPA `/projetos` lista-os.

**Acceptance Scenarios**:

1. **Given** JSON `aegis.canvas-oportunidades` válido, **When** `canvas_import`, **Then** projetos são criados.
2. **Given** `project_id` existente, **When** `canvas_import_into`, **Then** o projeto aberto é atualizado com a 1ª oportunidade.

---

### User Story 3 - Admin consulta dashboard e libera encontro (Priority: P2)

Admin autentica-se e usa tools `admin_*` no Claude para ver progresso e liberar encontros.

**Why this priority**: Segundo perfil; depende do mesmo servidor MCP.

**Independent Test**: Token admin → `admin_dashboard`; token aluno → 403 nas tools admin.

**Acceptance Scenarios**:

1. **Given** token admin, **When** `admin_dashboard`, **Then** lista alunos com métricas.
2. **Given** token não-admin, **When** `admin_dashboard`, **Then** acesso negado.
3. **Given** admin + `user_id` + `encontro_id`, **When** `admin_liberar_encontro`, **Then** encontro fica liberado no progresso.

---

### Edge Cases

- Token expirado ou inválido → erro de autenticação sem vazar detalhes internos.
- Email não verificado → tools de mentorado negadas (mesma regra da API).
- JSON de import inválido → erro de validação legível ao Claude.
- Mount `/mcp` não quebra `/api/health` nem a SPA.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Servidor MCP Streamable HTTP em `https://<host>/mcp` no mesmo processo FastAPI.
- **FR-002**: Autenticação via `Authorization: Bearer <JWT>` (mesmo token de `/api/auth/login`).
- **FR-003**: Tools mentorado (leitura e escrita) nas ferramentas do AI Hub, cada uma gated por `users.tools`: Maturidade (model/list/get/export/save); SWOT/TOWS (get/list/import/update/from_maturity/rebuild); Canvas (list/get/create/import/update/approve); OKR (list/get/active/create/update/activate/archive); Governança (sistemas, avaliação, gate); course get; strategic_map.
- **FR-004**: Tools admin: dashboard, list_users, user_progress, liberar_encontro — só com `is_admin`.
- **FR-005**: Resources/prompts MCP para prompts MD, schemas JSON e pilares SWOT.
- **FR-006**: Tools curadas (não espelhar OpenAPI inteiro).
- **FR-007**: Reutilizar lógica das rotas existentes (sem duplicar regras de negócio).

### Key Entities

- **MCP Session**: Cliente Claude → HTTPS `/mcp` com Bearer.
- **JWT User**: Mentorado verificado ou admin.

## Success Criteria *(mandatory)*

- **SC-001**: Mentorado completa SWOT via Claude sem abrir a UI de import manual.
- **SC-002**: Admin obtém dashboard via tool MCP com token admin.
- **SC-003**: Deploy unificado continua servindo API + SPA + MCP no mesmo container.
- **SC-004**: Mentorado grava Maturidade, TOWS, OKR, Canvas e Governança via MCP; o resultado aparece na SPA.
