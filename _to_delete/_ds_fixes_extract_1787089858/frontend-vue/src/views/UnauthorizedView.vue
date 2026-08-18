<script setup lang="ts">
import { UNAUTHORIZED_IMAGE_URL } from '@/constants/assets'
</script>

<template>
  <div class="unauthorized">
    <img
      :src="UNAUTHORIZED_IMAGE_URL"
      alt="Erro HTTP 401 — Acesso não autorizado"
      class="unauthorized-img"
    />
    <nav class="unauthorized-actions" aria-label="Ações">
      <RouterLink to="/login" class="btn btn-primary">Entrar</RouterLink>
      <RouterLink to="/" class="btn btn-ghost">Voltar ao início</RouterLink>
    </nav>
  </div>
</template>

<style scoped>
.unauthorized {
  min-height: 100vh;
  background: #0c1827;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}
.unauthorized-img {
  display: block;
  width: 100%;
  max-height: calc(100vh - 88px);
  object-fit: contain;
}
.unauthorized-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
  flex-wrap: wrap;
  padding: 20px 16px 28px;
}
.btn {
  display: inline-block;
  padding: 10px 20px;
  border-radius: var(--r-sm);
  font-size: 14px;
  font-weight: 600;
  text-decoration: none;
}
.btn-primary {
  background: #9b7e46;
  color: #fff;
}
.btn-primary:hover {
  background: #b8975a;
}
.btn-ghost {
  background: transparent;
  color: #e2e2e7;
  border: 1px solid rgba(226, 226, 231, 0.35);
}
.btn-ghost:hover {
  border-color: #e2e2e7;
}
</style>
