<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, reactive } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import {
  getCanvasProject,
  updateCanvasProject,
  importIntoCanvasProject,
  type CanvasProject,
  type CanvasProjectPayload,
  type CanvasListField,
  type CanvasQuadrant,
  type CanvasImportDocument,
} from '@/api/canvasProjects'
import {
  getSwotAnalysisById,
  listSwotAnalyses,
  type SwotAnalysis,
  type SwotAnalysisSummary,
  type SwotInitiative,
  type SwotListField,
  type SwotTowsField,
} from '@/api/swotAnalysis'
import { getActiveOkrCycle, type OkrCycle } from '@/api/okrs'
import { useAutosave } from '@/composables/useAutosave'

const route = useRoute()
const router = useRouter()
const projectId = computed(() => String(route.params.id || ''))

const loading = ref(true)
const error = ref<string | null>(null)
// AR-03: fila de gravação, debounce e guarda de saída vêm do composable
// compartilhado — ver src/composables/useAutosave.ts.
const autosave = useAutosave(async () => {
  const payload: CanvasProjectPayload = { ...form.value }
  const updated = await updateCanvasProject(projectId.value, payload)
  applyProject(updated)
})
const saveState = autosave.saveState
const saveError = autosave.error
const importState = ref<'idle' | 'importing' | 'ok' | 'error'>('idle')
const importError = ref<string | null>(null)
const importOkMsg = ref('')
const fileInput = ref<HTMLInputElement | null>(null)
const project = ref<CanvasProject | null>(null)
const openHelp = ref<CanvasListField | null>(null)

type EvalField = 'valor' | 'dados' | 'custo' | 'riscos'

type EvalHelp = {
  field: EvalField
  num: string
  title: string
  hint: string
  tagline: string
  answers: string
  pulls: string
  questions: string[]
  examples: string[]
  alert: string
}

/** Banda de Avaliação — repertório de partida (perguntas + exemplos). */
const EVAL_CELLS: EvalHelp[] = [
  {
    field: 'valor',
    num: '04',
    title: 'Valor esperado',
    hint: 'Ganho direto (tempo/custo/receita) + indireto (qualidade/risco). Como medir?',
    tagline: 'o porquê',
    answers: 'Que ganho concreto essa oportunidade traz, e como vamos medir se deu certo?',
    pulls: 'Puxa a nota de Valor no bloco 08.',
    questions: [
      'Qual o ganho direto: tempo economizado, custo reduzido, receita gerada, capacidade liberada?',
      'Qual o ganho indireto: qualidade, redução de risco, experiência do cliente, retenção?',
      'Quem sente o ganho — a área, o cliente, a empresa toda?',
      'Qual a métrica de sucesso e a linha de base atual (de X para Y)?',
      'Em quanto tempo o valor aparece — semanas, um trimestre, um ano?',
    ],
    examples: [
      'Reduzir ~40% do tempo gasto em contatos repetidos; liberar a equipe para o caso complexo.',
      'Meta: tempo de resposta de 8 h → 5 h (−30%) e CSAT de 72 → 77.',
      'Aumentar conversão do e-commerce em 3–5 p.p. com recomendação personalizada.',
      'Cortar 15 h/semana de trabalho manual de conciliação no Financeiro.',
      'Reduzir prazo de revisão de contratos de 5 dias → 2 dias no Jurídico.',
      'Ganho indireto: menos erro humano em cálculo de reembolso (redução de risco).',
      'Ganho de capacidade: atender 30% mais pedidos sem aumentar o time.',
      'Métrica de sucesso definida: "% de contatos resolvidos sem intervenção humana".',
    ],
    alert:
      'Se ninguém consegue nomear a métrica nem a linha de base, o “valor” ainda é entusiasmo — não dá para pontuar o bloco 08 com honestidade.',
  },
  {
    field: 'dados',
    num: '05',
    title: 'Dados & insumos',
    hint: 'Combustível: volume, qualidade, acesso, formato. Sem dado, não sai do papel.',
    tagline: 'o veto',
    answers: 'Existe dado disponível, com qualidade e acesso, para alimentar essa oportunidade? Sem isso, ela não sai do papel.',
    pulls: 'Puxa a nota de Viabilidade no bloco 08.',
    questions: [
      'Que dado a IA precisa consumir para funcionar? Ele existe hoje?',
      'Onde está — sistema, planilha, e-mail, cabeça das pessoas? É acessível via API/export?',
      'Qual o volume e o histórico disponível (meses/anos, nº de registros)?',
      'Qual a qualidade: está estruturado, rotulado, atualizado, consistente?',
      'Há restrição de acesso (base de terceiros, dado pessoal, contrato)?',
    ],
    examples: [
      'Histórico de ~2 anos de tickets no CRM; categorização inconsistente (qualidade média).',
      'Base de FAQ e políticas em documentos soltos; precisa ser consolidada antes de usar.',
      'Dados de vendas por loja no ERP, com integração via API já disponível.',
      'Estoque fragmentado entre 3 sistemas que não conversam (bloqueador de viabilidade).',
      'Contratos em PDF escaneado (imagem, não texto) — exige OCR antes de qualquer extração.',
      'Dados de clientes sujeitos à LGPD; acesso exige base legal e anonimização.',
      'Volume alto e diário (bom para aprendizado); porém sem rótulo de “resolvido/não resolvido”.',
      'O dado existe só no conhecimento tácito da equipe — não capturado em lugar nenhum.',
    ],
    alert:
      'Se a resposta for “teríamos que começar a coletar do zero”, a viabilidade cai e a oportunidade provavelmente é uma aposta estratégica, não um ganho rápido.',
  },
  {
    field: 'custo',
    num: '06',
    title: 'Custo & complexidade',
    hint: 'CapEx (construir) × OpEx (operar: inferência/tokens + manutenção) + integração.',
    tagline: 'o preço real',
    answers: 'Quanto custa construir e, principalmente, operar e integrar isso ao dia a dia?',
    pulls: 'Puxa as notas de Valor e de Viabilidade no bloco 08.',
    questions: [
      'CapEx (construir): desenvolvimento, configuração, integração inicial, curadoria de dados.',
      'OpEx (operar): custo de inferência/tokens no volume real, licenças, manutenção, monitoramento.',
      'Qual a complexidade de integração com os sistemas atuais?',
      'Qual a mudança de processo e de pessoas necessária (o 70% da regra 10-20-70)?',
      'É construir do zero, usar plataforma existente ou contratar pronto?',
    ],
    examples: [
      'CapEx baixo: usa a plataforma de atendimento que já temos; só configuração.',
      'OpEx de inferência moderado, mas sensível ao volume (alto nº de mensagens/mês).',
      'Integração média: já existe API do ERP; falta mapear os campos.',
      'Integração alta: exigiria conectar 3 sistemas legados — principal fonte de esforço.',
      'Custo humano real: treinar 18 atendentes e mudar o script de atendimento.',
      'Manutenção contínua: alguém precisa revisar respostas e reajustar mensalmente.',
      'Curadoria de dados como custo escondido: limpar e rotular a base antes de começar.',
      'Opção pronta de mercado reduz CapEx, mas cria OpEx recorrente de licença.',
    ],
    alert:
      'Se o time só falou de tecnologia e não citou pessoas/processo, o custo está subestimado — 70% do esforço mora justamente aí.',
  },
  {
    field: 'riscos',
    num: '07',
    title: 'Riscos & governança',
    hint: 'LGPD e regras do setor, alucinação, dependência. Que supervisão humana é obrigatória?',
    tagline: 'os limites',
    answers: 'O que pode dar errado e que supervisão é obrigatória para operar com segurança?',
    pulls: 'Puxa a nota de Viabilidade no bloco 08.',
    questions: [
      'Regulatório: LGPD, regras do setor (saúde, financeiro, jurídico), retenção de dados.',
      'Erro do modelo: o que acontece se a IA errar? O erro é reversível ou caro?',
      'Alucinação: a tarefa tolera resposta inventada? Onde isso seria perigoso?',
      'Dependência: ficamos reféns de um fornecedor, modelo ou dado externo?',
      'Autonomia: qual o nível de human-in-the-loop obrigatório — sugerir, aprovar ou agir sozinho?',
    ],
    examples: [
      'LGPD: dados pessoais de clientes → base legal, minimização e anonimização.',
      'Ação financeira (troca/reembolso) exige aprovação humana antes de executar.',
      'Alucinação inaceitável em política de troca → respostas restritas à base oficial.',
      'Setor regulado: no jurídico, toda peça gerada passa por revisão de advogado.',
      'Risco reputacional se o cliente perceber que falou com um bot sem aviso.',
      'Dependência de um único fornecedor de modelo → prever plano B / portabilidade.',
      'Nível de autonomia definido: copiloto sugere, humano aprova e envia (fase 1).',
      'Viés: recomendação de crédito/preço precisa de auditoria para evitar discriminação.',
    ],
    alert:
      'Se a oportunidade só é viável com a IA agindo sozinha em algo irreversível, o risco derruba a viabilidade — repense o escopo ou adie.',
  },
]

