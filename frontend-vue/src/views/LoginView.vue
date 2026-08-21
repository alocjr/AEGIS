<script setup lang="ts">
import { useRouter, RouterLink } from 'vue-router'
import AuthOverlay from '@/components/landing/AuthOverlay.vue'

const router = useRouter()

const HUB_SHOTS = [
  { src: '/assets/hub-maturity.jpg', label: 'Maturidade' },
  { src: '/assets/hub-swot.jpg', label: 'SWOT' },
  { src: '/assets/hub-canvas.jpg', label: 'Canvas' },
  { src: '/assets/hub-mapa.jpg', label: 'Mapa estratégico' },
] as const

function onClose() {
  router.replace('/')
}
</script>

<template>
  <div class="login-page">
    <aside class="login-brand">
      <RouterLink to="/" class="login-brand__home">← Início</RouterLink>

      <div class="login-brand__hero">
        <img
          class="login-brand__logo"
          src="/assets/valorian-logo.jpg"
          alt="Valorian 4 Future — AI Executive Mentoring"
          width="1550"
          height="1439"
        />
        <p class="login-brand__eyebrow">AI Executive Mentoring</p>
        <h1 class="login-brand__title">Mentoria executiva para liderar com inteligência artificial.</h1>
        <p class="login-brand__lead">
          Entre para acessar o programa, os instrumentos do AI Hub e o mapa da sua jornada.
        </p>
      </div>

      <ul class="login-mosaic" aria-hidden="true">
        <li v-for="shot in HUB_SHOTS" :key="shot.src">
          <figure>
            <img :src="shot.src" :alt="shot.label" />
            <figcaption>{{ shot.label }}</figcaption>
          </figure>
        </li>
      </ul>

      <p class="login-brand__tools">Maturidade · SWOT · Canvas · OKR · Governança</p>
    </aside>

    <main class="login-panel">
      <AuthOverlay :show="true" @close="onClose" />
    </main>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  min-height: 100dvh;
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(360px, 0.85fr);
  background: var(--navy-deep);
}

.login-brand {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 28px;
  padding: 32px 48px 40px;
  overflow: hidden;
  color: var(--wh);
  border-right: 1px solid rgba(155, 126, 70, 0.28);
  background:
    radial-gradient(ellipse at 20% 0%, rgba(155, 126, 70, 0.16) 0%, transparent 52%),
    radial-gradient(ellipse at 90% 100%, rgba(155, 126, 70, 0.1) 0%, transparent 46%),
    var(--navy-deep);
}

.login-brand::before {
  content: '';
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(184, 150, 46, 0.07) 1px, transparent 1px),
    linear-gradient(90deg, rgba(184, 150, 46, 0.07) 1px, transparent 1px);
  background-size: 44px 44px;
  mask-image: radial-gradient(ellipse at 40% 28%, #000 18%, transparent 72%);
  pointer-events: none;
}

.login-brand__home {
  position: relative;
  z-index: 1;
  width: fit-content;
  font-size: var(--fs-sm);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: rgba(244, 241, 235, 0.62);
  transition: color 0.15s;
}
.login-brand__home:hover {
  color: var(--gold2);
}

.login-brand__hero {
  position: relative;
  z-index: 1;
  max-width: 520px;
}

.login-brand__logo {
  display: block;
  width: min(220px, 58%);
  height: auto;
  margin: 0 0 28px -12px;
  filter: drop-shadow(0 16px 40px rgba(155, 126, 70, 0.28));
}

.login-brand__eyebrow {
  font-size: var(--fs-xs);
  font-weight: 600;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: var(--gold2);
  margin-bottom: 12px;
}

.login-brand__title {
  font-family: var(--serif);
  font-weight: 400;
  font-size: clamp(28px, 3.4vw, 42px);
  line-height: 1.15;
  color: #f4f1eb;
  margin-bottom: 14px;
}

.login-brand__lead {
  font-size: var(--fs-md);
  line-height: 1.6;
  color: rgba(244, 241, 235, 0.68);
  max-width: 42ch;
}

.login-mosaic {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  list-style: none;
  margin-top: auto;
}

.login-mosaic figure {
  position: relative;
  margin: 0;
  overflow: hidden;
  aspect-ratio: 16 / 10;
  border-radius: var(--r-sm);
  border: 1px solid rgba(184, 150, 46, 0.28);
  background: #0a1420;
}

.login-mosaic img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: top left;
  display: block;
  filter: saturate(0.88) contrast(1.02);
  transform: scale(1.01);
  transition: transform 0.45s ease;
}

.login-mosaic figure:hover img {
  transform: scale(1.06);
}

.login-mosaic figcaption {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  padding: 22px 10px 8px;
  background: linear-gradient(transparent, rgba(12, 24, 39, 0.88));
  color: var(--gold2);
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.login-brand__tools {
  position: relative;
  z-index: 1;
  font-size: var(--fs-xs);
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: rgba(244, 241, 235, 0.42);
}

.login-panel {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 48px 40px;
  background: var(--bg);
}

@media (max-width: 960px) {
  .login-page {
    grid-template-columns: 1fr;
  }

  .login-brand {
    padding: 24px 24px 28px;
    border-right: none;
    border-bottom: 1px solid rgba(155, 126, 70, 0.28);
    gap: 18px;
  }

  .login-brand__logo {
    width: 140px;
    margin: 0 0 16px -8px;
  }

  .login-brand__title {
    font-size: 26px;
  }

  .login-brand__lead {
    max-width: none;
  }

  .login-mosaic,
  .login-brand__tools {
    display: none;
  }

  .login-panel {
    align-items: flex-start;
    padding: 32px 22px 48px;
    min-height: auto;
  }
}
</style>
