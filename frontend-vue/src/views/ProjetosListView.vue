<script setup lang="ts">
import { useProjetosList } from '@/composables/useProjetosList'
import PageHeader from '@/components/ui/PageHeader.vue'
import StateBlock from '@/components/ui/StateBlock.vue'
import ProjetosListBody from '@/components/projetos/ProjetosListBody.vue'

const editor = useProjetosList()
const { loading, error } = editor
</script>

<template>
  <div class="wrap">
    <PageHeader
      title="Projetos · Canvas de Oportunidades"
      subtitle="Um canvas por área de negócio. Crie um projeto, abra o canvas e preencha da dor à decisão (01→08), ou importe o JSON gerado pelo prompt do Canvas de Oportunidades."
    />
    <StateBlock v-if="loading" state="loading" />
    <StateBlock v-else-if="error" state="error" :message="error" />
    <ProjetosListBody v-else :editor="editor" />
  </div>
</template>

<style scoped>
.wrap {
  max-width: 1080px;
  margin: 0 auto;
  padding: 28px 20px 60px;
}
</style>
