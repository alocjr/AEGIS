<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import { fetchUserCourseAndProgress, liberarEncontro, updateUserProgress } from '@/api/admin'

const route = useRoute()
const userId = computed(() => route.params.userId as string)

const loading = ref(true)
const error = ref<string | null>(null)
const data = ref<Awaited<ReturnType<typeof fetchUserCourseAndProgress>> | null>(null)
const liberandoId = ref<number | null>(null)
/** Datas dos encontros em edição (encontro_id -> ISO ou '') */
const agendaEdit = ref<Record<string, string>>({})
const agendaSaving = ref(false)
const agendaSaveError = ref<string | null>(null)

function pct(done: number, total: number): number {
  if (total <= 0) return 0
  return Math.min(100, Math.round((done / total) * 100))
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString('pt-BR', {
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

/** Converte ISO para valor de input datetime-local (horário local) */
function isoToDatetimeLocal(iso: string): string {
  if (!iso || !iso.trim()) return ''
  try {
    const d = new Date(iso)
    if (isNaN(d.getTime())) return ''
    const y = d.getFullYear()
    const m = String(d.getMonth() + 1).padStart(2, '0')
    const day = String(d.getDate()).padStart(2, '0')
    const h = String(d.getHours()).padStart(2, '0')
    const min = String(d.getMinutes()).padStart(2, '0')
    return `${y}-${m}-${day}T${h}:${min}`
  } catch {
    return ''
  }
}

/** Converte valor de input datetime-local para ISO */
function datetimeLocalToIso(local: string): string {
  if (!local || !local.trim()) return ''
  try {
    return new Date(local).toISOString()
  } catch {
    return ''
  }
}

const progress = computed(() => data.value?.progress ?? null)
const encontrosDone = computed(() => progress.value?.concluidos_efetivos?.length ?? 0)
const encontrosTotal = computed(() => progress.value?.total ?? 0)

interface EncontroItem {
  id: number
  titulo: string
  semana: number
}
const todosEncontros = computed<EncontroItem[]>(() => {
  const pfe = data.value?.programa_formacao_executiva as { jornada_aprendizagem?: { semana: number; encontros?: { id: number; titulo?: string }[] }[] } | undefined
  const jornada = pfe?.jornada_aprendizagem ?? []
  const list: EncontroItem[] = []
  for (const sem of jornada) {
    for (const enc of sem.encontros ?? []) {
      const id = typeof enc.id === 'number' ? enc.id : parseInt(String(enc.id), 10)
      if (!isNaN(id)) {
        list.push({
          id,
          titulo: enc.titulo ?? `Encontro ${id}`,
          semana: sem.semana ?? 0,
        })
      }
    }
  }
  return list.sort((a, b) => a.id - b.id)
})

const liberados = computed(() => new Set(progress.value?.encontros_liberados ?? []))
const concluidosEfetivos = computed(() => new Set(progress.value?.concluidos_efetivos ?? []))
const encontroConclusoes = computed(() => progress.value?.encontro_conclusoes ?? {})
const materialChecks = computed(() => progress.value?.material_checks ?? {})
const materiaisPorEncontro = computed(() => data.value?.materiais_por_encontro ?? {})
const quizPorEncontro = computed(() => data.value?.quiz_por_encontro ?? {})

const encontrosLiberados = computed(() => {
  return todosEncontros.value
    .filter((enc) => liberados.value.has(enc.id))
    .map((enc) => {
      const eid = String(enc.id)
      const concluido = concluidosEfetivos.value.has(enc.id)
      const conclusaoIso = encontroConclusoes.value[eid]
      const materiaisMarcados = Object.keys(materialChecks.value[eid] ?? {}).length
      const materiaisTotal = materiaisPorEncontro.value[eid] ?? 0
      const materiaisPct = materiaisTotal > 0 ? pct(materiaisMarcados, materiaisTotal) : 0
      const quiz = quizPorEncontro.value[eid] ?? { tem_quiz: false, respondido: false }
      const quizScore = quiz.score ?? 0
      const quizTotal = quiz.total ?? 0
      const quizPct = quizTotal > 0 ? pct(quizScore, quizTotal) : 0
      return {
        ...enc,
        concluido,
        conclusaoIso: conclusaoIso ?? null,
        materiaisMarcados,
        materiaisTotal,
        materiaisPct,
        quizTem: quiz.tem_quiz,
        quizRespondido: quiz.respondido,
        quizScore,
        quizTotal,
        quizPct,
      }
    })
})

/** Totais gerais: materiais e quiz (para resumo no topo) */
const totaisMateriais = computed(() => {
  let marcados = 0
  let total = 0
  for (const enc of encontrosLiberados.value) {
    marcados += enc.materiaisMarcados
    total += enc.materiaisTotal
  }
  return { marcados, total, pct: total > 0 ? pct(marcados, total) : 0 }
})
const totaisQuiz = computed(() => {
  const comQuiz = encontrosLiberados.value.filter((e) => e.quizTem)
  const respondidos = comQuiz.filter((e) => e.quizRespondido)
  const totalPerguntas = respondidos.reduce((s, e) => s + e.quizTotal, 0)
  const totalAcertos = respondidos.reduce((s, e) => s + e.quizScore, 0)
  return {
    sessoesTotal: comQuiz.length,
    sessoesExecutadas: respondidos.length,
    perguntasRespondidas: totalPerguntas,
    acertos: totalAcertos,
    pctAcertos: totalPerguntas > 0 ? pct(totalAcertos, totalPerguntas) : 0,
  }
})

const encontrosNaoLiberados = computed(() =>
  todosEncontros.value.filter((enc) => !liberados.value.has(enc.id))
)

async function loadData() {
  if (!userId.value) return
  try {
    data.value = await fetchUserCourseAndProgress(userId.value)
    error.value = null
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Erro ao carregar progresso.'
  } finally {
    loading.value = false
  }
}

async function onLiberar(encontroId: number) {
  if (!userId.value) return
  liberandoId.value = encontroId
  try {
    await liberarEncontro(userId.value, encontroId)
    await loadData()
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Erro ao liberar encontro.'
  } finally {
    liberandoId.value = null
  }
}

/** Sincroniza agendaEdit com os encontros e dados atuais */
function syncAgendaEdit() {
  const prog = data.value?.progress?.encontro_agendas ?? {}
  const next: Record<string, string> = {}
  todosEncontros.value.forEach((enc) => {
    next[String(enc.id)] = prog[String(enc.id)] ?? ''
  })
  agendaEdit.value = next
}

watch(
  () => [data.value, todosEncontros.value] as const,
  () => syncAgendaEdit(),
  { immediate: true }
)

async function saveAgenda() {
  if (!userId.value || !data.value?.course_slug) return
  agendaSaveError.value = null
  agendaSaving.value = true
  try {
    const agendas: Record<string, string> = {}
    for (const [encId, val] of Object.entries(agendaEdit.value)) {
      const v = typeof val === 'string' ? val.trim() : ''
      if (v) agendas[encId] = v
    }
    await updateUserProgress(userId.value, data.value.course_slug, agendas)
    await loadData()
  } catch (e) {
    agendaSaveError.value = e instanceof Error ? e.message : 'Erro ao salvar datas.'
  } finally {
    agendaSaving.value = false
  }
}

function onAgendaInput(encId: number, datetimeLocal: string) {
  const next = { ...agendaEdit.value }
  next[String(encId)] = datetimeLocal.trim() ? datetimeLocalToIso(datetimeLocal) : ''
  agendaEdit.value = next
}

onMounted(() => loadData())
</script>

<template>
  <div class="progresso-aluno">
    <nav class="breadcrumb">
      <RouterLink to="/admin">Dashboard</RouterLink>
      <span>/</span>
      <span>Progresso · {{ data?.user?.name ?? 'Aluno' }}</span>
    </nav>

    <div v-if="loading" class="loading">Carregando...</div>
    <div v-else-if="error" class="error-msg">{{ error }}</div>

    <template v-else-if="data">
      <div class="card-header">
        <h1 class="card-name">{{ data.user.name }}</h1>
        <a :href="`mailto:${data.user.email}`" class="card-email">{{ data.user.email }}</a>
        <div class="card-trilha">{{ data.course_slug || '—' }}</div>
      </div>

      <div class="card-progress">
        <div class="progress-row">
          <span class="progress-label">Encontros</span>
          <div class="progress-bar-wrap">
            <div
              class="progress-bar-fill"
              :style="{ width: pct(encontrosDone, encontrosTotal) + '%' }"
            />
          </div>
          <span class="progress-pct">{{ encontrosDone }}/{{ encontrosTotal }}</span>
        </div>
        <div class="progress-row progress-row--full" v-if="progress?.encontros_liberados?.length">
          <span class="progress-label">Encontros liberados</span>
          <span class="progress-val">{{ progress.encontros_liberados.join(', ') }}</span>
        </div>
      </div>

      <div class="resumo-cards">
        <div class="resumo-card resumo-card--materiais">
          <div class="resumo-card-header">
            <span class="resumo-card-title">Materiais checkados</span>
            <span class="resumo-card-pct">{{ totaisMateriais.pct }}%</span>
          </div>
          <div class="resumo-bar-wrap">
            <div class="resumo-bar-fill" :style="{ width: totaisMateriais.pct + '%' }" />
          </div>
          <div class="resumo-card-detail">
            <span class="resumo-card-nums">{{ totaisMateriais.marcados }}/{{ totaisMateriais.total }}</span>
            <span class="resumo-card-desc">materiais marcados no total</span>
          </div>
        </div>
        <div class="resumo-card resumo-card--quiz">
          <div class="resumo-card-header">
            <span class="resumo-card-title">Quiz</span>
            <span class="resumo-card-pct" v-if="totaisQuiz.perguntasRespondidas > 0">{{ totaisQuiz.pctAcertos }}%</span>
            <span class="resumo-card-pct resumo-card-pct--muted" v-else>—</span>
          </div>
          <div class="resumo-bar-wrap resumo-bar-wrap--quiz">
            <div class="resumo-bar-fill resumo-bar-fill--quiz" :style="{ width: (totaisQuiz.perguntasRespondidas ? totaisQuiz.pctAcertos : 0) + '%' }" />
          </div>
          <div class="resumo-card-detail">
            <span class="resumo-card-nums">{{ totaisQuiz.sessoesExecutadas }}/{{ totaisQuiz.sessoesTotal }} sessões</span>
            <span class="resumo-card-desc" v-if="totaisQuiz.perguntasRespondidas > 0">
              {{ totaisQuiz.acertos }}/{{ totaisQuiz.perguntasRespondidas }} acertos
            </span>
            <span class="resumo-card-desc" v-else>Nenhuma pergunta respondida</span>
          </div>
        </div>
      </div>

      <div v-if="encontrosLiberados.length > 0" class="enc-section enc-section--liberados">
        <h2 class="sec-title">Encontros liberados</h2>
        <p class="sec-desc">Progresso do aluno em cada encontro liberado.</p>
        <ul class="enc-list enc-list--progress">
          <li
            v-for="enc in encontrosLiberados"
            :key="enc.id"
            class="enc-item enc-item--liberado"
          >
            <div class="enc-info">
              <span class="enc-num">Encontro {{ enc.id }}</span>
              <span class="enc-titulo">{{ enc.titulo }}</span>
              <span class="enc-semana" v-if="enc.semana">Semana {{ enc.semana }}</span>
            </div>
            <div class="enc-progress">
              <div class="enc-status-badge" :class="enc.concluido ? 'enc-status-badge--done' : 'enc-status-badge--pending'">
                <span v-if="enc.concluido">✓ Concluído</span>
                <span v-else>Em andamento</span>
                <span class="enc-status-date" v-if="enc.conclusaoIso">{{ formatDate(enc.conclusaoIso) }}</span>
              </div>
              <div class="enc-detalhes">
                <div class="enc-bloco enc-bloco--materiais">
                  <div class="enc-bloco-header">
                    <span class="enc-bloco-label">Materiais</span>
                    <span class="enc-bloco-val">{{ enc.materiaisMarcados }}/{{ enc.materiaisTotal }}</span>
                  </div>
                  <div class="enc-bar-wrap">
                    <div
                      class="enc-bar-fill enc-bar-fill--materiais"
                      :style="{ width: enc.materiaisPct + '%' }"
                    />
                  </div>
                  <span class="enc-bloco-pct">{{ enc.materiaisPct }}%</span>
                </div>
                <div class="enc-bloco enc-bloco--quiz">
                  <div class="enc-bloco-header">
                    <span class="enc-bloco-label">Quiz</span>
                    <span v-if="!enc.quizTem" class="enc-bloco-val enc-bloco-val--muted">—</span>
                    <span v-else-if="enc.quizRespondido" class="enc-bloco-val">
                      <template v-if="enc.quizTotal > 0">{{ enc.quizScore }}/{{ enc.quizTotal }} ({{ enc.quizPct }}%)</template>
                      <template v-else>Concluído</template>
                    </span>
                    <span v-else class="enc-bloco-val enc-bloco-val--pending">Pendente</span>
                  </div>
                  <template v-if="enc.quizTem && enc.quizRespondido && enc.quizTotal > 0">
                    <div class="enc-bar-wrap enc-bar-wrap--quiz">
                      <div
                        class="enc-bar-fill enc-bar-fill--quiz"
                        :style="{ width: enc.quizPct + '%' }"
                      />
                    </div>
                    <span class="enc-bloco-pct">{{ enc.quizPct }}% acertos</span>
                  </template>
                  <template v-else-if="enc.quizTem && enc.quizRespondido">
                    <span class="enc-bloco-pct">Concluído</span>
                  </template>
                </div>
              </div>
            </div>
          </li>
        </ul>
      </div>

      <div v-if="encontrosNaoLiberados.length > 0" class="enc-section">
        <h2 class="sec-title">Encontros não liberados</h2>
        <p class="sec-desc">Libere os encontros para o aluno acessar o conteúdo no programa.</p>
        <ul class="enc-list">
          <li
            v-for="enc in encontrosNaoLiberados"
            :key="enc.id"
            class="enc-item"
          >
            <div class="enc-info">
              <span class="enc-num">Encontro {{ enc.id }}</span>
              <span class="enc-titulo">{{ enc.titulo }}</span>
              <span class="enc-semana" v-if="enc.semana">Semana {{ enc.semana }}</span>
            </div>
            <button
              type="button"
              class="btn-liberar"
              :disabled="liberandoId === enc.id"
              @click="onLiberar(enc.id)"
            >
              {{ liberandoId === enc.id ? 'Liberando…' : 'Liberar' }}
            </button>
          </li>
        </ul>
      </div>

      <div v-if="todosEncontros.length > 0" class="agenda-section">
        <h2 class="sec-title">Agenda (datas dos encontros)</h2>
        <p class="sec-desc">Defina a data e hora de cada encontro. O aluno verá essas datas na tela Agenda e poderá exportar para o Google Calendar.</p>
        <div class="agenda-list agenda-list--edit">
          <div
            v-for="enc in todosEncontros"
            :key="enc.id"
            class="agenda-item agenda-item--edit"
          >
            <div class="agenda-item-info">
              <span class="agenda-num">Encontro {{ enc.id }}</span>
              <span class="agenda-titulo">{{ enc.titulo }}</span>
            </div>
            <div class="agenda-item-field">
              <input
                type="datetime-local"
                :value="isoToDatetimeLocal(agendaEdit[String(enc.id)] ?? '')"
                @input="onAgendaInput(enc.id, ($event.target as HTMLInputElement).value)"
                class="agenda-input"
              />
            </div>
          </div>
        </div>
        <div v-if="agendaSaveError" class="agenda-save-error">{{ agendaSaveError }}</div>
        <button
          type="button"
          class="btn-salvar-agenda"
          :disabled="agendaSaving"
          @click="saveAgenda"
        >
          {{ agendaSaving ? 'Salvando…' : 'Salvar datas' }}
        </button>
      </div>

      <div class="actions">
        <RouterLink to="/admin" class="btn-back">← Voltar ao Dashboard</RouterLink>
      </div>
    </template>
  </div>
</template>

<style scoped>
.progresso-aluno {
  max-width: 720px;
  margin: 0 auto;
}
.breadcrumb {
  font-size: 13px;
  color: var(--k5);
  margin-bottom: 20px;
}
.breadcrumb a {
  color: var(--gold2);
}
.breadcrumb a:hover {
  text-decoration: underline;
}
.loading,
.error-msg {
  padding: 40px 0;
  color: var(--k5);
}
.error-msg {
  color: #8f2b2b;
}

.card-header {
  background: var(--k0);
  color: var(--wh);
  padding: 24px;
  border-radius: 8px;
  margin-bottom: 20px;
}
.card-name {
  font-family: var(--serif);
  font-size: 22px;
  margin: 0 0 6px 0;
}
.card-email {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.85);
  text-decoration: none;
  display: block;
  margin-bottom: 8px;
}
.card-email:hover {
  color: var(--gold2);
}
.card-trilha {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--gold2);
}
.card-progress {
  background: var(--wh);
  border: 1px solid var(--bd);
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 20px;
}
.progress-row {
  display: grid;
  grid-template-columns: 140px 1fr 48px;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}
.progress-row:last-child {
  margin-bottom: 0;
}
.progress-row--full {
  grid-template-columns: 140px 1fr;
}
.progress-val {
  font-size: 12px;
  color: var(--k3);
}
.progress-label {
  font-size: 12px;
  color: var(--k5);
}
.progress-bar-wrap {
  height: 8px;
  background: var(--k8);
  border-radius: 4px;
  overflow: hidden;
}
.progress-bar-fill {
  height: 100%;
  background: var(--k0);
  border-radius: 4px;
  transition: width 0.25s ease;
}
.progress-pct {
  font-size: 12px;
  color: var(--k5);
  text-align: right;
}

.resumo-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 20px;
  margin-bottom: 24px;
}
.resumo-card {
  background: var(--wh);
  border: 1px solid var(--bd);
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 1px 3px rgba(12, 35, 64, 0.04);
}
.resumo-card-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 12px;
}
.resumo-card-title {
  font-size: 13px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--k4);
}
.resumo-card-pct {
  font-size: 20px;
  font-weight: 700;
  color: var(--k0);
}
.resumo-card-pct--muted {
  font-size: 14px;
  font-weight: 500;
  color: var(--k5);
}
.resumo-bar-wrap {
  height: 10px;
  background: var(--k8);
  border-radius: 6px;
  overflow: hidden;
  margin-bottom: 10px;
}
.resumo-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--k0), #1a3a5c);
  border-radius: 6px;
  transition: width 0.35s ease;
}
.resumo-bar-wrap--quiz .resumo-bar-fill,
.resumo-bar-fill--quiz {
  background: linear-gradient(90deg, var(--gold), var(--gold2));
}
.resumo-card-detail {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.resumo-card-nums {
  font-size: 15px;
  font-weight: 600;
  color: var(--k0);
}
.resumo-card-desc {
  font-size: 12px;
  color: var(--k5);
}

.enc-section {
  background: var(--wh);
  border: 1px solid var(--bd);
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 20px;
}
.enc-section--liberados {
  margin-bottom: 24px;
}
.enc-list--progress .enc-item {
  background: var(--wh);
  border: 1px solid var(--bd);
  border-radius: 10px;
  margin-bottom: 12px;
  padding: 16px 20px;
  box-shadow: 0 1px 2px rgba(12, 35, 64, 0.04);
}
.enc-list--progress .enc-item:last-child {
  margin-bottom: 0;
}
.enc-item--liberado {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 16px;
}
.enc-info {
  min-width: 0;
  flex: 1 1 200px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.enc-progress {
  flex: 1 1 280px;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 14px;
  align-items: flex-end;
}
.enc-status-badge {
  font-size: 13px;
  font-weight: 600;
  padding: 6px 12px;
  border-radius: 8px;
  display: inline-flex;
  flex-direction: column;
  gap: 2px;
  align-items: flex-end;
}
.enc-status-badge--done {
  background: var(--green-done-row);
  color: var(--success);
  border: 1px solid var(--green-done-bd);
}
.enc-status-badge--pending {
  background: var(--warnBg);
  color: var(--warn);
  border: 1px solid rgba(193, 122, 44, 0.3);
}
.enc-status-date {
  font-size: 11px;
  font-weight: 400;
  color: var(--k5);
}
.enc-detalhes {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px 24px;
  width: 100%;
  max-width: 360px;
}
@media (max-width: 520px) {
  .enc-detalhes {
    grid-template-columns: 1fr;
  }
}
.enc-bloco {
  background: var(--k9);
  border-radius: 8px;
  padding: 12px;
  border: 1px solid var(--bd2);
}
.enc-bloco-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 8px;
}
.enc-bloco-label {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--k5);
}
.enc-bloco-val {
  font-size: 13px;
  font-weight: 600;
  color: var(--k0);
}
.enc-bloco-val--muted {
  color: var(--k5);
  font-weight: 500;
}
.enc-bloco-val--pending {
  color: var(--warn);
}
.enc-bar-wrap {
  height: 8px;
  background: var(--k8);
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 6px;
}
.enc-bar-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.3s ease;
}
.enc-bar-fill--materiais {
  background: linear-gradient(90deg, var(--k0), #1a3a5c);
}
.enc-bar-fill--quiz {
  background: linear-gradient(90deg, var(--gold), var(--gold2));
}
.enc-bar-wrap--quiz {
  margin-bottom: 6px;
}
.enc-bloco-pct {
  font-size: 11px;
  font-weight: 600;
  color: var(--k4);
}
.sec-title {
  font-size: 16px;
  margin: 0 0 8px 0;
  color: var(--k0);
}
.sec-desc {
  font-size: 13px;
  color: var(--k5);
  margin-bottom: 14px;
}
.enc-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 1px;
  border: 1px solid var(--bd);
  border-radius: 6px;
  overflow: hidden;
}
.enc-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 16px;
  background: var(--k9);
}
.enc-num {
  font-size: 12px;
  font-weight: 600;
  color: var(--k5);
}
.enc-titulo {
  font-size: 14px;
  color: var(--k0);
}
.enc-semana {
  font-size: 12px;
  color: var(--k5);
}
.btn-liberar {
  flex-shrink: 0;
  height: 36px;
  padding: 0 18px;
  border: 1px solid var(--k0);
  background: var(--k0);
  color: var(--wh);
  font-size: 13px;
  font-weight: 600;
  border-radius: 4px;
  cursor: pointer;
}
.btn-liberar:hover:not(:disabled) {
  opacity: 0.9;
}
.btn-liberar:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.agenda-section {
  background: var(--wh);
  border: 1px solid var(--bd);
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 20px;
}
.agenda-section .sec-title {
  margin: 0 0 8px 0;
}
.agenda-section .sec-desc {
  font-size: 13px;
  color: var(--k5);
  margin: 0 0 16px 0;
}
.agenda-list {
  display: flex;
  flex-direction: column;
  gap: 1px;
  border: 1px solid var(--bd);
  border-radius: 6px;
  overflow: hidden;
}
.agenda-list--edit {
  margin-bottom: 16px;
}
.agenda-item {
  display: flex;
  justify-content: space-between;
  padding: 12px 14px;
  background: var(--k9);
}
.agenda-item--edit {
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}
.agenda-item-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}
.agenda-num {
  font-weight: 600;
  color: var(--k0);
}
.agenda-titulo {
  font-size: 12px;
  color: var(--k5);
}
.agenda-item-field {
  flex-shrink: 0;
}
.agenda-input {
  font-size: 13px;
  padding: 8px 10px;
  border: 1px solid var(--bd);
  border-radius: 4px;
  background: var(--wh);
  color: var(--k0);
  min-width: 180px;
}
.agenda-input:focus {
  outline: none;
  border-color: var(--gold);
}
.agenda-save-error {
  font-size: 13px;
  color: #8f2b2b;
  margin-bottom: 10px;
}
.btn-salvar-agenda {
  font-size: 13px;
  font-weight: 600;
  padding: 10px 20px;
  background: var(--k0);
  color: var(--wh);
  border: none;
  border-radius: 6px;
  cursor: pointer;
}
.btn-salvar-agenda:hover:not(:disabled) {
  opacity: 0.9;
}
.btn-salvar-agenda:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}
.agenda-date {
  font-size: 13px;
  color: var(--k5);
}
.actions {
  padding-top: 8px;
}
.btn-back {
  font-size: 14px;
  color: var(--k0);
  text-decoration: none;
}
.btn-back:hover {
  text-decoration: underline;
}
</style>
