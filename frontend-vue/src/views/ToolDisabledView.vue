<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { TOOL_HOME_ORDER } from '@/lib/tools'
import AppCard from '@/components/ui/AppCard.vue'
import AppButton from '@/components/ui/AppButton.vue'

const route = useRoute()
const auth = useAuthStore()

const toolId = computed(() => String(route.query.tool || ''))
const toolLabel = computed(() => {
  const hit = TOOL_HOME_ORDER.find((t) => t.id === toolId.value)
  return hit?.id
    ? (
        {
          maturity: 'Modelo de Maturidade',
          swot: 'SWOT de IA',
          canvas: 'AI Canvas',
          okr: 'OKR',
          strategic_map: 'Mapa Estratégico',
          governance: 'Governança de IA',
        } as Record<string, string>
      )[hit.id] || hit.id
    : 'esta ferramenta'
})

const fallbackPath = computed(() => auth.homePathWithoutTrilha() || '/programa')
</script>

<template>
  <div class="page">
    <AppCard>
      <h1>Ferramenta não disponível</h1>
      <p>
        <strong>{{ toolLabel }}</strong> não está habilitada para o seu acesso.
        Peça ao administrador da plataforma para liberar.
      </p>
      <AppButton :to="fallbackPath">Voltar</AppButton>
    </AppCard>
  </div>
</template>

<style scoped>
.page {
  max-width: 520px;
  margin: 48px auto;
  padding: 0 20px 60px;
}
h1 {
  font-family: var(--serif);
  font-size: var(--fs-xl);
  color: var(--k0);
  margin-bottom: 10px;
}
p {
  font-size: var(--fs-base);
  color: var(--k3);
  line-height: 1.55;
  margin-bottom: 20px;
}
</style>
