/**
 * UX-04: fonte única do menu do /admin. AdminLayout.vue renderiza este
 * array em vez de RouterLinks fixos — antes o menu declarava 7 destinos
 * enquanto o router tinha 10 rotas filhas, e /admin/alunos e /admin/progresso
 * só existiam por URL direta (dois placeholders "em migração" servidos em
 * produção, sem link algum para eles).
 *
 * Toda rota de nível superior em router/index.ts (filha direta de
 * AdminLayout) deve ter uma entrada aqui, ou ser uma rota de
 * detalhe/drill-down documentada como tal (ex.: admin/progresso/:userId,
 * acessível a partir de AdminDashboardView e AdminUsuariosView, não do
 * menu principal).
 */
export interface AdminNavItem {
  to: string
  label: string
  /** Só o Dashboard precisa disso — '/admin' é prefixo de toda outra rota do menu. */
  exact?: boolean
}

export const ADMIN_NAV_ITEMS: AdminNavItem[] = [
  { to: '/admin', label: 'Dashboard', exact: true },
  { to: '/admin/acessos', label: 'Acessos' },
  { to: '/admin/trilhas', label: 'Trilhas' },
  { to: '/admin/materiais-landing', label: 'Materiais da Landing' },
  { to: '/admin/prompts-landing', label: 'Prompts da Landing' },
  { to: '/admin/usuarios', label: 'Usuários' },
  { to: '/admin/quiz', label: 'Quiz' },
]
