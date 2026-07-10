<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  photoUrl: { type: String, default: '' },
  label: { type: String, default: 'Photo d\'identité' },
  hint: { type: String, default: 'Format 3×4 · JPEG, PNG ou WebP · max 2 Mo' },
  compact: { type: Boolean, default: false },
})

const emit = defineEmits(['upload'])

const preview = ref(props.photoUrl || '')
const inputRef = ref(null)
const dragging = ref(false)

watch(() => props.photoUrl, (v) => {
  preview.value = v || ''
})

function openPicker() {
  inputRef.value?.click()
}

function onDragOver(e) {
  e.preventDefault()
  dragging.value = true
}

function onDragLeave() {
  dragging.value = false
}

function onDrop(e) {
  e.preventDefault()
  dragging.value = false
  const file = e.dataTransfer?.files?.[0]
  if (file) emit('upload', file)
}

function onFileChange(e) {
  const file = e.target.files?.[0]
  if (file) {
    preview.value = URL.createObjectURL(file)
    emit('upload', file)
  }
  e.target.value = ''
}
</script>

<template>
  <div :class="compact ? 'flex items-center gap-4' : ''">
    <div
      class="group relative mx-auto overflow-hidden rounded-2xl border-2 border-dashed transition"
      :class="[
        compact ? 'h-28 w-21 shrink-0' : 'mx-0 h-52 w-40',
        dragging
          ? 'border-primary-500 bg-primary-50 dark:border-primary-400 dark:bg-primary-950/40'
          : 'border-slate-300 bg-slate-50 hover:border-primary-400 dark:border-slate-600 dark:bg-slate-900/50 dark:hover:border-primary-500',
      ]"
      style="aspect-ratio: 3/4"
      @dragover="onDragOver"
      @dragleave="onDragLeave"
      @drop="onDrop"
      @click="openPicker"
    >
      <img
        v-if="preview"
        :src="preview"
        alt="Photo d'identité"
        class="h-full w-full object-cover"
      />
      <div
        v-else
        class="flex h-full flex-col items-center justify-center gap-2 p-3 text-center"
      >
        <span class="text-3xl opacity-60">🪪</span>
        <span class="text-xs font-medium text-slate-500 dark:text-slate-400">3 × 4</span>
      </div>
      <div
        class="absolute inset-0 flex items-center justify-center bg-slate-900/50 opacity-0 transition group-hover:opacity-100"
      >
        <span class="rounded-lg bg-white/90 px-3 py-1.5 text-xs font-semibold text-slate-800">
          📷 Choisir
        </span>
      </div>
    </div>

    <div v-if="!compact" class="mt-3 text-center sm:text-left">
      <p class="text-sm font-semibold text-slate-700 dark:text-slate-200">{{ label }}</p>
      <p class="mt-0.5 text-xs text-slate-500 dark:text-slate-400">{{ hint }}</p>
      <button
        type="button"
        class="mt-2 text-xs font-medium text-primary-600 hover:underline dark:text-primary-400"
        @click.stop="openPicker"
      >
        Parcourir ou glisser-déposer
      </button>
    </div>

    <input
      ref="inputRef"
      type="file"
      accept="image/jpeg,image/png,image/webp"
      class="hidden"
      @change="onFileChange"
    />
  </div>
</template>
