<script setup lang="ts">
// UX-06: antes, uma ilustração em tela cheia sobre #0c1827 com botões em hex
// cru — único ponto da base fora do design system e sem tipografia da
// marca. Agora usa o mesmo AccessStateLayout do 404 e do "acesso negado".
import AccessStateLayout from '@/components/ui/AccessStateLayout.vue'
import AppButton from '@/components/ui/AppButton.vue'
</script>

<template>
  <AccessStateLayout variant="401" title="Acesso não autorizado">
    Sua sessão expirou ou você não tem permissão para acessar esta página. Entre novamente para continuar.
    <template #actions>
      <AppButton variant="primary" to="/login">Entrar</AppButton>
      <AppButton variant="secondary" to="/">Voltar ao início</AppButton>
    </template>
  </AccessStateLayout>
</template>
