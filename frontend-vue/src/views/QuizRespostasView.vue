<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { fetchQuizList } from '@/api/quiz'
import type { QuizListItem } from '@/api/quiz'

const loading = ref(true)
const error = ref<string | null>(null)
const list = ref<QuizListItem[]>([])
const ativo = ref<number>(999)

onMounted(async () => {
  try {
    const data = await fetchQuizList()
    list.value = data.items ?? []
    ativo.value = data.ativo != null ? data.ativo : 999
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Erro ao carregar quiz.'
  } finally {
    loading.value = false
  }
})

function liberado(item: QuizListItem): boolean {
  return item.encontro <= ativo.value
}

function scoreLevel(pct: number | null): 'high' | 'mid' | 'low' | 'none' {
  if (pct == null) return 'none'
  if (pct >= 80) return 'high'
  if (pct >= 50) return 'mid'
  return 'low'
}

function pctForItem(item: QuizListItem): number | null {
  const answered = item.total_answered ?? item.total ?? 0
  if (answered === 0 || item.score == null) return null
  return Math.round((item.score / answered) * 100)
}

/** Percentual de perguntas respondidas em relação ao total (para a barra à esquerda do Abrir). */
function progressAnsweredForItem(item: QuizListItem): number {
  const total = item.total ?? 0
  if (total <= 0) return 0
  const answered = item.total_answered ?? 0
  return Math.min(100, Math.round((answered / total) * 100))
}

const dashboard = computed(() => {
  const items = list.value
  const total = items.length
  const responded = items.filter((i) => i.submitted_at != null).length
  let sumScore = 0
  let sumAnswered = 0
  items.forEach((i) => {
    const answered = i.total_answered ?? i.total ?? 0
    if (i.score != null && answered > 0) {
      sumScore += i.score
      sumAnswered += answered
    }
  })
  const avgPct = sumAnswered > 0 ? Math.round((sumScore / sumAnswered) * 100) : 0
  const pctResponded = total > 0 ? Math.round((responded / total) * 100) : 0
  return {
    total,
    responded,
    avgPct,
    sumScore,
    sumAnswered,
    pctResponded,
  }
})

