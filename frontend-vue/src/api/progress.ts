import { post } from './client'

export interface ProgressMaterialCheckPayload {
  encontro_id: number
  material_index: number
  checked: boolean
  course_slug?: string
}

export function updateMaterialCheck(payload: ProgressMaterialCheckPayload): Promise<void> {
  return post<void>('/api/progress/material', payload)
}

export function completeEncontro(encontroId: number, courseSlug?: string): Promise<void> {
  const url = courseSlug
    ? `/api/progress/complete/${encontroId}?course_slug=${encodeURIComponent(courseSlug)}`
    : `/api/progress/complete/${encontroId}`
  return post<void>(url, {})
}
