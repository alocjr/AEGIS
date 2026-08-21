<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { TOOL_HOME_ORDER } from '@/lib/tools'
import AccessStateLayout from '@/components/ui/AccessStateLayout.vue'
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
  <AccessStateLayout variant="tool-disabled" title="Ferramenta não disponível" nested>
    <strong>{{ toolLabel }}</strong> não está habilitada para o seu acesso. Peça ao administrador da plataforma para liberar.
    <template #actions>
      <AppButton variant="primary" :to="fallbackPath">Voltar</AppButton>
    </template>
  </AccessStateLayout>
</template>
