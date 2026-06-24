import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
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
      { path: 'ai-maturity/:id', name: 'AiMaturityDetail', component: () => import('@/views/AiMaturityDetailView.vue'), meta: { title: 'Resultado · Maturidade IA' } },
      { path: 'quiz-respostas', name: 'QuizRespostas', component: () => import('@/views/QuizRespostasView.vue'), meta: { title: 'Quiz Respostas' } },
      { path: 'quiz/q/:quizId', name: 'QuizById', component: () => import('@/views/QuizView.vue'), meta: { title: 'Quiz' } },
      { path: 'quiz/:encontroId(\\d+)', name: 'Quiz', component: () => import('@/views/QuizView.vue'), meta: { title: 'Quiz' } },
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
      { path: 'trilhas', name: 'AdminTrilhas', component: () => import('@/views/admin/AdminTrilhasView.vue'), meta: { title: 'Admin · Trilhas' } },
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

const protectedPaths = ['/programa', '/materiais', '/agenda', '/quiz-respostas', '/ai-maturity', '/quiz']
const adminPathPrefix = '/admin'

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

  const isProtected = protectedPaths.some((p) => to.path === p || to.path.startsWith('/quiz/') || to.path.startsWith('/ai-maturity'))
  if (isProtected && !auth.isLoggedIn) {
    next('/')
    return
  }
  if (isProtected && auth.user?.email_verified === false) {
    next('/login')
    return
  }

  if (to.path === '/') {
    if (auth.isLoggedIn && !auth.isAdmin && auth.user?.email_verified !== false) {
      next('/programa')
      return
    }
  }
  next()
})

router.afterEach((to) => {
  const title = (to.meta?.title as string) ?? 'Valorian 4 Future'
  document.title = title.includes('Valorian') ? title : `${title} · Valorian 4 Future`
})

export default router
