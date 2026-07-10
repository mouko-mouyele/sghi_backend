<script setup>
import { computed } from 'vue'

const props = defineProps({
  page: { type: Number, required: true },
  pageSize: { type: Number, required: true },
  total: { type: Number, required: true },
  totalPages: { type: Number, required: true },
  showSizeSelector: { type: Boolean, default: true },
  sizeOptions: { type: Array, default: () => [10, 15, 20, 30] },
})

const emit = defineEmits(['update:page', 'update:pageSize'])

const from = computed(() => (props.total ? (props.page - 1) * props.pageSize + 1 : 0))
const to = computed(() => Math.min(props.page * props.pageSize, props.total))

const pages = computed(() => {
  const max = props.totalPages
  const current = props.page
  if (max <= 7) return Array.from({ length: max }, (_, i) => i + 1)
  const set = new Set([1, max, current, current - 1, current + 1])
  return [...set].filter((p) => p >= 1 && p <= max).sort((a, b) => a - b)
})

function go(p) {
  if (p >= 1 && p <= props.totalPages && p !== props.page) emit('update:page', p)
}

function onSizeChange(e) {
  emit('update:pageSize', Number(e.target.value))
  emit('update:page', 1)
}
</script>

<template>
  <div
    v-if="total > 0"
    class="flex flex-wrap items-center justify-between gap-4 border-t border-slate-100 px-4 py-3 dark:border-slate-700"
  >
    <p class="text-sm text-slate-500 dark:text-slate-400">
      <span class="font-medium text-slate-700 dark:text-slate-200">{{ from }}–{{ to }}</span>
      sur {{ total }} résultat{{ total > 1 ? 's' : '' }}
    </p>

    <div class="flex flex-wrap items-center gap-2">
      <select
        v-if="showSizeSelector"
        :value="pageSize"
        class="rounded-lg border border-slate-200 bg-white px-2 py-1.5 text-xs dark:border-slate-600 dark:bg-slate-800"
        @change="onSizeChange"
      >
        <option v-for="n in sizeOptions" :key="n" :value="n">{{ n }} / page</option>
      </select>

      <button
        type="button"
        class="rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-medium transition hover:bg-slate-50 disabled:opacity-40 dark:border-slate-600 dark:hover:bg-slate-800"
        :disabled="page <= 1"
        @click="go(page - 1)"
      >
        ← Préc.
      </button>

      <template v-for="(p, idx) in pages" :key="p">
        <span v-if="idx > 0 && p - pages[idx - 1] > 1" class="px-1 text-slate-400">…</span>
        <button
          type="button"
          class="min-w-[2rem] rounded-lg px-2 py-1.5 text-xs font-semibold transition"
          :class="p === page
            ? 'bg-primary-600 text-white shadow-sm'
            : 'border border-slate-200 hover:bg-slate-50 dark:border-slate-600 dark:hover:bg-slate-800'"
          @click="go(p)"
        >
          {{ p }}
        </button>
      </template>

      <button
        type="button"
        class="rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-medium transition hover:bg-slate-50 disabled:opacity-40 dark:border-slate-600 dark:hover:bg-slate-800"
        :disabled="page >= totalPages"
        @click="go(page + 1)"
      >
        Suiv. →
      </button>
    </div>
  </div>
</template>
