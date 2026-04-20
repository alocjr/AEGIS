<script setup lang="ts">
import { LOGO_URL } from '@/constants/assets'

defineProps<{
  show: boolean
}>()

defineEmits<{
  close: []
}>()
</script>

<template>
  <div
    class="brand-story-overlay"
    :class="{ open: show }"
    role="dialog"
    aria-modal="true"
    aria-label="Nossa história"
    @click.self="$emit('close')"
  >
    <div class="brand-story-card" @click.stop>
      <img :src="LOGO_URL" alt="Valorian 4 Future" class="brand-story-logo" />
      <div class="brand-story-title">Nossa história</div>
      <div class="brand-story-text">
        <p>
          A <strong>Valorian 4 Future</strong> nasceu da crença de que a inteligência artificial pode e deve ser uma alavanca para o desenvolvimento de líderes e organizações. Unimos mentoria executiva de alto nível à aplicação estratégica de IA, preparando profissionais para decisões mais rápidas, dados mais claros e visão de futuro.
        </p>
        <p>
          Nosso programa <em>AI Executive Training</em> foi desenhado para quem quer liderar com impacto: entender onde a IA gera valor, como integrar ferramentas ao dia a dia e como construir uma cultura orientada a resultados e inovação.
        </p>
        <p>
          Valorian 4 Future é mais do que treinamento — é a ponte entre o hoje e o amanhã que sua carreira e sua empresa precisam.
        </p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.brand-story-overlay {
  display: none;
  position: fixed;
  inset: 0;
  z-index: 1000;
  background: rgba(12, 35, 64, 0.96);
  align-items: center;
  justify-content: center;
  padding: 40px;
  box-sizing: border-box;
  cursor: pointer;
}
.brand-story-overlay.open {
  display: flex;
}
.brand-story-card {
  cursor: default;
  background: #fff;
  max-width: 720px;
  width: 100%;
  max-height: 90vh;
  overflow-y: auto;
  padding: 48px 56px;
  border-radius: 4px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.4);
  text-align: center;
}
.brand-story-logo {
  width: 100%;
  max-width: 380px;
  height: auto;
  margin: 0 auto 32px;
  display: block;
}
.brand-story-title {
  font-family: var(--serif);
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: var(--k5);
  margin-bottom: 20px;
}
.brand-story-text {
  font-size: 17px;
  line-height: 1.75;
  color: var(--k0);
  text-align: left;
}
.brand-story-text p {
  margin-bottom: 1em;
}
.brand-story-text p:last-child {
  margin-bottom: 0;
}
</style>
