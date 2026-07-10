<script setup>
import { ref, onMounted } from 'vue'
import PatientLayout from '../../components/PatientLayout.vue'
import { patientApi } from '../../api/patient.js'

const results = ref([])
const loading = ref(true)

onMounted(async () => {
  try {
    const { data } = await patientApi.labResults()
    results.value = data
  } finally {
    loading.value = false
  }
})

function fmt(d) {
  if (!d) return '—'
  return new Date(d).toLocaleDateString('fr-FR')
}
</script>

<template>
  <PatientLayout>
    <header class="mb-8">
      <h1 class="font-display text-3xl font-bold text-slate-900 dark:text-white">Résultats de laboratoire</h1>
      <p class="mt-1 text-slate-600 dark:text-slate-400">Résultats validés par le biologiste — téléchargement PDF signé</p>
    </header>

    <div v-if="loading" class="text-slate-400 dark:text-slate-500">Chargement...</div>
    <div v-else class="space-y-4">
      <div v-for="r in results" :key="r.id" class="flex flex-wrap items-center justify-between gap-4 rounded-2xl bg-white dark:bg-slate-800 p-5 shadow-sm dark:shadow-none">
        <div>
          <p class="font-semibold">{{ r.examen }}</p>
          <p class="mt-1 text-lg text-blue-800">{{ r.valeur }} <span class="text-sm text-slate-500 dark:text-slate-400">{{ r.unite }}</span></p>
          <p class="text-xs text-slate-500 dark:text-slate-400">Validé le {{ fmt(r.date_validation) }}</p>
        </div>
        <a
          v-if="r.pdf_url"
          :href="r.pdf_url"
          target="_blank"
          rel="noopener"
          class="flex items-center gap-2 rounded-xl bg-red-50 dark:bg-red-950/40 px-4 py-2 text-sm font-medium text-red-700 dark:text-red-300 hover:bg-red-100"
        >
          📄 Télécharger PDF
        </a>
        <span v-else class="text-xs text-slate-400 dark:text-slate-500">PDF en cours</span>
      </div>
      <p v-if="!results.length" class="rounded-2xl bg-blue-50 dark:bg-blue-950/40 py-12 text-center text-blue-700">
        Aucun résultat publié pour le moment
      </p>
    </div>
  </PatientLayout>
</template>
