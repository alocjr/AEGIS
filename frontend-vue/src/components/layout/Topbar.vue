<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import {
  TOOL_CANVAS,
  TOOL_GOVERNANCE,
  TOOL_MATURITY,
  TOOL_OKR,
  TOOL_STRATEGIC_MAP,
  TOOL_SWOT,
} from '@/lib/tools'

type NavGroup = 'mentoria' | 'hub'

const auth = useAuthStore()
const menuOpen = ref(false)
const openGroup = ref<NavGroup | null>(null)
const mentoriaEl = ref<HTMLElement | null>(null)
const hubEl = ref<HTMLElement | null>(null)
const route = useRoute()

/** Membros de organização sem trilha (ex.: criados por um admin de organização) não têm
 * progresso/materiais/agenda/quiz de mentoria — só as ferramentas do AI Hub. */
const hasTrilha = computed(() => (auth.user?.course_slugs?.length ?? 0) > 0)

const showMentoria = computed(() => hasTrilha.value)
const showAiHub = computed(
  () =>
    auth.hasTool(TOOL_MATURITY) ||
    auth.hasTool(TOOL_SWOT) ||
    auth.hasTool(TOOL_OKR) ||
    auth.hasTool(TOOL_CANVAS) ||
    auth.hasTool(TOOL_STRATEGIC_MAP) ||
    auth.hasTool(TOOL_GOVERNANCE),
)

function pathIn(prefixes: string[]): boolean {
  const p = route.path
  return prefixes.some((pre) => p === pre || p.startsWith(`${pre}/`))
}

const mentoriaActive = computed(() =>
  pathIn(['/programa', '/materiais', '/agenda', '/quiz-respostas', '/quiz']),
)
const hubActive = computed(() =>
  pathIn([
    '/ai-maturity',
    '/swot',
    '/okrs',
    '/projetos',
    '/roadmap',
    '/mapa-estrategico',
    '/governanca',
  ]),
)

function toggleGroup(id: NavGroup) {
  openGroup.value = openGroup.value === id ? null : id
}

function closeNav() {
  menuOpen.value = false
  openGroup.value = null
}

function onDocPointerDown(ev: PointerEvent) {
  if (!openGroup.value) return
  const t = ev.target as Node
  if (openGroup.value === 'mentoria' && mentoriaEl.value?.contains(t)) return
  if (openGroup.value === 'hub' && hubEl.value?.contains(t)) return
  openGroup.value = null
}

function onKeydown(ev: KeyboardEvent) {
  if (ev.key === 'Escape') openGroup.value = null
}

onMounted(() => {
  auth.loadUser()
  document.addEventListener('pointerdown', onDocPointerDown)
  document.addEventListener('keydown', onKeydown)
})

onUnmounted(() => {
  document.removeEventListener('pointerdown', onDocPointerDown)
  document.removeEventListener('keydown', onKeydown)
})

watch(() => route.path, () => {
  closeNav()
})

function onLogout() {
  void auth.logout().then(() => {
    window.location.replace('/')
  })
}

function toggleMenu() {
  menuOpen.value = !menuOpen.value
  if (!menuOpen.value) openGroup.value = null
}

const orgOptions = computed(() => auth.user?.organizations ?? [])
const showOrgSwitcher = computed(() => orgOptions.value.length > 1)
const switchingOrg = ref(false)

async function onSwitchOrg(ev: Event) {
  const id = (ev.target as HTMLSelectElement).value
  if (!id || id === auth.user?.organization_id) return
  switchingOrg.value = true
  try {
    await auth.switchOrganization(id)
  } catch {
    switchingOrg.value = false
  }
}
</script>

