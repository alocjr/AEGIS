<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import { fetchQuiz, fetchQuizById, fetchMyQuizResponse, submitQuiz } from '@/api/quiz'
import type { QuizDoc, QuizSubmitResponse } from '@/api/quiz'

const route = useRoute()
const quizIdParam = computed(() => route.params.quizId as string | undefined)
const encontroIdParam = computed(() => (route.params.encontroId ? Number(route.params.encontroId) : 0))
/** Encontro numérico usado nas chamadas de API (vem da rota ou do quiz carregado por quiz_id). */
const encontroId = computed(() => {
  if (encontroIdParam.value) return encontroIdParam.value
  return quiz.value?.encontro ?? 0
})

const loading = ref(true)
const error = ref<string | null>(null)
const quiz = ref<QuizDoc | null>(null)
const myResponse = ref<Awaited<ReturnType<typeof fetchMyQuizResponse>> | null>(null)
const answers = ref<Record<string, number>>({})
const feedback = ref<Record<string, { is_correct: boolean; rationale: string; selected_index: number; correct_index: number | null }>>({})

/** Após enviar um batch: resultado da sessão + quiz com racionais das 3 perguntas para exibir no relatório */
const lastSubmit = ref<QuizSubmitResponse | null>(null)
const sessionQuizWithRationales = ref<QuizDoc | null>(null)
const showReport = ref(false)
const submitting = ref(false)
const reviewMode = ref(false)

const questoes = computed(() => quiz.value?.questoes ?? [])
const allAnswered = computed(() => quiz.value?.all_answered === true)

function scoreLevel(pct: number | null): 'high' | 'mid' | 'low' | 'none' {
  if (pct == null || pct < 0) return 'none'
  if (pct >= 80) return 'high'
  if (pct >= 50) return 'mid'
  return 'low'
}

function setAnswer(qId: number, index: number) {
  answers.value = { ...answers.value, [String(qId)]: index }
}

function getAnswer(qId: number): number | undefined {
  return answers.value[String(qId)]
}

function getFb(qId: number) {
  return feedback.value[String(qId)]
}

const isReviewQuery = computed(() => route.query.review === '1')

