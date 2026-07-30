import { del, get, patch, post, postFormData, put } from './client'

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

// ——— Materiais da landing ———

export interface LandingMaterial {
  id: string
  title: string
  description: string
  material_url: string
  summary_url: string
  audio_url: string | null
  order: number
  active: boolean
  created_at: string | null
  updated_at: string | null
}

export interface LandingMaterialPayload {
  title: string
  description: string
  material_url: string
  summary_url: string
  audio_url?: string | null
  order?: number
  active?: boolean
}

export function listLandingMaterials(): Promise<LandingMaterial[]> {
  return get<LandingMaterial[]>('/api/admin/landing-materials')
}

export function createLandingMaterial(body: LandingMaterialPayload): Promise<LandingMaterial> {
  return post<LandingMaterial>('/api/admin/landing-materials', body)
}

export function updateLandingMaterial(
  id: string,
  body: Partial<LandingMaterialPayload>
): Promise<LandingMaterial> {
  return put<LandingMaterial>(`/api/admin/landing-materials/${encodeURIComponent(id)}`, body)
}

export function deleteLandingMaterial(id: string): Promise<{ message: string; id: string }> {
  return del<{ message: string; id: string }>(`/api/admin/landing-materials/${encodeURIComponent(id)}`)
}

export interface LandingMaterialUploadResult {
  url: string
  filename: string
  size: number
}

/** Envia arquivo para material_gratuito/ e retorna a URL pública. */
export function uploadLandingMaterialFile(file: File): Promise<LandingMaterialUploadResult> {
  const fd = new FormData()
  fd.append('file', file)
  return postFormData<LandingMaterialUploadResult>('/api/admin/landing-materials/upload', fd)
}

// ——— Prompts da landing ———

export interface LandingPrompt {
  id: string
  title: string
  description: string
  meta_label: string
  prompt_url: string
  order: number
  active: boolean
  created_at: string | null
  updated_at: string | null
}

export interface LandingPromptPayload {
  title: string
  description: string
  meta_label?: string
  prompt_url: string
  order?: number
  active?: boolean
}

export function listLandingPrompts(): Promise<LandingPrompt[]> {
  return get<LandingPrompt[]>('/api/admin/landing-prompts')
}

export function createLandingPrompt(body: LandingPromptPayload): Promise<LandingPrompt> {
  return post<LandingPrompt>('/api/admin/landing-prompts', body)
}

export function updateLandingPrompt(
  id: string,
  body: Partial<LandingPromptPayload>
): Promise<LandingPrompt> {
  return put<LandingPrompt>(`/api/admin/landing-prompts/${encodeURIComponent(id)}`, body)
}

export function deleteLandingPrompt(id: string): Promise<{ message: string; id: string }> {
  return del<{ message: string; id: string }>(`/api/admin/landing-prompts/${encodeURIComponent(id)}`)
}

export interface LandingPromptUploadResult {
  url: string
  filename: string
  size: number
}

/** Envia arquivo MD/TXT para material_gratuito/ e retorna a URL pública. */
export function uploadLandingPromptFile(file: File): Promise<LandingPromptUploadResult> {
  const fd = new FormData()
  fd.append('file', file)
  return postFormData<LandingPromptUploadResult>('/api/admin/landing-prompts/upload', fd)
}
