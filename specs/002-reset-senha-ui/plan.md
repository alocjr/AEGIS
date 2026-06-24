# Implementation Plan: Reset de Senha na Interface

**Branch**: `002-reset-senha-ui` | **Date**: 2026-06-24 | **Spec**: [spec.md](./spec.md)

**Input**: Stack Vue 3 no AuthOverlay, reutilizar `forgotPassword` e `resetPassword` de `frontend-vue/src/api/auth.ts`, sem mudanças no backend salvo gap de contrato.

## Summary

Adicionar fluxo completo de recuperação de senha no componente `AuthOverlay.vue` usando máquina de estados local (`login` → `forgot` → `reset`). Integração exclusiva com APIs existentes via client HTTP já implementado. Sem novas rotas obrigatórias nem alterações de backend — contrato atual atende todos os FRs.

## Technical Context

**Language/Version**: TypeScript 5.x, Vue 3.4+ (Composition API + `<script setup>`)

**Primary Dependencies**: Vue Router (já usado), `fetch` via `frontend-vue/src/api/client.ts`

**Storage**: N/A no frontend (tokens de reset não persistidos em localStorage)

**Testing**: Validação manual conforme [quickstart.md](./quickstart.md); sem suite E2E existente no projeto

**Target Platform**: SPA Vue servida em `/login` e overlay futuro; proxy Vite em dev

**Project Type**: Web application (frontend-only change)

**Performance Goals**: Resposta de UI imediata; chamadas API únicas por submit

**Constraints**: Mensagens genéricas no forgot; não expor `reset_token` em produção; diff mínimo em um componente

**Scale/Scope**: 1 componente principal (`AuthOverlay.vue`), 0 mudanças backend esperadas

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Status | Notas |
|-----------|--------|-------|
| I. Brownfield First | ✅ PASS | Estende `AuthOverlay` existente |
| II. Mudanças Mínimas | ✅ PASS | Um arquivo Vue + possível ajuste CSS no mesmo arquivo |
| III. Segurança | ✅ PASS | Não armazena token; mensagem genérica no forgot |
| IV. API e Contratos | ✅ PASS | Reutiliza `auth.ts`; contrato documentado em `contracts/` |
| V. MongoDB | ✅ N/A | Sem mudança de persistência |
| VI. Deploy Unificado | ✅ PASS | Sem impacto no Docker/build |
| VII. Qualidade Pragmática | ✅ PASS | quickstart.md para testes manuais |

**Post-design re-check**: ✅ Nenhuma violação. Complexity Tracking vazio.

## Project Structure

### Documentation (this feature)

```text
specs/002-reset-senha-ui/
├── plan.md              # Este arquivo
├── research.md          # Decisões de design
├── data-model.md        # Estados e validações UI
├── quickstart.md        # Guia de validação manual
├── contracts/
│   └── auth-reset-api.md
├── spec.md
└── tasks.md             # Gerado por /speckit-tasks
```

### Source Code (alterações previstas)

```text
frontend-vue/src/
├── api/
│   └── auth.ts                    # Já possui forgotPassword / resetPassword — sem alteração
├── components/landing/
│   └── AuthOverlay.vue            # PRINCIPAL: views login | forgot | reset
└── views/
    └── LoginView.vue              # Sem alteração (já embute AuthOverlay)
```

**Structure Decision**: Implementação concentrada em `AuthOverlay.vue` para cobrir `/login` e qualquer uso futuro do overlay na landing. API client já pronto; backend intocado.

## Architecture

### State machine (AuthOverlay)

```text
                    ┌─────────────┐
         ┌─────────►│    login    │◄────────┐
         │          └──────┬──────┘         │
         │  "Esqueci..."   │                │ "Voltar ao login"
         │                 ▼                │
         │          ┌─────────────┐         │
         │          │   forgot    │─────────┤
         │          └──────┬──────┘         │
         │    sucesso +     │                │
         │    "Já tenho      │ "Nova senha"  │
         │     token"        ▼                │
         │          ┌─────────────┐         │
         └──────────│    reset    │─────────┘
                    └─────────────┘
```

### UI por view

| View | Campos | Ação primária | API |
|------|--------|---------------|-----|
| `login` | email, password | Entrar | `login()` (existente) |
| `forgot` | email | Enviar instruções | `forgotPassword({ email })` |
| `reset` | token, new_password, confirm | Redefinir senha | `resetPassword({ token, new_password })` |

### Comportamentos

1. **Forgot success**: exibir `response.message` (genérico). Se `response.reset_token` presente (dev), exibir aviso discreto com token copiável — não persistir.
2. **Reset success**: mensagem de sucesso + botão "Ir para login" que limpa campos e volta à view `login`.
3. **Validação cliente**: email não vazio + `@`; senha ≥ 6; confirmação igual.
4. **Erros API**: mapear `Error.message` do client (`detail` do FastAPI) para português quando necessário.
5. **Reset overlay**: ao `show` passar de false→true, resetar para view `login` e limpar campos (estender watch existente).

### Estilo

Reutilizar classes existentes: `.auth-card`, `.auth-input`, `.auth-btn`, `.auth-error`. Adicionar:
- `.auth-link` — link texto "Esqueci minha senha" / navegação secundária
- `.auth-success` — feedback positivo (verde/neutro)
- `.auth-hint` — bloco dev-only para token

### Backend / contrato

Contrato em [contracts/auth-reset-api.md](./contracts/auth-reset-api.md). **Gap analysis**: nenhum gap bloqueante identificado. Campos e status codes compatíveis com a spec.

### Fora de escopo (confirmado)

- Envio de email SMTP/SES
- Nova rota Vue dedicada (`/reset-password`) — opcional futura
- Testes automatizados E2E
- Alterações em `lp.html` (login via `LoginView` cobre o fluxo SPA)

## Implementation Phases

### Phase A — Estrutura e navegação (P2 parcial)
- Adicionar `view: Ref<'login'|'forgot'|'reset'>`
- Títulos dinâmicos no `.auth-title`
- Links de navegação entre views
- Reset de estado no `watch(show)`

### Phase B — Forgot password (P1)
- Formulário email + submit `forgotPassword`
- Loading / error / success states
- Exibição condicional de `reset_token` quando retornado

### Phase C — Reset password (P1)
- Formulário token + senha + confirmação
- Validação local antes do POST
- Submit `resetPassword` + feedback

### Phase D — Polimento
- `aria-label` por view no dialog
- Enter key nos formulários forgot/reset
- Mensagens PT-BR consistentes com login existente

## Complexity Tracking

> Nenhuma violação da constitution que exija justificativa.

## Generated Artifacts

| Artifact | Path |
|----------|------|
| Research | [research.md](./research.md) |
| Data model | [data-model.md](./data-model.md) |
| API contract | [contracts/auth-reset-api.md](./contracts/auth-reset-api.md) |
| Quickstart | [quickstart.md](./quickstart.md) |

**Próximo passo**: `/speckit-tasks`