async function load() {
  const byId = !!quizIdParam.value
  if (!byId && !encontroIdParam.value) return
  loading.value = true
  error.value = null
  showReport.value = false
  lastSubmit.value = null
  sessionQuizWithRationales.value = null
  try {
    const fetchQuizFn = byId
      ? (opts?: { review?: boolean; batch?: number }) => fetchQuizById(quizIdParam.value!, opts)
      : (opts?: { review?: boolean; batch?: number }) => fetchQuiz(encontroIdParam.value, opts)

    if (isReviewQuery.value) {
      const reviewQuiz = await fetchQuizFn({ review: true })
      quiz.value = reviewQuiz
      const myRes = await fetchMyQuizResponse(reviewQuiz.encontro)
      myResponse.value = myRes
      answers.value = { ...(myRes.answers || {}) }
      feedback.value = { ...(myRes.feedback || {}) }
      reviewMode.value = true
    } else {
      const quizRes = await fetchQuizFn({ batch: 3 })
      quiz.value = quizRes
      const myRes = await fetchMyQuizResponse(quizRes.encontro)
      myResponse.value = myRes
      answers.value = { ...(myRes.answers || {}) }
      feedback.value = { ...(myRes.feedback || {}) }

      if (quizRes.questoes.length === 0 && quizRes.all_answered) {
        reviewMode.value = true
        const reviewQuiz = await fetchQuizFn({ review: true })
        quiz.value = reviewQuiz
        const updated = await fetchMyQuizResponse(reviewQuiz.encontro)
        myResponse.value = updated
        answers.value = { ...(updated.answers || {}) }
        feedback.value = { ...(updated.feedback || {}) }
      } else if (quizRes.questoes.length === 0) {
        quiz.value = quizRes
      }
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Erro ao carregar quiz.'
  } finally {
    loading.value = false
  }
}

async function doSubmit() {
  const qs = questoes.value
  const missing = qs.filter((q) => getAnswer(q.id) === undefined)
  if (missing.length) {
    error.value = 'Responda todas as questões antes de enviar.'
    return
  }
  const toSend: Record<string, number> = {}
  qs.forEach((q) => {
    const v = getAnswer(q.id)
    if (v !== undefined) toSend[String(q.id)] = v
  })
  submitting.value = true
  error.value = null
  try {
    const result = await submitQuiz(encontroId.value, toSend)
    lastSubmit.value = result
    feedback.value = { ...feedback.value, ...result.feedback }

    const ids = qs.map((q) => q.id).join(',')
    sessionQuizWithRationales.value = await fetchQuiz(encontroId.value, { rationales_for: ids })
    showReport.value = true

    if (result.submitted_at) {
      reviewMode.value = true
      const reviewQuiz = await fetchQuiz(encontroId.value, { review: true })
      quiz.value = reviewQuiz
      const updated = await fetchMyQuizResponse(encontroId.value)
      myResponse.value = updated
      answers.value = { ...(updated.answers || {}) }
      feedback.value = { ...(updated.feedback || {}) }
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Erro ao enviar respostas.'
  } finally {
    submitting.value = false
  }
}

const SESSION_SIZE = 3

const sessionReport = computed(() => {
  const s = lastSubmit.value
  if (!s) return null
  const totalQuestions = s.total ?? 0
  const sessionPct = Math.round((s.session_correct / SESSION_SIZE) * 100)
  const answeredPct = s.total_answered > 0 ? Math.round((s.score / s.total_answered) * 100) : 0
  const completionPct = totalQuestions > 0 ? Math.round((s.total_answered / totalQuestions) * 100) : 0
  return {
    sessionCorrect: s.session_correct,
    sessionTotal: SESSION_SIZE,
    sessionPct,
    totalCorrect: s.score,
    totalAnswered: s.total_answered,
    totalQuestions,
    answeredPct,
    completionPct,
  }
})

const reviewReport = computed(() => {
  const r = myResponse.value
  if (!r || r.score == null || r.total == null) return null
  const answered = Object.keys(r.answers || {}).length
  const pct = r.total > 0 ? Math.round((r.score / r.total) * 100) : 0
  return {
    score: r.score,
    total: r.total,
    answered,
    pct,
  }
})

onMounted(load)
watch([encontroIdParam, quizIdParam, isReviewQuery], load)
</script>

<template>
  <div class="wrap">
    <header class="page-header">
      <h1>Quiz — Encontro {{ encontroId }}</h1>
      <p v-if="quiz && !reviewMode" class="muted">
        {{ quiz.titulo }}
      </p>
      <p v-else-if="quiz && reviewMode" class="muted">
        Você respondeu todas as questões. Racional de cada alternativa abaixo.
      </p>
    </header>

    <div v-if="loading" class="loading">Carregando quiz...</div>

    <template v-else-if="error">
      <div class="error-msg">{{ error }}</div>
    </template>

    <!-- Sem perguntas disponíveis -->
    <div v-else-if="quiz && questoes.length === 0 && !allAnswered" class="card">
      <div class="title">Encontro {{ quiz.encontro }}</div>
      <p class="muted">Nenhuma pergunta disponível.</p>
    </div>

    <!-- Modo revisão (todas respondidas) -->
    <template v-else-if="quiz && reviewMode && questoes.length > 0">
      <div v-if="reviewReport" class="card report-left report-left--review">
        <h2 class="report-heading">Resultado do quiz</h2>

        <!-- Bloco: Resultado final -->
        <section class="report-block report-block--session">
          <div class="report-block-label">Resultado final</div>
          <div class="report-block-content">
            <div class="report-big-ring">
              <svg class="ring-svg" viewBox="0 0 100 100">
                <circle class="bg" cx="50" cy="50" r="42" />
                <circle
                  class="fill"
                  :class="scoreLevel(reviewReport.pct)"
                  cx="50"
                  cy="50"
                  r="42"
                  stroke-dasharray="263.9"
                  :stroke-dashoffset="263.9 - (reviewReport.pct / 100) * 263.9"
                />
              </svg>
              <div class="report-big-value">
                <span class="num">{{ reviewReport.score }}/{{ reviewReport.total }}</span>
                <span class="sublabel">acertos</span>
              </div>
            </div>
            <div class="report-block-bar">
              <div class="bar-track">
                <div
                  class="bar-fill"
                  :class="scoreLevel(reviewReport.pct)"
                  :style="{ width: reviewReport.pct + '%' }"
                ></div>
              </div>
              <div class="bar-legend">{{ reviewReport.pct }}%</div>
            </div>
          </div>
        </section>

        <!-- Bloco: Resumo -->
        <section class="report-block report-block--answered">
          <div class="report-block-label">Resumo</div>
          <div class="report-block-content">
            <div class="report-big-num">
              <span class="num">{{ reviewReport.score }}</span>
              <span class="sep">/</span>
              <span class="den">{{ reviewReport.total }}</span>
            </div>
            <div class="report-block-desc">questões respondidas · {{ reviewReport.pct }}% de acertos</div>
            <div class="report-block-bar">
              <div class="bar-track">
                <div
                  class="bar-fill"
                  :class="scoreLevel(reviewReport.pct)"
                  :style="{ width: reviewReport.pct + '%' }"
                ></div>
              </div>
            </div>
          </div>
        </section>
      </div>
      <div class="card questions-card">
        <div v-for="q in questoes" :key="q.id" class="q">
          <div class="q-title"><strong>Q{{ q.id }}.</strong> {{ q.pergunta }}</div>
          <div class="opts opts-review">
            <div
              v-for="(op, opIdx) in q.opcoes"
              :key="opIdx"
              class="opt-block"
              :class="{
                correct: op.isCorrect,
                wrong: getFb(q.id)?.selected_index === op.index && !op.isCorrect,
              }"
            >
              <div class="opt-label">
                {{ getFb(q.id)?.selected_index === op.index ? '[Sua escolha] ' : '' }}{{ op.isCorrect ? '[Correta]' : '' }}
              </div>
              <div class="opt-text">{{ op.text }}</div>
              <div v-if="op.rationale" class="opt-rationale">{{ op.rationale }}</div>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- Relatório após enviar um batch de 3 (ainda há mais perguntas) -->
    <template v-else-if="showReport && sessionReport && sessionQuizWithRationales">
      <div class="report-wrap report-wrap--session">
        <div class="card report-left report-left--session">
          <h2 class="report-heading">Relatório desta sessão</h2>

          <!-- Resumo em relação às perguntas respondidas -->
          <div class="session-resumo">
            <div class="session-resumo-line">
              <span class="session-resumo-num">{{ sessionReport.totalAnswered }}</span>
              <span class="session-resumo-de"> de {{ sessionReport.totalQuestions }} perguntas respondidas</span>
            </div>
            <div class="session-resumo-line session-resumo-acertos">
              <span class="session-resumo-pct">{{ sessionReport.answeredPct }}%</span>
              <span class="session-resumo-label">de acertos nas respondidas</span>
            </div>
          </div>

          <!-- Bloco 1: Esta sessão (3 perguntas) -->
          <section class="report-block report-block--session">
            <div class="report-block-label">Esta sessão (3 perguntas)</div>
            <div class="report-block-content">
              <div class="report-chart-row">
                <div class="report-big-ring report-big-ring--session">
                  <svg class="ring-svg" viewBox="0 0 100 100">
                    <circle class="bg" cx="50" cy="50" r="40" />
                    <circle
                      class="fill"
                      :class="scoreLevel(sessionReport.sessionPct)"
                      cx="50"
                      cy="50"
                      r="40"
                      stroke-dasharray="251.2"
                      :stroke-dashoffset="251.2 - (sessionReport.sessionPct / 100) * 251.2"
                    />
                  </svg>
                  <div class="report-big-value">
                    <span class="num">{{ sessionReport.sessionCorrect }}/{{ sessionReport.sessionTotal }}</span>
                    <span class="sublabel">acertos</span>
                  </div>
                </div>
                <div class="report-chart-legend">
                  <span class="report-chart-pct" :class="scoreLevel(sessionReport.sessionPct)">{{ sessionReport.sessionPct }}%</span>
                  <span class="report-chart-desc">nesta rodada</span>
                </div>
              </div>
              <div class="report-bar-row">
                <div class="report-bar-label"><span>Acertos</span><span>{{ sessionReport.sessionPct }}%</span></div>
                <div class="bar-track bar-track--thick">
                  <div
                    class="bar-fill bar-fill--round"
                    :class="scoreLevel(sessionReport.sessionPct)"
                    :style="{ width: sessionReport.sessionPct + '%' }"
                  ></div>
                </div>
              </div>
            </div>
          </section>

          <!-- Bloco 2: Acertos em relação às perguntas já respondidas -->
          <section class="report-block report-block--answered">
            <div class="report-block-label">Acertos nas perguntas já respondidas</div>
            <div class="report-block-content">
              <div class="report-chart-row">
                <div class="report-big-num report-big-num--acertos report-big-num--large">
                  <span class="num">{{ sessionReport.totalCorrect }}</span>
                  <span class="sep">/</span>
                  <span class="den">{{ sessionReport.totalAnswered }}</span>
                </div>
                <div class="report-chart-legend">
                  <span class="report-chart-pct" :class="scoreLevel(sessionReport.answeredPct)">{{ sessionReport.answeredPct }}%</span>
                  <span class="report-chart-desc">de acertos</span>
                </div>
              </div>
              <div class="report-bar-row">
                <div class="report-bar-label"><span>Percentual de acertos</span><span>{{ sessionReport.answeredPct }}%</span></div>
                <div class="bar-track bar-track--thick">
                  <div
                    class="bar-fill bar-fill--round"
                    :class="scoreLevel(sessionReport.answeredPct)"
                    :style="{ width: sessionReport.answeredPct + '%' }"
                  ></div>
                </div>
              </div>
            </div>
          </section>

          <!-- Bloco 3: Conclusão do quiz (respondidas / total) -->
          <section class="report-block report-block--total">
            <div class="report-block-label">Conclusão do quiz</div>
            <div class="report-block-content">
              <div class="report-chart-row">
                <div class="report-big-num report-big-num--conclusao report-big-num--large">
                  <span class="num">{{ sessionReport.totalAnswered }}</span>
                  <span class="sep">/</span>
                  <span class="den">{{ sessionReport.totalQuestions }}</span>
                </div>
                <div class="report-chart-legend">
                  <span class="report-chart-pct report-chart-pct--conclusao">{{ sessionReport.completionPct }}%</span>
                  <span class="report-chart-desc">concluído</span>
                </div>
              </div>
              <div class="report-bar-row">
                <div class="report-bar-label"><span>Perguntas respondidas</span><span>{{ sessionReport.completionPct }}%</span></div>
                <div class="bar-track bar-track--thick">
                  <div
                    class="bar-fill bar-fill--round bar-fill--conclusao"
                    :style="{ width: sessionReport.completionPct + '%' }"
                  ></div>
                </div>
              </div>
            </div>
          </section>

          <div class="report-actions">
            <template v-if="lastSubmit?.submitted_at">
              <p class="report-done-msg">Você concluiu o quiz deste encontro.</p>
            </template>
            <RouterLink :to="quizIdParam ? `/quiz/q/${quizIdParam}?review=1` : `/quiz/${encontroId}?review=1`" class="btn-prime">Ver todas as respostas</RouterLink>
          </div>
        </div>
        <div class="card report-right report-right--session">
          <div class="sec-title sec-title--session">Perguntas desta sessão</div>
          <p class="sec-desc">Racional de cada alternativa abaixo.</p>
          <div class="report-questions">
            <div v-for="q in sessionQuizWithRationales.questoes" :key="q.id" class="q">
              <div class="q-title"><strong>Q{{ q.id }}.</strong> {{ q.pergunta }}</div>
              <div class="opts opts-review">
                <div
                  v-for="(op, opIdx) in q.opcoes"
                  :key="opIdx"
                  class="opt-block"
                  :class="{
                    correct: op.isCorrect,
                    wrong: getFb(q.id)?.selected_index === op.index && !op.isCorrect,
                  }"
                >
                  <div class="opt-label">
                    {{ getFb(q.id)?.selected_index === op.index ? '[Sua escolha] ' : '' }}{{ op.isCorrect ? '[Correta]' : '' }}
                  </div>
                  <div class="opt-text">{{ op.text }}</div>
                  <div v-if="op.rationale" class="opt-rationale">{{ op.rationale }}</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- Formulário: 3 perguntas em ordem -->
    <template v-else-if="quiz && questoes.length > 0">
      <div class="card meta-card">
        <div class="title">{{ quiz.titulo }}</div>
        <p class="muted">{{ questoes.length }} questões (próximas não respondidas). Responda e envie para avançar.</p>
        <p v-if="myResponse?.score != null && myResponse?.total != null" class="result-info">
          Total até agora: {{ myResponse.score }}/{{ myResponse.total }} acertos
        </p>
      </div>
      <div class="card questions-card">
        <div v-for="q in questoes" :key="q.id" class="q">
          <div class="q-title"><strong>Q{{ q.id }}.</strong> {{ q.pergunta }}</div>
          <div class="opts">
            <button
              v-for="(op, opIdx) in q.opcoes"
              :key="opIdx"
              type="button"
              class="opt"
              :class="{
                active: getAnswer(q.id) === op.index,
                correct: getFb(q.id) && op.index === getFb(q.id).correct_index,
                wrong: getFb(q.id) && getFb(q.id).selected_index === op.index && !getFb(q.id).is_correct,
              }"
              @click="setAnswer(q.id, op.index)"
            >
              {{ op.text }}
            </button>
          </div>
          <p v-if="q.hint" class="hint">Dica: {{ q.hint }}</p>
          <div v-if="getFb(q.id)" class="fb" :class="getFb(q.id).is_correct ? 'ok' : 'bad'">
            <strong>{{ getFb(q.id).is_correct ? 'Correta' : 'Incorreta' }}</strong><br>{{ getFb(q.id).rationale || '—' }}
          </div>
        </div>
      </div>
      <div class="card actions-card">
        <button type="button" class="btn-prime" :disabled="submitting" @click="doSubmit">
          {{ submitting ? 'Enviando…' : 'Enviar respostas' }}
        </button>
        <button type="button" class="btn-sec" @click="answers = {}; feedback = {}; error = null">
          Limpar
        </button>
      </div>
    </template>
  </div>
