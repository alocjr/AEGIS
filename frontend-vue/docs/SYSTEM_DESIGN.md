# AEGIS · `frontend-vue` — System Design e Auditoria de Consistência

**Escopo analisado:** `frontend-vue/` (35 views, 5 componentes, 16 módulos de API, 30.898 linhas de `src/`)
**Data:** 18 de agosto de 2026 · **Commit base:** `d99b26b`

---

## Sumário executivo

O `frontend-vue` é uma SPA Vue 3 + TypeScript que entrega **quatro produtos dentro de um mesmo shell**: a mentoria (trilhas, agenda, materiais, quiz), o AI Hub estratégico (Maturidade → SWOT/TOWS → OKR → Canvas → Mapa Estratégico), a Governança de IA (inventário, avaliação de risco, gates) e o painel administrativo.

A **espinha dorsal está correta e é a melhor parte do projeto**: camada de API isolada (zero `fetch` solto nas views, zero `any` em toda a base), autorização em três eixos (sessão, papel, ferramenta liberada) centralizada num único `beforeEach`, telemetria declarativa e um domínio estratégico modelado com rastreabilidade real entre artefatos.

O que destoa está quase todo em **uma camada só: a de apresentação**. Não existe biblioteca de componentes — 35 views reimplementam botão, card, modal, tabela e estados de carregamento com CSS próprio (13.288 linhas de CSS dentro de arquivos `.vue`, 43% do código-fonte). Isso produziu três sistemas de tokens concorrentes, 82 cores fora do sistema, 27 tamanhos de fonte e secundárias de texto que reprovam em contraste WCAG em 227 pontos do produto.

Há também **dois bloqueios de entrega**: o build de produção não passa (48 erros de tipo registrados em `tsc5.txt`) e o cache está desligado para todos os assets.

**41 itens destoantes** catalogados adiante — 4 críticos, 12 altos, 18 médios, 7 baixos — com ajuste proposto e plano em 4 ondas.

---

# PARTE I — SYSTEM DESIGN

## 1. Stack e cadeia de build

| Camada | Escolha | Observação |
|---|---|---|
| Framework | Vue 3.5 (`<script setup>`, Composition API) | uso idiomático e consistente |
| Linguagem | TypeScript 5.6, `strict: true`, `noUncheckedIndexedAccess: true` | configuração exigente — e é ela que expõe os 48 erros atuais |
| Build | Vite 6, alias `@ → src` | `sourcemap` só fora de produção |
| Estado | Pinia 2 | 2 stores apenas |
| Rotas | vue-router 4, `createWebHistory`, lazy por rota | 39 rotas |
| Estilo | CSS puro com custom properties, `<style scoped>` | sem pré-processador, sem utilitários |
| Dependência morta | `plotly.js-dist-min` (4,7 MB) | não importada em lugar nenhum |

O build é `vue-tsc -b && vite build`. Em desenvolvimento o Vite faz proxy de `/api`, `/static` e `/material_gratuito` para `http://127.0.0.1:8000`. Em produção o FastAPI detecta `frontend-vue/dist/index.html` e passa a servir a SPA.

## 2. Arquitetura em camadas

```
                    ┌──────────────────────────────────────────┐
   Navegador  ─────►│  index.html → main.ts → App.vue          │
                    │  createPinia() · router · main.css       │
                    └────────────────┬─────────────────────────┘
                                     │
         ┌───────────────────────────┼───────────────────────────┐
         │                           │                           │
  ┌──────▼──────┐            ┌───────▼────────┐          ┌───────▼───────┐
  │ DefaultLayout│            │  AdminLayout   │          │ rotas soltas  │
  │  Topbar fixa │            │ sidebar 220px  │          │ /login  /401  │
  │  (pílulas)   │            │  (sem topbar)  │          │               │
  └──────┬───────┘            └───────┬────────┘          └───────────────┘
         │                            │
    25 views de produto          10 views de admin
         │                            │
         └────────────┬───────────────┘
                      │
        ┌─────────────▼──────────────┐      ┌────────────────────────┐
        │  stores/  (Pinia)          │      │  lib/                  │
        │   auth · courses           │◄────►│   tools · track        │
        └─────────────┬──────────────┘      │   strategicMapGraph    │
                      │                     │   accessFormat         │
        ┌─────────────▼──────────────┐      └────────────────────────┘
        │  api/  (16 módulos)        │
        │  client.ts: fetch, cookie, │
        │  ApiError, 401 → /401      │
        └─────────────┬──────────────┘
                      │  cookie HttpOnly · credentials: include
                ┌─────▼──────┐
                │  FastAPI   │
                └────────────┘
```

**Regra de dependência respeitada:** views → api → client. Nenhuma view chama `fetch` diretamente (a única exceção é `lib/track.ts`, intencional: telemetria *fire-and-forget* que não pode propagar erro de rede para a UI).

## 3. Mapa de rotas e domínios

### 3.1 Público / mentoria (`DefaultLayout`)

