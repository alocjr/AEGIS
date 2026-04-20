import { del, get, patch, post, put } from './client'

// ——— Usuários ———

export interface AdminUser {
  id: string
  name: string
  email: string
  phone: string
  course_slug: string
  course_slugs: string[]
  is_admin: boolean
  created_at: string | null
}

export interface AdminUserDetail extends AdminUser {
  encontro_agendas: Record<string, string>
}

export function listUsers(): Promise<AdminUser[]> {
  return get<AdminUser[]>('/api/admin/users')
}

export function getUser(userId: string): Promise<AdminUserDetail> {
  return get<AdminUserDetail>(`/api/admin/users/${encodeURIComponent(userId)}`)
}

export function createUser(body: {
  name: string
  email: string
  password: string
  course_slugs: string[]
  phone?: string
  encontro_agendas?: Record<string, string>
}): Promise<{ message: string; user_id: string; email: string; course_slugs: string[] }> {
  return post('/api/admin/users', body)
}

export function updateUser(
  userId: string,
  body: {
    name?: string
    email?: string
    password?: string
    course_slugs?: string[]
    phone?: string
    is_admin?: boolean
    encontro_agendas?: Record<string, string>
  }
): Promise<{ message: string; id: string }> {
  return put(`/api/admin/users/${encodeURIComponent(userId)}`, body)
}

export function deleteUser(userId: string): Promise<{ message: string; id: string }> {
  return del(`/api/admin/users/${encodeURIComponent(userId)}`)
}

// ——— Dashboard ———

export interface DashboardStudent {
  id: string
  name: string
  email: string
  phone: string
  course_slug: string
  course_titulo: string
  encontros_done: number
  encontros_total: number
  material_checked: number
  material_total: number
  quiz_done: number
  quiz_total: number
  maturity_done: number
  maturity_total: number
  next_meeting_iso: string | null
}

export function fetchDashboard(): Promise<DashboardStudent[]> {
  return get<DashboardStudent[]>('/api/admin/dashboard')
}

export interface UserCourseAndProgress {
  user: { id: string; name: string; email: string }
  course_slug: string
  programa_formacao_executiva: Record<string, unknown>
  materiais_por_encontro?: Record<string, number>
  quiz_por_encontro?: Record<string, { tem_quiz: boolean; respondido: boolean; score?: number; total?: number }>
  progress: {
    concluidos: number[]
    ativo: number
    total: number
    concluidos_efetivos: number[]
    ativo_efetivo: number
    encontros_liberados: number[]
    material_checks: Record<string, unknown>
    encontro_conclusoes: Record<string, string>
    encontro_agendas: Record<string, string>
  }
}

export function fetchUserCourseAndProgress(
  userId: string,
  courseSlug?: string
): Promise<UserCourseAndProgress> {
  const url = `/api/admin/users/${encodeURIComponent(userId)}/course-and-progress`
  const params = courseSlug ? `?course_slug=${encodeURIComponent(courseSlug)}` : ''
  return get<UserCourseAndProgress>(url + params)
}

export function liberarEncontro(userId: string, encontroId: number): Promise<void> {
  return post<void>(`/api/admin/users/${encodeURIComponent(userId)}/liberar-encontro`, {
    encontro_id: encontroId,
  })
}

export function updateUserProgress(
  userId: string,
  courseSlug: string,
  encontroAgendas: Record<string, string>
): Promise<{ message: string; encontro_agendas: Record<string, string> }> {
  return patch(`/api/admin/users/${encodeURIComponent(userId)}/progress`, {
    course_slug: courseSlug,
    encontro_agendas: encontroAgendas,
  })
}

// ——— Trilhas (cursos) ———

export interface CourseListItem {
  slug: string
  titulo: string
  tema: string
}

export interface CourseDetail {
  slug: string
  programa_formacao_executiva: Record<string, unknown>
}

export function fetchCourseList(): Promise<CourseListItem[]> {
  return get<CourseListItem[]>('/api/admin/courses')
}

export function fetchCourse(slug: string): Promise<CourseDetail> {
  return get<CourseDetail>(`/api/admin/courses/${encodeURIComponent(slug)}`)
}

export function createCourse(slug: string, programaFormacaoExecutiva: Record<string, unknown>): Promise<{ slug: string; message: string }> {
  return post<{ slug: string; message: string }>('/api/admin/courses', {
    slug,
    programa_formacao_executiva: programaFormacaoExecutiva,
  })
}

export function updateCourse(slug: string, programaFormacaoExecutiva: Record<string, unknown>): Promise<{ slug: string; message: string }> {
  return put<{ slug: string; message: string }>(`/api/admin/courses/${encodeURIComponent(slug)}`, {
    programa_formacao_executiva: programaFormacaoExecutiva,
  })
}

export function deleteCourse(slug: string): Promise<{ slug: string; message: string }> {
  return del<{ slug: string; message: string }>(`/api/admin/courses/${encodeURIComponent(slug)}`)
}

// ——— Quiz (admin) ———

export interface AdminQuizListItem {
  encontro: number
  titulo: string
  total: number
}

export interface AdminQuizGroup {
  course_slug: string | null
  titulo: string
  quizzes: AdminQuizListItem[]
}

export interface AdminQuizListResponse {
  grouped: AdminQuizGroup[]
}

export interface AdminQuizOpcao {
  text: string
  rationale?: string
  isCorrect?: boolean
}

export interface AdminQuizQuestao {
  id: number
  pergunta: string
  hint?: string
  opcoes: AdminQuizOpcao[]
}

export interface AdminQuizDetail {
  encontro: number
  titulo: string
  questoes: AdminQuizQuestao[]
}

export interface AdminQuizCreateUpdatePayload {
  encontro: number
  titulo?: string | null
  questoes: AdminQuizQuestao[]
}

export function fetchAdminQuizList(): Promise<AdminQuizListResponse> {
  return get<AdminQuizListResponse>('/api/admin/quiz')
}

export function fetchAdminQuiz(encontroId: number): Promise<AdminQuizDetail> {
  return get<AdminQuizDetail>(`/api/admin/quiz/${encontroId}`)
}

export function createOrUpdateQuiz(payload: AdminQuizCreateUpdatePayload): Promise<{ message: string; encontro: number }> {
  return post<{ message: string; encontro: number }>('/api/admin/quiz', payload)
}

export function deleteQuiz(encontroId: number): Promise<{ message: string; encontro: number }> {
  return del<{ message: string; encontro: number }>(`/api/admin/quiz/${encontroId}`)
}