</template>

<style scoped>
.wrap {
  max-width: 920px;
  margin: 0 auto;
  padding: 0 20px 40px;
  padding-top: calc(var(--bar-h) + 24px);
}
.page-header {
  margin-bottom: 24px;
}
.page-header h1 {
  font-family: var(--serif);
  font-size: 26px;
  font-weight: 400;
  margin-bottom: 6px;
  color: var(--k0);
}
.muted {
  font-size: 14px;
  color: var(--k3);
}
.loading {
  background: #fff;
  border: 1px solid var(--bd);
  border-radius: 10px;
  padding: 28px 20px;
  text-align: center;
  color: var(--k5);
}
.error-msg {
  padding: 20px;
  color: var(--low);
  background: var(--lowBg);
  border: 1px solid var(--low);
  border-radius: 8px;
}
.card {
  background: #fff;
  border: 1px solid var(--bd);
  border-radius: 10px;
  padding: 22px 22px 20px;
  margin-bottom: 18px;
  box-shadow: 0 4px 18px rgba(15, 23, 42, 0.04);
}
.title,
.report-title {
  font-family: var(--serif);
  font-size: 18px;
  margin-bottom: 8px;
  color: var(--k0);
}

/* Título do card de relatório: não cortar */
.report-heading {
  font-family: var(--serif);
  font-size: 20px;
  font-weight: 600;
  color: var(--k0);
  margin: 0 0 24px 0;
  line-height: 1.3;
  word-wrap: break-word;
  overflow-wrap: break-word;
  min-width: 0;
}
.result-info {
  font-size: 13px;
  color: var(--k5);
  margin-top: 8px;
}