function formatDate(iso: string | null): string {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString('pt-BR', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function ringStrokeOffset(pct: number | null): number {
  const r = 30
  const c = 2 * Math.PI * r
  return pct != null ? c - (pct / 100) * c : c
}
</script>

<template>
  <div class="wrap">
    <header class="page-header">
      <h1>Desempenho nos Quizzes</h1>
      <p class="muted">
        Acompanhe suas respostas por encontro. Clique em &ldquo;Abrir&rdquo; para responder ou rever.
      </p>
    </header>

    <div v-if="loading" class="loading">Carregando...</div>

    <template v-else-if="error">
      <div class="error-msg">{{ error }}</div>
    </template>

    <div v-else-if="list.length === 0" class="empty-wrap">
      <div class="empty">Nenhum quiz disponível para este programa.</div>
    </div>

    <div v-else class="dashboard-wrap">
      <div class="dashboard">
        <div class="kpi-card primary">
          <div class="kpi-label">Total de quizzes</div>
          <div class="kpi-value">{{ dashboard.total }}</div>
          <div class="kpi-sub">encontros com quiz</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">Respondidos</div>
          <div class="kpi-value">{{ dashboard.responded }}</div>
          <div class="kpi-sub">de {{ dashboard.total }}</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">Média de acertos</div>
          <div
            class="kpi-value"
            :class="{
              success: dashboard.avgPct >= 80,
              gold: dashboard.avgPct >= 50 && dashboard.avgPct < 80,
            }"
          >
            {{ dashboard.sumTotal > 0 ? dashboard.avgPct + '%' : '—' }}
          </div>
          <div class="kpi-sub">
            {{ dashboard.sumAnswered > 0 ? dashboard.sumScore + '/' + dashboard.sumAnswered + ' questões' : '' }}
          </div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">Conclusão</div>
          <div class="kpi-value gold">{{ dashboard.pctResponded }}%</div>
          <div class="kpi-sub">quizzes realizados</div>
        </div>
      </div>

      <div class="overall-bar-wrap">
        <div class="sec-title">Progresso geral</div>
        <div class="overall-bar-track">
          <div
            class="overall-bar-fill"
            :style="{ width: dashboard.pctResponded + '%' }"
          ></div>
        </div>
        <div class="overall-bar-legend">
          <span>{{ dashboard.responded }} respondidos</span>
          <span>{{ dashboard.total }} quizzes</span>
        </div>
      </div>

      <div class="list-section">
        <div class="sec-title">Por encontro</div>
        <div class="quiz-cards">
          <template v-for="item in list" :key="item.encontro">
            <RouterLink
              v-if="liberado(item)"
              :to="item.quiz_id ? `/quiz/q/${item.quiz_id}` : `/quiz/${item.encontro}`"
              class="quiz-card-link"
            >
              <div
                class="quiz-card"
                :class="{
                  pending: !item.submitted_at,
                  locked: !liberado(item),
                }"
              >
                <div class="quiz-score-wrap">
                  <div class="quiz-score-ring">
                    <svg viewBox="0 0 72 72" class="ring-svg">
                      <circle class="bg" cx="36" cy="36" r="30" />
                      <circle
                        class="fill"
                        :class="scoreLevel(pctForItem(item))"
                        cx="36"
                        cy="36"
                        r="30"
                        fill="none"
                        stroke-width="6"
                        stroke-linecap="round"
                        :stroke-dasharray="2 * Math.PI * 30"
                        :stroke-dashoffset="ringStrokeOffset(pctForItem(item))"
                      />
                    </svg>
                    <div class="quiz-score-value">
                      <template v-if="pctForItem(item) != null">{{ pctForItem(item) }}%</template>
                      <template v-else>—</template>
                    </div>
                  </div>
                  <div class="quiz-score-frac">
                    <template v-if="pctForItem(item) != null">{{ item.score }}/{{ item.total_answered ?? item.total }}</template>
                    <template v-else>{{ liberado(item) ? 'pendente' : 'bloqueado' }}</template>
                  </div>
                </div>
                <div class="quiz-card-body">
                  <div class="enc-badge">Encontro {{ item.encontro }}</div>
                  <div class="quiz-title">{{ item.titulo }}</div>
                  <div class="quiz-meta" :class="{ pending: !item.submitted_at }">
                    <template v-if="item.submitted_at">
                      {{ item.score }}/{{ item.total_answered ?? item.total }} acertos ·
                      {{ formatDate(item.submitted_at) }}
                    </template>
                    <template v-else-if="liberado(item)">Não respondido</template>
                    <template v-else>
                      Conclua o encontro {{ item.encontro }} no programa para liberar
                    </template>
                  </div>
                </div>
                <div class="quiz-card-right">
                  <div class="quiz-bar-wrap">
                    <span class="quiz-bar-label">{{ item.total_answered ?? 0 }}/{{ item.total ?? 0 }}</span>
                    <div class="quiz-bar-mini" :title="(item.total_answered ?? 0) + '/' + (item.total ?? 0) + ' perguntas respondidas'">
                      <div
                        class="fill progress-fill"
                        :style="{
                          width: progressAnsweredForItem(item) + '%',
                        }"
                      ></div>
                    </div>
                  </div>
                  <span class="btn-open">
                    Abrir
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M5 12h14M12 5l7 7-7 7" />
                    </svg>
                  </span>
                </div>
              </div>
            </RouterLink>
            <div v-else class="quiz-card-link locked">
              <div class="quiz-card pending locked">
                <div class="quiz-score-wrap">
                  <div class="quiz-score-ring">
                    <svg viewBox="0 0 72 72" class="ring-svg">
                      <circle class="bg" cx="36" cy="36" r="30" />
                      <circle
                        class="fill none"
                        cx="36"
                        cy="36"
                        r="30"
                        fill="none"
                        stroke-width="6"
                        stroke-linecap="round"
                        :stroke-dasharray="2 * Math.PI * 30"
                        :stroke-dashoffset="2 * Math.PI * 30"
                      />
                    </svg>
                    <div class="quiz-score-value">—</div>
                  </div>
                  <div class="quiz-score-frac">bloqueado</div>
                </div>
                <div class="quiz-card-body">
                  <div class="enc-badge">Encontro {{ item.encontro }}</div>
                  <div class="quiz-title">{{ item.titulo }}</div>
                  <div class="quiz-meta pending">
                    Conclua o encontro {{ item.encontro }} no programa para liberar
                  </div>
                </div>
                <div class="quiz-card-right">
                  <div class="quiz-bar-wrap">
                    <span class="quiz-bar-label">—/—</span>
                    <div class="quiz-bar-mini" title="Quiz bloqueado">
                      <div class="fill none" style="width: 0%"></div>
                    </div>
                  </div>
                  <span class="btn-open">Bloqueado</span>
                </div>
              </div>
            </div>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.wrap {
  max-width: 920px;
  margin: 0 auto;
  padding: 0 20px 48px;
  padding-top: calc(var(--bar-h) + 28px);
}
.page-header {
  margin-bottom: 28px;
}
.page-header h1 {
  font-family: var(--serif);
  font-size: 28px;
  font-weight: 400;
  margin-bottom: 6px;
  color: var(--k0);
}
.page-header .muted {
  font-size: 14px;
  color: var(--k3);
}