const drafts = reactive<Record<CanvasListField, string>>({
  contexto: '',
  dores: '',
  oportunidade: '',
  dados: '',
  valor: '',
  custo: '',
  riscos: '',
})

const form = ref({
  title: '',
  area_negocio: '',
  responsavel: '',
  data: '',
  objetivo_estrategico: '',
  contexto: [] as string[],
  dores: [] as string[],
  oportunidade: [] as string[],
  oportunidade_tipos: [] as string[],
  dados: [] as string[],
  valor: [] as string[],
  custo: [] as string[],
  riscos: [] as string[],
  score_valor: null as number | null,
  score_viabilidade: null as number | null,
  proximo_passo: '',
  justificativa_tows: '',
  swot_id: null as string | null,
  swot_item_ids: [] as string[],
  tows_ids: [] as string[],
  kr_ids: [] as string[],
})

/** Origem estratégica: iniciativas TOWS da SWOT que justificam este projeto. */
const TOWS_GROUPS: { field: SwotTowsField; label: string; hint: string }[] = [
  { field: 'tows_fo', label: 'F × O · Ofensiva', hint: 'Forças que capturam oportunidades' },
  { field: 'tows_fa', label: 'F × A · Defesa', hint: 'Forças que neutralizam ameaças' },
  { field: 'tows_fxo', label: 'f × O · Reforço', hint: 'Fraquezas que travam oportunidades' },
  { field: 'tows_fxa', label: 'f × A · Sobrevivência', hint: 'Vulnerabilidade encontra risco' },
]

const SWOT_QUADRANT_LABEL: Record<SwotListField, string> = {
  forcas: 'Força',
  fraquezas: 'Fraqueza',
  oportunidades: 'Oportunidade',
  ameacas: 'Ameaça',
}

const MAX_TOWS_LINKS = 20

const swotList = ref<SwotAnalysisSummary[]>([])
const swot = ref<SwotAnalysis | null>(null)
const swotLoading = ref(false)
const swotError = ref<string | null>(null)
const originOpen = ref(false)

/** Itens SWOT por id, para mostrar o que cada estratégia cruza. */
const swotItemsById = computed(() => {
  const map = new Map<string, { texto: string; quadrant: SwotListField }>()
  const doc = swot.value
  if (!doc) return map
  for (const field of ['forcas', 'fraquezas', 'oportunidades', 'ameacas'] as SwotListField[]) {
    for (const item of doc[field] || []) {
      map.set(item.id, { texto: item.texto, quadrant: field })
    }
  }
  return map
})

const selectedInitiatives = computed(() => {
  const doc = swot.value
  if (!doc) return []
  const chosen = new Set(form.value.tows_ids)
  return TOWS_GROUPS.flatMap((group) =>
    (doc[group.field] || [])
      .filter((initiative) => initiative.id && chosen.has(initiative.id))
      .map((initiative) => ({ ...initiative, groupLabel: group.label }))
  )
})

const selectedItems = computed(() =>
  form.value.swot_item_ids
    .map((id) => ({ id, item: swotItemsById.value.get(id) }))
    .filter((entry): entry is { id: string; item: { texto: string; quadrant: SwotListField } } =>
      !!entry.item
    )
)

/** Rótulo das contrapartes de uma iniciativa (lado interno × lado externo). */
function crossingLabel(initiative: SwotInitiative): string {
  const texts = [...(initiative.itens_internos || []), ...(initiative.itens_externos || [])]
    .map((id) => swotItemsById.value.get(id)?.texto)
    .filter((text): text is string => !!text)
  return texts.join(' × ')
}

function isTowsSelected(initiativeId?: string): boolean {
  return !!initiativeId && form.value.tows_ids.includes(initiativeId)
}

async function loadSwot(swotId: string) {
  swotLoading.value = true
  swotError.value = null
  try {
    swot.value = await getSwotAnalysisById(swotId)
  } catch (e) {
    swot.value = null
    swotError.value = e instanceof Error ? e.message : 'Falha ao carregar a SWOT.'
  } finally {
    swotLoading.value = false
  }
}

async function loadOrigin(p: CanvasProject) {
  try {
    const list = await listSwotAnalyses()
    swotList.value = list.items
  } catch (e) {
    swotError.value = e instanceof Error ? e.message : 'Falha ao listar as SWOTs.'
    return
  }
  const linked = p.swot_id && swotList.value.some((s) => s.id === p.swot_id) ? p.swot_id : null
  if (p.swot_id && !linked) {
    // SWOT de origem foi apagada: solta os vínculos para não travar o autosave
    form.value.swot_id = null
    form.value.swot_item_ids = []
    form.value.tows_ids = []
  }
  const preferred = linked || swotList.value[0]?.id || null
  if (preferred) await loadSwot(preferred)
}

async function onSelectSwot(event: Event) {
  const nextId = (event.target as HTMLSelectElement).value
  if (!nextId || nextId === swot.value?.id) return
  // Vínculos pertencem à SWOT anterior — trocar de SWOT limpa a seleção
  const had = form.value.tows_ids.length + form.value.swot_item_ids.length > 0
  form.value.tows_ids = []
  form.value.swot_item_ids = []
  form.value.swot_id = null
  await loadSwot(nextId)
  if (had) await persist()
}

async function toggleTows(initiativeId?: string) {
  if (!initiativeId || !swot.value) return
  const chosen = new Set(form.value.tows_ids)
  if (chosen.has(initiativeId)) {
    chosen.delete(initiativeId)
  } else {
    if (chosen.size >= MAX_TOWS_LINKS) {
      swotError.value = `Máximo de ${MAX_TOWS_LINKS} iniciativas por projeto.`
      return
    }
    chosen.add(initiativeId)
  }
  swotError.value = null
  form.value.tows_ids = [...chosen]
  const stillLinked = form.value.tows_ids.length + form.value.swot_item_ids.length > 0
  form.value.swot_id = stillLinked ? swot.value.id : null
  await persist()
}

async function removeSwotItemLink(itemId: string) {
  form.value.swot_item_ids = form.value.swot_item_ids.filter((id) => id !== itemId)
  const stillLinked = form.value.tows_ids.length + form.value.swot_item_ids.length > 0
  form.value.swot_id = stillLinked ? form.value.swot_id : null
  await persist()
}

