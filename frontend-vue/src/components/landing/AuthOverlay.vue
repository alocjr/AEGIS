<script setup lang="ts">
import { ref, watch, nextTick, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { login, forgotPassword, resetPassword, verifyEmail, resendVerification } from '@/api/auth'
import type { AuthUser } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'
import FormField from '@/components/ui/FormField.vue'
import AppButton from '@/components/ui/AppButton.vue'

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

const viewLead = computed(() => {
  if (view.value === 'forgot') return 'Informe seu email para receber as instruções de recuperação.'
  if (view.value === 'reset') {
    return 'Defina sua nova senha. O token do email já foi preenchido quando você clicou no link.'
  }
  return 'Use o email da sua conta para acessar o programa e os instrumentos do AI Hub.'
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

function stripQueryParam(key: string) {
  if (!route.query[key]) return
  const query = { ...route.query }
  delete query[key]
  router.replace({ path: route.path, query })
}

function stripResetTokenQuery() {
  stripQueryParam('reset_token')
}

function readQueryToken(key: string): string {
  const raw = route.query[key]
  if (typeof raw === 'string') return raw.trim()
  if (Array.isArray(raw) && raw[0]) return raw[0].trim()
  return ''
}

function readResetTokenFromQuery(): string {
  return readQueryToken('reset_token')
}

async function handleVerifyTokenFromQuery() {
  const tokenFromQuery = readQueryToken('verify_token')
  if (!tokenFromQuery) return
  stripQueryParam('verify_token')
  loading.value = true
  clearFeedback()
  try {
    const data = await verifyEmail(tokenFromQuery)
    success.value = data.message
    view.value = 'login'
    if (authStore.user) {
      authStore.setUser({ ...authStore.user, email_verified: true })
    }
  } catch (err: unknown) {
    error.value = err instanceof Error ? err.message : 'Token inválido ou expirado.'
    view.value = 'login'
  } finally {
    loading.value = false
  }
}

function handleOverlayOpen() {
  const tokenFromQuery = readResetTokenFromQuery()
  resetOverlayState()
  if (tokenFromQuery) {
    resetToken.value = tokenFromQuery
    view.value = 'reset'
    stripResetTokenQuery()
    return
  }
  void handleVerifyTokenFromQuery()
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
  if (user.email_verified === false) {
    success.value = 'Confirme seu email para acessar o programa. Verifique sua caixa de entrada.'
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
    if (data.user) {
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

async function submitResendVerification() {
  clearFeedback()
  loading.value = true
  try {
    const data = await resendVerification()
    success.value = data.message
  } catch (err: unknown) {
    error.value = err instanceof Error ? err.message : 'Erro de conexão. Tente novamente.'
  } finally {
    loading.value = false
  }
}

function onClose() {
  emit('close')
}
</script>

<template>
  <section class="auth-panel" :aria-label="dialogAriaLabel">
    <p class="auth-eyebrow">Acesso à plataforma</p>
    <h1 class="auth-title">{{ viewTitle }}</h1>
    <p class="auth-lead">{{ viewLead }}</p>

    <form v-if="view === 'login'" class="auth-form" @submit.prevent="doLogin">
      <FormField label="Email" required>
        <template #default="{ fieldId, describedBy }">
          <input
            :id="fieldId"
            v-model="email"
            type="email"
            class="auth-input"
            autocomplete="email"
            :aria-describedby="describedBy"
          />
        </template>
      </FormField>
      <FormField label="Senha" required>
        <template #default="{ fieldId, describedBy }">
          <input
            :id="fieldId"
            v-model="password"
            type="password"
            class="auth-input"
            autocomplete="current-password"
            :aria-describedby="describedBy"
          />
        </template>
      </FormField>
      <button type="button" class="auth-link" @click="goToForgot">Esqueci minha senha</button>
      <p v-if="error" class="auth-error" role="alert">{{ error }}</p>
      <p v-if="success" class="auth-success">{{ success }}</p>
      <div v-if="authStore.user?.email_verified === false" class="auth-actions">
        <AppButton variant="secondary" :disabled="loading" @click="submitResendVerification">
          {{ loading ? 'Enviando…' : 'Reenviar email de confirmação' }}
        </AppButton>
      </div>
      <div class="auth-submit">
        <AppButton variant="primary" type="submit" :disabled="loading">
          {{ loading ? 'Entrando…' : 'Entrar' }}
        </AppButton>
      </div>
      <button type="button" class="auth-back" @click="onClose">Voltar ao início</button>
    </form>

    <form v-else-if="view === 'forgot'" class="auth-form" @submit.prevent="submitForgot">
      <FormField label="Email" required>
        <template #default="{ fieldId, describedBy }">
          <input
            :id="fieldId"
            v-model="forgotEmail"
            type="email"
            class="auth-input"
            autocomplete="email"
            :aria-describedby="describedBy"
          />
        </template>
      </FormField>
      <p v-if="error" class="auth-error" role="alert">{{ error }}</p>
      <p v-if="success" class="auth-success">{{ success }}</p>
      <div class="auth-submit">
        <AppButton variant="primary" type="submit" :disabled="loading">
          {{ loading ? 'Enviando…' : 'Enviar instruções' }}
        </AppButton>
      </div>
      <div class="auth-nav">
        <button type="button" class="auth-link" @click="goToLogin">Voltar ao login</button>
        <button v-if="success" type="button" class="auth-link" @click="goToReset">Já tenho o token</button>
      </div>
    </form>

    <form v-else class="auth-form" @submit.prevent="submitReset">
      <FormField v-if="!resetToken" label="Token de recuperação" required>
        <template #default="{ fieldId, describedBy }">
          <input
            :id="fieldId"
            v-model="resetToken"
            type="text"
            class="auth-input"
            autocomplete="one-time-code"
            :aria-describedby="describedBy"
          />
        </template>
      </FormField>
      <FormField label="Nova senha" required>
        <template #default="{ fieldId, describedBy }">
          <input
            :id="fieldId"
            v-model="newPassword"
            type="password"
            class="auth-input"
            autocomplete="new-password"
            :aria-describedby="describedBy"
          />
        </template>
      </FormField>
      <FormField label="Confirmar nova senha" required>
        <template #default="{ fieldId, describedBy }">
          <input
            :id="fieldId"
            v-model="confirmPassword"
            type="password"
            class="auth-input"
            autocomplete="new-password"
            :aria-describedby="describedBy"
          />
        </template>
      </FormField>
      <p v-if="error" class="auth-error" role="alert">{{ error }}</p>
      <p v-if="success" class="auth-success">{{ success }}</p>
      <div class="auth-submit">
        <AppButton v-if="!success" variant="primary" type="submit" :disabled="loading">
          {{ loading ? 'Salvando…' : 'Redefinir senha' }}
        </AppButton>
        <AppButton v-else variant="primary" type="button" @click="resetOverlayState">
          Ir para login
        </AppButton>
      </div>
      <div class="auth-nav">
        <button type="button" class="auth-link" @click="goToLogin">Voltar ao login</button>
        <button type="button" class="auth-link" @click="goToForgot">Solicitar novo token</button>
      </div>
    </form>
  </section>
</template>

<style scoped>
.auth-panel {
  width: min(100%, 400px);
}

.auth-eyebrow {
  font-size: var(--fs-xs);
  font-weight: 600;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: var(--gold);
  margin-bottom: 10px;
}

.auth-title {
  font-family: var(--serif);
  font-weight: 400;
  font-size: var(--fs-3xl);
  line-height: 1.15;
  color: var(--k0);
  margin-bottom: 10px;
}

.auth-lead {
  font-size: var(--fs-md);
  color: var(--k3);
  line-height: 1.55;
  margin: 0 0 28px;
}

.auth-form {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.auth-input {
  width: 100%;
  height: 46px;
  padding: 0 14px;
  border: 1px solid var(--bd);
  border-radius: var(--r-sm);
  background: var(--wh);
  font-size: 15px;
  color: var(--k0);
  box-sizing: border-box;
}
.auth-input:focus {
  outline: none;
  border-color: var(--k0);
  box-shadow: 0 0 0 3px rgba(12, 35, 64, 0.08);
}

.auth-error {
  font-size: var(--fs-sm);
  color: var(--low);
  margin: 0;
  line-height: 1.45;
}
.auth-success {
  font-size: var(--fs-sm);
  color: var(--success);
  margin: 0;
  line-height: 1.45;
}

.auth-link {
  display: block;
  width: fit-content;
  margin: -4px 0 0;
  padding: 0;
  border: none;
  background: none;
  color: var(--gold);
  font-size: var(--fs-sm);
  font-weight: 600;
  cursor: pointer;
}
.auth-link:hover {
  color: var(--gold2);
}

.auth-actions {
  display: flex;
}

.auth-submit :deep(.app-btn) {
  width: 100%;
  height: 46px;
}

.auth-nav {
  display: flex;
  flex-wrap: wrap;
  gap: 12px 16px;
}
.auth-nav .auth-link {
  margin: 0;
}

.auth-back {
  margin-top: 4px;
  padding: 0;
  border: none;
  background: none;
  color: var(--k4);
  font-size: var(--fs-sm);
  cursor: pointer;
  width: fit-content;
}
.auth-back:hover {
  color: var(--k0);
}
</style>
