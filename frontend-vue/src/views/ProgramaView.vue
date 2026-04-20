<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { fetchCurrentCourse } from '@/api/course'
import { updateMaterialCheck, completeEncontro } from '@/api/progress'
import { useAuthStore } from '@/stores/auth'
import type { CurrentCourseResponse } from '@/api/course'
import type {
  Encontro,
  JornadaSemana,
  MaterialSuporte,
  ProgramaFormacaoExecutiva,
  EstruturaEncontro,
  EntregavelResumo,
} from '@/types'

const ROMANOS = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X', 'XI', 'XII', 'XIII', 'XIV', 'XV']

function romano(n: number): string {
  return ROMANOS[n - 1] ?? String(n)
}

function isExternalUrl(url?: string): boolean {
  return !!(url && (url.startsWith('http://') || url.startsWith('https://')))
}

function parseMatItem(item: string): { tipo: string; nome: string } {
  const i = item.indexOf(':')
  if (i < 0) return { tipo: 'Material', nome: item.trim() }
  return { tipo: item.slice(0, i).trim(), nome: item.slice(i + 1).trim() }
}

const auth = useAuthStore()
const loading = ref(true)
const error = ref<string | null>(null)
const data = ref<CurrentCourseResponse | null>(null)
const expandedId = ref<number | null>(null)
const expandedSemana = ref<number | null>(null)
const completingId = ref<number | null>(null)
const materialToggling = ref<string | null>(null)
const selectingAllId = ref<number | null>(null)
const hoverStep = ref<{ enc: Encontro; semana: number } | null>(null)

const programa = computed<ProgramaFormacaoExecutiva | undefined>(() => {
  const p = data.value?.programa_formacao_executiva
  return p as ProgramaFormacaoExecutiva | undefined
})

const progress = computed(() => data.value?.progress ?? null)

const liberados = computed(() => progress.value?.encontros_liberados ?? [1])

const concluidosEfetivos = computed(() => progress.value?.concluidos_efetivos ?? [])

const ativoEfetivo = computed(() => progress.value?.ativo_efetivo ?? 1)

const materialChecks = computed(() => progress.value?.material_checks ?? {})
const quizPorEncontro = computed(() => progress.value?.quiz_por_encontro ?? {})

const jornada = computed(() => programa.value?.jornada_aprendizagem ?? [])

const totalEncontros = computed(() =>
  jornada.value.reduce((acc, sem) => acc + (sem.encontros?.length ?? 0), 0)
)

const numSemanas = computed(() => jornada.value.length)

const metodologia = computed(() => programa.value?.metodologia_detalhada)

const entregaveisResumo = computed(() => programa.value?.entregaveis_resumo ?? [])

type EncStatus = 'done' | 'active' | 'locked'

const instSteps = computed(() =>
  (jornada.value ?? []).flatMap((sem) =>
    (sem.encontros ?? []).map((enc) => ({ semana: sem.semana, enc }))
  )
)

/** Status do encontro: usa encontros_liberados para definir o que está acessível (check de materiais e Quiz). */
function statusEnc(enc: Encontro): EncStatus {
  if (concluidosEfetivos.value.includes(enc.id)) return 'done'
  if (liberados.value.includes(enc.id)) return 'active'
  return 'locked'
}

function isLiberado(enc: Encontro): boolean {
  return liberados.value.includes(enc.id)
}

function isConcluido(enc: Encontro): boolean {
  return concluidosEfetivos.value.includes(enc.id)
}

function podeClicarConcluir(enc: Encontro): boolean {
  const materiaisOk = (enc.material_suporte ?? []).length <= Object.keys(materialChecks.value[String(enc.id)] ?? {}).length
  return materiaisOk
}

/** Apenas o encontro ativo é editável (marcar/desmarcar materiais, concluir). */
function isEncontroEditavel(enc: Encontro): boolean {
  return statusEnc(enc) === 'active'
}

/** Encontros ativo ou concluído: mesma aparência (fundo claro) e permitem abrir links e quiz. */
function isEncontroAcessivel(enc: Encontro): boolean {
  return statusEnc(enc) === 'active' || statusEnc(enc) === 'done'
}

const progressPct = computed(() => {
  const done = concluidosEfetivos.value.length
  const tot = (progress.value?.total ?? totalEncontros.value) || 1
  return tot ? Math.round((done / tot) * 100) : 0
})

const sidebarFacts = computed(() => {
  const done = concluidosEfetivos.value.length
  const tot = progress.value?.total ?? totalEncontros.value
  return [
    [numSemanas.value + ' sem.', 'Duração', ''],
    ['2x/sem.', 'Frequência', ''],
    [done + '/' + tot, 'Progresso', 'g'],
    [entregaveisResumo.value.length, 'Entregáveis', ''],
  ]
})

const nextEncontro = computed(() => {
  let found: { enc: Encontro; sem: number } | null = null
  for (const sem of jornada.value) {
    for (const enc of sem.encontros ?? []) {
      if (enc.id === ativoEfetivo.value) {
        found = { enc, sem: sem.semana }
        break
      }
    }
    if (found) break
  }
  return found
})

const metricsRows = computed(() => {
  const done = concluidosEfetivos.value.length
  const tot = (progress.value?.total ?? totalEncontros.value) || 1
  const pctAll = Math.round((done / tot) * 100)
  const semAtual = Math.ceil(ativoEfetivo.value / 2)
  let pctSem = 0
  const sem = jornada.value.find((s) => s.semana === semAtual)
  if (sem?.encontros) {
    let totalMat = 0
    let doneMat = 0
    for (const enc of sem.encontros) {
      const n = (enc.material_suporte ?? []).length
      totalMat += n
      const encChecks = materialChecks.value[String(enc.id)] ?? {}
      for (let i = 0; i < n; i++) if (encChecks[String(i)]) doneMat += 1
    }
    pctSem = totalMat > 0 ? Math.round((doneMat / totalMat) * 100) : 0
  }
  return [
    { lbl: 'Programa', pct: pctAll, color: 'var(--gold)' },
    { lbl: 'Semana ' + semAtual, pct: pctSem, color: 'rgba(255,255,255,.45)' },
  ]
})

const ribbonShow = ref(false)
const ribbonMsg = ref('')