| Rota | View | LOC | Papel |
|---|---|---:|---|
| `/` | LandingView | 54 | embute `public/lp.html` num `<iframe>` |
| `/programa` | ProgramaView | 1.949 | progresso do aluno na trilha, check de materiais, conclusão de encontro |
| `/materiais` | MateriaisView | 330 | biblioteca de apoio por encontro |
| `/agenda` | AgendaView | 601 | calendário da jornada |
| `/trilhas` · `/trilhas/:slug` | TrilhasView · TrilhaShowcaseView | 27 · 812 | catálogo e vitrine de trilha |
| `/quiz/:encontroId` · `/quiz/q/:quizId` | QuizView | 1.225 | aplicação do quiz |
| `/quiz-respostas` | QuizRespostasView | 688 | histórico de respostas |

### 3.2 AI Hub — a cadeia estratégica

| Rota | View | LOC | Artefato produzido |
|---|---|---:|---|
| `/ai-maturity` | AiMaturityListView | 443 | lista de autoavaliações |
| `/ai-maturity/new` · `/:id/edit` | AiMaturityView | 1.318 | **Diagnóstico** (4 dimensões × 3 tiers) |
| `/ai-maturity/:id` | AiMaturityDetailView | 972 | resultado + geração de SWOT |
| `/swot/:id?` | SwotAnalysisView | 2.255 | **SWOT + TOWS** (4 quadrantes, pilares, watchlist) |
| `/okrs` · `/okrs/:id` | OkrCyclesListView · OkrCycleEditorView | 463 · 1.246 | **Ciclo de OKR** (objetivos + KRs) |
| `/projetos` · `/projetos/:id` | ProjetosListView · ProjetoCanvasView | 1.137 · 2.105 | **AI Canvas** do projeto |
| `/mapa-estrategico` | MapaEstrategicoView | 1.624 | **Mapa** com lentes e linhagem |

### 3.3 Governança de IA

| Rota | View | LOC | Papel |
|---|---|---:|---|
| `/governanca/dashboard` | GovernanceDashboardView | 448 | métricas, profundidade, evidências |
| `/governanca/inventario` | GovernanceInventoryView | 376 | inventário de sistemas de IA |
| `/governanca/sistemas/:id` | GovernanceSystemView | 888 | ficha do sistema + avaliação de risco |
| `/governanca/gate/:id` | GovernanceGateView | 517 | checklist e decisão do gate |

### 3.4 Organização e administração

`/organizacao/usuarios` (OrgMembersView, 595) · `/admin` + 9 subrotas (dashboard, acessos, trilhas, materiais/prompts da landing, usuários, alunos, progresso, progresso do aluno, quiz).

## 4. Modelo de acesso — três eixos

Toda a autorização de navegação vive num único `router.beforeEach` (`router/index.ts:105`), o que é o desenho certo. São três verificações independentes:

1. **Sessão** — cookie HttpOnly. `auth.loadUser()` roda uma vez por sessão de router; sem sessão em rota protegida → `/401`.
2. **Papel** — `is_admin` (prefixo `/admin`) e `is_org_admin` (prefixo `/organizacao`).
3. **Ferramenta liberada** — `lib/tools.ts` mapeia prefixo de rota → id de ferramenta (`maturity`, `swot`, `okr`, `canvas`, `strategic_map`, `governance`). Se o usuário não tem a ferramenta em `user.tools`, vai para `/acesso-negado?tool=…`.

Há ainda uma quarta regra, de **destino**: em `/`, um usuário logado com trilha vai para `/programa`; sem trilha, cai na primeira ferramenta liberada segundo `TOOL_HOME_ORDER`. E-mail não verificado é desviado para `/login`.

No cliente, `api/client.ts` fecha o ciclo: um `401` em qualquer chamada que **não** seja sonda de sessão (`/api/auth/me|login|logout`) dispara logout e `window.location.assign('/401')`.

## 5. Camada de API

16 módulos, ~2.182 linhas, 111 funções, 142 tipos exportados. Contrato de erro unificado em `ApiError { message, code, status }`, com suporte ao formato `detail: { code, message }` do backend para erros de negócio com código estável.

| Módulo | Endpoint base | Funções | Tipos |
|---|---|---:|---:|
| `admin` | `/api/admin/*` | 33 | 25 |
| `governance` | `/api/governance/*` | 18 | 32 |
| `swotAnalysis` | `/api/swot-analysis` | 8 | 15 |
| `canvasProjects` | `/api/canvas-projects` | 8 | 9 |
| `okrs` | `/api/okrs` | 8 | 11 |
| `auth` | `/api/auth/*` | 7 | 6 |
| `client` | — | 7 (get/post/put/patch/del/postFormData/apiRequest) | 1 |
| `maturity` | `/api/maturity` | 5 | 18 |
| `quiz` · `orgAdmin` · `strategicMap` · demais | vários | 25 | 45 |

## 6. Estado

**Pinia (global, 2 stores):** `auth` (usuário, `loaded`, trilha corrente, `hasTool`) e `courses` (catálogo + cache por slug).

**Local por view (dominante):** cada tela de editor mantém seu próprio `loading` / `error` / `saveState` / formulário reativo. 28 views declaram `loading`, 26 declaram `error`.

**Autosave:** 5 views gravam sozinhas (Maturidade, SWOT, Canvas, OKR, Governança). O padrão maduro é o do OKR — debounce de 1.200 ms, fila de uma gravação, `beforeunload` e `onBeforeRouteLeave`.