/* Questões */
.questions-card {
  padding: 24px;
}
.q {
  border-top: 1px solid var(--k7);
  padding: 14px 0;
}
.q:first-child {
  border-top: none;
}
.q-title {
  margin-bottom: 12px;
  font-size: 15px;
  color: var(--k0);
}
.opts {
  display: grid;
  gap: 8px;
}
.opt {
  border: 1px solid var(--bd);
  padding: 12px 14px;
  background: #fff;
  cursor: pointer;
  text-align: left;
  border-radius: 4px;
  font-size: 14px;
  transition: background 0.15s, border-color 0.15s;
}
.opt:hover {
  border-color: var(--k5);
}
.opt.active {
  background: var(--k0);
  color: #fff;
  border-color: var(--k0);
}
.opt.correct {
  border-color: var(--success);
  background: var(--successBg);
  color: var(--k0);
}
.opt.wrong {
  border-color: var(--low);
  background: var(--lowBg);
  color: var(--k0);
}
.hint {
  margin-top: 8px;
  font-size: 13px;
  color: var(--k3);
}
.fb {
  margin-top: 10px;
  padding: 10px 12px;
  border: 1px solid var(--bd);
  font-size: 14px;
  border-radius: 4px;
}
.fb.ok {
  border-color: var(--success);
  background: var(--successBg);
}
.fb.bad {
  border-color: var(--low);
  background: var(--lowBg);
}

