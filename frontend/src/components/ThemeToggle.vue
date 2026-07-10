<script setup>
import { computed } from 'vue'
import { useTheme, THEME_OPTIONS } from '../composables/useTheme.js'

defineProps({
  compact: { type: Boolean, default: false },
})

const { mode, isDark, setTheme, cycleTheme } = useTheme()

const current = computed(() => THEME_OPTIONS.find((o) => o.value === mode.value) || THEME_OPTIONS[1])

const ariaLabel = computed(() => {
  if (mode.value === 'system') {
    return `Thème système — affichage ${isDark ? 'sombre' : 'clair'} selon l'appareil`
  }
  return mode.value === 'dark' ? 'Thème sombre actif' : 'Thème clair actif'
})
</script>

<template>
  <!-- Version compacte : cycle Clair → Système → Sombre -->
  <button
    v-if="compact"
    type="button"
    :aria-label="ariaLabel"
    :title="`${current.label}${mode === 'system' ? ' (auto)' : ''} — clic pour changer`"
    class="flex h-10 w-10 items-center justify-center rounded-xl border border-slate-200 bg-white/90 text-lg shadow-sm transition hover:bg-slate-50 dark:border-slate-600 dark:bg-slate-800 dark:hover:bg-slate-700"
    @click="cycleTheme"
  >
    {{ current.icon }}
    <span class="sr-only">{{ current.label }}</span>
  </button>

  <!-- Version sidebar : sélecteur 3 boutons -->
  <div v-else class="rounded-xl border border-slate-200 bg-slate-50/80 p-1 dark:border-slate-600 dark:bg-slate-800/80">
    <p class="mb-1.5 px-2 text-[10px] font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500">
      Apparence
    </p>
    <div class="grid grid-cols-3 gap-1">
      <button
        v-for="opt in THEME_OPTIONS"
        :key="opt.value"
        type="button"
        :aria-pressed="mode === opt.value"
        :aria-label="`Thème ${opt.label}`"
        class="flex flex-col items-center gap-0.5 rounded-lg px-1 py-2 text-center transition"
        :class="mode === opt.value
          ? 'bg-white text-violet-700 shadow-sm ring-1 ring-violet-200 dark:bg-slate-700 dark:text-violet-200 dark:ring-violet-700/50'
          : 'text-slate-500 hover:bg-white/60 hover:text-slate-700 dark:text-slate-400 dark:hover:bg-slate-700/50 dark:hover:text-slate-200'"
        @click="setTheme(opt.value)"
      >
        <span class="text-base leading-none">{{ opt.icon }}</span>
        <span class="text-[10px] font-semibold leading-tight">{{ opt.short }}</span>
      </button>
    </div>
    <p v-if="mode === 'system'" class="mt-1.5 px-1 text-center text-[10px] text-slate-400 dark:text-slate-500">
      Suit l'appareil · actuellement {{ isDark ? 'sombre' : 'clair' }}
    </p>
  </div>
</template>
