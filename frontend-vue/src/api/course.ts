import { get } from './client'

export interface CurrentCourseResponse {
  course_slug: string
  programa_formacao_executiva: Record<string, unknown>
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
    quiz_por_encontro?: Record<string, { tem_quiz: boolean; respondido: boolean }>
  }
}

export function fetchCurrentCourse(courseSlug?: string): Promise<CurrentCourseResponse> {
  const url = courseSlug
    ? `/api/course/current?course_slug=${encodeURIComponent(courseSlug)}`
    : '/api/course/current'
  return get<CurrentCourseResponse>(url)
}
