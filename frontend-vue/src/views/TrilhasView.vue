<script setup lang="ts">
import { useCourses } from '@/composables/useCourses'
import CourseCard from '@/components/course/CourseCard.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import StateBlock from '@/components/ui/StateBlock.vue'

const { courses, loading, error } = useCourses()
</script>

<template>
  <div class="wrap">
    <PageHeader title="Trilhas de Aprendizagem" subtitle="Conheça nossas trilhas." />
    <StateBlock v-if="loading" state="loading" message="Carregando trilhas…" />
    <StateBlock v-else-if="error" state="error" :message="error" />
    <StateBlock v-else-if="courses.length === 0" state="empty" message="Nenhuma trilha cadastrada." />
    <div v-else class="card-grid">
      <CourseCard v-for="c in courses" :key="c.slug" :course="c" />
    </div>
  </div>
</template>

<style scoped>
.wrap { max-width: 980px; margin: 24px auto; padding: 0 20px; }
.card-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; }
</style>