/* Revisão: blocos de opção */
.opts-review {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.opt-block {
  border: 1px solid var(--bd);
  padding: 12px 14px;
  background: #fff;
  text-align: left;
  border-radius: 4px;
}
.opt-block.correct {
  border-color: var(--success);
  background: var(--successBg);
}
.opt-block.wrong {
  border-color: var(--low);
  background: var(--lowBg);
}
.opt-label {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.05em;
  color: var(--k3);
  margin-bottom: 4px;
}
.opt-text {
  font-size: 15px;
  margin-bottom: 6px;
}
.opt-rationale {
  font-size: 14px;
  color: var(--k3);
  line-height: 1.5;
  padding-top: 6px;
  border-top: 1px solid rgba(14, 14, 14, 0.06);
}

/* Relatório */
.report-dash::before {
  content: '';
  display: block;
  height: 3px;
  background: linear-gradient(90deg, var(--k0), var(--gold));
  margin: -20px -20px 16px -20px;
  border-radius: 6px 6px 0 0;
}
.report-dash-top {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  gap: 20px;
  margin-bottom: 16px;
}
.report-score-ring {
  width: 100px;
  height: 100px;
  flex-shrink: 0;
  position: relative;
}
.report-score-ring.small {
  width: 88px;
  height: 88px;
}
.report-score-ring .ring-svg {
  width: 100%;
  height: 100%;
  transform: rotate(-90deg);
}
.report-score-ring .bg {
  stroke: var(--k8);
  stroke-width: 8;
  fill: none;
}
.report-score-ring .fill {
  stroke-width: 8;
  fill: none;
  stroke-linecap: round;
}
.report-score-ring .fill.high {
  stroke: var(--success);
}
.report-score-ring .fill.mid {
  stroke: var(--warn);
}
.report-score-ring .fill.low {
  stroke: var(--low);
}
.report-score-ring .value {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  font-family: var(--serif);
  font-size: 22px;
  font-weight: 600;
  color: var(--k0);
}
.report-score-ring.small .value {
  font-size: 18px;
}
.report-score-ring .value span:last-child {
  font-size: 12px;
  font-weight: 400;
  color: var(--k5);
}
.report-kpis {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  flex: 1;
  min-width: 0;
}
.report-kpi .k {
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--k5);
  margin-bottom: 4px;
}
.report-kpi .v {
  font-family: var(--serif);
  font-size: 18px;
  font-weight: 600;
  color: var(--k0);
}
.report-kpi .v.success {
  color: var(--success);
}
.report-bar-wrap {
  margin-top: 12px;
}
.bar-label {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--k5);
  margin-bottom: 8px;
  display: flex;
  justify-content: space-between;
}
.report-bar-track {
  height: 10px;
  background: var(--k8);
  border-radius: 5px;
  overflow: hidden;
}
.report-bar-fill {
  height: 100%;
  border-radius: 5px;
  transition: width 0.6s ease;
}
.report-bar-fill.high {
  background: var(--success);
}
.report-bar-fill.mid {
  background: var(--warn);
}
.report-bar-fill.low {
  background: var(--low);
}