.loading {
  background: #fff;
  border: 1px solid var(--bd);
  border-radius: 6px;
  padding: 32px;
  text-align: center;
  color: var(--k5);
}
.error-msg {
  padding: 24px 0;
  color: #b63737;
}
.empty-wrap {
  margin-top: 0;
}
.empty {
  text-align: center;
  color: var(--k5);
  padding: 48px 20px;
  font-size: 15px;
}

.dashboard {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
  margin-bottom: 32px;
}
.kpi-card {
  background: #fff;
  border: 1px solid var(--bd);
  border-radius: 6px;
  padding: 20px;
  position: relative;
  overflow: hidden;
}
.kpi-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: var(--gold);
}
.kpi-card.primary::before {
  background: linear-gradient(90deg, var(--k0) 0%, var(--gold) 100%);
}
.kpi-label {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--k5);
  margin-bottom: 6px;
}
.kpi-value {
  font-family: var(--serif);
  font-size: 28px;
  font-weight: 400;
  color: var(--k0);
}
.kpi-value.gold {
  color: var(--gold);
}
.kpi-value.success {
  color: var(--success);
}
.kpi-sub {
  font-size: 12px;
  color: var(--k5);
  margin-top: 4px;
}

.overall-bar-wrap {
  margin-top: 24px;
  background: #fff;
  border: 1px solid var(--bd);
  border-radius: 6px;
  padding: 24px;
}
.overall-bar-wrap .sec-title {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--k5);
  margin-bottom: 12px;
}
.overall-bar-track {
  height: 10px;
  background: var(--k8);
  border-radius: 5px;
  overflow: hidden;
}
.overall-bar-fill {
  height: 100%;
  border-radius: 5px;
  background: linear-gradient(90deg, var(--k0), var(--gold));
  transition: width 0.6s ease;
}
.overall-bar-legend {
  display: flex;
  justify-content: space-between;
  margin-top: 10px;
  font-size: 13px;
  color: var(--k3);
}

