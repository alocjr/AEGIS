import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { toolRequiredForPath } from '@/lib/tools'
import { resourceKeyForRoute, trackResourceAccess } from '@/lib/track'
import DefaultLayout from '@/layouts/DefaultLayout.vue'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    component: DefaultLayout,
    children: [
      { path: '', name: 'Landing', component: () => import('@/views/LandingView.vue'), meta: { title: 'Valorian 4 Future' } },
      { path: 'programa', name: 'Programa', component: () => import('@/views/ProgramaView.vue'), meta: { title: 'Programa' } },
      { path: 'materiais', name: 'Materiais', component: () => import('@/views/MateriaisView.vue'), meta: { title: 'Materiais' } },
      { path: 'trilhas', name: 'Trilhas', component: () => import('@/views/TrilhasView.vue'), meta: { title: 'Trilhas' } },
      { path: 'trilhas/:slug', name: 'TrilhaShowcase', component: () => import('@/views/TrilhaShowcaseView.vue'), meta: { title: 'Trilha' } },
      { path: 'agenda', name: 'Agenda', component: () => import('@/views/AgendaView.vue'), meta: { title: 'Agenda' } },
      { path: 'ai-maturity', name: 'AiMaturityList', component: () => import('@/views/AiMaturityListView.vue'), meta: { title: 'Maturidade IA' } },
      { path: 'ai-maturity/new', name: 'AiMaturityNew', component: () => import('@/views/AiMaturityView.vue'), meta: { title: 'Nova autoavaliação' } },
      {
        path: 'ai-maturity/:id/edit',
        name: 'AiMaturityEdit',
        component: () => import('@/views/AiMaturityView.vue'),
        meta: { title: 'Editar autoavaliação' },
      },
      { path: 'ai-maturity/:id', name: 'AiMaturityDetail', component: () => import('@/views/AiMaturityDetailView.vue'), meta: { title: 'Resultado · Maturidade IA' } },
      { path: 'projetos', name: 'ProjetosList', component: () => import('@/views/ProjetosListView.vue'), meta: { title: 'Projetos' } },
      { path: 'projetos/:id', name: 'ProjetoCanvas', component: () => import('@/views/ProjetoCanvasView.vue'), meta: { title: 'Canvas · Projeto' } },
      { path: 'swot/:id?', name: 'SwotAnalysis', component: () => import('@/views/SwotAnalysisView.vue'), meta: { title: 'SWOT de IA' } },
      { path: 'okrs', name: 'OkrCyclesList', component: () => import('@/views/okrs/OkrCyclesListView.vue'), meta: { title: 'OKR' } },
      { path: 'okrs/:id', name: 'OkrCycleEditor', component: () => import('@/views/okrs/OkrCycleEditorView.vue'), meta: { title: 'OKR · Ciclo' } },
      {
        path: 'mapa-estrategico',
        name: 'MapaEstrategico',
        component: () => import('@/views/MapaEstrategicoView.vue'),
        meta: { title: 'Mapa Estratégico' },
      },
      {
        path: 'governanca/dashboard',
        name: 'GovernanceDashboard',
        component: () => import('@/views/governanca/GovernanceDashboardView.vue'),
        meta: { title: 'Governança · Dashboard' },
      },
      {
        path: 'governanca/inventario',
        name: 'GovernanceInventory',
        component: () => import('@/views/governanca/GovernanceInventoryView.vue'),
        meta: { title: 'Governança · Inventário' },
      },
      {
        path: 'governanca/sistemas/:id',
        name: 'GovernanceSystem',
        component: () => import('@/views/governanca/GovernanceSystemView.vue'),
        meta: { title: 'Governança · Sistema' },
      },
      {
        path: 'governanca/gate/:id',
        name: 'GovernanceGate',
        component: () => import('@/views/governanca/GovernanceGateView.vue'),
        meta: { title: 'Governança · Gate' },
      },
      {
        path: 'organizacao/usuarios',
        name: 'OrgMembers',
        component: () => import('@/views/organizacao/OrgMembersView.vue'),
        meta: { title: 'Minha Organização' },
      },
      { path: 'quiz-respostas', name: 'QuizRespostas', component: () => import('@/views/QuizRespostasView.vue'), meta: { title: 'Quiz Respostas' } },
      { path: 'quiz/q/:quizId', name: 'QuizById', component: () => import('@/views/QuizView.vue'), meta: { title: 'Quiz' } },
      { path: 'quiz/:encontroId(\\d+)', name: 'Quiz', component: () => import('@/views/QuizView.vue'), meta: { title: 'Quiz' } },
      {
        path: 'acesso-negado',
        name: 'ToolDisabled',
        component: () => import('@/views/ToolDisabledView.vue'),
        meta: { title: 'Ferramenta não disponível' },
      },
    ],
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/LoginView.vue'),
    meta: { title: 'Entrar' },
  },
  {
    path: '/admin',
    component: () => import('@/layouts/AdminLayout.vue'),
    children: [
      { path: '', name: 'AdminDashboard', component: () => import('@/views/admin/AdminDashboardView.vue'), meta: { title: 'Admin' } },
      { path: 'acessos', name: 'AdminAnalytics', component: () => import('@/views/admin/AdminAnalyticsView.vue'), meta: { title: 'Admin · Acessos' } },
      { path: 'trilhas', name: 'AdminTrilhas', component: () => import('@/views/admin/AdminTrilhasView.vue'), meta: { title: 'Admin · Trilhas' } },
      { path: 'materiais-landing', name: 'AdminMateriaisLanding', component: () => import('@/views/admin/AdminMateriaisLandingView.vue'), meta: { title: 'Admin · Materiais Landing' } },
      { path: 'prompts-landing', name: 'AdminPromptsLanding', component: () => import('@/views/admin/AdminPromptsLandingView.vue'), meta: { title: 'Admin · Prompts Landing' } },
      { path: 'usuarios', name: 'AdminUsuarios', component: () => import('@/views/admin/AdminUsuariosView.vue'), meta: { title: 'Admin · Usuários' } },
      { path: 'alunos', name: 'AdminAlunos', component: () => import('@/views/admin/AdminAlunosView.vue'), meta: { title: 'Admin · Alunos' } },
      { path: 'progresso', name: 'AdminProgresso', component: () => import('@/views/admin/AdminProgressoView.vue'), meta: { title: 'Admin · Progresso' } },
      { path: 'progresso/:userId', name: 'AdminProgressoAluno', component: () => import('@/views/admin/AdminProgressoAlunoView.vue'), meta: { title: 'Admin · Progresso do aluno' } },
      { path: 'quiz', name: 'AdminQuiz', component: () => import('@/views/admin/AdminQuizView.vue'), meta: { title: 'Admin · Quiz' } },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
})

