<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import { useCoursesStore } from '@/stores/courses'
import { useAuthStore } from '@/stores/auth'
import type { CoursePublic, Encontro, JornadaSemana, MaterialSuporte, ProgramaFormacaoExecutiva } from '@/types'

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

const route = useRoute()
const slug = computed(() => route.params.slug as string)
const store = useCoursesStore()
const auth = useAuthStore()

onMounted(() => {
  if (slug.value) {
    store.loadCourse(slug.value)
    if (auth.user?.course_slugs?.includes(slug.value)) {
      auth.setCurrentCourseSlug(slug.value)
    }
  }
})

const course = computed(() => store.getBySlug(slug.value))

const programa = computed<ProgramaFormacaoExecutiva | undefined>(
  () => course.value?.programa_formacao_executiva
)

const titulo = computed(() => {
  const p = programa.value
  return p?.cabecalho?.titulo ?? course.value?.titulo ?? course.value?.slug ?? ''
})

const objetivo = computed(() => {
  const p = programa.value
  return p?.visao_geral?.objetivo ?? course.value?.objetivo ?? ''
})

const jornada = computed(() => programa.value?.jornada_aprendizagem ?? [])

const totalEncontros = computed(() =>
  jornada.value.reduce((acc, sem) => acc + (sem.encontros?.length ?? 0), 0)
)

const numSemanas = computed(() => jornada.value.length)

/** ID do primeiro encontro (único expandido e em modo somente leitura) */
const firstEncontroId = computed(() => {
  const firstSem = jornada.value[0]
  const firstEnc = firstSem?.encontros?.[0]
  return firstEnc?.id ?? null
})

const metodologia = computed(() => programa.value?.metodologia_detalhada)
const entregaveisResumo = computed(() => programa.value?.entregaveis_resumo ?? [])

function entregavelParaEncontro(encId: number) {
  return entregaveisResumo.value.find((e) => e.origem === `Encontro ${encId}`)
}

function isFirstEncontro(enc: Encontro): boolean {
  return firstEncontroId.value !== null && enc.id === firstEncontroId.value
}
</script>

<template>
  <div class="wrap">
    <div v-if="store.loading" class="loading">Carregando trilha...</div>

    <template v-else-if="course">
      <nav class="breadcrumb">
        <RouterLink to="/trilhas">Trilhas</RouterLink>
        <span>/</span>
        <span>{{ titulo }}</span>
      </nav>

      <!-- Sem programa completo: fallback resumido -->
      <template v-if="!programa || jornada.length === 0">
        <h1>{{ titulo }}</h1>
        <p class="muted">{{ objetivo }}</p>
        <div class="meta">
          {{ course.num_encontros ?? totalEncontros ?? 0 }} encontros ·
          {{ course.num_semanas ?? numSemanas ?? 0 }} semanas
        </div>
        <p class="note">
          Conteúdo em amostra. Faça login para acessar o programa completo.
        </p>
      </template>

      <!-- Programa completo: intro + encontros -->
      <template v-else>
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
            </div>
          </div>
        </section>

        <!-- Jornada: semanas e encontros -->
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
                active: isFirstEncontro(enc),
                open: isFirstEncontro(enc),
                locked: !isFirstEncontro(enc),
              }"
            >
              <!-- Cabeçalho do encontro (sempre visível) -->
              <div
                class="mod-hd"
                :class="{ 'showcase-locked': !isFirstEncontro(enc) }"
              >
                <div class="mod-idx">{{ romano(enc.id) }}</div>
                <div class="mod-info">
                  <div class="mod-top">
                    <span class="mod-title">{{ enc.titulo ?? '' }}</span>
                    <span
                      class="mod-tag"
                      :class="
                        isFirstEncontro(enc) ? 'tg-active' : 'tg-lock'
                      "
                    >
                      {{ isFirstEncontro(enc) ? 'Amostra' : 'Conteúdo reservado' }}
                    </span>
                  </div>
                  <div v-if="enc.subtitulo" class="mod-sub">
                    {{ enc.subtitulo }}
                  </div>
                  <div class="mod-meta">
                    <span>Semana {{ sem.semana }}</span>
                    <span>·</span>
                    <span
                      >{{ (enc.material_suporte ?? []).length }} materiais</span
                    >
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
                  >
                    <polyline points="6 9 12 15 18 9" />
                  </svg>
                </div>
              </div>

              <!-- Corpo: apenas para o primeiro encontro (somente leitura) -->
              <div v-if="isFirstEncontro(enc)" class="mod-body">
                <div class="mod-inner">
                  <div class="sec-hd">Foco do Encontro</div>
                  <p class="enc-tema">{{ enc.tema ?? '' }}</p>

                  <div class="cols2">
                    <div class="col">
                      <div class="col-hd">Objetivos</div>
                      <ul class="col-ul">
                        <li
                          v-for="(o, i) in (enc.objetivos ?? [])"
                          :key="i"
                          v-text="o"
                        />
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

                  <template
                    v-if="
                      metodologia?.estrutura_encontro &&
                      metodologia.estrutura_encontro.length
                    "
                  >
                    <div class="sec-hd">Estrutura do Encontro</div>
                    <div class="metod-grid">
                      <div
                        v-for="(b, i) in metodologia.estrutura_encontro"
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
                      v-for="(m, i) in (enc.material_suporte ?? [])"
                      :key="i"
                    >
                      <a
                        v-if="isExternalUrl(m.url)"
                        :href="m.url"
                        target="_blank"
                        rel="noopener"
                        class="mat-row"
                      >
                        <input
                          type="checkbox"
                          class="mat-check"
                          checked
                          disabled
                        />
                        <div class="mat-type">{{
                          parseMatItem(m.item).tipo
                        }}</div>
                        <div class="mat-vr"></div>
                        <div class="mat-info">
                          <div class="mat-name">
                            {{ parseMatItem(m.item).nome }}
                          </div>
                          <div class="mat-sub">
                            <span class="mat-badge mb-ext">Externo</span>
                          </div>
                        </div>
                      </a>
                      <div v-else class="mat-row">
                        <input
                          type="checkbox"
                          class="mat-check"
                          checked
                          disabled
                        />
                        <div class="mat-type">{{
                          parseMatItem(m.item).tipo
                        }}</div>
                        <div class="mat-vr"></div>
                        <div class="mat-info">
                          <div class="mat-name">
                            {{ parseMatItem(m.item).nome }}
                          </div>
                          <div class="mat-sub">
                            <span class="mat-badge mb-int">Interno</span>
                          </div>
                        </div>
                      </div>
                    </template>
                  </div>

                  <div
                    v-if="entregavelParaEncontro(enc.id)"
                    class="entregavel"
                  >
                    <span class="entregavel-star">★</span>
                    <div>
                      Entregável:
                      <strong>{{
                        entregavelParaEncontro(enc.id)?.item ?? ''
                      }}</strong>
                    </div>
                    <div class="entregavel-orig">
                      {{ entregavelParaEncontro(enc.id)?.origem ?? '' }}
                    </div>
                  </div>
                </div>
                <div class="mod-foot">
                  <span class="foot-note">
                    Conteúdo em amostra. Faça login para acessar todos os
                    encontros.
                  </span>
                </div>
              </div>
            </div>
          </div>
        </template>
      </template>
    </template>

    <div v-else class="empty">
      {{ store.error || 'Trilha não encontrada.' }}
    </div>
  </div>
