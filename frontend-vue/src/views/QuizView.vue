<script setup lang="ts">
import { useQuizEditor } from '@/composables/useQuizEditor'
import PageHeader from '@/components/ui/PageHeader.vue'
import StateBlock from '@/components/ui/StateBlock.vue'
import QuizBody from '@/components/quiz/QuizBody.vue'

const editor = useQuizEditor()
const { loading, error, quiz, encontroId, reviewMode } = editor
</script>

<template>
  <div class="wrap">
    <PageHeader
      :title="`Quiz — Encontro ${encontroId}`"
      :subtitle="
        quiz && reviewMode
          ? 'Você respondeu todas as questões. Racional de cada alternativa abaixo.'
          : quiz
            ? quiz.titulo
            : null
      "
    />
    <StateBlock v-if="loading" state="loading" message="Carregando quiz…" />
    <StateBlock v-else-if="error" state="error" :message="error" />
    <QuizBody v-else-if="quiz" :editor="editor" />
  </div>
</template>

<style scoped>
.wrap {
  max-width: 720px;
  margin: 0 auto;
  padding: 16px 16px 48px;
}
</style>
