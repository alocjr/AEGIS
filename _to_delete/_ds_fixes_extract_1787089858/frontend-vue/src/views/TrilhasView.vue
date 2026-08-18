<script setup lang="ts">
import { useCourses } from '@/composables/useCourses'
import CourseCard from '@/components/course/CourseCard.vue'

const { courses, loading, error } = useCourses()
</script>

<template>
  <div class="wrap">
    <h1>Trilhas de Aprendizagem</h1>
    <p class="muted">Conheça nossas trilhas.</p>
    <div v-if="loading" class="loading">Carregando trilhas...</div>
    <div v-else-if="error" class="empty">{{ error }}</div>
    <div v-else-if="courses.length === 0" class="empty">Nenhuma trilha cadastrada.</div>
    <div v-else class="card-grid">
      <CourseCard v-for="c in courses" :key="c.slug" :course="c" />
    </div>
  </div>
</template>

<style scoped>
.wrap { max-width: 980px; margin: 24px auto; padding: 0 20px; }
h1 { font-size: 24px; margin-bottom: 8px; }
.muted { color: var(--k3); font-size: 14px; margin-bottom: 24px; }
.card-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; }
.loading, .empty { text-align: center; padding: 48px 20px; color: var(--k5); }
</style>
