<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { fetchMyMaturityResponses, fetchMaturityModel, type MaturityResponseListItem, type MaturityModel } from '@/api/maturity'

const loading = ref(true)
const error = ref<string | null>(null)
const items = ref<MaturityResponseListItem[]>([])
const model = ref<MaturityModel | null>(null)

function formatDate(iso: string | null): string {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString('pt-BR', {
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

/** Iniciais da dimensão (primeiras letras das duas primeiras palavras, máx. 2 caracteres) */
function getInitials(name: string): string {
  const words = name.trim().split(/\s+/).filter(Boolean)
  if (!words.length) return '?'
  const a = words[0][0] ?? ''
  const b = words[1]?.[0] ?? ''
  return (a + b).toUpperCase().slice(0, 2) || '?'
}

/** Retorna percentual por dimensão na ordem do modelo, para o mini gráfico */
function getDimensionPcts(
  item: MaturityResponseListItem,
  dimensions: { id: string; name: string }[] | undefined
): { name: string; pct: number; initials: string }[] {
  if (!dimensions?.length || !item.result?.dimension_scores) return []
  return dimensions.map((dim) => {
    const ds = item.result!.dimension_scores![dim.id] || { score: 0, max: 1 }
    const pct = ds.max ? Math.round((ds.score / ds.max) * 100) : 0
    return { name: dim.name, pct, initials: getInitials(dim.name) }
  })
}

/** Gera pontos do polígono do radar (0-100% → raio) e posições das iniciais. SVG: size 72, center 36, rMax 26 */
const RADAR_SIZE = 72
const RADAR_CX = 36
const RADAR_CY = 36
const RADAR_R = 26
const RADAR_LABEL_R = 32

function radarPoints(dims: { pct: number }[]): string {
  if (!dims.length) return ''
  const n = dims.length
  return dims
    .map((d, i) => {
      const angle = -Math.PI / 2 + (2 * Math.PI * i) / n
      const r = (d.pct / 100) * RADAR_R
      const x = RADAR_CX + r * Math.cos(angle)
      const y = RADAR_CY + r * Math.sin(angle)
      return `${x},${y}`
    })
    .join(' ')
}

function radarAxisEnd(i: number, n: number): { x: number; y: number } {
  const angle = -Math.PI / 2 + (2 * Math.PI * i) / n
  return {
    x: RADAR_CX + RADAR_R * Math.cos(angle),
    y: RADAR_CY + RADAR_R * Math.sin(angle),
  }
}

function radarLabelPos(i: number, n: number): { x: number; y: number } {
  const angle = -Math.PI / 2 + (2 * Math.PI * i) / n
  return {
    x: RADAR_CX + RADAR_LABEL_R * Math.cos(angle),
    y: RADAR_CY + RADAR_LABEL_R * Math.sin(angle),
  }
}

onMounted(async () => {
  try {
    const [listRes, mod] = await Promise.all([
      fetchMyMaturityResponses(),
      fetchMaturityModel(),
    ])
    items.value = listRes.items ?? []
    model.value = mod
    error.value = null
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Erro ao carregar.'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="wrap">
    <div class="page-header">
      <h1 class="page-title">{{ model?.assessment_title ?? 'Modelo de Maturidade em IA' }}</h1>
      <p class="page-desc">Suas autoavaliações. Realize novas avaliações para acompanhar sua evolução.</p>
    </div>

    <div v-if="loading" class="card">Carregando...</div>
    <div v-else-if="error" class="card error-msg">{{ error }}</div>

    <template v-else>
      <div class="card card-cta">
        <RouterLink to="/ai-maturity/new" class="btn-new">
          + Nova autoavaliação
        </RouterLink>
      </div>

      <div v-if="items.length === 0" class="card card-empty">
        <p>Você ainda não realizou nenhuma autoavaliação.</p>
        <RouterLink to="/ai-maturity/new" class="link-new">Fazer primeira autoavaliação →</RouterLink>
      </div>

      <ul v-else class="list">
        <li v-for="item in items" :key="item.id" class="list-item">
          <RouterLink :to="`/ai-maturity/${item.id}`" class="list-link">
            <div class="list-main">
              <span class="list-date">{{ formatDate(item.submitted_at) }}</span>
              <span class="list-level">{{ item.result?.level?.label ?? '—' }}</span>
              <div class="list-charts-wrap" v-if="getDimensionPcts(item, model?.dimensions).length">
                <div class="list-mini-chart">
                  <div
                    v-for="d in getDimensionPcts(item, model?.dimensions)"
                    :key="d.name"
                    class="mini-bar-row"
                  >
                    <span class="mini-bar-label" :title="`${d.name}: ${d.pct}%`">{{ d.name }}</span>
                    <div class="mini-bar-wrap">
                      <div class="mini-bar-fill" :style="{ width: d.pct + '%' }" />
                    </div>
                  </div>
                </div>
                <div class="list-mini-radar" :title="item.result?.level?.label ?? ''">
                  <svg viewBox="0 0 72 72" class="radar-svg" aria-hidden="true">
                    <defs>
                      <linearGradient :id="'radarFill-' + item.id" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stop-color="var(--gold)" stop-opacity="0.35" />
                        <stop offset="100%" stop-color="var(--gold2)" stop-opacity="0.5" />
                      </linearGradient>
                    </defs>
                    <g v-for="(d, idx) in getDimensionPcts(item, model?.dimensions)" :key="'ax-' + d.name">
                      <line
                        :x1="RADAR_CX"
                        :y1="RADAR_CY"
                        :x2="radarAxisEnd(idx, getDimensionPcts(item, model?.dimensions).length).x"
                        :y2="radarAxisEnd(idx, getDimensionPcts(item, model?.dimensions).length).y"
                        class="radar-axis"
                      />
                    </g>
                    <polygon
                      v-if="getDimensionPcts(item, model?.dimensions).length"
                      :points="radarPoints(getDimensionPcts(item, model?.dimensions))"
                      class="radar-polygon"
                      :fill="'url(#radarFill-' + item.id + ')'"
                      stroke="var(--gold2)"
                      stroke-width="1.2"
                    />
                    <text
                      v-for="(d, idx) in getDimensionPcts(item, model?.dimensions)"
                      :key="'lb-' + d.name"
                      :x="radarLabelPos(idx, getDimensionPcts(item, model?.dimensions).length).x"
                      :y="radarLabelPos(idx, getDimensionPcts(item, model?.dimensions).length).y"
                      class="radar-label"
                      text-anchor="middle"
                      dominant-baseline="middle"
                    >{{ d.initials }}</text>
                  </svg>
                </div>
              </div>
            </div>
            <div class="list-score">
              <span class="list-pct">{{ item.result?.percent_score ?? 0 }}%</span>
              <span class="list-points">{{ item.result?.total_score ?? 0 }}/{{ item.result?.max_score ?? 0 }}</span>
              <span class="list-pts-label"> pts</span>
            </div>
          </RouterLink>
        </li>
      </ul>
    </template>
  </div>
</template>

<style scoped>
.wrap {
  max-width: 640px;
  margin: 0 auto;
  padding: 22px 16px 40px;
}
.page-header {
  margin-bottom: 24px;
}
.page-title {
  font-family: var(--serif);
  font-size: 24px;
  font-weight: 600;
  color: var(--k0);
  margin: 0 0 8px 0;
}
.page-desc {
  font-size: 14px;
  color: var(--k5);
  margin: 0;
}
.card {
  background: var(--wh);
  border: 1px solid var(--bd);
  padding: 18px;
  margin-bottom: 14px;
  border-radius: 8px;
}
.error-msg {
  color: #8f2b2b;
}
.card-cta {
  margin-bottom: 20px;
}
.btn-new {
  display: inline-block;
  padding: 12px 24px;
  background: var(--k0);
  color: var(--wh);
  font-weight: 600;
  text-decoration: none;
  border-radius: 8px;
  transition: opacity 0.2s;
}
.btn-new:hover {
  opacity: 0.9;
}
.card-empty {
  text-align: center;
  color: var(--k5);
}
.card-empty p {
  margin: 0 0 12px 0;
}
.link-new {
  color: var(--gold2);
  font-weight: 500;
  text-decoration: none;
}
.link-new:hover {
  text-decoration: underline;
}
.list {
  list-style: none;
  padding: 0;
  margin: 0;
}
.list-item {
  margin-bottom: 8px;
}
.list-link {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 18px;
  background: var(--wh);
  border: 1px solid var(--bd);
  border-radius: 8px;
  text-decoration: none;
  color: inherit;
  transition: background 0.2s, border-color 0.2s;
}
.list-link:hover {
  background: var(--k9);
  border-color: var(--goldbd);
}
.list-main {
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex: 1;
  min-width: 0;
}
.list-date {
  font-size: 14px;
  color: var(--k0);
  font-weight: 500;
}
.list-level {
  font-size: 12px;
  color: var(--gold2);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.list-charts-wrap {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
/* Barras à esquerda, radar à direita, ambos alinhados ao centro do item */
.list-mini-radar {
  flex-shrink: 0;
  width: 72px;
  height: 72px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.radar-svg {
  width: 100%;
  height: 100%;
  display: block;
}
.radar-axis {
  stroke: var(--k7);
  stroke-width: 0.8;
}
.radar-polygon {
  transition: opacity 0.2s;
}
.list-link:hover .radar-polygon {
  opacity: 0.95;
}
.radar-label {
  font-size: 9px;
  font-weight: 600;
  fill: var(--k4);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
}
.list-mini-chart {
  display: flex;
  flex-direction: column;
  gap: 5px;
  max-width: 260px;
  flex: 1;
  min-width: 0;
}
.mini-bar-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.mini-bar-label {
  flex: 0 0 auto;
  font-size: 11px;
  color: var(--k5);
  max-width: 100px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.mini-bar-wrap {
  flex: 1;
  min-width: 0;
  height: 6px;
  background: var(--k8);
  border-radius: 3px;
  overflow: hidden;
}
.mini-bar-fill {
  height: 100%;
  border-radius: 3px;
  background: linear-gradient(90deg, var(--gold), var(--gold2));
  min-width: 2px;
  transition: width 0.3s ease;
}
.list-score {
  text-align: right;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
}
.list-pct {
  font-family: var(--serif);
  font-size: 2.25rem;
  font-weight: 600;
  color: var(--k0);
  line-height: 1.1;
}
.list-points {
  font-family: var(--serif);
  font-size: 18px;
  font-weight: 600;
  color: var(--k0);
}
.list-pts-label {
  font-size: 12px;
  color: var(--k5);
  font-weight: 400;
}
</style>