/** Key Results (OKR) que este projeto endereça — do ciclo OKR ativo da organização. */
const MAX_KR_LINKS = 20
const okrCycle = ref<OkrCycle | null>(null)
const okrLoading = ref(false)
const okrError = ref<string | null>(null)
const krSectionOpen = ref(false)

const krsById = computed(() => {
  const map = new Map<string, { titulo: string; objetivoTitulo: string; progress_pct: number }>()
  for (const obj of okrCycle.value?.objectives || []) {
    for (const kr of obj.key_results) {
      map.set(kr.id, { titulo: kr.titulo, objetivoTitulo: obj.titulo, progress_pct: kr.progress_pct })
    }
  }
  return map
})

const selectedKeyResults = computed(() =>
  form.value.kr_ids
    .map((id) => ({ id, kr: krsById.value.get(id) }))
    .filter((entry): entry is { id: string; kr: { titulo: string; objetivoTitulo: string; progress_pct: number } } => !!entry.kr)
)

function isKrSelected(krId?: string): boolean {
  return !!krId && form.value.kr_ids.includes(krId)
}

async function toggleKr(krId?: string) {
  if (!krId) return
  const chosen = new Set(form.value.kr_ids)
  if (chosen.has(krId)) {
    chosen.delete(krId)
  } else {
    if (chosen.size >= MAX_KR_LINKS) {
      okrError.value = `Máximo de ${MAX_KR_LINKS} Key Results por projeto.`
      return
    }
    chosen.add(krId)
  }
  okrError.value = null
  form.value.kr_ids = [...chosen]
  await persist()
}

async function loadActiveOkrCycle() {
  okrLoading.value = true
  try {
    okrCycle.value = await getActiveOkrCycle()
  } catch {
    // Sem ciclo ativo (404) é estado normal — o template mostra um aviso apontando para /okrs
    okrCycle.value = null
  } finally {
    okrLoading.value = false
  }
}

const typeOptions = ref<string[]>([
  'Automação',
  'Classificação/Previsão',
  'Extração/Busca',
  'Geração',
  'Copiloto',
  'Agente autônomo',
])

const quadrant = computed<CanvasQuadrant>(() => {
  const v = form.value.score_valor
  const f = form.value.score_viabilidade
  if (v == null || f == null) return null
  const highV = v >= 4
  const highF = f >= 4
  if (highV && highF) return 'ganho_rapido'
  if (highV && !highF) return 'aposta_estrategica'
  if (!highV && highF) return 'incremental'
  return 'evitar'
})

function asList(value: unknown): string[] {
  if (Array.isArray(value)) return value.map(String).map((s) => s.trim()).filter(Boolean)
  if (typeof value === 'string' && value.trim()) return [value.trim()]
  return []
}

function maskDate(raw: string): string {
  const digits = raw.replace(/\D/g, '').slice(0, 8)
  const parts: string[] = []
  if (digits.length > 0) parts.push(digits.slice(0, 2))
  if (digits.length > 2) parts.push(digits.slice(2, 4))
  if (digits.length > 4) parts.push(digits.slice(4, 8))
  return parts.join('/')
}

function onDateInput(ev: Event) {
  const input = ev.target as HTMLInputElement
  const masked = maskDate(input.value)
  form.value.data = masked
  input.value = masked
}

function applyProject(p: CanvasProject) {
  project.value = p
  form.value = {
    title: p.title || 'Novo projeto',
    area_negocio: p.area_negocio || '',
    responsavel: p.responsavel || '',
    data: maskDate(p.data || ''),
    objetivo_estrategico: p.objetivo_estrategico || '',
    contexto: asList(p.contexto),
    dores: asList(p.dores),
    oportunidade: asList(p.oportunidade),
    oportunidade_tipos: [...(p.oportunidade_tipos || [])],
    dados: asList(p.dados),
    valor: asList(p.valor),
    custo: asList(p.custo),
    riscos: asList(p.riscos),
    score_valor: p.score_valor,
    score_viabilidade: p.score_viabilidade,
    proximo_passo: p.proximo_passo || '',
    justificativa_tows: p.justificativa_tows || '',
    swot_id: p.swot_id ?? null,
    swot_item_ids: [...(p.swot_item_ids || [])],
    tows_ids: [...(p.tows_ids || [])],
    kr_ids: [...(p.kr_ids || [])],
  }
  if (p.opportunity_type_options?.length) {
    typeOptions.value = p.opportunity_type_options
  }
}

function addItem(field: CanvasListField) {
  const text = drafts[field].trim()
  if (!text) return
  if (form.value[field].length >= 40) return
  form.value[field] = [...form.value[field], text]
  drafts[field] = ''
  void persist()
}

function removeItem(field: CanvasListField, index: number) {
  form.value[field] = form.value[field].filter((_, i) => i !== index)
  void persist()
}

function autosizeItem(el: HTMLTextAreaElement | null | Event) {
  const ta =
    el instanceof Event ? (el.target as HTMLTextAreaElement | null) : el
  if (!ta) return
  ta.style.height = 'auto'
  ta.style.height = `${ta.scrollHeight}px`
}

function onItemBlur(field: CanvasListField, index: number, ev: Event) {
  const input = ev.target as HTMLTextAreaElement
  const next = input.value.trim()
  const list = [...form.value[field]]
  if (!next) {
    list.splice(index, 1)
  } else {
    list[index] = next
  }
  form.value[field] = list
  void persist()
}

function onDraftKeydown(field: CanvasListField, ev: KeyboardEvent) {
  if (ev.key === 'Enter') {
    ev.preventDefault()
    addItem(field)
  }
}

function toggleHelp(field: CanvasListField, ev?: Event) {
  ev?.stopPropagation()
  openHelp.value = openHelp.value === field ? null : field
}

function onDocPointerDown(ev: Event) {
  const target = ev.target as HTMLElement | null
  if (!target) return
  if (target.closest('.cell-help') || target.closest('.cell-help-btn')) return
  openHelp.value = null
}

function toggleType(t: string) {
  const set = new Set(form.value.oportunidade_tipos)
  if (set.has(t)) set.delete(t)
  else set.add(t)
  form.value.oportunidade_tipos = [...set]
  void persist()
}

function setScore(field: 'score_valor' | 'score_viabilidade', n: number) {
  form.value[field] = form.value[field] === n ? null : n
  void persist()
}

function openImportPicker() {
  importError.value = null
  importState.value = 'idle'
  importOkMsg.value = ''
  fileInput.value?.click()
}

async function onImportFile(ev: Event) {
  const input = ev.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file || !projectId.value) return

  importState.value = 'importing'
  importError.value = null
  importOkMsg.value = ''
  try {
    const text = await file.text()
    let parsed: unknown
    try {
      parsed = JSON.parse(text)
    } catch {
      throw new Error('Arquivo inválido. Envie um JSON válido.')
    }
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
      throw new Error('JSON inválido. Esperado um objeto aegis.canvas-oportunidades.')
    }
    const doc = parsed as CanvasImportDocument
    if (doc.schema != null && doc.schema !== 'aegis.canvas-oportunidades') {
      throw new Error('Formato inválido. Esperado schema=aegis.canvas-oportunidades.')
    }
    if (doc.versao != null && String(doc.versao) !== '1') {
      throw new Error('Versão não suportada. Use versao "1".')
    }
    const result = await importIntoCanvasProject(projectId.value, doc)
    applyProject(result.item)
    importState.value = 'ok'
    saveState.value = 'saved'
    importOkMsg.value =
      result.available > 1
        ? `Canvas preenchido com a 1ª oportunidade (${result.available} no arquivo). Use Importar JSON na lista para criar todas.`
        : 'JSON importado com sucesso.'
    window.setTimeout(() => {
      if (importState.value === 'ok') importState.value = 'idle'
      if (saveState.value === 'saved') saveState.value = 'idle'
    }, 4000)
  } catch (e) {
    importState.value = 'error'
    importError.value = e instanceof Error ? e.message : 'Falha na importação.'
  }
}

