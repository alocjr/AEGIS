<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { fetchCurrentCourse } from '@/api/course'
import type { JornadaSemana, Encontro, MaterialSuporte } from '@/types'

function parseMatItem(item: string): { tipo: string; nome: string } {
  const i = item.indexOf(':')
  if (i < 0) return { tipo: 'Material', nome: item.trim() }
  return { tipo: item.slice(0, i).trim(), nome: item.slice(i + 1).trim() }
}

function isExternalUrl(url?: string): boolean {
  return !!(url && (url.startsWith('http://') || url.startsWith('https://')))
}

type IconType = 'video' | 'pdf' | 'link' | 'document'

function getIconType(m: MaterialSuporte): IconType {
  const url = (m.url ?? '').toLowerCase()
  const { tipo } = parseMatItem(m.item)
  const t = tipo.toLowerCase()
  if (url.includes('youtube.com') || url.includes('youtu.be') || t.includes('vídeo') || t.includes('video')) return 'video'
  if (url.endsWith('.pdf') || t === 'pdf') return 'pdf'
  if (isExternalUrl(m.url)) return 'link'
  return 'document'
}

interface MaterialItem {
  encontro: Encontro
  semana: number
  material: MaterialSuporte
  matIndex: number
}

const loading = ref(true)
const error = ref<string | null>(null)
const courseTitle = ref('')
const data = ref<Awaited<ReturnType<typeof fetchCurrentCourse>> | null>(null)

const programa = computed(() => data.value?.programa_formacao_executiva as { jornada_aprendizagem?: JornadaSemana[] } | undefined)
const jornada = computed(() => programa.value?.jornada_aprendizagem ?? [])

/** Lista plana de materiais com contexto do encontro */
const materialsByEncontro = computed<Record<number, MaterialItem[]>>(() => {
  const byEnc: Record<number, MaterialItem[]> = {}
  ;(jornada.value ?? []).forEach((sem) => {
    ;(sem.encontros ?? []).forEach((enc) => {
      const list = (enc.material_suporte ?? []).map((m, matIndex) => ({
        encontro: enc,
        semana: sem.semana,
        material: m,
        matIndex,
      }))
      if (list.length) byEnc[enc.id] = list
    })
  })
  return byEnc
})

const encontroIds = computed(() => Object.keys(materialsByEncontro.value).map(Number).sort((a, b) => a - b))
const totalMateriais = computed(() =>
  encontroIds.value.reduce((acc, id) => acc + (materialsByEncontro.value[id]?.length ?? 0), 0)
)

