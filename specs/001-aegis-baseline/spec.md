# Feature Specification: AEGIS Baseline (Brownfield)

**Feature Branch**: `main` (documentação de estado atual; não é feature de implementação)

**Created**: 2026-06-24

**Status**: Accepted (baseline)

**Input**: Documentar o estado atual da plataforma AEGIS como referência brownfield para desenvolvimento orientado por especificação.

## User Scenarios & Testing

### User Story 1 - Aluno acessa trilha e progride (Priority: P1)

Como aluno autenticado, quero acessar minha trilha de formação, marcar materiais e concluir encontros para acompanhar minha evolução no programa.

**Why this priority**: É o fluxo central de valor da plataforma de mentoria.

**Independent Test**: Login → `/programa` → marcar material → concluir encontro → progresso persistido e visível.

**Acceptance Scenarios**:

1. **Given** aluno com trilha atribuída, **When** faz login, **Then** acessa o programa com encontros liberados conforme regras de progresso.
2. **Given** encontro ativo, **When** marca materiais e conclui encontro, **Then** o progresso é salvo em `progress` no MongoDB.
3. **Given** quiz associado ao encontro, **When** o aluno responde, **Then** a resposta fica registrada em `quiz_responses`.

---

### User Story 2 - Aluno realiza diagnóstico de maturidade em IA (Priority: P1)

Como aluno, quero responder o questionário de maturidade em IA e consultar resultados anteriores para entender minha evolução.

**Why this priority**: Diferencial do produto (AI Maturity Model).

**Independent Test**: Login → `/ai-maturity` → nova autoavaliação → resultado com score e nível → histórico listado.

**Acceptance Scenarios**:

1. **Given** modelo em `ai_maturity_model`, **When** aluno inicia avaliação, **Then** vê dimensões e perguntas do modelo ativo.
2. **Given** respostas válidas (1–5), **When** submete, **Then** recebe score total, por dimensão e nível de maturidade.
3. **Given** avaliações anteriores, **When** consulta histórico, **Then** vê lista ordenada por data.

---

### User Story 3 - Admin gerencia alunos e conteúdo (Priority: P2)

Como administrador, quero gerenciar usuários, trilhas, progresso e quiz para operar a mentoria.

**Why this priority**: Operação da plataforma depende da área admin.

**Independent Test**: Login admin → `/admin` → CRUD usuário/trilha → liberar encontro para aluno.

**Acceptance Scenarios**:

1. **Given** usuário com `is_admin` ou `INITIAL_ADMIN_EMAIL`, **When** acessa `/admin`, **Then** vê dashboard e menus administrativos.
2. **Given** aluno existente, **When** admin atualiza trilhas ou progresso, **Then** mudanças refletem na experiência do aluno.
3. **Given** encontro com quiz, **When** admin configura quiz, **Then** aluno pode responder na trilha.

---

### User Story 4 - Visitante explora trilhas e deixa lead (Priority: P3)

Como visitante, quero ver trilhas disponíveis na vitrine pública e registrar interesse.

**Why this priority**: Aquisição e marketing; não bloqueia alunos autenticados.

**Independent Test**: Acessar landing/trilhas sem login → ver catálogo → submeter lead.

**Acceptance Scenarios**:

1. **Given** trilhas publicadas em `courses`, **When** visitante acessa vitrine, **Then** vê listagem e detalhe por slug.
2. **Given** formulário de lead, **When** submete dados válidos, **Then** lead é persistido em `leads`.

---

### Edge Cases

- Aluno sem trilha atribuída: programa vazio ou mensagem orientativa.
- Token JWT expirado: redirecionamento para login/landing.
- Modelo `ai_maturity_model` ausente: API retorna erro de serviço indisponível.
- MongoDB inacessível: health check retorna 503.

## Requirements

### Functional Requirements

- **FR-001**: Sistema MUST autenticar usuários via email/senha com JWT.
- **FR-002**: Sistema MUST permitir reset de senha via token temporário (API implementada).
- **FR-003**: Sistema MUST persistir progresso por usuário e trilha (`course_slug`).
- **FR-004**: Sistema MUST servir conteúdo de trilhas a partir de `courses` no MongoDB.
- **FR-005**: Sistema MUST carregar AI Maturity Model da coleção `ai_maturity_model`.
- **FR-006**: Sistema MUST permitir múltiplas autoavaliações de maturidade por aluno.
- **FR-007**: Sistema MUST restringir rotas `/admin` e `/api/admin` a administradores.
- **FR-008**: Sistema MUST expor health check com status do MongoDB.
- **FR-009**: Sistema MUST servir SPA Vue em produção quando `frontend-vue/dist` existir.

### Key Entities

- **User**: nome, email, password_hash, is_admin, trilhas associadas.
- **Course (Trilha)**: slug, `programa_formacao_executiva` com jornada e encontros.
- **Progress**: user_id, course_slug, concluídos, materiais, agendas.
- **Quiz / QuizResponse**: questionário por encontro e respostas do aluno.
- **AiMaturityModel**: versão, dimensões, escala, scoring_logic.
- **MaturityResponse**: respostas e resultado calculado por avaliação.
- **Lead**: contato capturado na área pública.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Aluno consegue completar login e acessar programa em menos de 3 interações.
- **SC-002**: Progresso persiste entre sessões para o mesmo usuário e trilha.
- **SC-003**: Autoavaliação de maturidade gera resultado consistente com o modelo ativo no banco.
- **SC-004**: Admin consegue criar usuário com trilha e liberar encontro sem intervenção manual no banco.
- **SC-005**: Deploy Docker sobe API + SPA com health check respondendo.

## Assumptions

- MongoDB (Atlas ou local) está provisionado e acessível via `MONGODB_URI`.
- Conteúdo de trilhas e modelo de maturidade são mantidos no banco, não em arquivos `prototype/`.
- Envio de email para reset de senha não está no escopo do baseline (API pronta; UI opcional).
- Idioma da interface e specs de negócio: português.