function persist(): Promise<void> {
  if (!projectId.value) return Promise.resolve()
  return autosave.save()
}

onMounted(async () => {
  document.addEventListener('pointerdown', onDocPointerDown)
  try {
    const p = await getCanvasProject(projectId.value)
    applyProject(p)
    if ((p.tows_ids || []).length || (p.swot_item_ids || []).length) originOpen.value = true
    void loadOrigin(p)
    if ((p.kr_ids || []).length) krSectionOpen.value = true
    void loadActiveOkrCycle()
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Erro ao carregar projeto.'
    if (String(error.value).includes('nao encontrado') || String(error.value).includes('não encontrado')) {
      setTimeout(() => router.push('/projetos'), 1500)
    }
  } finally {
    loading.value = false
  }
})

onUnmounted(() => {
  document.removeEventListener('pointerdown', onDocPointerDown)
})
</script>

<template>
  <div class="page">
    <div class="toolbar">
      <RouterLink to="/projetos" class="back">← Projetos</RouterLink>
      <div class="toolbar-actions">
        <input
          ref="fileInput"
          type="file"
          accept="application/json,.json"
          class="sr-only"
          @change="onImportFile"
        />
        <button
          type="button"
          class="import-btn"
          :disabled="loading || importState === 'importing'"
          @click="openImportPicker"
        >
          {{ importState === 'importing' ? 'Importando…' : 'Importar JSON' }}
        </button>
        <div class="save-status">
          <span v-if="saveState === 'saving'">Salvando…</span>
          <span v-else-if="saveState === 'saved'" class="ok">Salvo</span>
          <span v-else-if="saveState === 'error'" class="err">{{ saveError || 'Erro ao salvar' }}</span>
          <span v-else class="muted">Salva ao sair do campo</span>
        </div>
      </div>
    </div>

    <div v-if="importState === 'error'" class="banner err">{{ importError }}</div>
    <div v-else-if="importState === 'ok'" class="banner ok">{{ importOkMsg }}</div>

    <div v-if="loading" class="state">Carregando canvas…</div>
    <div v-else-if="error" class="state err">{{ error }}</div>

    <div v-else class="sheet">
      <header class="sheet-header">
        <div>
          <div class="brand">Valorian · Instrumento estratégico</div>
          <h1>
            Canvas de Oportunidades de IA
            <span>por área de negócio</span>
          </h1>
          <p class="subtitle">Um canvas por área. Preencha na ordem 01 → 08: da dor real à decisão de investir.</p>
          <label class="title-field">
            <span>Nome do projeto</span>
            <input v-model="form.title" type="text" maxlength="200" @blur="persist" />
          </label>
        </div>
        <div class="meta">
          <label>
            <span>Área de negócio</span>
            <input v-model="form.area_negocio" type="text" placeholder="Ex.: Comercial" maxlength="200" @blur="persist" />
          </label>
          <label>
            <span>Responsável</span>
            <input v-model="form.responsavel" type="text" placeholder="Nome" maxlength="200" @blur="persist" />
          </label>
          <label>
            <span>Data</span>
            <input
              :value="form.data"
              type="text"
              inputmode="numeric"
              placeholder="dd/mm/aaaa"
              maxlength="10"
              autocomplete="off"
              @input="onDateInput"
              @blur="persist"
            />
          </label>
          <label>
            <span>Objetivo estratégico da área</span>
            <input
              v-model="form.objetivo_estrategico"
              type="text"
              placeholder="O que essa área precisa entregar"
              maxlength="2000"
              @blur="persist"
            />
          </label>
        </div>
        <label class="head-justify">
          <span>Como este projeto trata as estratégias TOWS</span>
          <textarea
            v-model="form.justificativa_tows"
            rows="3"
            maxlength="4000"
            placeholder="Ex.: executa a ofensiva F×O de usar o patrocínio executivo para lançar o copiloto de atendimento antes do concorrente; e cobre parte da fraqueza de dados dispersos ao consolidar o histórico de tickets."
            @blur="persist"
          />
          <em class="head-justify-hint">
            Justifique o vínculo: que iniciativas do bloco 00 este projeto executa, até onde ele
            entrega cada uma e o que fica de fora.
            <template v-if="form.tows_ids.length">
              {{ form.tows_ids.length }} iniciativa(s) vinculada(s).
            </template>
          </em>
        </label>
      </header>

      <section class="origin">
        <button
          type="button"
          class="origin-head"
          :aria-expanded="originOpen"
          @click="originOpen = !originOpen"
        >
          <span class="num">00</span>
          <span class="cell-title origin-title">Origem estratégica · TOWS</span>
          <span v-if="form.tows_ids.length" class="origin-count">
            {{ form.tows_ids.length }} iniciativa(s)
          </span>
          <span v-else class="origin-count muted">nenhuma iniciativa vinculada</span>
          <span class="origin-caret" aria-hidden="true">{{ originOpen ? '−' : '+' }}</span>
        </button>

        <div v-if="!originOpen && selectedInitiatives.length" class="origin-chips">
          <span v-for="init in selectedInitiatives" :key="init.id" class="origin-chip">
            <b>{{ init.groupLabel }}</b>{{ init.acao }}
          </span>
        </div>

        <div v-if="originOpen" class="origin-body">
          <p class="hint">
            Marque as iniciativas da matriz TOWS que este projeto executa. O vínculo aparece no
            Mapa Estratégico ligando maturidade → SWOT → este canvas.
          </p>

          <div v-if="swotError" class="origin-err">{{ swotError }}</div>

          <p v-if="swotLoading" class="origin-none">Carregando estratégias…</p>

          <p v-else-if="!swotList.length" class="origin-none">
            Nenhuma SWOT criada ainda.
            <RouterLink to="/swot" class="origin-link">Abrir SWOT de IA</RouterLink>
          </p>

          <template v-else-if="swot">
            <label v-if="swotList.length > 1" class="origin-select">
              <span>SWOT de origem</span>
              <select :value="swot.id" @change="onSelectSwot">
                <option v-for="s in swotList" :key="s.id" :value="s.id">
                  {{ s.veredito_titulo || 'SWOT sem veredito' }} · {{ s.tows_count }} estratégia(s)
                </option>
              </select>
            </label>

            <div class="origin-groups">
              <div v-for="group in TOWS_GROUPS" :key="group.field" class="origin-group">
                <div class="origin-group-head">
                  <b>{{ group.label }}</b>
                  <span>{{ group.hint }}</span>
                </div>
                <p v-if="!(swot[group.field] || []).length" class="origin-none">
                  Sem estratégias neste cruzamento.
                </p>
                <ul v-else class="origin-list">
                  <li v-for="(init, initIdx) in swot[group.field]" :key="init.id || initIdx">
                    <label class="origin-item" :class="{ active: isTowsSelected(init.id) }">
                      <input
                        type="checkbox"
                        :checked="isTowsSelected(init.id)"
                        :disabled="!init.id"
                        @change="toggleTows(init.id)"
                      />
                      <span class="origin-item-body">
                        <span class="origin-acao">{{ init.acao || '—' }}</span>
                        <span v-if="crossingLabel(init)" class="origin-cross">
                          {{ crossingLabel(init) }}
                        </span>
                      </span>
                    </label>
                  </li>
                </ul>
              </div>
            </div>

            <div v-if="selectedItems.length" class="origin-items">
              <span class="origin-items-label">Itens SWOT vinculados</span>
              <span v-for="entry in selectedItems" :key="entry.id" class="origin-chip">
                <b>{{ SWOT_QUADRANT_LABEL[entry.item.quadrant] }}</b>{{ entry.item.texto }}
                <button
                  type="button"
                  class="origin-chip-x"
                  title="Remover vínculo"
                  @click="removeSwotItemLink(entry.id)"
                >×</button>
              </span>
            </div>
          </template>
        </div>
      </section>

      <section class="origin">
        <button
          type="button"
          class="origin-head"
          :aria-expanded="krSectionOpen"
          @click="krSectionOpen = !krSectionOpen"
        >
          <span class="num">00</span>
          <span class="cell-title origin-title">Key Results (OKR) endereçados</span>
          <span v-if="form.kr_ids.length" class="origin-count">
            {{ form.kr_ids.length }} resultado(s)
          </span>
          <span v-else class="origin-count muted">nenhum Key Result vinculado</span>
          <span class="origin-caret" aria-hidden="true">{{ krSectionOpen ? '−' : '+' }}</span>
        </button>

        <div v-if="!krSectionOpen && selectedKeyResults.length" class="origin-chips">
          <span v-for="entry in selectedKeyResults" :key="entry.id" class="origin-chip">
            <b>{{ entry.kr.objetivoTitulo }}</b>{{ entry.kr.titulo }}
          </span>
        </div>

        <div v-if="krSectionOpen" class="origin-body">
          <p class="hint">
            Marque os Key Results que este projeto endereça. O vínculo aparece no Mapa
            Estratégico ligando o Objective ao Key Result e a este canvas.
          </p>

          <div v-if="okrError" class="origin-err">{{ okrError }}</div>
          <p v-if="okrLoading" class="origin-none">Carregando ciclo OKR…</p>
          <p v-else-if="!okrCycle" class="origin-none">
            Nenhum ciclo OKR ativo.
            <RouterLink to="/okrs" class="origin-link">Abrir painel de OKR</RouterLink>
          </p>
          <p v-else-if="!okrCycle.objectives.length" class="origin-none">
            O ciclo ativo ({{ okrCycle.label }}) ainda não tem Objectives.
            <RouterLink :to="`/okrs/${okrCycle.id}`" class="origin-link">Editar ciclo</RouterLink>
          </p>
          <div v-else class="origin-groups">
            <div v-for="obj in okrCycle.objectives" :key="obj.id" class="origin-group">
              <div class="origin-group-head">
                <b>{{ obj.titulo }}</b>
              </div>
              <p v-if="!obj.key_results.length" class="origin-none">Sem Key Results neste objetivo.</p>
              <ul v-else class="origin-list">
                <li v-for="kr in obj.key_results" :key="kr.id">
                  <label class="origin-item" :class="{ active: isKrSelected(kr.id) }">
                    <input
                      type="checkbox"
                      :checked="isKrSelected(kr.id)"
                      @change="toggleKr(kr.id)"
                    />
                    <span class="origin-item-body">
                      <span class="origin-acao">{{ kr.titulo || '—' }}</span>
                      <span class="origin-cross">{{ kr.progress_pct.toFixed(0) }}% concluído</span>
                    </span>
                  </label>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      <div class="grid">
        <div class="cell c4 band-diag">
          <span class="num">01</span>
          <div class="cell-title">Contexto da área</div>
          <div class="hint">KPIs e processos-chave. Onde essa área cria ou destrói valor hoje?</div>
          <ul class="item-list">
            <li v-for="(item, idx) in form.contexto" :key="'c' + idx" class="item-row">
              <textarea
                :value="item"
                class="item-input"
                rows="1"
                maxlength="500"
                :ref="(el) => autosizeItem(el as HTMLTextAreaElement | null)"
                @input="autosizeItem"
                @blur="onItemBlur('contexto', idx, $event)"
              />
              <button type="button" class="item-remove" title="Remover" @click="removeItem('contexto', idx)">×</button>
            </li>
          </ul>
          <div class="item-add">
            <input
              v-model="drafts.contexto"
              type="text"
              maxlength="500"
              placeholder="Adicionar item…"
              @keydown="onDraftKeydown('contexto', $event)"
            />
            <button type="button" @click="addItem('contexto')">+</button>
          </div>
        </div>
        <div class="cell c4 band-diag">
          <span class="num">02</span>
          <div class="cell-title">Dores &amp; gargalos</div>
          <div class="hint">Atrito, retrabalho, erro, custo, lentidão. <strong>Descreva a dor — não a solução.</strong></div>
          <ul class="item-list">
            <li v-for="(item, idx) in form.dores" :key="'d' + idx" class="item-row">
              <textarea
                :value="item"
                class="item-input"
                rows="1"
                maxlength="500"
                :ref="(el) => autosizeItem(el as HTMLTextAreaElement | null)"
                @input="autosizeItem"
                @blur="onItemBlur('dores', idx, $event)"
              />
              <button type="button" class="item-remove" title="Remover" @click="removeItem('dores', idx)">×</button>
            </li>
          </ul>
          <div class="item-add">
            <input
              v-model="drafts.dores"
              type="text"
              maxlength="500"
              placeholder="Adicionar item…"
              @keydown="onDraftKeydown('dores', $event)"
            />
            <button type="button" @click="addItem('dores')">+</button>
          </div>
        </div>
        <div class="cell c4 band-diag cell-last">
          <span class="num">03</span>
          <div class="cell-title">Oportunidade de IA</div>
          <div class="hint">Em uma frase: o que a IA faria e qual dor do bloco 02 ela ataca.</div>
          <ul class="item-list">
            <li v-for="(item, idx) in form.oportunidade" :key="'o' + idx" class="item-row">
              <textarea
                :value="item"
                class="item-input"
                rows="1"
                maxlength="500"
                :ref="(el) => autosizeItem(el as HTMLTextAreaElement | null)"
                @input="autosizeItem"
                @blur="onItemBlur('oportunidade', idx, $event)"
              />
              <button type="button" class="item-remove" title="Remover" @click="removeItem('oportunidade', idx)">×</button>
            </li>
          </ul>
          <div class="item-add">
            <input
              v-model="drafts.oportunidade"
              type="text"
              maxlength="500"
              placeholder="Adicionar item…"
              @keydown="onDraftKeydown('oportunidade', $event)"
            />
            <button type="button" @click="addItem('oportunidade')">+</button>
          </div>
          <div class="chips">
            <button
              v-for="t in typeOptions"
              :key="t"
              type="button"
              class="chip"
              :class="{ active: form.oportunidade_tipos.includes(t) }"
              @click="toggleType(t)"
            >
              {{ t }}
            </button>
          </div>
        </div>

        <div
          v-for="(cell, cellIdx) in EVAL_CELLS"
          :key="cell.field"
          class="cell c-eval band-eval"
          :class="{ 'cell-last': cellIdx === EVAL_CELLS.length - 1, 'help-open': openHelp === cell.field }"
        >
          <button
            type="button"
            class="cell-help-btn"
            :aria-expanded="openHelp === cell.field"
            :aria-label="`Ajuda · ${cell.title}`"
            @click="toggleHelp(cell.field, $event)"
          >
            ?
          </button>
          <div
            v-if="openHelp === cell.field"
            class="cell-help"
            role="dialog"
            :aria-label="`Banco de itens · ${cell.title}`"
          >
            <div class="cell-help-head">
              <span class="cell-help-num">{{ cell.num }}</span>
              <div>
                <strong>{{ cell.title }}</strong>
                <span class="cell-help-tag">{{ cell.tagline }}</span>
              </div>
            </div>
            <p class="cell-help-answers">{{ cell.answers }}</p>
            <p class="cell-help-pulls">{{ cell.pulls }}</p>
            <p class="cell-help-note">
              Perguntas-guia e itens de exemplo — copie, adapte à sua área e descarte o que não se aplica.
            </p>
            <div class="cell-help-section">Perguntas-guia</div>
            <ul class="cell-help-questions">
              <li v-for="(q, qi) in cell.questions" :key="'q' + qi">{{ q }}</li>
            </ul>
            <div class="cell-help-section">Itens de exemplo</div>
            <ul class="cell-help-examples">
              <li v-for="(ex, ei) in cell.examples" :key="'e' + ei">{{ ex }}</li>
            </ul>
            <p class="cell-help-alert"><strong>Sinal de alerta.</strong> {{ cell.alert }}</p>
          </div>
          <span class="num">{{ cell.num }}</span>
          <div class="cell-title">{{ cell.title }}</div>
          <div class="hint">{{ cell.hint }}</div>
          <ul class="item-list">
            <li v-for="(item, idx) in form[cell.field]" :key="cell.field + idx" class="item-row">
              <textarea
                :value="item"
                class="item-input"
                rows="1"
                maxlength="500"
                :ref="(el) => autosizeItem(el as HTMLTextAreaElement | null)"
                @input="autosizeItem"
                @blur="onItemBlur(cell.field, idx, $event)"
              />
              <button type="button" class="item-remove" title="Remover" @click="removeItem(cell.field, idx)">×</button>
            </li>
          </ul>
          <div class="item-add">
            <input
              v-model="drafts[cell.field]"
              type="text"
              maxlength="500"
              placeholder="Adicionar item…"
              @keydown="onDraftKeydown(cell.field, $event)"
            />
            <button type="button" @click="addItem(cell.field)">+</button>
          </div>
        </div>
      </div>

      <div class="decision">
        <div class="dec-left">
          <span class="num num-amber">08</span>
          <div class="cell-title">Decisão</div>
          <div class="hint">Preencha 04–07 antes de pontuar. Notas de 1 a 5 — o cruzamento define o quadrante e o próximo passo.</div>
          <div class="scores">
            <div class="score">
              <b>Valor</b>
              <div class="dots">
                <button
                  v-for="n in 5"
                  :key="'v' + n"
                  type="button"
                  class="dot"
                  :class="{ active: form.score_valor === n }"
                  @click="setScore('score_valor', n)"
                >
                  {{ n }}
                </button>
              </div>
            </div>
            <div class="score">
              <b>Viabilidade</b>
              <div class="dots">
                <button
                  v-for="n in 5"
                  :key="'f' + n"
                  type="button"
                  class="dot"
                  :class="{ active: form.score_viabilidade === n }"
                  @click="setScore('score_viabilidade', n)"
                >
                  {{ n }}
                </button>
              </div>
            </div>
          </div>
          <div class="next">
            <label>Próximo passo concreto</label>
            <textarea
              v-model="form.proximo_passo"
              class="write write-sm"
              rows="2"
              placeholder="Ex.: PoC de 3 semanas com dados de faturamento…"
              @blur="persist"
            />
          </div>
        </div>
        <div class="matrix-wrap">
          <div class="matrix-cap">Onde essa oportunidade cai</div>
          <div class="matrix">
            <div class="qy">Valor →</div>
            <div class="q q-bet" :class="{ active: quadrant === 'aposta_estrategica' }">
              <b>Aposta estratégica</b>Alto valor, baixa viab. — planeje e destrave.
            </div>
            <div class="q q-go" :class="{ active: quadrant === 'ganho_rapido' }">
              <b>Ganho rápido</b>Alto valor, alta viab. — faça já.
            </div>
            <div class="q q-avoid" :class="{ active: quadrant === 'evitar' }">
              <b>Evitar · vaidade</b>Baixo valor, baixa viab. — só hype.
            </div>
            <div class="q q-inc" :class="{ active: quadrant === 'incremental' }">
              <b>Incremental</b>Baixo valor, alta viab. — encaixe quando sobrar.
            </div>
            <div /><div class="qx">Viabilidade →</div>
          </div>
        </div>
      </div>

      <footer class="sheet-footer">
        <span>Complementar à <b>SWOT de IA</b> — a SWOT olha a organização; este canvas desce à área.</span>
        <span>Consolide um canvas por área numa <b>matriz de portfólio</b> para priorizar o roadmap.</span>
      </footer>
    </div>
  </div>
