<script setup lang="ts">
/**
 * AR-01: título + subtítulo + ações de página, reimplementado em 17 arquivos
 * (.page-header) e 18 (.page-title) com pequenas variações de espaçamento e
 * tipografia. Uma view usa a #actions slot para os botões do canto direito.
 */
defineProps<{
  title: string
  subtitle?: string | null
}>()
</script>

<template>
  <header class="page-header">
    <div class="page-header__text">
      <h1 class="page-header__title">{{ title }}</h1>
      <p v-if="subtitle" class="page-header__subtitle">{{ subtitle }}</p>
    </div>
    <div v-if="$slots.actions" class="page-header__actions">
      <slot name="actions" />
    </div>
  </header>
</template>

<style scoped>
.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  flex-wrap: wrap;
  margin-bottom: 28px;
}
.page-header__title {
  font-family: var(--serif);
  font-weight: 400;
  font-size: var(--fs-2xl);
  color: var(--k0);
  letter-spacing: -0.01em;
}
.page-header__subtitle {
  margin-top: 6px;
  font-size: var(--fs-md);
  color: var(--k3);
  max-width: 62ch;
}
.page-header__actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

@media (max-width: 640px) {
  .page-header {
    flex-direction: column;
    align-items: stretch;
  }
  .page-header__actions {
    justify-content: flex-end;
  }
}
</style>
