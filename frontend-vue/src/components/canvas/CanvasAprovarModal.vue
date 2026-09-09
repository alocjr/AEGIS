<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import AppModal from '@/components/ui/AppModal.vue'
import AppButton from '@/components/ui/AppButton.vue'
import {
  CANVAS_PERIODICIDADES,
  type CanvasAprovarProjetoPayload,
  type CanvasPeriodicidade,
} from '@/api/canvasProjects'

const props = defineProps<{
  open: boolean
  saving?: boolean
  error?: string | null
  alreadyApproved?: boolean
  initialComentario?: string
  initialDataInicioReal?: string
  initialPeriodicidade?: CanvasPeriodicidade | ''
}>()

const emit = defineEmits<{
  close: []
  submit: [CanvasAprovarProjetoPayload]
}>()

const comentario = ref('')
const dataInicioReal = ref('')
const periodicidade = ref<CanvasPeriodicidade | ''>('')

watch(
  () => props.open,
  (open) => {
    if (!open) return
    comentario.value = props.initialComentario || ''
    dataInicioReal.value = props.initialDataInicioReal || ''
    periodicidade.value = props.initialPeriodicidade || ''
  }
)

const canSubmit = computed(
  () =>
    !!comentario.value.trim() &&
    !!dataInicioReal.value &&
    !!periodicidade.value &&
    !props.saving
)

function onSubmit() {
  if (!canSubmit.value || !periodicidade.value) return
  emit('submit', {
    comentario: comentario.value.trim(),
    data_inicio_real: dataInicioReal.value,
    periodicidade: periodicidade.value,
  })
}
</script>

<template>
  <AppModal
    :open="open"
    :title="alreadyApproved ? 'Atualizar aprovação' : 'Aprovar projeto'"
    size="md"
    @close="emit('close')"
  >
    <p class="hint">
      Registro C-level: quem autorizou o investimento, a data real de início e o ritmo de acompanhamento.
      Projetos aprovados passam a aparecer no Mapa Estratégico.
    </p>
    <label class="field">
      <span>Quem aprovou</span>
      <textarea
        v-model="comentario"
        rows="3"
        maxlength="1000"
        placeholder="Ex.: Ana (CEO), Bruno (CFO) e Carla (CHRO) no comitê de 09/04."
      />
    </label>
    <div class="row">
      <label class="field">
        <span>Data de início real</span>
        <input v-model="dataInicioReal" type="date" />
      </label>
      <label class="field">
        <span>Acompanhamento</span>
        <select v-model="periodicidade">
          <option value="">Periodicidade</option>
          <option v-for="p in CANVAS_PERIODICIDADES" :key="p.id" :value="p.id">{{ p.label }}</option>
        </select>
      </label>
    </div>
    <p v-if="error" class="err">{{ error }}</p>
    <template #footer>
      <AppButton variant="secondary" :disabled="saving" @click="emit('close')">Cancelar</AppButton>
      <AppButton variant="primary" :disabled="!canSubmit" @click="onSubmit">
        {{ saving ? 'Salvando…' : alreadyApproved ? 'Salvar aprovação' : 'Aprovar projeto' }}
      </AppButton>
    </template>
  </AppModal>
</template>

<style scoped>
.hint {
  margin: 0 0 14px;
  font-size: 13px;
  color: var(--k5);
  line-height: 1.45;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 12px;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--k5);
}
.field textarea,
.field input,
.field select {
  font-family: inherit;
  font-size: 14px;
  font-weight: 500;
  letter-spacing: 0;
  text-transform: none;
  color: var(--k0);
  border: 1px solid var(--bd);
  border-radius: var(--r-md);
  padding: 8px 10px;
  background: #fff;
}
.field textarea {
  resize: vertical;
  min-height: 72px;
  line-height: 1.4;
}
.row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.err {
  color: #8f2b2b;
  font-size: 13px;
  margin: 0 0 4px;
}
@media (max-width: 520px) {
  .row {
    grid-template-columns: 1fr;
  }
}
</style>
