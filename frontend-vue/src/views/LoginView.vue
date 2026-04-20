<script setup lang="ts">
import { useRouter } from 'vue-router'
import AuthOverlay from '@/components/landing/AuthOverlay.vue'

const router = useRouter()

function onClose() {
  router.replace('/')
}
</script>

<template>
  <div class="login-page">
    <AuthOverlay :show="true" @close="onClose" />
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  background: var(--navy-deep, #0C1827);
}
</style>
