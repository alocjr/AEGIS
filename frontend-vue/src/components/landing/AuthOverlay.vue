<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { login, setStoredToken } from '@/api/auth'
import type { AuthUser } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'

const props = defineProps<{
  show: boolean
}>()

const emit = defineEmits<{
  close: []
}>()

const router = useRouter()
const authStore = useAuthStore()
const email = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

watch(
  () => props.show,
  (visible) => {
    if (visible) {
      error.value = ''
      email.value = ''
      password.value = ''
    }
  }
)

async function redirectAfterLogin(user: AuthUser) {
  // Aluno → programa (com reload para garantir token e rota); Admin → dashboard
  if (user.is_admin) {
    await nextTick()
    try {
      await router.replace('/admin')
    } catch {
      window.location.replace('/admin')
    }
    return
  }
  // Redirecionamento com reload garante que a app carrega já em /programa com token no localStorage
  window.location.replace('/programa')
}

async function doLogin() {
  const e = email.value.trim()
  const p = password.value
  error.value = ''
  if (!e || !p) {
    error.value = 'Preencha email e senha.'
    return
  }
  loading.value = true
  try {
    const data = await login({ email: e, password: p })
    if (data.access_token && data.user) {
      setStoredToken(data.access_token)
      authStore.setUser(data.user)
      await redirectAfterLogin(data.user)
      return
    } else {
      error.value = 'Credenciais inválidas.'
    }
  } catch (err: unknown) {
    error.value = err instanceof Error ? err.message : 'Erro de conexão. Tente novamente.'
  } finally {
    loading.value = false
  }
}

function onClose() {
  emit('close')
}

function onOverlayClick(e: MouseEvent) {
  if ((e.target as HTMLElement).id === 'auth-overlay') onClose()
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter') doLogin()
}
</script>

<template>
  <div
    id="auth-overlay"
    class="auth-overlay"
    :class="{ show: show }"
    v-show="show"
    role="dialog"
    aria-modal="true"
    aria-label="Entrar"
    @click="onOverlayClick"
  >
    <div class="auth-card">
      <div class="auth-head">
        <span class="auth-title">Entrar</span>
        <button type="button" class="auth-close" aria-label="Fechar" @click="onClose">×</button>
      </div>
      <input
        v-model="email"
        type="email"
        class="auth-input"
        placeholder="Email"
        autocomplete="email"
      />
      <input
        v-model="password"
        type="password"
        class="auth-input"
        placeholder="Senha"
        autocomplete="current-password"
        @keydown="onKeydown"
      />
      <div class="auth-error">{{ error }}</div>
      <div>
        <button type="button" class="auth-btn" :disabled="loading" @click="doLogin">
          {{ loading ? 'Entrando…' : 'Entrar' }}
        </button>
        <button type="button" class="auth-btn alt" @click="onClose">Fechar</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.auth-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: none;
  align-items: center;
  justify-content: center;
  z-index: 999;
}
.auth-overlay.show {
  display: flex;
}
.auth-card {
  width: min(92vw, 420px);
  background: var(--wh);
  border: 1px solid var(--bd);
  border-radius: 8px;
  padding: 28px;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.15);
}
.auth-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.auth-title {
  font-family: var(--serif);
  font-size: 22px;
  color: var(--k0);
}
.auth-close {
  width: 32px;
  height: 32px;
  border: none;
  background: transparent;
  color: var(--k5);
  font-size: 20px;
  cursor: pointer;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.auth-close:hover {
  background: var(--k8);
  color: var(--k0);
}
.auth-input {
  width: 100%;
  height: 44px;
  padding: 0 14px;
  border: 1px solid var(--bd);
  border-radius: 4px;
  font-size: 15px;
  margin-bottom: 12px;
}
.auth-input:focus {
  outline: none;
  border-color: var(--k0);
}
.auth-error {
  font-size: 13px;
  color: #8f2b2b;
  min-height: 20px;
  margin-bottom: 8px;
}
.auth-btn {
  height: 44px;
  padding: 0 20px;
  border: 1px solid var(--k0);
  background: var(--k0);
  color: var(--wh);
  font-size: 14px;
  font-weight: 600;
  border-radius: 4px;
}
.auth-btn:hover:not(:disabled) {
  opacity: 0.92;
}
.auth-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}
.auth-btn.alt {
  background: transparent;
  color: var(--k0);
  margin-left: 8px;
}
</style>