## 7. A cadeia de valor rastreável

O diferencial do produto é que os artefatos não são telas soltas — eles se referenciam:

```
  Maturidade ──► SWOT ──► TOWS ──► OKR ──────┐
   (4 dim.)      (4 quad.)  (4 cruz.)         ├──► Mapa Estratégico
                     └────► AI Canvas ────────┘     (lentes pan/ges/lin,
                                                     linhagem por nó)
                     Governança ──► Gates ──► Evidências
```

- `AiMaturityDetailView` chama `createSwotFromMaturity` — o diagnóstico vira SWOT.
- `SwotAnalysisView` reconstrói TOWS sob demanda (`updateSwotAnalysis(..., { rebuildTows })`).
- `OkrCycleEditorView` e `ProjetoCanvasView` importam iniciativas TOWS da SWOT.
- `MapaEstrategicoView` consome `fetchStrategicMap` e monta o grafo em `lib/strategicMapGraph.ts` (1.201 linhas de lógica pura, testável, fora da view) — **este é o padrão arquitetural que o resto do projeto deveria seguir.**

## 8. Design system atual

`assets/main.css` define **32 tokens**: 2 famílias tipográficas, escala de cinzas `--k0…--k9`, dourado da marca, bege e verde de estado, bordas, 3 pares de estado (success/warn/low) e 2 medidas de layout (`--bar-h: 64px`, `--sw: 340px`). Todos os 32 são efetivamente usados — nenhum token morto.

O problema não é o que existe: é o que foi criado **por fora**. Ver DS-01 a DS-07.

## 9. Telemetria

`lib/track.ts` mapeia nome de rota → chave de recurso (`maturity.lista`, `swot.editor`, `governance.gate`…) e dispara `POST /api/public/track` com `keepalive`, silenciando falhas. O catálogo é espelho de `backend/app/analytics.py`. `/admin` fica de fora de propósito (painel não é recurso); `Landing` também, porque quem registra é o próprio `lp.js` — evitando contagem dupla.

## 10. Segurança e entrega

- Sessão por **cookie HttpOnly**, nunca token em `localStorage`. ✔
- `public/_headers` com CSP restritiva, HSTS com preload, `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy`. ✔
- Zero `v-html` em toda a base — sem superfície de XSS por template. ✔
- Todos os 9 `target="_blank"` acompanham `rel="noopener"`. ✔
- **Mas**: `Cache-Control: no-cache, no-store, must-revalidate` em `/*` anula o cache de assets com hash (CD-03).

---

# PARTE II — ITENS QUE DESTOAM

Severidade: 🔴 crítico · 🟠 alto · 🟡 médio · ⚪ baixo

## A. Design System

### 🔴 DS-01 · Três sistemas de tokens concorrentes — a marca renderiza dois dourados e duas serifas

`AiMaturityView.vue:591-613` e `SwotAnalysisView.vue:1168-1178` **redefinem tokens globais com outros valores**:

| Token | Global (`main.css`) | Maturidade / SWOT | Mapa Estratégico | Canvas |
|---|---|---|---|---|
| `--gold` | `#9b7e46` | `#c6a15b` | herda | — |
| `--navy` | (via `--k0`) `#0c2340` | `#0e1b33` | `#0c2340` | — |
| `--serif` | Palatino Linotype… | Cambria, Hoefler Text… | herda | — |
| `--ink` | — | `#242a33` | — | `#12232e` |
| `--line` | — | `rgba(198,161,91,.32)` | — | `#d8d2c6` |
| `--muted` | — | `#6e6a60` | `var(--k3)` | — |

Consequência: SWOT e Maturidade são visualmente um produto; Mapa, Governança e Admin são outro. O mesmo nome de token significa coisas diferentes conforme a rota.

**Ajuste.** Decidir qual é a marca — a leitura editorial de SWOT/Maturidade é a que mais se aproxima de "premium, executivo e sóbrio". Promover esses valores a `main.css` sob nomes explícitos (`--brand-navy`, `--brand-gold`, `--brand-serif`, `--ink`, `--line`, `--muted`), remover os quatro blocos locais e migrar as demais telas. Proibir redefinição de token global em `<style scoped>` via revisão de PR.

### 🟠 DS-02 · 82 cores hex distintas em 346 ocorrências fora do sistema

Concentração: `SwotAnalysisView` 52, `ProjetoCanvasView` 48, `ProjetosListView` 47, `AiMaturityView` 38, `GovernanceInventoryView` 14, `GovernanceSystemView` 14, `MapaEstrategicoView` 13.

**Ajuste.** Fechar uma paleta semântica de ~24 tokens (4 superfícies, 4 níveis de texto, 3 bordas, 4 dimensões de maturidade, 5 níveis de maturidade, 4 estados) e substituir por codemod. Travar com `stylelint` (`color-no-hex`) no CI.

### 🟠 DS-03 · Sem escala tipográfica — 27 tamanhos, incluindo fracionários

`13px` (129×), `12px` (125×), `14px` (117×), `11px` (94×), `10px` (29×) … e **`12.5px`, `11.5px`, `10.5px`, `9.5px`, `13.5px`, `14.5px`, `8px`**. Meio pixel não é decisão de design — é resíduo de ajuste visual manual.

