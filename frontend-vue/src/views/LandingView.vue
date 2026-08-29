<script setup lang="ts">
import { onMounted } from 'vue'

/**
 * AR-07: redireciona para lp.html estática (sem iframe).
 * Em produção o backend já serve lp.html em GET /; em dev (Vite) usamos /lp.html.
 * loginBase e apiBase permitem à LP saber onde está o app Vue e a API de leads.
 */
const base = import.meta.env.VITE_API_BASE_URL ?? ''
const origin = typeof window !== 'undefined' ? window.location.origin : ''
const landingBase =
  base
    ? base.replace(/\/$/, '') + '/'
    : import.meta.env.DEV
      ? origin + '/lp.html'
      : origin + '/'
const apiBaseForLeads = base.trim().replace(/\/$/, '')
const landingParams = new URLSearchParams()
if (origin) landingParams.set('loginBase', origin)
if (apiBaseForLeads) landingParams.set('apiBase', apiBaseForLeads)
const q = landingParams.toString()
const landingUrl = (() => {
  if (!landingBase) return landingBase
  if (!q) return landingBase
  const sep = landingBase.includes('?') ? '&' : '?'
  return landingBase + sep + q
})()

onMounted(() => {
  if (landingUrl) window.location.replace(landingUrl)
})
</script>

<template>
  <div class="landing-redirect" aria-live="polite">
    <p>Redirecionando para a página inicial…</p>
  </div>
</template>

<style scoped>
.landing-redirect {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 40vh;
  color: var(--k3);
  font-size: var(--fs-md);
}
</style>
