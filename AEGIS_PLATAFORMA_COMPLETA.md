# Valorian 4 Future (AEGIS) — Documentação Consolidada da Plataforma

**Produto:** Plataforma de mentoria executiva em Inteligência Artificial  
**Repositório:** AEGIS  
**Gerado em:** 2026-06-24  
**Origem:** Consolidação do Spec Kit (`.specify/`, `specs/`), README, implementação no código e auditoria de segurança

> Este documento único reúne constitution, especificações brownfield, feature specs, planos, contratos, tarefas e o **estado atual da implementação** (incluindo hardening de segurança pós-auditoria). Onde specs antigas divergem do código, prevalece a seção **Implementação Atual**.

---

## Índice

### Índice do documento

1. [Visão geral](#1-visão-geral)
2. [Constitution (Spec Kit)](#2-constitution-spec-kit)
3. [Baseline brownfield — `001-aegis-baseline`](#3-baseline-brownfield--001-aegis-baseline)
4. [**Requisitos funcionais por módulo**](#4-requisitos-funcionais-por-módulo-implementação) ← detalhamento do código
5. [Feature — Reset de senha na UI (`002-reset-senha-ui`)](#5-feature--reset-de-senha-na-ui-002-reset-senha-ui)
6. [Implementação técnica atual](#6-implementação-técnica-atual)
7. [API — referência de endpoints](#7-api--referência-de-endpoints)
8. [Frontend — rotas e componentes](#8-frontend--rotas-e-componentes)
9. [Modelo de dados MongoDB](#9-modelo-de-dados-mongodb)
10. [Autenticação, sessão e segurança](#10-autenticação-sessão-e-segurança)
11. [Deploy e operação](#11-deploy-e-operação)
12. [Spec Kit — workflow de desenvolvimento](#12-spec-kit--workflow-de-desenvolvimento)
13. [Apêndices](#13-apêndices)

### Índice de módulos, funcionalidades e requisitos (Seção 4)

**Total:** 9 módulos · 30 funcionalidades · 140 requisitos `MOD-*`

- **[M1 — Autenticação e Identidade](#m1)** (30 requisitos)
  - [Cadastro de usuário](#m1-cadastro)
    - [MOD-AUTH-001](#mod-auth-001) — Permitir auto-cadastro com nome, email e senha
    - [MOD-AUTH-002](#mod-auth-002) — Após cadastro: criar usuário com `email_verified: false`
    - [MOD-AUTH-003](#mod-auth-003) — Cadastro autenticar imediatamente (cookie + token no corpo)
    - [MOD-AUTH-004](#mod-auth-004) — Email duplicado retornar 409
  - [Login e logout](#m1-login)
    - [MOD-AUTH-010](#mod-auth-010) — Autenticar por email/senha
    - [MOD-AUTH-011](#mod-auth-011) — Login bem-sucedido emitir JWT e cookie HttpOnly
    - [MOD-AUTH-012](#mod-auth-012) — Login resetar contador de falhas e remover lockout
    - [MOD-AUTH-013](#mod-auth-013) — Logout invalidar sessão no cliente
    - [MOD-AUTH-014](#mod-auth-014) — Credenciais inválidas retornar mensagem genérica
    - [MOD-AUTH-015](#mod-auth-015) — Após 6 falhas consecutivas, conta bloquear por 15 min
    - [MOD-AUTH-016](#mod-auth-016) — Tentativas com email inexistente usar hash dummy
    - [MOD-AUTH-017](#mod-auth-017) — Login ter rate limit 5 req/min por IP
  - [Sessão e perfil](#m1-sessao)
    - [MOD-AUTH-020](#mod-auth-020) — JWT ser lido do cookie `access_token` ou header Bearer
    - [MOD-AUTH-021](#mod-auth-021) — `GET /me` retornar perfil + trilhas do aluno
    - [MOD-AUTH-022](#mod-auth-022) — Resposta de perfil incluir `email_verified`
    - [MOD-AUTH-023](#mod-auth-023) — Token expirado ou inválido retornar 401
  - [Verificação de email](#m1-verify)
    - [MOD-AUTH-030](#mod-auth-030) — Registro enviar link de verificação por email
    - [MOD-AUTH-031](#mod-auth-031) — `POST /verify-email` validar token e marcar `email_verified: true`
    - [MOD-AUTH-032](#mod-auth-032) — Usuário autenticado poder reenviar email de verificação
    - [MOD-AUTH-033](#mod-auth-033) — Rotas sensíveis bloquear usuário não verificado
    - [MOD-AUTH-034](#mod-auth-034) — Usuários criados pelo admin nascer verificados
    - [MOD-AUTH-035](#mod-auth-035) — Link de verificação apontar para `/login?verify_token=...`
  - [Recuperação de senha](#m1-reset)
    - [MOD-AUTH-040](#mod-auth-040) — Usuário solicitar reset informando email
    - [MOD-AUTH-041](#mod-auth-041) — Reset invalidar tokens anteriores ativos do mesmo usuário
    - [MOD-AUTH-042](#mod-auth-042) — Token expirar (default 30 min) e ser single-use
    - [MOD-AUTH-043](#mod-auth-043) — Email conter link `/login?reset_token=...` e token alternativo
    - [MOD-AUTH-044](#mod-auth-044) — `POST /reset-password` atualizar senha e marcar token usado
    - [MOD-AUTH-045](#mod-auth-045) — API NOT retornar token de reset no corpo HTTP
    - [MOD-AUTH-046](#mod-auth-046) — UI oferecer fluxo login → forgot → reset no AuthOverlay
    - [MOD-AUTH-047](#mod-auth-047) — Forgot-password ter rate limit 5/min por IP + email

- **[M2 — Trilhas (Curso)](#m2)** (14 requisitos)
  - [Conteúdo de trilhas](#m2-conteudo)
    - [MOD-COURSE-001](#mod-course-001) — Conteúdo ser persistido em `courses` no MongoDB
    - [MOD-COURSE-002](#mod-course-002) — Na primeira subida, fazer seed de `trilha-ia-executiva` se vazio
    - [MOD-COURSE-003](#mod-course-003) — Cada trilha ter `slug` único
    - [MOD-COURSE-004](#mod-course-004) — Jornada organizar encontros por semana
    - [MOD-COURSE-005](#mod-course-005) — Payload de trilha limitar tamanho (max 2 MiB JSON)
  - [Acesso do aluno à trilha](#m2-acesso)
    - [MOD-COURSE-010](#mod-course-010) — Aluno verificado consultar trilha atual
    - [MOD-COURSE-011](#mod-course-011) — Aluno poder selecionar trilha via `?course_slug=`
    - [MOD-COURSE-012](#mod-course-012) — Trilha omitida usar trilha principal do usuário
    - [MOD-COURSE-013](#mod-course-013) — Resposta incluir progresso completo + metadados de quiz
    - [MOD-COURSE-014](#mod-course-014) — Progress ser criado automaticamente se inexistente
    - [MOD-COURSE-015](#mod-course-015) — Resposta calcular `concluidos_efetivos` e `ativo_efetivo`
  - [Vitrine pública](#m2-vitrine)
    - [MOD-COURSE-020](#mod-course-020) — Visitante listar trilhas sem autenticação
    - [MOD-COURSE-021](#mod-course-021) — Visitante ver detalhe completo por slug
    - [MOD-COURSE-022](#mod-course-022) — SPA exibir vitrine em `/trilhas` e `/trilhas/:slug`

- **[M3 — Progresso do Aluno](#m3)** (18 requisitos)
  - [Marcação de materiais](#m3-materiais)
    - [MOD-PROG-001](#mod-prog-001) — Aluno marcar/desmarcar materiais de apoio por encontro
    - [MOD-PROG-002](#mod-prog-002) — Índice de material ser válido para o encontro
    - [MOD-PROG-003](#mod-prog-003) — Marcação registrar timestamp UTC por material
    - [MOD-PROG-004](#mod-prog-004) — Marcar materiais recalcular encontros liberados automaticamente
  - [Regras de liberação de encontros](#m3-liberacao)
    - [MOD-PROG-010](#mod-prog-010) — Primeiro encontro estar sempre liberado
    - [MOD-PROG-011](#mod-prog-011) — Próximo encontro liberar quando **todos** materiais do anterior estivere…
    - [MOD-PROG-012](#mod-prog-012) — Admin poder liberar encontro manualmente (sem regra de materiais)
    - [MOD-PROG-013](#mod-prog-013) — Liberações admin e automáticas coexistir (união de conjuntos)
  - [Conclusão de encontros](#m3-conclusao)
    - [MOD-PROG-020](#mod-prog-020) — Aluno concluir apenas o encontro **ativo** atual
    - [MOD-PROG-021](#mod-prog-021) — Conclusão exigir encontro liberado
    - [MOD-PROG-022](#mod-prog-022) — Conclusão exigir 100% dos materiais marcados
    - [MOD-PROG-023](#mod-prog-023) — Conclusão registrar data em `encontro_conclusoes`
    - [MOD-PROG-024](#mod-prog-024) — Conclusão avançar `ativo` para próximo encontro
    - [MOD-PROG-025](#mod-prog-025) — Conclusão auto-liberar próximo encontro na sequência
    - [MOD-PROG-026](#mod-prog-026) — Re-conclusão de encontro já concluído ser idempotente
  - [Agenda de encontros](#m3-agenda)
    - [MOD-PROG-030](#mod-prog-030) — Admin definir datas por encontro (`encontro_agendas`)
    - [MOD-PROG-031](#mod-prog-031) — Aluno visualizar agenda na view `/agenda`
    - [MOD-PROG-032](#mod-prog-032) — Dashboard admin ordenar alunos por próximo encontro

- **[M4 — Quiz](#m4)** (15 requisitos)
  - [Acesso e listagem](#m4-acesso)
    - [MOD-QUIZ-001](#mod-quiz-001) — Quiz estar associado a um `encontro` (unique index)
    - [MOD-QUIZ-002](#mod-quiz-002) — Aluno listar todos os quizzes com status de resposta
    - [MOD-QUIZ-003](#mod-quiz-003) — Acesso ao quiz exigir encontro liberado e ≤ ativo
    - [MOD-QUIZ-004](#mod-quiz-004) — Quiz ser obtido por encontro_id ou por ObjectId (`quiz_id`)
  - [Modos de entrega de questões](#m4-modos)
    - [MOD-QUIZ-010](#mod-quiz-010) — Quiz completo omitir respostas corretas e racionais
    - [MOD-QUIZ-011](#mod-quiz-011) — Parâmetro `batch=N` retornar N questões não respondidas
    - [MOD-QUIZ-012](#mod-quiz-012) — Modo `review=true` incluir racionais das questões respondidas
    - [MOD-QUIZ-013](#mod-quiz-013) — `rationales_for=1,2,3` retornar racionais de IDs específicos
  - [Envio e pontuação](#m4-envio)
    - [MOD-QUIZ-020](#mod-quiz-020) — Aluno enviar respostas incrementalmente (merge)
    - [MOD-QUIZ-021](#mod-quiz-021) — Resposta inválida (índice fora das opções) retornar 400
    - [MOD-QUIZ-022](#mod-quiz-022) — Sistema calcular feedback por questão
    - [MOD-QUIZ-023](#mod-quiz-023) — `submitted_at` ser setado quando todas questões respondidas
    - [MOD-QUIZ-024](#mod-quiz-024) — Resposta incluir score da sessão atual
    - [MOD-QUIZ-025](#mod-quiz-025) — Aluno consultar resposta existente
    - [MOD-QUIZ-026](#mod-quiz-026) — Conclusão de encontro NOT exigir quiz respondido

- **[M5 — Maturidade em IA](#m5)** (10 requisitos)
  - [Modelo de diagnóstico](#m5-modelo)
    - [MOD-MAT-001](#mod-mat-001) — Modelo ser carregado da coleção `ai_maturity_model`
    - [MOD-MAT-002](#mod-mat-002) — Modelo conter `dimensions` com questions
    - [MOD-MAT-003](#mod-mat-003) — Modelo definir `scoring` por abrangência com faixas min/max → nível
    - [MOD-MAT-004](#mod-mat-004) — Escala de resposta ser 1–5 por questão
  - [Autoavaliação](#m5-autoavaliacao)
    - [MOD-MAT-010](#mod-mat-010) — Aluno responder **todas** as questões do modelo
    - [MOD-MAT-011](#mod-mat-011) — Sistema calcular score total, percentual e por dimensão
    - [MOD-MAT-012](#mod-mat-012) — Aluno poder ter **múltiplas** autoavaliações
    - [MOD-MAT-013](#mod-mat-013) — Histórico filtrar por `model_version` ativa
    - [MOD-MAT-014](#mod-mat-014) — Aluno consultar detalhe de avaliação anterior
    - [MOD-MAT-015](#mod-mat-015) — Apenas dono da resposta acessar detalhe

- **[M6 — Área Pública e Landing](#m6)** (8 requisitos)
  - [Landing page](#m6-landing)
    - [MOD-PUB-001](#mod-pub-001) — Raiz `/` servir landing `lp.html`
    - [MOD-PUB-002](#mod-pub-002) — Landing capturar leads via formulário de aplicação
    - [MOD-PUB-003](#mod-pub-003) — Formulário validar captcha aritmético (soma)
    - [MOD-PUB-004](#mod-pub-004) — Lead ser persistido com timestamp UTC
    - [MOD-PUB-005](#mod-pub-005) — Scripts ser externos (`/lp.js`) por CSP
    - [MOD-PUB-006](#mod-pub-006) — Landing expor SEO (robots.txt, sitemap.xml, meta description)
  - [Integração landing ↔ SPA](#m6-integracao)
    - [MOD-PUB-010](#mod-pub-010) — Link "Entrar" respeitar `loginBase` query param
    - [MOD-PUB-011](#mod-pub-011) — API de leads aceitar `apiBase` query param

- **[M7 — Administração](#m7)** (19 requisitos)
  - [Dashboard operacional](#m7-dashboard)
    - [MOD-ADM-001](#mod-adm-001) — Admin ver dashboard com todos os alunos não-admin
    - [MOD-ADM-002](#mod-adm-002) — Dashboard mostrar progresso por trilha principal
    - [MOD-ADM-003](#mod-adm-003) — Dashboard ordenar por data do próximo encontro
  - [Gestão de usuários](#m7-usuarios)
    - [MOD-ADM-010](#mod-adm-010) — Admin criar usuário com 1+ trilhas
    - [MOD-ADM-011](#mod-adm-011) — Usuário criado nascer com email verificado
    - [MOD-ADM-012](#mod-adm-012) — Admin listar, editar e excluir usuários
    - [MOD-ADM-013](#mod-adm-013) — Admin NOT excluir a si mesmo
    - [MOD-ADM-014](#mod-adm-014) — Exclusão cascatear progress, quiz_responses, maturity_responses
    - [MOD-ADM-015](#mod-adm-015) — Admin visualizar curso+progresso de aluno
    - [MOD-ADM-016](#mod-adm-016) — Promoção a admin ser via CLI (bootstrap único)
  - [Gestão de trilhas](#m7-trilhas)
    - [MOD-ADM-020](#mod-adm-020) — Admin CRUD trilhas (courses)
    - [MOD-ADM-021](#mod-adm-021) — Update de trilha sincronizar `quiz_id` nos encontros
    - [MOD-ADM-022](#mod-adm-022) — Delete de trilha remover documento
  - [Gestão de progresso](#m7-progresso)
    - [MOD-ADM-030](#mod-adm-030) — Admin liberar encontro específico para aluno
    - [MOD-ADM-031](#mod-adm-031) — Admin atualizar agendas de encontros por trilha
  - [Gestão de quiz (admin)](#m7-quiz)
    - [MOD-ADM-040](#mod-adm-040) — Admin listar quizzes agrupados por trilha
    - [MOD-ADM-041](#mod-adm-041) — Admin CRUD quiz por encontro
    - [MOD-ADM-042](#mod-adm-042) — Criar/atualizar quiz propagar `quiz_id` em todas trilhas
    - [MOD-ADM-043](#mod-adm-043) — Admin sincronizar quiz_ids em massa

- **[M8 — Plataforma e Segurança](#m8)** (13 requisitos)
  - [Infraestrutura](#m8-infra)
    - [MOD-PLAT-001](#mod-plat-001) — App expor health check com ping MongoDB
    - [MOD-PLAT-002](#mod-plat-002) — Produção servir SPA de `frontend-vue/dist`
    - [MOD-PLAT-003](#mod-plat-003) — Container rodar como usuário não-root
    - [MOD-PLAT-004](#mod-plat-004) — Startup falhar sem MONGODB_URI e JWT_SECRET_KEY
    - [MOD-PLAT-005](#mod-plat-005) — Índices Mongo ser criados no startup
  - [Segurança HTTP](#m8-seguranca)
    - [MOD-SEC-001](#mod-sec-001) — Responses incluir CSP, HSTS, X-Frame-Options, etc.
    - [MOD-SEC-002](#mod-sec-002) — `/docs`, `/redoc`, `/openapi.json` desabilitar em production
    - [MOD-SEC-003](#mod-sec-003) — CORS restringir origens explícitas com credentials
    - [MOD-SEC-004](#mod-sec-004) — Filtros Mongo usar campos tipados Pydantic
    - [MOD-SEC-005](#mod-sec-005) — Rate limits persistir contadores com TTL 1h
  - [Email transacional](#m8-email)
    - [MOD-SEC-010](#mod-sec-010) — Sistema enviar email reset se SMTP configurado
    - [MOD-SEC-011](#mod-sec-011) — Sistema enviar email verificação no registro/resend
    - [MOD-SEC-012](#mod-sec-012) — Links usar `APP_BASE_URL` configurável

- **[M9 — Interface (SPA Vue 3)](#m9)** (13 requisitos)
  - [Autenticação na UI](#m9-auth-ui)
    - [MOD-UI-001](#mod-ui-001) — Login usar cookie HttpOnly (sem localStorage)
    - [MOD-UI-002](#mod-ui-002) — AuthOverlay gerenciar login, forgot, reset e verify
    - [MOD-UI-003](#mod-ui-003) — Usuário não verificado ver mensagem e botão reenviar
    - [MOD-UI-004](#mod-ui-004) — Logout chamar API e limpar store
  - [Navegação e guards](#m9-navegacao)
    - [MOD-UI-010](#mod-ui-010) — Rotas protegidas exigir login
    - [MOD-UI-011](#mod-ui-011) — Rotas admin exigir is_admin
    - [MOD-UI-012](#mod-ui-012) — Aluno logado verificado em `/` ir para /programa
    - [MOD-UI-013](#mod-ui-013) — Aluno com múltiplas trilhas selecionar trilha ativa
  - [Views principais](#m9-views)
    - [MOD-UI-020](#mod-ui-020) — `/programa` exibir jornada com progresso visual
    - [MOD-UI-021](#mod-ui-021) — `/materiais` listar materiais por encontro
    - [MOD-UI-022](#mod-ui-022) — `/quiz/:encontroId` suportar modo batch e review
    - [MOD-UI-023](#mod-ui-023) — `/ai-maturity` listar histórico e permitir nova avaliação
    - [MOD-UI-024](#mod-ui-024) — `/admin/*` cobrir dashboard, usuários, trilhas, progresso, quiz

---

## 1. Visão geral

### 1.1 Propósito

AEGIS (Valorian 4 Future) é uma plataforma web de mentoria executiva que entrega:

- **Trilhas de formação** com encontros, materiais e progresso rastreado
- **Quiz** por encontro
- **AI Maturity Model** — autoavaliação de maturidade em IA com histórico
- **Área administrativa** para gestão de alunos, trilhas, progresso e quiz
- **Landing pública** com vitrine de trilhas e captura de leads

### 1.2 Stack

| Camada | Tecnologia |
|--------|------------|
| API | FastAPI, PyMongo, python-jose, passlib/bcrypt, slowapi |
| Banco | MongoDB (Atlas ou local) |
| SPA | Vue 3, TypeScript, Vite, Pinia, Vue Router |
| Deploy | Docker (frontend build + uvicorn no mesmo container) |
| Email | SMTP genérico (reset de senha, verificação de email) |

### 1.3 Estrutura do repositório

| Caminho | Descrição |
|---------|-----------|
| `backend/` | API FastAPI |
| `backend/app/routes/` | Rotas REST |
| `backend/app/schemas.py` | Schemas Pydantic |
| `backend/app/deps.py` | Dependências de auth |
| `backend/app/security.py` | JWT, hash de senha, tokens |
| `backend/data/course.json` | Seed da trilha padrão |
| `backend/app/scripts/promote_admin.py` | CLI bootstrap de admin |
| `frontend-vue/` | SPA Vue 3 |
| `frontend-vue/public/lp.html` | Landing page estática |
| `frontend-vue/public/lp.js` | Scripts da landing (CSP-safe) |
| `specs/` | Especificações Spec Kit por feature |
| `.specify/memory/constitution.md` | Constitution do projeto |
| `util/create_user.py` | Script legado de criação de usuário |
| `Dockerfile` / `docker-compose.yml` | Build e deploy |

---

## 2. Constitution (Spec Kit)

**Versão:** 1.0.0 | **Ratified:** 2026-06-24

### Princípios

| # | Princípio | Resumo |
|---|-----------|--------|
| I | Brownfield First | Estender FastAPI + MongoDB + Vue 3; refatorações amplas só quando solicitadas |
| II | Mudanças Mínimas | Menor diff correto; reutilizar padrões existentes |
| III | Segurança por Padrão | JWT, senhas com hash, tokens de reset só em hash, auth não enumera emails |
| IV | API e Contratos Explícitos | REST `/api/*`, schemas em `schemas.py`, clientes em `frontend-vue/src/api/` |
| V | MongoDB como Fonte de Verdade | Trilhas, progresso, quiz e maturidade no banco |
| VI | Deploy Unificado | Vue em `dist/` servido pelo uvicorn; health em `/api/health` |
| VII | Qualidade Pragmática | Validação manual documentada; testes só quando agregam valor |

### Workflow Spec Kit

1. Uma feature = branch `NNN-nome-curto` + diretório em `specs/`
2. Fluxo: `/speckit-specify` → `/speckit-clarify` → `/speckit-plan` → `/speckit-tasks` → `/speckit-analyze` → `/speckit-implement`
3. Specs = **o quê/por quê**; planos = **como**
4. Atualizar README apenas quando setup/deploy/operação mudarem

---

## 3. Baseline brownfield — `001-aegis-baseline`

**Branch:** `main` (documentação de estado)  
**Status:** Accepted (baseline)  
**Criado:** 2026-06-24

### User Stories

#### US1 — Aluno acessa trilha e progride (P1)

Como aluno autenticado, quero acessar minha trilha, marcar materiais e concluir encontros.

**Teste independente:** Login → `/programa` → marcar material → concluir encontro → progresso persistido.

**Cenários de aceite:**

1. Aluno com trilha atribuída acessa programa com encontros liberados conforme regras.
2. Marcar materiais e concluir encontro salva em `progress`.
3. Quiz associado registra resposta em `quiz_responses`.

#### US2 — Diagnóstico de maturidade em IA (P1)

Como aluno, quero responder o questionário de maturidade e consultar histórico.

**Teste independente:** Login → `/ai-maturity` → nova autoavaliação → resultado com score → histórico.

**Cenários de aceite:**

1. Modelo em `ai_maturity_model` exibe dimensões e perguntas.
2. Respostas válidas (1–5) geram score total, por dimensão e nível.
3. Histórico ordenado por data.

#### US3 — Admin gerencia alunos e conteúdo (P2)

Como administrador, quero gerenciar usuários, trilhas, progresso e quiz.

**Teste independente:** Login admin → `/admin` → CRUD → liberar encontro.

**Cenários de aceite:**

1. Usuário com `is_admin: true` acessa dashboard admin. *(Atualizado: não usa mais `INITIAL_ADMIN_EMAIL`.)*
2. Admin atualiza trilhas/progresso → reflete na experiência do aluno.
3. Admin configura quiz → aluno responde na trilha.

#### US4 — Visitante explora trilhas e deixa lead (P3)

Como visitante, quero ver trilhas e registrar interesse.

**Teste independente:** Landing/trilhas sem login → catálogo → submeter lead.

### Requisitos funcionais (baseline)

Os FRs de alto nível do baseline (`FR-001` a `FR-009`) estão **detalhados por módulo na [Seção 4](#4-requisitos-funcionais-por-módulo-implementação)**, com regras de negócio, validações e referências ao código implementado.

| ID baseline | Módulo detalhado |
|-------------|------------------|
| FR-001 | [M1 — Autenticação e Identidade](#m1--autenticação-e-identidade) |
| FR-002 | [M1.4 — Recuperação de senha](#funcionalidade-recuperação-de-senha) |
| FR-003 | [M3 — Progresso do Aluno](#m3--progresso-do-aluno) |
| FR-004 | [M2 — Trilhas (Curso)](#m2--trilhas-curso) |
| FR-005, FR-006 | [M5 — Maturidade em IA](#m5--maturidade-em-ia) |
| FR-007 | [M7 — Administração](#m7--administração) |
| FR-008 | [M8 — Plataforma e Segurança](#m8--plataforma-e-segurança) |
| FR-009 | [M9 — Interface (SPA)](#m9--interface-spa-vue-3) |

### Entidades principais

| Entidade | Campos / uso |
|----------|--------------|
| **User** | name, email, password_hash, is_admin, email_verified, course_slugs |
| **Course** | slug, programa_formacao_executiva (jornada, encontros) |
| **Progress** | user_id, course_slug, concluidos, materiais, agendas, encontros_liberados |
| **Quiz / QuizResponse** | questionário por encontro; respostas do aluno |
| **AiMaturityModel** | version, levels (abrangência), dimensions, scoring por tier |
| **MaturityResponse** | respostas e resultado calculado |
| **Lead** | contato da landing |
| **PasswordReset** | token_hash, expires_at, used_at |
| **EmailVerification** | token_hash, expires_at, used_at *(pós-segurança)* |
| **AuthRateLimit** | contadores por email/IP *(pós-segurança)* |

### Critérios de sucesso

- SC-001: Login e acesso ao programa em ≤ 3 interações
- SC-002: Progresso persiste entre sessões
- SC-003: Autoavaliação consistente com modelo no banco
- SC-004: Admin cria usuário e libera encontro sem Mongo manual
- SC-005: Deploy Docker com health check OK

### Edge cases

- Aluno sem trilha: programa vazio ou orientação
- JWT expirado: redirecionamento para login
- Modelo maturidade ausente: erro de serviço
- MongoDB inacessível: health 503
- Email não verificado: bloqueio de rotas sensíveis *(pós-segurança)*

---

## 4. Requisitos funcionais por módulo (implementação)

Documentação derivada do código em `backend/app/routes/`, `backend/app/deps.py`, `backend/app/schemas.py` e `frontend-vue/src/`. Cada requisito inclui **regras de negócio**, **códigos HTTP**, **defaults de config** e **referência técnica** validados contra a implementação atual.

**Última revisão contra código:** 2026-06-24

**Convenção de IDs:** `MOD-{Módulo}-{seq}` (ex.: `MOD-AUTH-003`).

**Níveis de acesso:**

| Dependência | Escopo |
|-------------|--------|
| Público | Sem autenticação |
| Autenticado | Cookie JWT válido (`get_current_user`) |
| Verificado | Autenticado + `email_verified !== false` (`get_verified_user`) |
| Admin | Verificado + `is_admin: true` (`get_current_admin`) |

---

<a id="m1"></a>
### M1 — Autenticação e Identidade

**Rotas:** `/api/auth/*` · **Arquivos:** `routes/auth.py`, `deps.py`, `security.py`, `utils/login_lockout.py`, `utils/auth_cookie.py`, `utils/email_verification.py`, `utils/rate_limit.py`, `utils/email.py`

**Acesso:** cadastro/login/logout/forgot/reset/verify-email = **Público**; `/me` e `/resend-verification` = **Autenticado**

<a id="m1-cadastro"></a>
#### Funcionalidade: Cadastro de usuário

| ID | Requisito | Regras de negócio | Referência |
|----|-----------|-------------------|------------|
| <span id="mod-auth-001">MOD-AUTH-001</span> | O sistema MUST permitir auto-cadastro com nome, email e senha | `RegisterRequest`: nome 2–120 chars (`strip`); email `EmailStr` normalizado `lower()`; senha 6–128 chars. Hash novo via `pbkdf2_sha256` (`passlib`); verificação aceita hashes bcrypt legados (`$2a$`/`$2b$`/`$2y$`). Senhas >72 bytes pré-hash SHA-256 antes do bcrypt. Persiste `created_at` UTC. Não atribui trilha nem `is_admin`. | `POST /register`, `schemas.RegisterRequest`, `security.hash_password` |
| <span id="mod-auth-002">MOD-AUTH-002</span> | Após cadastro, MUST criar usuário com `email_verified: false` | Campo explícito no insert. Em seguida chama `issue_and_send_verification()`: gera token, grava hash em `email_verifications`, dispara SMTP. Se SMTP ausente (`smtp_host`+`user`+`password`), cadastro **não falha** — apenas log warning. | `auth.py:register`, `email_verification.issue_and_send_verification` |
| <span id="mod-auth-003">MOD-AUTH-003</span> | Cadastro MUST autenticar imediatamente (cookie + token no corpo) | Resposta `AuthResponse`: `access_token`, `token_type: bearer`, `user` com `_user_payload`. JWT HS256, claim `sub`=ObjectId string, exp default **480 min** (`JWT_EXPIRE_MINUTES`). Cookie `access_token` HttpOnly setado via `set_auth_cookie`. | `create_access_token`, `set_auth_cookie`, `auth.py:register` |
| <span id="mod-auth-004">MOD-AUTH-004</span> | Email duplicado MUST retornar 409 | `find_one({"email": lower})` antes do insert. Body: `{"detail": "Email ja cadastrado"}`. | `auth.py:register` L51–53 |

<a id="m1-login"></a>
#### Funcionalidade: Login e logout

| ID | Requisito | Regras de negócio | Referência |
|----|-----------|-------------------|------------|
| <span id="mod-auth-010">MOD-AUTH-010</span> | O sistema MUST autenticar por email/senha | Fluxo: `enforce_email_rate_limit` → `authenticate_login`. Email `strip().lower()`. Senha validada com `verify_password` (pbkdf2 ou bcrypt legado). | `POST /login`, `login_lockout.authenticate_login` |
| <span id="mod-auth-011">MOD-AUTH-011</span> | Login bem-sucedido MUST emitir JWT e cookie HttpOnly | Cookie: nome `access_token`, `path=/`, `SameSite=strict`, `HttpOnly=true`, `max_age=jwt_expire_minutes×60`. `Secure=true` somente se `ENVIRONMENT=production` (case-insensitive). Corpo JSON repete token + `_user_payload` (inclui `email_verified`). | `utils/auth_cookie.py`, `auth.py:login` |
| <span id="mod-auth-012">MOD-AUTH-012</span> | Login MUST resetar contador de falhas e remover lockout | `$set: failed_login_attempts=0`; `$unset: locked_until`. Executado apenas após senha válida. | `login_lockout.py` L58–64 |
| <span id="mod-auth-013">MOD-AUTH-013</span> | Logout MUST invalidar sessão no cliente | `POST /logout` sem auth obrigatória. `clear_auth_cookie`: mesmo nome/atributos com `value=""`, `max_age=0`. Resposta: `{"message": "Logout realizado."}`. Frontend chama API e zera Pinia store. | `auth.py:logout`, `Topbar.vue`, `AdminLayout.vue` |
| <span id="mod-auth-014">MOD-AUTH-014</span> | Credenciais inválidas MUST retornar mensagem genérica | HTTP **401**, detail fixo `"Credenciais invalidas"` — mesmo texto para email inexistente ou senha errada. Incrementa `failed_login_attempts` só se usuário existir. | `login_lockout.py` L43–56 |
| <span id="mod-auth-015">MOD-AUTH-015</span> | Após 6 falhas consecutivas, conta MUST bloquear por 15 min | Constantes: `MAX_FAILED_LOGIN_ATTEMPTS=6`, `LOGIN_LOCKOUT_MINUTES=15`. No 6º erro: `$set locked_until = now+15min`. Tentativa durante lock: HTTP **429**, `"Conta temporariamente bloqueada. Tente novamente em alguns minutos."` | `login_lockout.py` L13–14, L34–38, L50–51 |
| <span id="mod-auth-016">MOD-AUTH-016</span> | Tentativas com email inexistente MUST usar hash dummy | Se `user` é None, `verify_password` roda contra `_DUMMY_PASSWORD_HASH` (bcrypt fixo). Mesmo caminho de código que falha real, sem incrementar contador (usuário não existe). | `login_lockout.py` L40–41 |
| <span id="mod-auth-017">MOD-AUTH-017</span> | Login MUST ter rate limit 5 req/min por IP | `@limiter.limit("5/minute")` (slowapi, por IP). **Adicional:** `enforce_email_rate_limit(db, email, "login")` — max **5** eventos/email/scope em janela **1 min**; HTTP **429** `"Muitas tentativas. Aguarde um momento e tente novamente."`; insert em `auth_rate_limits`. | `auth.py:login`, `rate_limit.py` |

<a id="m1-sessao"></a>
#### Funcionalidade: Sessão e perfil

| ID | Requisito | Regras de negócio | Referência |
|----|-----------|-------------------|------------|
| <span id="mod-auth-020">MOD-AUTH-020</span> | JWT MUST ser lido do cookie `access_token` ou header Bearer | Ordem: `request.cookies.get("access_token")` **primeiro**; se ausente, `Authorization: Bearer` via `HTTPBearer(auto_error=False)`. JWT decode com `JWT_SECRET_KEY` UTF-8 bytes; algoritmo default HS256. Erros: 401 `"Nao autenticado"` / `"Token invalido"` / `"Usuario nao encontrado"`. | `deps.get_current_user` |
| <span id="mod-auth-021">MOD-AUTH-021</span> | `GET /me` MUST retornar perfil + trilhas do aluno | Campos: `id`, `name`, `email`, `is_admin`, `email_verified`, `course_slugs`. Slugs = união ordenada (`dict.fromkeys`): slugs distintos em `progress` **+** `user.course_slugs` ou `[course_slug]`. Requer auth (não exige email verificado). | `auth.py:me` |
| <span id="mod-auth-022">MOD-AUTH-022</span> | Resposta de perfil MUST incluir `email_verified` | `is_email_verified(user)`: retorna `True` se campo ausente (legado) ou `True` explícito; `False` apenas se `email_verified is False`. | `deps.is_email_verified`, `_user_payload` |
| <span id="mod-auth-023">MOD-AUTH-023</span> | Token expirado ou inválido MUST retornar 401 | Backend rejeita JWT expirado/inválido. Frontend `loadUser()` chama `/me` com `credentials: include`; em erro zera `user`, `currentCourseSlug`, marca `loaded=true` (sem redirect automático). Guards tratam `isLoggedIn=false`. | `deps.py`, `stores/auth.ts:loadUser` |

<a id="m1-verify"></a>
#### Funcionalidade: Verificação de email

| ID | Requisito | Regras de negócio | Referência |
|----|-----------|-------------------|------------|
| <span id="mod-auth-030">MOD-AUTH-030</span> | Registro MUST enviar link de verificação por email | Token: `secrets.token_urlsafe(48)`; hash SHA-256 hex em `email_verifications.token_hash` (unique index). Expiração: `EMAIL_VERIFICATION_EXPIRE_MINUTES` default **1440** (24h); TTL index Mongo em `expires_at`. Tokens anteriores não usados invalidados com `used_at` + `invalidated_reason: replaced_by_new_request`. Link: `{APP_BASE_URL}/login?verify_token=...` (URL-encoded). | `email_verification.py`, `config.email_verification_expire_minutes` |
| <span id="mod-auth-031">MOD-AUTH-031</span> | `POST /verify-email` MUST validar token e marcar `email_verified: true` | Body: `{token}` min 20 / max 512 chars. Público (sem cookie). Busca doc com `token_hash`, `used_at=null`, `expires_at > now`. Sucesso: `$set email_verified=true, updated_at`; marca token `used_at`. Falha: HTTP **400** `"Token inválido ou expirado"`. Sucesso: `{"message": "Email confirmado com sucesso."}`. | `auth.py:verify_email`, `verify_email_token()` |
| <span id="mod-auth-032">MOD-AUTH-032</span> | Usuário autenticado MUST poder reenviar email de verificação | Requer cookie/Bearer (`get_current_user`). Rate limit slowapi 5/min IP + `enforce_email_rate_limit(..., "resend_verification")`. Se já verificado: **200** `"Seu email já está confirmado."` (não reenvia). Caso contrário: reemite token e responde `"Enviamos um novo link de confirmação para o seu email."`. | `POST /resend-verification` |
| <span id="mod-auth-033">MOD-AUTH-033</span> | Rotas sensíveis MUST bloquear usuário não verificado | `get_verified_user` encadeado após `get_current_user`. HTTP **403**: `"Confirme seu email antes de acessar este recurso."`. Aplica a: `/api/course`, `/api/progress`, `/api/quiz`, `/api/maturity`, `/api/admin`. **Não** bloqueia `/api/auth/me` nem `/resend-verification`. | `deps.get_verified_user` |
| <span id="mod-auth-034">MOD-AUTH-034</span> | Usuários criados pelo admin MUST nascer verificados | `POST /admin/users` seta `email_verified: true` no `user_doc`. Bootstrap CLI `promote_admin.py` também seta `email_verified: true` + `is_admin: true`. | `admin.py:create_user`, `scripts/promote_admin.py` |
| <span id="mod-auth-035">MOD-AUTH-035</span> | Link de verificação MUST apontar para `/login?verify_token=...` | Frontend `AuthOverlay`: ao abrir overlay lê query `verify_token`, chama `POST /verify-email`, remove query da URL, exibe sucesso/erro na view login. Se já logado, atualiza `authStore.user.email_verified=true`. | `email.py:_build_verify_link`, `AuthOverlay.vue:handleVerifyTokenFromQuery` |

<a id="m1-reset"></a>
#### Funcionalidade: Recuperação de senha

| ID | Requisito | Regras de negócio | Referência |
|----|-----------|-------------------|------------|
| <span id="mod-auth-040">MOD-AUTH-040</span> | Usuário MUST solicitar reset informando email | Body `{email: EmailStr}`. Se email **não** existe: retorna **200** com mensagem genérica (mesmo JSON). Se existe: gera token, persiste, envia email. Mensagem fixa: `"Se o email existir, enviaremos instruções para reset de senha."` | `POST /forgot-password` |
| <span id="mod-auth-041">MOD-AUTH-041</span> | Reset MUST invalidar tokens anteriores ativos do mesmo usuário | `update_many` em `password_resets` com `user_id` + `used_at=null` → `used_at=now`, `invalidated_reason: replaced_by_new_request`. | `auth.py:forgot_password` L143–147 |
| <span id="mod-auth-042">MOD-AUTH-042</span> | Token MUST expirar (default 30 min) e ser single-use | Token opaco `token_urlsafe(48)`; só hash SHA-256 persistido. `expires_at = now + PASSWORD_RESET_EXPIRE_MINUTES` (default **30**). TTL index Mongo em `expires_at`. Uso: `used_at` setado no reset bem-sucedido. | `password_resets`, `config.password_reset_expire_minutes` |
| <span id="mod-auth-043">MOD-AUTH-043</span> | Email MUST conter link `/login?reset_token=...` e token alternativo | Template HTML/text (`email_templates.py`): botão + URL fallback + bloco "Token alternativo" para tela Nova senha. Assunto: `"Recuperação de senha — Valorian 4 Future"`. SMTP: TLS default porta 587 ou SSL (`SMTP_USE_SSL`). | `send_password_reset_email`, `render_password_reset_*` |
| <span id="mod-auth-044">MOD-AUTH-044</span> | `POST /reset-password` MUST atualizar senha e marcar token usado | Body: `token` (20–512), `new_password` (6–128). Valida hash+expiração+`used_at=null`. Atualiza `users.password_hash` + `updated_at`; marca reset `used_at`. Sucesso: `"Senha atualizada com sucesso."`; falha: **400** token inválido/expirado. | `POST /reset-password`, `ResetPasswordRequest` |
| <span id="mod-auth-045">MOD-AUTH-045</span> | API MUST NOT retornar token de reset no corpo HTTP | Resposta forgot-password contém **somente** `{message}`. Campo `reset_token` removido de schema e frontend. Token obtido exclusivamente via email (ou suporte manual). | commit `d7bee91`, `GenericMessageResponse` |
| <span id="mod-auth-046">MOD-AUTH-046</span> | UI MUST oferecer fluxo login → forgot → reset no AuthOverlay | Views: `login \| forgot \| reset`. Links: "Esqueci minha senha", "Voltar ao login", "Já tenho o token", "Solicitar novo token". Query `?reset_token=` abre view reset e limpa URL. Validação cliente: email com `@`, senha ≥6, confirmação igual. Enter submete forms. Overlay reopen → `resetOverlayState()`. Rota dedicada: `/login` via `LoginView.vue`. | `AuthOverlay.vue` |
| <span id="mod-auth-047">MOD-AUTH-047</span> | Forgot-password MUST ter rate limit 5/min por IP + email | `@limiter.limit("5/minute")` + `enforce_email_rate_limit(..., "forgot_password")` — mesma janela/contagem do login. | `auth.py:forgot_password` |

---

<a id="m2"></a>
### M2 — Trilhas (Curso)

**Rotas:** `/api/course/*`, `/api/public/courses*` · **Arquivos:** `routes/course.py`, `routes/public.py`, `utils/course_payload.py`, `main.py` (seed)

**Acesso:** `/api/course/current` = **Verificado**; `/api/public/*` = **Público**

<a id="m2-conteudo"></a>
#### Funcionalidade: Conteúdo de trilhas

| ID | Requisito | Regras de negócio | Referência |
|----|-----------|-------------------|------------|
| <span id="mod-course-001">MOD-COURSE-001</span> | Conteúdo MUST ser persistido em `courses` no MongoDB | Documento: `{slug, programa_formacao_executiva}`. PFE inclui `cabecalho`, `visao_geral`, `jornada_aprendizagem[]` → semanas → `encontros[]` com `id`, `titulo`, `objetivos`, `material_suporte[]`, `quiz_id` opcional (ObjectId). | coleção `courses` |
| <span id="mod-course-002">MOD-COURSE-002</span> | Na primeira subida, MUST fazer seed de `trilha-ia-executiva` se vazio | `startup`: se `db.courses.find_one({slug: COURSE_SLUG})` ausente, lê `backend/data/course.json` e `insert_one`. Constante `COURSE_SLUG = "trilha-ia-executiva"`. | `main.seed_course_if_needed()` |
| <span id="mod-course-003">MOD-COURSE-003</span> | Cada trilha MUST ter `slug` único | Index `courses.slug` unique. Admin create rejeita slug duplicado (**400**). | `database.init_indexes`, `admin.create_course` |
| <span id="mod-course-004">MOD-COURSE-004</span> | Jornada MUST organizar encontros por semana | Cada semana: `tema_central`, `encontros[]`. Materiais: `{item, url}`. IDs de encontro usados em progresso, quiz e liberação — ordem definida pela sequência na jornada (não necessariamente id=1). | `course.json`, schema trilha |
| <span id="mod-course-005">MOD-COURSE-005</span> | Payload de trilha MUST limitar tamanho (max 2 MiB JSON) | Validador Pydantic serializa JSON UTF-8; se > **2 MiB** → `ValueError` → 422. Aplica em `AdminCreateCourseRequest` e `AdminUpdateCourseRequest`. | `schemas._check_payload_size` |

<a id="m2-acesso"></a>
#### Funcionalidade: Acesso do aluno à trilha

| ID | Requisito | Regras de negócio | Referência |
|----|-----------|-------------------|------------|
| <span id="mod-course-010">MOD-COURSE-010</span> | Aluno verificado MUST consultar trilha atual | `GET /api/course/current`. Depende `get_verified_user`. Trilha inexistente → **404** `"Curso nao encontrado"`. | `course.py:get_current_course` |
| <span id="mod-course-011">MOD-COURSE-011</span> | Aluno MUST poder selecionar trilha via `?course_slug=` | Query opcional. `_user_has_course`: true se slug == `user.course_slug`, ∈ `course_slugs`, ou existe doc em `progress`. Caso contrário **403** `"Voce nao tem acesso a esta trilha"`. | `_user_has_course()` |
| <span id="mod-course-012">MOD-COURSE-012</span> | Trilha omitida MUST usar trilha principal do usuário | Fallback: `user.course_slug` → `user.course_slugs[0]` → `COURSE_SLUG` (`trilha-ia-executiva`). Mesma lógica em progress/quiz via `_resolve_course_slug`. | `get_current_course`, `progress._resolve_course_slug` |
| <span id="mod-course-013">MOD-COURSE-013</span> | Resposta MUST incluir progresso completo + metadados de quiz | JSON: `course_slug`, `programa_formacao_executiva` (ObjectIds → string via `payload_for_json`), `progress` com: `concluidos`, `ativo`, `total`, `concluidos_efetivos`, `ativo_efetivo`, `encontros_liberados`, `material_checks`, `encontro_conclusoes`, `encontro_agendas`, `quiz_por_encontro` (por id: `tem_quiz`, `respondido`). | `course.py` return L130–145 |
| <span id="mod-course-014">MOD-COURSE-014</span> | Progress MUST ser criado automaticamente se inexistente | `_get_or_create_progress`: insert com `concluidos=[]`, `ativo=1`, `total` calculado, `encontros_liberados=[1]`, `material_checks={}`, `encontro_conclusoes={}`, `updated_at`. Index unique `(user_id, course_slug)`. Patch legacy docs sem `material_checks`/`encontro_conclusoes`. | `_get_or_create_progress()` |
| <span id="mod-course-015">MOD-COURSE-015</span> | Resposta MUST calcular `concluidos_efetivos` e `ativo_efetivo` | Percorre ids na ordem da jornada: `concluidos_efetivos` = ids presentes em `progress.concluidos`; `ativo_efetivo` = primeiro id **não** concluído; se todos concluídos → `max(ids)+1`. **Nota:** quiz respondido **não** altera conclusão (nome da função é legado). | `_progress_with_quiz_effect()` |

<a id="m2-vitrine"></a>
#### Funcionalidade: Vitrine pública

| ID | Requisito | Regras de negócio | Referência |
|----|-----------|-------------------|------------|
| <span id="mod-course-020">MOD-COURSE-020</span> | Visitante MUST listar trilhas sem autenticação | `GET /api/public/courses`. Para cada doc: `_course_summary` → `slug`, `titulo`, `tema`, `trilha`, `publico`, `objetivo`, `num_semanas` (len jornada), `num_encontros` (soma encontros). | `public.list_courses_public` |
| <span id="mod-course-021">MOD-COURSE-021</span> | Visitante MUST ver detalhe completo por slug | `GET /api/public/courses/{slug}`. Retorna `{slug, programa_formacao_executiva}` integral. Slug inexistente → **404**. | `public.get_course_public` |
| <span id="mod-course-022">MOD-COURSE-022</span> | SPA MUST exibir vitrine em `/trilhas` e `/trilhas/:slug` | Rotas Vue **sem** guard de auth (`TrilhasView`, `TrilhaShowcaseView`). Consomem API pública. | `router/index.ts` |

---

<a id="m3"></a>
### M3 — Progresso do Aluno

**Rotas:** `/api/progress/*` · **Arquivos:** `routes/progress.py`, `utils/progress_liberados.py`, `routes/course.py` (liberação na leitura)

**Acesso:** **Verificado** · Index unique: `(user_id, course_slug)`

<a id="m3-materiais"></a>
#### Funcionalidade: Marcação de materiais

| ID | Requisito | Regras de negócio | Referência |
|----|-----------|-------------------|------------|
| <span id="mod-prog-001">MOD-PROG-001</span> | Aluno MUST marcar/desmarcar materiais de apoio por encontro | `POST /api/progress/material`. Body: `encontro_id` (int), `material_index` (int), `checked` (bool), `course_slug` opcional. Resolve trilha via `_resolve_course_slug`. Resposta serializada com timestamps ISO em `material_checks`. | `MaterialCheckRequest`, `update_material_check` |
| <span id="mod-prog-002">MOD-PROG-002</span> | Índice de material MUST ser válido para o encontro | `find_encontro(payload, encontro_id)` obrigatório; senão **400** `"Encontro invalido"`. Índice 0-based; deve ser `< len(material_suporte)` senão **400** `"Material invalido"`. | `progress.py` L82–88 |
| <span id="mod-prog-003">MOD-PROG-003</span> | Marcação MUST registrar timestamp UTC por material | Estrutura aninhada: `material_checks[str(encontro_id)][str(material_index)] = datetime UTC`. Desmarcar: remove chave; se dict vazio remove encontro. | `progress.material_checks` |
| <span id="mod-prog-004">MOD-PROG-004</span> | Marcar materiais MUST recalcular encontros liberados automaticamente | Após update: `liberados = sorted(recompute_liberados ∪ encontros_liberados_existentes)`. Upsert em `progress` preserva `concluidos`, `ativo`, `total`, `encontro_conclusoes`. Também recalculado em `GET /course/current` se divergir do stored. | `recompute_liberados()`, `course.py` L108–116 |

<a id="m3-liberacao"></a>
#### Funcionalidade: Regras de liberação de encontros

| ID | Requisito | Regras de negócio | Referência |
|----|-----------|-------------------|------------|
| <span id="mod-prog-010">MOD-PROG-010</span> | Primeiro encontro MUST estar sempre liberado | `recompute_liberados`: `ordered = sorted(ids da jornada)`; `liberados = [ordered[0]]`. Se jornada vazia, fallback `[1]`. Progress inicial: `encontros_liberados: [1]`. | `progress_liberados.py` L20–25 |
| <span id="mod-prog-011">MOD-PROG-011</span> | Próximo encontro MUST liberar quando **todos** materiais do anterior estiverem marcados | Para cada par consecutivo na ordem: se `len(checks[prev_id]) >= len(material_suporte)` do encontro anterior, adiciona próximo id; senão **para** a cadeia. Encontro **sem** materiais libera o seguinte imediatamente. | `recompute_liberados()` L26–35 |
| <span id="mod-prog-012">MOD-PROG-012</span> | Admin MUST poder liberar encontro manualmente (sem regra de materiais) | `POST /api/admin/users/{id}/liberar-encontro` body `{encontro_id}`. Usa **`user.course_slug`** (trilha principal, não query multi-trilha). Valida id contra max id da jornada. Append id se ausente. | `admin.liberar_encontro` |
| <span id="mod-prog-013">MOD-PROG-013</span> | Liberações admin e automáticas MUST coexistir (união de conjuntos) | Set union antes de persistir: `liberados_regra \| liberados_existentes`. Admin nunca remove liberações automáticas já concedidas. | `progress.py` L107–109, `course.py` L109–111 |

<a id="m3-conclusao"></a>
#### Funcionalidade: Conclusão de encontros

| ID | Requisito | Regras de negócio | Referência |
|----|-----------|-------------------|------------|
| <span id="mod-prog-020">MOD-PROG-020</span> | Aluno MUST concluir apenas o encontro **ativo** atual | `POST /api/progress/complete/{encontro_id}`. Rejeita se `encontro_id != progress.ativo` → **400** `"Conclua o encontro ativo primeiro"`. Valida range `1..max_id` da jornada. | `complete_encontro` L154–155 |
| <span id="mod-prog-021">MOD-PROG-021</span> | Conclusão MUST exigir encontro liberado | Se `encontro_id not in encontros_liberados` → **403** `"Este encontro ainda nao foi liberado para voce. Aguarde a liberacao pelo administrador."` | `complete_encontro` L157–162 |
| <span id="mod-prog-022">MOD-PROG-022</span> | Conclusão MUST exigir 100% dos materiais marcados | Compara `len(material_checks[str(id)])` vs `len(material_suporte)` do encontro. Incompleto → **400** `"Marque todos os materiais antes de concluir"`. | `complete_encontro` L168–171 |
| <span id="mod-prog-023">MOD-PROG-023</span> | Conclusão MUST registrar data em `encontro_conclusoes` | `encontro_conclusoes[str(encontro_id)] = now UTC`. Serializado ISO na resposta via `_serialize_progress`. | `complete_encontro` L176–177 |
| <span id="mod-prog-024">MOD-PROG-024</span> | Conclusão MUST avançar `ativo` para próximo encontro | `novo_ativo = min(encontro_id + 1, progress.total)`. `concluidos` append + sort. | `complete_encontro` L173–187 |
| <span id="mod-prog-025">MOD-PROG-025</span> | Conclusão MUST auto-liberar próximo encontro na sequência | Se `encontro_id + 1 <= total` e ainda não liberado, append a `encontros_liberados` e sort. | `complete_encontro` L179–184 |
| <span id="mod-prog-026">MOD-PROG-026</span> | Re-conclusão de encontro já concluído MUST ser idempotente | Se `encontro_id in progress.concluidos`: retorna `_serialize_progress` atual **sem** mutação (HTTP 200). | `complete_encontro` L151–152 |

<a id="m3-agenda"></a>
#### Funcionalidade: Agenda de encontros

| ID | Requisito | Regras de negócio | Referência |
|----|-----------|-------------------|------------|
| <span id="mod-prog-030">MOD-PROG-030</span> | Admin MUST definir datas por encontro (`encontro_agendas`) | Mapa `encontro_id (string) → ISO datetime string`. Definido em: create user (`encontro_agendas` só na **primeira** trilha do loop `i==0`), update user (`encontro_agendas` na trilha principal), ou `PATCH /admin/users/{id}/progress` com `course_slug` explícito. Chaves normalizadas para string no PATCH. | `AdminCreateUserRequest`, `AdminUpdateProgressRequest`, `admin.update_user` |
| <span id="mod-prog-031">MOD-PROG-031</span> | Aluno MUST visualizar agenda na view `/agenda` | Consome `encontro_agendas` retornado em `GET /api/course/current` dentro de `progress`. Rota protegida (auth + email verificado). | `AgendaView.vue`, `course.py` |
| <span id="mod-prog-032">MOD-PROG-032</span> | Dashboard admin MUST ordenar alunos por próximo encontro | Para cada aluno: `next_iso = encontro_agendas.get(str(ativo))`; parse ISO → timestamp `_next_ts`. Sort key `(ts is None, ts)` — **sem data vai ao final**. Retorna também métricas agregadas de materiais/quiz/maturidade. | `admin.get_dashboard` L176–206 |

---

<a id="m4"></a>
### M4 — Quiz

**Rotas:** `/api/quiz/*` · **Arquivos:** `routes/quiz.py`, coleções `quiz`, `quiz_responses`

**Acesso:** **Verificado** · Index unique: `quiz.encontro`, `(user_id, encontro)` em responses

<a id="m4-acesso"></a>
#### Funcionalidade: Acesso e listagem

| ID | Requisito | Regras de negócio | Referência |
|----|-----------|-------------------|------------|
| <span id="mod-quiz-001">MOD-QUIZ-001</span> | Quiz MUST estar associado a um `encontro` (unique index) | Um documento por `encontro` int. Admin upsert via `update_one({encontro}, upsert=True)`. Questões: `{id, pergunta, hint?, opcoes[{text, rationale?, isCorrect?}]}`. | `database.init_indexes`, `admin.create_or_update_quiz` |
| <span id="mod-quiz-002">MOD-QUIZ-002</span> | Aluno MUST listar todos os quizzes com status de resposta | `GET /api/quiz?course_slug=`. Retorna `{items[], ativo, encontros_liberados}`. Por quiz: `encontro`, `titulo`, `total` (qtd questões), `total_answered`, `score`, `submitted_at` ISO, `quiz_id` se existir. Ordenado por `encontro`. | `list_my_quiz_responses` |
| <span id="mod-quiz-003">MOD-QUIZ-003</span> | Acesso ao quiz MUST exigir encontro liberado e ≤ ativo | Condição de bloqueio: `encontro_id > progress.ativo` **OU** `encontro_id not in encontros_liberados` → **403** com mensagem indicando concluir/liberar encontro. Default `ativo=1`, `liberados=[1]` se progress ausente. | `_get_quiz_impl` L96–100 |
| <span id="mod-quiz-004">MOD-QUIZ-004</span> | Quiz MUST ser obtido por encontro_id ou por ObjectId (`quiz_id`) | `GET /api/quiz/{encontro_id}` ou `GET /api/quiz/by-id/{quiz_id}`. Segundo resolve `quiz.encontro` e delega mesma lógica. ObjectId inválido → **404**. Query params compartilhados: `batch`, `review`, `rationales_for`, `course_slug`. | `get_quiz`, `get_quiz_by_id` |

<a id="m4-modos"></a>
#### Funcionalidade: Modos de entrega de questões

| ID | Requisito | Regras de negócio | Referência |
|----|-----------|-------------------|------------|
| <span id="mod-quiz-010">MOD-QUIZ-010</span> | Quiz completo MUST omitir respostas corretas e racionais | `_sanitize_quiz_doc`: opções expõem `{index, text}` apenas. Questões incluem `id`, `pergunta`, `hint`. | default GET sem flags |
| <span id="mod-quiz-011">MOD-QUIZ-011</span> | Parâmetro `batch=N` MUST retornar N questões não respondidas | Filtra questões cujo `str(id)` ∉ `existing_answers`; retorna primeiras N. Se vazio: `{questoes: [], all_answered: true}`. `N` ignorado se ≤0 (cai no modo completo). | `?batch=` L117–127 |
| <span id="mod-quiz-012">MOD-QUIZ-012</span> | Modo `review=true` MUST incluir racionais das questões respondidas | Exige resposta prévia; senão **403** `"Responda ao menos uma questao..."`. Se todas respondidas → quiz completo com racionais; senão só questões já respondidas. Opções incluem `rationale`, `isCorrect`. | `?review=true` L110–116 |
| <span id="mod-quiz-013">MOD-QUIZ-013</span> | `rationales_for=1,2,3` MUST retornar racionais de IDs específicos | Parse CSV → set de ints; filtra questões por `q.id`. Sempre `include_rationales=True`. Útil para feedback imediato pós-submit parcial. | `?rationales_for=` L105–109 |

<a id="m4-envio"></a>
#### Funcionalidade: Envio e pontuação

| ID | Requisito | Regras de negócio | Referência |
|----|-----------|-------------------|------------|
| <span id="mod-quiz-020">MOD-QUIZ-020</span> | Aluno MUST enviar respostas incrementalmente (merge) | `POST /api/quiz/{encontro_id}/submit` body `{answers: {qid: selected_index}}`. Merge em doc existente (`upsert`). Ignora qids desconhecidos; índice inválido → **400**. | `submit_quiz` L238–245 |
| <span id="mod-quiz-021">MOD-QUIZ-021</span> | Resposta inválida (índice fora das opções) MUST retornar 400 | Valida `0 <= selected < len(opcoes)` por questão enviada. | `submit_quiz` L243–244 |
| <span id="mod-quiz-022">MOD-QUIZ-022</span> | Sistema MUST calcular feedback por questão | Por resposta: `is_correct` (opção `isCorrect===true`), `rationale` da opção escolhida, `selected_index`, `correct_index`. Score global = contagem de corretas em **todas** answers acumuladas. | `_compute_feedback_for_answers` |
| <span id="mod-quiz-023">MOD-QUIZ-023</span> | `submitted_at` MUST ser setado quando todas questões respondidas | Quando `len(existing_answers) >= total_questoes`: `submitted_at=now UTC`. Se parcial, mantém `submitted_at` anterior se existia, senão null. | `submit_quiz` L252–255 |
| <span id="mod-quiz-024">MOD-QUIZ-024</span> | Resposta MUST incluir score da sessão atual | Retorno inclui `session_correct`/`session_total` calculados **apenas** sobre `payload.answers` deste request (batch). Também retorna `score`, `total`, `total_answered`, `feedback` mergeado, `submitted_at` ISO. | `submit_quiz` L257–288 |
| <span id="mod-quiz-025">MOD-QUIZ-025</span> | Aluno MUST consultar resposta existente | `GET /api/quiz/{encontro_id}/my-response`. Mesmas regras de liberação. Sem doc: `{answers:{}, score:null, ...}`. Com doc: answers, score, total, feedback, submitted_at. | `get_my_quiz_response` |
| <span id="mod-quiz-026">MOD-QUIZ-026</span> | Conclusão de encontro MUST NOT exigir quiz respondido | `_progress_with_quiz_effect` só olha `progress.concluidos`; quiz é paralelo ao fluxo de conclusão. Metadados `quiz_por_encontro` são informativos na UI. | `course._progress_with_quiz_effect` |

---

<a id="m5"></a>
### M5 — Maturidade em IA

**Rotas:** `/api/maturity/*` · **Arquivos:** `routes/maturity.py`, coleções `ai_maturity_model`, `maturity_responses`

**Acesso:** **Verificado**

<a id="m5-modelo"></a>
#### Funcionalidade: Modelo de diagnóstico

| ID | Requisito | Regras de negócio | Referência |
|----|-----------|-------------------|------------|
| <span id="mod-mat-001">MOD-MAT-001</span> | Modelo MUST ser carregado da coleção `ai_maturity_model` | `find_one(sort=[("_id", -1)])` — documento mais recente. Seed inicial opcional via JSON em `backend/data/`. | `_load_model()` |
| <span id="mod-mat-002">MOD-MAT-002</span> | Modelo MUST conter `dimensions` com questions | Coleção vazia → **503** `"Modelo de maturidade nao configurado"`. Se `dimensions` ausente/vazio → **503** `"Modelo de maturidade invalido"`. | `GET /api/maturity/model` |
| <span id="mod-mat-003">MOD-MAT-003</span> | Modelo MUST definir `scoring` por abrangência com faixas min/max → nível | Usa `scoring[tier]`; primeira faixa onde `min <= total_score <= max` define `level`. | `_score_submission()` |
| <span id="mod-mat-004">MOD-MAT-004</span> | Escala de resposta MUST ser 1–5 por questão | Valores `<1` ou `>5` tratados como 0 no cálculo; no submit **todas** questões obrigatórias com valor 1–5 senão **400** `"Resposta invalida para {qid}"`. | `save_my_response`, `_score_submission` |

<a id="m5-autoavaliacao"></a>
#### Funcionalidade: Autoavaliação

| ID | Requisito | Regras de negócio | Referência |
|----|-----------|-------------------|------------|
| <span id="mod-mat-010">MOD-MAT-010</span> | Aluno MUST responder **todas** as questões do modelo | Conjunto `all_questions` = união de `q.id` em todas dimensions. Payload deve conter cada id; ausência → valor 0 → rejeitado no submit. | `save_my_response` L131–140 |
| <span id="mod-mat-011">MOD-MAT-011</span> | Sistema MUST calcular score total, percentual e por dimensão | Por questão: `dim_score += value * weight` (default weight=1); `dim_max += 5 * weight`. `percent_score = round(total_score/max_score*100, 2)`. Por dimensão: `avg = dim_score/question_count` arredondado 2 casas. | `_score_submission()` |
| <span id="mod-mat-012">MOD-MAT-012</span> | Aluno MUST poder ter **múltiplas** autoavaliações | Index `(user_id, submitted_at desc)` — **sem** unique por versão (índice antigo unique removido no startup). Cada submit = novo documento. | `maturity_responses`, `init_indexes` |
| <span id="mod-mat-013">MOD-MAT-013</span> | Histórico MUST filtrar por `model_version` ativa | `GET /my-responses`: filtra `model_version == model.version` do doc ativo. Sort `submitted_at` desc. Resumo por item: id, submitted_at, total_score, max_score, percent_score, level, dimension_scores. | `list_my_responses` |
| <span id="mod-mat-014">MOD-MAT-014</span> | Aluno MUST consultar detalhe de avaliação anterior | `GET /my-responses/{response_id}`. Retorna `answers` completas + `result` + `submitted_at`. ObjectId inválido → **404**. | `get_my_response_by_id` |
| <span id="mod-mat-015">MOD-MAT-015</span> | Apenas dono da resposta MUST acessar detalhe | Query `{"_id": oid, "user_id": user._id}`. Documento de outro usuário → **404** (não 403, para não vazar existência). | `get_my_response_by_id` L114 |

---

<a id="m6"></a>
### M6 — Área Pública e Landing

**Rotas:** `/api/public/*`, `/`, `/lp.js`, `/robots.txt`, `/sitemap.xml` · **Arquivos:** `routes/public.py`, `public/lp.html`, `public/lp.js`, `main.py`

**Acesso:** **Público**

<a id="m6-landing"></a>
#### Funcionalidade: Landing page

| ID | Requisito | Regras de negócio | Referência |
|----|-----------|-------------------|------------|
| <span id="mod-pub-001">MOD-PUB-001</span> | Raiz `/` MUST servir landing `lp.html` | Prioridade: `frontend-vue/dist/lp.html` → `public/lp.html` → fallback SPA index. Headers `no-cache`. Conteúdo: programa 9 encontros, framework V.A.L.O.R., formulário de aplicação, navbar com scroll/reveal animations via `lp.js`. | `main.py:_landing()`, `root()` |
| <span id="mod-pub-002">MOD-PUB-002</span> | Landing MUST capturar leads via formulário de aplicação | Campos POST: `nome_completo`, `cargo`, `empresa`, `faturamento_anual`, `email`, `contexto_ia` (opcional), `num1`, `num2`, `captcha_answer`. Frontend valida captcha antes do fetch; backend revalida. | `LeadCreate`, `lp.js:handleSubmit` |
| <span id="mod-pub-003">MOD-PUB-003</span> | Formulário MUST validar captcha aritmético (soma) | Frontend: `answer === n1+n2` senão alert + `refreshCaptcha()`. Backend: **400** se `num1+num2 != captcha_answer`. Números gerados 0–9 client-side; reenviados no payload para validação server-side. | `public.create_lead`, `lp.js:refreshCaptcha` |
| <span id="mod-pub-004">MOD-PUB-004</span> | Lead MUST ser persistido com timestamp UTC | Doc: campos strip/lower no email, `created_at` UTC. Resposta **200**: `{ok: true, message: "Aplicação recebida. Entraremos em contato em até 24 horas úteis."}`. Index `leads.created_at`. | `POST /api/public/leads` |
| <span id="mod-pub-005">MOD-PUB-005</span> | Scripts MUST ser externos (`/lp.js`) por CSP | `<script src="/lp.js" defer>` — sem inline. CSP backend: `script-src 'self'`. Rota dedicada `GET /lp.js` serve de dist ou public. | `main.py:lp_js`, `SECURITY_HEADERS` |
| <span id="mod-pub-006">MOD-PUB-006</span> | Landing MUST expor SEO (robots.txt, sitemap.xml, meta description) | `GET /robots.txt`, `GET /sitemap.xml` via `_public_static_file`. Meta `description` + `canonical` no `<head>` de `lp.html`. | `main.py`, `lp.html` |

<a id="m6-integracao"></a>
#### Funcionalidade: Integração landing ↔ SPA

| ID | Requisito | Regras de negócio | Referência |
|----|-----------|-------------------|------------|
| <span id="mod-pub-010">MOD-PUB-010</span> | Link "Entrar" MUST respeitar `loginBase` query param | Se `?loginBase=https://host` presente: `a.href = loginBase + '/login'`, `target='_top'`. Usado quando landing em iframe/cross-origin. | `lp.js` IIFE nav-login |
| <span id="mod-pub-011">MOD-PUB-011</span> | API de leads MUST aceitar `apiBase` query param | `leadsApiUrl()`: se `?apiBase=` → POST para `{apiBase}/api/public/leads`; senão same-origin `/api/public/leads`. Permite landing estática apontar para backend remoto. | `lp.js:leadsApiUrl()` |

---

<a id="m7"></a>
### M7 — Administração

**Rotas:** `/api/admin/*`, `/admin/*` · **Arquivos:** `routes/admin.py`, `views/admin/*`

**Acesso:** **Admin** (`get_current_admin` = verificado + `is_admin: true`)

<a id="m7-dashboard"></a>
#### Funcionalidade: Dashboard operacional

| ID | Requisito | Regras de negócio | Referência |
|----|-----------|-------------------|------------|
| <span id="mod-adm-001">MOD-ADM-001</span> | Admin MUST ver dashboard com todos os alunos não-admin | Query users: `$or: [{is_admin: {$ne: true}}, {is_admin: {$exists: false}}]`. Por aluno: id, name, email, phone, course_slug/titulo, encontros_done/total, material_checked/total, quiz_done/total (global quiz count), maturity_done (0 ou 1), next_meeting_iso. | `GET /api/admin/dashboard` |
| <span id="mod-adm-002">MOD-ADM-002</span> | Dashboard MUST mostrar progresso por trilha principal | Usa primeira slug de `course_slugs` ou `course_slug`; progress lookup `(user_id, primary_slug)`. Materiais totais somados de todos encontros da trilha via `_get_total_materiais`. | `get_dashboard` L152–170 |
| <span id="mod-adm-003">MOD-ADM-003</span> | Dashboard MUST ordenar por data do próximo encontro | Parse ISO de `encontro_agendas[str(ativo)]` → timestamp; sort key `(ts is None, ts)` — alunos **com** data primeiro (ascendente = mais próximo no topo); sem data (`None`) **por último**. Campo interno `_next_ts` removido antes do return. | `get_dashboard` L204–206 |

<a id="m7-usuarios"></a>
#### Funcionalidade: Gestão de usuários

| ID | Requisito | Regras de negócio | Referência |
|----|-----------|-------------------|------------|
| <span id="mod-adm-010">MOD-ADM-010</span> | Admin MUST criar usuário com 1+ trilhas | Valida cada slug existe em `courses`. Cria `user` + um doc `progress` **por trilha** (concluidos=[], ativo=1, total encontros, liberados=[1]). `course_slug` = primeiro slug; `course_slugs` = lista completa. Retorna `user_id`, email, course_slugs. | `POST /api/admin/users` |
| <span id="mod-adm-011">MOD-ADM-011</span> | Usuário criado MUST nascer com email verificado | `email_verified: true` no insert (provisionamento confiável). Senha hasheada; phone opcional strip. | `admin.create_user` L238 |
| <span id="mod-adm-012">MOD-ADM-012</span> | Admin MUST listar, editar e excluir usuários | **GET** lista todos (inclui admins) com id, slugs, is_admin, created_at ISO. **PUT** parcial: name, email (unique check), password (se non-empty), course_slugs (cria progress faltante), phone, is_admin, encontro_agendas. **DELETE** remove user + dados relacionados. | `/api/admin/users` |
| <span id="mod-adm-013">MOD-ADM-013</span> | Admin MUST NOT excluir a si mesmo | Compara `uid == admin["_id"]` → **400** `"Nao e possivel excluir seu proprio usuario"`. | `delete_user` L423–427 |
| <span id="mod-adm-014">MOD-ADM-014</span> | Exclusão MUST cascatear progress, quiz_responses, maturity_responses | `delete_many` nas três coleções por `user_id` após `users.delete_one`. Não remove tokens reset/verify nem leads. | `delete_user` L432–435 |
| <span id="mod-adm-015">MOD-ADM-015</span> | Admin MUST visualizar curso+progresso de aluno | `GET /users/{id}/course-and-progress?course_slug=`. Retorna user resumo, PFE JSON-safe, `materiais_por_encontro`, `quiz_por_encontro` (tem_quiz, respondido, score, total), progress completo com efetivos. Progress default se ausente. | `get_user_course_and_progress` |
| <span id="mod-adm-016">MOD-ADM-016</span> | Promoção a admin MUST ser via CLI (bootstrap único) | `python -m app.scripts.promote_admin --email X` (cwd `backend/`). `update_one` por email: `is_admin=true`, `email_verified=true`, `updated_at`. Exit 1 se email não encontrado. **Não** existe flag env de admin. | `scripts/promote_admin.py` |

<a id="m7-trilhas"></a>
#### Funcionalidade: Gestão de trilhas

| ID | Requisito | Regras de negócio | Referência |
|----|-----------|-------------------|------------|
| <span id="mod-adm-020">MOD-ADM-020</span> | Admin MUST CRUD trilhas (courses) | **GET** list/detail. **POST** `{slug, programa_formacao_executiva}` slug strip, unique. **PUT** substitui PFE com `_fill_quiz_ids_in_payload`. **DELETE** remove doc (progress órfão permanece). | `/api/admin/courses` |
| <span id="mod-adm-021">MOD-ADM-021</span> | Update de trilha MUST sincronizar `quiz_id` nos encontros | Para cada encontro id na jornada: lookup `quiz.find_one({encontro})` → set `enc.quiz_id` ObjectId ou remove key. | `_fill_quiz_ids_in_payload()` |
| <span id="mod-adm-022">MOD-ADM-022</span> | Delete de trilha MUST remover documento | `delete_one({slug})`; **404** se nada deletado. Não cascade progress/quiz_responses. | `DELETE /courses/{slug}` |

<a id="m7-progresso"></a>
#### Funcionalidade: Gestão de progresso

| ID | Requisito | Regras de negócio | Referência |
|----|-----------|-------------------|------------|
| <span id="mod-adm-030">MOD-ADM-030</span> | Admin MUST liberar encontro específico para aluno | Body `{encontro_id}`. Opera na trilha **`user.course_slug`** (limitação atual para multi-trilha). Cria progress default se ausente. Append id a liberados se needed. | `POST .../liberar-encontro` |
| <span id="mod-adm-031">MOD-ADM-031</span> | Admin MUST atualizar agendas de encontros por trilha | `PATCH /users/{id}/progress` body `{course_slug, encontro_agendas}`. Exige progress existente (**404** se não). Normaliza keys string; ignora valores vazios. | `update_user_progress` |

<a id="m7-quiz"></a>
#### Funcionalidade: Gestão de quiz (admin)

| ID | Requisito | Regras de negócio | Referência |
|----|-----------|-------------------|------------|
| <span id="mod-adm-040">MOD-ADM-040</span> | Admin MUST listar quizzes agrupados por trilha | Retorno `{grouped: [{course_slug, titulo, quizzes[]}]}` ordenado por titulo trilha. Quizzes cujo encontro não pertence a nenhuma trilha → grupo `"Sem trilha"` (`course_slug: null`). | `GET /api/admin/quiz` |
| <span id="mod-adm-041">MOD-ADM-041</span> | Admin MUST CRUD quiz por encontro | **GET** `/{encontro_id}` questões completas (com isCorrect). **POST** upsert `{encontro, titulo?, questoes[]}` max 100 questões; titulo default `"Quiz Encontro {n}"`. **DELETE** remove quiz + limpa quiz_id nas trilhas. | `/api/admin/quiz*` |
| <span id="mod-adm-042">MOD-ADM-042</span> | Criar/atualizar quiz MUST propagar `quiz_id` em todas trilhas | Após upsert: `_sync_quiz_id_in_courses(db, encontro, ObjectId)` atualiza **todos** courses cujo PFE contém aquele encontro id. | `create_or_update_quiz` |
| <span id="mod-adm-043">MOD-ADM-043</span> | Admin MUST sincronizar quiz_ids em massa | `POST /sync-quiz-ids`: para **cada** course, reaplica `_fill_quiz_ids_in_payload` e update. Retorna `{courses_updated: N}`. | `sync_quiz_ids` |

---

<a id="m8"></a>
### M8 — Plataforma e Segurança

**Arquivos:** `main.py`, `database.py`, `config.py`, `Dockerfile`, middlewares

<a id="m8-infra"></a>
#### Funcionalidade: Infraestrutura

| ID | Requisito | Regras de negócio | Referência |
|----|-----------|-------------------|------------|
| <span id="mod-plat-001">MOD-PLAT-001</span> | App MUST expor health check com ping MongoDB | `GET /api/health`: `db.client.admin.command("ping")`. Sucesso: **200** `{status:"ok", mongodb:"connected"}`. Falha: **503** `{status:"degraded", mongodb:"disconnected", detail}`. Usado pelo HEALTHCHECK Docker. | `main.py:health` |
| <span id="mod-plat-002">MOD-PLAT-002</span> | Produção MUST servir SPA de `frontend-vue/dist` | Flag `USE_VUE_UI = dist/index.html exists`. Monta `/assets` estáticos. Rotas explícitas: `/`, `/programa`, `/admin/*`, `/login`, `/quiz/{id}`, etc. + fallback `/{full_path}` → index.html (no-cache). Sem dist: serve só `lp.html` em `/` se existir. | `main.py` L74+, L173+ |
| <span id="mod-plat-003">MOD-PLAT-003</span> | Container MUST rodar como usuário não-root | Dockerfile: `adduser appuser`, `chown -R appuser:appuser /app`, `USER appuser` antes CMD uvicorn. | `Dockerfile`, commit `00b056d` |
| <span id="mod-plat-004">MOD-PLAT-004</span> | Startup MUST falhar sem MONGODB_URI e JWT_SECRET_KEY | `@app.on_event("startup")` raise `RuntimeError` com mensagem orientando `.env`. Também executa `init_indexes()` e `seed_course_if_needed()`. | `main.startup` |
| <span id="mod-plat-005">MOD-PLAT-005</span> | Índices Mongo MUST ser criados no startup | users.email unique; password_resets/email_verifications token_hash unique + TTL expires_at; progress (user_id,course_slug) unique; courses.slug unique; quiz.encontro unique; quiz_responses (user_id,encontro) unique; maturity_responses (user_id,submitted_at); auth_rate_limits TTL `at` 3600s + compound (email,scope,at). | `database.init_indexes` |

<a id="m8-seguranca"></a>
#### Funcionalidade: Segurança HTTP

| ID | Requisito | Regras de negócio | Referência |
|----|-----------|-------------------|------------|
| <span id="mod-sec-001">MOD-SEC-001</span> | Responses MUST incluir CSP, HSTS, X-Frame-Options, etc. | Middleware aplica em **todas** respostas: CSP (`default-src self`, `script-src self`, `style-src self unsafe-inline fonts.googleapis.com`, `frame-ancestors none`, etc.), `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy` restritiva, HSTS 2 anos preload. | `SecurityHeadersMiddleware`, `SECURITY_HEADERS` |
| <span id="mod-sec-002">MOD-SEC-002</span> | `/docs`, `/redoc`, `/openapi.json` MUST desabilitar em production | `FastAPI(docs_url=redoc_url=openapi_url=None)` quando `settings.environment.lower()=="production"`. Dev: docs em `/docs`. | `main.py` app init |
| <span id="mod-sec-003">MOD-SEC-003</span> | CORS MUST restringir origens explícitas com credentials | `CORS_ORIGINS` CSV → lista; fallback `localhost:5173`. `allow_credentials=True`, methods/headers `*`. Necessário para cookie cross-origin. | `CORSMiddleware`, `config.cors_origins` |
| <span id="mod-sec-004">MOD-SEC-004</span> | Filtros Mongo MUST usar campos tipados Pydantic | Rotas constroem filtros a partir de campos validados (`EmailStr`, `ObjectId.is_valid`, ints) — nunca `request.json()` bruto como query. Manter padrão em código novo. | achado #8 auditoria |
| <span id="mod-sec-005">MOD-SEC-005</span> | Rate limits MUST persistir contadores com TTL 1h | `auth_rate_limits`: insert `{email, scope, at}` por tentativa; count na janela 1 min; scopes válidos: `login`, `forgot_password`, `resend_verification`. TTL index `at` expireAfterSeconds=**3600**. slowapi separado por IP. | `rate_limit.py`, `database.py` |

<a id="m8-email"></a>
#### Funcionalidade: Email transacional

| ID | Requisito | Regras de negócio | Referência |
|----|-----------|-------------------|------------|
| <span id="mod-sec-010">MOD-SEC-010</span> | Sistema MUST enviar email reset se SMTP configurado | `smtp_configured()` = host+user+password non-empty. Falha SMTP: log exception, retorna False; **forgot-password ainda 200 genérico**. Porta default 587; TLS default true; alternativa SSL (`SMTP_USE_SSL`). From: `SMTP_FROM` ou `SMTP_USER`. | `send_password_reset_email` |
| <span id="mod-sec-011">MOD-SEC-011</span> | Sistema MUST enviar email verificação no registro/resend | Mesma infra SMTP; templates HTML/text sem bloco token alternativo (só link). Assunto: `"Confirme seu email — Valorian 4 Future"`. Falha não bloqueia registro. | `send_verification_email` |
| <span id="mod-sec-012">MOD-SEC-012</span> | Links MUST usar `APP_BASE_URL` configurável | Env `APP_BASE_URL` default `http://localhost:5173`; trailing slash stripped. Usado em reset e verify links. | `config.app_base_url`, `email.py` |

---

<a id="m9"></a>
### M9 — Interface (SPA Vue 3)

**Arquivos:** `frontend-vue/src/router/`, `stores/auth.ts`, `api/client.ts`, `api/auth.ts`, `components/landing/AuthOverlay.vue`, `views/*`

**Proxy dev:** Vite `:5173` → backend `:8000` para `/api` e `/static`

<a id="m9-auth-ui"></a>
#### Funcionalidade: Autenticação na UI

| ID | Requisito | Regras de negócio | Referência |
|----|-----------|-------------------|------------|
| <span id="mod-ui-001">MOD-UI-001</span> | Login MUST usar cookie HttpOnly (sem localStorage) | `api/client.ts`: `credentials: 'include'` em todo fetch; **sem** header Authorization manual. `auth.ts`: login POST retorna user; não persiste token. `isLoggedIn` = `user !== null` após loadUser. | `client.ts`, `stores/auth.ts` |
| <span id="mod-ui-002">MOD-UI-002</span> | AuthOverlay MUST gerenciar login, forgot, reset e verify | Views `login\|forgot\|reset`; títulos/aria dinâmicos. Query `reset_token` → view reset; `verify_token` → POST verify-email automático. Navegação: Esqueci senha, Voltar, Já tenho token, Reenviar verificação. Validação + Enter key. | `AuthOverlay.vue` |
| <span id="mod-ui-003">MOD-UI-003</span> | Usuário não verificado MUST ver mensagem e botão reenviar | Pós-login: se `email_verified===false`, **não** redireciona para `/programa`; exibe success + botão `resendVerification()`. Guard bloqueia rotas protegidas → `/login`. | `redirectAfterLogin`, router guard |
| <span id="mod-ui-004">MOD-UI-004</span> | Logout MUST chamar API e limpar store | `logoutApi()` → `POST /logout`; zera user e currentCourseSlug. Topbar/AdminLayout: await logout + `window.location.replace('/')`. | `auth.ts`, `Topbar.vue`, `AdminLayout.vue` |

<a id="m9-navegacao"></a>
#### Funcionalidade: Navegação e guards

| ID | Requisito | Regras de negócio | Referência |
|----|-----------|-------------------|------------|
| <span id="mod-ui-010">MOD-UI-010</span> | Rotas protegidas MUST exigir login | Lista: `/programa`, `/materiais`, `/agenda`, `/quiz-respostas`, `/ai-maturity`, paths `/quiz/*`. Sem login → redirect `/`. Com login mas `email_verified===false` → redirect `/login`. | `router/index.ts:beforeEach` |
| <span id="mod-ui-011">MOD-UI-011</span> | Rotas admin MUST exigir is_admin | Prefixo `/admin` (exact ou subpaths). Sem login ou não-admin → `/`. Não verifica email separadamente (admin já verificado no backend). | `beforeEach` isAdminRoute |
| <span id="mod-ui-012">MOD-UI-012</span> | Aluno logado verificado em `/` MUST ir para /programa | Condição: `isLoggedIn && !isAdmin && email_verified !== false`. Admins permanecem na landing. | `router beforeEach` |
| <span id="mod-ui-013">MOD-UI-013</span> | Aluno com múltiplas trilhas MUST selecionar trilha ativa | Pinia `currentCourseSlug`; inicializado com primeiro slug de `/me` em loadUser. Usado nas chamadas API com `?course_slug=`. | `stores/auth.ts` |

<a id="m9-views"></a>
#### Funcionalidade: Views principais

| ID | Requisito | Regras de negócio | Referência |
|----|-----------|-------------------|------------|
| <span id="mod-ui-020">MOD-UI-020</span> | `/programa` MUST exibir jornada com progresso visual | Consome `GET /api/course/current` (cookie auth). Exibe encontros liberados/concluídos, materiais, link quiz. Layout `DefaultLayout` + topbar. | `ProgramaView.vue` |
| <span id="mod-ui-021">MOD-UI-021</span> | `/materiais` MUST listar materiais por encontro | Sincroniza checks via `POST /api/progress/material`. Respeita trilha ativa. | `MateriaisView.vue` |
| <span id="mod-ui-022">MOD-UI-022</span> | `/quiz/:encontroId` MUST suportar modo batch e review | Rotas alternativas: `/quiz/q/:quizId`. Passa query params `batch`, `review`, `rationales_for`, `course_slug` à API. | `QuizView.vue`, router |
| <span id="mod-ui-023">MOD-UI-023</span> | `/ai-maturity` MUST listar histórico e permitir nova avaliação | Rotas: list (`/ai-maturity`), new (`/ai-maturity/new`), detail (`/ai-maturity/:id`). Submit → `POST /my-response`. | `AiMaturity*View.vue` |
| <span id="mod-ui-024">MOD-UI-024</span> | `/admin/*` MUST cobrir dashboard, usuários, trilhas, progresso, quiz | `AdminLayout` sidebar: dashboard, trilhas, usuarios, alunos, progresso (+ detalhe aluno), quiz. Cada view consome endpoints `/api/admin/*`. | `views/admin/*`, `AdminLayout.vue` |

---

### Mapa de rastreabilidade (baseline → módulo)

| User Story baseline | Módulos relacionados |
|---------------------|---------------------|
| US1 — Aluno progride na trilha | M1, M2, M3, M4, M9 |
| US2 — Maturidade IA | M1, M5, M9 |
| US3 — Admin opera plataforma | M1, M7, M9 |
| US4 — Visitante e leads | M2, M6 |

---

## 5. Feature — Reset de senha na UI (`002-reset-senha-ui`)

**Branch:** `002-reset-senha-ui`  
**Status:** Implementado (UI + backend SMTP + hardening)  
**Criado:** 2026-06-24

### 4.1 Especificação funcional

#### US1 — Solicitar reset por email (P1)

- Link "Esqueci minha senha" no overlay de login
- Formulário de email com validação
- Mensagem genérica de confirmação (não revela se email existe)
- Erro amigável em falha de rede

#### US2 — Definir nova senha com token (P1)

- Campos: token, nova senha, confirmação
- Validação: senha ≥ 6, confirmação igual
- Token inválido/expirado → mensagem clara em PT-BR
- Após sucesso → login com nova senha

#### US3 — Navegação entre telas (P2)

- Voltar ao login desde forgot/reset
- "Já tenho o token" / "Solicitar novo token"
- Overlay reaberto → estado inicial login
- Query `?reset_token=` na URL abre tela de reset *(implementado)*

### Requisitos (FR)

| ID | Requisito |
|----|-----------|
| FR-001 | Link "Esqueci minha senha" na tela de login |
| FR-002 | Solicitar reset informando email |
| FR-003 | Mensagem genérica pós-solicitação |
| FR-004 | Token + nova senha + confirmação |
| FR-005 | Validar coincidência de senhas |
| FR-006 | Feedback claro (sucesso, validação, token, rede) |
| FR-007 | Retorno ao login |
| FR-008 | Reutilizar API backend (sem lógica duplicada) |
| FR-009 | Envio de email fora do escopo UI *(SMTP implementado separadamente)* |

### 4.2 Plano técnico

**Escopo original:** alteração concentrada em `AuthOverlay.vue` com máquina de estados:

```text
login ──"Esqueci..."──► forgot ──"Já tenho token"──► reset
  ▲                        │                            │
  └────── "Voltar ao login" ┴────────────────────────────┘
```

| View | Campos | API |
|------|--------|-----|
| login | email, password | `POST /api/auth/login` |
| forgot | email | `POST /api/auth/forgot-password` |
| reset | token, new_password, confirm | `POST /api/auth/reset-password` |

**Arquivo principal:** `frontend-vue/src/components/landing/AuthOverlay.vue`  
**Rota:** `/login` via `LoginView.vue`

### 4.3 Pesquisa de design (decisões)

| Tópico | Decisão |
|--------|---------|
| Onde implementar | `AuthOverlay.vue` (estados internos) |
| Token em dev | ~~`PASSWORD_RESET_RETURN_TOKEN` na API~~ **Removido por segurança** — token só via email SMTP |
| Validação | Cliente: senha ≥ 6, confirmação igual; servidor via Pydantic |
| Persistência de token | Não usar localStorage; query param `reset_token` na URL para link do email |
| Gap backend | Nenhum bloqueante na época do plano |

### 4.4 Modelo de dados (UI)

**Estado local (`AuthOverlay`):**

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `view` | `login \| forgot \| reset` | Tela ativa |
| `loading` | boolean | Submit em andamento |
| `error` / `success` | string | Feedback |
| `forgotEmail`, `resetToken`, `newPassword`, `confirmPassword` | string | Campos por view |

**Mapeamento de erros:**

| Condição | Mensagem |
|----------|----------|
| Email vazio | Informe seu email. |
| Email sem @ | Email inválido. |
| Senhas diferentes | As senhas não coincidem. |
| Senha < 6 | A senha deve ter pelo menos 6 caracteres. |
| API 400 reset | Token inválido ou expirado. |
| Rede | Erro de conexão. Tente novamente. |

### 4.5 Contrato API (reset)

#### POST /api/auth/forgot-password

**Request:** `{ "email": "aluno@exemplo.com" }`

**Response 200 (sempre):**

```json
{
  "message": "Se o email existir, enviaremos instruções para reset de senha."
}
```

- Rate limit: 5/min por IP + contador por email
- Email enviado via SMTP com link `/login?reset_token=...` e token alternativo no corpo
- **Não retorna `reset_token` na resposta HTTP** *(correção de segurança `d7bee91`)*

#### POST /api/auth/reset-password

**Request:** `{ "token": "...", "new_password": "..." }`

**Response 200:** `{ "message": "Senha atualizada com sucesso." }`  
**Response 400:** `{ "detail": "Token inválido ou expirado" }`

### 4.6 Tarefas (002) — resumo

28 tarefas em 6 fases; **27/28 concluídas** (T028 validação manual pendente de execução formal):

- Phase 1–2: Setup + máquina de estados
- Phase 3: US1 forgot
- Phase 4: US2 reset
- Phase 5: US3 navegação
- Phase 6: Polish (CSS, aria, Enter key)

### 4.7 Quickstart de validação

```bash
# Backend
cd backend && source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Frontend
cd frontend-vue && npm run dev
```

**Cenários:**

1. Email existente → mensagem genérica; token chega por email (SMTP configurado)
2. Email inexistente → mesma mensagem genérica
3. Token válido → senha atualizada → login OK
4. Token inválido → erro amigável
5. Validações cliente (email vazio, senhas diferentes, senha curta)
6. Navegação login ↔ forgot ↔ reset; query `?reset_token=` abre reset

---

## 6. Implementação técnica atual

### 5.1 Arquitetura

```text
┌─────────────────────────────────────────────────────────────┐
│  Browser                                                     │
│  ├── lp.html + lp.js (landing, leads, CSP script-src self)  │
│  └── Vue SPA (programa, admin, quiz, maturidade)            │
│       credentials: include → cookie HttpOnly access_token    │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTPS / proxy Vite (dev)
┌──────────────────────────▼──────────────────────────────────┐
│  FastAPI (uvicorn) — backend/app/main.py                     │
│  ├── SecurityHeadersMiddleware (CSP, HSTS, X-Frame-Options)  │
│  ├── SlowAPIMiddleware (rate limiting)                       │
│  ├── CORSMiddleware (origens explícitas, credentials)        │
│  └── Rotas /api/* + arquivos estáticos (dist, lp.html)       │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│  MongoDB (Atlas / local)                                     │
│  users, courses, progress, quiz, maturity, leads, ...        │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 Backend — módulos principais

| Módulo | Responsabilidade |
|--------|------------------|
| `main.py` | App FastAPI, CORS, CSP, rotas estáticas, seed de curso |
| `config.py` | Settings via env (Pydantic Settings) |
| `database.py` | Cliente MongoDB, índices TTL |
| `deps.py` | `get_current_user`, `get_verified_user`, `get_current_admin` |
| `security.py` | Hash senha, JWT, tokens reset/verify |
| `limiter.py` | Instância slowapi |
| `utils/login_lockout.py` | Lockout 6 falhas → 15 min |
| `utils/rate_limit.py` | Contador por email no Mongo |
| `utils/auth_cookie.py` | Cookie HttpOnly JWT |
| `utils/email.py` | SMTP reset + verificação |
| `utils/email_verification.py` | Emissão/validação tokens verify |
| `utils/email_templates.py` | HTML/text transacional |

### 5.3 Frontend — módulos principais

| Módulo | Responsabilidade |
|--------|------------------|
| `api/client.ts` | fetch com `credentials: 'include'` |
| `api/auth.ts` | login, logout, me, forgot, reset, verify, resend |
| `stores/auth.ts` | Pinia: user, isLoggedIn, loadUser, logout |
| `router/index.ts` | Guards: auth, admin, email_verified |
| `components/landing/AuthOverlay.vue` | Login + reset + verify token |
| `views/admin/*` | CRUD admin |
| `views/*` | Programa, quiz, maturidade, trilhas |

### 5.4 Trilha padrão (seed)

Arquivo `backend/data/course.json` → slug `trilha-ia-executiva`, importado na primeira subida se Mongo vazio.

Estrutura `programa_formacao_executiva`:

- `cabecalho` — título, tema, público, trilha
- `visao_geral` — objetivo, instrutor
- `jornada_aprendizagem[]` — semanas → encontros com objetivos, materiais, quiz_id

Cada **encontro** contém: `id`, `titulo`, `objetivos`, `material_suporte[]`, etc.

---

## 7. API — referência de endpoints

### 6.1 Autenticação — `/api/auth`

| Método | Rota | Auth | Descrição |
|--------|------|------|-----------|
| POST | `/register` | — | Cadastro; `email_verified: false`; envia email verify |
| POST | `/login` | — | Login; seta cookie HttpOnly; rate limit 5/min |
| POST | `/logout` | — | Limpa cookie |
| GET | `/me` | Cookie/Bearer | Perfil + course_slugs |
| POST | `/verify-email` | — | `{ token }` → marca email_verified |
| POST | `/resend-verification` | Cookie/Bearer | Reenvia email; rate limit |
| POST | `/forgot-password` | — | Reset; mensagem genérica; rate limit |
| POST | `/reset-password` | — | Nova senha com token |

**Response login/register (corpo + cookie):**

```json
{
  "access_token": "...",
  "token_type": "bearer",
  "user": {
    "id": "...",
    "name": "...",
    "email": "...",
    "is_admin": false,
    "email_verified": true
  }
}
```

### 6.2 Curso e progresso

| Método | Rota | Auth | Descrição |
|--------|------|------|-----------|
| GET | `/api/course/current` | Verificado | Trilha atual do aluno |
| POST | `/api/progress/material` | Verificado | Marca/desmarca material |
| POST | `/api/progress/complete/{encontro_id}` | Verificado | Conclui encontro |

### 6.3 Quiz — `/api/quiz`

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/quiz` | Lista quizzes |
| GET | `/api/quiz/by-id/{quiz_id}` | Quiz por ID |
| GET | `/api/quiz/{encontro_id}` | Quiz do encontro |
| GET | `/api/quiz/{encontro_id}/my-response` | Resposta do aluno |
| POST | `/api/quiz/{encontro_id}/submit` | Enviar respostas |

### 6.4 Maturidade IA — `/api/maturity`

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/maturity/model` | Modelo ativo |
| GET | `/api/maturity/my-responses` | Histórico do aluno |
| GET | `/api/maturity/my-responses/{id}` | Detalhe |
| POST | `/api/maturity/my-response` | Nova autoavaliação |

### 6.5 Público — `/api/public`

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/public/courses` | Lista trilhas (resumo) |
| GET | `/api/public/courses/{slug}` | Trilha completa |
| POST | `/api/public/leads` | Formulário landing (captcha soma) |

**Lead payload:**

```json
{
  "nome_completo": "...",
  "cargo": "...",
  "empresa": "...",
  "faturamento_anual": "...",
  "email": "...",
  "contexto_ia": "...",
  "num1": 3,
  "num2": 7,
  "captcha_answer": 10
}
```

### 6.6 Admin — `/api/admin`

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/dashboard` | Visão geral |
| GET/POST/PUT/DELETE | `/courses`, `/courses/{slug}` | CRUD trilhas |
| GET/POST/PUT/DELETE | `/users`, `/users/{id}` | CRUD usuários |
| GET | `/users/{id}/course-and-progress` | Trilha + progresso |
| POST | `/users/{id}/liberar-encontro` | Libera encontro |
| PATCH | `/users/{id}/progress` | Atualiza agendas |
| GET/POST/DELETE | `/quiz`, `/quiz/{encontro_id}` | CRUD quiz |
| POST | `/sync-quiz-ids` | Sincroniza quiz_id nas trilhas |

### 6.7 Infra

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/health` | `{ status, mongodb }` — 503 se Mongo down |
| GET | `/robots.txt`, `/sitemap.xml`, `/lp.js` | Arquivos estáticos |

---

## 8. Frontend — rotas e componentes

### 7.1 Rotas Vue

| Rota | View | Proteção |
|------|------|----------|
| `/` | LandingView | Pública |
| `/programa` | ProgramaView | Auth + email verificado |
| `/materiais` | MateriaisView | Auth + verificado |
| `/trilhas`, `/trilhas/:slug` | Trilhas / Showcase | Pública |
| `/agenda` | AgendaView | Auth + verificado |
| `/ai-maturity/*` | Maturidade | Auth + verificado |
| `/quiz/*` | QuizView | Auth + verificado |
| `/quiz-respostas` | QuizRespostasView | Auth + verificado |
| `/login` | LoginView + AuthOverlay | Pública |
| `/admin/*` | Admin views | Auth + is_admin + verificado |

### 7.2 Guards (`router/index.ts`)

1. Carrega usuário via `GET /api/auth/me` (cookie)
2. Rotas `/admin` → exige login + `is_admin`
3. Rotas protegidas → exige login; se `email_verified === false` → `/login`
4. `/` com aluno logado verificado → redirect `/programa`

---

## 9. Modelo de dados MongoDB

### Coleções

| Coleção | Índices principais | Uso |
|---------|-------------------|-----|
| `users` | `email` unique | Contas; `is_admin`, `email_verified`, `failed_login_attempts`, `locked_until` |
| `courses` | `slug` unique | Trilhas |
| `progress` | `(user_id, course_slug)` unique | Progresso por aluno/trilha |
| `quiz` | `encontro` unique | Questionários |
| `quiz_responses` | `(user_id, encontro)` unique | Respostas |
| `ai_maturity_model` | `version` | Questionário de diagnóstico |
| `maturity_responses` | `(user_id, model_id, submitted_at)` | Autoavaliações com referência ao modelo |
| `password_resets` | `token_hash` unique; TTL `expires_at` | Tokens reset |
| `email_verifications` | `token_hash` unique; TTL `expires_at` | Tokens verify |
| `auth_rate_limits` | TTL `at`; `(email, scope, at)` | Rate limiting |
| `leads` | `created_at` | Leads landing |

### Documento `progress` (campos)

- `concluidos: number[]` — IDs de encontros concluídos
- `ativo: number` — encontro ativo
- `total: number`
- `encontros_liberados: number[]`
- `material_checks: object` — checks por encontro/material
- `encontro_conclusoes: object`
- `encontro_agendas: object` — ISO datetime por encontro

---

## 10. Autenticação, sessão e segurança

### 9.1 Sessão (estado atual)

- JWT emitido no login/register
- Armazenado em cookie **`access_token`**: `HttpOnly`, `SameSite=Strict`, `Secure` se `ENVIRONMENT=production`
- Frontend: `credentials: 'include'` — **sem localStorage**
- Logout: `POST /api/auth/logout` limpa cookie
- Header `Authorization: Bearer` ainda aceito (compatibilidade)

### 9.2 Verificação de email

- Registro: `email_verified: false` + email SMTP
- Link: `/login?verify_token=...`
- Rotas sensíveis: `get_verified_user` (403 se não verificado)
- Legado sem campo: tratado como verificado
- Admin-created users: `email_verified: true`

### 9.3 Rate limiting e lockout

- **slowapi:** 5 req/min por IP em `/login`, `/forgot-password`, `/resend-verification`
- **Por email:** coleção `auth_rate_limits`
- **Lockout:** 6 falhas consecutivas → bloqueio 15 min (`failed_login_attempts`, `locked_until`)
- Mensagem genérica "Credenciais invalidas"; hash dummy anti timing-oracle

### 9.4 Admin bootstrap

- **Removido:** `INITIAL_ADMIN_EMAIL`
- **Usar:** `python -m app.scripts.promote_admin --email admin@exemplo.com`
- Define `is_admin: true` e `email_verified: true` no MongoDB

### 9.5 Headers de segurança

```
Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' ...
X-Frame-Options: DENY
Strict-Transport-Security: max-age=63072000; includeSubDomains; preload
```

Scripts da landing em `/lp.js` (sem inline).

### 9.6 Auditoria — commits de correção

| # | Achado | Commit |
|---|--------|--------|
| 1 | Vazamento reset_token na API | `d7bee91` |
| 2b | INITIAL_ADMIN_EMAIL bypass | `55d4cbb` |
| 3 | Rate limiting / lockout | `fea9d34` |
| 4 | Verificação de email | `bfa9520` |
| 5 | JWT localStorage → cookie | `a6b4c0a` |
| 6 | Container root + /docs | `00b056d` |
| 7 | CSP unsafe-inline | `69ff3ed` |
| 8 | NoSQL injection | Sem ação (Pydantic tipado) |

---

## 11. Deploy e operação

### 10.1 Desenvolvimento local

```bash
# MongoDB (Atlas ou local)
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # MONGODB_URI, JWT_SECRET_KEY, SMTP...
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

cd frontend-vue
npm install && npm run dev   # http://localhost:5173
```

### 10.2 Produção (Docker)

```bash
cp backend/.env.example backend/.env
# Preencher: MONGODB_URI, JWT_SECRET_KEY, ENVIRONMENT=production, CORS_ORIGINS, SMTP, APP_BASE_URL
docker compose up --build
# http://localhost:8000
```

- Container roda como **`appuser`** (non-root)
- `/docs`, `/redoc`, `/openapi.json` desabilitados com `ENVIRONMENT=production`
- Health check: `GET /api/health`

### 10.3 Variáveis de ambiente

| Variável | Obrigatória | Descrição |
|----------|-------------|-----------|
| `MONGODB_URI` | Sim | Connection string MongoDB |
| `JWT_SECRET_KEY` | Sim | Chave JWT (≥ 32 chars) |
| `ENVIRONMENT` | Recomendada | `production` → Secure cookie, sem /docs |
| `CORS_ORIGINS` | Sim (prod) | Origens permitidas (vírgula) |
| `APP_BASE_URL` | Sim (email) | URL pública do frontend |
| `SMTP_*` | Sim (email) | Host, user, password, from |
| `PASSWORD_RESET_EXPIRE_MINUTES` | Não | Default 30 |
| `JWT_EXPIRE_MINUTES` | Não | Default 480 |
| `MONGODB_DB_NAME` | Não | Default `aegis` |

**Removidas (não usar):** `INITIAL_ADMIN_EMAIL`, `PASSWORD_RESET_RETURN_TOKEN`

### 10.4 Checklist pós-deploy

1. `ENVIRONMENT=production`
2. `python -m app.scripts.promote_admin --email ...`
3. SMTP funcional (reset + verificação)
4. `CORS_ORIGINS` = URL pública exata
5. HTTPS ativo (cookie Secure)

---

## 12. Spec Kit — workflow de desenvolvimento

### Setup (já inicializado)

- CLI: `specify` (GitHub Spec Kit v0.11.6)
- Templates: `.specify/`
- Skills Cursor: `.cursor/skills/speckit-*`
- Constitution: `.specify/memory/constitution.md`
- Baseline: `specs/001-aegis-baseline/spec.md`
- Feature exemplo: `specs/002-reset-senha-ui/`

### Fluxo por feature

```text
/speckit-specify  → spec.md + branch NNN-nome
/speckit-clarify  → esclarecer ambiguidades (opcional)
/speckit-plan     → plan.md, research.md, data-model.md, contracts/
/speckit-tasks    → tasks.md
/speckit-analyze  → validar consistência
/speckit-implement → código
```

Extensão **git** habilitada em `.specify/extensions.yml` (commits/branches automáticos).

### Specs existentes

| Diretório | Conteúdo |
|-----------|----------|
| `specs/001-aegis-baseline/` | spec.md, checklists/requirements.md |
| `specs/002-reset-senha-ui/` | spec, plan, research, data-model, tasks, quickstart, contracts/, checklists/ |

---

## 13. Apêndices

### A. Funcionalidades por persona

**Aluno**

- Login (cookie), reset senha, verificação email
- Programa com encontros, materiais, conclusão
- Quiz por encontro
- AI Maturity Model com histórico
- Agenda

**Admin**

- Dashboard, CRUD usuários/trilhas
- Liberar encontros, editar progresso/agendas
- CRUD quiz, sync quiz_id

**Visitante**

- Landing `lp.html` (9 encontros, framework V.A.L.O.R.)
- Vitrine trilhas
- Formulário de aplicação → `leads`

### B. Email transacional

| Tipo | Link | Template |
|------|------|----------|
| Reset senha | `/login?reset_token=...` | `render_password_reset_html/text` |
| Verificação | `/login?verify_token=...` | `render_email_verification_html/text` |

Paleta visual alinhada à landing (navy/gold/ivory).

### C. Divergências specs → implementação

| Spec / doc antigo | Estado atual |
|-------------------|--------------|
| `INITIAL_ADMIN_EMAIL` para admin | Removido; usar `promote_admin.py` |
| `PASSWORD_RESET_RETURN_TOKEN` | Removido; token só por email |
| JWT em `localStorage` | Cookie HttpOnly |
| Reset UI sem email | SMTP implementado; link no email |
| Baseline: "envio email fora escopo" | SMTP + templates implementados |
| `/docs` sempre ativo | Desabilitado em `ENVIRONMENT=production` |

### D. Referências no repositório

| Arquivo | Conteúdo |
|---------|----------|
| `README.md` | Guia rápido do projeto |
| `SECURITY_AUDIT.md` | Auditoria e status das correções |
| `SECURITY_FIX_PROMPT.md` | Prompt de implementação das correções |
| `backend/README.md` | Backend, health, reset |
| `frontend-vue/README.md` | Estrutura frontend |
| `.specify/memory/constitution.md` | Constitution fonte |
| `specs/*/` | Specs individuais por feature |

---

*Documento gerado para exportação consolidada. Para specs vivas por feature, consulte `specs/` e `.specify/`.*
