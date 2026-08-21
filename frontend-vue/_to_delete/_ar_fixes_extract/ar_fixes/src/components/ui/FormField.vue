<script setup lang="ts">
/**
 * AR-01: label + controle + mensagem de ajuda/erro, hoje remontado à mão em
 * cada formulário (label solto sem `for`/`id` associado em vários pontos —
 * problema de acessibilidade além de duplicação). O id é gerado aqui e
 * exposto via slot para o input do consumidor se ligar com :id="fieldId".
 */
import { computed, useId } from 'vue'

const props = withDefaults(
  defineProps<{
    label: string
    hint?: string | null
    error?: string | null
    required?: boolean
  }>(),
  { hint: null, error: null, required: false }
)

const fieldId = `field-${useId()}`
const hintId = computed(() => (props.hint ? `${fieldId}-hint` : undefined))
const errorId = computed(() => (props.error ? `${fieldId}-error` : undefined))
const describedBy = computed(() => [hintId.value, errorId.value].filter(Boolean).join(' ') || undefined)
</script>

<template>
  <div class="form-field" :class="{ 'form-field--error': !!error }">
    <label :for="fieldId" class="form-field__label">
      {{ label }}
      <span v-if="required" class="form-field__required" aria-hidden="true">*</span>
    </label>
    <slot :field-id="fieldId" :described-by="describedBy" />
    <p v-if="error" :id="errorId" class="form-field__error" role="alert">{{ error }}</p>
    <p v-else-if="hint" :id="hintId" class="form-field__hint">{{ hint }}</p>
  </div>
</template>

<style scoped>
.form-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.form-field__label {
  font-size: var(--fs-sm);
  font-weight: 600;
  color: var(--k2);
}
.form-field__required {
  color: var(--low);
}
.form-field__hint {
  font-size: var(--fs-xs);
  color: var(--k4);
}
.form-field__error {
  font-size: var(--fs-xs);
  color: var(--low);
  font-weight: 600;
}
.form-field--error :deep(input),
.form-field--error :deep(textarea),
.form-field--error :deep(select) {
  border-color: var(--low) !important;
}
</style>
