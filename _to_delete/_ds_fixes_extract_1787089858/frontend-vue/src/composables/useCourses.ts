import { computed, onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { useCoursesStore } from '@/stores/courses'

export function useCourses() {
  const store = useCoursesStore()
  const { list, loading, error } = storeToRefs(store)

  onMounted(() => {
    if (list.value.length === 0) {
      store.loadCourses()
    }
  })

  return {
    courses: list,
    loading,
    error,
    loadCourses: store.loadCourses,
    getBySlug: store.getBySlug,
  }
}

export function useCourse(slug: string | undefined) {
  const store = useCoursesStore()
  const course = computed(() => (slug ? store.getBySlug(slug) : undefined))

  onMounted(() => {
    if (slug) store.loadCourse(slug)
  })

  return {
    course,
    loading: store.loading,
    error: store.error,
    loadCourse: store.loadCourse,
  }
}
