# Quickstart: Validar Reset de Senha na UI

**Feature**: `002-reset-senha-ui` | **Pré-requisito**: implementação concluída em `AuthOverlay.vue`

## Setup

```bash
# Terminal 1 — backend
cd backend
source .venv/bin/activate   # se aplicável
# Em backend/.env para dev:
# PASSWORD_RESET_RETURN_TOKEN=true
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2 — frontend
cd frontend-vue
npm run dev
```

Usuário de teste deve existir no MongoDB (ex.: via `util/create_user.py`).

## Cenário 1 — Solicitar reset (email existente)

1. Abrir `http://localhost:5173/login`
2. Clicar **Esqueci minha senha**
3. Informar email cadastrado → **Enviar**
4. **Esperado**: mensagem genérica de confirmação (não confirma que email existe)
5. Com `PASSWORD_RESET_RETURN_TOKEN=true`: token visível no hint dev

## Cenário 2 — Solicitar reset (email inexistente)

1. Fluxo forgot com email não cadastrado
2. **Esperado**: mesma mensagem genérica do cenário 1 (SC-003)

## Cenário 3 — Redefinir senha com token válido

1. Obter token (hint dev ou nova solicitação forgot)
2. Ir para **Nova senha** / preencher token
3. Nova senha ≥ 6 chars + confirmação igual → **Redefinir**
4. **Esperado**: "Senha atualizada com sucesso"
5. Voltar ao login → entrar com nova senha
6. **Esperado**: login OK (SC-002)

## Cenário 4 — Token inválido

1. Informar token aleatório na tela reset
2. **Esperado**: "Token inválido ou expirado" (SC-004)

## Cenário 5 — Validação cliente

| Ação | Esperado |
|------|----------|
| Forgot com email vazio | Erro de validação |
| Reset com senhas diferentes | "As senhas não coincidem." |
| Reset com senha < 6 chars | Erro de comprimento mínimo |

## Cenário 6 — Navegação

1. Forgot → **Voltar ao login** → formulário de entrada
2. Fechar overlay / reabrir → estado inicial login
3. Forgot sucesso → **Já tenho o token** → tela reset com token pré-preenchido (se dev)

## Produção

Com `PASSWORD_RESET_RETURN_TOKEN=false`, cenários 1 e 3 exigem token obtido por canal externo (email futuro ou suporte).