.report-wrap {
  display: grid;
  grid-template-columns: minmax(300px, 400px) 1fr;
  gap: 24px;
  align-items: start;
}
.report-wrap--session {
  grid-template-columns: minmax(320px, 420px) 1fr;
  gap: 28px;
}
.report-left {
  min-width: 0;
  position: relative;
}
.report-left--review {
}
.report-left.card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: linear-gradient(90deg, var(--k0), var(--gold));
  border-radius: 6px 6px 0 0;
  margin: -20px -20px 0 -20px;
}

/* Resumo: perguntas respondidas + % acertos (em relação às respondidas) */
.session-resumo {
  background: linear-gradient(135deg, var(--k0) 0%, #1a3254 100%);
  color: #fff;
  padding: 20px 22px;
  border-radius: 10px;
  margin-bottom: 24px;
  box-shadow: 0 4px 16px rgba(12, 35, 64, 0.15);
}
.session-resumo-line {
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 6px;
}
.session-resumo-line + .session-resumo-line {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid rgba(255, 255, 255, 0.2);
}
.session-resumo-num {
  font-family: var(--serif);
  font-size: 28px;
  font-weight: 700;
  line-height: 1;
}
.session-resumo-de {
  font-size: 14px;
  opacity: 0.9;
}
.session-resumo-acertos .session-resumo-pct {
  font-family: var(--serif);
  font-size: 24px;
  font-weight: 700;
  color: #7dd3a0;
}
.session-resumo-label {
  font-size: 13px;
  opacity: 0.9;
}

/* Blocos do relatório */
.report-block {
  margin-bottom: 24px;
  padding-bottom: 24px;
  border-bottom: 1px solid var(--k7);
}
.report-block:last-of-type {
  margin-bottom: 0;
  padding-bottom: 0;
  border-bottom: none;
}
.report-block-label {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--k5);
  margin-bottom: 12px;
}
.report-block-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-width: 0;
}
.report-chart-row {
  display: flex;
  align-items: center;
  gap: 20px;
  flex-wrap: wrap;
}
.report-chart-legend {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.report-chart-pct {
  font-family: var(--serif);
  font-size: 26px;
  font-weight: 700;
  color: var(--k0);
}
.report-chart-pct.high {
  color: var(--success);
}
.report-chart-pct.mid {
  color: var(--warn);
}
.report-chart-pct.low {
  color: var(--low);
}
.report-chart-pct--conclusao {
  color: var(--k0);
}
.report-chart-desc {
  font-size: 12px;
  color: var(--k5);
}
.report-bar-row {
  margin-top: 4px;
}
.report-bar-label {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--k5);
  margin-bottom: 8px;
}
.bar-track {
  height: 8px;
  background: var(--k8);
  border-radius: 4px;
  overflow: hidden;
}
.bar-track--thick {
  height: 12px;
  border-radius: 6px;
}
.bar-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.6s ease;
}
.bar-fill--round {
  border-radius: 6px;
}
.bar-fill.high {
  background: var(--success);
}
.bar-fill.mid {
  background: var(--warn);
}
.bar-fill.low {
  background: var(--low);
}
.bar-fill--conclusao {
  background: linear-gradient(90deg, var(--k0), var(--gold));
}
.report-block-bar .bar-track {
  height: 8px;
  background: var(--k8);
  border-radius: 4px;
  overflow: hidden;
}
.report-block-bar .bar-legend {
  font-size: 12px;
  color: var(--k5);
  margin-top: 6px;
  font-weight: 600;
}