function jumpTo(encId: number) {
  const el = document.getElementById(`enc${encId}`)
  if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

/** Apenas uma semana pode estar aberta no menu; ao abrir outra, esta fecha. */
function toggleNavCh(semana: number) {
  expandedSemana.value = expandedSemana.value === semana ? null : semana
}

function isMaterialChecked(encId: number, matIndex: number): boolean {
  const enc = materialChecks.value[String(encId)]
  return enc ? Object.prototype.hasOwnProperty.call(enc, String(matIndex)) : false
}

function allMateriaisChecked(enc: Encontro): boolean {
  const total = (enc.material_suporte ?? []).length
  if (total === 0) return false
  const checks = materialChecks.value[String(enc.id)] ?? {}
  return Object.keys(checks).length >= total
}

async function onSelectAllMateriais(enc: Encontro) {
  const materials = enc.material_suporte ?? []
  if (materials.length === 0) return
  selectingAllId.value = enc.id
  const checkAll = !allMateriaisChecked(enc)
  const slug = auth.currentCourseSlug ?? undefined
  try {
    for (let i = 0; i < materials.length; i++) {
      await updateMaterialCheck({ encontro_id: enc.id, material_index: i, checked: checkAll, course_slug: slug })
    }
    await loadProgram()
  } catch {
    await loadProgram()
  } finally {
    selectingAllId.value = null
  }
}

function entregavelParaEncontro(encId: number) {
  return entregaveisResumo.value.find((e) => e.origem === `Encontro ${encId}`)
}

function toggleExpand(enc: Encontro) {
  expandedId.value = expandedId.value === enc.id ? null : enc.id
}

async function onMaterialToggle(encId: number, matIndex: number, checked: boolean) {
  const key = `${encId}-${matIndex}`
  materialToggling.value = key
  const slug = auth.currentCourseSlug ?? undefined
  try {
    await updateMaterialCheck({ encontro_id: encId, material_index: matIndex, checked, course_slug: slug })
    await loadProgram()
  } catch {
    // revert would need local state; on next load it will be correct
  } finally {
    materialToggling.value = null
  }
}

async function onCompleteEncontro(encId: number) {
  completingId.value = encId
  try {
    await completeEncontro(encId, auth.currentCourseSlug ?? undefined)
    await loadProgram()
    expandedId.value = null
    ribbonMsg.value = 'Encontro concluído com sucesso. Progresso atualizado.'
    ribbonShow.value = true
    window.scrollTo({ top: 0, behavior: 'smooth' })
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Erro ao concluir encontro.'
  } finally {
    completingId.value = null
  }
}

async function loadProgram() {
  loading.value = true
  error.value = null
  try {
    data.value = await fetchCurrentCourse(auth.currentCourseSlug ?? undefined)
    if (expandedId.value === null && progress.value?.ativo_efetivo) {
      expandedId.value = progress.value.ativo_efetivo
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Erro ao carregar programa.'
    data.value = null
  } finally {
    loading.value = false
  }
}

onMounted(() => loadProgram())
</script>

<template>
  <div class="wrap">
    <div v-if="loading" class="loading"><div class="spin"></div><div>Carregando programa...</div></div>
    <div v-else-if="error" class="error-msg">{{ error }}</div>

    <template v-else-if="data && programa">
      <div class="shell">
        <aside class="sidebar">
          <div class="sb-top">
            <div class="sb-eyebrow">Programa em curso</div>
            <div class="sb-title">{{ (programa?.cabecalho?.titulo ?? '') + ' · ' + (programa?.cabecalho?.tema ?? '') }}</div>
            <div class="sb-prog">
              <div class="sb-prog-nums">
                <span class="sb-prog-big">{{ concluidosEfetivos.length }}</span>
                <span class="sb-prog-den">de {{ progress?.total ?? totalEncontros }} encontros</span>
              </div>
              <div class="sb-prog-track">
                <div class="sb-prog-fill" :style="{ width: progressPct + '%' }"></div>
              </div>
              <div class="sb-prog-note">{{ progressPct }}% concluído · {{ (progress?.total ?? totalEncontros) - concluidosEfetivos.length }} restantes</div>
            </div>
            <div class="sb-facts">
              <div v-for="(f, i) in sidebarFacts" :key="i" class="sb-fact">
                <span class="sb-fact-v" :class="f[2] ? ' g' : ''">{{ f[0] }}</span>
                <span class="sb-fact-k">{{ f[1] }}</span>
              </div>
            </div>
          </div>
          <nav class="sb-nav">
            <div
              v-for="sem in jornada"
              :key="sem.semana"
              class="nav-ch"
              :class="{ open: (expandedSemana ?? jornada[0]?.semana) === sem.semana }"
            >
              <div class="nav-ch-hd" @click="toggleNavCh(sem.semana)">
                <span class="nav-ch-n">S{{ sem.semana }}</span>
                <span class="nav-ch-nm">{{ sem.tema_central ?? '' }}</span>
                <div class="nav-arr">▶</div>
              </div>
              <div class="nav-ch-items">
                <div
                  v-for="enc in (sem.encontros ?? [])"
                  :key="enc.id"
                  class="nav-entry"
                  :class="{
                    done: statusEnc(enc) === 'done',
                    current: statusEnc(enc) === 'active',
                    locked: statusEnc(enc) === 'locked',
                  }"
                  @click="(statusEnc(enc) === 'done' || statusEnc(enc) === 'active') && jumpTo(enc.id)"
                >
                  <div class="ndot" :class="{
                    'nd-done': statusEnc(enc) === 'done',
                    'nd-cur': statusEnc(enc) === 'active',
                    'nd-lock': statusEnc(enc) === 'locked',
                  }">
                    <template v-if="statusEnc(enc) === 'done'">✓</template>
                    <template v-else-if="statusEnc(enc) === 'active'">•</template>
                  </div>
                  <span class="nav-entry-txt">{{ enc.titulo ?? '' }}</span>
                  <span class="nav-entry-num">{{ romano(enc.id) }}</span>
                </div>
              </div>
            </div>
          </nav>
          <div class="sb-bot">
            <div class="sb-next">
              <div class="sb-next-tag">Próximo Encontro</div>
              <div class="sb-next-title">{{ nextEncontro?.enc?.titulo ?? '-' }}</div>
              <div class="sb-next-meta">{{ nextEncontro ? 'Semana ' + nextEncontro.sem + ' · Encontro ' + romano(nextEncontro.enc.id) : '-' }}</div>
            </div>
          </div>
        </aside>

        <div class="main">
          <div class="ribbon" :class="{ show: ribbonShow }">
            <div class="ribbon-rule"></div>
            <span>{{ ribbonMsg }}</span>
            <button type="button" class="ribbon-close" aria-label="Fechar" @click="ribbonShow = false">×</button>
          </div>

          <section class="intro">
            <p class="intro-kicker">{{ programa?.cabecalho?.tema ?? '' }}</p>
            <h1 class="intro-h1">
              {{ programa?.cabecalho?.titulo ?? '' }}<br />
              <em>{{ programa?.cabecalho?.publico ?? '' }}</em>
            </h1>
            <p class="intro-sub">{{ programa?.cabecalho?.trilha ?? '' }}</p>
            <p class="intro-desc">{{ programa?.visao_geral?.objetivo ?? '' }}</p>
            <div class="kpis">
              <div class="kpi">
                <div class="kpi-v">{{ totalEncontros }}</div>
                <div class="kpi-k">Encontros</div>
              </div>
              <div class="kpi">
                <div class="kpi-v">{{ numSemanas }}</div>
                <div class="kpi-k">Semanas</div>
              </div>
              <div class="kpi">
                <div class="kpi-v g">{{ entregaveisResumo.length }}</div>
                <div class="kpi-k">Entregáveis</div>
              </div>
              <div class="kpi" v-if="programa?.cabecalho?.ano">
                <div class="kpi-v g">{{ programa.cabecalho.ano }}</div>
                <div class="kpi-k">Ano</div>
              </div>
            </div>
            <div v-if="programa?.visao_geral?.instrutor" class="inst-row">
              <div>
                <div class="inst-role">Facilitador</div>
                <div class="inst-name">{{ programa.visao_geral.instrutor }}</div>
                <div class="inst-separator"></div>
                <div class="inst-progress">
                  <div class="inst-progress-label">Progresso dos encontros</div>
                  <div class="inst-progress-track" aria-label="Linha do tempo dos encontros">
                    <button
                      v-for="step in instSteps"
                      :key="step.enc.id"
                      type="button"
                      class="inst-step"
                      :class="{
                        'inst-step--done': statusEnc(step.enc) === 'done',
                        'inst-step--active': statusEnc(step.enc) === 'active',
                        'inst-step--locked': statusEnc(step.enc) === 'locked',
                      }"
                      :title="`Semana ${step.semana} · ${(step.enc.titulo ?? `Encontro ${step.enc.id}`)}`"
                      @mouseenter="hoverStep = { enc: step.enc, semana: step.semana }"
                      @mouseleave="hoverStep = null"
                      @click="jumpTo(step.enc.id)"
                    >
                      <span class="inst-step-num">{{ romano(step.enc.id) }}</span>
                    </button>
                  </div>
                  <div v-if="hoverStep" class="inst-hover-card">
                    <div class="inst-hover-title">
                      Encontro {{ romano(hoverStep.enc.id) }} ·
                      {{ hoverStep.enc.titulo ?? `Encontro ${hoverStep.enc.id}` }}
                    </div>
                    <div class="inst-hover-meta">
                      Semana {{ hoverStep.semana }} ·
                      <span v-if="statusEnc(hoverStep.enc) === 'done'">Concluído</span>
                      <span v-else-if="statusEnc(hoverStep.enc) === 'active'">Em andamento</span>
                      <span v-else>Bloqueado</span>
                    </div>
                    <div v-if="hoverStep.enc.tema" class="inst-hover-desc">
                      {{ hoverStep.enc.tema }}
                    </div>
                  </div>
                  <div class="inst-progress-legend">
                    <span class="leg leg--done">Concluído</span>
                    <span class="leg leg--active">Em andamento</span>
                    <span class="leg leg--locked">Bloqueado</span>
                  </div>
                </div>
              </div>
              <div class="inst-wapp">
                <a href="https://wa.me/5581982579870" target="_blank" rel="noopener" title="Fale conosco no WhatsApp" aria-label="WhatsApp">
                  <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/></svg>
                </a>
                <a href="https://www.linkedin.com/in/alocjr/" target="_blank" rel="noopener" title="LinkedIn" aria-label="LinkedIn">
                  <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20"><path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/></svg>
                </a>
              </div>
            </div>
          </section>

          <template v-for="sem in jornada" :key="sem.semana">
            <div class="ch-div">
              <div class="ch-rule"></div>
              <div class="ch-lbl">
                <span class="ch-num">Semana {{ sem.semana }}</span>
                {{ sem.tema_central ?? '' }}
              </div>
              <div class="ch-rule"></div>
            </div>
            <div class="mpad">
              <div
                v-for="enc in (sem.encontros ?? [])"
                :key="enc.id"
                :id="`enc${enc.id}`"
                class="mod"
                :class="{
                  active: statusEnc(enc) === 'active' && expandedId === enc.id,
                  'mod--done': statusEnc(enc) === 'done',
                  open: expandedId === enc.id,
                  locked: statusEnc(enc) === 'locked',
                }"
              >
                <div class="mod-hd" @click="toggleExpand(enc)">
                  <div class="mod-idx">{{ romano(enc.id) }}</div>
                  <div class="mod-info">
                    <div class="mod-top">
                      <span class="mod-title">{{ enc.titulo ?? '' }}</span>
                      <span
                        class="mod-tag"
                        :class="{
                          'tg-done': statusEnc(enc) === 'done',
                          'tg-active': statusEnc(enc) === 'active',
                          'tg-lock': statusEnc(enc) === 'locked',
                        }"
                      >
                        {{
                          statusEnc(enc) === 'done'
                            ? 'Concluído'
                            : statusEnc(enc) === 'active'
                              ? 'Em andamento'
                              : 'Bloqueado'
                        }}
                      </span>
                    </div>
                    <div v-if="enc.subtitulo" class="mod-sub">{{ enc.subtitulo }}</div>
                    <div class="mod-meta">
                      <span>Semana {{ sem.semana }}</span>
                      <span class="mm-sep">·</span>
                      <span>{{ (enc.material_suporte ?? []).length }} materiais</span>
                      <template v-if="statusEnc(enc) === 'active'">
                        <span class="mm-sep">·</span>
                        <span class="mm-hi">Em progresso</span>
                      </template>
                    </div>
                  </div>
                  <div class="mod-right">
                    <svg
                      width="14"
                      height="14"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="1.5"
                      :class="{ 'arrow-open': expandedId === enc.id }"
                    >
                      <polyline points="6 9 12 15 18 9" />
                    </svg>
                  </div>
                </div>

                <div
                  v-show="expandedId === enc.id"
                  class="mod-body"
                  :class="{ 'mod-body--readonly': !isEncontroAcessivel(enc) }"
                >
                  <div class="mod-inner">
                    <div v-if="!isEncontroAcessivel(enc)" class="readonly-badge">
                      Somente leitura — conclua o encontro em andamento para desbloquear
                    </div>
                    <div class="sec-hd">Foco do Encontro</div>
                    <p class="enc-tema">{{ enc.tema ?? '' }}</p>

                    <div class="cols2">
                      <div class="col">
                        <div class="col-hd">Objetivos</div>
                        <ul class="col-ul">
                          <li v-for="(o, i) in (enc.objetivos ?? [])" :key="i" v-text="o" />
                        </ul>
                      </div>
                      <div class="col">
                        <div class="col-hd">Resultados Esperados</div>
                        <ul class="col-ul">
                          <li
                            v-for="(r, i) in (enc.resultados_esperados ?? [])"
                            :key="i"
                            v-text="r"
                          />
                        </ul>
                      </div>
                    </div>

                    <template v-if="metodologia?.estrutura_encontro?.length">
                      <div class="sec-hd">Estrutura do Encontro</div>
                      <div class="metod-grid">
                        <div
                          v-for="(b, i) in (metodologia.estrutura_encontro as EstruturaEncontro[])"
                          :key="i"
                          class="metod-cell"
                        >
                          <div class="metod-n">{{ b.duracao ?? '' }}</div>
                          <div class="metod-hd">{{ b.bloco ?? '' }}</div>
                          <div class="metod-desc">{{ b.descricao ?? '' }}</div>
                        </div>
                      </div>
                    </template>

                    <div class="sec-hd">Materiais de Apoio</div>
                    <div class="mat-list">
                      <template
                        v-for="(m, matIdx) in (enc.material_suporte ?? [])"
                        :key="matIdx"
                      >
                        <a
                          v-if="isEncontroAcessivel(enc) && isExternalUrl((m as MaterialSuporte).url)"
                          :href="(m as MaterialSuporte).url"
                          target="_blank"
                          rel="noopener"
                          class="mat-row"
                        >
                          <input
                            v-if="isEncontroEditavel(enc)"
                            type="checkbox"
                            class="mat-check"
                            :checked="isMaterialChecked(enc.id, matIdx)"
                            :disabled="!!materialToggling"
                            @click.prevent="
                              onMaterialToggle(
                                enc.id,
                                matIdx,
                                !isMaterialChecked(enc.id, matIdx)
                              )
                            "
                          />
                          <span
                            v-else
                            class="mat-check mat-check--ro"
                            aria-hidden="true"
                          >{{ isMaterialChecked(enc.id, matIdx) ? '✓' : '○' }}</span>
                          <div class="mat-type">{{ parseMatItem((m as MaterialSuporte).item).tipo }}</div>
                          <div class="mat-vr"></div>
                          <div class="mat-info">
                            <div class="mat-name">
                              {{ parseMatItem((m as MaterialSuporte).item).nome }}
                            </div>
                            <div class="mat-sub">
                              <span class="mat-badge mb-ext">Externo</span>
                            </div>
                          </div>
                          <div class="mat-icon" aria-hidden="true">↗</div>
                        </a>
                        <div
                          v-else-if="!isEncontroAcessivel(enc) && isExternalUrl((m as MaterialSuporte).url)"
                          class="mat-row mat-row--readonly"
                        >
                          <span class="mat-check mat-check--ro" aria-hidden="true">
                            {{ isMaterialChecked(enc.id, matIdx) ? '✓' : '○' }}
                          </span>
                          <div class="mat-type">{{ parseMatItem((m as MaterialSuporte).item).tipo }}</div>
                          <div class="mat-vr"></div>
                          <div class="mat-info">
                            <div class="mat-name">
                              {{ parseMatItem((m as MaterialSuporte).item).nome }}
                            </div>
                            <div class="mat-sub">
                              <span class="mat-badge mb-ext">Externo</span>
                            </div>
                          </div>
                        </div>
                        <div
                          v-else-if="isEncontroEditavel(enc)"
                          class="mat-row"
                        >
                          <input
                            type="checkbox"
                            class="mat-check"
                            :checked="isMaterialChecked(enc.id, matIdx)"
                            :disabled="!!materialToggling"
                            @change="
                              onMaterialToggle(
                                enc.id,
                                matIdx,
                                !isMaterialChecked(enc.id, matIdx)
                              )
                            "
                          />
                          <div class="mat-type">{{ parseMatItem((m as MaterialSuporte).item).tipo }}</div>
                          <div class="mat-vr"></div>
                          <div class="mat-info">
                            <div class="mat-name">
                              {{ parseMatItem((m as MaterialSuporte).item).nome }}
                            </div>
                            <div class="mat-sub">
                              <span class="mat-badge mb-int">Interno</span>
                            </div>
                          </div>
                        </div>
                        <div
                          v-else-if="statusEnc(enc) === 'done'"
                          class="mat-row"
                        >
                          <span class="mat-check mat-check--ro" aria-hidden="true">
                            {{ isMaterialChecked(enc.id, matIdx) ? '✓' : '○' }}
                          </span>
                          <div class="mat-type">{{ parseMatItem((m as MaterialSuporte).item).tipo }}</div>
                          <div class="mat-vr"></div>
                          <div class="mat-info">
                            <div class="mat-name">
                              {{ parseMatItem((m as MaterialSuporte).item).nome }}
                            </div>
                            <div class="mat-sub">
                              <span class="mat-badge mb-int">Interno</span>
                            </div>
                          </div>
                        </div>
                        <div v-else class="mat-row mat-row--readonly">
                          <span class="mat-check mat-check--ro" aria-hidden="true">
                            {{ isMaterialChecked(enc.id, matIdx) ? '✓' : '○' }}
                          </span>
                          <div class="mat-type">{{ parseMatItem((m as MaterialSuporte).item).tipo }}</div>
                          <div class="mat-vr"></div>
                          <div class="mat-info">
                            <div class="mat-name">
                              {{ parseMatItem((m as MaterialSuporte).item).nome }}
                            </div>
                            <div class="mat-sub">
                              <span class="mat-badge mb-int">Interno</span>
                            </div>
                          </div>
                        </div>
                      </template>
                      <button
                        v-if="isEncontroEditavel(enc) && (enc.material_suporte ?? []).length > 0"
                        type="button"
                        class="mat-row mat-row-select-all"
                        :disabled="!!selectingAllId"
                        @click="onSelectAllMateriais(enc)"
                      >
                        <input
                          type="checkbox"
                          class="mat-check"
                          :checked="allMateriaisChecked(enc)"
                          :disabled="!!selectingAllId"
                          tabindex="-1"
                          readonly
                          aria-hidden="true"
                        />
                        <div class="mat-type mat-type--action">Ação</div>
                        <div class="mat-vr"></div>
                        <div class="mat-info">
                          <div class="mat-name mat-name--action">
                            {{ selectingAllId === enc.id ? 'Atualizando…' : (allMateriaisChecked(enc) ? 'Desmarcar todos' : 'Selecionar todos') }}
                          </div>
                        </div>
                      </button>
                    </div>

                    <div v-if="entregavelParaEncontro(enc.id)" class="entregavel">
                      <span class="entregavel-star">★</span>
                      <div>
                        Entregável:
                        <strong>{{ entregavelParaEncontro(enc.id)?.item ?? '' }}</strong>
                      </div>
                      <div class="entregavel-orig">
                        {{ entregavelParaEncontro(enc.id)?.origem ?? '' }}
                      </div>
                    </div>

                    <div class="mod-foot">
                      <template v-if="statusEnc(enc) === 'active'">
                        <button
                          type="button"
                          class="btn-prime"
                          :disabled="completingId === enc.id || !podeClicarConcluir(enc)"
                          @click="onCompleteEncontro(enc.id)"
                        >
                          {{ completingId === enc.id ? 'Concluindo…' : '✓ Concluir Encontro' }}
                        </button>
                        <RouterLink :to="enc.quiz_id ? `/quiz/q/${enc.quiz_id}` : `/quiz/${enc.id}`" class="btn-quiz">Abrir Quiz</RouterLink>
                        <span class="foot-note">
                          {{
                            (enc.material_suporte ?? []).length > Object.keys(materialChecks[enc.id] ?? {}).length
                              ? 'Marque todos os materiais para concluir'
                              : 'Todos os materiais revisados'
                          }}
                        </span>
                      </template>
                      <template v-else-if="statusEnc(enc) === 'done'">
                        <RouterLink :to="enc.quiz_id ? `/quiz/q/${enc.quiz_id}` : `/quiz/${enc.id}`" class="btn-quiz">Abrir Quiz</RouterLink>
                        <button type="button" class="btn-prime btn--done" disabled>✓ Concluído</button>
                      </template>
                      <template v-else>
                        <span class="foot-note foot-note--muted">Somente leitura — conclua o encontro em andamento</span>
                        <button type="button" class="btn-prime" disabled>Disponível em breve</button>
                      </template>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </template>
        </div>
      </div>

      <div class="metrics">
        <div class="met-gold"></div>
        <div class="met-body">
          <div class="met-lbl">Status do Programa</div>
          <div class="met-rows">
            <div v-for="(r, i) in metricsRows" :key="i" class="met-row">
              <div class="met-row-hd">{{ r.lbl }} <span>{{ r.pct }}%</span></div>
              <div class="met-track">
                <div class="met-track-fill" :style="{ width: r.pct + '%', background: r.color }"></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.wrap {
  min-height: calc(100vh - var(--bar-h));
}
.shell {
  display: flex;
  min-height: calc(100vh - var(--bar-h));
}
.sidebar {
  width: var(--sw);
  flex-shrink: 0;
  position: sticky;
  top: var(--bar-h);
  height: calc(100vh - var(--bar-h));
  overflow-y: auto;
  background: var(--wh);
  border-right: 1px solid var(--bd);
  display: flex;
  flex-direction: column;
}
.sb-top {
  padding: 28px 24px 22px;
  border-bottom: 1px solid var(--bd);
}
.sb-eyebrow {
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: var(--k5);
  margin-bottom: 11px;
  display: flex;
  align-items: center;
  gap: 10px;
}
.sb-eyebrow::before {
  content: '';
  width: 18px;
  height: 1px;
  background: var(--gold);
  opacity: 0.7;
}
.sb-title {
  font-family: var(--serif);
  font-size: 14px;
  color: var(--k0);
  margin-bottom: 22px;
}
.sb-prog {
  margin-bottom: 18px;
}
.sb-prog-nums {
  display: flex;
  gap: 5px;
  margin-bottom: 7px;
}
.sb-prog-big {
  font-family: var(--serif);
  font-size: 34px;
}
.sb-prog-den {
  font-size: 12px;
  color: var(--k5);
}
.sb-prog-track {
  height: 1.5px;
  background: var(--k7);
  position: relative;
  margin-bottom: 5px;
}
.sb-prog-fill {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  background: var(--k0);
}
.sb-prog-note {
  font-size: 11px;
  color: var(--k5);
}
.sb-facts {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1px;
  background: var(--bd);
  border: 1px solid var(--bd);
}
.sb-fact {
  background: var(--wh);
  padding: 8px 10px;
}
.sb-fact-v {
  font-family: var(--serif);
  font-size: 15px;
  color: var(--k0);
}
.sb-fact-v.g {
  color: var(--gold);
}
.sb-fact-k {
  font-size: 9.5px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--k5);
}
.sb-nav {
  flex: 1;
  padding: 14px 0 8px;
  min-height: 0;
}
.nav-ch-hd {
  display: flex;
  align-items: center;
  gap: 11px;
  padding: 7px 24px;
  cursor: pointer;
}
.nav-ch-n {
  font-size: 10px;
  letter-spacing: 0.14em;
  color: var(--k3);
  min-width: 22px;
}
.nav-ch-nm {
  font-size: 11.5px;
  font-weight: 600;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--k3);
  flex: 1;
}
.nav-arr {
  color: var(--k6);
  font-size: 10px;
}
.nav-ch-items {
  padding-bottom: 4px;
}
.nav-ch:not(.open) .nav-ch-items {
  display: none;
}
.nav-entry {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 8px 24px 8px 20px;
  cursor: pointer;
  border-left: 2px solid transparent;
}
.nav-entry.current {
  background: var(--k8);
  border-left-color: var(--k0);
}
.nav-entry.locked {
  cursor: default;
  opacity: 0.35;
}
.nav-entry.done,
.nav-entry.current {
  cursor: pointer;
}
.ndot {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  border: 1.5px solid;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 8px;
  flex-shrink: 0;
}
.nd-done {
  border-color: var(--k0);
  background: var(--k0);
  color: #fff;
}
.nd-cur {
  border-color: var(--k0);
}
.nd-todo,
.nd-lock {
  border-color: var(--k7);
}
.nav-entry-txt {
  flex: 1;
  font-size: 13px;
  color: var(--k4);
}
.nav-entry-num {
  font-family: var(--serif);
  font-style: italic;
  font-size: 11.5px;
  color: var(--k4);
}
.sb-bot {
  border-top: 1px solid var(--bd);
  padding: 18px 24px;
}
.sb-next {
  border-left: 2px solid var(--gold);
  padding: 10px 0 10px 14px;
}
.sb-next-tag {
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: var(--gold);
  margin-bottom: 4px;
}
.sb-next-title {
  font-size: 14px;
  color: var(--k0);
}
.sb-next-meta {
  font-size: 12px;
  color: var(--k4);
}

