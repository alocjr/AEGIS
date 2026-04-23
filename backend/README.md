# Backend – Valorian 4 Future (Aegis)

API FastAPI + MongoDB para a plataforma de mentoria.

## Desenvolvimento

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edite .env com MONGODB_URI e JWT_SECRET_KEY
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Acesso: `http://127.0.0.1:8000`. Documentação interativa: `http://127.0.0.1:8000/docs`.

## Produção

- **Não use** `--reload`.
- Defina no ambiente (ou `.env` em servidor):
  - `MONGODB_URI`, `JWT_SECRET_KEY` (obrigatórios)
  - `CORS_ORIGINS`: origem(s) do frontend (ex.: `https://app.seudominio.com`)
  - `MONGODB_DB_NAME`, `JWT_EXPIRE_MINUTES` (opcionais)
- Build do frontend: em `frontend-vue/` execute `npm ci && npm run build`. O backend serve os arquivos de `frontend-vue/dist` quando existirem.

Exemplo de comando em produção:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Health check

- `GET /api/health`: retorna `{"status": "ok", "mongodb": "connected"}` se o app e o MongoDB estiverem ok. Retorna 503 se o MongoDB estiver inacessível (útil para load balancer e monitoramento).

## Reset de senha

- `POST /api/auth/forgot-password` com `{ "email": "..." }`: cria token de reset (resposta sempre genérica para não expor se o email existe).
- `POST /api/auth/reset-password` com `{ "token": "...", "new_password": "..." }`: valida token e atualiza a senha.
- Em desenvolvimento, opcionalmente habilite `PASSWORD_RESET_RETURN_TOKEN=true` para a API devolver `reset_token` na resposta do `forgot-password`.

## Variáveis de ambiente

Ver `.env.example`. Nunca commite `.env` com credenciais reais.
