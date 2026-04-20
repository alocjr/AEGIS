<script setup lang="ts">
import { RouterLink } from 'vue-router'
import { LOGO_URL } from '@/constants/assets'

defineEmits<{
  openAbout: []
  openLogin: []
}>()
</script>

<template>
  <header class="topbar">
    <RouterLink to="/" class="tb-brand">
      <img :src="LOGO_URL" alt="Valorian 4 Future" />
      <span class="tb-sub">Formação Executiva</span>
    </RouterLink>
    <div class="tb-right">
      <button type="button" class="tb-pill" @click="$emit('openAbout')">Sobre nós</button>
      <button type="button" class="tb-pill tb-pill-g" @click="$emit('openLogin')">Entrar</button>
    </div>
  </header>
</template>

<style scoped>
.topbar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: var(--bar-h);
  background: var(--k0);
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  display: flex;
  align-items: center;
  padding: 0 28px;
  z-index: 400;
}
.tb-brand {
  display: flex;
  align-items: center;
  gap: 14px;
  color: var(--wh);
  text-decoration: none;
}
.tb-brand img {
  height: 52px;
  width: auto;
  display: block;
  object-fit: contain;
}
.tb-sub {
  font-size: 12px;
  font-weight: 300;
  letter-spacing: 0.15em;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.5);
}
.tb-right {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 8px;
}
.tb-pill {
  height: 36px;
  padding: 0 16px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 4px;
  font-size: 13px;
  letter-spacing: 0.05em;
  color: rgba(255, 255, 255, 0.9);
  background: transparent;
  display: inline-flex;
  align-items: center;
  transition: background 0.2s, border-color 0.2s;
}
.tb-pill:hover {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(255, 255, 255, 0.35);
}
.tb-pill-g {
  color: var(--gold2);
  border-color: rgba(155, 126, 70, 0.4);
}
.tb-pill-g:hover {
  background: rgba(155, 126, 70, 0.15);
  border-color: var(--gold2);
}
</style>
