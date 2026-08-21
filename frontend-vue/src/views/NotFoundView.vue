<script setup lang="ts">
// UX-07: o router não tinha rota catch-all — qualquer caminho inválido caía
// em tela em branco dentro do layout. Reaproveita o AccessStateLayout do
// UX-06 (mesma família de evento: acesso/rota indisponível).
import AccessStateLayout from '@/components/ui/AccessStateLayout.vue'
import AppButton from '@/components/ui/AppButton.vue'
</script>

<template>
  <AccessStateLayout variant="404" title="Página não encontrada">
    O endereço acessado não existe ou foi movido.
    <template #actions>
      <AppButton variant="primary" to="/">Voltar ao início</AppButton>
    </template>
  </AccessStateLayout>
</template>