.main {
  flex: 1;
  min-width: 0;
  background: var(--k9);
  overflow-y: auto;
}
.ribbon {
  display: none;
  align-items: center;
  gap: 14px;
  padding: 0 44px;
  height: 44px;
  background: var(--k0);
  font-size: 13px;
  color: rgba(255, 255, 255, 0.45);
}
.ribbon.show {
  display: flex;
}
.ribbon-rule {
  width: 18px;
  height: 1px;
  background: var(--gold);
}
.ribbon-close {
  margin-left: auto;
  color: rgba(255, 255, 255, 0.25);
  font-size: 19px;
  cursor: pointer;
  background: none;
  border: none;
  padding: 0 8px;
}

.loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
  gap: 16px;
  color: var(--k5);
}
.spin {
  width: 28px;
  height: 28px;
  border: 1.5px solid var(--k7);
  border-top-color: var(--k3);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
.error-msg {
  padding: 40px 20px;
  text-align: center;
  color: #8f2b2b;
}

.intro {
  background: var(--wh);
  border-bottom: 1px solid var(--bd);
  padding: 56px 60px 48px;
}
.intro-kicker {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: var(--k5);
  margin-bottom: 22px;
  display: flex;
  align-items: center;
  gap: 14px;
}
.intro-kicker::before {
  content: '';
  width: 28px;
  height: 1px;
  background: var(--k0);
}
.intro-h1 {
  font-family: var(--serif);
  font-size: clamp(28px, 3.6vw, 42px);
  font-weight: 400;
  line-height: 1.1;
  color: var(--k0);
  margin-bottom: 8px;
}
.intro-h1 em {
  font-style: italic;
  font-size: 0.88em;
  color: var(--k4);
}
.intro-sub {
  font-family: var(--serif);
  font-style: italic;
  font-size: 18px;
  color: var(--k5);
  margin-bottom: 20px;
}
.intro-desc {
  font-size: 14.5px;
  font-weight: 300;
  color: var(--k3);
  max-width: 510px;
  line-height: 1.8;
  margin-bottom: 36px;
}
.kpis {
  display: flex;
  align-items: stretch;
  border: 1px solid var(--bd);
  background: var(--k9);
  width: fit-content;
}
.kpi {
  padding: 14px 28px;
  border-right: 1px solid var(--bd);
}
.kpi:last-child {
  border-right: none;
}
.kpi-v {
  font-family: var(--serif);
  font-size: 27px;
}
.kpi-v.g {
  color: var(--gold);
}
.kpi-k {
  font-size: 10.5px;
  font-weight: 600;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--k5);
}
.inst-row {
  display: flex;
  align-items: flex-start;
  gap: 18px;
  margin-top: 30px;
  padding-top: 24px;
  border-top: 1px solid var(--bd2);
}
.inst-role {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--k5);
}
.inst-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--k0);
}
.inst-separator {
  margin: 14px 0 10px;
  width: 32px;
  height: 1px;
  background: var(--bd2);
}
.inst-progress {
  margin-top: 10px;
  width: 100%;
}
.inst-progress-label {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--k5);
  margin-bottom: 4px;
}
.inst-progress-track {
  margin: 4px 0 6px;
  padding: 4px 0;
  display: flex;
  gap: 4px;
  width: 100%;
  overflow-x: auto;
  scrollbar-width: thin;
}
.inst-progress-track::-webkit-scrollbar {
  height: 4px;
}
.inst-progress-track::-webkit-scrollbar-thumb {
  background: var(--k7);
  border-radius: 999px;
}
.inst-hover-card {
  margin-top: 4px;
  padding: 8px 10px;
  border-radius: 6px;
  border: 1px solid var(--bd2);
  background: var(--wh);
  box-shadow: 0 1px 3px rgba(12, 35, 64, 0.08);
}
.inst-hover-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--k0);
  margin-bottom: 2px;
}
.inst-hover-meta {
  font-size: 11px;
  color: var(--k5);
  margin-bottom: 2px;
}
.inst-hover-desc {
  font-size: 11px;
  color: var(--k4);
}
.inst-step {
  flex: 1 1 0;
  min-width: 45px;
  max-width: 70px;
  border-radius: 6px;
  border: 1px solid var(--k7);
  background: var(--k8);
  padding: 6px 10px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  cursor: pointer;
  text-align: center;
}
.inst-step-num {
  font-family: var(--serif);
  font-size: 12px;
  color: var(--k3);
}
.inst-step--done {
  background: var(--green-done-row);
  border-color: var(--green-done-bd);
}
.inst-step--done .inst-step-num {
  color: var(--success);
}
.inst-step--active {
  background: var(--wh);
  border-color: var(--k0);
}
.inst-step--active .inst-step-num {
  color: var(--k0);
}
.inst-step--locked {
  opacity: 0.8;
  border-style: dashed;
}
.inst-progress-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 4px;
}
.inst-progress-legend .leg {
  font-size: 10px;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: var(--k5);
}
.inst-progress-legend .leg::before {
  content: '';
  width: 10px;
  height: 6px;
  border-radius: 999px;
  background: var(--k7);
}
.inst-progress-legend .leg--done::before {
  background: var(--green-done-bd);
}
.inst-progress-legend .leg--active::before {
  background: var(--k0);
}
.inst-progress-legend .leg--locked::before {
  background: var(--k7);
}
.inst-wapp {
  margin-left: auto;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: center;
}
.inst-wapp a {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  color: #fff;
  text-decoration: none;
  transition: transform 0.2s ease;
}
.inst-wapp a:hover {
  transform: scale(1.08);
}
.inst-wapp a[href*='wa.me'] {
  background: #25d366;
}
.inst-wapp a[href*='linkedin'] {
  background: #0a66c2;
}

