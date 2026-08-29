<script setup lang="ts">
import { ref, watch } from 'vue'
import { RouterLink, RouterView, useRoute } from 'vue-router'
import Topbar from '@/components/layout/Topbar.vue'
import { ADMIN_NAV_ITEMS } from '@/lib/adminNav'

const route = useRoute()
const drawerOpen = ref(false)

watch(
  () => route.path,
  () => {
    drawerOpen.value = false
  }
)
</script>

<template>
  <Topbar />
  <div class="admin-layout" :class="{ 'admin-layout--drawer-open': drawerOpen }">
    <button
      type="button"
      class="admin-menu-toggle"
      aria-label="Abrir menu administrativo"
      :aria-expanded="drawerOpen"
      @click="drawerOpen = !drawerOpen"
    >
      <span aria-hidden="true" />
      <span aria-hidden="true" />
      <span aria-hidden="true" />
    </button>
    <div
      class="admin-sidebar-backdrop"
      aria-hidden="true"
      @click="drawerOpen = false"
    />
    <aside class="admin-sidebar" aria-label="Menu administrativo">
      <p class="admin-sidebar-title">Administração</p>
      <RouterLink
        v-for="item in ADMIN_NAV_ITEMS"
        :key="item.to"
        :to="item.to"
        class="admin-sidebar-link"
        v-bind="item.exact ? { 'exact-active-class': 'active' } : { 'active-class': 'active' }"
      >{{ item.label }}</RouterLink>
    </aside>
    <main class="admin-main">
      <RouterView />
    </main>
  </div>
</template>

<style scoped>
.admin-layout {
  display: flex;
  min-height: calc(100vh - var(--bar-h));
  padding-top: var(--bar-h);
  position: relative;
}

.admin-menu-toggle {
  display: none;
  position: fixed;
  top: calc(var(--bar-h) + 12px);
  left: 12px;
  z-index: 120;
  width: 44px;
  height: 44px;
  padding: 10px;
  border: 1px solid var(--bd);
  border-radius: var(--r-md);
  background: var(--wh);
  box-shadow: var(--shadow-1);
  flex-direction: column;
  justify-content: center;
  gap: 5px;
}

.admin-menu-toggle span {
  display: block;
  height: 2px;
  background: var(--k0);
  border-radius: 1px;
}

.admin-sidebar-backdrop {
  display: none;
}

.admin-sidebar {
  width: 220px;
  flex-shrink: 0;
  background: var(--k0);
  color: var(--wh);
  padding: 20px 0;
  display: flex;
  flex-direction: column;
  z-index: 110;
}

.admin-sidebar-title {
  padding: 0 24px 12px;
  font-size: var(--fs-xs);
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.45);
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

.admin-main {
  flex: 1;
  min-width: 0;
  padding: 24px;
  background: var(--k9);
}

@media (max-width: 1023px) {
  .admin-menu-toggle {
    display: flex;
  }

  .admin-sidebar-backdrop {
    display: block;
    position: fixed;
    top: var(--bar-h);
    left: 0;
    right: 0;
    bottom: 0;
    z-index: 100;
    background: rgba(12, 35, 64, 0.45);
    opacity: 0;
    pointer-events: none;
    transition: opacity 0.2s ease;
  }

  .admin-layout--drawer-open .admin-sidebar-backdrop {
    opacity: 1;
    pointer-events: auto;
  }

  .admin-sidebar {
    position: fixed;
    top: var(--bar-h);
    left: 0;
    bottom: 0;
    transform: translateX(-100%);
    transition: transform 0.2s ease;
    box-shadow: var(--shadow-3);
  }

  .admin-layout--drawer-open .admin-sidebar {
    transform: translateX(0);
  }

  .admin-main {
    padding: 56px 16px 24px;
  }
}

@media (max-width: 767px) {
  .admin-main {
    padding: 52px 12px 20px;
  }
}
</style>
