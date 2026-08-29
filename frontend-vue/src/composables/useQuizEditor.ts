import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { fetchQuiz, fetchQuizById, fetchMyQuizResponse, submitQuiz } from '@/api/quiz'
import type { QuizDoc, QuizSubmitResponse } from '@/api/quiz'


export function useQuizEditor() {
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
  return {
    quizIdParam, encontroId, loading, error, quiz, myResponse, answers, feedback,
    lastSubmit, sessionQuizWithRationales, showReport, submitting, reviewMode,
    questoes, allAnswered, sessionReport, reviewReport, SESSION_SIZE,
    scoreLevel, setAnswer, getAnswer, getFb, doSubmit,

  }
}

export type QuizEditor = ReturnType<typeof useQuizEditor>