**Ajuste.** Escala de 8 degraus em tokens: `--fs-xs 11 / --fs-sm 12 / --fs-base 13 / --fs-md 14 / --fs-lg 16 / --fs-xl 20 / --fs-2xl 26 / --fs-3xl 34`. Zero fracionários.

### 🟠 DS-05 · Terceira família tipográfica, carregada de dentro de um componente

`ProjetoCanvasView.vue:1155` faz `@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk…')` **dentro de `<style scoped>`**, e usa a fonte em 13 declarações. É a única view com identidade tipográfica própria, e o `@import` é uma requisição render-blocking disparada no meio do CSS da rota.

**Ajuste.** Se Space Grotesk entra na marca: `<link rel="preconnect">` + `preload` em `index.html` e token `--display`. Se não entra: remover as 13 declarações e o `@import`. Não deixar como está.

### 🟡 DS-04 · 13 raios de borda e 31 sombras distintas

Raios: 1, 2, 3, 4, 5, 6, 7, 8, 10, 12, 20, 99, 999px. Sombras: 31 valores únicos, incluindo três variações quase idênticas de `0 4px 1Xpx rgba(12,35,64,.08)`.

**Ajuste.** `--r-sm 4 / --r-md 8 / --r-lg 12 / --r-pill 999px`; `--shadow-1` (repouso), `--shadow-2` (elevado), `--shadow-3` (modal).

### 🟡 DS-06 · Variáveis usadas sem definição

- `MateriaisView.vue:287` → `color: var(--k2)` — **`--k2` não existe** (a escala pula de `--k1` para `--k3`). A declaração é inócua: o texto herda a cor do pai. Bug silencioso.
- `LoginView.vue:21` → `var(--navy-deep, #0C1827)` — só funciona pelo fallback.
- `AdminPromptsLandingView` (2×) e `AdminMateriaisLandingView` (2×) → `var(--bg, #f7f5f0)` — idem.

**Ajuste.** Definir `--k2` (ou trocar a chamada por `--k1`), e promover `--navy-deep` e `--bg` a tokens reais.

### 🟡 DS-07 · Oito larguras de página diferentes

520 / 860 / 900 / 920 / 980 / 1000 / 1100 / 1200 px, sem regra.

**Ajuste.** Três larguras: `--w-read 860px` (leitura/formulário), `--w-app 1120px` (painéis e tabelas), full-bleed (mapa, canvas).

## B. Arquitetura de componentes

### 🔴 AR-01 · Não existe biblioteca de componentes

35 views para **5 componentes** (1.153 linhas, 3,7% do código). **13.288 linhas de CSS dentro de arquivos `.vue`** — 43% de todo o `src/`.

Classes reimplementadas do zero, contadas por arquivo distinto:

| Classe | Arquivos | Classe | Arquivos |
|---|---:|---|---:|
| `.error-msg` | 23 | `.card` | 10 |
| `.loading` | 20 | `.input` | 10 |
| `.page-title` | 18 | `.btn-secondary` | 10 |
| `.page-header` | 17 | `.modal-backdrop` | 8 |
| `.wrap` | 12 | `.btn-danger` | 8 |
| `.btn-primary` | 12 | `.data-table` | 6 |
| `.muted` / `.empty` | 11 | `.modal-*` (9 classes) | 4 cada |

**Ajuste — a intervenção de maior alavancagem do projeto.** Criar `src/components/ui/` com 12 primitivos, nesta ordem de impacto:

1. `StateBlock` (loading / empty / error) — mata 43 reimplementações de uma vez
2. `PageHeader` (título + subtítulo + ações) — 35 telas
3. `AppButton` (primary / secondary / danger / ghost / sm) — 30+ telas
4. `AppModal` (com foco, Escape e trap — ver UX-03) — 8 telas
5. `DataTable` + `AppInput`/`FormField` + `AppCard` + `Badge` + `Toolbar` + `Tabs` + `SaveIndicator` + `Toast`

Meta mensurável: reduzir as 13.288 linhas de CSS local para menos de 6.000.

### 🟠 AR-02 · God components

`SwotAnalysisView` 2.255 · `ProjetoCanvasView` 2.105 · `ProgramaView` 1.949 (207 seletores de classe) · `MapaEstrategicoView` 1.624 · `AiMaturityView` 1.318 · `OkrCycleEditorView` 1.246 · `QuizView` 1.225 linhas.

**Ajuste.** O projeto já tem o remédio: `lib/strategicMapGraph.ts` tirou 1.201 linhas de regra de domínio de dentro da view. Replicar — `lib/swotModel.ts`, `lib/canvasModel.ts`, `lib/maturityScore.ts` — e quebrar cada view em seções (`SwotQuadrant.vue`, `TowsMatrix.vue`, `CanvasBand.vue`). Meta: nenhuma view acima de 600 linhas.

### 🟠 AR-03 · Autosave implementado 5 vezes, de 4 maneiras — uma delas com corrida

