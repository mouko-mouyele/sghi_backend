<script setup>
import { ref, computed, onMounted } from 'vue'
import PatientLayout from '../../components/PatientLayout.vue'
import { patientApi } from '../../api/patient.js'

const plan = ref(null)
const loading = ref(true)
const tab = ref('soins')
const showForm = ref(false)
const message = ref('')
const messageType = ref('success')
const form = ref({ medicament: '', heure_prise: '08:00', prescription_id: null })

const hosp = computed(() => plan.value?.hospitalisation)
const soins = computed(() => plan.value?.soins || [])
const constantes = computed(() => plan.value?.constantes || [])
const ordonnances = computed(() => plan.value?.ordonnances || [])
const rappels = computed(() => plan.value?.rappels || [])

const statutClass = {
  REALISE: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-200',
  PLANIFIE: 'bg-blue-100 text-blue-800 dark:bg-blue-950/40',
  EN_RETARD: 'bg-amber-100 text-amber-800 dark:bg-amber-950/40',
  OMIS: 'bg-red-100 text-red-800 dark:bg-red-950/40',
}

function fmt(d) {
  if (!d) return '—'
  return new Date(d).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' })
}

function fmtDate(d) {
  if (!d) return '—'
  return new Date(d).toLocaleDateString('fr-FR')
}

function fmtTime(t) {
  if (!t) return '—'
  return String(t).slice(0, 5)
}

function toast(text, type = 'success') {
  message.value = text
  messageType.value = type
  setTimeout(() => { message.value = '' }, 4000)
}

async function load() {
  loading.value = true
  try {
    const { data } = await patientApi.carePlan()
    plan.value = data
  } finally {
    loading.value = false
  }
}

async function addReminder() {
  if (!form.value.medicament.trim()) {
    toast('Indiquez le médicament', 'error')
    return
  }
  try {
    await patientApi.createReminder({
      medicament: form.value.medicament.trim(),
      heure_prise: form.value.heure_prise,
      prescription_id: form.value.prescription_id,
    })
    toast('Rappel ajouté')
    showForm.value = false
    form.value = { medicament: '', heure_prise: '08:00', prescription_id: null }
    load()
  } catch (e) {
    toast(e.response?.data?.detail || 'Erreur', 'error')
  }
}

async function toggleReminder(r) {
  try {
    await patientApi.updateReminder(r.id, { actif: !r.actif })
    load()
  } catch {
    toast('Erreur', 'error')
  }
}

async function removeReminder(r) {
  try {
    await patientApi.deleteReminder(r.id)
    toast('Rappel supprimé')
    load()
  } catch {
    toast('Erreur', 'error')
  }
}

function useOrdonnance(o) {
  form.value.medicament = o.medicament
  form.value.prescription_id = o.id
  showForm.value = true
  tab.value = 'rappels'
}

onMounted(load)
</script>