</template>

<style scoped>
/* DS-05: @import de fonte removido daqui — era uma requisição bloqueante de
   terceira família tipográfica no meio do CSS de uma rota. As 13 declarações
   de 'Space Grotesk' abaixo foram trocadas pela pilha --sans/--serif já usada
   no resto do produto (DS-01: uma família editorial única). */

.page {
  --ink: #12232e;
  --ink-soft: #3c525f;
  --paper: #f7f5ef;
  --line: #d8d2c6;
  --amber: var(--warn);
  --amber-tint: #f3e7cc;
  --slate: #5b7a86;
  --slate-tint: #e4ecee;
  --teal: #2f6e6a;
  /* DS-01/DS-02: --danger e --ok apontam para os tokens de estado globais
     (eram cores quase-duplicadas de --low/--success com nomes locais). */
  --danger: var(--low);
  --ok: var(--success);
  max-width: 1180px;
  margin: 0 auto;
  padding: 20px 16px 48px;
  color: var(--ink);
}
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
  flex-wrap: wrap;
}
.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.import-btn {
  border: 1px solid var(--bd);
  background: #fff;
  color: var(--k0);
  font-size: 11px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  padding: 6px 12px;
  border-radius: var(--r-pill);
  cursor: pointer;
  font-family: inherit;
}
.import-btn:hover:not(:disabled) {
  border-color: var(--k0);
}
.import-btn:disabled {
  opacity: 0.6;
  cursor: wait;
}
.banner {
  border-radius: 10px;
  padding: 12px 14px;
  margin-bottom: 12px;
  font-size: 13px;
  border: 1px solid var(--bd);
  background: var(--wh);
}
.banner.ok {
  color: #2f6e4a;
  border-color: #bbd3b7;
  background: #e8f0e7;
}
.banner.err {
  color: #8f2b2b;
  border-color: #e2bcbc;
  background: #f8ecec;
}
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
.back {
  color: var(--k0, var(--ink));
  text-decoration: none;
  font-size: 14px;
}
.back:hover {
  text-decoration: underline;
}
.save-status {
  font-size: 12px;
  color: var(--ink-soft);
}
.save-status .ok {
  color: var(--ok);
}
.save-status .err,
.state.err {
  color: var(--danger);
}
.state {
  padding: 40px 0;
  color: var(--ink-soft);
}
.sheet {
  background: var(--paper);
  border: 1px solid var(--line);
  box-shadow: 0 18px 50px -28px rgba(18, 35, 46, 0.45);
}
.sheet-header {
  padding: 26px 30px 22px;
  border-bottom: 3px solid var(--ink);
  display: flex;
  flex-wrap: wrap;
  gap: 22px;
  align-items: flex-end;
  justify-content: space-between;
}
.brand {
  font-family: var(--sans);
  font-weight: 700;
  font-size: 11px;
  letter-spacing: 0.32em;
  text-transform: uppercase;
  color: var(--amber);
  margin-bottom: 8px;
}
h1 {
  font-family: var(--serif);
  font-weight: 700;
  font-size: 27px;
  line-height: 1.08;
  margin: 0;
  max-width: 22ch;
}
h1 span {
  color: var(--slate);
}
.subtitle {
  font-size: 13px;
  color: var(--ink-soft);
  margin-top: 8px;
  max-width: 46ch;
}
.title-field {
  display: block;
  margin-top: 14px;
  max-width: 360px;
}
.title-field span,
.meta label span,
.head-justify > span,
.next label {
  display: block;
  font-size: 10px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--ink-soft);
  font-weight: 600;
  margin-bottom: 2px;
}
.title-field input,
.meta input {
  width: 100%;
  border: none;
  border-bottom: 1.5px dotted var(--slate);
  min-height: 28px;
  font-size: 13px;
  color: var(--ink);
  padding: 2px;
  background: transparent;
  font-family: inherit;
  outline: none;
}
.title-field input:focus,
.meta input:focus,
.write:focus {
  border-bottom-color: var(--amber);
  background: #fffef9;
}
.meta {
  display: grid;
  grid-template-columns: repeat(2, minmax(150px, 1fr));
  gap: 10px 20px;
  min-width: min(320px, 100%);
}
.head-justify {
  flex-basis: 100%;
  display: block;
  padding-top: 14px;
  border-top: 1px dotted var(--line);
}
.head-justify textarea {
  width: 100%;
  min-height: 56px;
  resize: vertical;
  border: 1px solid var(--line);
  border-radius: var(--r-xs);
  background: #fff;
  font-family: inherit;
  font-size: 13px;
  line-height: 1.45;
  color: var(--ink);
  padding: 7px 9px;
  outline: none;
}
.head-justify textarea:focus {
  border-color: var(--amber);
  background: #fffef9;
}
.head-justify-hint {
  display: block;
  margin-top: 4px;
  font-size: 11px;
  line-height: 1.35;
  color: var(--ink-soft);
  font-style: normal;
}

