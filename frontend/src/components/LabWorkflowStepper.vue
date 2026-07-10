<script setup>
import { computed } from 'vue'

const props = defineProps({
  statut: { type: String, required: true },
  compact: { type: Boolean, default: false },
})

const steps = [
  { key: 'COMMANDE', label: 'Commande', icon: '📋' },
  { key: 'PRELEVEMENT', label: 'Prélèvement', icon: '🩸' },
  { key: 'AFFECTATION', label: 'Affectation', icon: '🧪' },
  { key: 'SAISIE', label: 'Saisie', icon: '⌨️' },
  { key: 'VALIDATION', label: 'Validation', icon: '✅' },
  { key: 'PUBLIE', label: 'Publié', icon: '📄' },
]

const order = ['COMMANDE', 'PRELEVEMENT', 'AFFECTATION', 'SAISIE', 'VALIDATION', 'PUBLIE']

const currentIdx = computed(() => {
  const i = order.indexOf(props.statut)
  return i >= 0 ? i : 0
})

function stepState(idx) {
  if (props.statut === 'PUBLIE') return 'done'
  if (idx < currentIdx.value) return 'done'
  if (idx === currentIdx.value) return 'active'
  return 'pending'
}
</script>

<template>
  <div :class="compact ? 'gap-1' : 'gap-2'" class="flex flex-wrap items-center">
    <template v-for="(step, idx) in steps" :key="step.key">
      <div
        class="flex items-center gap-1.5 rounded-xl transition"
        :class="{
          'bg-violet-600 px-2.5 py-1 text-white shadow-md shadow-violet-500/30': stepState(idx) === 'active' && !compact,
          'bg-violet-100 dark:bg-violet-900/40 px-2.5 py-1 text-violet-800': stepState(idx) === 'active' && compact,
          'bg-emerald-50 dark:bg-emerald-950/40 px-2 py-0.5 text-emerald-700 dark:text-emerald-300': stepState(idx) === 'done',
          'bg-slate-100 dark:bg-slate-800 px-2 py-0.5 text-slate-400 dark:text-slate-500': stepState(idx) === 'pending',
        }"
      >
        <span :class="compact ? 'text-xs' : 'text-sm'">{{ step.icon }}</span>
        <span
          v-if="!compact || stepState(idx) === 'active'"
          class="font-medium"
          :class="compact ? 'text-[10px]' : 'text-xs'"
        >
          {{ step.label }}
        </span>
      </div>
      <div
        v-if="idx < steps.length - 1"
        class="h-0.5 w-3 rounded-full sm:w-5"
        :class="stepState(idx) === 'done' ? 'bg-emerald-300' : 'bg-slate-200 dark:bg-slate-700'"
      />
    </template>
  </div>
</template>
