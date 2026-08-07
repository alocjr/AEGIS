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
  /** Pode criar/editar/remover membros da própria organização (sem trilha/mentoria). */
  is_org_admin: boolean
  created_at: string | null
  /** Organização (time) à qual o usuário pertence — SWOT/Canvas/Maturidade são compartilhados nela. */
  organization_id: string | null
  organization_name: string
  /** Ferramentas do AI Hub liberadas (ids do catálogo). */
  tools: string[]
}

export interface AdminUserDetail extends AdminUser {
  encontro_agendas: Record<string, string>
}

export interface PlatformTool {
  id: string
  label: string
  path: string
  descricao: string
}

export function listPlatformTools(): Promise<{ items: PlatformTool[] }> {
  return get<{ items: PlatformTool[] }>('/api/admin/tools')
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
  organization_id?: string
  tools?: string[]
}): Promise<{ message: string; user_id: string; email: string; course_slugs: string[]; tools: string[] }> {
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
    is_org_admin?: boolean
    encontro_agendas?: Record<string, string>
    organization_id?: string
    tools?: string[]
    apply_tools_to_organization?: boolean
  }
): Promise<{ message: string; id: string; members_updated?: number }> {
  return put(`/api/admin/users/${encodeURIComponent(userId)}`, body)
}

export function setOrganizationTools(
  orgId: string,
  tools: string[]
): Promise<{ message: string; organization_id: string; tools: string[]; members_updated: number }> {
  return put(`/api/admin/organizations/${encodeURIComponent(orgId)}/tools`, { tools })
}

export function deleteUser(userId: string): Promise<{ message: string; id: string }> {
  return del(`/api/admin/users/${encodeURIComponent(userId)}`)
}

// ——— Organizações ———

export interface AdminOrganization {
  id: string
  name: string
  member_count: number
}

export function listOrganizations(): Promise<AdminOrganization[]> {
  return get<AdminOrganization[]>('/api/admin/organizations')
}

export function createOrganization(name: string): Promise<{ id: string; name: string }> {
  return post('/api/admin/organizations', { name })
}

// ——— Dashboard ———

/** Progresso de trilha/quiz — individual por membro. */
export interface DashboardMember {
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
  next_meeting_iso: string | null
}

/** Organização — SWOT/Canvas/Maturidade são compartilhados por todos os membros. */
export interface DashboardOrganization {
  id: string | null
  name: string
  maturity_done: number
  maturity_total: number
  swot_filled: boolean
  canvas_count: number
  members: DashboardMember[]
}

export function fetchDashboard(): Promise<DashboardOrganization[]> {
  return get<DashboardOrganization[]>('/api/admin/dashboard')
}

// ——— Analytics de acesso ———

export interface ResourceAccessItem {
  key: string
  label: string
  category: string
  /** Ferramenta/área que agrupa a funcionalidade (ex.: "SWOT de IA"). */
  group: string
  events: number
  unique_users: number
  unique_visitors: number
  last_at: string | null
}

export interface ResourceAccessCategory {
  key: string
  label: string
  events: number
  resources: ResourceAccessItem[]
}

export interface ResourceAccessReport {
  range_days: number
  since: string
  generated_at: string
  totals: {
    events: number
    unique_users: number
    unique_visitors: number
    tracked_resources: number
  }
  daily: { day: string; events: number }[]
  categories: ResourceAccessCategory[]
}

/** Períodos aceitos pelo backend (`ALLOWED_ANALYTICS_RANGES`). */
export const ANALYTICS_RANGES = [7, 30, 90, 365] as const

export function fetchResourceAccessReport(days: number): Promise<ResourceAccessReport> {
  return get<ResourceAccessReport>(`/api/admin/analytics/resources?days=${days}`)
}

export interface UserCourseAndProgress {
  user: { id: string; name: string; email: string }
  course_slug: string
  programa_formacao_executiva: Record<string, unknown>
  materiais_por_encontro?: Record<string, number>
  quiz_por_encontro?: Record<string, { tem_quiz: boolean; respondido: boolean; score?: number; total?: number }>
  swot_filled: boolean
  swot_updated_at: string | null
  canvas_count: number
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
  /** Cliques acumulados nos links do card, somando material e resumo executivo. */
  access_count: number
  access_visitors: number
  last_access_at: string | null
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
  /** Cliques acumulados no link do prompt na landing. */
  access_count: number
  access_visitors: number
  last_access_at: string | null
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
