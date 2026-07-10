<script setup>
import { ref, onMounted, watch } from 'vue'
import PatientLayout from '../../components/PatientLayout.vue'
import { patientApi } from '../../api/patient.js'

const list = ref([])
const medecins = ref([])
const occupiedSlots = ref([])
const loading = ref(true)
const showForm = ref(false)
const message = ref('')
const errorMsg = ref('')
const form = ref({ medecin_id: '', date_heure: '', motif: '', duree_minutes: 30 })

const minDatetime = new Date(Date.now() - new Date().getTimezoneOffset() * 60000)
  .toISOString()
  .slice(0, 16)

function parseApiError(e, fallback) {
  const detail = e.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) return detail.map((d) => d.msg || JSON.stringify(d)).join(' · ')
  if (e.message?.includes('Invalid time value')) return 'Date ou heure invalide'
  return fallback
}

/** Envoie l'heure locale telle que saisie (fuseau hôpital), sans conversion UTC. */
function toLocalDatetimePayload(value) {
  if (!value || !value.includes('T')) return null
  return value.length === 16 ? `${value}:00` : value
}

async function loadOccupied() {
  occupiedSlots.value = []
  if (!form.value.medecin_id || !form.value.date_heure) return
  const day = form.value.date_heure.slice(0, 10)
  try {
    const { data } = await patientApi.busySlots(form.value.medecin_id, day)
    occupiedSlots.value = data
  } catch { /* ignore */ }
}

async function load() {
  loading.value = true
  try {
    const [rdv, med] = await Promise.all([patientApi.appointments(), patientApi.medecins()])
    list.value = rdv.data
    medecins.value = med.data
  } finally {
    loading.value = false
  }
}

async function book() {
  errorMsg.value = ''
  message.value = ''
  if (!form.value.medecin_id) {
    errorMsg.value = 'Veuillez choisir un médecin'
    return
  }
  const dateHeure = toLocalDatetimePayload(form.value.date_heure)
  if (!dateHeure) {
    errorMsg.value = 'Veuillez choisir une date et une heure'
    return
  }
  try {
    await patientApi.bookAppointment({
      medecin_id: Number(form.value.medecin_id),
      date_heure: dateHeure,
      motif: form.value.motif,
      duree_minutes: form.value.duree_minutes,
    })
    message.value = 'Demande envoyée — en attente de confirmation par l\'accueil (email envoyé)'
    showForm.value = false
    form.value = { medecin_id: '', date_heure: '', motif: '', duree_minutes: 30 }
    occupiedSlots.value = []
    load()
  } catch (e) {
    errorMsg.value = parseApiError(e, 'Impossible de réserver ce créneau')
    loadOccupied()
  }
}

async function cancel(r) {
  if (!confirm(`Annuler le RDV du ${new Date(r.date_heure).toLocaleString('fr-FR')} ?`)) return
  try {
    await patientApi.cancelAppointment(r.id)
    message.value = 'Rendez-vous annulé'
    load()
  } catch (e) {
    errorMsg.value = parseApiError(e, 'Erreur lors de l\'annulation')
  }
}

function fmt(d) {
  return new Date(d).toLocaleString('fr-FR', { dateStyle: 'medium', timeStyle: 'short' })
}

function fmtSlot(iso) {
  const d = new Date(iso)
  return d.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })
}

function statutLabel(s) {
  return { PLANIFIE: 'En attente', CONFIRME: 'Confirmé', ANNULE: 'Annulé', TERMINE: 'Terminé' }[s] || s
}

function statutClass(s) {
  return {
    CONFIRME: 'bg-emerald-100 dark:bg-emerald-900/40 text-emerald-800 dark:text-emerald-200',
    PLANIFIE: 'bg-amber-100 text-amber-800 dark:text-amber-200',
    ANNULE: 'bg-red-100 text-red-700 dark:text-red-300',
    TERMINE: 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400',
  }[s] || 'bg-slate-100 dark:bg-slate-800'
}

