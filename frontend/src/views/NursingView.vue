<script setup>
import { ref, onMounted, computed } from 'vue'
import AppLayout from '../components/AppLayout.vue'
import StatCard from '../components/StatCard.vue'
import { dashboard, hospitalization, nursing } from '../api/client'
import { parseApiError } from '../utils/errors.js'

const roleStats = ref(null)
const cares = ref([])
const activeHosp = ref([])
const loading = ref(true)
const filterStatut = ref('')
const message = ref('')
const errorMsg = ref('')
const showVitals = ref(false)
const showCare = ref(false)

const vitalsForm = ref({
  hospitalisation_id: '',
  temperature: '',
  tension_systolique: '',
  tension_diastolique: '',
  frequence_cardiaque: '',
  saturation_o2: '',
  notes: '',
})

const careForm = ref({
  hospitalisation_id: '',
  description: '',
  planifie_a: '',
})

const statutClass = {
  PLANIFIE: 'bg-blue-100 text-blue-800 dark:bg-blue-950/40',
  EN_RETARD: 'bg-amber-100 text-amber-800 dark:bg-amber-950/40',
  OMIS: 'bg-red-100 text-red-800 dark:bg-red-950/40',
  REALISE: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/40',
}

function fmt(d) {
  if (!d) return '—'
  return new Date(d).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' })
}

function toLocalInput(date = new Date()) {
  const dt = new Date(date)
  const pad = (n) => String(n).padStart(2, '0')
  return `${dt.getFullYear()}-${pad(dt.getMonth() + 1)}-${pad(dt.getDate())}T${pad(dt.getHours())}:${pad(dt.getMinutes())}`
}

async function load() {
  loading.value = true
  errorMsg.value = ''
  try {
    const [statsRes, careRes, hospRes] = await Promise.all([
      dashboard.moi(),
      nursing.planning({ statut: filterStatut.value || undefined }),
      hospitalization.active(),
    ])
    roleStats.value = statsRes.data
    cares.value = careRes.data
    activeHosp.value = hospRes.data
  } catch (e) {
    errorMsg.value = parseApiError(e)
  } finally {
    loading.value = false
  }
}

function openVitals() {
  vitalsForm.value = {
    hospitalisation_id: activeHosp.value[0]?.id || '',
    temperature: '',
    tension_systolique: '',
    tension_diastolique: '',
    frequence_cardiaque: '',
    saturation_o2: '',
    notes: '',
  }
  showVitals.value = true
}

function openCare() {
  careForm.value = {
    hospitalisation_id: activeHosp.value[0]?.id || '',
    description: '',
    planifie_a: toLocalInput(),
  }
  showCare.value = true
}

async function submitVitals() {
  try {
    await nursing.recordVitals({
      hospitalisation_id: Number(vitalsForm.value.hospitalisation_id),
      temperature: vitalsForm.value.temperature ? Number(vitalsForm.value.temperature) : null,
      tension_systolique: vitalsForm.value.tension_systolique ? Number(vitalsForm.value.tension_systolique) : null,
      tension_diastolique: vitalsForm.value.tension_diastolique ? Number(vitalsForm.value.tension_diastolique) : null,
      frequence_cardiaque: vitalsForm.value.frequence_cardiaque ? Number(vitalsForm.value.frequence_cardiaque) : null,
      saturation_o2: vitalsForm.value.saturation_o2 ? Number(vitalsForm.value.saturation_o2) : null,
      notes: vitalsForm.value.notes,
    })
    showVitals.value = false
    message.value = 'Constantes enregistrées'
    load()
  } catch (e) {
    errorMsg.value = parseApiError(e)
  }
}

async function submitCare() {
  try {
    await nursing.createCare({
      hospitalisation_id: Number(careForm.value.hospitalisation_id),
      description: careForm.value.description,
      planifie_a: new Date(careForm.value.planifie_a).toISOString(),
    })
    showCare.value = false
    message.value = 'Soin planifié'
    load()
  } catch (e) {
    errorMsg.value = parseApiError(e)
  }
}

async function completeCare(id) {
  try {
    await nursing.completeCare(id)
    message.value = 'Soin marqué comme réalisé'
    load()
  } catch (e) {
    errorMsg.value = parseApiError(e)
  }
}

onMounted(load)
</script>