<template>
  <PatientLayout>
    <header class="mb-6">
      <h1 class="font-display text-3xl font-bold text-slate-900 dark:text-white">Plan de soins</h1>
      <p class="mt-1 text-slate-600 dark:text-slate-400">
        Suivi hospitalier, ordonnances médicales et rappels de prise
      </p>
    </header>

    <div v-if="loading" class="py-16 text-center text-slate-400">Chargement…</div>

    <template v-else-if="plan">
      <!-- Stats -->
      <div class="mb-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div class="rounded-2xl bg-white p-4 shadow-sm dark:bg-slate-800">
          <p class="text-xs text-slate-500">Soins planifiés</p>
          <p class="text-2xl font-bold text-teal-700">{{ plan.soins_total }}</p>
        </div>
        <div class="rounded-2xl bg-white p-4 shadow-sm dark:bg-slate-800">
          <p class="text-xs text-slate-500">Réalisés</p>
          <p class="text-2xl font-bold text-emerald-600">{{ plan.soins_realises }}</p>
        </div>
        <div class="rounded-2xl bg-white p-4 shadow-sm dark:bg-slate-800">
          <p class="text-xs text-slate-500">En attente</p>
          <p class="text-2xl font-bold text-blue-600">{{ plan.soins_en_attente }}</p>
        </div>
        <div class="rounded-2xl bg-white p-4 shadow-sm dark:bg-slate-800">
          <p class="text-xs text-slate-500">Rappels actifs</p>
          <p class="text-2xl font-bold text-violet-600">{{ rappels.filter(r => r.actif).length }}</p>
        </div>
      </div>

      <!-- Hospitalisation -->
      <section v-if="hosp" class="mb-6 overflow-hidden rounded-2xl border border-amber-200 bg-gradient-to-r from-amber-50 to-orange-50 dark:border-amber-900 dark:from-amber-950/30 dark:to-orange-950/20">
        <div class="p-5">
          <div class="flex flex-wrap items-start justify-between gap-3">
            <div>
              <span class="rounded-full bg-amber-200 px-3 py-0.5 text-xs font-semibold text-amber-900 dark:bg-amber-900 dark:text-amber-100">
                {{ hosp.statut_label }}
              </span>
              <h2 class="mt-2 font-display text-xl font-bold text-amber-950 dark:text-amber-100">Hospitalisation en cours</h2>
              <p class="mt-1 text-sm text-amber-800 dark:text-amber-200">{{ hosp.localisation }}</p>
            </div>
            <div class="text-right text-sm text-amber-800 dark:text-amber-200">
              <p>Entrée : {{ fmt(hosp.date_entree) }}</p>
              <p v-if="hosp.date_sortie_prevue">Sortie prévue : {{ fmtDate(hosp.date_sortie_prevue) }}</p>
            </div>
          </div>
          <div class="mt-4 grid gap-3 sm:grid-cols-2">
            <div class="rounded-xl bg-white/70 p-3 dark:bg-slate-900/40">
              <p class="text-xs font-medium uppercase text-slate-500">Médecin référent</p>
              <p class="font-semibold">{{ hosp.medecin_referent }}</p>
            </div>
            <div class="rounded-xl bg-white/70 p-3 dark:bg-slate-900/40">
              <p class="text-xs font-medium uppercase text-slate-500">Motif</p>
              <p class="text-sm">{{ hosp.motif_admission }}</p>
            </div>
          </div>
          <p v-if="hosp.notes" class="mt-3 text-xs italic text-amber-700 dark:text-amber-300">{{ hosp.notes }}</p>
        </div>
      </section>

      <div v-else class="mb-6 rounded-2xl border border-slate-200 bg-slate-50 py-8 text-center dark:border-slate-700 dark:bg-slate-800/60">
        <p class="text-4xl">🏠</p>
        <p class="mt-2 font-medium text-slate-600 dark:text-slate-300">Pas d'hospitalisation active</p>
        <p class="text-sm text-slate-500">Les soins infirmiers apparaîtront ici lors d'une admission</p>
      </div>

      <!-- Tabs -->
      <div class="mb-4 flex flex-wrap gap-2 border-b border-slate-200 dark:border-slate-700">
        <button
          v-for="t in [
            { id: 'soins', label: 'Soins infirmiers', icon: '💉', n: soins.length },
            { id: 'constantes', label: 'Constantes', icon: '🩺', n: constantes.length },
            { id: 'ordonnances', label: 'Ordonnances', icon: '📋', n: ordonnances.length },
            { id: 'rappels', label: 'Rappels', icon: '⏰', n: rappels.length },
          ]"
          :key="t.id"
          type="button"
          class="border-b-2 px-4 py-2 text-sm font-medium"
          :class="tab === t.id ? 'border-teal-600 text-teal-700' : 'border-transparent text-slate-500'"
          @click="tab = t.id"
        >
          {{ t.icon }} {{ t.label }} <span v-if="t.n" class="text-xs">({{ t.n }})</span>
        </button>
      </div>

      <p
        v-if="message"
        class="mb-4 rounded-xl px-4 py-2 text-sm"
        :class="messageType === 'error' ? 'bg-red-50 text-red-700' : 'bg-emerald-50 text-emerald-700'"
      >
        {{ message }}
      </p>

      <!-- Soins infirmiers -->
      <div v-if="tab === 'soins'" class="space-y-3">
        <article
          v-for="s in soins"
          :key="s.id"
          class="rounded-2xl border bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-800"
        >
          <div class="flex flex-wrap items-start justify-between gap-2">
            <p class="font-medium">{{ s.description }}</p>
            <span class="rounded-full px-2.5 py-0.5 text-xs font-medium" :class="statutClass[s.statut] || statutClass.PLANIFIE">
              {{ s.statut_label }}
            </span>
          </div>
          <div class="mt-2 flex flex-wrap gap-4 text-xs text-slate-500">
            <span>📅 Planifié : {{ fmt(s.planifie_a) }}</span>
            <span v-if="s.realise_a">✅ Réalisé : {{ fmt(s.realise_a) }}</span>
            <span v-if="s.infirmier_nom">👩‍⚕️ {{ s.infirmier_nom }}</span>
            <span v-if="s.medicament_lie">💊 {{ s.medicament_lie }}</span>
          </div>
        </article>
        <p v-if="!soins.length" class="py-10 text-center text-slate-400">Aucun soin planifié pour le moment</p>
      </div>

      <!-- Constantes vitales -->
      <div v-else-if="tab === 'constantes'" class="space-y-3">
        <article
          v-for="v in constantes"
          :key="v.id"
          class="rounded-2xl border bg-white p-4 dark:border-slate-700 dark:bg-slate-800"
        >
          <p class="mb-3 text-xs text-slate-500">{{ fmt(v.date_prise) }}</p>
          <div class="grid grid-cols-2 gap-3 sm:grid-cols-5">
            <div class="rounded-xl bg-red-50 p-3 text-center dark:bg-red-950/30">
              <p class="text-xs text-slate-500">Température</p>
              <p class="text-lg font-bold">{{ v.temperature ?? '—' }}<span class="text-xs">°C</span></p>
            </div>
            <div class="rounded-xl bg-blue-50 p-3 text-center dark:bg-blue-950/30">
              <p class="text-xs text-slate-500">Tension</p>
              <p class="text-lg font-bold">{{ v.tension_systolique ?? '—' }}/{{ v.tension_diastolique ?? '—' }}</p>
            </div>
            <div class="rounded-xl bg-pink-50 p-3 text-center dark:bg-pink-950/30">
              <p class="text-xs text-slate-500">Fréq. cardiaque</p>
              <p class="text-lg font-bold">{{ v.frequence_cardiaque ?? '—' }}<span class="text-xs"> bpm</span></p>
            </div>
            <div class="rounded-xl bg-cyan-50 p-3 text-center dark:bg-cyan-950/30">
              <p class="text-xs text-slate-500">SpO2</p>
              <p class="text-lg font-bold">{{ v.saturation_o2 ?? '—' }}<span class="text-xs">%</span></p>
            </div>
          </div>
        </article>
        <p v-if="!constantes.length" class="py-10 text-center text-slate-400">Aucune constante enregistrée</p>
      </div>

      <!-- Ordonnances -->
      <div v-else-if="tab === 'ordonnances'" class="space-y-3">
        <article
          v-for="o in ordonnances"
          :key="o.id"
          class="flex flex-wrap items-start justify-between gap-3 rounded-2xl border bg-white p-4 dark:border-slate-700 dark:bg-slate-800"
        >
          <div>
            <p class="font-semibold text-teal-800 dark:text-teal-200">{{ o.medicament }}</p>
            <p class="mt-1 text-sm">{{ o.posologie }} · {{ o.duree_jours }} jours</p>
            <p v-if="o.instructions" class="mt-1 text-xs text-slate-500">{{ o.instructions }}</p>
            <p class="mt-2 text-xs text-slate-400">{{ o.medecin }} — {{ fmt(o.date_consultation) }}</p>
          </div>
          <button
            type="button"
            class="shrink-0 rounded-xl bg-violet-100 px-3 py-1.5 text-xs font-medium text-violet-800 hover:bg-violet-200 dark:bg-violet-950/40"
            @click="useOrdonnance(o)"
          >
            + Rappel
          </button>
        </article>
        <p v-if="!ordonnances.length" class="py-10 text-center text-slate-400">Aucune ordonnance validée</p>
      </div>

      <!-- Rappels -->
      <div v-else-if="tab === 'rappels'">
        <div class="mb-4 flex justify-end">
          <button type="button" class="rounded-xl bg-violet-600 px-4 py-2 text-sm text-white" @click="showForm = !showForm">
            + Ajouter un rappel
          </button>
        </div>

        <div v-if="showForm" class="mb-4 rounded-2xl border border-violet-200 bg-violet-50/50 p-4 dark:border-violet-900 dark:bg-violet-950/20">
          <div class="grid gap-3 sm:grid-cols-2">
            <input v-model="form.medicament" class="input-field" placeholder="Médicament" />
            <input v-model="form.heure_prise" type="time" class="input-field" />
          </div>
          <button type="button" class="mt-3 rounded-xl bg-violet-600 px-4 py-2 text-sm text-white" @click="addReminder">
            Enregistrer
          </button>
        </div>

        <div class="space-y-2">
          <div
            v-for="r in rappels"
            :key="r.id"
            class="flex flex-wrap items-center justify-between gap-3 rounded-xl bg-white px-4 py-3 shadow-sm dark:bg-slate-800"
          >
            <div>
              <p class="font-medium">{{ r.medicament }}</p>
              <p class="text-sm text-slate-500">Prise à {{ fmtTime(r.heure_prise) }}</p>
            </div>
            <div class="flex items-center gap-2">
              <button
                type="button"
                class="rounded-full px-3 py-1 text-xs font-medium"
                :class="r.actif ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-500'"
                @click="toggleReminder(r)"
              >
                {{ r.actif ? 'Actif' : 'Inactif' }}
              </button>
              <button type="button" class="text-xs text-red-500 hover:underline" @click="removeReminder(r)">Supprimer</button>
            </div>
          </div>
          <p v-if="!rappels.length" class="py-8 text-center text-slate-400">Aucun rappel — ajoutez-en depuis vos ordonnances</p>
        </div>
      </div>
    </template>
  </PatientLayout>
</template>
