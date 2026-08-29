<script setup lang="ts">
import { useMaturityEditor } from '@/composables/useMaturityEditor'
import StateBlock from '@/components/ui/StateBlock.vue'
import AiMaturityBody from '@/components/maturity/AiMaturityBody.vue'

const editor = useMaturityEditor()
const { loading, error, model } = editor
</script>

<template>
  <div class="wrap">
    <StateBlock v-if="loading" state="loading" message="Carregando diagnóstico…" />
    <StateBlock v-else-if="error" state="error" :message="error" />
    <AiMaturityBody v-else-if="model" :editor="editor" />
  </div>
</template>

<style scoped>
.wrap {
  max-width: 920px;
  margin: 0 auto;
  padding: 16px 16px 48px;
}
</style>
