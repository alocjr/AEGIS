<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { fetchDashboard } from '@/api/admin'
import type { DashboardStudent } from '@/api/admin'

const loading = ref(true)
const error = ref<string | null>(null)
const students = ref<DashboardStudent[]>([])

function pct(done: number, total: number): number {
  if (total <= 0) return 0
  return Math.min(100, Math.round((done / total) * 100))
}

function formatNext(iso: string): string {
  try {
    const d = new Date(iso)
    return d.toLocaleDateString('pt-BR', {
      weekday: 'short',
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return iso
  }
}

/** Número só com dígitos para wa.me (ex.: 5511987654321) */
function phoneDigits(phone: string): string {
  return (phone || '').replace(/\D/g, '')
}

function whatsAppUrl(phone: string): string | null {
  const digits = phoneDigits(phone)
  if (!digits.length) return null
  return `https://wa.me/${digits}`
}

/** Formata para exibição: código do país espaço (DDD) número com hífen. Ex.: 55 (11) 98765-4321 */
function formatPhoneDisplay(phone: string): string {
  const digits = phoneDigits(phone)
  if (digits.length < 8) return phone || ''
  const country = digits.length >= 12 ? digits.slice(0, 2) : ''
  const dddStart = country ? 2 : 0
  const ddd = digits.slice(dddStart, dddStart + 2)
  const rest = digits.slice(dddStart + 2)
  const prefix = country ? `${country} ` : ''
  if (rest.length === 8) return `${prefix}(${ddd}) ${rest.slice(0, 4)}-${rest.slice(4)}`
  if (rest.length >= 9) return `${prefix}(${ddd}) ${rest.slice(0, 5)}-${rest.slice(5, 9)}`
  return `${prefix}(${ddd}) ${rest}`
}

onMounted(async () => {
  try {
    students.value = await fetchDashboard()
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Erro ao carregar dashboard.'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="dashboard">
    <h1 class="dashboard-title">Dashboard</h1>
    <p class="dashboard-sub">Alunos e progresso por trilha</p>

    <div v-if="loading" class="loading">Carregando...</div>
    <div v-else-if="error" class="error-msg">{{ error }}</div>
    <div v-else-if="students.length === 0" class="empty">Nenhum aluno cadastrado.</div>

    <div v-else class="card-grid">
      <article
        v-for="s in students"
        :key="s.id"
        class="student-card"
        role="button"
        tabindex="0"
        @click="$router.push(`/admin/progresso/${s.id}`)"
        @keydown.enter="$router.push(`/admin/progresso/${s.id}`)"
      >
        <div class="card-header">
          <div class="card-header-inner">
            <h2 class="card-name">{{ s.name }}</h2>
            <span class="card-trilha">{{ s.course_titulo || s.course_slug || '—' }}</span>
          </div>
          <div class="card-contacts">
            <a :href="`mailto:${s.email}`" class="card-email" @click.stop title="Enviar e-mail">{{ s.email }}</a>
            <a
              v-if="whatsAppUrl(s.phone)"
              :href="whatsAppUrl(s.phone)!"
              target="_blank"
              rel="noopener"
              class="card-phone"
              title="Abrir WhatsApp"
            >
              {{ formatPhoneDisplay(s.phone) }}
            </a>
          </div>
        </div>

        <div class="card-progress">
          <div class="progress-row">
            <span class="progress-label">Encontros</span>
            <div class="progress-bar-wrap">
              <div
                class="progress-bar-fill"
                :style="{ width: pct(s.encontros_done, s.encontros_total) + '%' }"
              />
            </div>
            <span class="progress-pct">{{ s.encontros_done }}/{{ s.encontros_total }}</span>
          </div>
          <div class="progress-row">
            <span class="progress-label">Quiz</span>
            <div class="progress-bar-wrap">
              <div
                class="progress-bar-fill progress-bar-quiz"
                :style="{ width: pct(s.quiz_done, s.quiz_total) + '%' }"
              />
            </div>
            <span class="progress-pct">{{ s.quiz_done }}/{{ s.quiz_total }}</span>
          </div>
          <div class="progress-row">
            <span class="progress-label">Modelo de Maturidade</span>
            <div class="progress-bar-wrap">
              <div
                class="progress-bar-fill progress-bar-maturity"
                :style="{ width: pct(s.maturity_done, s.maturity_total) + '%' }"
              />
            </div>
            <span class="progress-pct">{{ s.maturity_done }}/{{ s.maturity_total }}</span>
          </div>
        </div>

        <div v-if="s.next_meeting_iso" class="card-next">
          <span class="card-next-label">Próximo encontro</span>
          <span class="card-next-date">{{ formatNext(s.next_meeting_iso) }}</span>
        </div>
        <div class="card-cta">
          <span>Ver detalhes</span>
          <span class="card-cta-arrow">→</span>
        </div>
      </article>
    </div>
  </div>
</template>

<style scoped>
.dashboard {
  max-width: 1200px;
  margin: 0 auto;
}
.dashboard-title {
  font-family: var(--serif);
  font-size: 28px;
  color: var(--k0);
  margin-bottom: 4px;
}
.dashboard-sub {
  font-size: 14px;
  color: var(--k5);
  margin-bottom: 24px;
}
.loading,
.error-msg,
.empty {
  padding: 40px 0;
  color: var(--k5);
}
.error-msg {
  color: #8f2b2b;
}

.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 24px;
}

.student-card {
  background: var(--wh);
  border: 1px solid var(--bd);
  border-radius: 12px;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0;
  overflow: hidden;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
  box-shadow: 0 1px 3px rgba(12, 35, 64, 0.04);
}

.student-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(12, 35, 64, 0.1), 0 2px 6px rgba(12, 35, 64, 0.06);
  border-color: var(--goldbd);
}

.student-card:focus {
  outline: none;
}

.student-card:focus-visible {
  box-shadow: 0 0 0 2px var(--wh), 0 0 0 4px var(--gold);
}

.card-header {
  background: linear-gradient(145deg, var(--k0) 0%, #132d52 100%);
  padding: 20px 22px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.card-header-inner {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.card-name {
  font-family: var(--serif);
  font-size: 19px;
  font-weight: 600;
  color: var(--wh);
  margin: 0;
  letter-spacing: -0.02em;
  line-height: 1.3;
}

.card-trilha {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--gold2);
  opacity: 0.95;
}

.card-contacts {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.card-email,
.card-phone {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.88);
  text-decoration: none;
  display: block;
  transition: color 0.15s ease;
}

.card-email:hover {
  color: var(--gold2);
}

.card-phone:hover {
  color: #25d366;
}

.card-progress {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 22px;
  background: var(--wh);
}

.progress-row {
  display: grid;
  grid-template-columns: 140px 1fr 52px;
  align-items: center;
  gap: 12px;
}

.progress-label {
  font-size: 12px;
  font-weight: 500;
  color: var(--k4);
}

.progress-bar-wrap {
  height: 10px;
  background: var(--k8);
  border-radius: 6px;
  overflow: hidden;
}

.progress-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--k0), #1a3a5c);
  border-radius: 6px;
  transition: width 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.progress-bar-quiz {
  background: linear-gradient(90deg, var(--gold), var(--gold2));
}

.progress-bar-maturity {
  background: linear-gradient(90deg, #2d6a4f, #40916c);
}

.progress-pct {
  font-size: 12px;
  font-weight: 600;
  color: var(--k4);
  text-align: right;
  min-width: 2.5em;
}

.card-next {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 14px 22px;
  background: var(--k9);
  border-top: 1px solid var(--bd2);
  font-size: 12px;
}

.card-next-label {
  font-weight: 600;
  color: var(--k4);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.card-next-date {
  color: var(--k3);
  font-size: 13px;
}

.card-cta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 22px;
  font-size: 13px;
  font-weight: 500;
  color: var(--gold);
  border-top: 1px solid var(--bd2);
  transition: background 0.15s ease, color 0.15s ease;
}

.student-card:hover .card-cta {
  background: var(--golddim);
  color: var(--k0);
}

.card-cta-arrow {
  opacity: 0.7;
  transition: transform 0.2s ease;
}

.student-card:hover .card-cta-arrow {
  transform: translateX(4px);
}
</style>
