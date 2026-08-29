# Valorian 4 Future · Frontend Vue (TypeScript)

Interface em **Vue 3**, **TypeScript** e **Vite** para a plataforma AEGIS (mentoria executiva em IA).

## Estrutura

| Pasta | Conteúdo |
|---|---|
| `src/api/` | Cliente HTTP, tipos de API e endpoints |
| `src/assets/` | CSS global (`main.css` — tokens do design system) |
| `src/components/` | Componentes reutilizáveis (`ui/`, `layout/`, `course/`) |
| `src/composables/` | Lógica reutilizável (ex.: `useAutosave`, `useCourses`) |
| `src/layouts/` | Shells (`DefaultLayout`, `AdminLayout`) |
| `src/lib/` | Utilitários, domínio (`lib/domain/`), navegação admin |
| `src/router/` | Rotas, guards e meta de título |
| `src/stores/` | Pinia (auth, courses) |
| `src/views/` | Páginas (uma por rota) |
| `public/` | Assets estáticos, incluindo `lp.html` (landing) |

Tipos de curso/trilha ficam em `src/api/courses.ts`. O diretório `src/types/` mantém apenas reexports de compatibilidade.

Componentes UI compartilhados: `AppButton`, `AppModal`, `AppCard`, `PageHeader`, `StateBlock`, `AccessStateLayout`, etc. — ver `src/components/ui/`.

## Desenvolvimento

```bash
cd frontend-vue
npm install
npm run dev
```

Acesse `http://localhost:5173`. O Vite faz proxy de `/api` e `/static` para o backend em `http://127.0.0.1:8000`. Deixe o backend rodando em outro terminal.

A rota `/` no app Vue redireciona para `public/lp.html` (landing estática). Em produção, o backend serve `lp.html` diretamente em `GET /`.

## Build e integração com o backend

```bash
npm run build
```

O build gera `dist/` (inclui `lp.html` copiado de `public/`). O FastAPI detecta `frontend-vue/dist/index.html` e passa a servir a SPA nas rotas do app (`/programa`, `/admin`, etc.), mantendo `lp.html` em `/`.

## Scripts

- `npm run dev` — servidor de desenvolvimento
- `npm run build` — build de produção (`vue-tsc` + `vite build`)
- `npm run preview` — preview do build
- `npm run type-check` — verificação de tipos

## Documentação de design

Auditoria e roadmap de UI: `docs/SYSTEM_DESIGN.md`.
