<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import {
  fetchAdminQuizList,
  fetchAdminQuiz,
  createOrUpdateQuiz,
  deleteQuiz,
  fetchCourseList,
  fetchCourse,
} from '@/api/admin'
import type {
  AdminQuizListItem,
  AdminQuizGroup,
  AdminQuizDetail,
  AdminQuizQuestao,
  AdminQuizOpcao,
  CourseListItem,
} from '@/api/admin'

const loading = ref(true)
const error = ref<string | null>(null)
const groupedByTrilha = ref<AdminQuizGroup[]>([])

/** Lista plana de todos os quizzes (para sugerir próximo encontro ao criar). */
const allQuizzes = computed(() =>
  groupedByTrilha.value.flatMap((g) => g.quizzes)
)

/** Trilhas (cursos) para o seletor do modal. */
const trilhas = ref<CourseListItem[]>([])

const modalOpen = ref(false)
const modalMode = ref<'create' | 'edit'>('create')
const modalTrilhaSlug = ref<string | null>(null) // empty string = "Sem trilha"
const modalEncontro = ref<number>(1)
const modalEncontroOptions = ref<{ id: number; titulo?: string }[]>([])
const modalEncontroLoading = ref(false)
const originalEncontro = ref<number | null>(null)
const modalTitulo = ref('')
const modalQuestoes = ref<AdminQuizQuestao[]>([])
const modalSaving = ref(false)
const modalError = ref<string | null>(null)

/** Extrai IDs dos encontros da jornada do curso (ordem da trilha). */
function getEncontrosFromCourse(pfe: Record<string, unknown>): { id: number; titulo?: string }[] {
  const jornada = (pfe?.jornada_aprendizagem as unknown[]) ?? []
  const out: { id: number; titulo?: string }[] = []
  for (const semana of jornada) {
    const encs = (semana as Record<string, unknown>)?.encontros as unknown[] ?? []
    for (const enc of encs) {
      const e = enc as Record<string, unknown>
      const id = typeof e?.id === 'number' ? e.id : Number(e?.id)
      if (!Number.isNaN(id)) {
        out.push({
          id,
          titulo: typeof e?.titulo === 'string' ? e.titulo : undefined,
        })
      }
    }
  }
  return out.sort((a, b) => a.id - b.id)
}

function emptyOpcao(): AdminQuizOpcao {
  return { text: '', rationale: '', isCorrect: false }
}

function emptyQuestao(id: number): AdminQuizQuestao {
  return {
    id,
    pergunta: '',
    hint: '',
    opcoes: [emptyOpcao(), emptyOpcao()],
  }
}

function nextQuestaoId(): number {
  const ids = modalQuestoes.value.map((q) => q.id)
  if (ids.length === 0) return 1
  return Math.max(...ids) + 1
}

function setCorrectOption(questaoIndex: number, opcaoIndex: number) {
  const q = modalQuestoes.value[questaoIndex]
  q.opcoes.forEach((op, i) => {
    op.isCorrect = i === opcaoIndex
  })
}

function addQuestao() {
  modalQuestoes.value = [...modalQuestoes.value, emptyQuestao(nextQuestaoId())]
}

function removeQuestao(index: number) {
  modalQuestoes.value = modalQuestoes.value.filter((_, i) => i !== index)
}

function addOpcao(questaoIndex: number) {
  const q = modalQuestoes.value[questaoIndex]
  q.opcoes = [...q.opcoes, emptyOpcao()]
}

function removeOpcao(questaoIndex: number, opcaoIndex: number) {
  const q = modalQuestoes.value[questaoIndex]
  if (q.opcoes.length <= 2) return
  q.opcoes = q.opcoes.filter((_, i) => i !== opcaoIndex)
  if (q.opcoes.every((o) => !o.isCorrect) && q.opcoes.length > 0) {
    q.opcoes[0].isCorrect = true
  }
}

async function loadEncontrosForTrilha(slug: string | null | undefined) {
  modalEncontroOptions.value = []
  const s = slug === '' ? null : slug
  if (!s) return
  modalEncontroLoading.value = true
  try {
    const course = await fetchCourse(s)
    const pfe = course?.programa_formacao_executiva ?? {}
    modalEncontroOptions.value = getEncontrosFromCourse(pfe as Record<string, unknown>)
  } finally {
    modalEncontroLoading.value = false
  }
}