onMounted(async () => {
  try {
    data.value = await fetchCurrentCourse()
    const pfe = data.value?.programa_formacao_executiva as { cabecalho?: { titulo?: string } }
    courseTitle.value = pfe?.cabecalho?.titulo ?? 'Materiais'
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Erro ao carregar materiais.'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="shell">
    <div v-if="loading" class="loading">
      <div class="spin"></div>
      <span>Carregando materiais…</span>
    </div>
    <div v-else-if="error" class="error-msg">{{ error }}</div>

    <template v-else>
      <div class="page-head">
        <div class="page-kicker">Sua trilha</div>
        <h1 class="page-title">Materiais · {{ courseTitle }}</h1>
        <p class="page-desc">
          {{ encontroIds.length }} encontros · {{ totalMateriais }} materiais de apoio.
        </p>
      </div>

      <div class="enc-sections">
        <section
          v-for="encId in encontroIds"
          :key="encId"
          class="enc-section"
        >
          <h2 class="enc-section-title">
            Encontro {{ encId }}
            <span v-if="materialsByEncontro[encId]?.[0]?.encontro?.titulo" class="enc-section-sub">
              {{ materialsByEncontro[encId][0].encontro.titulo }}
            </span>
          </h2>
          <div class="mat-grid">
            <template v-for="(row, idx) in (materialsByEncontro[encId] ?? [])" :key="`${encId}-${idx}`">
              <a
                v-if="isExternalUrl(row.material.url)"
                :href="row.material.url!"
                target="_blank"
                rel="noopener"
                class="mat-card mat-card--link"
              >
                <div class="mat-icon-wrap" :class="`mat-icon-wrap--${getIconType(row.material)}`">
                  <span class="mat-icon" aria-hidden="true">
                    <template v-if="getIconType(row.material) === 'video'">▶</template>
                    <template v-else-if="getIconType(row.material) === 'pdf'">PDF</template>
                    <template v-else-if="getIconType(row.material) === 'link'">↗</template>
                    <template v-else>📄</template>
                  </span>
                </div>
                <div class="mat-body">
                  <span class="mat-type">{{ parseMatItem(row.material.item).tipo }}</span>
                  <span class="mat-name">{{ parseMatItem(row.material.item).nome }}</span>
                </div>
              </a>
              <div v-else class="mat-card">
                <div class="mat-icon-wrap mat-icon-wrap--document">
                  <span class="mat-icon" aria-hidden="true">📄</span>
                </div>
                <div class="mat-body">
                  <span class="mat-type">{{ parseMatItem(row.material.item).tipo }}</span>
                  <span class="mat-name">{{ parseMatItem(row.material.item).nome }}</span>
                </div>
              </div>
            </template>
          </div>
        </section>
      </div>
    </template>
  </div>
</template>

<style scoped>
.shell {
  min-height: calc(100vh - var(--bar-h));
  padding: 40px 44px 60px;
}
.loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 50vh;
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
  to { transform: rotate(360deg); }
}
.error-msg {
  text-align: center;
  padding: 60px 24px;
  color: var(--k4);
}

.page-head {
  margin-bottom: 36px;
}
.page-kicker {
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: var(--k5);
  margin-bottom: 10px;
}
.page-title {
  font-family: var(--serif);
  font-size: 32px;
  color: var(--k0);
  margin-bottom: 8px;
}
.page-desc {
  font-size: 14px;
  color: var(--k4);
}

.enc-sections {
  display: flex;
  flex-direction: column;
  gap: 32px;
}
.enc-section-title {
  font-family: var(--serif);
  font-size: 20px;
  color: var(--k0);
  margin: 0 0 16px 0;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--bd);
}
.enc-section-sub {
  font-weight: 400;
  font-size: 0.85em;
  color: var(--k4);
}

.mat-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 20px;
}
.mat-card {
  display: flex;
  flex-direction: column;
  background: var(--wh);
  border: 1px solid var(--bd);
  border-radius: 8px;
  overflow: hidden;
  text-decoration: none;
  color: inherit;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}
.mat-card--link {
  cursor: pointer;
}
.mat-card--link:hover {
  border-color: var(--goldbd);
  box-shadow: 0 4px 20px rgba(12, 35, 64, 0.08);
}
.mat-icon-wrap {
  aspect-ratio: 16 / 10;
  background: var(--k9);
  display: flex;
  align-items: center;
  justify-content: center;
}
.mat-icon {
  font-size: 32px;
  font-weight: 600;
  color: var(--k5);
}
.mat-icon-wrap--video .mat-icon {
  color: var(--k2);
  font-size: 28px;
}
.mat-icon-wrap--pdf .mat-icon {
  font-size: 14px;
  letter-spacing: 0.08em;
  color: var(--k3);
}
.mat-icon-wrap--link .mat-icon {
  font-size: 28px;
  color: var(--gold);
}
.mat-icon-wrap--document .mat-icon {
  font-size: 28px;
}
.mat-body {
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.mat-type {
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--k5);
}
.mat-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--k0);
  line-height: 1.35;
}

@media (max-width: 640px) {
  .shell {
    padding: 24px 20px 40px;
  }
  .mat-grid {
    grid-template-columns: 1fr 1fr;
  }
}
</style>