| View | Debounce | Guarda de concorrência | Proteção ao sair | `saveState` |
|---|---|---|---|---|
| `OkrCycleEditorView` | 1.200 ms | fila de 1 | ✅ `beforeunload` + `onBeforeRouteLeave` | 3 estados |
| `AiMaturityView` | 280 ms | `persisting`/`pendingPersist` | ❌ | 4 estados |
| `SwotAnalysisView` | nenhum | `saving`/`pendingSave` | ❌ | 4 estados |
| `ProjetoCanvasView` | nenhum | `saving`/`pendingSave` | ❌ | 4 estados |
| `GovernanceSystemView` | nenhum | **nenhuma** | ❌ | 4 estados |

`GovernanceSystemView.vue:92` chama `updateAiSystem` sem qualquer guarda: duas edições rápidas disparam dois PATCH concorrentes e a resposta que chegar por último vence — pode ser a mais antiga. É um bug de perda de dado, não um estilo.

**Ajuste.** Um único `composables/useAutosave(fn, { delay })` que padroniza: debounce, fila de uma gravação, união `'idle' | 'saving' | 'saved' | 'error'`, indicador visual e guarda de saída. Adotar nas 5 views.

### 🟡 AR-04 · Domínio duplicado no cliente

- **Membros da organização em dois módulos e dois tipos:** `orgAdmin.listOrgMembers()` → `/api/org-admin/members` (`OrgMember`) e `governance.listOrganizationMembers()` → `/api/governance/organization-members` (`OrganizationMember`).
- **Dimensões de maturidade em 4 lugares:** `AiMaturityDetailView:40-43` (hex cru), `AiMaturityView:47-56` (vars locais), `MapaEstrategicoView:931-934` (vars locais), `strategicMapGraph:150-154` (classes CSS).
- **Rótulos dos quadrantes SWOT em 4 views:** `GovernanceSystemView:38`, `MapaEstrategicoView:60`, `ProjetoCanvasView:216`, `SwotAnalysisView:66`.

**Ajuste.** `src/lib/domain/` como fonte única: `MATURITY_DIMENSIONS` (id, rótulo, abreviação, cor), `SWOT_QUADRANTS`, `TOWS_META`. Parte já vive em `api/swotAnalysis.ts` (`SWOT_PILLARS`, `MATURITY_DIMENSIONS`) — consolidar ali ou migrar tudo para `lib/domain/`, mas em **um** lugar.

### 🟡 AR-05 · `types/index.ts` cobre só um domínio

O diretório `types/` existe e tem 72 linhas — apenas o domínio "curso". Os outros 12 domínios declaram seus tipos dentro de `api/*.ts` (governance 32, admin 25, maturity 18…). Dois lugares para a mesma decisão.

**Ajuste.** Manter a convenção majoritária (tipo junto do módulo de API) e **esvaziar** `types/index.ts`, movendo os tipos de curso para `api/course.ts`. Ou o inverso — mas não os dois.

### 🟡 AR-07 · Duas stacks de frontend no mesmo produto

A landing é HTML/JS estático (`public/lp.html` + `lp.js`, além de `calc.html`, `tutorial-tokens.html`, `universo-da-ia-interativo.html`, `ficcao-realidade-catalogo-interativo.html`) e o app Vue **a embute num `<iframe>`** (`LandingView.vue`), passando `loginBase` e `apiBase` por querystring.

Custos: marca e componentes existem duas vezes; a telemetria precisa de uma exceção documentada (`lib/track.ts` exclui a rota `Landing` para não contar duas vezes); e a home do app não é uma página indexável.

**Ajuste.** Manter a LP estática é legítimo (performance e CSP). Mas servir `/` diretamente no edge/backend e **remover a rota `Landing` do router**, em vez de encapsular num iframe.

### ⚪ AR-06 · Nomenclatura da API mistura três verbos e dois idiomas

Verbos: `fetchX` (18), `getX` (10), `listX` (9). Idioma: `aprovarPortfolio`, `confirmarProfundidade`, `liberarEncontro`, `getProfundidade`, `emptyPilares` convivem com `createGate`, `listAiSystems`. Endpoints: `/api/swot-analysis`, `/api/canvas-projects`, `/api/org-admin` (kebab) vs `/api/okrs`, `/api/maturity`, `/api/governance`.

**Ajuste.** Convenção `list / get / create / update / delete` e identificadores em inglês (português apenas em rótulos de UI). O padrão de endpoint é contrato do backend — registrar como dívida conjunta, não mudar unilateralmente.

## C. UX e fluxo

### 🟠 UX-01 · Perda de dados silenciosa em 4 editores

SWOT, Canvas, Maturidade e Governança não avisam ao sair com gravação pendente. Só `OkrCycleEditorView` registra `beforeunload` e `onBeforeRouteLeave`. Em telas onde o usuário passa meia hora preenchendo um diagnóstico, um clique na topbar pode descartar a última edição.

**Ajuste.** Guarda embutida no `useAutosave` (AR-03) — resolve os quatro de uma vez.

### 🟡 UX-02 · Estados de carregamento, vazio e erro artesanais

28 views declaram `loading`, 26 declaram `error`, cada uma com marcação e microcópia próprias: `"Carregando..."` (18×) convive com `"Carregando…"`, `"Carregando trilhas..."`, `"Carregando o mapa…"`, `"Carregando diagnóstico…"` — **reticências ASCII e Unicode misturadas no mesmo produto**. Nenhuma tela usa skeleton.

