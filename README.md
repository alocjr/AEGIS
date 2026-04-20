# Valorian 4 Future (Aegis)

Plataforma de mentoria com backend FastAPI + MongoDB e frontend Vue 3.

- **Backend:** FastAPI, autenticação JWT, progresso por usuário, trilhas, quiz, modelo de maturidade
- **Frontend:** Vue 3 + TypeScript em `frontend-vue/` (SPA)
- **Persistência:** MongoDB

## Estrutura

- `backend/` – API (ver `backend/README.md`)
- `frontend-vue/` – SPA Vue (login, programa, trilhas, admin, quiz, maturidade)
- `backend/data/course.json` – seed do curso (importado para o MongoDB na primeira subida)

## Desenvolvimento

### 1. Subir MongoDB

```bash
docker compose up -d
```

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

### 3. Frontend

```bash
cd frontend-vue
npm install
npm run dev
```

Acesse `http://localhost:5173` (proxy para a API em 8000).

## Produção

1. **Backend:** Configure `MONGODB_URI`, `JWT_SECRET_KEY` e `CORS_ORIGINS` (origem real do frontend). Rode **sem** `--reload`:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```
2. **Frontend:** Em `frontend-vue/`: `npm ci && npm run build`. Opcional: defina `VITE_API_BASE_URL` se a API estiver em outro host.
3. O backend serve a SPA em `frontend-vue/dist` quando existir (rotas `/`, `/programa`, `/admin`, etc.).

Ver `backend/README.md` para health check e variáveis de ambiente.

## Endpoints principais

- `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me`
- `GET /api/course/current`, `POST /api/progress/complete/{encontro_id}`
- `GET /api/health` – health check (inclui MongoDB)
