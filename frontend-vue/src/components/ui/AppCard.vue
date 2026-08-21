<script setup lang="ts">
/**
 * AR-01: substitui os wrappers ".card"/".panel"/".box" divergentes
 * (16 arquivos, 3 nomes de classe distintos para o mesmo padrão visual:
 * fundo branco, borda 1px, raio e sombra do design system).
 */
withDefaults(
  defineProps<{
    /** Remove padding interno, para quando o conteúdo controla o próprio espaçamento (ex.: tabelas). */
    flush?: boolean
    /** Realça a borda com a cor de destaque (uso raro: card selecionado/ativo). */
    highlighted?: boolean
  }>(),
  { flush: false, highlighted: false }
)
</script>

<template>
  <section class="app-card" :class="{ 'app-card--flush': flush, 'app-card--highlighted': highlighted }">
    <header v-if="$slots.header" class="app-card__header">
      <slot name="header" />
    </header>
    <div class="app-card__body">
      <slot />
    </div>
    <footer v-if="$slots.footer" class="app-card__footer">
      <slot name="footer" />
    </footer>
  </section>
</template>

<style scoped>
.app-card {
  background: var(--wh);
  border: 1px solid var(--bd);
  border-radius: var(--r-lg);
  box-shadow: var(--shadow-1);
}
.app-card--highlighted {
  border-color: var(--gold);
}
.app-card__header {
  padding: 18px 22px;
  border-bottom: 1px solid var(--bd);
}
.app-card__body {
  padding: 22px;
}
.app-card--flush .app-card__body {
  padding: 0;
}
.app-card__footer {
  padding: 16px 22px;
  border-top: 1px solid var(--bd);
}
</style>
