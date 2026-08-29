<script setup lang="ts">
import { useStrategicMap } from '@/composables/useStrategicMap'
import MapaBody from '@/components/mapa/MapaBody.vue'

const editor = useStrategicMap()
</script>

<template>
  <MapaBody :editor="editor" />
</template>
