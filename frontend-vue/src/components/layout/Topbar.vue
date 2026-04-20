<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const menuOpen = ref(false)
const route = useRoute()

onMounted(() => {
  auth.loadUser()
})

watch(() => route.path, () => {
  menuOpen.value = false
})

function onLogout() {
  auth.logout()
  window.location.replace('/')
}

function toggleMenu() {
  menuOpen.value = !menuOpen.value
}
</script>

<template>
  <header class="topbar">
    <RouterLink to="/" class="tb-brand" @click="menuOpen = false">
      <span class="tb-sub">Valorian 4 Future</span>
    </RouterLink>
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
        <RouterLink to="/programa" class="tb-pill" @click="menuOpen = false">Progresso</RouterLink>
        <RouterLink to="/materiais" class="tb-pill" @click="menuOpen = false">Materiais</RouterLink>
        <RouterLink to="/agenda" class="tb-pill" @click="menuOpen = false">Agenda</RouterLink>
        <RouterLink to="/quiz-respostas" class="tb-pill" @click="menuOpen = false">Quiz</RouterLink>
        <RouterLink to="/ai-maturity" class="tb-pill" @click="menuOpen = false">Modelo de Maturidade</RouterLink>
        <RouterLink
          v-if="(auth.user?.course_slugs?.length ?? 0) > 1"
          to="/trilhas"
          class="tb-pill tb-pill-g"
          @click="menuOpen = false"
        >Trocar trilha</RouterLink>
        <RouterLink v-if="auth.isAdmin" to="/admin" class="tb-pill" @click="menuOpen = false">Admin</RouterLink>
        <button type="button" class="tb-pill tb-pill-logout" @click="onLogout">Sair</button>
      </template>
      <template v-else>
        <RouterLink to="/" class="tb-pill" @click="menuOpen = false">Início</RouterLink>
        <RouterLink to="/trilhas" class="tb-pill" @click="menuOpen = false">Trilhas</RouterLink>
      </template>
    </nav>
    <div
      v-if="menuOpen"
      class="tb-backdrop"
      aria-hidden="true"
      @click="menuOpen = false"
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
  border-radius: 4px;
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
  border-radius: 4px;
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
.tb-pill:hover {
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
.tb-backdrop {
  display: none;
}

@media (max-width: 900px) {
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
