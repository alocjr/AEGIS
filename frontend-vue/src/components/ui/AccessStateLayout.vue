<script setup lang="ts">
import AppCard from './AppCard.vue'

/**
 * UX-06 / UX-07: unifica os três estados de "acesso barrado" — 401
 * (UnauthorizedView), ferramenta desabilitada (ToolDisabledView) e agora
 * 404 (NotFoundView, que não existia — router sem catch-all, UX-07). Antes,
 * /401 era uma ilustração em tela cheia sobre #0c1827 com botões em hex cru
 * (#9b7e46, #b8975a), sem topbar nem tipografia da marca; /acesso-negado já
 * usava os tokens do design system. Mesma família de evento, dois produtos
 * visuais — agora um só componente, três variantes de rótulo/texto.
 */
withDefaults(
  defineProps<{
    variant: '401' | 'tool-disabled' | '404'
    title: string
    /** true quando renderizado dentro do DefaultLayout (com topbar fixa) — evita 100vh dobrado. */
    nested?: boolean
  }>(),
  { nested: false }
)

const BADGE_LABEL: Record<'401' | 'tool-disabled' | '404', string> = {
  '401': '401',
  'tool-disabled': '—',
  '404': '404',
}
</script>

<template>
  <div class="access-state" :class="{ 'access-state--nested': nested }">
    <AppCard class="access-state__card">
      <div class="access-state__badge" :class="`access-state__badge--${variant}`" aria-hidden="true">
        {{ BADGE_LABEL[variant] }}
      </div>
      <h1 class="access-state__title">{{ title }}</h1>
      <p class="access-state__message"><slot /></p>
      <div class="access-state__actions">
        <slot name="actions" />
      </div>
    </AppCard>
  </div>
</template>

<style scoped>
.access-state {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: var(--bg);
}
.access-state--nested {
  min-height: calc(100vh - var(--bar-h));
}
.access-state__card {
  max-width: 460px;
  width: 100%;
  text-align: center;
}
.access-state__badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 56px;
  height: 40px;
  padding: 0 14px;
  margin: 0 auto 18px;
  border-radius: var(--r-pill);
  border: 1px solid var(--goldbd);
  background: var(--golddim);
  color: var(--gold);
  font-family: var(--serif);
  font-size: var(--fs-lg);
  font-weight: 600;
  letter-spacing: 0.02em;
}
.access-state__title {
  font-family: var(--serif);
  font-weight: 400;
  font-size: var(--fs-xl);
  color: var(--k0);
  margin-bottom: 10px;
}
.access-state__message {
  font-size: var(--fs-base);
  color: var(--k3);
  line-height: 1.55;
  margin-bottom: 22px;
}
.access-state__actions {
  display: flex;
  gap: 10px;
  justify-content: center;
  flex-wrap: wrap;
}
</style>
