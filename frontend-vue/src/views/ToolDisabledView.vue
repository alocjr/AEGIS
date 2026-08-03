<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { TOOL_HOME_ORDER } from '@/lib/tools'

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
    <div class="card">
      <h1>Ferramenta não disponível</h1>
      <p>
        <strong>{{ toolLabel }}</strong> não está habilitada para o seu acesso.
        Peça ao administrador da plataforma para liberar.
      </p>
      <RouterLink :to="fallbackPath" class="btn">Voltar</RouterLink>
    </div>
  </div>
</template>

<style scoped>
.page {
  max-width: 520px;
  margin: 48px auto;
  padding: 0 20px 60px;
}
.card {
  background: var(--wh);
  border: 1px solid var(--bd);
  border-radius: 12px;
  padding: 28px 24px;
}
h1 {
  font-family: var(--serif);
  font-size: 22px;
  color: var(--k0);
  margin-bottom: 10px;
}
p {
  font-size: 14px;
  color: var(--k3);
  line-height: 1.55;
  margin-bottom: 20px;
}
.btn {
  display: inline-block;
  padding: 8px 16px;
  background: var(--k0);
  color: var(--wh);
  border-radius: 6px;
  font-size: 13px;
  text-decoration: none;
}
</style>