function openCreate() {
  modalMode.value = 'create'
  originalEncontro.value = null
  modalError.value = null
  modalOpen.value = true
  if (trilhas.value.length > 0) {
    modalTrilhaSlug.value = trilhas.value[0].slug
    loadEncontrosForTrilha(trilhas.value[0].slug!).then(() => {
      const opts = modalEncontroOptions.value
      if (opts.length > 0) {
        const maxExisting = Math.max(0, ...allQuizzes.value.map((q) => q.encontro))
        const next = opts.find((e) => e.id > maxExisting) ?? opts[opts.length - 1]
        modalEncontro.value = next.id
      } else {
        modalEncontro.value = Math.max(1, ...allQuizzes.value.map((q) => q.encontro), 0) + 1
      }
    })
  } else {
    modalTrilhaSlug.value = ''
    modalEncontro.value = Math.max(1, ...allQuizzes.value.map((q) => q.encontro), 0) + 1
  }
  modalTitulo.value = ''
  modalQuestoes.value = [emptyQuestao(1)]
}

async function openEdit(item: AdminQuizListItem) {
  modalMode.value = 'edit'
  originalEncontro.value = item.encontro
  modalError.value = null
  modalOpen.value = true
  try {
    const quiz = await fetchAdminQuiz(item.encontro)
    modalEncontro.value = quiz.encontro
    modalTitulo.value = quiz.titulo ?? ''
    modalQuestoes.value =
      quiz.questoes?.length > 0
        ? quiz.questoes.map((q) => ({
            id: q.id,
            pergunta: q.pergunta ?? '',
            hint: q.hint ?? '',
            opcoes:
              q.opcoes?.length >= 2
                ? q.opcoes.map((o) => ({
                    text: o.text ?? '',
                    rationale: o.rationale ?? '',
                    isCorrect: o.isCorrect ?? false,
                  }))
                : [emptyOpcao(), emptyOpcao()],
          }))
        : [emptyQuestao(1)]
    modalQuestoes.value.forEach((q) => {
      if (q.opcoes.length > 0 && q.opcoes.every((o) => !o.isCorrect)) {
        q.opcoes[0].isCorrect = true
      }
    })
    const groupContaining = groupedByTrilha.value.find((g) =>
      g.quizzes.some((q) => q.encontro === item.encontro)
    )
    modalTrilhaSlug.value = groupContaining?.course_slug ?? ''
    await loadEncontrosForTrilha(modalTrilhaSlug.value || undefined)
    if (modalEncontroOptions.value.length > 0 && !modalEncontroOptions.value.some((e) => e.id === modalEncontro.value)) {
      modalEncontro.value = modalEncontroOptions.value[0].id
    }
  } catch (e) {
    modalError.value = e instanceof Error ? e.message : 'Erro ao carregar quiz.'
  }
}

function closeModal() {
  modalOpen.value = false
  modalError.value = null
  modalSaving.value = false
  originalEncontro.value = null
}

async function onTrilhaChange() {
  const slug = modalTrilhaSlug.value
  await loadEncontrosForTrilha(slug || undefined)
  const opts = modalEncontroOptions.value
  if (opts.length > 0) {
    if (!opts.some((e) => e.id === modalEncontro.value)) {
      modalEncontro.value = opts[0].id
    }
  } else {
    modalEncontro.value = Math.max(1, ...allQuizzes.value.map((q) => q.encontro), 0) + 1
  }
}

function validate(): string | null {
  if (modalQuestoes.value.length === 0) {
    return 'Adicione pelo menos uma questão.'
  }
  for (let i = 0; i < modalQuestoes.value.length; i++) {
    const q = modalQuestoes.value[i]
    if (!q.pergunta.trim()) return `Questão ${i + 1}: preencha o enunciado.`
    if (q.opcoes.length < 2) return `Questão ${i + 1}: adicione pelo menos 2 opções.`
    const withText = q.opcoes.filter((o) => o.text.trim())
    if (withText.length < 2) return `Questão ${i + 1}: preencha pelo menos 2 opções.`
    const correct = q.opcoes.find((o) => o.isCorrect)
    if (!correct || !correct.text.trim()) {
      return `Questão ${i + 1}: marque a opção correta.`
    }
  }
  return null
}

