import { get, post } from './client'

export interface QuizListItem {
  encontro: number
  /** ObjectId do quiz (para link estável). */
  quiz_id?: string
  titulo: string
  total: number
  total_answered?: number
  score: number | null
  submitted_at: string | null
}

export interface QuizListResponse {
  items: QuizListItem[]
  ativo: number
  encontros_liberados: number[]
}

export interface QuizOpcao {
  index: number
  text: string
  rationale?: string
  isCorrect?: boolean
}

export interface QuizQuestao {
  id: number
  pergunta: string
  hint?: string
  opcoes: QuizOpcao[]
}

export interface QuizDoc {
  encontro: number
  titulo: string
  questoes: QuizQuestao[]
  all_answered?: boolean
}

export interface QuizMyResponse {
  answers: Record<string, number>
  score: number | null
  total: number | null
  feedback: Record<string, { is_correct: boolean; rationale: string; selected_index: number; correct_index: number | null }>
  submitted_at: string | null
}

export interface QuizSubmitResponse {
  answers: Record<string, number>
  score: number
  total: number
  total_answered: number
  feedback: Record<string, { is_correct: boolean; rationale: string; selected_index: number; correct_index: number | null }>
  submitted_at: string | null
  session_correct: number
  session_total: number
}

export function fetchQuizList(): Promise<QuizListResponse> {
  return get<QuizListResponse>('/api/quiz')
}

export function fetchQuiz(
  encontroId: number,
  opts?: { batch?: number; review?: boolean; rationales_for?: string }
): Promise<QuizDoc> {
  const params = new URLSearchParams()
  if (opts?.batch != null) params.set('batch', String(opts.batch))
  if (opts?.review) params.set('review', '1')
  if (opts?.rationales_for) params.set('rationales_for', opts.rationales_for)
  const qs = params.toString()
  return get<QuizDoc>(`/api/quiz/${encontroId}${qs ? `?${qs}` : ''}`)
}

/** Carrega quiz pelo ObjectId (quiz_id do encontro). */
export function fetchQuizById(
  quizId: string,
  opts?: { batch?: number; review?: boolean; rationales_for?: string }
): Promise<QuizDoc> {
  const params = new URLSearchParams()
  if (opts?.batch != null) params.set('batch', String(opts.batch))
  if (opts?.review) params.set('review', '1')
  if (opts?.rationales_for) params.set('rationales_for', opts.rationales_for ?? '')
  const qs = params.toString()
  return get<QuizDoc>(`/api/quiz/by-id/${quizId}${qs ? `?${qs}` : ''}`)
}

export function fetchMyQuizResponse(encontroId: number): Promise<QuizMyResponse> {
  return get<QuizMyResponse>(`/api/quiz/${encontroId}/my-response`)
}

export function submitQuiz(encontroId: number, answers: Record<string, number>): Promise<QuizSubmitResponse> {
  return post<QuizSubmitResponse>(`/api/quiz/${encontroId}/submit`, { answers })
}
