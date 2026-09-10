<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import AppModal from '@/components/ui/AppModal.vue'
import AppButton from '@/components/ui/AppButton.vue'
import { cloneCanvasProject, type CanvasProject } from '@/api/canvasProjects'
import { useAuthStore } from '@/stores/auth'

const props = defineProps<{
  open: boolean
  projectId: string
  sourceTitle: string
}>()

const emit = defineEmits<{
  close: []
  cloned: [CanvasProject & { dest_organization_id: string }]
}>()

const auth = useAuthStore()
const orgs = computed(() => {
  const list = auth.user?.organizations ?? []
  if (list.length) return list
  const id = auth.user?.organization_id
  if (!id) return []
  return [{ id, name: auth.user?.organization_name || 'Organização atual', is_org_admin: false }]
})
const currentOrgId = computed(() => auth.user?.organization_id || '')
const destOrgId = ref('')
const title = ref('')
const saving = ref(false)
const error = ref<string | null>(null)

watch(
  () => props.open,
  (open) => {
    if (!open) return
    error.value = null
    saving.value = false
    destOrgId.value = currentOrgId.value || orgs.value[0]?.id || ''
    const base = (props.sourceTitle || 'Novo projeto').trim() || 'Novo projeto'
    title.value = base.endsWith(' (cópia)') ? base : `${base} (cópia)`
  }
)

const destIsOther = computed(
  () => !!destOrgId.value && destOrgId.value !== currentOrgId.value
)

const canSubmit = computed(
  () => !!props.projectId && !!destOrgId.value && !!title.value.trim() && !saving.value
)

async function onSubmit() {
  if (!canSubmit.value) return
  saving.value = true
  error.value = null
  try {
    const cloned = await cloneCanvasProject(props.projectId, {
      organization_id: destOrgId.value,
      title: title.value.trim(),
    })
    emit('cloned', { ...cloned, dest_organization_id: destOrgId.value })
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Erro ao clonar o projeto.'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <AppModal :open="open" title="Clonar projeto" size="sm" @close="emit('close')">
    <p class="hint">
      Cria uma cópia do canvas (incluindo o cronograma) na organização escolhida.
      Aprovação executiva e vínculo com o portfólio de Governança não são copiados.
    </p>
    <label class="field">
      <span>Organização destino</span>
      <select v-model="destOrgId">
        <option v-for="org in orgs" :key="org.id" :value="org.id">
          {{ org.name }}{{ org.id === currentOrgId ? ' · atual' : '' }}
        </option>
      </select>
    </label>
    <p v-if="destIsOther" class="hint warn">
      Na outra organização, vínculos com SWOT e OKR não são levados — esses artefatos
      pertencem à origem. Depois de clonar, a sessão passa para o destino.
    </p>
    <label class="field">
      <span>Nome da cópia</span>
      <input v-model="title" type="text" maxlength="200" />
    </label>
    <p v-if="error" class="err">{{ error }}</p>
    <template #footer>
      <AppButton variant="secondary" :disabled="saving" @click="emit('close')">Cancelar</AppButton>
      <AppButton variant="primary" :disabled="!canSubmit" @click="onSubmit">
        {{ saving ? 'Clonando…' : 'Clonar' }}
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
.hint.warn {
  color: var(--k3);
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
.err {
  color: #8f2b2b;
  font-size: 13px;
  margin: 0 0 4px;
}
</style>
