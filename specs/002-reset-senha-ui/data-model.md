# Data Model: Reset de Senha (UI)

**Feature**: `002-reset-senha-ui` | **Scope**: Estado local do componente (sem entidades persistidas no frontend)

## View State

| Campo | Tipo | Valores | Descrição |
|-------|------|---------|-----------|
| `view` | union | `login` \| `forgot` \| `reset` | Tela ativa no overlay |
| `loading` | boolean | — | Submit em andamento |
| `error` | string | — | Mensagem de erro (validação ou API) |
| `success` | string | — | Mensagem de sucesso (forgot/reset) |

## Form Fields by View

### login (existente)

| Campo | Tipo | Validação |
|-------|------|-----------|
| `email` | string | não vazio |
| `password` | string | não vazio |

### forgot

| Campo | Tipo | Validação |
|-------|------|-----------|
| `forgotEmail` | string | não vazio; contém `@` |

### reset

| Campo | Tipo | Validação |
|-------|------|-----------|
| `resetToken` | string | não vazio; min 20 (alinhado ao schema backend) |
| `newPassword` | string | length ≥ 6 |
| `confirmPassword` | string | igual a `newPassword` |

## Ephemeral API Response (não persistido)

| Campo | Origem | Uso na UI |
|-------|--------|-----------|
| `message` | forgot / reset response | Exibir ao usuário |
| `reset_token` | forgot response (opcional) | Hint dev + pré-preencher `resetToken` ao ir para reset |

## State Transitions

```text
INIT (overlay opens)     → view=login, campos limpos
login + "Esqueci..."     → view=forgot, success/error limpos
forgot + submit OK       → success=message; opcional reset_token
forgot + "Já tenho token"→ view=reset
forgot + "Voltar"        → view=login
reset + submit OK        → success=message; opção voltar login
reset + "Voltar"         → view=login ou forgot
overlay close/reopen     → view=login, todos campos limpos
```

## Error Mapping

| Condição | Mensagem UI |
|----------|-------------|
| Email vazio (forgot) | `Informe seu email.` |
| Email sem @ | `Email inválido.` |
| Senhas diferentes | `As senhas não coincidem.` |
| Senha < 6 | `A senha deve ter pelo menos 6 caracteres.` |
| API 400 reset | `Token inválido ou expirado.` (ou detail do servidor) |
| Rede / 5xx | `Erro de conexão. Tente novamente.` |