watch(() => [form.value.medecin_id, form.value.date_heure], loadOccupied)

onMounted(load)
</script>

<template>
  <PatientLayout>
    <header class="mb-6 flex flex-wrap items-center justify-between gap-4">
      <div>
        <h1 class="font-display text-3xl font-bold text-slate-900 dark:text-white">Mes rendez-vous</h1>
        <p class="mt-1 text-slate-600 dark:text-slate-400">Prise de RDV synchronisée aux disponibilités des médecins</p>
      </div>
      <button class="btn-primary bg-teal-600 hover:bg-teal-700" @click="showForm = !showForm">+ Prendre RDV</button>
    </header>

    <div v-if="showForm" class="mb-6 rounded-2xl bg-white dark:bg-slate-800 p-6 shadow-sm dark:shadow-none">
      <h2 class="mb-4 font-semibold">Nouveau rendez-vous</h2>
      <div class="grid gap-3 sm:grid-cols-2">
        <select v-model="form.medecin_id" class="input-field" required>
          <option value="">Choisir un médecin</option>
          <option v-for="m in medecins" :key="m.id" :value="m.id">
            Dr {{ m.first_name }} {{ m.last_name }} — {{ m.specialty || 'Généraliste' }}
          </option>
        </select>
        <input
          v-model="form.date_heure"
          type="datetime-local"
          class="input-field"
          :min="minDatetime"
          required
          @change="loadOccupied"
        />
        <input v-model="form.motif" class="input-field sm:col-span-2" placeholder="Motif de consultation" required />
      </div>

      <div v-if="occupiedSlots.length" class="mt-4 rounded-xl bg-amber-50 dark:bg-amber-950/40 px-4 py-3 text-sm text-amber-900">
        <p class="font-medium">Créneaux déjà réservés ce jour :</p>
        <ul class="mt-1 list-inside list-disc">
          <li v-for="(s, i) in occupiedSlots" :key="i">
            {{ fmtSlot(s.debut) }} – {{ fmtSlot(s.fin) }} ({{ s.duree_minutes }} min)
          </li>
        </ul>
        <p class="mt-2 text-xs text-amber-700">Évitez ces plages ou choisissez un autre jour.</p>
      </div>

      <button class="mt-4 rounded-xl bg-teal-600 px-5 py-2 text-sm font-medium text-white" @click="book">Confirmer</button>
    </div>

    <p v-if="message" class="mb-4 text-sm text-emerald-600">{{ message }}</p>
    <p v-if="errorMsg" class="mb-4 rounded-lg bg-red-50 dark:bg-red-950/40 px-4 py-2 text-sm text-red-700 dark:text-red-300">{{ errorMsg }}</p>

    <div class="space-y-3">
      <div v-for="r in list" :key="r.id" class="flex flex-wrap items-center justify-between gap-4 rounded-2xl bg-white dark:bg-slate-800 p-5 shadow-sm dark:shadow-none">
        <div>
          <p class="font-semibold">{{ r.medecin_nom }}</p>
          <p class="text-sm text-teal-600 dark:text-teal-400">{{ r.medecin_specialty }}</p>
          <p class="mt-1 text-sm text-slate-600 dark:text-slate-400">{{ fmt(r.date_heure) }} · {{ r.motif }}</p>
        </div>
        <div class="flex items-center gap-2">
          <span class="rounded-full px-3 py-1 text-xs font-medium" :class="statutClass(r.statut)">{{ statutLabel(r.statut) }}</span>
          <button
            v-if="['PLANIFIE', 'CONFIRME'].includes(r.statut)"
            class="rounded-lg bg-red-50 dark:bg-red-950/40 px-3 py-1 text-xs text-red-700 dark:text-red-300 hover:bg-red-100"
            @click="cancel(r)"
          >
            Annuler
          </button>
        </div>
      </div>
      <p v-if="!loading && !list.length" class="py-12 text-center text-slate-400 dark:text-slate-500">Aucun rendez-vous</p>
    </div>
  </PatientLayout>
</template>
