import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { fetchMe, logoutApi } from '@/api/auth'
import type { AuthUser } from '@/api/auth'
import { firstEnabledToolPath } from '@/lib/tools'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<AuthUser | null>(null)
  const loaded = ref(false)
  /** Trilha atualmente selecionada (para usuários com mais de uma). Usado em /programa e nas APIs de progresso. */
  const currentCourseSlug = ref<string | null>(null)

  const isLoggedIn = computed(() => user.value !== null)
  const isAdmin = computed(() => user.value?.is_admin ?? false)
  const isOrgAdmin = computed(() => user.value?.is_org_admin ?? false)
  const tools = computed(() => user.value?.tools ?? [])

  function hasTool(toolId: string): boolean {
    return tools.value.includes(toolId)
  }

  /** Destino pós-login quando não há trilha: primeira ferramenta liberada, ou null. */
  function homePathWithoutTrilha(): string | null {
    return firstEnabledToolPath(tools.value)
  }

  async function loadUser() {
    try {
      user.value = await fetchMe()
      const slugs = user.value?.course_slugs
      if (slugs?.length && currentCourseSlug.value == null) {
        currentCourseSlug.value = slugs[0] ?? null
      }
    } catch {
      user.value = null
      currentCourseSlug.value = null
    } finally {
      loaded.value = true
    }
  }

  function setUser(u: AuthUser | null) {
    user.value = u
    if (u) loaded.value = true
  }

  function setCurrentCourseSlug(slug: string | null) {
    currentCourseSlug.value = slug
  }

  async function logout() {
    try {
      await logoutApi()
    } catch {
      // Cookie pode já estar ausente; limpa estado local mesmo assim.
    }
    user.value = null
    currentCourseSlug.value = null
  }

  return {
    user,
    loaded,
    currentCourseSlug,
    isLoggedIn,
    isAdmin,
    isOrgAdmin,
    tools,
    hasTool,
    homePathWithoutTrilha,
    loadUser,
    setUser,
    setCurrentCourseSlug,
    logout,
  }
})
