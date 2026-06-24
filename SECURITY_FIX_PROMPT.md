Leia `SECURITY_AUDIT.md` na raiz deste repositório (AEGIS). Ele documenta 8 achados de uma auditoria de segurança. Implemente as correções abaixo, uma por uma, criando um commit por achado (não amend, não agrupar tudo em um commit só). Depois de cada correção, rode os testes existentes (se houver) e confirme que a aplicação ainda sobe (`docker compose up --build` ou o equivalente local) antes de seguir para o próximo item.

## 1. [Crítico] `PASSWORD_RESET_RETURN_TOKEN` vaza token de reset na API

- Em `backend/app/config.py`, remova completamente o campo `password_reset_return_token` (e a leitura da env var correspondente).
- Em `backend/app/routes/auth.py`, remova o bloco que retorna `reset_token` no corpo da resposta de `/forgot-password` (ou rota equivalente). A resposta deve sempre ser uma mensagem genérica, independentemente de o e-mail existir ou não (para não vazar quais e-mails estão cadastrados).
- Se existirem testes automatizados que dependiam de capturar o token via resposta da API, ajuste-os para capturar o token a partir do mock/stub da camada de envio de e-mail (`send_password_reset_email`) em vez da resposta HTTP.

## 2b. [Alto] Bootstrap de admin via `INITIAL_ADMIN_EMAIL`

- Em `backend/app/deps.py`, remova a lógica em `get_current_admin` que concede `is_admin = True` com base em `settings.initial_admin_email`. A autorização de admin deve depender exclusivamente do campo `is_admin` persistido no documento do usuário no MongoDB.
- Crie um script de migração/CLI único (ex.: `backend/app/scripts/promote_admin.py`) que recebe um e-mail como argumento e seta `is_admin: true` no documento correspondente no Mongo, para uso manual único de bootstrap.
- Remova `initial_admin_email` de `backend/app/config.py` e do `.env.example` depois de migrar o admin atual (se houver) usando o script novo.

## 3. [Alto] Sem rate limiting no login e no reset de senha

- Adicione a dependência `slowapi` (ou equivalente compatível com FastAPI) ao backend.
- Aplique rate limiting por IP e por e-mail nas rotas `/api/auth/login` e `/api/auth/forgot-password` (ex.: máximo de 5 tentativas por minuto por IP, e um limite adicional por conta).
- Implemente um contador de tentativas falhas de login persistido no MongoDB (campo no documento do usuário, ex. `failed_login_attempts` e `locked_until`), bloqueando temporariamente a conta após N tentativas falhas consecutivas (ex.: 6 tentativas → bloqueio de 15 minutos). Resete o contador em login bem-sucedido.
- Garanta que as mensagens de erro de login não revelem se o e-mail existe ou não, e que o tempo de resposta não varie de forma detectável entre "usuário não existe" e "senha errada" (evitar timing oracle).

## 4. [Médio] Auto-registro sem verificação de e-mail

- Adicione um campo `email_verified: bool = False` ao documento de usuário criado em `/register`.
- Gere um token de verificação (mesmo padrão usado no reset de senha, com expiração) e envie um e-mail de verificação via a infraestrutura SMTP já existente.
- Crie uma rota `/api/auth/verify-email` que valida o token e marca `email_verified: true`.
- Bloqueie (retornando 403 com mensagem clara) o acesso a rotas sensíveis (conteúdo de cursos, dashboard, rotas administrativas) para usuários com `email_verified: false`, mantendo o login funcional apenas para permitir reenvio de verificação.
- Adicione uma rota de reenvio de e-mail de verificação, também com rate limiting.

## 5. [Médio] JWT em `localStorage`

- No backend, ajuste a rota de login para, além de retornar o token no corpo (se necessário manter compatibilidade), também setar um cookie `HttpOnly`, `Secure`, `SameSite=Strict` contendo o JWT.
- No frontend (`frontend-vue/src/api/auth.ts` e `frontend-vue/src/api/client.ts`), remova o uso de `localStorage.setItem`/`getItem` para o token. Configure o cliente HTTP (axios/fetch) para enviar credenciais via cookie (`withCredentials: true` ou equivalente) em vez de montar manualmente o header `Authorization`.
- Implemente a rota de logout no backend para limpar o cookie (`Set-Cookie` com `Max-Age=0`).
- Ajuste o middleware/dependência de autenticação do backend (`get_current_user` em `deps.py`) para ler o JWT do cookie em vez de (ou além de) um header `Authorization`.

## 6. [Médio] Container roda como root; `/docs` exposto sem autenticação

- No `Dockerfile`, adicione a criação de um usuário não privilegiado (`RUN adduser --disabled-password --gecos '' appuser`) e a diretiva `USER appuser` antes do `CMD`, garantindo que os arquivos da aplicação tenham permissão de leitura para esse usuário.
- Em `backend/app/main.py`, configure a instância do FastAPI para desabilitar `/docs`, `/redoc` e `/openapi.json` quando uma variável de ambiente de produção estiver ativa (ex.: `ENVIRONMENT=production` → `docs_url=None, redoc_url=None, openapi_url=None`), mantendo-os habilitados em desenvolvimento/local.

## 7. [Baixo] CSP com `script-src 'unsafe-inline'`

- Em `backend/app/main.py`, remova `'unsafe-inline'` de `script-src` na Content-Security-Policy.
- Caso existam scripts inline necessários no frontend, migre-os para arquivos externos ou implemente nonces gerados por requisição e propague o nonce para o header CSP.
- Após a mudança, verifique manualmente (abrindo a aplicação no navegador e checando o console) que nenhum script legítimo está sendo bloqueado.

## 8. Sem ação necessária

- Não foi encontrado vetor de injeção NoSQL (rotas usam Pydantic tipado). Não é necessário alterar nada relacionado a este item, apenas mantenha esse padrão (nunca passar `request.json()`/`payload.dict()` bruto direto como filtro do MongoDB) em código novo.

## Critério de conclusão

Ao final, atualize `SECURITY_AUDIT.md` marcando cada achado como "Corrigido" com a referência do commit correspondente, e me avise quais itens (se algum) não puderam ser totalmente resolvidos e por quê.
