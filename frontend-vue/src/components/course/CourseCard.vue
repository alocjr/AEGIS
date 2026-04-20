<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import type { CoursePublic } from '@/types'

const props = withDefaults(
  defineProps<{
    course: CoursePublic
    buttonLabel?: string
    snippetLength?: number
  }>(),
  { buttonLabel: 'Conhecer trilha', snippetLength: 220 }
)

const objectiveSnippet = computed(() => {
  const o = props.course.objetivo ?? ''
  const len = props.snippetLength
  return o.length > len ? o.slice(0, len) + '…' : o
})

const publicoLabel = computed(() => {
  const p = (props.course.publico ?? '').trim()
  if (!p) return ''
  const lower = p.toLowerCase()
  return lower.startsWith('para ') ? lower : `Para ${lower}`
})
</script>

<template>
  <div class="trilha-card">
    <RouterLink :to="`/trilhas/${course.slug}`">
      <span class="tema">{{ course.tema || course.trilha || '' }}</span>
      <h3>{{ course.titulo || course.slug }}</h3>
      <p v-if="course.publico" class="publico">{{ publicoLabel }}</p>
      <p class="objetivo">{{ objectiveSnippet }}</p>
      <div class="meta">
        {{ course.num_encontros ?? 0 }} encontros · {{ course.num_semanas ?? 0 }} semanas
      </div>
      <span class="btn-card">{{ buttonLabel }}</span>
    </RouterLink>
  </div>
</template>

<style scoped>
.trilha-card {
  background: var(--wh);
  border: 1px solid var(--bd);
  border-radius: 6px;
  padding: 28px;
  display: flex;
  flex-direction: column;
  transition: box-shadow 0.2s, border-color 0.2s;
}
.trilha-card:hover {
  border-color: var(--k0);
  box-shadow: 0 8px 28px rgba(0, 0, 0, 0.08);
}
.trilha-card a {
  text-decoration: none;
  color: inherit;
  flex: 1;
  display: flex;
  flex-direction: column;
}
.tema {
  font-size: 11px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--gold);
  margin-bottom: 10px;
}
.trilha-card h3 {
  font-family: var(--serif);
  font-size: 20px;
  margin-bottom: 8px;
  color: var(--k0);
}
.publico {
  font-size: 13px;
  color: var(--k5);
  margin-bottom: 12px;
  font-style: italic;
}
.objetivo {
  font-size: 14px;
  color: var(--k3);
  line-height: 1.6;
  flex: 1;
  margin-bottom: 16px;
  display: -webkit-box;
  -webkit-line-clamp: 4;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.meta {
  font-size: 12px;
  color: var(--k5);
  margin-bottom: 16px;
}
.btn-card {
  display: inline-block;
  padding: 10px 18px;
  border: 1px solid var(--k0);
  background: var(--k0);
  color: var(--wh);
  font-size: 13px;
  border-radius: 4px;
  margin-top: auto;
  width: fit-content;
  transition: opacity 0.2s;
}
.trilha-card .btn-card:hover {
  opacity: 0.9;
}
</style>
