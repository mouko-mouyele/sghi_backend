<script setup>
import { ref, onMounted } from 'vue'
import AdminLayout from '../../components/AdminLayout.vue'
import { adminApi } from '../../api/admin.js'

const data = ref(null)
const loading = ref(true)

onMounted(async () => {
  try {
    const { data: d } = await adminApi.urgences()
    data.value = d
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <AdminLayout>
    <header class="mb-8">
      <h1 class="font-display text-3xl font-bold text-slate-900 dark:text-white">Service des urgences</h1>
      <p class="mt-1 text-slate-600 dark:text-slate-400">Suivi en temps réel des admissions urgentes</p>
    </header>

    <div v-if="loading" class="text-center text-slate-400 dark:text-slate-500">Chargement...</div>

    <template v-else-if="data">
      <div class="mb-6 grid gap-4 sm:grid-cols-3">
        <div class="rounded-2xl border-2 border-red-200 bg-red-50 dark:bg-red-950/40 p-5 text-center">
          <p class="text-3xl font-bold text-red-700 dark:text-red-300">{{ data.hospitalisations?.length || 0 }}</p>
          <p class="text-sm text-red-600 dark:text-red-400">Patients aux urgences</p>
        </div>
        <div class="rounded-2xl bg-white dark:bg-slate-800 p-5 text-center shadow-sm dark:shadow-none">
          <p class="text-3xl font-bold text-emerald-600">{{ data.lits_disponibles }}</p>
          <p class="text-sm text-slate-500 dark:text-slate-400">Lits disponibles</p>
        </div>
        <div class="rounded-2xl bg-white dark:bg-slate-800 p-5 text-center shadow-sm dark:shadow-none">
          <p class="text-3xl font-bold text-slate-800 dark:text-slate-100">{{ data.lits_total }}</p>
          <p class="text-sm text-slate-500 dark:text-slate-400">Lits total urgences</p>
        </div>
      </div>

      <div class="overflow-hidden rounded-2xl bg-white dark:bg-slate-800 shadow-sm dark:shadow-none">
        <table class="w-full text-sm">
          <thead class="bg-red-50 dark:bg-red-950/40">
            <tr>
              <th class="px-4 py-3 text-left">Patient</th>
              <th class="px-4 py-3 text-left">N° Dossier</th>
              <th class="px-4 py-3 text-left">Lit</th>
              <th class="px-4 py-3 text-left">Médecin</th>
              <th class="px-4 py-3 text-left">Entrée</th>
              <th class="px-4 py-3 text-left">Motif</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="h in data.hospitalisations" :key="h.hospitalisation_id" class="border-t">
              <td class="px-4 py-3 font-medium">{{ h.patient_nom }}</td>
              <td class="px-4 py-3 font-mono text-xs">{{ h.numero_dossier }}</td>
              <td class="px-4 py-3">{{ h.lit }}</td>
              <td class="px-4 py-3">{{ h.medecin }}</td>
              <td class="px-4 py-3">{{ h.date_entree?.slice(0, 16).replace('T', ' ') }}</td>
              <td class="px-4 py-3 text-slate-500 dark:text-slate-400">{{ h.motif }}</td>
            </tr>
            <tr v-if="!data.hospitalisations?.length">
              <td colspan="6" class="px-4 py-8 text-center text-slate-400 dark:text-slate-500">Aucune hospitalisation active aux urgences</td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </AdminLayout>
</template>