async function saveModal() {
  modalError.value = null
  const err = validate()
  if (err) {
    modalError.value = err
    return
  }
  modalSaving.value = true
  try {
    const newEncontro = modalEncontro.value
    if (modalMode.value === 'edit' && originalEncontro.value !== null && originalEncontro.value !== newEncontro) {
      await deleteQuiz(originalEncontro.value)
    }
    const payload = {
      encontro: newEncontro,
      titulo: modalTitulo.value.trim() || undefined,
      questoes: modalQuestoes.value.map((q) => ({
        id: q.id,
        pergunta: q.pergunta.trim(),
        hint: q.hint?.trim() || undefined,
        opcoes: q.opcoes.map((o) => ({
          text: o.text.trim(),
          rationale: o.rationale?.trim() || undefined,
          isCorrect: !!o.isCorrect,
        })),
      })),
    }
    await createOrUpdateQuiz(payload)
    const res = await fetchAdminQuizList()
    groupedByTrilha.value = res.grouped
    closeModal()
  } catch (e) {
    modalError.value = e instanceof Error ? e.message : 'Erro ao salvar quiz.'
  } finally {
    modalSaving.value = false
  }
}

onMounted(async () => {
  try {
    const [res, courses] = await Promise.all([fetchAdminQuizList(), fetchCourseList()])
    groupedByTrilha.value = res.grouped
    trilhas.value = courses
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Erro ao carregar dados.'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="quiz-page">
    <header class="page-header">
      <h1 class="page-title">Quiz</h1>
      <p class="page-sub">Criar e editar quizzes por encontro.</p>
      <div class="page-actions">
        <button type="button" class="btn-primary" @click="openCreate">Novo quiz</button>
      </div>
    </header>

    <div v-if="loading" class="loading">Carregando...</div>
    <div v-else-if="error" class="error-msg">{{ error }}</div>
    <div v-else-if="allQuizzes.length === 0" class="empty">
      Nenhum quiz cadastrado. Clique em <strong>Novo quiz</strong> para criar.
    </div>
    <div v-else class="grouped-quizzes">
      <section v-for="group in groupedByTrilha" :key="group.course_slug ?? 'orphan'" class="trilha-section">
        <h2 class="trilha-section-title">{{ group.titulo }}</h2>
        <div class="card-grid">
          <article v-for="q in group.quizzes" :key="q.encontro" class="quiz-card">
            <div class="quiz-card-header">
              <h3 class="quiz-title">{{ q.titulo || `Quiz Encontro ${q.encontro}` }}</h3>
              <span class="quiz-meta">Encontro {{ q.encontro }} · {{ q.total }} questão(ões)</span>
            </div>
            <div class="quiz-card-actions">
              <button type="button" class="btn-secondary btn-sm" @click="openEdit(q)">Editar</button>
            </div>
          </article>
        </div>
      </section>
    </div>

    <!-- Modal Criar / Editar -->
    <Teleport to="body">
      <div v-if="modalOpen" class="modal-backdrop" @click.self="closeModal">
        <div class="modal-box modal-quiz">
          <div class="modal-header">
            <h2>{{ modalMode === 'create' ? 'Novo quiz' : 'Editar quiz' }}</h2>
            <button type="button" class="modal-close" aria-label="Fechar" @click="closeModal">×</button>
          </div>
          <div class="modal-body">
            <div v-if="modalError" class="modal-error">{{ modalError }}</div>
            <div class="form-row">
              <div class="form-group">
                <label for="quiz-trilha">Trilha</label>
                <select
                  id="quiz-trilha"
                  v-model="modalTrilhaSlug"
                  class="input select"
                  @change="onTrilhaChange"
                >
                  <option value="">Sem trilha</option>
                  <option
                    v-for="t in trilhas"
                    :key="t.slug"
                    :value="t.slug"
                  >
                    {{ t.titulo || t.slug }}
                  </option>
                </select>
              </div>
              <div class="form-group">
                <label for="quiz-encontro">Encontro</label>
                <select
                  v-if="modalEncontroOptions.length > 0"
                  id="quiz-encontro"
                  v-model.number="modalEncontro"
                  class="input select"
                  :disabled="modalEncontroLoading"
                >
                  <option
                    v-for="e in modalEncontroOptions"
                    :key="e.id"
                    :value="e.id"
                  >
                    {{ e.id }}{{ e.titulo ? ` — ${e.titulo}` : '' }}
                  </option>
                </select>
                <input
                  v-else
                  id="quiz-encontro-num"
                  v-model.number="modalEncontro"
                  type="number"
                  min="1"
                  step="1"
                  class="input input-num"
                />
                <span v-if="modalEncontroLoading" class="form-hint">Carregando encontros…</span>
              </div>
              <div class="form-group flex-1">
                <label for="quiz-titulo">Título</label>
                <input
                  id="quiz-titulo"
                  v-model="modalTitulo"
                  type="text"
                  placeholder="ex: Quiz Encontro 1"
                  class="input"
                />
              </div>
            </div>

            <div class="questoes-section">
              <div class="questoes-header">
                <label class="section-label">Questões</label>
                <button type="button" class="btn-secondary btn-sm" @click="addQuestao">+ Adicionar questão</button>
              </div>
              <div
                v-for="(questao, qIdx) in modalQuestoes"
                :key="questao.id"
                class="questao-block"
              >
                <div class="questao-header">
                  <span class="questao-num">Questão {{ qIdx + 1 }}</span>
                  <button
                    type="button"
                    class="btn-ghost btn-sm"
                    :disabled="modalQuestoes.length <= 1"
                    @click="removeQuestao(qIdx)"
                  >
                    Remover
                  </button>
                </div>
                <div class="form-group">
                  <label>Enunciado</label>
                  <textarea
                    v-model="questao.pergunta"
                    class="input textarea"
                    rows="2"
                    placeholder="Pergunta..."
                  />
                </div>
                <div class="form-group">
                  <label>Dica (opcional)</label>
                  <input
                    v-model="questao.hint"
                    type="text"
                    class="input"
                    placeholder="Dica para o aluno"
                  />
                </div>
                <div class="opcoes-list">
                  <label class="opcoes-label">Opções (marque a correta)</label>
                  <div
                    v-for="(opcao, oIdx) in questao.opcoes"
                    :key="oIdx"
                    class="opcao-row"
                  >
                    <input
                      type="radio"
                      :name="`correct-${qIdx}`"
                      :checked="opcao.isCorrect"
                      @change="setCorrectOption(qIdx, oIdx)"
                    />
                    <input
                      v-model="opcao.text"
                      type="text"
                      class="input opcao-text"
                      placeholder="Texto da opção"
                    />
                    <input
                      v-model="opcao.rationale"
                      type="text"
                      class="input opcao-rationale"
                      placeholder="Racional (feedback)"
                    />
                    <button
                      type="button"
                      class="btn-ghost btn-sm"
                      :disabled="questao.opcoes.length <= 2"
                      @click="removeOpcao(qIdx, oIdx)"
                    >
                      ×
                    </button>
                  </div>
                  <button type="button" class="btn-ghost btn-sm add-opcao" @click="addOpcao(qIdx)">
                    + Opção
                  </button>
                </div>
              </div>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn-secondary" @click="closeModal">Cancelar</button>
            <button type="button" class="btn-primary" :disabled="modalSaving" @click="saveModal">
              {{ modalSaving ? 'Salvando…' : (modalMode === 'create' ? 'Criar' : 'Salvar') }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.quiz-page {
  max-width: 1000px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 28px;
}

.page-title {
  font-family: var(--serif);
  font-size: 28px;
  color: var(--k0);
  margin-bottom: 4px;
}

.page-sub {
  font-size: 14px;
  color: var(--k5);
  margin-bottom: 16px;
}

.page-actions {
  display: flex;
  gap: 12px;
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

.empty strong {
  color: var(--k0);
}

.grouped-quizzes {
  display: flex;
  flex-direction: column;
  gap: 32px;
}

.trilha-section {
  margin: 0;
}

.trilha-section-title {
  font-family: var(--serif);
  font-size: 18px;
  font-weight: 600;
  color: var(--k0);
  margin: 0 0 16px 0;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--bd2);
}

.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
}

.quiz-card {
  background: var(--wh);
  border: 1px solid var(--bd);
  border-radius: 12px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  transition: box-shadow 0.2s ease, border-color 0.2s ease;
}

.quiz-card:hover {
  box-shadow: 0 4px 16px rgba(12, 35, 64, 0.08);
  border-color: var(--goldbd);
}

.quiz-card-header {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.quiz-title {
  font-family: var(--serif);
  font-size: 18px;
  font-weight: 600;
  color: var(--k0);
  margin: 0;
  line-height: 1.3;
}

.quiz-meta {
  font-size: 12px;
  color: var(--k5);
}

.quiz-card-actions {
  margin-top: auto;
}

.btn-primary,
.btn-secondary,
.btn-danger,
.btn-ghost {
  padding: 10px 18px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  border: 1px solid transparent;
  transition: background 0.15s ease, color 0.15s ease, border-color 0.15s ease;
}

.btn-primary {
  background: var(--k0);
  color: var(--wh);
}

.btn-primary:hover:not(:disabled) {
  background: #132d52;
}

.btn-primary:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.btn-secondary {
  background: var(--wh);
  color: var(--k0);
  border-color: var(--bd);
}

.btn-secondary:hover {
  background: var(--k8);
}

.btn-ghost {
  background: transparent;
  color: var(--k5);
  border: none;
}

.btn-ghost:hover:not(:disabled) {
  background: var(--k8);
  color: var(--k0);
}

.btn-ghost:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-sm {
  padding: 6px 12px;
  font-size: 13px;
}

/* Modal */
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 24px;
}

.modal-box {
  background: var(--wh);
  border-radius: 12px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
  max-width: 640px;
  width: 100%;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
}

.modal-quiz {
  max-width: 720px;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid var(--bd2);
}

.modal-header h2 {
  font-family: var(--serif);
  font-size: 20px;
  font-weight: 600;
  margin: 0;
  color: var(--k0);
}

.modal-close {
  width: 36px;
  height: 36px;
  border: none;
  background: none;
  font-size: 24px;
  line-height: 1;
  color: var(--k5);
  cursor: pointer;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.modal-close:hover {
  background: var(--k8);
  color: var(--k0);
}

.modal-body {
  padding: 24px;
  overflow-y: auto;
  flex: 1;
}

.modal-error {
  padding: 12px 14px;
  background: #fdecec;
  color: #8f2b2b;
  border-radius: 8px;
  font-size: 14px;
  margin-bottom: 16px;
}

.form-row {
  display: flex;
  gap: 16px;
  align-items: flex-start;
}

.form-row .flex-1 {
  flex: 1;
}

.form-group {
  margin-bottom: 18px;
}

.form-group label,
.section-label {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: var(--k0);
  margin-bottom: 6px;
}

.form-hint {
  display: block;
  font-size: 12px;
  color: var(--k5);
  margin-top: 4px;
}

.input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--bd);
  border-radius: 8px;
  font-size: 14px;
  font-family: inherit;
}

.input-num {
  width: 100px;
}

.select {
  cursor: pointer;
  appearance: auto;
}

.input:read-only {
  background: var(--k8);
  color: var(--k4);
}

.textarea {
  resize: vertical;
  min-height: 60px;
}

.questoes-section {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid var(--bd2);
}

.questoes-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.questao-block {
  background: var(--k8);
  border-radius: 10px;
  padding: 16px;
  margin-bottom: 16px;
}

.questao-block .form-group {
  margin-bottom: 12px;
}

.questao-block .form-group:last-child {
  margin-bottom: 0;
}

.questao-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.questao-num {
  font-size: 13px;
  font-weight: 600;
  color: var(--k0);
}

.opcoes-list {
  margin-top: 12px;
}

.opcoes-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--k4);
  margin-bottom: 8px;
  display: block;
}

.opcao-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.opcao-row input[type='radio'] {
  flex-shrink: 0;
}

.opcao-text {
  flex: 1;
  min-width: 0;
}

.opcao-rationale {
  flex: 1;
  min-width: 0;
  font-size: 13px;
}

.add-opcao {
  margin-top: 4px;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 24px;
  border-top: 1px solid var(--bd2);
}
</style>