<template>
  <header class="topbar">
    <RouterLink to="/" class="tb-brand" @click="closeNav">
      <span class="tb-sub">Valorian 4 Future</span>
    </RouterLink>
    <div v-if="auth.isLoggedIn && (showOrgSwitcher || auth.user?.organization_name)" class="tb-org">
      <select
        v-if="showOrgSwitcher"
        class="tb-org-select"
        :value="auth.user?.organization_id || ''"
        :disabled="switchingOrg"
        aria-label="Trocar organização"
        @change="onSwitchOrg"
      >
        <option v-for="org in orgOptions" :key="org.id" :value="org.id">{{ org.name }}</option>
      </select>
      <span v-else class="tb-org-name">{{ auth.user?.organization_name }}</span>
    </div>
    <button
      type="button"
      class="tb-burger"
      aria-label="Abrir menu"
      :aria-expanded="menuOpen"
      @click="toggleMenu"
    >
      <span class="tb-burger-bar" />
      <span class="tb-burger-bar" />
      <span class="tb-burger-bar" />
    </button>
    <nav class="tb-right" :class="{ 'tb-right--open': menuOpen }">
      <template v-if="auth.isLoggedIn">
        <div v-if="showMentoria" ref="mentoriaEl" class="tb-dd">
          <button
            type="button"
            class="tb-pill tb-dd-btn"
            :class="{ 'tb-pill--on': mentoriaActive }"
            :aria-expanded="openGroup === 'mentoria'"
            aria-haspopup="menu"
            aria-controls="tb-menu-mentoria"
            @click="toggleGroup('mentoria')"
          >
            Mentoria
            <span class="tb-caret" aria-hidden="true" />
          </button>
          <div
            v-show="openGroup === 'mentoria'"
            id="tb-menu-mentoria"
            class="tb-dd-panel"
            role="menu"
          >
            <RouterLink to="/programa" class="tb-dd-item" role="menuitem" @click="closeNav">Progresso</RouterLink>
            <RouterLink to="/materiais" class="tb-dd-item" role="menuitem" @click="closeNav">Materiais</RouterLink>
            <RouterLink to="/agenda" class="tb-dd-item" role="menuitem" @click="closeNav">Agenda</RouterLink>
            <RouterLink to="/quiz-respostas" class="tb-dd-item" role="menuitem" @click="closeNav">Quiz</RouterLink>
          </div>
        </div>
        <div v-if="showAiHub" ref="hubEl" class="tb-dd">
          <button
            type="button"
            class="tb-pill tb-dd-btn"
            :class="{ 'tb-pill--on': hubActive }"
            :aria-expanded="openGroup === 'hub'"
            aria-haspopup="menu"
            aria-controls="tb-menu-hub"
            @click="toggleGroup('hub')"
          >
            AI Hub
            <span class="tb-caret" aria-hidden="true" />
          </button>
          <div
            v-show="openGroup === 'hub'"
            id="tb-menu-hub"
            class="tb-dd-panel"
            role="menu"
          >
            <RouterLink
              v-if="auth.hasTool(TOOL_MATURITY)"
              to="/ai-maturity"
              class="tb-dd-item"
              role="menuitem"
              @click="closeNav"
            >Modelo de Maturidade</RouterLink>
            <RouterLink
              v-if="auth.hasTool(TOOL_SWOT)"
              to="/swot"
              class="tb-dd-item"
              role="menuitem"
              @click="closeNav"
            >SWOT</RouterLink>
            <RouterLink
              v-if="auth.hasTool(TOOL_OKR)"
              to="/okrs"
              class="tb-dd-item"
              role="menuitem"
              @click="closeNav"
            >OKR</RouterLink>
            <RouterLink
              v-if="auth.hasTool(TOOL_CANVAS)"
              to="/projetos"
              class="tb-dd-item"
              role="menuitem"
              @click="closeNav"
            >AI Canvas</RouterLink>
            <RouterLink
              v-if="auth.hasTool(TOOL_CANVAS)"
              to="/roadmap"
              class="tb-dd-item"
              role="menuitem"
              @click="closeNav"
            >Roadmap</RouterLink>
            <RouterLink
              v-if="auth.hasTool(TOOL_STRATEGIC_MAP)"
              to="/mapa-estrategico"
              class="tb-dd-item"
              role="menuitem"
              @click="closeNav"
            >Mapa Estratégico</RouterLink>
            <RouterLink
              v-if="auth.hasTool(TOOL_GOVERNANCE)"
              to="/governanca/inventario"
              class="tb-dd-item"
              role="menuitem"
              @click="closeNav"
            >Governança</RouterLink>
          </div>
        </div>
        <RouterLink
          v-if="auth.isOrgAdmin"
          to="/organizacao/usuarios"
          class="tb-pill"
          @click="closeNav"
        >Minha Organização</RouterLink>
        <RouterLink
          v-if="(auth.user?.course_slugs?.length ?? 0) > 1"
          to="/trilhas"
          class="tb-pill tb-pill-g"
          @click="closeNav"
        >Trocar trilha</RouterLink>
        <RouterLink v-if="auth.isAdmin" to="/admin" class="tb-pill" @click="closeNav">Admin</RouterLink>
        <button type="button" class="tb-pill tb-pill-logout" @click="onLogout">Sair</button>
      </template>
      <template v-else>
        <RouterLink to="/" class="tb-pill" @click="closeNav">Início</RouterLink>
        <RouterLink to="/trilhas" class="tb-pill" @click="closeNav">Trilhas</RouterLink>
      </template>
    </nav>
    <div
      v-if="menuOpen"
      class="tb-backdrop"
      aria-hidden="true"
      @click="closeNav"
    />
  </header>
