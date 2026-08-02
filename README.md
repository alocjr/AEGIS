# Valorian 4 Future (Aegis)

Plataforma de mentoria executiva com backend FastAPI + MongoDB e frontend Vue 3.

- **Backend:** FastAPI, autenticação JWT, reset de senha, progresso por aluno, trilhas, quiz e diagnóstico de maturidade em IA
- **Frontend:** Vue 3 + TypeScript em `frontend-vue/` (SPA + landing)
- **Persistência:** MongoDB (local via Docker Compose ou Atlas em produção)

## Funcionalidades principais

### Aluno
- Login e cadastro com JWT
- Reset de senha (`forgot-password` / `reset-password`)
- Trilhas de formação com encontros, materiais e progresso
- Marcação de materiais e conclusão de encontros
- Quiz por encontro (múltiplas tentativas conforme regras da trilha)
- **AI Maturity Model:** autoavaliação de maturidade em IA com múltiplas respostas por aluno e histórico de resultados
- Agenda e visualização de progresso

### Admin
- Dashboard com visão geral dos alunos
- CRUD de usuários e trilhas (`courses`)
- Gestão de progresso por aluno (liberação de encontros, agendas)
- CRUD de quiz e sincronização de `quiz_id` nas trilhas

### Público
- Listagem e vitrine de trilhas (`/api/public/courses`)
- Captura de leads

### MCP (Claude remoto)
- Endpoint Streamable HTTP em `/mcp` com **OAuth Connectors** (login Valorian no browser)
- Página de onboarding: `/conectar-claude`
- Ver [docs/mcp.md](docs/mcp.md)

## Estrutura do repositório

| Caminho | Descrição |
|---------|-----------|
| `backend/` | API FastAPI (ver `backend/README.md`) |
| `frontend-vue/` | SPA Vue (programa, trilhas, admin, quiz, maturidade) |
| `backend/data/course.json` | Seed da trilha padrão (importado na primeira subida se o Mongo estiver vazio) |
| `docs/mcp.md` | Configuração do servidor MCP Claude |
| `mcp-client/` | Exemplos de config Claude Desktop / Code |
| `util/create_user.py` | Script para criar ou atualizar usuário admin |
| `util/aegis_mcp_token.py` | Obtém JWT para o cliente MCP |
| `Dockerfile` | Build de produção: frontend + backend no mesmo container |
| `docker-compose.yml` | Deploy do app (MongoDB externo, ex.: Atlas) |

## Coleções MongoDB

| Coleção | Uso |
|---------|-----|
| `users` | Usuários e admins |
| `courses` | Trilhas e conteúdo (`programa_formacao_executiva`) |
| `progress` | Progresso por usuário e trilha |
| `quiz` / `quiz_responses` | Questionários e respostas |
| `ai_maturity_model` | Questionário de maturidade em IA (documento ativo) |
| `maturity_responses` | Autoavaliações (`model_id` → `ai_maturity_model`) |
| `password_resets` | Tokens de reset de senha |
| `leads` | Leads da landing |

O questionário é lido da coleção `ai_maturity_model` (documento mais recente). Em ambiente vazio, o bootstrap usa `backend/data/ai_maturity_model.json` só para seed inicial. Cada resposta em `maturity_responses` guarda `model_id` do questionário usado.

## Desenvolvimento

### 1. MongoDB

Use MongoDB Atlas ou suba um Mongo local:

```bash
docker compose up -d
```

> O `docker-compose.yml` atual sobe apenas o app. O banco costuma ficar na nuvem (`MONGODB_URI` no `.env`).

### 2. Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edite .env: MONGODB_URI, JWT_SECRET_KEY
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Documentação interativa: `http://127.0.0.1:8000/docs`

### 3. Frontend

```bash
cd frontend-vue
npm install
npm run dev
```

Acesse `http://localhost:5173` (proxy para a API em `8000`).

### 4. Criar admin

Na raiz do projeto, com `MONGODB_URI` configurado:

```bash
ADMIN_EMAIL=admin@exemplo.com ADMIN_PASSWORD=sua_senha_segura python util/create_user.py
```

Opcional: defina `INITIAL_ADMIN_EMAIL` no `.env` para conceder acesso admin a um email sem `is_admin` no banco.

## Produção (Docker)

Front e back no mesmo container; MongoDB permanece externo (Atlas).

```bash
cp .env.docker.example .env   # ou use backend/.env
# Preencha MONGODB_URI e JWT_SECRET_KEY
docker compose up --build
```

O app fica em `http://localhost:8000`. O health check interno usa `GET /api/health`.

Alternativa sem Compose:

```bash
docker build -t aegis .
docker run --env-file backend/.env -p 8000:8000 aegis
```

Para deploy manual sem Docker: configure as variáveis de ambiente, rode `npm ci && npm run build` em `frontend-vue/` e inicie o uvicorn **sem** `--reload`. O backend serve o SPA em `frontend-vue/dist` quando existir.

## Endpoints principais

### Autenticação (`/api/auth`)
- `POST /register`, `POST /login`, `GET /me`
- `POST /forgot-password`, `POST /reset-password`

### Curso e progresso
- `GET /api/course/current`
- `POST /api/progress/material`, `POST /api/progress/complete/{encontro_id}`

### Quiz (`/api/quiz`)
- Listagem, detalhe por encontro ou ID, envio e consulta de respostas

### Maturidade IA (`/api/maturity`)
- `GET /model` — modelo ativo em `ai_maturity_model`
- `GET /my-responses`, `GET /my-responses/{id}`, `POST /my-response` (autosave / upsert com `model_id`)

### Público (`/api/public`)
- `GET /courses`, `GET /courses/{slug}`, `POST /leads`

### Admin (`/api/admin`)
- Dashboard, usuários, trilhas, progresso, quiz

### Infra
- `GET /api/health` — health check (inclui MongoDB)

## Variáveis de ambiente

Ver `backend/.env.example`. Obrigatórias: `MONGODB_URI`, `JWT_SECRET_KEY`.

Principais opcionais: `MONGODB_DB_NAME`, `CORS_ORIGINS`, `JWT_EXPIRE_MINUTES`, `INITIAL_ADMIN_EMAIL`, `PASSWORD_RESET_EXPIRE_MINUTES`, `PASSWORD_RESET_RETURN_TOKEN` (apenas dev).

Detalhes de reset de senha e health check: `backend/README.md`.

## Desenvolvimento com Spec Kit

O projeto usa [GitHub Spec Kit](https://github.github.com/spec-kit/) (Spec-Driven Development) com integração **Cursor**.

### Setup (já inicializado)

- CLI: `specify` (via `uv tool install specify-cli --from git+https://github.com/github/spec-kit.git@v0.11.6`)
- Templates e scripts: `.specify/`
- Skills Cursor: `.cursor/skills/speckit-*`
- Constitution: `.specify/memory/constitution.md`
- Baseline brownfield: `specs/001-aegis-baseline/spec.md`

### Fluxo por feature

1. `/speckit-specify` — definir o quê/por quê (cria branch `NNN-nome` e `specs/NNN-nome/`)
2. `/speckit-clarify` — esclarecer ambiguidades (opcional)
3. `/speckit-plan` — plano técnico com stack AEGIS
4. `/speckit-tasks` — tarefas acionáveis
5. `/speckit-analyze` — validar consistência antes de codar
6. `/speckit-implement` — executar implementação

Extensão **git** habilitada: commits e branches automáticos entre fases (config em `.specify/extensions.yml`).

