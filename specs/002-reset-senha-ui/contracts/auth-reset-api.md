# Contract: Auth Reset API (consumo frontend)

**Feature**: `002-reset-senha-ui` | **Status**: Existente — sem alterações previstas

Base URL: mesma origem (`VITE_API_BASE_URL` ou proxy Vite em dev)

## POST /api/auth/forgot-password

**Request**

```json
{
  "email": "aluno@exemplo.com"
}
```

**Response 200** (sempre genérico para o usuário)

```json
{
  "message": "Se o email existir, enviaremos instruções para reset de senha."
}
```

**Response 200** (dev — `PASSWORD_RESET_RETURN_TOKEN=true`)

```json
{
  "message": "Se o email existir, enviaremos instruções para reset de senha.",
  "reset_token": "<url-safe-token>"
}
```

**Client**: `forgotPassword({ email })` → `Promise<GenericMessageResponse>`

**UI rules**:
- Exibir apenas `message` como confirmação principal.
- Se `reset_token` presente, mostrar bloco auxiliar (dev); nunca tratar ausência de token como erro.

---

## POST /api/auth/reset-password

**Request**

```json
{
  "token": "<token-from-email-or-dev>",
  "new_password": "novaSenha123"
}
```

**Response 200**

```json
{
  "message": "Senha atualizada com sucesso."
}
```

**Response 400**

```json
{
  "detail": "Token inválido ou expirado"
}
```

**Client**: `resetPassword({ token, new_password })` → `Promise<GenericMessageResponse>`

**UI rules**:
- Mapear 400 para mensagem amigável em português.
- Após sucesso, orientar usuário a fazer login com nova senha.

---

## Validation (backend — referência para UI)

| Campo | Regra |
|-------|-------|
| `email` | EmailStr (Pydantic) |
| `token` | min 20, max 512 |
| `new_password` | min 6, max 128 |

## Auth header

Endpoints são **públicos** (sem Bearer token).
