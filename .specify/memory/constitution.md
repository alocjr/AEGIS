# AEGIS (Valorian 4 Future) Constitution

## Core Principles

### I. Brownfield First
Respeitar a arquitetura existente: FastAPI + MongoDB no backend, Vue 3 + TypeScript no frontend. Novas features estendem o sistema; refatorações amplas só quando explicitamente solicitadas.

### II. Mudanças Mínimas
Cada entrega deve ser o menor diff correto. Não adicionar abstrações, dependências ou arquivos fora do escopo da feature. Reutilizar rotas, schemas, stores e padrões já presentes no repositório.

### III. Segurança por Padrão
Autenticação via JWT; senhas sempre com hash; tokens de reset armazenados apenas em hash; nunca commitar `.env` ou credenciais. Respostas de auth não devem revelar se um email existe quando aplicável.

### IV. API e Contratos Explícitos
Endpoints REST sob `/api/*`. Schemas Pydantic em `backend/app/schemas.py`. Clientes HTTP em `frontend-vue/src/api/*`. Mudanças de contrato exigem atualização sincronizada de backend e frontend.

### V. MongoDB como Fonte de Verdade
Trilhas (`courses`), progresso (`progress`), quiz, modelo de maturidade (`ai_maturity_model`) e respostas vivem no MongoDB. Evitar hardcode de conteúdo de negócio em arquivos estáticos quando a coleção correspondente existir.

### VI. Deploy Unificado
Manter compatibilidade com o Dockerfile atual: build do Vue em `frontend-vue/dist` servido pelo uvicorn junto com a API. Health check em `GET /api/health`.

### VII. Qualidade Pragmática
Preferir validação manual documentada quando não houver suite automatizada para o escopo. Testes automatizados só quando agregarem cobertura real de comportamento.

## Stack e Estrutura

| Camada | Tecnologia | Caminhos principais |
|--------|------------|---------------------|
| API | FastAPI, PyMongo, python-jose, passlib | `backend/app/routes/`, `backend/app/schemas.py` |
| Auth | JWT Bearer | `backend/app/security.py`, `backend/app/deps.py` |
| SPA | Vue 3, TypeScript, Vite | `frontend-vue/src/views/`, `frontend-vue/src/router/` |
| Admin | Rotas `/admin` + `/api/admin` | `frontend-vue/src/views/admin/` |
| Utilitários | Scripts Python | `util/` |

## Workflow Spec Kit

1. Uma feature = branch `NNN-nome-curto` (extensão git) + diretório em `specs/`.
2. Fluxo recomendado: `/speckit-specify` → `/speckit-clarify` (se necessário) → `/speckit-plan` → `/speckit-tasks` → `/speckit-analyze` → `/speckit-implement`.
3. Specs descrevem **o quê** e **por quê**; planos técnicos definem **como** com a stack acima.
4. Atualizar `README.md` apenas quando a mudança impactar setup, deploy ou operação.

## Governança

- Esta constitution prevalece sobre decisões ad hoc do agente.
- Emendas exigem PR dedicado e atualização da data em **Last Amended**.
- PRs devem referenciar a spec/plan/tasks da feature em `specs/` quando aplicável.

**Version**: 1.0.0 | **Ratified**: 2026-06-24 | **Last Amended**: 2026-06-24