.ch-div {
  display: flex;
  align-items: center;
  gap: 18px;
  padding: 30px 44px 14px;
}
.ch-rule {
  flex: 1;
  height: 1px;
  background: var(--bd);
}
.ch-lbl {
  font-size: 10.5px;
  font-weight: 600;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: var(--k5);
  display: flex;
  gap: 11px;
  white-space: nowrap;
}
.ch-num {
  font-family: var(--serif);
  font-style: italic;
  font-size: 13px;
  color: var(--k6);
}
.mpad {
  padding: 0 44px 6px;
}
.mod {
  border: 1px solid rgba(14, 14, 14, 0.16);
  background: var(--wh);
  margin-bottom: 2px;
  overflow: hidden;
}
.mod.active {
  border-color: var(--k0);
  background: var(--k8);
}
.mod.locked {
  background: var(--k9);
  border-color: transparent;
}
.mod.open .mod-body {
  display: block;
}
.mod-body {
  display: none;
  border-top: 1px solid var(--bd2);
}
/* Item em execução: cores claras (fundo branco) */
.mod.active .mod-body {
  background: var(--wh);
}
.mod.active .mod-body .mod-inner {
  background: var(--wh);
}
.mod.active .mod-body .mat-list {
  border-color: var(--bd);
  background: var(--wh);
}
.mod.active .mod-body .mat-row {
  background: var(--wh);
}
.mod.active .mod-body .mat-row:hover {
  background: var(--k9);
}
.mod.active .mod-body .mod-foot {
  background: var(--wh);
  border-top: 1px solid var(--bd2);
}
/* Encontros concluídos: fundo verde elegante (links e quiz acessíveis) */
.mod.mod--done {
  background: var(--green-done-bg);
  border-color: var(--green-done-bd);
}
.mod.mod--done .mod-body {
  background: var(--green-done-bg);
}
.mod.mod--done .mod-body .mod-inner {
  background: var(--green-done-bg);
}
.mod.mod--done .mod-body .mat-list {
  border-color: var(--green-done-bd);
  background: var(--green-done-bg);
}
.mod.mod--done .mod-body .mat-row {
  background: var(--green-done-row);
}
.mod.mod--done .mod-body .mat-row:hover {
  background: var(--green-done-bd);
}
.mod.mod--done .mod-body .mod-foot {
  background: var(--green-done-bg);
  border-top: 1px solid var(--green-done-bd);
}
.mod-hd {
  display: flex;
  align-items: center;
  cursor: pointer;
}
.mod-idx {
  width: 50px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-right: 1px solid var(--bd);
  font-family: var(--serif);
  font-style: italic;
  font-size: 15px;
  color: var(--k4);
}
.mod-info {
  flex: 1;
  padding: 17px 20px;
  min-width: 0;
}
.mod-top {
  display: flex;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 4px;
  flex-wrap: wrap;
}
.mod-title {
  font-family: var(--serif);
  font-size: 19px;
  color: var(--k0);
}
.mod-sub {
  font-family: var(--serif);
  font-style: italic;
  font-size: 15px;
  color: var(--k5);
}
.mod-tag {
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  padding: 3px 8px;
  border: 1px solid;
}
.tg-done {
  color: var(--k4);
  border-color: var(--k7);
}
.tg-active {
  color: var(--k0);
  border-color: var(--k0);
}
.tg-todo,
.tg-lock {
  color: var(--k5);
  border-color: var(--k7);
}
.mod-meta {
  font-size: 14px;
  color: var(--k5);
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}
.mm-sep {
  color: inherit;
}
.mm-hi {
  color: var(--gold);
}
.mod-right {
  padding: 0 18px;
  flex-shrink: 0;
  color: var(--k5);
  display: flex;
  align-items: center;
  gap: 8px;
}
.mod-right .arrow-open {
  transform: rotate(180deg);
}
.lock-msg {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 22px;
  border-top: 1px solid var(--bd2);
  background: var(--k9);
}
.lock-msg p {
  margin: 0.5em 0 0;
  font-size: 14px;
  color: var(--k4);
}
.lock-msg-icon {
  font-size: 1.2em;
}
.readonly-badge {
  font-size: 12px;
  color: var(--k4);
  background: var(--beige-row);
  padding: 8px 12px;
  border-radius: 6px;
  margin-bottom: 16px;
  border: 1px solid var(--beige-bd);
}
.mod-body--readonly {
  background: var(--beige-bg);
}
.mod-body--readonly .mod-inner {
  background: var(--beige-bg);
}
.mod-body--readonly .sec-hd,
.mod-body--readonly .col-hd {
  color: var(--k4);
}
.mod-body--readonly .enc-tema,
.mod-body--readonly .mat-name {
  color: var(--k3);
}
.mod-body--readonly .mat-list {
  border-color: var(--beige-bd);
}
.mod-body--readonly .mat-row--readonly {
  background: var(--beige-row);
}
.mod-body--readonly .mod-foot {
  background: var(--beige-bg);
  border-top: 1px solid var(--beige-bd);
}
.mod-inner {
  padding: 26px 26px 0;
}
.mod-foot {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 14px 26px;
  margin-top: 24px;
  flex-wrap: wrap;
}
.btn-prime {
  height: 38px;
  padding: 0 22px;
  background: var(--k0);
  border: 1px solid var(--k0);
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
.btn-prime:disabled {
  opacity: 0.4;
  cursor: default;
}
.btn-prime.btn--done {
  background: var(--success);
  border-color: var(--success);
  color: #fff;
}
.btn-prime.btn--done:disabled {
  opacity: 1;
}
.btn-quiz {
  height: 38px;
  padding: 0 20px;
  background: var(--golddim);
  border: 1px solid var(--goldbd);
  color: var(--gold);
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  border-radius: 2px;
  transition: background 0.2s ease, border-color 0.2s ease, color 0.2s ease;
  text-decoration: none;
}
.btn-quiz:hover {
  background: var(--gold);
  border-color: var(--gold);
  color: #fff;
}
.foot-note {
  margin-left: auto;
  font-size: 13px;
  color: var(--k6);
}
.foot-note--muted {
  color: var(--k5);
}

.metrics {
  position: fixed;
  bottom: 26px;
  right: 28px;
  width: 188px;
  background: var(--k0);
  z-index: 200;
  overflow: hidden;
}
.met-gold {
  height: 1px;
  background: var(--gold);
}
.met-body {
  padding: 16px;
}
.met-lbl {
  font-size: 9.5px;
  font-weight: 600;
  letter-spacing: 0.24em;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.2);
  margin-bottom: 15px;
}
.met-rows {
  display: flex;
  flex-direction: column;
  gap: 11px;
}
.met-row-hd {
  display: flex;
  justify-content: space-between;
  margin-bottom: 5px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.3);
}
.met-row-hd span {
  font-family: var(--serif);
  font-size: 14px;
  color: rgba(255, 255, 255, 0.65);
}
.met-track {
  height: 1px;
  background: rgba(255, 255, 255, 0.1);
}
.met-track-fill {
  height: 100%;
  transition: width 0.3s ease;
}
.sec-hd {
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: var(--k5);
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 14px;
}
.sec-hd::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--bd);
}
.enc-tema {
  font-size: 16px;
  font-weight: 300;
  color: var(--k3);
  line-height: 1.8;
  margin-bottom: 22px;
}
.cols2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1px;
  background: var(--bd);
  border: 1px solid var(--bd);
  margin-bottom: 24px;
}
.col {
  background: var(--wh);
  padding: 18px 22px;
}
.col-hd {
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: var(--k5);
  padding-bottom: 12px;
  border-bottom: 1px solid var(--bd2);
  margin-bottom: 14px;
}
.col-ul {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 9px;
}
.col-ul li {
  font-size: 15px;
  font-weight: 300;
  color: var(--k0);
  line-height: 1.55;
  padding-left: 15px;
  position: relative;
}
.col-ul li::before {
  content: '';
  position: absolute;
  left: 0;
  top: 9px;
  width: 6px;
  height: 1px;
  background: var(--k0);
}
.metod-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 1px;
  background: var(--bd);
  border: 1px solid var(--bd);
  margin-bottom: 24px;
}
.metod-cell {
  background: var(--wh);
  padding: 10px 12px;
}
.metod-n {
  font-family: var(--serif);
  font-size: 16px;
}
.metod-hd {
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--k5);
}
.metod-desc {
  font-size: 12px;
  color: var(--k4);
  line-height: 1.45;
}
.mat-list {
  display: flex;
  flex-direction: column;
  gap: 1px;
  background: var(--bd);
  border: 1px solid var(--bd);
  margin-bottom: 24px;
}
.mat-row {
  background: var(--wh);
  display: flex;
  align-items: center;
  padding: 14px 18px;
  text-decoration: none;
  color: inherit;
  cursor: pointer;
}
a.mat-row:hover {
  background: var(--k8);
}
.mat-row-select-all {
  border: none;
  width: 100%;
  text-align: left;
  font: inherit;
  color: inherit;
  cursor: pointer;
  background: var(--k9);
  border-bottom: 1px solid var(--bd);
}
.mat-row-select-all:hover:not(:disabled) {
  background: var(--k8);
}
.mat-row-select-all:disabled {
  cursor: not-allowed;
  opacity: 0.85;
}
.mat-name--action,
.mat-type--action {
  font-weight: 600;
  color: var(--k0);
}
.mat-type--action {
  letter-spacing: 0.08em;
}
.mat-check {
  margin-right: 12px;
  accent-color: var(--k0);
  cursor: pointer;
}
.mat-check--ro {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  margin-right: 12px;
  font-size: 12px;
  color: var(--k5);
  cursor: default;
}
.mat-row--readonly {
  cursor: default;
  pointer-events: none;
  background: var(--beige-row);
}
.mod-body--readonly .mat-row--readonly {
  background: var(--beige-row);
}
a.mat-row--readonly {
  pointer-events: none;
}
.mat-type {
  width: 76px;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--k5);
  padding-right: 14px;
  flex-shrink: 0;
}
.mat-vr {
  width: 1px;
  height: 18px;
  background: var(--bd);
  margin-right: 16px;
  flex-shrink: 0;
}
.mat-info {
  flex: 1;
  min-width: 0;
}
.mat-name {
  font-family: var(--serif);
  font-size: 16px;
  font-weight: 500;
  color: var(--k0);
  line-height: 1.45;
  letter-spacing: 0.01em;
}
.mat-sub {
  font-size: 13px;
  color: var(--k5);
  display: flex;
  gap: 8px;
}
.mat-badge {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.08em;
  padding: 2px 7px;
  border: 1px solid;
}
.mb-ext {
  color: var(--gold);
  border-color: var(--goldbd);
}
.mb-int {
  color: var(--k5);
  border-color: var(--k7);
}
.mat-icon {
  font-size: 12px;
  color: var(--k5);
}
.entregavel {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 13px 18px;
  border: 1px solid var(--goldbd);
  background: var(--golddim);
  margin-bottom: 24px;
}
.entregavel-star {
  color: var(--gold);
}
.entregavel-orig {
  font-size: 13px;
  color: var(--k5);
  margin-left: auto;
}

@media (max-width: 860px) {
  .sidebar {
    display: none;
  }
  .intro {
    padding: 36px 24px 32px;
  }
  .ch-div,
  .mpad {
    padding-left: 20px;
    padding-right: 20px;
  }
  .cols2 {
    grid-template-columns: 1fr;
  }
  .metod-grid {
    grid-template-columns: 1fr 1fr;
  }
  .metrics {
    display: none;
  }
}
</style>