.list-section {
  margin-top: 28px;
}
.list-section .sec-title {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--k5);
  margin-bottom: 14px;
  display: flex;
  align-items: center;
  gap: 10px;
}
.list-section .sec-title::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--bd);
}
.quiz-cards {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.quiz-card {
  background: #fff;
  border: 1px solid var(--bd);
  border-radius: 6px;
  overflow: hidden;
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 20px;
  align-items: center;
  padding: 0;
  min-height: 88px;
  transition: box-shadow 0.2s, border-color 0.2s;
}
.quiz-card-link {
  text-decoration: none;
  color: inherit;
  display: contents;
}
.quiz-card-link:hover .quiz-card {
  border-color: var(--k0);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
}
.quiz-card-link.locked {
  pointer-events: none;
  cursor: default;
}
.quiz-card.pending {
  opacity: 0.92;
}
.quiz-card.locked {
  opacity: 0.7;
}
.quiz-card.locked .btn-open {
  background: var(--k5);
  border-color: var(--k5);
  cursor: default;
}

.quiz-score-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
  margin: 14px 0 14px 18px;
}
.quiz-score-ring {
  width: 72px;
  height: 72px;
  flex-shrink: 0;
  position: relative;
}
.quiz-score-ring .ring-svg {
  width: 100%;
  height: 100%;
  display: block;
  transform: rotate(-90deg);
}
.quiz-score-ring .bg {
  stroke: var(--k8);
  stroke-width: 6;
  fill: none;
}
.quiz-score-ring .fill {
  stroke-width: 6;
  fill: none;
  stroke-linecap: round;
  transition: stroke-dashoffset 0.5s ease;
}
.quiz-score-ring .fill.high {
  stroke: var(--success);
}
.quiz-score-ring .fill.mid {
  stroke: var(--warn);
}
.quiz-score-ring .fill.low {
  stroke: var(--low);
}
.quiz-score-ring .fill.none {
  stroke: var(--k7);
}
.quiz-score-value {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--serif);
  font-size: 18px;
  font-weight: 600;
  color: var(--k0);
}
.quiz-score-frac {
  font-size: 11px;
  color: var(--k5);
  font-weight: 500;
  text-align: center;
  line-height: 1.3;
  max-width: 90px;
}

.quiz-card-body {
  padding: 18px 0;
  min-width: 0;
}
.quiz-card-body .enc-badge {
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--gold);
  margin-bottom: 4px;
}
.quiz-card-body .quiz-title {
  font-family: var(--serif);
  font-size: 17px;
  color: var(--k0);
  margin-bottom: 6px;
}
.quiz-card-body .quiz-meta {
  font-size: 13px;
  color: var(--k5);
}
.quiz-card-body .quiz-meta.pending {
  font-style: italic;
}
.quiz-card-right {
  padding: 18px 20px 18px 0;
  display: flex;
  align-items: center;
  gap: 12px;
}
.quiz-bar-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}
.quiz-bar-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--k3);
}
.quiz-bar-mini {
  width: 80px;
  height: 6px;
  background: var(--k8);
  border-radius: 3px;
  overflow: hidden;
}
.quiz-bar-mini .fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.4s ease;
}
.quiz-bar-mini .fill.high {
  background: var(--success);
}
.quiz-bar-mini .fill.mid {
  background: var(--warn);
}
.quiz-bar-mini .fill.low {
  background: var(--low);
}
.quiz-bar-mini .fill.none {
  background: var(--k7);
}
.quiz-bar-mini .fill.progress-fill {
  background: var(--k0);
}
.btn-open {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border: 1px solid var(--k0);
  background: var(--k0);
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  text-decoration: none;
  border-radius: 4px;
  white-space: nowrap;
  transition: opacity 0.2s;
}
.btn-open:hover {
  opacity: 0.9;
}
.btn-open svg {
  width: 14px;
  height: 14px;
  opacity: 0.9;
}

@media (max-width: 640px) {
  .quiz-card {
    grid-template-columns: 1fr;
    gap: 0;
    padding-bottom: 16px;
  }
  .quiz-score-wrap {
    margin: 16px auto 8px;
    justify-content: center;
  }
  .quiz-card-body {
    padding: 0 18px 12px;
    text-align: center;
  }
  .quiz-card-right {
    flex-wrap: wrap;
    justify-content: center;
    padding: 0 18px 18px;
  }
  .dashboard {
    grid-template-columns: 1fr 1fr;
  }
}
</style>
