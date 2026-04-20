<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import Topbar from '@/components/layout/Topbar.vue'

const route = useRoute()
const isLanding = computed(() => route.path === '/')
</script>

<template>
  <Topbar v-if="!isLanding" />
  <main class="main" :class="{ 'main--no-topbar': isLanding }">
    <RouterView />
  </main>
</template>

<style scoped>
.main {
  padding-top: var(--bar-h);
  min-height: 100vh;
}
.main--no-topbar {
  padding-top: 0;
}
</style>
