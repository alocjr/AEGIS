/**
 * Catálogo espelho do AI Hub (ids e paths). A fonte de verdade dos rótulos é
 * `GET /api/admin/tools`; aqui só o mapeamento path ↔ id, para o router e o menu.
 */

export const TOOL_MATURITY = 'maturity'
export const TOOL_SWOT = 'swot'
export const TOOL_OKR = 'okr'
export const TOOL_CANVAS = 'canvas'
export const TOOL_STRATEGIC_MAP = 'strategic_map'
export const TOOL_GOVERNANCE = 'governance'

export type ToolId =
  | typeof TOOL_MATURITY
  | typeof TOOL_SWOT
  | typeof TOOL_OKR
  | typeof TOOL_CANVAS
  | typeof TOOL_STRATEGIC_MAP
  | typeof TOOL_GOVERNANCE

/** Ordem de preferência ao redirecionar o usuário (primeira ferramenta liberada). */
export const TOOL_HOME_ORDER: { id: ToolId; path: string }[] = [
  { id: TOOL_MATURITY, path: '/ai-maturity' },
  { id: TOOL_SWOT, path: '/swot' },
  { id: TOOL_CANVAS, path: '/projetos' },
  { id: TOOL_OKR, path: '/okrs' },
  { id: TOOL_STRATEGIC_MAP, path: '/mapa-estrategico' },
  { id: TOOL_GOVERNANCE, path: '/governanca/inventario' },
]

/** Prefixos de rota → ferramenta exigida. Mentoria não entra: usa `course_slugs`. */
const PATH_TOOL_RULES: { prefix: string; tool: ToolId }[] = [
  { prefix: '/ai-maturity', tool: TOOL_MATURITY },
  { prefix: '/swot', tool: TOOL_SWOT },
  { prefix: '/okrs', tool: TOOL_OKR },
  { prefix: '/projetos', tool: TOOL_CANVAS },
  { prefix: '/mapa-estrategico', tool: TOOL_STRATEGIC_MAP },
  { prefix: '/governanca', tool: TOOL_GOVERNANCE },
]

export function toolRequiredForPath(path: string): ToolId | null {
  for (const rule of PATH_TOOL_RULES) {
    if (path === rule.prefix || path.startsWith(rule.prefix + '/')) {
      return rule.tool
    }
  }
  return null
}

export function firstEnabledToolPath(tools: string[] | undefined | null): string | null {
  const set = new Set(tools || [])
  for (const entry of TOOL_HOME_ORDER) {
    if (set.has(entry.id)) return entry.path
  }
  return null
}
