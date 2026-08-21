<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch, nextTick } from 'vue'

/**
 * AR-01: consolida os 6 modais implementados à mão na base (cada um com seu
 * próprio backdrop, trap de foco ausente e handling de Escape inconsistente
 * — 2 dos 6 nem fechavam com Escape). Também resolve UX-03 do audit original
 * (foco perdido ao abrir/fechar modal, sem aria-modal).
 */
const props = withDefaults(
  defineProps<{
    open: boolean
    title?: string | null
    /** Fecha ao clicar no backdrop. Default true. */
    closeOnBackdrop?: boolean
    size?: 'sm' | 'md' | 'lg'
  }>(),
  { title: null, closeOnBackdrop: true, size: 'md' }
)

const emit = defineEmits<{ close: [] }>()

const dialogRef = ref<HTMLElement | null>(null)
let lastFocused: HTMLElement | null = null

function focusableEls(): HTMLElement[] {
  if (!dialogRef.value) return []
  return Array.from(
    dialogRef.value.querySelectorAll<HTMLElement>(
      'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])'
    )
  )
}

function onKeydown(e: KeyboardEvent) {
  if (!props.open) return
  if (e.key === 'Escape') {
    e.stopPropagation()
    emit('close')
    return
  }
  if (e.key === 'Tab') {
    const els = focusableEls()
    if (els.length === 0) return
    const first = els[0]
    const last = els[els.length - 1]
    if (!first || !last) return
    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault()
      last.focus()
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault()
      first.focus()
    }
  }
}

watch(
  () => props.open,
  async (isOpen) => {
    if (isOpen) {
      lastFocused = document.activeElement as HTMLElement | null
      document.body.style.overflow = 'hidden'
      await nextTick()
      const els = focusableEls()
      ;(els[0] ?? dialogRef.value)?.focus()
    } else {
      document.body.style.overflow = ''
      lastFocused?.focus()
    }
  }
)

onMounted(() => window.addEventListener('keydown', onKeydown, true))
onUnmounted(() => {
  window.removeEventListener('keydown', onKeydown, true)
  if (props.open) document.body.style.overflow = ''
})
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="app-modal__backdrop" @mousedown.self="closeOnBackdrop && emit('close')">
      <div
        ref="dialogRef"
        class="app-modal"
        :class="`app-modal--${size}`"
        role="dialog"
        aria-modal="true"
        :aria-label="title ?? undefined"
        tabindex="-1"
      >
        <header v-if="title || $slots.header" class="app-modal__header">
          <slot name="header">
            <h2 class="app-modal__title">{{ title }}</h2>
          </slot>
          <button type="button" class="app-modal__close" aria-label="Fechar" @click="emit('close')">✕</button>
        </header>
        <div class="app-modal__body">
          <slot />
        </div>
        <footer v-if="$slots.footer" class="app-modal__footer">
          <slot name="footer" />
        </footer>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.app-modal__backdrop {
  position: fixed;
  inset: 0;
  background: rgba(12, 24, 39, 0.55);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  z-index: 1000;
}
.app-modal {
  background: var(--wh);
  border-radius: var(--r-lg);
  box-shadow: var(--shadow-3);
  width: 100%;
  max-height: calc(100vh - 48px);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.app-modal--sm {
  max-width: 420px;
}
.app-modal--md {
  max-width: 620px;
}
.app-modal--lg {
  max-width: 880px;
}
.app-modal__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 20px 24px;
  border-bottom: 1px solid var(--bd);
  flex-shrink: 0;
}
.app-modal__title {
  font-family: var(--serif);
  font-size: var(--fs-xl);
  font-weight: 400;
  color: var(--k0);
}
.app-modal__close {
  background: transparent;
  border: none;
  cursor: pointer;
  color: var(--k4);
  font-size: var(--fs-md);
  line-height: 1;
  padding: 6px;
  border-radius: var(--r-sm);
  flex-shrink: 0;
}
.app-modal__close:hover {
  background: var(--k9);
  color: var(--k1);
}
.app-modal__close:focus-visible {
  outline: 2px solid var(--gold);
  outline-offset: 2px;
}
.app-modal__body {
  padding: 24px;
  overflow-y: auto;
}
.app-modal__footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  padding: 16px 24px;
  border-top: 1px solid var(--bd);
  flex-shrink: 0;
}
</style>
