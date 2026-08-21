<script setup lang="ts">
/**
 * AR-01: consolida os "pill"/"tag"/"chip" de status (nível de maturidade,
 * tier de plano, status de gate de governança, dimensão SWOT) que hoje
 * reimplementam a mesma forma (raio pill, fundo tonal + texto da mesma cor)
 * com paletas de cores redeclaradas em cada view.
 */
withDefaults(
  defineProps<{
    tone?: 'neutral' | 'success' | 'warn' | 'low' | 'gold'
    size?: 'sm' | 'md'
  }>(),
  { tone: 'neutral', size: 'md' }
)
</script>

<template>
  <span class="badge" :class="[`badge--${tone}`, `badge--${size}`]">
    <slot />
  </span>
</template>

<style scoped>
.badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  border-radius: var(--r-pill);
  font-weight: 600;
  line-height: 1.4;
  white-space: nowrap;
}
.badge--md {
  padding: 3px 12px;
  font-size: var(--fs-sm);
}
.badge--sm {
  padding: 2px 9px;
  font-size: var(--fs-xs);
}

.badge--neutral {
  background: var(--k9);
  color: var(--k3);
}
.badge--success {
  background: var(--successBg);
  color: var(--success);
}
.badge--warn {
  background: var(--warnBg);
  color: var(--warn);
}
.badge--low {
  background: var(--lowBg);
  color: var(--low);
}
.badge--gold {
  background: rgba(155, 126, 70, 0.14);
  color: var(--gold);
}
</style>