</template>

<style scoped>
.wrap {
  max-width: 900px;
  margin: 24px auto;
  padding: 0 20px 48px;
}
.breadcrumb {
  font-size: 13px;
  color: var(--k5);
  margin-bottom: 16px;
}
.breadcrumb a {
  color: var(--gold2);
}
.breadcrumb a:hover {
  text-decoration: underline;
}

/* Intro */
.intro {
  background: var(--wh);
  border-bottom: 1px solid var(--bd);
  padding: 40px 0 32px;
  margin: 0 -20px 0;
  padding-left: 20px;
  padding-right: 20px;
}
.intro-kicker {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: var(--k5);
  margin-bottom: 16px;
}
.intro-h1 {
  font-family: var(--serif);
  font-size: clamp(28px, 4vw, 40px);
  font-weight: 400;
  line-height: 1.2;
  color: var(--k0);
  margin-bottom: 8px;
}
.intro-h1 em {
  font-style: italic;
  color: var(--k3);
}
.intro-sub {
  font-family: var(--serif);
  font-style: italic;
  font-size: 16px;
  color: var(--k5);
  margin-bottom: 16px;
}
.intro-desc {
  font-size: 14px;
  font-weight: 300;
  color: var(--k3);
  max-width: 560px;
  line-height: 1.7;
  margin-bottom: 24px;
}
.kpis {
  display: flex;
  align-items: stretch;
  border: 1px solid var(--bd);
  background: var(--k9);
  width: fit-content;
  flex-wrap: wrap;
}
.kpi {
  padding: 12px 20px;
  border-right: 1px solid var(--bd);
}
.kpi:last-child {
  border-right: none;
}
.kpi-v {
  font-family: var(--serif);
  font-size: 22px;
}
.kpi-v.g {
  color: var(--gold);
}
.kpi-k {
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--k5);
}
.inst-row {
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid var(--bd2);
}
.inst-role {
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: var(--k5);
}
.inst-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--k0);
}

