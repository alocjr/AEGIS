<script setup lang="ts">
import { usePrograma } from '@/composables/usePrograma'
import StateBlock from '@/components/ui/StateBlock.vue'
import ProgramaBody from '@/components/programa/ProgramaBody.vue'

const editor = usePrograma()
const { loading, error, noTrilha, data, programa } = editor
</script>

<template>
  <div class="wrap">
    <StateBlock v-if="loading" state="loading" message="Carregando programa…" />
    <StateBlock
      v-else-if="noTrilha"
      state="empty"
      message="Você ainda não tem uma trilha de mentoria. Sua conta participa da organização e já pode usar as ferramentas do AI Hub. O acesso à mentoria é atribuído pela equipe Valorian."
    />
    <StateBlock v-else-if="error" state="error" :message="error" />
    <ProgramaBody v-else-if="data && programa" :editor="editor" />
  </div>
</template>

<style scoped>
.wrap {
  min-height: calc(100vh - var(--bar-h));
}
</style>
