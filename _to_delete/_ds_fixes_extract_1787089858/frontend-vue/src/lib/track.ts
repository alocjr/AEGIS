/**
 * Contagem de acesso aos recursos (dashboard do admin).
 *
 * O mapa abaixo é o espelho do catálogo estático de `backend/app/analytics.py`: uma chave por
 * funcionalidade, não por ferramenta, para o admin ver *o que* dentro da ferramenta é usado.
 * Chave que o backend não reconhece é descartada lá — aqui não há validação a fazer.
 *
 * A rota `Landing` fica de fora de propósito: ela só embute `lp.html` num iframe, e é o próprio
 * `lp.js` que registra o acesso. Registrar nos dois lugares contaria a mesma visita duas vezes.
 * As rotas de `/admin` também ficam de fora — o painel não é recurso da plataforma.
 */

const RESOURCE_BY_ROUTE_NAME: Record<string, string> = {
  Login: 'plataforma.login',
  OrgMembers: 'plataforma.organizacao',

  Programa: 'mentoria.programa',
  Materiais: 'mentoria.materiais',
  Agenda: 'mentoria.agenda',
  Trilhas: 'mentoria.trilhas',
  TrilhaShowcase: 'mentoria.trilha',
  Quiz: 'mentoria.quiz',
  QuizById: 'mentoria.quiz',
  QuizRespostas: 'mentoria.quiz_respostas',

  AiMaturityList: 'maturity.lista',
  AiMaturityNew: 'maturity.nova',
  AiMaturityEdit: 'maturity.edicao',
  AiMaturityDetail: 'maturity.resultado',
  SwotAnalysis: 'swot.editor',
  ProjetosList: 'canvas.lista',
  ProjetoCanvas: 'canvas.projeto',
  OkrCyclesList: 'okr.ciclos',
  OkrCycleEditor: 'okr.editor',
  MapaEstrategico: 'strategic_map.painel',
  GovernanceDashboard: 'governance.dashboard',
  GovernanceInventory: 'governance.inventario',
  GovernanceSystem: 'governance.sistema',
  GovernanceGate: 'governance.gate',
}

export function resourceKeyForRoute(routeName: string | symbol | null | undefined): string | null {
  if (typeof routeName !== 'string') return null
  return RESOURCE_BY_ROUTE_NAME[routeName] ?? null
}

const baseURL = import.meta.env.VITE_API_BASE_URL ?? ''

/** Dispara e esquece: falha de rede em telemetria não pode aparecer para o usuário. */
export function trackResourceAccess(resourceKey: string): void {
  void fetch(`${baseURL}/api/public/track`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ resource_key: resourceKey }),
    credentials: 'include',
    keepalive: true,
  }).catch(() => {})
}
