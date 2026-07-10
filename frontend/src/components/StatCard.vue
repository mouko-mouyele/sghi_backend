<script setup>
defineProps({
  title: String,
  value: [String, Number],
  subtitle: String,
  icon: String,
  color: { type: String, default: 'primary' },
  trend: String,
})
</script>

<template>
  <div class="card group relative overflow-hidden transition hover:-translate-y-0.5 hover:shadow-lg dark:hover:shadow-card-dark">
    <div
      class="absolute -right-4 -top-4 h-24 w-24 rounded-full opacity-10"
      :class="{
        'bg-primary-50 dark:bg-primary-950/400': color === 'primary',
        'bg-accent-500': color === 'accent',
        'bg-amber-50 dark:bg-amber-950/400': color === 'warning',
        'bg-violet-50 dark:bg-violet-950/400': color === 'purple',
      }"
    />
    <div class="flex items-start justify-between">
      <div>
        <p class="text-sm font-medium text-slate-500 dark:text-slate-400">{{ title }}</p>
        <p class="mt-1 font-display text-3xl font-bold text-slate-900 dark:text-white">{{ value }}</p>
        <p v-if="subtitle" class="mt-1 text-xs text-slate-400 dark:text-slate-500">{{ subtitle }}</p>
        <p v-if="trend" class="mt-2 text-xs font-medium text-accent-600">{{ trend }}</p>
      </div>
      <div
        class="flex h-12 w-12 items-center justify-center rounded-2xl text-2xl"
        :class="{
          'bg-primary-100 dark:bg-primary-900/40': color === 'primary',
          'bg-emerald-100 dark:bg-emerald-900/40': color === 'accent',
          'bg-amber-100': color === 'warning',
          'bg-violet-100 dark:bg-violet-900/40': color === 'purple',
        }"
      >
        {{ icon }}
      </div>
    </div>
  </div>
</template>
