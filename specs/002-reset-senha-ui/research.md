# Research: Reset de Senha na Interface

**Feature**: `002-reset-senha-ui` | **Date**: 2026-06-24

## R1 — Onde implementar o fluxo de UI?

**Decision**: Estender `AuthOverlay.vue` com máquina de estados interna (`login` | `forgot` | `reset`).

**Rationale**:
- `LoginView.vue` já embute `AuthOverlay` com `show=true`.
- Spec exige link no overlay de login; componente único evita duplicação.
- Constitution exige diff mínimo.

**Alternatives considered**:
| Alternativa | Rejeitada porque |
|-------------|------------------|
| Novo componente `PasswordResetFlow.vue` | Mais arquivos sem ganho claro para 3 telas simples |
| Nova rota `/reset-password` | Spec não exige; overlay cobre MVP; rota pode vir depois |
| Alterar `lp.html` estático | Fora do padrão Vue; login SPA já em `/login` |

## R2 — Como obter token em desenvolvimento sem email?

**Decision**: Quando a API retornar `reset_token` (env `PASSWORD_RESET_RETURN_TOKEN=true`), exibir hint copiável na tela de sucesso do forgot e link "Já tenho o token" para view `reset`.

**Rationale**:
- Backend já suporta `reset_token` opcional na resposta.
- Em produção (`PASSWORD_RESET_RETURN_TOKEN=false`), campo não aparece — seguro por padrão.
- Atende SC-005 sem infra de email.

**Alternatives considered**:
| Alternativa | Rejeitada porque |
|-------------|------------------|
| Console.log do token | UX ruim para testadores não-dev |
| Sempre pedir token manual de suporte | Não viável em dev |
| Implementar email nesta feature | Fora de escopo (FR-009) |

## R3 — Validação de senha e erros

**Decision**: Validar no cliente: senha ≥ 6 chars, confirmação igual; confiar em `api/client.ts` para propagar `detail` do FastAPI como `Error.message`.

**Rationale**:
- Alinhado a `LoginRequest` / `ResetPasswordRequest` (min 6) no backend.
- Mensagem 400 do reset: `"Token inválido ou expirado"` — já em português.

**Alternatives considered**:
| Alternativa | Rejeitada porque |
|-------------|------------------|
| Biblioteca de validação (Zod/Vuelidate) | Over-engineering para 3 campos |
| Duplicar mensagens no backend | Backend fora de escopo |

## R4 — Gap de contrato backend?

**Decision**: Nenhuma alteração de backend necessária.

**Rationale**:
- `POST /api/auth/forgot-password` → `{ email }` → `{ message, reset_token? }`
- `POST /api/auth/reset-password` → `{ token, new_password }` → `{ message }`
- Client functions `forgotPassword` / `resetPassword` já tipadas em `auth.ts`.

**Alternatives considered**: N/A — contrato verificado e suficiente.

## R5 — Persistência de token entre telas?

**Decision**: Não persistir token em localStorage/sessionStorage. Opcionalmente pré-preencher campo token na memória da sessão do overlay ao navegar forgot→reset após sucesso com `reset_token`.

**Rationale**:
- Reduz risco de token órfão no browser.
- UX melhor em dev quando token vem na resposta.

**Alternatives considered**:
| Alternativa | Rejeitada porque |
|-------------|------------------|
| Query param `?token=` na URL | Pode vazar em logs/referrer; fase futura se necessário |
