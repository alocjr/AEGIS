import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { fetchPublicCourses, fetchPublicCourseBySlug } from '@/api/courses'
import type { CoursePublic, ProgramaFormacaoExecutiva } from '@/types'

/** Deriva campos de resumo do programa para exibir no card da lista (evita bug ao voltar de /trilhas/:slug). */
function toListCourse(slug: string, programa?: ProgramaFormacaoExecutiva): CoursePublic {
  const cab = programa?.cabecalho ?? {}
  const vg = programa?.visao_geral ?? {}
  const j = programa?.jornada_aprendizagem ?? []
  const num_encontros = j.reduce((acc, s) => acc + (s.encontros?.length ?? 0), 0)
  return {
    slug,
    titulo: cab.titulo ?? slug,
    tema: cab.tema,
    trilha: cab.trilha,
    publico: cab.publico,
    objetivo: vg.objetivo,
    num_semanas: j.length,
    num_encontros,
    programa_formacao_executiva: programa,
  }
}

export const useCoursesStore = defineStore('courses', () => {
  const list = ref<CoursePublic[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  const courses = computed(() => list.value)

  async function loadCourses() {
    loading.value = true
    error.value = null
    try {
      list.value = await fetchPublicCourses()
      return list.value
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Erro ao carregar trilhas.'
      return []
    } finally {
      loading.value = false
    }
  }

  async function loadCourse(slug: string) {
    loading.value = true
    error.value = null
    try {
      const course = await fetchPublicCourseBySlug(slug)
      const merged: CoursePublic = toListCourse(
        course.slug,
        course.programa_formacao_executiva
      )
      const idx = list.value.findIndex((c) => c.slug === slug)
      if (idx >= 0) list.value[idx] = merged
      else list.value.push(merged)
      return merged
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Erro ao carregar trilha.'
      return null
    } finally {
      loading.value = false
    }
  }

  function getBySlug(slug: string): CoursePublic | undefined {
    return list.value.find((c) => c.slug === slug)
  }

  return { list: courses, loading, error, loadCourses, loadCourse, getBySlug }
})