.origin {
  position: relative;
  border-bottom: 1px solid var(--line);
  background: #fffdf8;
}
.origin::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  background: var(--amber);
}
.origin-head {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 12px 16px;
  border: none;
  background: transparent;
  text-align: left;
  font-family: inherit;
  color: var(--ink);
  cursor: pointer;
}
.origin-head .num {
  color: var(--amber);
}
.origin-title {
  margin: 0;
  padding: 0;
}
.origin-count {
  font-size: 11px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  font-weight: 600;
  color: var(--amber);
}
.origin-count.muted {
  color: var(--ink-soft);
  font-weight: 500;
}
.origin-caret {
  margin-left: auto;
  font-size: 16px;
  line-height: 1;
  color: var(--ink-soft);
}
.origin-chips,
.origin-items {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  padding: 0 16px 12px;
}
.origin-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  max-width: 100%;
  padding: 3px 9px;
  border: 1px solid #e3ce9c;
  border-radius: 20px;
  background: var(--amber-tint);
  font-size: 11px;
  line-height: 1.3;
  color: var(--ink);
}
.origin-chip b {
  font-family: var(--sans);
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--amber);
}
.origin-chip-x {
  border: none;
  background: transparent;
  color: var(--ink-soft);
  font-size: 13px;
  line-height: 1;
  padding: 0;
}
.origin-chip-x:hover {
  color: var(--danger);
}
.origin-body {
  padding: 0 16px 16px;
}
.origin-body .hint {
  max-width: 70ch;
  margin-bottom: 10px;
}
.origin-err {
  margin-bottom: 10px;
  padding: 8px 10px;
  border-left: 3px solid var(--danger);
  background: #f8eee8;
  font-size: 12px;
  color: var(--ink);
}
.origin-none {
  font-size: 12px;
  color: var(--ink-soft);
  margin: 4px 0;
}
.origin-link {
  color: var(--amber);
  text-decoration: underline;
}
.origin-select {
  display: block;
  max-width: 420px;
  margin-bottom: 12px;
}
.origin-select span {
  display: block;
  font-size: 10px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--ink-soft);
  font-weight: 600;
  margin-bottom: 3px;
}
.origin-select select {
  width: 100%;
  border: 1px solid var(--line);
  border-radius: var(--r-xs);
  background: #fff;
  font-family: inherit;
  font-size: 13px;
  color: var(--ink);
  padding: 6px 8px;
}
.origin-groups {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 12px;
}
.origin-group {
  border: 1px solid var(--line);
  border-radius: var(--r-xs);
  background: #fff;
  padding: 10px;
}
.origin-group-head b {
  display: block;
  font-family: var(--sans);
  font-size: 11px;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--teal);
}
.origin-group-head span {
  display: block;
  font-size: 11px;
  color: var(--ink-soft);
  margin-bottom: 6px;
}
.origin-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.origin-item {
  display: flex;
  gap: 8px;
  align-items: flex-start;
  padding: 6px 8px;
  border: 1px solid transparent;
  border-radius: var(--r-xs);
  cursor: pointer;
}
.origin-item:hover {
  background: #faf8f2;
}
.origin-item.active {
  border-color: #e3ce9c;
  background: var(--amber-tint);
}
.origin-item input {
  margin-top: 2px;
  flex-shrink: 0;
  accent-color: var(--amber);
}
.origin-item-body {
  min-width: 0;
}
.origin-acao {
  display: block;
  font-size: 12px;
  line-height: 1.35;
  color: var(--ink);
}
.origin-cross {
  display: block;
  margin-top: 2px;
  font-size: 11px;
  line-height: 1.3;
  color: var(--ink-soft);
  font-style: italic;
}
.origin-items {
  padding: 12px 0 0;
}
.origin-items-label {
  font-size: 10px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--ink-soft);
  font-weight: 600;
}