**Ajuste.** `<StateBlock :state="…">` com cópia padrão e skeleton opcional. Guia de microcópia: reticências tipográficas (`…`) sempre; "Carregando…" sem complemento, porque o contexto já é a tela.

### 🟡 UX-03 · Modais sem contrato de acessibilidade

8 views implementam modal (`.modal-backdrop`); apenas 2 tratam `Escape`; nenhuma tem focus-trap, retorno de foco ao fechar, ou `role="dialog"` + `aria-modal` de forma consistente. Com teclado, o foco continua navegando o conteúdo atrás do modal.

**Ajuste.** `AppModal` único: `role="dialog" aria-modal="true"`, trap de foco, `Escape`, restauração do foco de origem, `inert`/`aria-hidden` no conteúdo de fundo, bloqueio de scroll.

### 🟡 UX-04 · Menu do admin não reflete o router — e duas telas são stubs em produção

`AdminLayout.vue` expõe **7** destinos; o router declara **10** rotas em `/admin`. `/admin/alunos` e `/admin/progresso` só existem por URL direta — e ambas são placeholders: *"Gestão de alunos (em migração)"* e *"Progresso dos alunos (em migração)"* (14 linhas cada), servidos em produção.

**Ajuste.** Concluir ou remover as duas telas; derivar o menu de uma constante compartilhada com o router, para que menu e rotas não possam divergir de novo.

### 🟡 UX-05 · Dois padrões de navegação — e uma exceção sem par no menu

A área logada usa topbar fixa de 64px com pílulas; `/admin` usa sidebar escura de 220px **sem topbar, sem marca e sem caminho de volta para as ferramentas do AI Hub** (só um "← Início"). São dois produtos visuais para o mesmo usuário — um admin da plataforma que também usa as ferramentas troca de linguagem visual ao navegar.

Além disso, em `Topbar.vue:40-50` o link do SWOT é o único que **não** é `RouterLink`: é `<a href="/swot">` com `preventDefault`, `router.push` manual e fallback `window.location.assign('/swot')` em caso de erro. Os outros 8 itens são `RouterLink` simples.

**Ajuste.** Unificar o shell: mesma topbar em todo o produto, com sidebar contextual dentro do `/admin`. E converter o item SWOT em `RouterLink` — se o `try/catch` existe por causa de uma falha real de navegação, tratar a causa (provavelmente o parâmetro opcional `/swot/:id?`), não o sintoma.

### 🟡 UX-07 · Não existe rota 404

O router não declara catch-all. Qualquer caminho inválido resulta em tela em branco dentro do layout.

**Ajuste.** `{ path: '/:pathMatch(.*)*', name: 'NotFound', component: NotFoundView }`, reaproveitando o layout de estado de acesso do UX-06.

### ⚪ UX-06 · Dois tratamentos visuais para o mesmo tipo de evento

`/401` (`UnauthorizedView`) é uma ilustração de tela cheia sobre `#0c1827`, com botões em hex cru (`#9b7e46`, `#b8975a`, `#e2e2e7`), sem topbar e sem tipografia da marca. `/acesso-negado` (`ToolDisabledView`) é um card claro, discreto, com `var(--serif)`. Mesma família de evento — acesso barrado — resolvida de dois jeitos opostos.

**Ajuste.** Um `AccessStateLayout` com variantes `401`, `tool-disabled` e `404`.

## D. Responsividade e acessibilidade

### 🟠 AC-01 · 27 dos 42 arquivos de UI não têm nenhuma media query

Sem qualquer tratamento responsivo: **todo o `/admin`** (10 telas), **toda a Governança** (4 telas), o editor de OKR, `OrgMembersView`, `AiMaturityListView`, `AdminLayout` (sidebar rígida de 220px) e os 4 componentes de landing.

Onde existe responsividade, há **13 breakpoints diferentes**: 520, 560, 640, 700, 720, 760, 800, 820, 860, 900, 980, 1100, 1180px.

**Ajuste.** Três breakpoints em tokens (`640` / `1024` / `1280`). Prioridade de conserto: (1) `AdminLayout` → sidebar vira drawer abaixo de 1024; (2) `DataTable` → scroll horizontal contido, e cards empilhados abaixo de 640; (3) formulários de Governança e OKR em coluna única.

### 🟠 AC-02 · Texto secundário reprova em contraste WCAG AA — em 227 pontos

Contraste real dos tokens sobre o fundo padrão `--k9 #f8f8f6`:

| Token | Valor | Contraste | WCAG AA (texto normal) |
|---|---|---:|---|
| `--k3` | `#505050` | 7,58:1 | ✅ |
| `--k4` | `#7a7a7a` | 4,04:1 | ❌ (passa só em texto grande) |
| **`--k5`** | **`#a6a6a6`** | **2,29:1** | ❌ **reprova mesmo em texto grande** |
| `--k6` | `#c8c8c8` | 1,57:1 | ❌ |
| `--gold` | `#9b7e46` | 3,61:1 | ❌ |
| `--gold2` | `#b8975a` | 2,59:1 | ❌ |
| `--success` | `#1e8a4f` | 4,11:1 | ❌ (marginal) |
| `--warn` | `#c17a2c` | 3,24:1 | ❌ |

