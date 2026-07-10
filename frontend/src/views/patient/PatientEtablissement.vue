<script setup>
import { ref, onMounted } from 'vue'
import PatientLayout from '../../components/PatientLayout.vue'
import { patientApi } from '../../api/patient.js'
import { HOSPITAL_EMERGENCY_PHONE } from '../../utils/hospital.js'

const etab = ref(null)
const loading = ref(true)

onMounted(async () => {
  try {
    const { data } = await patientApi.establishment()
    etab.value = data
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <PatientLayout>
    <header class="mb-8">
      <h1 class="font-display text-3xl font-bold text-slate-900 dark:text-white">Localisation — CHU de Brazzaville</h1>
      <p class="mt-1 text-slate-600 dark:text-slate-400">Informations pratiques et carte Google Maps</p>
    </header>

    <div v-if="loading" class="text-slate-400 dark:text-slate-500">Chargement...</div>

    <template v-else-if="etab">
      <div class="mb-6 grid gap-6 lg:grid-cols-2">
        <div class="rounded-2xl bg-white dark:bg-slate-800 p-6 shadow-sm dark:shadow-none">
          <h2 class="text-xl font-bold text-teal-900 dark:text-teal-100">{{ etab.nom_etablissement }}</h2>
          <p class="mt-3 text-slate-600 dark:text-slate-400">{{ etab.adresse }}</p>
          <div class="mt-6 space-y-3 text-sm">
            <p>📞 <strong>Accueil :</strong> {{ etab.telephone }}</p>
            <p>🚨 <strong>Urgences :</strong> {{ etab.urgences_telephone || HOSPITAL_EMERGENCY_PHONE }}</p>
            <p>✉️ <strong>Email :</strong> {{ etab.email }}</p>
            <p v-if="etab.site_web">🌐 <a :href="etab.site_web" target="_blank" rel="noopener" class="text-teal-600 dark:text-teal-400 underline">{{ etab.site_web }}</a></p>
          </div>
          <pre class="mt-4 whitespace-pre-wrap rounded-xl bg-slate-50 dark:bg-slate-800/60 p-4 text-sm text-slate-700 dark:text-slate-300">{{ etab.horaires }}</pre>
          <p class="mt-4 text-sm text-slate-500 dark:text-slate-400">{{ etab.description }}</p>
          <div class="mt-6 flex flex-wrap gap-3">
            <a
              :href="etab.google_maps_directions_url"
              target="_blank"
              rel="noopener"
              class="rounded-xl bg-teal-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-teal-700"
            >
              🗺️ Itinéraire Google Maps
            </a>
            <a
              :href="`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(etab.google_maps_query)}`"
              target="_blank"
              rel="noopener"
              class="rounded-xl border border-teal-200 px-5 py-2.5 text-sm font-medium text-teal-700 hover:bg-teal-50 dark:bg-teal-950/40"
            >
              Ouvrir dans Google Maps
            </a>
          </div>
        </div>

        <div class="overflow-hidden rounded-2xl bg-white dark:bg-slate-800 shadow-lg">
          <iframe
            :src="etab.google_maps_embed_url"
            class="h-[420px] w-full border-0"
            loading="lazy"
            allowfullscreen
            referrerpolicy="no-referrer-when-downgrade"
            title="Google Maps — CHU Brazzaville"
          />
          <p class="border-t px-4 py-2 text-center text-xs text-slate-400 dark:text-slate-500">
            Coordonnées GPS : {{ etab.latitude }}, {{ etab.longitude }}
          </p>
        </div>
      </div>

      <div class="rounded-2xl bg-teal-50 dark:bg-teal-950/40 p-6">
        <h3 class="font-semibold text-teal-900 dark:text-teal-100">Comment venir au CHU de Brazzaville ?</h3>
        <ul class="mt-3 list-inside list-disc space-y-1 text-sm text-teal-800">
          <li>Depuis le centre-ville : direction Avenue Amilcar Cabral (Talangaï)</li>
          <li>Transport : taxi ou bus lignes passant par le quartier Talangaï</li>
          <li>Parking visiteurs disponible à l'entrée principale</li>
          <li>Accueil urgences : entrée séparée, ouvert 24h/24</li>
        </ul>
      </div>
    </template>
  </PatientLayout>
</template>
