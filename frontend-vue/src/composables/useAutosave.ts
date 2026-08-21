import { onBeforeUnmount, onMounted } from 'vue'
import { onBeforeRouteLeave } from 'vue-router'
import { ref } from 'vue'

/**
 * Estado de gravação padrão do produto — mesma união usada nas 5 telas com
 * autosave (Maturidade, SWOT, Canvas, OKR, Governança) antes desta extração.
 */
export type AutosaveState = 'idle' | 'saving' | 'saved' | 'error'

export interface UseAutosaveOptions {
  /** ms de debounce padrão para scheduleSave(); save() sempre roda na hora. */
  delay?: number
  /** ms até saveState voltar a 'idle' depois de 'saved'. 0 desliga o auto-reset. */
  idleAfter?: number
  /** Mensagem usada quando saveFn rejeita sem um Error com .message. */
  fallbackError?: string
  /**
   * Registra `beforeunload` (aviso nativo do navegador ao fechar/recarregar
   * com gravação pendente) e `onBeforeRouteLeave` (grava antes de navegar
   * para outra rota, em vez de descartar silenciosamente). Default: true.
   */
  guardExit?: boolean
}

/**
 * Autosave com fila de uma gravação — extraído do padrão que já existia,
 * repetido e divergente, em AiMaturityView, SwotAnalysisView,
 * ProjetoCanvasView e GovernanceSystemView (AR-03). GovernanceSystemView não
 * tinha NENHUMA guarda de concorrência — duas edições rápidas podiam
 * disparar dois PATCH e a resposta mais lenta vencer por último. As outras
 * três reimplementavam a mesma fila com pequenas divergências de detalhe.
 *
 * `OkrCycleEditorView` fica de fora desta extração de propósito: seu
 * autosave já é correto e tem uma necessidade real e específica — rastrear
 * gerações de edição para reconciliar IDs atribuídos pelo servidor no
 * primeiro save — que um composable genérico não deveria tentar generalizar.
 * Ele continua sendo a referência; ver `OkrCycleEditorView.vue`.
 *
 * Uso:
 *   const autosave = useAutosave(async () => {
 *     const updated = await updateThing(id.value, { ...form.value })
 *     applyDoc(updated)
 *   })
 *   const saveState = autosave.saveState   // reaproveita o nome já usado nas views
 *   const saveError = autosave.error
 *   watch(form, () => autosave.scheduleSave(400), { deep: true })
 *   // ou, para ações estruturais (sem esperar o debounce):
 *   function onAdd() { list.value.push(x); void autosave.save() }
 */
export function useAutosave(saveFn: () => Promise<void>, options: UseAutosaveOptions = {}) {
  const { delay = 0, idleAfter = 1600, fallbackError = 'Erro ao salvar.', guardExit = true } = options

  const saveState = ref<AutosaveState>('idle')
  const error = ref<string | null>(null)

  let inFlight = false
  let pending = false
  let currentChain: Promise<void> | null = null
  let debounceTimer: ReturnType<typeof setTimeout> | null = null
  let idleTimer: ReturnType<typeof setTimeout> | null = null

  function clearIdleTimer() {
    if (idleTimer) {
      clearTimeout(idleTimer)
      idleTimer = null
    }
  }

  function clearDebounce() {
    if (debounceTimer) {
      clearTimeout(debounceTimer)
      debounceTimer = null
    }
  }

  function runOnce(): Promise<void> {
    clearIdleTimer()
    saveState.value = 'saving'
    error.value = null
    return saveFn()
      .then(() => {
        saveState.value = 'saved'
        if (idleAfter > 0) {
          idleTimer = setTimeout(() => {
            if (saveState.value === 'saved') saveState.value = 'idle'
          }, idleAfter)
        }
      })
      .catch((e: unknown) => {
        saveState.value = 'error'
        error.value = e instanceof Error ? e.message : fallbackError
      })
  }

  /** Grava agora. Se já houver uma gravação em curso, entra na fila (só a
   * mais recente é reexecutada — nunca duas em paralelo). Retorna uma
   * promise que só resolve quando a fila esvaziar de verdade. */
  function save(): Promise<void> {
    clearDebounce()
    if (inFlight) {
      pending = true
      return currentChain ?? Promise.resolve()
    }
    inFlight = true
    currentChain = runOnce().finally(() => {
      inFlight = false
      if (pending) {
        pending = false
        return save()
      }
      currentChain = null
    })
    return currentChain
  }

  /** Agenda uma gravação debounced; chamadas repetidas adiam a anterior. */
  function scheduleSave(ms: number = delay): void {
    clearDebounce()
    debounceTimer = setTimeout(() => {
      debounceTimer = null
      void save()
    }, ms)
  }

  /** Espera a fila esvaziar — usar antes de sair da tela ou de uma ação que
   * depende do documento estar persistido (ex.: gerar SWOT a partir do
   * diagnóstico). Não força um save novo se não houver nada pendente. */
  function flush(): Promise<void> {
    if (debounceTimer) return save()
    if (inFlight) return currentChain ?? Promise.resolve()
    return Promise.resolve()
  }

  if (guardExit) {
    const hasPendingWork = () => inFlight || pending || debounceTimer !== null

    function onBeforeUnload(e: BeforeUnloadEvent) {
      if (!hasPendingWork()) return
      e.preventDefault()
      e.returnValue = ''
    }

    onMounted(() => {
      window.addEventListener('beforeunload', onBeforeUnload)
    })
    onBeforeUnmount(() => {
      window.removeEventListener('beforeunload', onBeforeUnload)
    })
    // Navegação dentro do app: grava o que estiver pendente em vez de
    // descartar (era o comportamento antes desta extração).
    onBeforeRouteLeave(async () => {
      await flush()
    })
  }

  return { saveState, error, save, scheduleSave, flush }
}
