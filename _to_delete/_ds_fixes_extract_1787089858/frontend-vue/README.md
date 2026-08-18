# Valorian 4 Future · Frontend Vue (TypeScript)

Interface modular em **Vue 3**, **TypeScript** e **Vite**, seguindo boas práticas de mercado.

## Assets

O logo fica em `public/assets/logo.png`. Substitua o placeholder pelo arquivo real da marca; ele é copiado para `dist/assets/` no build e servido em `/assets/logo.png`.

## Estrutura

- `src/api` – Cliente HTTP e endpoints (ex.: `courses.ts`)
- `src/components` – Componentes reutilizáveis (`layout/`, `course/`)
- `src/composables` – Lógica reutilizável (ex.: `useCourses`)
- `src/layouts` – Layouts (DefaultLayout, AdminLayout)
- `src/router` – Rotas e meta (títulos)
- `src/stores` – Pinia (ex.: `courses`)
- `src/types` – Tipos TypeScript globais
- `src/views` – Páginas (uma por rota)

## Desenvolvimento

```bash
cd frontend-vue
npm install
npm run dev
```

Acesse `http://localhost:5173`. O Vite faz proxy de `/api` e `/static` para o backend em `http://127.0.0.1:8000`. Deixe o backend rodando em outro terminal.

## Build e integração com o backend

```bash
npm run build
```

O build gera a pasta `dist/`. O FastAPI detecta `frontend-vue/dist/index.html` e passa a servir a SPA nas rotas atuais (/, /programa, /trilhas, /admin, etc.). Se `dist/` não existir, o backend continua servindo o frontend estático em `frontend/`.

## Scripts

- `npm run dev` – Servidor de desenvolvimento
- `npm run build` – Build de produção (`vue-tsc` + `vite build`)
- `npm run preview` – Preview do build
- `npm run type-check` – Verificação de tipos
