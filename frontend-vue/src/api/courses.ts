import { get } from './client'
import type { CoursePublic } from '@/types'

export function fetchPublicCourses(): Promise<CoursePublic[]> {
  return get<CoursePublic[]>('/api/public/courses')
}

export function fetchPublicCourseBySlug(slug: string): Promise<CoursePublic> {
  return get<CoursePublic>(`/api/public/courses/${encodeURIComponent(slug)}`)
}