<template>
  <AppLayout>
    <header class="mb-8 flex flex-wrap items-start justify-between gap-4">
      <div>
        <h1 class="font-display text-3xl font-bold text-slate-900 dark:text-white">Soins infirmiers</h1>
        <p class="mt-1 text-slate-500 dark:text-slate-400">Plan de soins, constantes vitales et alertes doses omises</p>
      </div>
      <div class="flex flex-wrap gap-2">
        <button type="button" class="btn-primary" @click="openVitals">+ Constantes</button>
        <button type="button" class="rounded-xl border border-primary-300 px-4 py-2 text-sm text-primary-700 dark:text-primary-300" @click="openCare">+ Planifier un soin</button>
      </div>
    </header>

    <div v-if="message" class="mb-4 rounded-xl bg-emerald-50 px-4 py-3 text-sm text-emerald-700 dark:bg-emerald-950/40">{{ message }}</div>
    <div v-if="errorMsg" class="mb-4 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-600 dark:bg-red-950/40">{{ errorMsg }}</div>

    <div v-if="loading" class="flex h-48 items-center justify-center">
      <div class="h-10 w-10 animate-spin rounded-full border-4 border-primary-200 border-t-primary-600" />
    </div>

    <template v-else>
      <div v-if="roleStats" class="mb-8 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard title="Hospitalisations actives" :value="roleStats.hospitalisations_actives" icon="🏥" color="primary" />
        <StatCard title="Soins en attente" :value="roleStats.soins_en_attente" icon="📋" color="primary" />
        <StatCard title="Soins en retard" :value="roleStats.soins_en_retard" icon="⏰" color="warning" />
        <StatCard title="Doses omises" :value="roleStats.doses_omises" icon="⚠️" color="warning" />
      </div>

      <div class="mb-4 flex flex-wrap gap-2">
        <button
          v-for="f in [{ v: '', l: 'Tous' }, { v: 'PLANIFIE', l: 'Planifiés' }, { v: 'EN_RETARD', l: 'En retard' }, { v: 'OMIS', l: 'Omis' }, { v: 'REALISE', l: 'Réalisés' }]"
          :key="f.v"
          type="button"
          class="rounded-full px-3 py-1 text-sm"
          :class="filterStatut === f.v ? 'bg-primary-600 text-white' : 'bg-slate-100 text-slate-600 dark:bg-slate-800'"
          @click="filterStatut = f.v; load()"
        >
          {{ f.l }}
        </button>
      </div>

      <div class="overflow-hidden rounded-2xl bg-white shadow-sm dark:bg-slate-800">
        <table class="w-full text-sm">
          <thead class="bg-slate-50 dark:bg-slate-800/60">
            <tr>
              <th class="px-4 py-3 text-left">Patient</th>
              <th class="px-4 py-3 text-left">Service</th>
              <th class="px-4 py-3 text-left">Soin</th>
              <th class="px-4 py-3 text-left">Planifié</th>
              <th class="px-4 py-3 text-left">Statut</th>
              <th class="px-4 py-3 text-right">Action</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!cares.length">
              <td colspan="6" class="px-4 py-8 text-center text-slate-500">Aucun soin pour ce filtre.</td>
            </tr>
            <tr v-for="c in cares" :key="c.id" class="border-t border-slate-100 dark:border-slate-700">
              <td class="px-4 py-3">
                <p class="font-medium">{{ c.patient_nom }}</p>
                <p class="text-xs text-slate-500">{{ c.patient_dossier }}</p>
              </td>
              <td class="px-4 py-3">{{ c.service || '—' }}</td>
              <td class="px-4 py-3">{{ c.description }}</td>
              <td class="px-4 py-3 text-slate-500">{{ fmt(c.planifie_a) }}</td>
              <td class="px-4 py-3">
                <span class="rounded-full px-2 py-0.5 text-xs font-medium" :class="statutClass[c.statut]">{{ c.statut }}</span>
              </td>
              <td class="px-4 py-3 text-right">
                <button
                  v-if="!c.realise_a && c.statut !== 'REALISE'"
                  type="button"
                  class="text-sm font-medium text-primary-600 hover:underline"
                  @click="completeCare(c.id)"
                >
                  Marquer réalisé
                </button>
                <span v-else class="text-xs text-emerald-600">{{ fmt(c.realise_a) }}</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>

    <div v-if="showVitals" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" @click.self="showVitals = false">
      <form class="w-full max-w-lg rounded-2xl bg-white p-6 dark:bg-slate-800" @submit.prevent="submitVitals">
        <h2 class="text-lg font-bold">Prise des constantes</h2>
        <div class="mt-4 space-y-3">
          <select v-model="vitalsForm.hospitalisation_id" class="input-field" required>
            <option v-for="h in activeHosp" :key="h.id" :value="h.id">{{ h.patient_nom }} — {{ h.service_nom }}</option>
          </select>
          <div class="grid grid-cols-2 gap-3">
            <input v-model="vitalsForm.temperature" type="number" step="0.1" class="input-field" placeholder="Temp. °C" />
            <input v-model="vitalsForm.frequence_cardiaque" type="number" class="input-field" placeholder="FC /min" />
            <input v-model="vitalsForm.tension_systolique" type="number" class="input-field" placeholder="TA sys" />
            <input v-model="vitalsForm.tension_diastolique" type="number" class="input-field" placeholder="TA dia" />
            <input v-model="vitalsForm.saturation_o2" type="number" class="input-field" placeholder="SpO2 %" />
          </div>
          <textarea v-model="vitalsForm.notes" class="input-field" rows="2" placeholder="Notes" />
        </div>
        <div class="mt-6 flex justify-end gap-2">
          <button type="button" class="rounded-xl border px-4 py-2 text-sm" @click="showVitals = false">Annuler</button>
          <button type="submit" class="btn-primary">Enregistrer</button>
        </div>
      </form>
    </div>

    <div v-if="showCare" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" @click.self="showCare = false">
      <form class="w-full max-w-lg rounded-2xl bg-white p-6 dark:bg-slate-800" @submit.prevent="submitCare">
        <h2 class="text-lg font-bold">Planifier un soin</h2>
        <div class="mt-4 space-y-3">
          <select v-model="careForm.hospitalisation_id" class="input-field" required>
            <option v-for="h in activeHosp" :key="h.id" :value="h.id">{{ h.patient_nom }} — {{ h.service_nom }}</option>
          </select>
          <textarea v-model="careForm.description" class="input-field" rows="3" placeholder="Description du soin" required />
          <input v-model="careForm.planifie_a" type="datetime-local" class="input-field" required />
        </div>
        <div class="mt-6 flex justify-end gap-2">
          <button type="button" class="rounded-xl border px-4 py-2 text-sm" @click="showCare = false">Annuler</button>
          <button type="submit" class="btn-primary">Planifier</button>
        </div>
      </form>
    </div>
  </AppLayout>
</template>
