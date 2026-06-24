# Tasks: Reset de Senha na Interface

**Input**: Design documents from `/specs/002-reset-senha-ui/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/auth-reset-api.md

**Tests**: Não solicitados na spec — validação manual via [quickstart.md](./quickstart.md)

**Organization**: Tarefas agrupadas por user story; implementação concentrada em `frontend-vue/src/components/landing/AuthOverlay.vue`

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode executar em paralelo (sem dependência de tarefas incompletas no mesmo arquivo)
- **[Story]**: US1, US2, US3 conforme spec.md

## Path Conventions

- Frontend: `frontend-vue/src/`
- Componente alvo: `frontend-vue/src/components/landing/AuthOverlay.vue`
- API (somente leitura): `frontend-vue/src/api/auth.ts`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirmar pré-requisitos antes de editar o componente

- [x] T001 Verificar que `forgotPassword` e `resetPassword` existem e estão tipados em `frontend-vue/src/api/auth.ts`
- [x] T002 Confirmar contrato em `specs/002-reset-senha-ui/contracts/auth-reset-api.md` alinhado com `backend/app/routes/auth.py` (sem alteração esperada)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Máquina de estados e estrutura de template — bloqueia todas as user stories

**⚠️ CRITICAL**: Nenhuma user story até concluir esta fase

- [x] T003 Adicionar tipo `AuthView = 'login' | 'forgot' | 'reset'` e ref `view` em `frontend-vue/src/components/landing/AuthOverlay.vue`
- [x] T004 Adicionar refs compartilhados `success`, `forgotEmail`, `resetToken`, `newPassword`, `confirmPassword` em `frontend-vue/src/components/landing/AuthOverlay.vue`
- [x] T005 Implementar função `resetOverlayState()` que limpa campos, `error`, `success` e define `view='login'` em `frontend-vue/src/components/landing/AuthOverlay.vue`
- [x] T006 Estender `watch(() => props.show)` para chamar `resetOverlayState()` quando overlay abrir em `frontend-vue/src/components/landing/AuthOverlay.vue`
- [x] T007 Refatorar template com `v-if`/`v-else-if` por `view` mantendo formulário de login intacto em `frontend-vue/src/components/landing/AuthOverlay.vue`
- [x] T008 Adicionar título dinâmico em `.auth-title` por view (Entrar / Recuperar senha / Nova senha) em `frontend-vue/src/components/landing/AuthOverlay.vue`
- [x] T009 Importar `forgotPassword` e `resetPassword` de `@/api/auth` em `frontend-vue/src/components/landing/AuthOverlay.vue`

**Checkpoint**: Login existente funciona; views alternam estruturalmente (placeholders OK)

---

## Phase 3: User Story 1 — Solicitar reset por email (Priority: P1) 🎯 MVP

**Goal**: Aluno solicita reset informando email e vê confirmação genérica

**Independent Test**: `/login` → Esqueci senha → email válido → mensagem genérica (quickstart cenário 1 e 2)

### Implementation for User Story 1

- [x] T010 [US1] Adicionar link "Esqueci minha senha" na view `login` que define `view='forgot'` em `frontend-vue/src/components/landing/AuthOverlay.vue`
- [x] T011 [US1] Implementar template da view `forgot` (input email, botão enviar, área erro/sucesso) em `frontend-vue/src/components/landing/AuthOverlay.vue`
- [x] T012 [US1] Implementar `submitForgot()` com validação (email não vazio, contém `@`) em `frontend-vue/src/components/landing/AuthOverlay.vue`
- [x] T013 [US1] Chamar `forgotPassword({ email })` em `submitForgot()` com estados `loading`/`error`/`success` em `frontend-vue/src/components/landing/AuthOverlay.vue`
- [x] T014 [US1] Exibir `response.message` como sucesso genérico sem indicar existência do email em `frontend-vue/src/components/landing/AuthOverlay.vue`
- [x] T015 [US1] Se `response.reset_token` presente, exibir bloco `.auth-hint` com token copiável (dev) em `frontend-vue/src/components/landing/AuthOverlay.vue`

**Checkpoint**: Fluxo forgot completo e testável isoladamente

---

## Phase 4: User Story 2 — Definir nova senha com token (Priority: P1)

**Goal**: Aluno informa token e nova senha e conclui recuperação

**Independent Test**: Token válido → nova senha → sucesso → login com nova senha (quickstart cenário 3 e 4)

### Implementation for User Story 2

- [x] T016 [US2] Implementar template da view `reset` (token, nova senha, confirmação, submit) em `frontend-vue/src/components/landing/AuthOverlay.vue`
- [x] T017 [US2] Implementar `submitReset()` com validação (token não vazio, senha ≥ 6, confirmação igual) em `frontend-vue/src/components/landing/AuthOverlay.vue`
- [x] T018 [US2] Chamar `resetPassword({ token, new_password })` em `submitReset()` com `loading`/`error`/`success` em `frontend-vue/src/components/landing/AuthOverlay.vue`
- [x] T019 [US2] Mapear erro API 400 para mensagem "Token inválido ou expirado" em `frontend-vue/src/components/landing/AuthOverlay.vue`
- [x] T020 [US2] Após sucesso, exibir orientação e botão "Ir para login" que chama `resetOverlayState()` em `frontend-vue/src/components/landing/AuthOverlay.vue`

**Checkpoint**: Fluxo reset completo; login com nova senha funciona

---

## Phase 5: User Story 3 — Navegação entre telas (Priority: P2)

**Goal**: Aluno alterna entre login, forgot e reset com clareza

**Independent Test**: Voltar ao login desde forgot/reset; link para nova senha após forgot (quickstart cenário 6)

### Implementation for User Story 3

- [x] T021 [US3] Adicionar "Voltar ao login" na view `forgot` (`view='login'`, limpar erro/sucesso) em `frontend-vue/src/components/landing/AuthOverlay.vue`
- [x] T022 [US3] Adicionar "Já tenho o token" na view `forgot` que vai para `reset` e pré-preenche `resetToken` se disponível em `frontend-vue/src/components/landing/AuthOverlay.vue`
- [x] T023 [US3] Adicionar link "Solicitar novo token" na view `reset` que volta para `forgot` preservando `forgotEmail` em `frontend-vue/src/components/landing/AuthOverlay.vue`
- [x] T024 [US3] Adicionar "Voltar ao login" na view `reset` em `frontend-vue/src/components/landing/AuthOverlay.vue`

**Checkpoint**: Navegação circular login ↔ forgot ↔ reset funcional

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Acessibilidade, UX e validação final

- [x] T025 Adicionar estilos `.auth-link`, `.auth-success`, `.auth-hint` em `frontend-vue/src/components/landing/AuthOverlay.vue`
- [x] T026 Atualizar `aria-label` do dialog por view (`Entrar` / `Recuperar senha` / `Nova senha`) em `frontend-vue/src/components/landing/AuthOverlay.vue`
- [x] T027 Adicionar handler `@keydown.enter` nos formulários `forgot` e `reset` em `frontend-vue/src/components/landing/AuthOverlay.vue`
- [ ] T028 Executar validação manual completa conforme `specs/002-reset-senha-ui/quickstart.md` (cenários 1–6)

---

## Dependencies & Execution Order

### Phase Dependencies

```text
Phase 1 (Setup) → Phase 2 (Foundational) → Phase 3 (US1) + Phase 4 (US2) → Phase 5 (US3) → Phase 6 (Polish)
```

### User Story Dependencies

| Story | Depende de | Independente após |
|-------|------------|-------------------|
| US1 (P1) | Phase 2 | T015 — forgot testável sozinho |
| US2 (P1) | Phase 2; link opcional de US3 T022 melhora UX | T020 — reset testável com token manual |
| US3 (P2) | US1 e US2 parcialmente implementados | T024 — navegação completa |

**Nota**: US1 e US2 podem ser implementadas em sequência no mesmo arquivo (T010–T020) sem US3; navegação mínima (ir para forgot) já está em T010.

### Parallel Opportunities

- T001 e T002 podem rodar em paralelo (arquivos diferentes)
- Após Phase 2, US1 (T010–T015) e início de US2 (T016 template) são sequenciais no mesmo arquivo — **sem paralelismo real** nesta feature
- T025–T027 podem ser feitos em paralelo conceitualmente mas no mesmo arquivo

### Parallel Example (único paralelismo real)

```bash
# Setup em paralelo:
T001: verificar frontend-vue/src/api/auth.ts
T002: verificar contrato specs/002-reset-senha-ui/contracts/auth-reset-api.md
```

---

## Implementation Strategy

### MVP First (User Story 1)

1. Phase 1 + Phase 2 (T001–T009)
2. Phase 3 US1 (T010–T015)
3. **VALIDAR** quickstart cenários 1–2
4. Parar ou continuar para US2

### Entrega completa P1 (recomendado)

1. Setup + Foundational (T001–T009)
2. US1 forgot (T010–T015)
3. US2 reset (T016–T020)
4. **VALIDAR** quickstart cenários 1–4
5. US3 navegação (T021–T024)
6. Polish (T025–T028)

### Estimativa

| Fase | Tarefas | Arquivos |
|------|---------|----------|
| Setup | 2 | auth.ts (read), contracts |
| Foundational | 7 | AuthOverlay.vue |
| US1 | 6 | AuthOverlay.vue |
| US2 | 5 | AuthOverlay.vue |
| US3 | 4 | AuthOverlay.vue |
| Polish | 4 | AuthOverlay.vue, quickstart |
| **Total** | **28** | 1 arquivo principal |

---

## Notes

- Não alterar `backend/` salvo gap de contrato (nenhum identificado no plano)
- Não alterar `frontend-vue/src/api/auth.ts` salvo tipagem faltante
- `LoginView.vue` não requer mudanças — já usa `AuthOverlay`
- Commit sugerido após cada checkpoint de user story