.grid {
  display: grid;
  grid-template-columns: repeat(12, 1fr);
}
.cell {
  border-right: 1px solid var(--line);
  border-bottom: 1px solid var(--line);
  padding: 14px 16px 16px;
  min-height: 132px;
  position: relative;
  background: var(--paper);
}
.cell::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  background: var(--stage, var(--slate));
}
.band-diag {
  --stage: var(--slate);
}
.band-eval {
  --stage: var(--teal);
}
.cell-last {
  border-right: none;
}
.cell.help-open {
  z-index: 8;
}
.cell-help-btn {
  position: absolute;
  top: 10px;
  right: 10px;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  border: 1px solid var(--line);
  background: #fff;
  color: var(--teal);
  font-family: var(--sans);
  font-weight: 700;
  font-size: 13px;
  line-height: 1;
  cursor: pointer;
  z-index: 3;
  display: grid;
  place-content: center;
  padding: 0;
}
.cell-help-btn:hover,
.cell-help-btn[aria-expanded='true'] {
  border-color: var(--teal);
  background: #eef6f5;
}
.cell-help {
  position: absolute;
  top: 38px;
  right: 8px;
  width: min(340px, calc(100vw - 48px));
  max-height: min(420px, 70vh);
  overflow: auto;
  background: #fffcf7;
  border: 1px solid var(--line);
  box-shadow: 0 12px 28px rgba(18, 35, 46, 0.18);
  padding: 12px 14px;
  z-index: 9;
  border-radius: var(--r-xs);
}
.cell-help-head {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  margin-bottom: 8px;
}
.cell-help-num {
  font-family: var(--sans);
  font-weight: 700;
  font-size: 14px;
  color: var(--teal);
  line-height: 1.2;
}
.cell-help-head strong {
  display: block;
  font-size: 13px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--ink);
}
.cell-help-tag {
  display: block;
  margin-top: 2px;
  font-size: 11px;
  font-style: italic;
  color: var(--ink-soft);
}
.cell-help-answers {
  margin: 0 0 6px;
  font-size: 12px;
  line-height: 1.4;
  color: var(--ink);
}
.cell-help-pulls {
  margin: 0 0 8px;
  font-size: 11px;
  font-weight: 600;
  color: var(--teal);
}
.cell-help-note {
  margin: 0 0 10px;
  font-size: 11px;
  line-height: 1.4;
  color: var(--ink-soft);
  font-style: italic;
}
.cell-help-section {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--ink-soft);
  margin: 8px 0 4px;
}
.cell-help-questions,
.cell-help-examples {
  list-style: none;
  margin: 0;
  padding: 0;
}
.cell-help-questions li,
.cell-help-examples li {
  position: relative;
  padding: 0 0 6px 12px;
  font-size: 12px;
  line-height: 1.4;
  color: var(--ink);
}
.cell-help-questions li::before,
.cell-help-examples li::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0.45em;
  width: 5px;
  height: 5px;
  border-radius: 1px;
  background: var(--teal);
  transform: rotate(45deg);
}
.cell-help-alert {
  margin: 10px 0 0;
  padding: 8px 10px;
  background: #f8eee8;
  border-left: 3px solid var(--danger, #9c3b2e);
  font-size: 12px;
  line-height: 1.4;
  color: var(--ink);
}
.cell-help-alert strong {
  color: var(--danger, #9c3b2e);
}
.num {
  font-family: var(--sans);
  font-weight: 700;
  font-size: 12px;
  color: var(--stage, var(--slate));
}
.num-amber {
  color: var(--amber);
}
.cell-title {
  font-family: var(--sans);
  font-weight: 600;
  font-size: 14px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin: 2px 0 5px;
  padding-right: 28px;
}
.hint {
  font-size: 11px;
  color: var(--ink-soft);
  line-height: 1.35;
}
.write {
  margin-top: 9px;
  width: 100%;
  min-height: 72px;
  border: none;
  outline: none;
  resize: vertical;
  font-size: 13px;
  color: var(--ink);
  font-family: inherit;
  background: transparent;
  line-height: 1.45;
}
.write-sm {
  min-height: 44px;
}
.item-list {
  list-style: none;
  margin: 10px 0 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.item-row {
  display: flex;
  gap: 4px;
  align-items: flex-start;
}
.item-input {
  flex: 1;
  min-width: 0;
  border: none;
  border-bottom: 1px dotted var(--line);
  background: transparent;
  font-size: 13px;
  color: var(--ink);
  font-family: inherit;
  padding: 4px 2px;
  outline: none;
  resize: none;
  overflow: hidden;
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.4;
  min-height: calc(1.4em + 8px);
  field-sizing: content;
}
.item-input:focus {
  border-bottom-color: var(--amber);
  background: #fffef9;
}
.item-row .item-remove {
  margin-top: 2px;
}
.item-remove {
  flex-shrink: 0;
  width: 24px;
  height: 24px;
  border: none;
  background: transparent;
  color: var(--ink-soft);
  cursor: pointer;
  font-size: 16px;
  line-height: 1;
  border-radius: var(--r-xs);
}
.item-remove:hover {
  color: var(--danger);
  background: #f1e1dd;
}
.item-add {
  display: flex;
  gap: 6px;
  margin-top: 8px;
}
.item-add input {
  flex: 1;
  min-width: 0;
  border: 1px dashed var(--line);
  border-radius: var(--r-xs);
  background: #fff;
  font-size: 12px;
  padding: 6px 8px;
  font-family: inherit;
  color: var(--ink);
  outline: none;
}
.item-add input:focus {
  border-color: var(--amber);
  border-style: solid;
}
.item-add button {
  flex-shrink: 0;
  width: 30px;
  border: 1px solid var(--line);
  border-radius: var(--r-xs);
  background: #fff;
  color: var(--ink);
  cursor: pointer;
  font-size: 16px;
  font-weight: 600;
}
.item-add button:hover {
  border-color: var(--amber);
  color: var(--amber);
}
.c4 {
  grid-column: span 4;
}
.c-eval {
  grid-column: span 3;
}
.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  margin-top: 8px;
}
.chip {
  font-size: 10px;
  border: 1px solid var(--line);
  border-radius: 20px;
  padding: 3px 9px;
  color: var(--ink-soft);
  background: #fff;
  cursor: pointer;
  font-family: inherit;
}
.chip.active {
  border-color: var(--teal);
  background: #e1ebe9;
  color: var(--teal);
  font-weight: 600;
}
.decision {
  display: grid;
  grid-template-columns: 1.15fr 1fr;
}
.dec-left {
  padding: 16px 18px;
  border-right: 1px solid var(--line);
  border-bottom: 1px solid var(--line);
  position: relative;
}
.dec-left::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  background: var(--amber);
}
.scores {
  display: flex;
  gap: 26px;
  margin: 12px 0 6px;
  flex-wrap: wrap;
}
.score b {
  font-family: var(--sans);
  font-size: 11px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--ink-soft);
  display: block;
  margin-bottom: 5px;
}
.dots {
  display: flex;
  gap: 6px;
}
.dot {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: 1.5px solid var(--slate);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: var(--ink-soft);
  font-family: var(--sans);
  font-weight: 600;
  background: #fff;
  cursor: pointer;
}
.dot.active {
  background: var(--amber);
  border-color: var(--amber);
  color: #fff;
}
.next {
  margin-top: 12px;
}
.matrix-wrap {
  padding: 16px 18px;
  border-bottom: 1px solid var(--line);
  display: flex;
  flex-direction: column;
}
.matrix-cap {
  font-family: var(--sans);
  font-weight: 600;
  font-size: 11px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--ink-soft);
  margin-bottom: 9px;
}
.matrix {
  display: grid;
  grid-template-columns: 16px 1fr 1fr;
  grid-template-rows: 1fr 1fr 16px;
  gap: 5px;
  flex: 1;
  min-height: 150px;
}
.qy {
  writing-mode: vertical-rl;
  transform: rotate(180deg);
  font-size: 9px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--ink-soft);
  text-align: center;
  grid-row: span 2;
  align-self: center;
}
.qx {
  font-size: 9px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--ink-soft);
  text-align: center;
  grid-column: 2 / 4;
}
.q {
  border-radius: var(--r-sm);
  padding: 8px 9px;
  font-size: 11px;
  line-height: 1.25;
  border: 1px solid var(--line);
  opacity: 0.72;
  transition: opacity 0.2s, box-shadow 0.2s;
}
.q.active {
  opacity: 1;
  box-shadow: 0 0 0 2px var(--ink);
}
.q b {
  display: block;
  font-family: var(--sans);
  font-size: 11px;
  margin-bottom: 2px;
}
.q-go {
  background: #e8f0e7;
  border-color: #bbd3b7;
}
.q-go b {
  color: var(--ok);
}
.q-bet {
  background: var(--amber-tint);
  border-color: #e3ce9c;
}
.q-bet b {
  color: var(--amber);
}
.q-inc {
  background: var(--slate-tint);
  border-color: #cbd8db;
}
.q-inc b {
  color: var(--slate);
}
.q-avoid {
  background: #f1e1dd;
  border-color: #ddbcb4;
}
.q-avoid b {
  color: var(--danger);
}
.sheet-footer {
  padding: 12px 30px 18px;
  display: flex;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px;
  font-size: 11px;
  color: var(--ink-soft);
}
.sheet-footer b {
  color: var(--amber);
  font-family: var(--sans);
}

@media (max-width: 820px) {
  h1 {
    font-size: 22px;
  }
  .c4,
  .c-eval {
    grid-column: span 12;
  }
  .cell-last {
    border-right: 1px solid var(--line);
  }
  .decision {
    grid-template-columns: 1fr;
  }
  .dec-left {
    border-right: none;
  }
  .meta {
    grid-template-columns: 1fr;
    width: 100%;
  }
  .sheet-header {
    padding: 20px 16px;
  }
}
</style>
