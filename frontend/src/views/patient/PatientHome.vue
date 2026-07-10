<script setup>

import { ref, onMounted } from 'vue'

import PatientLayout from '../../components/PatientLayout.vue'

import { patientApi } from '../../api/patient.js'
import { HOSPITAL_EMERGENCY_PHONE } from '../../utils/hospital.js'



const dash = ref({

  rdv_a_venir: 0,

  resultats_disponibles: 0,

  rappels_actifs: 0,

  factures_impayees: 0,

  montant_du: 0,

  hospitalisation_active: false,

  prochain_rdv: null,

})

const etab = ref(null)

const loading = ref(true)

const loadError = ref('')



onMounted(async () => {

  try {

    const [d, e] = await Promise.allSettled([

      patientApi.dashboard(),

      patientApi.establishment(),

    ])

    if (d.status === 'fulfilled') dash.value = { ...dash.value, ...d.value.data }

    else loadError.value = 'Certaines statistiques sont indisponibles.'

    if (e.status === 'fulfilled') etab.value = e.value.data

  } finally {

    loading.value = false

  }

})



function formatDate(iso) {

  if (!iso) return ''

  return new Date(iso).toLocaleString('fr-FR', { dateStyle: 'full', timeStyle: 'short' })

}

</script>



<template>

  <PatientLayout>

    <header class="mb-8">

      <h1 class="font-display text-3xl font-bold text-slate-900 dark:text-white">Tableau de bord patient</h1>

      <p class="mt-1 text-slate-600 dark:text-slate-400">Votre espace personnel — rendez-vous, soins, factures</p>

    </header>



    <div v-if="etab" class="mb-6 flex flex-wrap items-center justify-between gap-4 rounded-2xl bg-red-600 px-6 py-4 text-white shadow-lg">

      <div>

        <p class="text-sm font-medium text-red-100">Urgences 24h/24</p>

        <p class="text-xl font-bold">{{ etab.urgences_telephone || HOSPITAL_EMERGENCY_PHONE }}</p>

      </div>

      <router-link

        to="/patient/etablissement"

        class="rounded-xl bg-white/20 px-4 py-2 text-sm font-medium backdrop-blur hover:bg-white/30"

      >

        📍 Itinéraire vers le CHU

      </router-link>

    </div>



    <div v-if="loading" class="flex h-48 items-center justify-center text-slate-400">Chargement des statistiques…</div>



    <template v-else>

      <div v-if="loadError" class="mb-4 rounded-xl bg-amber-50 px-4 py-3 text-sm text-amber-800 dark:bg-amber-950/40">{{ loadError }}</div>



      <div class="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">

        <div class="rounded-2xl bg-white p-5 shadow-sm dark:bg-slate-800">

          <p class="text-sm text-slate-500 dark:text-slate-400">RDV à venir</p>

          <p class="mt-1 text-3xl font-bold text-teal-700">{{ dash.rdv_a_venir }}</p>

        </div>

        <div class="rounded-2xl bg-white p-5 shadow-sm dark:bg-slate-800">

          <p class="text-sm text-slate-500 dark:text-slate-400">Résultats labo</p>

          <p class="mt-1 text-3xl font-bold text-blue-700">{{ dash.resultats_disponibles }}</p>

        </div>

        <div class="rounded-2xl bg-white p-5 shadow-sm dark:bg-slate-800">

          <p class="text-sm text-slate-500 dark:text-slate-400">Rappels médicaments</p>

          <p class="mt-1 text-3xl font-bold text-violet-700">{{ dash.rappels_actifs }}</p>

        </div>

        <div class="rounded-2xl bg-white p-5 shadow-sm dark:bg-slate-800">

          <p class="text-sm text-slate-500 dark:text-slate-400">Factures impayées</p>

          <p class="mt-1 text-3xl font-bold" :class="dash.factures_impayees ? 'text-red-600' : 'text-emerald-600'">

            {{ dash.factures_impayees }}

          </p>

          <p v-if="dash.montant_du > 0" class="mt-1 text-xs text-red-500">{{ Number(dash.montant_du).toLocaleString('fr-FR') }} FCFA dus</p>

        </div>

        <div class="rounded-2xl bg-white p-5 shadow-sm dark:bg-slate-800">

          <p class="text-sm text-slate-500 dark:text-slate-400">Hospitalisation</p>

          <p class="mt-1 text-lg font-bold" :class="dash.hospitalisation_active ? 'text-amber-600' : 'text-emerald-600'">

            {{ dash.hospitalisation_active ? 'En cours' : 'Aucune' }}

          </p>

        </div>

      </div>



      <div v-if="dash.prochain_rdv" class="mb-8 rounded-2xl border-2 border-teal-200 bg-teal-50 p-6 dark:bg-teal-950/40">

        <p class="text-sm font-medium text-teal-700">Prochain rendez-vous</p>

        <p class="mt-2 text-xl font-bold text-teal-900 dark:text-teal-100">{{ dash.prochain_rdv.medecin }}</p>

        <p class="text-teal-700">{{ dash.prochain_rdv.specialty }}</p>

        <p class="mt-2 text-sm text-teal-800">{{ formatDate(dash.prochain_rdv.date_heure) }}</p>

        <p class="mt-1 text-sm text-slate-600 dark:text-slate-400">{{ dash.prochain_rdv.motif }}</p>

      </div>



      <div class="grid gap-6 lg:grid-cols-2">

        <div class="rounded-2xl bg-white p-6 shadow-sm dark:bg-slate-800">

          <h2 class="mb-4 font-semibold text-slate-900 dark:text-white">Accès rapide</h2>

          <div class="grid gap-2 sm:grid-cols-2">

            <router-link to="/patient/rendez-vous" class="rounded-xl bg-teal-50 px-4 py-3 text-sm font-medium text-teal-800 hover:bg-teal-100 dark:bg-teal-950/40">📅 Prendre RDV</router-link>

            <router-link to="/patient/laboratoire" class="rounded-xl bg-blue-50 px-4 py-3 text-sm font-medium text-blue-800 hover:bg-blue-100 dark:bg-blue-950/40">🔬 Mes résultats</router-link>

            <router-link to="/patient/messages" class="rounded-xl bg-violet-50 px-4 py-3 text-sm font-medium text-violet-800 hover:bg-violet-100 dark:bg-violet-900/40">💬 Contacter un médecin</router-link>

            <router-link to="/patient/factures" class="rounded-xl bg-emerald-50 px-4 py-3 text-sm font-medium text-emerald-800 hover:bg-emerald-100 dark:bg-emerald-950/40">💳 Payer mes factures</router-link>

            <router-link to="/patient/soins" class="rounded-xl bg-amber-50 px-4 py-3 text-sm font-medium text-amber-800 hover:bg-amber-100 dark:bg-amber-950/40">💊 Rappels médicaments</router-link>

            <router-link to="/patient/dossier" class="rounded-xl bg-slate-50 px-4 py-3 text-sm font-medium text-slate-800 hover:bg-slate-100 dark:bg-slate-700">📋 Mon dossier</router-link>

          </div>

        </div>



        <div v-if="etab" class="overflow-hidden rounded-2xl bg-white shadow-sm dark:bg-slate-800">

          <div class="border-b px-4 py-3 dark:border-slate-700">

            <h2 class="font-semibold">{{ etab.nom_etablissement }}</h2>

            <p class="text-sm text-slate-500 dark:text-slate-400">{{ etab.adresse }}</p>

          </div>

          <iframe

            :src="etab.google_maps_embed_url"

            class="h-56 w-full border-0"

            loading="lazy"

            referrerpolicy="no-referrer-when-downgrade"

            title="Carte Google Maps — CHU Brazzaville"

          />

          <div class="flex gap-2 p-3">

            <a

              :href="etab.google_maps_directions_url"

              target="_blank"

              rel="noopener"

              class="flex-1 rounded-xl bg-teal-600 py-2 text-center text-sm font-medium text-white hover:bg-teal-700"

            >

              Itinéraire Google Maps

            </a>

            <router-link to="/patient/etablissement" class="rounded-xl border px-4 py-2 text-sm dark:border-slate-600">Infos</router-link>

          </div>

        </div>

      </div>

    </template>

  </PatientLayout>

</template>