Uso real: **`color: var(--k5)` aparece 227 vezes em 29 arquivos** — é a cor padrão de metadados, legendas e dos textos `.loading`/`.empty`. `var(--k4)` mais 41 vezes. `var(--gold)` como cor de texto 64 vezes. E `UnauthorizedView` põe `#fff` sobre `#9b7e46` (3,84:1) no botão primário.

**Ajuste.** Rebaixar `--k5` a papel decorativo (bordas, ícones, separadores) e trocar todo texto em `--k5` por `--k3`. Escurecer `--k4` para ~`#6b6b6b` (≥4,5:1). Criar `--gold-text` (`#7d6437`, ~5,3:1) para dourado tipográfico, mantendo `--gold` para preenchimentos e bordas. Escurecer `--success` e `--warn` quando usados como texto.

### 🟡 AC-03 · Foco de teclado praticamente inexistente

Duas ocorrências de `:focus-visible` em toda a base; 19 de `:focus`. Como muitos botões e pílulas removem a borda padrão, a navegação por teclado fica sem indicação de posição em boa parte do produto.

**Ajuste.** Anel de foco global em `main.css`:
```css
:where(a, button, input, select, textarea, [tabindex]):focus-visible {
  outline: 2px solid var(--gold);
  outline-offset: 2px;
}
```

### 🟡 AC-04 · Nenhum tratamento de `prefers-reduced-motion`

Zero ocorrências. Há transições, animações (`@keyframes tb-fade`) e o mapa estratégico com transições de layout.

**Ajuste.** Bloco global de redução de movimento em `main.css`.

### 🟡 AC-05 · Formulários com rotulagem irregular

102 `<label>` para 168 atributos `for=` — a contagem não fecha, indicando `for` sem `<label>` correspondente ou reutilizado. Só 33 `aria-label` em 18 arquivos, para 8 modais e dezenas de botões-ícone.

**Ajuste.** Auditoria com `eslint-plugin-vuejs-accessibility` no CI; `FormField` (AR-01) resolve a associação `label`↔`input` estruturalmente.

## E. Build, entrega e higiene

### 🔴 CD-01 · O build de produção não passa — 48 erros de tipo

`tsc5.txt` (registro de `npm run type-check`) contém **48 erros em 10 arquivos**. Como o script é `vue-tsc -b && vite build`, o build falha antes de gerar bundle. O `dist/` versionado é de 02/08.

| Arquivo | Erros | | Código | Ocorrências | Significado |
|---|---:|---|---|---:|---|
| `AdminQuizView.vue` | 21 | | TS2532 | 16 | objeto possivelmente `undefined` |
| `SwotAnalysisView.vue` | 6 | | TS18048 | 14 | variável possivelmente `undefined` |
| `QuizView.vue` | 6 | | TS6196 | 6 | tipo declarado e não usado |
| `ProgramaView.vue` | 6 | | TS6133 | 4 | variável declarada e não usada |
| `TrilhaShowcaseView.vue` | 3 | | TS2345 | 3 | argumento incompatível |
| `AiMaturityListView.vue` | 2 | | TS2322 | 3 | atribuição incompatível |
| `AdminUsuarios` · `QuizRespostas` · `Agenda` · `stores/auth.ts` | 1 cada | | TS7053 · TS2339 | 2 | índice implícito · propriedade inexistente |

A grande maioria (30 dos 48) é consequência direta de `noUncheckedIndexedAccess: true` — acesso a `array[i]` sem guarda.

**Ajuste.** Zerar os 48 (é trabalho mecânico: guarda de índice, remoção de declarações mortas). **Não relaxar `noUncheckedIndexedAccess`** — é justamente ele que está evitando uma classe inteira de bugs em runtime. Depois: `npm run type-check` obrigatório no CI, e `dist/` fora do repositório.

### 🟡 CD-02 · Dependência morta de 4,7 MB

`plotly.js-dist-min@^3.4.0` está em `dependencies` e **não é importado em nenhum arquivo** de `src/` nem de `public/`.

**Ajuste.** Remover do `package.json` e regenerar o lock.

### 🟡 CD-03 · Cache desligado para todos os assets

`public/_headers` aplica `Cache-Control: no-cache, no-store, must-revalidate` em `/*`, e `index.html` repete via três `<meta http-equiv>`. Como o Vite já emite assets com hash de conteúdo no nome, isso força rebaixar **todo** o JS/CSS a cada visita — inclusive os bundles grandes das telas estratégicas.

**Ajuste.**
```
/index.html
  Cache-Control: no-store
/assets/*
  Cache-Control: public, max-age=31536000, immutable
```
E remover as três metas `http-equiv` de `index.html` (não confiáveis e agora redundantes).

### ⚪ CD-04 · Artefatos de build convivendo com o fonte

`dist/`, `tsconfig.tsbuildinfo`, `tsconfig.node.tsbuildinfo`, `vite.config.js`, `vite.config.d.ts` (compilados do `vite.config.ts`), `tsc5.txt` e `.DS_Store` (inclusive em `src/`) estão soltos no diretório.