/* Anel (gráfico circular) */
.report-big-ring {
  width: 100px;
  height: 100px;
  position: relative;
  flex-shrink: 0;
}
.report-big-ring--session {
  width: 110px;
  height: 110px;
  filter: drop-shadow(0 2px 8px rgba(0, 0, 0, 0.08));
}
.report-big-ring .ring-svg {
  width: 100%;
  height: 100%;
  transform: rotate(-90deg);
}
.report-big-ring .bg {
  stroke: var(--k8);
  stroke-width: 8;
  fill: none;
}
.report-big-ring--session .bg {
  stroke: var(--k7);
  stroke-width: 10;
}
.report-big-ring .fill {
  stroke-width: 8;
  fill: none;
  stroke-linecap: round;
}
.report-big-ring--session .fill {
  stroke-width: 10;
}
.report-big-ring .fill.high {
  stroke: var(--success);
}
.report-big-ring .fill.mid {
  stroke: var(--warn);
}
.report-big-ring .fill.low {
  stroke: var(--low);
}
.report-big-value {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  font-family: var(--serif);
}
.report-big-value .num {
  font-size: 24px;
  font-weight: 700;
  color: var(--k0);
  line-height: 1.1;
}
.report-big-ring--session .report-big-value .num {
  font-size: 22px;
}
.report-big-value .sublabel {
  font-size: 11px;
  font-weight: 500;
  color: var(--k5);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.report-big-num {
  display: flex;
  align-items: baseline;
  gap: 2px;
  flex-wrap: wrap;
}
.report-big-num--large .num,
.report-big-num--large .den {
  font-size: 36px;
}
.report-big-num--large .sep {
  font-size: 30px;
}
.report-big-num .num {
  font-family: var(--serif);
  font-size: 32px;
  font-weight: 700;
  color: var(--success);
  line-height: 1;
}
.report-big-num .sep {
  font-family: var(--serif);
  font-size: 28px;
  font-weight: 600;
  color: var(--k5);
}
.report-big-num .den {
  font-family: var(--serif);
  font-size: 28px;
  font-weight: 600;
  color: var(--k0);
}
.report-block-desc {
  font-size: 14px;
  color: var(--k5);
}
.report-block-bar {
  margin-top: 4px;
}
.report-big-num--acertos .num {
  color: var(--success);
}
.report-big-num--conclusao .num {
  color: var(--k0);
}
.report-block-desc strong {
  color: var(--k0);
  font-weight: 600;
}

/* Painel de sessão: blocos e gráficos */
.report-left--session .report-block {
  padding: 20px 22px;
  margin-bottom: 18px;
  border-radius: 10px;
  background: var(--k9);
  border: 1px solid var(--k7);
}
.report-left--session .report-block:last-of-type {
  margin-bottom: 0;
}
.report-left--session .report-block--session {
  background: linear-gradient(135deg, var(--k9) 0%, var(--k8) 100%);
  border-color: var(--k7);
}
.report-left--session .report-block-label {
  color: var(--k3);
  font-size: 10px;
  letter-spacing: 0.1em;
  margin-bottom: 12px;
}
.report-left--session .report-block-content {
  gap: 14px;
}
.report-left--session .report-block-bar,
.report-left--session .report-bar-row {
  margin-top: 6px;
}
.report-left--session .bar-track--thick {
  height: 14px;
  border-radius: 7px;
}
.report-left--session .bar-fill--round {
  border-radius: 7px;
}

/* Painel direito: perguntas da sessão */
.report-right--session {
  border-left: 4px solid var(--gold);
}
.report-right--session .sec-title--session {
  font-size: 13px;
  color: var(--k0);
  margin-bottom: 4px;
}
.report-right--session .sec-desc {
  font-size: 13px;
  color: var(--k5);
  margin-bottom: 18px;
}
.report-actions {
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid var(--k7);
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.report-done-msg {
  font-weight: 600;
  color: var(--success);
  margin: 0;
}
.sec-title {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--k3);
  margin-bottom: 14px;
}
.report-questions .q {
  border-top: 1px solid var(--k7);
  padding: 14px 0;
}
.report-questions .q:first-child {
  border-top: none;
}

.btn-prime {
  padding: 10px 18px;
  background: var(--k0);
  color: #fff;
  border: 1px solid var(--k0);
  border-radius: 4px;
  font-weight: 600;
  cursor: pointer;
}
.btn-prime:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}
.btn-sec {
  padding: 10px 18px;
  background: #fff;
  color: var(--k0);
  border: 1px solid var(--k0);
  border-radius: 4px;
  font-weight: 600;
  cursor: pointer;
  text-decoration: none;
  display: inline-block;
  text-align: center;
}
.actions-card {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
  justify-content: flex-start;
}

@media (max-width: 720px) {
  .report-wrap {
    grid-template-columns: 1fr;
  }
  .report-dash-top {
    flex-direction: column;
    align-items: center;
  }
  .actions-card {
    justify-content: center;
    text-align: center;
  }
  .questions-card {
    padding: 20px 16px;
  }
  .card {
    padding-inline: 18px;
  }
}
</style>
