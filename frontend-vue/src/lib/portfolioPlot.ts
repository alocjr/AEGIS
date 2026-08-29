/** Matriz valor × viabilidade do portfólio de projetos (AR-02). */
import type { CanvasProjectSummary, CanvasQuadrant } from '@/api/canvasProjects'

export const PORTFOLIO_PLOT = { x: 64, y: 40, w: 520, h: 440 }
export const PORTFOLIO_VIEWBOX = { w: 720, h: 560 }

export type PortfolioPlotPoint = {
  id: string
  title: string
  cx: number
  cy: number
  quadrant: Exclude<CanvasQuadrant, null>
  score_valor: number
  score_viabilidade: number
  area_negocio: string
  responsavel: string
  objetivo_estrategico: string
  proximo_passo: string
}

export function buildPortfolioPlotPoints(items: CanvasProjectSummary[]): PortfolioPlotPoint[] {
  const groups = new Map<string, CanvasProjectSummary[]>()
  for (const item of items) {
    const key = `${item.score_valor}-${item.score_viabilidade}`
    const list = groups.get(key) ?? []
    list.push(item)
    groups.set(key, list)
  }
  const points: PortfolioPlotPoint[] = []
  for (const group of groups.values()) {
    group.forEach((item, idx) => {
      const v = item.score_viabilidade as number
      const val = item.score_valor as number
      const baseX = PORTFOLIO_PLOT.x + ((v - 1) / 4) * PORTFOLIO_PLOT.w
      const baseY = PORTFOLIO_PLOT.y + PORTFOLIO_PLOT.h - ((val - 1) / 4) * PORTFOLIO_PLOT.h
      const angle = group.length === 1 ? 0 : (idx / group.length) * Math.PI * 2
      const radius = group.length === 1 ? 0 : 14 + Math.min(idx, 3) * 3
      points.push({
        id: item.id,
        title: item.title || 'Novo projeto',
        cx: baseX + Math.cos(angle) * radius,
        cy: baseY + Math.sin(angle) * radius,
        quadrant: item.quadrant as Exclude<CanvasQuadrant, null>,
        score_valor: val,
        score_viabilidade: v,
        area_negocio: item.area_negocio || '',
        responsavel: item.responsavel || '',
        objetivo_estrategico: item.objetivo_estrategico || '',
        proximo_passo: item.proximo_passo || '',
      })
    })
  }
  return points
}
