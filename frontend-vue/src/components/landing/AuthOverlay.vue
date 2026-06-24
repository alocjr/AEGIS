<script setup lang="ts">
import { ref, watch, nextTick, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { login, setStoredToken, forgotPassword, resetPassword } from '@/api/auth'
import type { AuthUser } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'

type AuthView = 'login' | 'forgot' | 'reset'

const props = defineProps<{
  show: boolean
}>()

const emit = defineEmits<{
  close: []
}>()

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const view = ref<AuthView>('login')
const email = ref('')
const password = ref('')
const forgotEmail = ref('')
const resetToken = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const error = ref('')
const success = ref('')
const loading = ref(false)

const viewTitle = computed(() => {
  if (view.value === 'forgot') return 'Recuperar senha'
  if (view.value === 'reset') return 'Nova senha'
  return 'Entrar'
})

const dialogAriaLabel = computed(() => viewTitle.value)

function resetOverlayState() {
  view.value = 'login'
  email.value = ''
  password.value = ''
  forgotEmail.value = ''
  resetToken.value = ''
  newPassword.value = ''
  confirmPassword.value = ''
  error.value = ''
  success.value = ''
  loading.value = false
}

function clearFeedback() {
  error.value = ''
  success.value = ''
}

function goToLogin() {
  clearFeedback()
  view.value = 'login'
}

function goToForgot() {
  clearFeedback()
  if (!forgotEmail.value && email.value) {
    forgotEmail.value = email.value.trim()
  }
  view.value = 'forgot'
}

function goToReset() {
  clearFeedback()
  view.value = 'reset'
}

function stripResetTokenQuery() {
  if (!route.query.reset_token) return
  const query = { ...route.query }
  delete query.reset_token
  router.replace({ path: route.path, query })
}

function readResetTokenFromQuery(): string {
  const raw = route.query.reset_token
  if (typeof raw === 'string') return raw.trim()
  if (Array.isArray(raw) && raw[0]) return raw[0].trim()
  return ''
}

function handleOverlayOpen() {
  const tokenFromQuery = readResetTokenFromQuery()
  resetOverlayState()
  if (tokenFromQuery) {
    resetToken.value = tokenFromQuery
    view.value = 'reset'
    stripResetTokenQuery()
  }
}

watch(
  () => props.show,
  (visible) => {
    if (visible) handleOverlayOpen()
  },
  { immediate: true }
)

async function redirectAfterLogin(user: AuthUser) {
  if (user.is_admin) {
    await nextTick()
    try {
      await router.replace('/admin')
    } catch {
      window.location.replace('/admin')
    }
    return
  }
  window.location.replace('/programa')
}

async function doLogin() {
  const e = email.value.trim()
  const p = password.value
  clearFeedback()
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
    }
    error.value = 'Credenciais inválidas.'
  } catch (err: unknown) {
    error.value = err instanceof Error ? err.message : 'Erro de conexão. Tente novamente.'
  } finally {
    loading.value = false
  }
}

async function submitForgot() {
  const e = forgotEmail.value.trim()
  clearFeedback()
  if (!e) {
    error.value = 'Informe seu email.'
    return
  }
  if (!e.includes('@')) {
    error.value = 'Email inválido.'
    return
  }
  loading.value = true
  try {
    const data = await forgotPassword({ email: e })
    success.value = data.message
  } catch (err: unknown) {
    error.value = err instanceof Error ? err.message : 'Erro de conexão. Tente novamente.'
  } finally {
    loading.value = false
  }
}

async function submitReset() {
  const token = resetToken.value.trim()
  const pwd = newPassword.value
  const confirm = confirmPassword.value
  clearFeedback()
  if (!token) {
    error.value = 'Informe o token de recuperação.'
    return
  }
  if (pwd.length < 6) {
    error.value = 'A senha deve ter pelo menos 6 caracteres.'
    return
  }
  if (pwd !== confirm) {
    error.value = 'As senhas não coincidem.'
    return
  }
  loading.value = true
  try {
    const data = await resetPassword({ token, new_password: pwd })
    success.value = data.message
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : 'Erro de conexão. Tente novamente.'
    if (msg.toLowerCase().includes('token')) {
      error.value = 'Token inválido ou expirado.'
    } else {
      error.value = msg
    }
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

function onLoginKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter') doLogin()
}

function onForgotKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter') submitForgot()
}

function onResetKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter') submitReset()
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
    :aria-label="dialogAriaLabel"
    @click="onOverlayClick"
  >
    <div class="auth-card">
      <div class="auth-head">
        <span class="auth-title">{{ viewTitle }}</span>
        <button type="button" class="auth-close" aria-label="Fechar" @click="onClose">×</button>
      </div>

      <!-- login -->
      <template v-if="view === 'login'">
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
          @keydown="onLoginKeydown"
        />
        <button type="button" class="auth-link" @click="goToForgot">Esqueci minha senha</button>
        <div class="auth-error">{{ error }}</div>
        <div>
          <button type="button" class="auth-btn" :disabled="loading" @click="doLogin">
            {{ loading ? 'Entrando…' : 'Entrar' }}
          </button>
          <button type="button" class="auth-btn alt" @click="onClose">Fechar</button>
        </div>
      </template>

      <!-- forgot -->
      <template v-else-if="view === 'forgot'">
        <p class="auth-desc">Informe seu email para receber instruções de recuperação.</p>
        <input
          v-model="forgotEmail"
          type="email"
          class="auth-input"
          placeholder="Email"
          autocomplete="email"
          @keydown="onForgotKeydown"
        />
        <div class="auth-error">{{ error }}</div>
        <div v-if="success" class="auth-success">{{ success }}</div>
        <div class="auth-actions">
          <button type="button" class="auth-btn" :disabled="loading" @click="submitForgot">
            {{ loading ? 'Enviando…' : 'Enviar instruções' }}
          </button>
        </div>
        <div class="auth-nav">
          <button type="button" class="auth-link" @click="goToLogin">Voltar ao login</button>
          <button
            v-if="success"
            type="button"
            class="auth-link"
            @click="goToReset"
          >
            Já tenho o token
          </button>
        </div>
      </template>

      <!-- reset -->
      <template v-else>
        <p class="auth-desc">
          Defina sua nova senha abaixo. O token do email já foi preenchido quando você clicou no link.
        </p>
        <input
          v-if="!resetToken"
          v-model="resetToken"
          type="text"
          class="auth-input"
          placeholder="Token de recuperação"
          autocomplete="one-time-code"
          @keydown="onResetKeydown"
        />
        <input
          v-model="newPassword"
          type="password"
          class="auth-input"
          placeholder="Nova senha"
          autocomplete="new-password"
          @keydown="onResetKeydown"
        />
        <input
          v-model="confirmPassword"
          type="password"
          class="auth-input"
          placeholder="Confirmar nova senha"
          autocomplete="new-password"
          @keydown="onResetKeydown"
        />
        <div class="auth-error">{{ error }}</div>
        <div v-if="success" class="auth-success">{{ success }}</div>
        <div class="auth-actions">
          <button
            v-if="!success"
            type="button"
            class="auth-btn"
            :disabled="loading"
            @click="submitReset"
          >
            {{ loading ? 'Salvando…' : 'Redefinir senha' }}
          </button>
          <button v-else type="button" class="auth-btn" @click="resetOverlayState">
            Ir para login
          </button>
        </div>
        <div class="auth-nav">
          <button type="button" class="auth-link" @click="goToLogin">Voltar ao login</button>
          <button type="button" class="auth-link" @click="goToForgot">Solicitar novo token</button>
        </div>
      </template>
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
.auth-desc {
  font-size: 14px;
  color: var(--k5);
  margin: 0 0 16px;
  line-height: 1.45;
}
.auth-input {
  width: 100%;
  height: 44px;
  padding: 0 14px;
  border: 1px solid var(--bd);
  border-radius: 4px;
  font-size: 15px;
  margin-bottom: 12px;
  box-sizing: border-box;
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
.auth-success {
  font-size: 13px;
  color: #1f5c3a;
  margin-bottom: 12px;
  line-height: 1.45;
}
.auth-hint {
  font-size: 12px;
  color: var(--k5);
  background: var(--k8, #f5f5f5);
  border: 1px dashed var(--bd);
  border-radius: 4px;
  padding: 10px 12px;
  margin-bottom: 12px;
  line-height: 1.4;
}
.auth-hint-label {
  display: block;
  margin-bottom: 6px;
  font-weight: 600;
}
.auth-hint-token {
  display: block;
  word-break: break-all;
  font-size: 11px;
  margin-bottom: 6px;
}
.auth-hint-copy {
  display: block;
  font-size: 11px;
  color: #1f5c3a;
  margin-top: 4px;
}
.auth-link {
  display: block;
  width: fit-content;
  margin: 0 0 12px;
  padding: 0;
  border: none;
  background: none;
  color: var(--k0);
  font-size: 13px;
  text-decoration: underline;
  cursor: pointer;
}
.auth-link.inline {
  display: inline;
  margin: 0 0 0 8px;
}
.auth-link:hover {
  opacity: 0.85;
}
.auth-actions {
  margin-bottom: 8px;
}
.auth-nav {
  display: flex;
  flex-wrap: wrap;
  gap: 12px 16px;
  margin-top: 4px;
}
.auth-nav .auth-link {
  margin: 0;
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
  cursor: pointer;
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
