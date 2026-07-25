<script setup lang="ts">
/**
 * Landing: exibe a página estática lp.html (aparência exata).
 * Em produção o backend serve lp.html em GET /; em dev (Vite) carregamos no iframe.
 * loginBase na URL do iframe permite à LP (cross-origin) saber onde está o app para o link "Entrar".
 */
const base = import.meta.env.VITE_API_BASE_URL ?? ''
const origin = typeof window !== 'undefined' ? window.location.origin : ''
/** Em dev: servir public/lp.html via Vite (sempre atual). Em prod: backend em /. */
const landingBase =
  base
    ? base.replace(/\/$/, '') + '/'
    : import.meta.env.DEV
      ? origin + '/lp.html'
      : origin + '/'
/** Mesma base que o cliente Vue (`client.ts`): necessária para o POST de leads quando a API está em outro host. */
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
</script>

<template>
  <div class="landing-iframe-wrap">
    <iframe
      :src="landingUrl"
      title="Valorian 4 Future — Landing"
      class="landing-iframe"
      frameborder="0"
    />
  </div>
</template>

<style scoped>
.landing-iframe-wrap {
  position: fixed;
  inset: 0;
  width: 100%;
  height: 100%;
}
.landing-iframe {
  width: 100%;
  height: 100%;
  display: block;
  border: none;
}
</style>
