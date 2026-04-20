<script setup lang="ts">
import { RouterLink, RouterView } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()

function onLogout() {
  auth.logout()
  window.location.replace('/')
}
</script>

<template>
  <div class="admin-layout">
    <aside class="admin-sidebar">
      <RouterLink to="/" class="admin-sidebar-link">← Início</RouterLink>
      <RouterLink to="/admin" class="admin-sidebar-link" exact-active-class="active">Dashboard</RouterLink>
      <RouterLink to="/admin/trilhas" class="admin-sidebar-link" active-class="active">Trilhas</RouterLink>
      <RouterLink to="/admin/usuarios" class="admin-sidebar-link" active-class="active">Usuários</RouterLink>
      <RouterLink to="/admin/quiz" class="admin-sidebar-link" active-class="active">Quiz</RouterLink>
      <button type="button" class="admin-sidebar-link admin-sidebar-logout" @click="onLogout">Sair</button>
    </aside>
    <main class="admin-main">
      <RouterView />
    </main>
  </div>
</template>

<style scoped>
.admin-layout {
  display: flex;
  min-height: 100vh;
}
.admin-sidebar {
  width: 220px;
  background: var(--k0);
  color: var(--wh);
  padding: 24px 0;
  display: flex;
  flex-direction: column;
}
.admin-sidebar-link {
  display: block;
  padding: 10px 24px;
  color: rgba(255, 255, 255, 0.8);
  text-decoration: none;
  font-size: 14px;
}
.admin-sidebar-link:hover,
.admin-sidebar-link.active {
  background: rgba(255, 255, 255, 0.08);
  color: var(--wh);
}
.admin-sidebar-logout {
  margin-top: auto;
  width: 100%;
  border: none;
  background: none;
  text-align: left;
  font-size: 14px;
  cursor: pointer;
  color: rgba(255, 255, 255, 0.8);
}
.admin-sidebar-logout:hover {
  background: rgba(255, 255, 255, 0.08);
  color: var(--wh);
}
.admin-main {
  flex: 1;
  padding: 24px;
  background: var(--k9);
}
</style>
