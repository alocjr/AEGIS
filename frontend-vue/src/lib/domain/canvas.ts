/**
 * AR-04: quadrantes da matriz valor × viabilidade (canvas de projetos).
 */
import type { CanvasQuadrant } from '@/api/canvasProjects'

export const CANVAS_QUADRANT_LABEL: Record<Exclude<CanvasQuadrant, null>, string> = {
  ganho_rapido: 'Ganho rápido',
  aposta_estrategica: 'Aposta estratégica',
  incremental: 'Incremental',
  evitar: 'Evitar · vaidade',
}

/** Variante em minúsculas para rótulos de grafo / mapa estratégico. */
export function canvasQuadrantLabelLower(quadrant: string | null | undefined): string {
  if (!quadrant) return ''
  const label = CANVAS_QUADRANT_LABEL[quadrant as Exclude<CanvasQuadrant, null>]
  return label ? label.toLowerCase() : quadrant
}