**Ajuste.** `.gitignore` cobrindo os seis padrões; manter só `vite.config.ts`.

### ⚪ CD-05 · `index.html` sem metadados

Só `<title>`. Sem `description`, `og:title`/`og:image`, `theme-color` ou `lang` nas rotas internas.

**Ajuste.** Bloco de meta base no `index.html` e atualização de `description`/`og` no `router.afterEach`, que já gerencia `document.title`.

### ⚪ CD-06 · README desatualizado

Descreve `src/api` com um exemplo (`courses.ts`) e uma estrutura de 8 pastas, sem mencionar as 6 ferramentas do AI Hub, o modelo de acesso por ferramenta, a governança ou a cadeia de rastreabilidade — que são o produto.

**Ajuste.** Reescrever com o mapa de rotas por domínio, o modelo de acesso em três eixos e um link para este documento.

---

# PARTE III — PLANO DE AJUSTE

## Onda 1 — Desbloquear (1 semana)

| # | Ação | Item |
|---|---|---|
| 1 | Zerar os 48 erros de tipo; `type-check` obrigatório no CI | CD-01 |
| 2 | Corrigir cache: `no-store` só no `index.html`, `immutable` em `/assets/*` | CD-03 |
| 3 | Remover `plotly.js-dist-min`; `.gitignore` para artefatos de build | CD-02, CD-04 |
| 4 | Adicionar guarda de concorrência em `GovernanceSystemView.persist()` | AR-03 |

> Critério de saída: `npm run build` verde, `dist/` fora do repo, sem gravação concorrente em Governança.

## Onda 2 — Fundação visual (2 semanas)

| # | Ação | Item |
|---|---|---|
| 5 | Decidir a marca única e consolidar tokens em `main.css`; remover os 4 blocos locais | DS-01 |
| 6 | Corrigir contraste: `--k5` vira decorativo, `--k4` escurece, criar `--gold-text` | AC-02 |
| 7 | Escala tipográfica de 8 degraus; raios e sombras em tokens; 3 larguras de página | DS-03, DS-04, DS-07 |
| 8 | Definir `--k2`, `--navy-deep`, `--bg`; resolver Space Grotesk | DS-06, DS-05 |
| 9 | Foco visível global + `prefers-reduced-motion` em `main.css` | AC-03, AC-04 |

> Critério de saída: nenhum token global redefinido em `<style scoped>`; zero texto abaixo de 4,5:1.

## Onda 3 — Biblioteca de componentes (3–4 semanas)

| # | Ação | Item |
|---|---|---|
| 10 | `StateBlock`, `PageHeader`, `AppButton` → migrar as 35 views | AR-01, UX-02 |
| 11 | `AppModal` com foco, Escape e trap → migrar os 8 modais | AR-01, UX-03 |
| 12 | `DataTable`, `FormField`, `AppCard`, `Badge`, `SaveIndicator` | AR-01, AC-05 |
| 13 | `useAutosave()` único → migrar as 5 views com autosave | AR-03, UX-01 |
| 14 | Codemod de cores hex → tokens; `stylelint` no CI | DS-02 |

> Critério de saída: CSS local abaixo de 6.000 linhas (de 13.288); zero hex fora de `main.css`.

## Onda 4 — Estrutura e cobertura (3 semanas)

| # | Ação | Item |
|---|---|---|
| 15 | Responsividade: `AdminLayout` drawer, tabelas em card, 3 breakpoints | AC-01 |
| 16 | Unificar o shell de navegação (topbar única + sidebar contextual) | UX-05 |
| 17 | Quebrar os 7 god components; regra de domínio para `lib/` | AR-02 |
| 18 | `lib/domain/` como fonte única (dimensões, quadrantes, TOWS) | AR-04 |
| 19 | Rota 404 + `AccessStateLayout` (401 / ferramenta / 404) | UX-06, UX-07 |
| 20 | Resolver `/admin/alunos` e `/admin/progresso`; menu derivado do router | UX-04 |
| 21 | Unificar membros da organização; convenção de nomes na API | AR-04, AR-06 |
| 22 | Tirar a landing do iframe; servir `/` no edge | AR-07 |
| 23 | Consolidar `types/`; atualizar README; meta tags | AR-05, CD-05, CD-06 |

> Critério de saída: nenhuma view acima de 600 linhas; todas as telas usáveis em 768px.

---

## Métricas de acompanhamento

| Indicador | Hoje | Meta |
|---|---:|---:|
| Erros de tipo (`vue-tsc`) | 48 | 0 |
| Linhas de CSS dentro de `.vue` | 13.288 | < 6.000 |
| Componentes reutilizáveis | 5 | ≥ 17 |
| Cores hex fora do sistema | 82 | 0 |
| Tamanhos de fonte distintos | 27 | 8 |
| Tokens globais redefinidos localmente | 3 | 0 |
| Textos abaixo de 4,5:1 (WCAG AA) | 268 ocorrências | 0 |
| Views sem media query | 27 de 42 | 0 |
| Maior view (linhas) | 2.255 | < 600 |

---

*Auditoria realizada sobre o código-fonte em `frontend-vue/src` — 30.898 linhas, 73 arquivos. Todas as evidências são referências diretas a arquivo e linha.*
