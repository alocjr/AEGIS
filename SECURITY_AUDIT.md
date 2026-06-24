# Auditoria de Segurança — AEGIS

**Data:** 2026-06-24  
**Última atualização:** 2026-06-24 (correções aplicadas)  
**Escopo:** repositório completo (`backend/`, `frontend-vue/`, `Dockerfile`, `docker-compose.yml`).

---

## Resumo executivo

| # | Achado | Severidade | Status |
|---|--------|------------|--------|
| 1 | Flag `PASSWORD_RESET_RETURN_TOKEN` vazava token de reset na API | **Crítico** | **Corrigido** — `d7bee91` |
| 2b | Bootstrap de admin via `INITIAL_ADMIN_EMAIL` | **Alto** | **Corrigido** — `55d4cbb` |
| 3 | Login sem rate limiting / lockout | **Alto** | **Corrigido** — `fea9d34` |
| 4 | Auto-registro sem verificação de e-mail | **Médio** | **Corrigido** — `bfa9520` |
| 5 | JWT em `localStorage` | **Médio** | **Corrigido** — `a6b4c0a` |
| 6 | Container root; `/docs` exposto | **Médio** | **Corrigido** — `00b056d` |
| 7 | CSP com `script-src 'unsafe-inline'` | **Baixo** | **Corrigido** — `69ff3ed` |
| 8 | Injeção NoSQL | — | Sem ação necessária |

---

## 1. Vazamento de token de reset de senha (Crítico) — Corrigido (`d7bee91`)

- Removido `password_reset_return_token` de `config.py` e `.env.example`.
- `/api/auth/forgot-password` retorna apenas mensagem genérica, sem `reset_token`.
- Frontend atualizado para não depender do token na resposta HTTP.

---

## 2b. Bootstrap de admin via `INITIAL_ADMIN_EMAIL` (Alto) — Corrigido (`55d4cbb`)

- Removida checagem de admin por env em `deps.py` e `auth.py`.
- Criado `backend/app/scripts/promote_admin.py` para bootstrap manual (`--email`).
- `is_admin` depende exclusivamente do campo persistido no MongoDB.

---

## 3. Login sem rate limiting / lockout (Alto) — Corrigido (`fea9d34`)

- `slowapi`: 5 req/min por IP em `/login` e `/forgot-password`.
- Contador por e-mail em Mongo (`auth_rate_limits`).
- Lockout após 6 tentativas falhas (15 min), com hash dummy anti timing-oracle.
- Mensagem genérica de credenciais inválidas.

---

## 4. Auto-registro sem verificação de e-mail (Médio) — Corrigido (`bfa9520`)

- Campo `email_verified: false` no registro; email de verificação via SMTP.
- Rotas `POST /api/auth/verify-email` e `POST /api/auth/resend-verification` (com rate limit).
- Rotas sensíveis (cursos, progresso, quiz, maturidade, admin) exigem `get_verified_user`.
- Usuários legados sem o campo são tratados como verificados (`email_verified is not False`).
- Usuários criados pelo admin recebem `email_verified: true`.

---

## 5. JWT em `localStorage` (Médio) — Corrigido (`a6b4c0a`)

- Cookie `HttpOnly`, `SameSite=Strict`, `Secure` em produção (`ENVIRONMENT=production`).
- `get_current_user` lê JWT do cookie (header `Authorization` mantido por compatibilidade).
- Rota `POST /api/auth/logout` limpa o cookie.
- Frontend usa `credentials: 'include'`; removido `localStorage` para token.

**Nota:** em produção, defina `ENVIRONMENT=production` no deploy para ativar `Secure` no cookie e desabilitar `/docs`.

---

## 6. Container root; documentação da API exposta (Médio) — Corrigido (`00b056d`)

- Dockerfile: usuário `appuser` + `USER appuser` antes do `CMD`.
- FastAPI: `docs_url`, `redoc_url` e `openapi_url` desabilitados quando `ENVIRONMENT=production`.

---

## 7. CSP com `unsafe-inline` (Baixo) — Corrigido (`69ff3ed`)

- Scripts inline de `lp.html` extraídos para `frontend-vue/public/lp.js`.
- CSP: `script-src 'self'` (sem `'unsafe-inline'`).
- Rota `GET /lp.js` no backend para servir o arquivo em dev e produção.

---

## 8. Injeção NoSQL — Sem ação necessária

Rotas usam Pydantic tipado; não passar payload bruto como filtro MongoDB em código novo.

---

## Deploy — checklist pós-correção

1. Definir `ENVIRONMENT=production` no ambiente de produção (DigitalOcean etc.).
2. Promover admin inicial: `python -m app.scripts.promote_admin --email admin@exemplo.com`
3. Configurar SMTP para emails de verificação e reset de senha.
4. Confirmar `CORS_ORIGINS` com a URL pública do frontend (cookie cross-origin exige origem explícita).
