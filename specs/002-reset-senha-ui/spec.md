# Feature Specification: Reset de Senha na Interface

**Feature Branch**: `002-reset-senha-ui`

**Created**: 2026-06-24

**Status**: Draft

**Input**: Permitir que o aluno solicite reset de senha e defina nova senha pela interface (link no overlay de login, formulários de email e token+senha). O backend de reset já existe; esta feature cobre apenas a experiência do usuário na interface.

## User Scenarios & Testing

### User Story 1 - Solicitar reset por email (Priority: P1)

Como aluno que esqueceu a senha, quero informar meu email na tela de login para receber instruções de recuperação, para voltar a acessar a plataforma sem contatar o suporte.

**Why this priority**: É o ponto de entrada do fluxo; sem ele o aluno não inicia a recuperação.

**Independent Test**: Na tela de login, clicar em "Esqueci minha senha", informar email válido e ver confirmação genérica de sucesso, independentemente de o email existir no sistema.

**Acceptance Scenarios**:

1. **Given** overlay de login aberto, **When** clico em "Esqueci minha senha", **Then** vejo formulário para informar email.
2. **Given** email em formato válido preenchido, **When** envio a solicitação, **Then** vejo mensagem genérica de confirmação (ex.: "Se o email existir, enviaremos instruções").
3. **Given** email em formato inválido ou vazio, **When** tento enviar, **Then** vejo mensagem de validação sem chamar o servidor (ou erro claro após tentativa).
4. **Given** falha de rede ou servidor, **When** envio a solicitação, **Then** vejo mensagem de erro amigável e posso tentar novamente.

---

### User Story 2 - Definir nova senha com token (Priority: P1)

Como aluno que recebeu um token de reset (por email em produção, ou exibido em ambiente de desenvolvimento), quero informar o token e a nova senha para concluir a recuperação e fazer login.

**Why this priority**: Completa o fluxo de valor — sem esta etapa a solicitação não resulta em acesso restaurado.

**Independent Test**: Acessar tela de nova senha, informar token válido + senha nova (mín. 6 caracteres) + confirmação, submeter e ver sucesso; em seguida fazer login com a nova senha.

**Acceptance Scenarios**:

1. **Given** tela de nova senha, **When** informo token, nova senha e confirmação iguais (mín. 6 caracteres), **Then** vejo mensagem de sucesso e orientação para entrar.
2. **Given** token inválido ou expirado, **When** submeto o formulário, **Then** vejo mensagem de erro sem revelar detalhes internos do sistema.
3. **Given** senha e confirmação diferentes, **When** submeto, **Then** vejo erro de validação antes ou após envio, sem alterar a senha.
4. **Given** reset concluído com sucesso, **When** volto ao login e uso a nova senha, **Then** autentico normalmente.

---

### User Story 3 - Navegar entre login, solicitação e nova senha (Priority: P2)

Como aluno, quero voltar ao login ou alternar entre as etapas do reset sem perder contexto, para concluir o fluxo com clareza.

**Why this priority**: Melhora usabilidade; não bloqueia o MVP se os fluxos P1 estiverem acessíveis.

**Independent Test**: De "Esqueci senha" voltar ao login; de "Nova senha" voltar ao login ou à solicitação de email.

**Acceptance Scenarios**:

1. **Given** formulário de solicitação de reset, **When** clico em "Voltar ao login", **Then** retorno ao formulário de entrada sem fechar o overlay (ou com comportamento consistente documentado).
2. **Given** formulário de nova senha, **When** clico em link para solicitar novo token, **Then** posso reiniciar o fluxo de email.
3. **Given** overlay fechado e reaberto, **When** abro login novamente, **Then** inicio no estado padrão (tela de login), salvo rota dedicada de reset com token na URL.

---

### Edge Cases

- Usuário solicita reset para email não cadastrado: mesma mensagem genérica de sucesso (não enumerar emails).
- Token já utilizado: mensagem de token inválido ou expirado.
- Senha abaixo do mínimo (6 caracteres): validação clara no cliente e mensagem do servidor se aplicável.
- Múltiplas solicitações seguidas: apenas o token mais recente válido (comportamento já garantido pelo backend).
- Ambiente sem envio de email: fluxo ainda utilizável quando o token for obtido por canal alternativo (ex.: dev ou suporte).

## Requirements

### Functional Requirements

- **FR-001**: Interface MUST exibir link ou ação "Esqueci minha senha" a partir da tela de login existente.
- **FR-002**: Interface MUST permitir solicitar reset informando apenas email, com validação de formato.
- **FR-003**: Após solicitação bem-sucedida, interface MUST exibir mensagem genérica que não confirme existência do email.
- **FR-004**: Interface MUST permitir informar token de reset, nova senha e confirmação de senha.
- **FR-005**: Interface MUST validar que nova senha e confirmação coincidem antes de concluir o reset.
- **FR-006**: Interface MUST exibir feedback claro para sucesso, erro de validação, token inválido/expirado e falha de conexão.
- **FR-007**: Interface MUST permitir retornar ao login a partir das telas de reset.
- **FR-008**: Interface MUST reutilizar o serviço de autenticação já exposto pelo backend (sem duplicar lógica de negócio no frontend).
- **FR-009**: Escopo MUST excluir implementação de envio de email transacional nesta feature (assumido fora de escopo ou ambiente dev).

### Key Entities

- **Solicitação de reset**: email informado pelo usuário; resposta sempre genérica ao usuário.
- **Token de reset**: valor opaco fornecido ao usuário por canal externo (email, suporte ou dev); usado uma vez com prazo de validade.
- **Nova credencial**: senha substituta com requisito mínimo de comprimento já definido na plataforma.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Aluno completa solicitação de reset em até 3 interações a partir do login.
- **SC-002**: Aluno com token válido define nova senha e consegue login na tentativa seguinte em 100% dos casos de teste manuais felizes.
- **SC-003**: Em testes com email inexistente, 0% das respostas da interface indicam explicitamente que o email não está cadastrado.
- **SC-004**: 100% dos erros de token inválido/expirado exibem mensagem compreensível em português, sem jargão técnico.
- **SC-005**: Fluxo utilizável em ambiente de desenvolvimento sem provedor de email (token obtido por mecanismo de dev documentado no plano técnico).

## Assumptions

- Endpoints de forgot-password e reset-password já estão implementados e estáveis no backend.
- Funções de cliente HTTP (`forgotPassword`, `resetPassword`) já existem em `frontend-vue/src/api/auth.ts`.
- Requisito de senha: mínimo 6 caracteres, alinhado ao cadastro/login atual.
- Idioma da interface: português.
- Envio de email em produção será tratado em feature ou infra separada; nesta entrega o foco é UI + integração com API.
- Estilo visual segue o overlay de login existente (`AuthOverlay`).