</template>
<style scoped>
.topbar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: var(--bar-h);
  background: var(--k0);
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  display: flex;
  align-items: center;
  padding: 0 20px;
  z-index: 400;
}
.tb-brand {
  display: flex;
  align-items: center;
  gap: 14px;
  color: var(--wh);
  text-decoration: none;
}
.tb-sub {
  font-size: 11px;
  font-weight: 300;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.9);
}
.tb-org {
  margin-left: 16px;
  min-width: 0;
}
.tb-org-name {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.65);
  letter-spacing: 0.04em;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 220px;
  display: block;
}
.tb-org-select {
  height: 32px;
  max-width: 220px;
  padding: 0 10px;
  border: 1px solid rgba(255, 255, 255, 0.25);
  border-radius: var(--r-xs);
  background: rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.95);
  font: inherit;
  font-size: 12px;
  letter-spacing: 0.03em;
  cursor: pointer;
}
.tb-org-select:disabled {
  opacity: 0.6;
  cursor: wait;
}
.tb-burger {
  display: none;
  margin-left: auto;
  width: 44px;
  height: 44px;
  padding: 0;
  border: none;
  background: transparent;
  color: rgba(255, 255, 255, 0.9);
  cursor: pointer;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: 5px;
  border-radius: var(--r-xs);
  transition: background 0.2s;
}
.tb-burger:hover {
  background: rgba(255, 255, 255, 0.08);
}
.tb-burger-bar {
  display: block;
  width: 20px;
  height: 2px;
  background: currentColor;
  border-radius: 1px;
  transition: transform 0.2s, opacity 0.2s;
}
.tb-right {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 8px;
}
.tb-pill {
  height: 36px;
  padding: 0 16px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: var(--r-xs);
  font-size: 13px;
  letter-spacing: 0.05em;
  color: rgba(255, 255, 255, 0.9);
  background: transparent;
  display: inline-flex;
  align-items: center;
  text-decoration: none;
  transition: background 0.2s, border-color 0.2s;
  white-space: nowrap;
}
.tb-pill:hover,
.tb-pill--on {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(255, 255, 255, 0.35);
}
.tb-pill-g {
  color: var(--gold2);
  border-color: rgba(155, 126, 70, 0.4);
}
.tb-pill-g:hover {
  background: rgba(155, 126, 70, 0.15);
  border-color: var(--gold2);
}
.tb-pill-logout {
  cursor: pointer;
  font-family: inherit;
}
.tb-pill-logout:hover {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(255, 255, 255, 0.35);
}
.tb-dd {
  position: relative;
}
.tb-dd-btn {
  cursor: pointer;
  font-family: inherit;
  gap: 8px;
}
.tb-caret {
  display: inline-block;
  width: 0;
  height: 0;
  border-left: 4px solid transparent;
  border-right: 4px solid transparent;
  border-top: 5px solid currentColor;
  opacity: 0.7;
  transition: transform 0.15s ease;
}
.tb-dd-btn[aria-expanded='true'] .tb-caret {
  transform: rotate(180deg);
}
.tb-dd-panel {
  position: absolute;
  top: calc(100% + 6px);
  right: 0;
  min-width: 220px;
  padding: 6px;
  display: flex;
  flex-direction: column;
  gap: 2px;
  background: var(--k0);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: var(--r-xs);
  box-shadow: 0 10px 28px rgba(0, 0, 0, 0.35);
  z-index: 410;
}
.tb-dd-item {
  display: flex;
  align-items: center;
  height: 36px;
  padding: 0 12px;
  border-radius: var(--r-xs);
  color: rgba(255, 255, 255, 0.9);
  text-decoration: none;
  font-size: 13px;
  letter-spacing: 0.04em;
  white-space: nowrap;
}
.tb-dd-item:hover,
.tb-dd-item.router-link-active {
  background: rgba(255, 255, 255, 0.1);
}
.tb-backdrop {
  display: none;
}

@media (max-width: 900px) {
  .tb-org-select,
  .tb-org-name {
    max-width: 42vw;
  }
  .tb-burger {
    display: flex;
  }
  .tb-right {
    position: fixed;
    top: var(--bar-h);
    right: 0;
    bottom: 0;
    width: min(280px, 85vw);
    margin: 0;
    padding: 20px 16px;
    flex-direction: column;
    align-items: stretch;
    gap: 4px;
    background: var(--k0);
    border-left: 1px solid rgba(255, 255, 255, 0.08);
    box-shadow: -4px 0 24px rgba(0, 0, 0, 0.2);
    transform: translateX(100%);
    visibility: hidden;
    transition: transform 0.25s ease, visibility 0.25s;
    z-index: 399;
    overflow-y: auto;
  }
  .tb-right--open {
    transform: translateX(0);
    visibility: visible;
  }
  .tb-pill {
    justify-content: center;
    height: 44px;
    padding: 0 16px;
  }
  .tb-dd {
    display: flex;
    flex-direction: column;
    align-items: stretch;
  }
  .tb-dd-panel {
    position: static;
    min-width: 0;
    margin-top: 4px;
    box-shadow: none;
  }
  .tb-dd-item {
    justify-content: center;
    height: 40px;
  }
  .tb-backdrop {
    display: block;
    position: fixed;
    inset: 0;
    top: var(--bar-h);
    background: rgba(0, 0, 0, 0.4);
    z-index: 398;
    animation: tb-fade 0.2s ease;
  }
}

@keyframes tb-fade {
  from { opacity: 0; }
  to { opacity: 1; }
}
</style>