/* Semanas / encontros */
.ch-div {
  display: flex;
  align-items: center;
  gap: 18px;
  padding: 28px 0 12px;
}
.ch-rule {
  flex: 1;
  height: 1px;
  background: var(--bd);
}
.ch-lbl {
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: var(--k5);
  display: flex;
  gap: 10px;
  white-space: nowrap;
}
.ch-num {
  font-family: var(--serif);
  font-style: italic;
  font-size: 12px;
  color: var(--k5);
}
.mpad {
  padding-bottom: 8px;
}
.mod {
  border: 1px solid rgba(14, 14, 14, 0.12);
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
  border-color: rgba(14, 14, 14, 0.08);
}
.mod-hd {
  display: flex;
  align-items: center;
}
.mod-hd.showcase-locked {
  cursor: default;
  pointer-events: none;
}
.mod-idx {
  width: 48px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-right: 1px solid var(--bd);
  font-family: var(--serif);
  font-style: italic;
  font-size: 15px;
  color: var(--k3);
}
.mod-info {
  flex: 1;
  padding: 16px 18px;
  min-width: 0;
}
.mod-top {
  display: flex;
  align-items: baseline;
  gap: 10px;
  margin-bottom: 4px;
  flex-wrap: wrap;
}
.mod-title {
  font-family: var(--serif);
  font-size: 18px;
  color: var(--k0);
}
.mod-sub {
  font-family: var(--serif);
  font-style: italic;
  font-size: 14px;
  color: var(--k5);
}
.mod-tag {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  padding: 3px 8px;
  border: 1px solid;
}
.tg-active {
  color: var(--k0);
  border-color: var(--k0);
}
.tg-lock {
  color: var(--k5);
  border-color: var(--k7);
}
.mod-meta {
  font-size: 13px;
  color: var(--k5);
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}
.mod-right {
  padding: 0 16px;
  flex-shrink: 0;
  color: var(--k5);
}
.mod-body {
  border-top: 1px solid var(--bd2);
}
.mod-inner {
  padding: 24px 24px 0;
}
.sec-hd {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--k5);
  margin-bottom: 10px;
  display: flex;
  align-items: center;
  gap: 12px;
}
.sec-hd::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--bd);
}
.enc-tema {
  font-size: 15px;
  font-weight: 300;
  color: var(--k3);
  line-height: 1.7;
  margin-bottom: 20px;
}
.cols2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1px;
  background: var(--bd);
  border: 1px solid var(--bd);
  margin-bottom: 20px;
}
.col {
  background: var(--wh);
  padding: 16px 20px;
}
.col-hd {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--k5);
  padding-bottom: 10px;
  border-bottom: 1px solid var(--bd2);
  margin-bottom: 12px;
}
.col-ul {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.col-ul li {
  font-size: 14px;
  font-weight: 300;
  color: var(--k0);
  line-height: 1.5;
  padding-left: 14px;
  position: relative;
}
.col-ul li::before {
  content: '';
  position: absolute;
  left: 0;
  top: 8px;
  width: 6px;
  height: 1px;
  background: var(--k0);
}
.metod-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
  gap: 1px;
  background: var(--bd);
  border: 1px solid var(--bd);
  margin-bottom: 20px;
}
.metod-cell {
  background: var(--wh);
  padding: 10px 12px;
}
.metod-n {
  font-family: var(--serif);
  font-size: 15px;
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
  color: var(--k3);
  line-height: 1.4;
}
.mat-list {
  display: flex;
  flex-direction: column;
  gap: 1px;
  background: var(--bd);
  border: 1px solid var(--bd);
  margin-bottom: 20px;
}
.mat-row {
  background: var(--wh);
  display: flex;
  align-items: center;
  padding: 12px 16px;
  text-decoration: none;
  color: inherit;
}
a.mat-row:hover {
  background: var(--k8);
}
.mat-check {
  margin-right: 12px;
  accent-color: var(--k0);
  pointer-events: none;
}
.mat-type {
  width: 72px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--k5);
  padding-right: 12px;
  flex-shrink: 0;
}
.mat-vr {
  width: 1px;
  height: 16px;
  background: var(--bd);
  margin-right: 14px;
  flex-shrink: 0;
}
.mat-info {
  flex: 1;
  min-width: 0;
}
.mat-name {
  font-size: 14px;
  color: var(--k0);
}
.mat-sub {
  font-size: 12px;
  color: var(--k5);
}
.mat-badge {
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.06em;
  padding: 2px 6px;
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
.entregavel {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border: 1px solid var(--goldbd);
  background: var(--golddim);
  margin-bottom: 20px;
}
.entregavel-star {
  color: var(--gold);
}
.entregavel-orig {
  font-size: 12px;
  color: var(--k5);
  margin-left: auto;
}
.mod-foot {
  display: flex;
  align-items: center;
  padding: 12px 24px;
  border-top: 1px solid var(--bd2);
  background: var(--k9);
  margin-top: 20px;
}
.foot-note {
  font-size: 13px;
  color: var(--k5);
}

/* Fallback sem programa */
h1 {
  font-family: var(--serif);
  font-size: 28px;
  margin-bottom: 12px;
}
.muted {
  color: var(--k3);
  line-height: 1.6;
  margin-bottom: 16px;
}
.meta {
  font-size: 13px;
  color: var(--k5);
  margin-bottom: 24px;
}
.note {
  font-size: 14px;
  color: var(--k5);
  padding: 16px;
  background: var(--k8);
  border-radius: 4px;
}

.loading,
.empty {
  text-align: center;
  padding: 48px 20px;
  color: var(--k5);
}

@media (max-width: 640px) {
  .cols2 {
    grid-template-columns: 1fr;
  }
  .metod-grid {
    grid-template-columns: 1fr 1fr;
  }
}
</style>