const protectedPaths = ['/programa', '/materiais', '/agenda', '/quiz-respostas', '/ai-maturity', '/projetos', '/swot', '/okrs', '/quiz', '/mapa-estrategico', '/governanca', '/organizacao']
const adminPathPrefix = '/admin'
const orgAdminPathPrefix = '/organizacao'

router.beforeEach(async (to, _from, next) => {
  const auth = useAuthStore()
  if (!auth.loaded) await auth.loadUser()

  const isAdminRoute = to.path === adminPathPrefix || to.path.startsWith(adminPathPrefix + '/')
  if (isAdminRoute) {
    if (!auth.isLoggedIn || !auth.isAdmin) {
      next('/')
      return
    }
  }

  const isOrgAdminRoute = to.path === orgAdminPathPrefix || to.path.startsWith(orgAdminPathPrefix + '/')
  if (isOrgAdminRoute) {
    if (!auth.isLoggedIn || !(auth.isOrgAdmin || auth.isAdmin)) {
      next('/')
      return
    }
  }

  const isProtected = protectedPaths.some(
    (p) =>
      to.path === p ||
      to.path.startsWith('/quiz/') ||
      to.path.startsWith('/ai-maturity') ||
      to.path.startsWith('/projetos') ||
      to.path.startsWith('/swot') ||
      to.path.startsWith('/okrs') ||
      to.path.startsWith('/governanca') ||
      to.path.startsWith('/organizacao')
  )
  if (isProtected && !auth.isLoggedIn) {
    next('/')
    return
  }
  if (isProtected && auth.user?.email_verified === false) {
    next('/login')
    return
  }

  const requiredTool = toolRequiredForPath(to.path)
  if (requiredTool && auth.isLoggedIn && !auth.hasTool(requiredTool)) {
    next({ name: 'ToolDisabled', query: { tool: requiredTool } })
    return
  }

  if (to.path === '/') {
    if (auth.isLoggedIn && !auth.isAdmin && auth.user?.email_verified !== false) {
      // Membro de organização sem trilha (ex.: criado por um admin de organização) não tem
      // "/programa" — cai na primeira ferramenta do AI Hub que o admin liberou.
      const hasTrilha = (auth.user?.course_slugs?.length ?? 0) > 0
      if (hasTrilha) {
        next('/programa')
        return
      }
      next(auth.homePathWithoutTrilha() || { name: 'ToolDisabled' })
      return
    }
  }
  next()
})

router.afterEach((to) => {
  const title = (to.meta?.title as string) ?? 'Valorian 4 Future'
  document.title = title.includes('Valorian') ? title : `${title} · Valorian 4 Future`

  const resourceKey = resourceKeyForRoute(to.name)
  if (resourceKey) trackResourceAccess(resourceKey)
})

export default router
