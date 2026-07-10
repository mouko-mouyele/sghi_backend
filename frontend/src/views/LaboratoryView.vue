<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import AppLayout from '../components/AppLayout.vue'
import StatCard from '../components/StatCard.vue'
import LabWorkflowStepper from '../components/LabWorkflowStepper.vue'
import { auth, laboratory, patients, getRole } from '../api/client'
import { parseApiError } from '../utils/errors.js'

const role = computed(() => getRole())
const isBiologist = computed(() => ['BIOLOGISTE', 'ADMIN'].includes(role.value))
const canPrescribe = computed(() => ['MEDECIN', 'ADMIN'].includes(role.value))

const user = ref(null)
const stats = ref(null)
const tab = ref('commandes')
const exams = ref([])
const orders = ref([])
const patientList = ref([])
const loading = ref(true)
const exporting = ref(false)
const filterStatut = ref('')
const searchQuery = ref('')
const expandedId = ref(null)
const resultForms = ref({})
const showOrderForm = ref(false)
const orderForm = ref({ patient_id: '', examen_id: '', notes: '' })
const toast = ref({ show: false, text: '', type: 'success' })
const now = ref(new Date())
let clockTimer = null
let toastTimer = null

const statuts = [
  { value: '', label: 'Tous', icon: '🔬' },
  { value: 'COMMANDE', label: 'Commandés', icon: '📋' },
  { value: 'PRELEVEMENT', label: 'Prélèvement', icon: '🩸' },
  { value: 'AFFECTATION', label: 'Affectation', icon: '🧪' },
  { value: 'SAISIE', label: 'Saisie', icon: '⌨️' },
  { value: 'VALIDATION', label: 'Validation', icon: '⏳' },
  { value: 'PUBLIE', label: 'Publiés', icon: '✅' },
]

const nextStep = {
  COMMANDE: { statut: 'PRELEVEMENT', label: 'Confirmer le prélèvement', icon: '🩸' },
  PRELEVEMENT: { statut: 'AFFECTATION', label: 'Affecter au laboratoire', icon: '🧪' },
  AFFECTATION: { statut: 'SAISIE', label: 'Ouvrir la saisie', icon: '⌨️' },
}

const examIcons = {
  NFS: '🩸', GLY: '💧', CREAT: '🫘', HIV: '🛡️',
}

const validationQueue = computed(() =>
  orders.value.filter((o) => o.statut === 'VALIDATION' && o.resultat && !o.resultat.valide),
)

const filteredOrders = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  if (!q) return orders.value
  return orders.value.filter((o) =>
    o.patient_nom.toLowerCase().includes(q)
    || o.patient_dossier.toLowerCase().includes(q)
    || o.examen_libelle.toLowerCase().includes(q)
    || o.examen_code.toLowerCase().includes(q),
  )
})

const clockLabel = computed(() =>
  now.value.toLocaleString('fr-FR', {
    weekday: 'long', day: 'numeric', month: 'long', hour: '2-digit', minute: '2-digit',
  }),
)

function showToast(text, type = 'success') {
  toast.value = { show: true, text, type }
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => { toast.value.show = false }, 4500)
}

function statutLabel(s) {
  return statuts.find((x) => x.value === s)?.label || s
}

function statutClass(s) {
  const map = {
    COMMANDE: 'border-slate-200 dark:border-slate-600 bg-slate-50 dark:bg-slate-800/60 text-slate-700 dark:text-slate-300',
    PRELEVEMENT: 'border-blue-200 bg-blue-50 dark:bg-blue-950/40 text-blue-800',
    AFFECTATION: 'border-indigo-200 bg-indigo-50 text-indigo-800',
    SAISIE: 'border-amber-200 bg-amber-50 dark:bg-amber-950/40 text-amber-800 dark:text-amber-200',
    VALIDATION: 'border-orange-300 bg-orange-50 dark:bg-orange-950/40 text-orange-800 dark:text-orange-200 ring-2 ring-orange-200',
    PUBLIE: 'border-emerald-200 dark:border-emerald-800 bg-emerald-50 dark:bg-emerald-950/40 text-emerald-800 dark:text-emerald-200',
  }
  return map[s] || 'border-slate-200 dark:border-slate-600 bg-slate-50 dark:bg-slate-800/60 text-slate-600 dark:text-slate-400'
}

function examIcon(code) {
  return examIcons[code] || '🔬'
}

function fmt(d) {
  if (!d) return '—'
  return new Date(d).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' })
}

function ensureResultForm(order) {
  if (!resultForms.value[order.id]) {
    resultForms.value[order.id] = {
      valeur: order.resultat?.valeur || '',
      unite: order.resultat?.unite || '',
      valeur_reference: order.resultat?.valeur_reference || '',
      commentaire: order.resultat?.commentaire || '',
    }
  }
  return resultForms.value[order.id]
}

function toggleExpand(order) {
  expandedId.value = expandedId.value === order.id ? null : order.id
  if (expandedId.value === order.id) ensureResultForm(order)
}

function openOrder(order) {
  expandedId.value = order.id
  ensureResultForm(order)
  tab.value = 'commandes'
}

async function load() {
  loading.value = true
  try {
    const reqs = [
      laboratory.dashboard(),
      laboratory.orders(filterStatut.value),
      laboratory.exams(),
    ]
    if (canPrescribe.value) reqs.push(patients.list({ page: 1, page_size: 100 }))
    const results = await Promise.all(reqs)
    stats.value = results[0].data
    orders.value = results[1].data
    exams.value = results[2].data
    if (canPrescribe.value) patientList.value = results[3].data.items
  } finally {
    loading.value = false
  }
}

async function advance(order) {
  const step = nextStep[order.statut]
  if (!step) return
  try {
    await laboratory.advanceWorkflow(order.id, step.statut)
    showToast(step.label)
    load()
  } catch (e) {
    showToast(parseApiError(e), 'error')
  }
}

async function saveResult(order) {
  try {
    await laboratory.submitResult(order.id, ensureResultForm(order))
    showToast('Résultat enregistré — en attente de validation biologiste')
    load()
  } catch (e) {
    showToast(parseApiError(e), 'error')
  }
}

async function validate(order) {
  if (!order.resultat?.id) return
  try {
    await laboratory.validateResult(order.resultat.id)
    showToast('Résultat validé, publié et PDF généré')
    load()
  } catch (e) {
    showToast(parseApiError(e), 'error')
  }
}

async function createOrder() {
  try {
    await laboratory.createOrder({
      patient_id: Number(orderForm.value.patient_id),
      examen_id: Number(orderForm.value.examen_id),
      notes: orderForm.value.notes,
    })
    showToast('Commande prescrite avec succès')
    showOrderForm.value = false
    orderForm.value = { patient_id: '', examen_id: '', notes: '' }
    tab.value = 'commandes'
    load()
  } catch (e) {
    showToast(parseApiError(e), 'error')
  }
}

async function exportCsv() {
  exporting.value = true
  try {
    await laboratory.exportCsv(filterStatut.value)
    showToast('Export CSV téléchargé — compatible Excel')
  } catch (e) {
    showToast(parseApiError(e, 'Erreur export CSV'), 'error')
  } finally {
    exporting.value = false
  }
}

function setFilter(value) {
  filterStatut.value = value
  load()
}

onMounted(async () => {
  clockTimer = setInterval(() => { now.value = new Date() }, 30000)
  try {
    const { data } = await auth.me()
    user.value = data
  } catch { /* AppLayout gère la session */ }
  load()
})

onUnmounted(() => {
  clearInterval(clockTimer)
  clearTimeout(toastTimer)
})
</script>

<template>
  <AppLayout>
    <!-- Toast -->
    <Transition name="toast">
      <div
        v-if="toast.show"
        class="fixed bottom-6 right-6 z-50 flex max-w-sm items-start gap-3 rounded-2xl px-5 py-4 shadow-2xl"
        :class="toast.type === 'error' ? 'bg-red-600 text-white' : 'bg-slate-900 text-white'"
      >
        <span class="text-xl">{{ toast.type === 'error' ? '⚠️' : '✓' }}</span>
        <p class="text-sm font-medium">{{ toast.text }}</p>
      </div>
    </Transition>

    <!-- Hero CHU -->
    <section class="relative mb-8 overflow-hidden rounded-3xl bg-gradient-to-br from-violet-900 via-indigo-900 to-slate-900 p-8 text-white shadow-xl dark:from-slate-950 dark:via-violet-950 dark:to-indigo-950 dark:shadow-violet-950/50">
      <div class="absolute -right-16 -top-16 h-64 w-64 rounded-full bg-violet-50 dark:bg-violet-950/400/20 blur-3xl" />
      <div class="absolute -bottom-20 -left-10 h-48 w-48 rounded-full bg-indigo-400/10 blur-2xl" />
      <div class="relative flex flex-wrap items-start justify-between gap-6">
        <div>
          <div class="mb-3 inline-flex items-center gap-2 rounded-full bg-white/10 px-3 py-1 text-xs font-medium backdrop-blur">
            <span class="h-2 w-2 animate-pulse rounded-full bg-emerald-400" />
            Service de Biologie Médicale — LIS actif
          </div>
          <h1 class="font-display text-3xl font-bold tracking-tight sm:text-4xl">
            Laboratoire d'Analyses
          </h1>
          <p class="mt-2 max-w-xl text-violet-200">
            CHU de Brazzaville — Système intégré de gestion des examens biologiques
          </p>
          <p v-if="user" class="mt-3 text-sm text-violet-300">
            Connecté : <strong class="text-white">{{ user.first_name }} {{ user.last_name }}</strong>
            · {{ user.role === 'BIOLOGISTE' ? 'Biologiste responsable' : user.role }}
          </p>
        </div>
        <div class="text-right">
          <p class="text-sm capitalize text-violet-300">{{ clockLabel }}</p>
          <div class="mt-4 flex flex-wrap justify-end gap-2">
            <button
              v-if="isBiologist"
              class="inline-flex items-center gap-2 rounded-xl bg-white/10 px-4 py-2.5 text-sm font-semibold text-white backdrop-blur transition hover:bg-white/20 disabled:opacity-50"
              :disabled="exporting"
              @click="exportCsv"
            >
              📊 {{ exporting ? 'Export...' : 'Export Excel' }}
            </button>
            <button
              v-if="canPrescribe"
              class="inline-flex items-center gap-2 rounded-xl bg-white px-4 py-2.5 text-sm font-semibold text-violet-900 shadow-lg transition hover:bg-violet-50"
              @click="showOrderForm = !showOrderForm"
            >
              + Prescrire un examen
            </button>
          </div>
        </div>
      </div>
    </section>

    <!-- KPIs -->
    <div v-if="loading && !stats" class="mb-8 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <div v-for="i in 4" :key="i" class="card h-28 animate-pulse bg-slate-100 dark:bg-slate-800" />
    </div>
    <div v-else-if="stats" class="mb-8 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <StatCard
        title="Commandes du jour"
        :value="stats.commandes_jour"
        :subtitle="`${stats.total_commandes} au total`"
        icon="📥"
        color="primary"
      />
      <StatCard
        title="En analyse"
        :value="stats.en_analyse"
        :subtitle="`${stats.en_attente_prelevement} en attente prélèvement`"
        icon="🧪"
        color="purple"
      />
      <StatCard
        title="À valider"
        :value="stats.a_valider"
        subtitle="Validation biologiste requise"
        icon="⏳"
        :color="stats.a_valider > 0 ? 'warning' : 'accent'"
        :trend="stats.a_valider > 0 ? 'Action prioritaire' : undefined"
      />
      <StatCard
        title="Publiés aujourd'hui"
        :value="stats.publies_jour"
        :subtitle="`${stats.publies_total} comptes-rendus signés`"
        icon="📄"
        color="accent"
      />
    </div>

    <!-- File de validation prioritaire -->
    <section
      v-if="isBiologist && validationQueue.length"
      class="mb-8 overflow-hidden rounded-2xl border-2 border-orange-200 dark:border-orange-800 bg-gradient-to-r from-orange-50 dark:from-orange-950/30 to-amber-50 dark:to-amber-950/20 shadow-sm dark:shadow-none"
    >
      <div class="flex flex-wrap items-center justify-between gap-3 border-b border-orange-200 dark:border-orange-800/60 px-6 py-4">
        <div class="flex items-center gap-3">
          <span class="flex h-10 w-10 items-center justify-center rounded-xl bg-orange-50 dark:bg-orange-950/400 text-lg text-white shadow-lg shadow-orange-500/30">⚡</span>
          <div>
            <h2 class="font-display text-lg font-bold text-orange-900 dark:text-orange-100">File prioritaire — Validation biologiste</h2>
            <p class="text-sm text-orange-700 dark:text-orange-300">{{ validationQueue.length }} résultat(s) en attente de signature</p>
          </div>
        </div>
      </div>
      <div class="divide-y divide-orange-100">
        <div
          v-for="order in validationQueue"
          :key="'vq-' + order.id"
          class="flex flex-wrap items-center justify-between gap-4 px-6 py-4"
        >
          <div class="flex items-center gap-4">
            <span class="flex h-12 w-12 items-center justify-center rounded-2xl bg-white dark:bg-slate-800 text-2xl shadow-sm dark:shadow-none">
              {{ examIcon(order.examen_code) }}
            </span>
            <div>
              <p class="font-semibold text-slate-900 dark:text-white">{{ order.examen_libelle }}</p>
              <p class="text-sm text-slate-600 dark:text-slate-400">
                {{ order.patient_nom }} · {{ order.patient_dossier }}
              </p>
              <p class="mt-1 text-sm font-medium text-orange-800 dark:text-orange-200">
                {{ order.resultat.valeur }} {{ order.resultat.unite }}
                <span v-if="order.resultat.valeur_reference" class="font-normal text-orange-600">
                  (ref. {{ order.resultat.valeur_reference }})
                </span>
              </p>
            </div>
          </div>
          <div class="flex gap-2">
            <button
              class="rounded-xl border border-orange-300 bg-white dark:bg-slate-800 px-4 py-2 text-sm font-medium text-orange-800 dark:text-orange-200 hover:bg-orange-50 dark:bg-orange-950/40"
              @click="openOrder(order)"
            >
              Détails
            </button>
            <button
              class="rounded-xl bg-orange-600 px-5 py-2 text-sm font-semibold text-white shadow-lg shadow-orange-600/25 hover:bg-orange-700"
              @click="validate(order)"
            >
              ✓ Valider &amp; publier
            </button>
          </div>
        </div>
      </div>
    </section>

    <!-- Tabs -->
    <div class="mb-6 flex flex-wrap items-center justify-between gap-4">
      <div class="flex rounded-2xl bg-slate-100 dark:bg-slate-800 p-1">
        <button
          :class="tab === 'commandes' ? 'bg-white dark:bg-slate-800 text-violet-900 dark:text-violet-100 shadow-sm dark:shadow-none' : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:text-slate-300'"
          class="rounded-xl px-5 py-2.5 text-sm font-semibold transition"
          @click="tab = 'commandes'"
        >
          Commandes
          <span class="ml-1 rounded-full bg-violet-100 dark:bg-violet-900/40 px-2 py-0.5 text-xs text-violet-700">{{ orders.length }}</span>
        </button>
        <button
          :class="tab === 'catalogue' ? 'bg-white dark:bg-slate-800 text-violet-900 dark:text-violet-100 shadow-sm dark:shadow-none' : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:text-slate-300'"
          class="rounded-xl px-5 py-2.5 text-sm font-semibold transition"
          @click="tab = 'catalogue'"
        >
          Catalogue
          <span class="ml-1 rounded-full bg-slate-200 dark:bg-slate-700 px-2 py-0.5 text-xs">{{ exams.length }}</span>
        </button>
      </div>
    </div>

    <!-- Prescription (médecin) -->
    <Transition name="slide">
      <div v-if="showOrderForm && canPrescribe" class="card mb-6 border-violet-100 dark:border-violet-800/60 bg-violet-50 dark:bg-violet-950/40/30">
        <h2 class="mb-1 font-display text-lg font-bold text-slate-900 dark:text-white">Prescription d'examen biologique</h2>
        <p class="mb-5 text-sm text-slate-500 dark:text-slate-400">La commande sera transmise au laboratoire pour traitement</p>
        <div class="grid gap-4 sm:grid-cols-2">
          <div>
            <label class="mb-1.5 block text-sm font-medium text-slate-700 dark:text-slate-300">Patient</label>
            <select v-model="orderForm.patient_id" class="input-field">
              <option value="">— Sélectionner un patient —</option>
              <option v-for="p in patientList" :key="p.id" :value="p.id">
                {{ p.prenom }} {{ p.nom }} ({{ p.numero_dossier }})
              </option>
            </select>
          </div>
          <div>
            <label class="mb-1.5 block text-sm font-medium text-slate-700 dark:text-slate-300">Examen</label>
            <select v-model="orderForm.examen_id" class="input-field">
              <option value="">— Sélectionner un examen —</option>
              <option v-for="e in exams" :key="e.id" :value="e.id">
                {{ e.code }} — {{ e.libelle }}
              </option>
            </select>
          </div>
          <div class="sm:col-span-2">
            <label class="mb-1.5 block text-sm font-medium text-slate-700 dark:text-slate-300">Indication clinique</label>
            <input v-model="orderForm.notes" class="input-field" placeholder="Motif, contexte clinique..." />
          </div>
        </div>
        <button class="btn-primary mt-5" @click="createOrder">Transmettre au laboratoire</button>
      </div>
    </Transition>

    <!-- Commandes -->
    <div v-show="tab === 'commandes'">
      <!-- Filtres -->
      <div class="mb-5 flex flex-wrap items-center gap-3">
        <div class="relative min-w-[220px] flex-1 sm:max-w-xs">
          <span class="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 dark:text-slate-500">🔍</span>
          <input
            v-model="searchQuery"
            class="input-field pl-10"
            placeholder="Patient, dossier, examen..."
          />
        </div>
        <div class="flex flex-wrap gap-2">
          <button
            v-for="s in statuts"
            :key="s.value"
            :class="filterStatut === s.value
              ? 'border-violet-300 bg-violet-600 text-white shadow-md'
              : 'border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:border-violet-200 dark:border-violet-700'"
            class="inline-flex items-center gap-1.5 rounded-xl border px-3 py-1.5 text-xs font-medium transition"
            @click="setFilter(s.value)"
          >
            {{ s.icon }} {{ s.label }}
          </button>
        </div>
        <button class="text-sm font-medium text-violet-600 hover:underline" @click="load">↻ Actualiser</button>
      </div>

      <div v-if="loading" class="flex h-48 items-center justify-center">
        <div class="h-10 w-10 animate-spin rounded-full border-4 border-violet-200 dark:border-violet-700 border-t-violet-600" />
      </div>

      <div v-else-if="!filteredOrders.length" class="card py-16 text-center">
        <p class="text-4xl">🔬</p>
        <p class="mt-4 font-medium text-slate-600 dark:text-slate-400">Aucune commande trouvée</p>
        <p class="mt-1 text-sm text-slate-400 dark:text-slate-500">Modifiez les filtres ou prescrivez un nouvel examen</p>
      </div>

      <div v-else class="space-y-4">
        <article
          v-for="order in filteredOrders"
          :key="order.id"
          class="overflow-hidden rounded-2xl border bg-white dark:bg-slate-800 shadow-sm dark:shadow-none transition hover:shadow-md"
          :class="order.statut === 'VALIDATION' ? 'border-orange-200 dark:border-orange-800 ring-1 ring-orange-100 dark:ring-orange-900/50' : 'border-slate-100 dark:border-slate-700'"
        >
          <div
            class="flex cursor-pointer flex-wrap items-center gap-4 px-5 py-4"
            @click="toggleExpand(order)"
          >
            <span class="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-violet-50 to-indigo-50 text-2xl">
              {{ examIcon(order.examen_code) }}
            </span>
            <div class="min-w-0 flex-1">
              <div class="flex flex-wrap items-center gap-2">
                <span class="font-mono text-xs text-slate-400 dark:text-slate-500">LAB-{{ String(order.id).padStart(5, '0') }}</span>
                <span :class="statutClass(order.statut)" class="rounded-full border px-2.5 py-0.5 text-xs font-semibold">
                  {{ statutLabel(order.statut) }}
                </span>
              </div>
              <h3 class="mt-1 font-display text-lg font-semibold text-slate-900 dark:text-white">{{ order.examen_libelle }}</h3>
              <p class="text-sm text-slate-500 dark:text-slate-400">
                {{ order.patient_nom }} · <span class="font-mono">{{ order.patient_dossier }}</span>
                · {{ fmt(order.date_commande) }}
              </p>
              <div class="mt-3 hidden sm:block">
                <LabWorkflowStepper :statut="order.statut" compact />
              </div>
            </div>
            <div class="flex items-center gap-3">
              <div v-if="order.resultat && order.statut === 'PUBLIE'" class="text-right">
                <p class="text-lg font-bold text-emerald-700 dark:text-emerald-300">{{ order.resultat.valeur }}</p>
                <p class="text-xs text-slate-500 dark:text-slate-400">{{ order.resultat.unite }}</p>
              </div>
              <span class="text-slate-300">{{ expandedId === order.id ? '▲' : '▼' }}</span>
            </div>
          </div>

          <div v-if="expandedId === order.id" class="border-t border-slate-100 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/60/80 px-5 py-5">
            <LabWorkflowStepper :statut="order.statut" class="mb-5 sm:hidden" />

            <div class="mb-4 grid gap-3 sm:grid-cols-3">
              <div class="rounded-xl bg-white dark:bg-slate-800 p-3 text-sm">
                <p class="text-xs font-medium uppercase tracking-wide text-slate-400 dark:text-slate-500">Patient</p>
                <p class="mt-1 font-semibold">{{ order.patient_nom }}</p>
                <p class="font-mono text-xs text-violet-600">{{ order.patient_dossier }}</p>
              </div>
              <div class="rounded-xl bg-white dark:bg-slate-800 p-3 text-sm">
                <p class="text-xs font-medium uppercase tracking-wide text-slate-400 dark:text-slate-500">Examen</p>
                <p class="mt-1 font-semibold">{{ order.examen_code }}</p>
                <p class="text-xs text-slate-500 dark:text-slate-400">{{ order.examen_libelle }}</p>
              </div>
              <div class="rounded-xl bg-white dark:bg-slate-800 p-3 text-sm">
                <p class="text-xs font-medium uppercase tracking-wide text-slate-400 dark:text-slate-500">Dates</p>
                <p class="mt-1">Commande : {{ fmt(order.date_commande) }}</p>
                <p v-if="order.date_prelevement">Prélèvement : {{ fmt(order.date_prelevement) }}</p>
              </div>
            </div>

            <p v-if="order.notes" class="mb-4 rounded-xl border border-violet-100 dark:border-violet-800/60 bg-violet-50 dark:bg-violet-950/40 px-4 py-3 text-sm text-violet-900 dark:text-violet-100">
              <strong>Indication :</strong> {{ order.notes }}
            </p>

            <div v-if="isBiologist && nextStep[order.statut]" class="mb-4">
              <button
                class="inline-flex items-center gap-2 rounded-xl bg-violet-600 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-violet-600/25 hover:bg-violet-700"
                @click.stop="advance(order)"
              >
                {{ nextStep[order.statut].icon }} {{ nextStep[order.statut].label }}
              </button>
            </div>

            <div
              v-if="isBiologist && ['SAISIE', 'VALIDATION'].includes(order.statut)"
              class="mb-4 rounded-2xl border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-800 p-5 shadow-sm dark:shadow-none"
            >
              <h4 class="mb-4 flex items-center gap-2 font-display font-semibold text-slate-800 dark:text-slate-100">
                <span class="flex h-8 w-8 items-center justify-center rounded-lg bg-violet-100 dark:bg-violet-900/40 text-sm">⌨️</span>
                Saisie des résultats
                <span v-if="order.resultat?.valide" class="ml-2 rounded-full bg-emerald-100 dark:bg-emerald-900/40 px-2 py-0.5 text-xs text-emerald-700 dark:text-emerald-300">
                  Validé — immuable
                </span>
              </h4>
              <div v-if="!order.resultat?.valide" class="grid gap-4 sm:grid-cols-2">
                <div>
                  <label class="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Valeur *</label>
                  <input v-model="ensureResultForm(order).valeur" class="input-field font-mono text-lg" placeholder="Ex. 5.2" />
                </div>
                <div>
                  <label class="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Unité</label>
                  <input v-model="ensureResultForm(order).unite" class="input-field" placeholder="g/L, mmol/L..." />
                </div>
                <div>
                  <label class="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Valeurs de référence</label>
                  <input v-model="ensureResultForm(order).valeur_reference" class="input-field" placeholder="4.0 — 5.5" />
                </div>
                <div>
                  <label class="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Commentaire biologiste</label>
                  <input v-model="ensureResultForm(order).commentaire" class="input-field" placeholder="Interprétation..." />
                </div>
              </div>
              <button
                v-if="!order.resultat?.valide"
                class="btn-primary mt-4"
                @click.stop="saveResult(order)"
              >
                Enregistrer le résultat
              </button>
            </div>

            <div
              v-if="isBiologist && order.statut === 'VALIDATION' && order.resultat && !order.resultat.valide"
              class="rounded-2xl border-2 border-orange-200 dark:border-orange-800 bg-gradient-to-r from-orange-50 dark:from-orange-950/30 to-white dark:to-slate-900 p-5"
            >
              <p class="mb-3 text-sm text-orange-800 dark:text-orange-200">
                Résultat prêt pour validation et signature électronique :
                <strong class="text-lg">{{ order.resultat.valeur }} {{ order.resultat.unite }}</strong>
              </p>
              <button
                class="rounded-xl bg-orange-600 px-6 py-2.5 text-sm font-bold text-white shadow-lg shadow-orange-600/30 hover:bg-orange-700"
                @click.stop="validate(order)"
              >
                ✓ Valider, publier &amp; générer le PDF
              </button>
            </div>

            <div v-if="order.statut === 'PUBLIE' && order.resultat" class="rounded-2xl border border-emerald-200 dark:border-emerald-800 bg-emerald-50 dark:bg-emerald-950/40 p-5">
              <div class="flex flex-wrap items-center justify-between gap-4">
                <div>
                  <p class="text-sm font-medium text-emerald-800 dark:text-emerald-200">Compte-rendu publié</p>
                  <p class="mt-1 text-2xl font-bold text-emerald-900 dark:text-emerald-100">
                    {{ order.resultat.valeur }} <span class="text-base font-normal">{{ order.resultat.unite }}</span>
                  </p>
                  <p class="mt-1 text-xs text-emerald-700 dark:text-emerald-300">Validé le {{ fmt(order.resultat.date_validation) }}</p>
                </div>
                <a
                  v-if="order.resultat.pdf_url"
                  :href="order.resultat.pdf_url"
                  target="_blank"
                  rel="noopener"
                  class="inline-flex items-center gap-2 rounded-xl bg-white dark:bg-slate-800 px-5 py-3 text-sm font-semibold text-red-700 dark:text-red-300 shadow-sm dark:shadow-none ring-1 ring-red-100 dark:ring-red-900/50 hover:bg-red-50 dark:bg-red-950/40"
                  @click.stop
                >
                  📄 Compte-rendu PDF signé
                </a>
              </div>
            </div>
          </div>
        </article>
      </div>
    </div>

    <!-- Catalogue -->
    <div v-show="tab === 'catalogue'">
      <p class="mb-5 text-sm text-slate-500 dark:text-slate-400">
        {{ stats?.examens_catalogue || exams.length }} examens référencés — tarification CHU
      </p>
      <div class="grid gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        <div
          v-for="exam in exams"
          :key="exam.id"
          class="group relative overflow-hidden rounded-2xl border border-slate-100 dark:border-slate-700 bg-white dark:bg-slate-800 p-5 shadow-sm dark:shadow-none transition hover:-translate-y-1 hover:border-violet-200 dark:border-violet-700 hover:shadow-lg"
        >
          <div class="absolute -right-6 -top-6 h-24 w-24 rounded-full bg-violet-100 dark:bg-violet-900/40 opacity-0 transition group-hover:opacity-100" />
          <div class="relative">
            <div class="flex items-start justify-between">
              <span class="flex h-12 w-12 items-center justify-center rounded-2xl bg-violet-50 dark:bg-violet-950/40 text-2xl">
                {{ examIcon(exam.code) }}
              </span>
              <span class="rounded-lg bg-emerald-50 dark:bg-emerald-950/40 px-2 py-1 text-sm font-bold text-emerald-700 dark:text-emerald-300">
                {{ Number(exam.prix).toLocaleString('fr-FR') }} <span class="text-xs font-normal">FCFA</span>
              </span>
            </div>
            <span class="mt-4 inline-block rounded-md bg-violet-100 dark:bg-violet-900/40 px-2 py-0.5 font-mono text-xs font-bold text-violet-700">
              {{ exam.code }}
            </span>
            <h3 class="mt-2 font-display font-semibold text-slate-900 dark:text-white">{{ exam.libelle }}</h3>
            <p class="mt-2 flex items-center gap-1 text-xs text-slate-400 dark:text-slate-500">
              <span class="inline-block h-1.5 w-1.5 rounded-full bg-amber-400" />
              Délai indicatif : {{ exam.delai_heures }}h
            </p>
          </div>
        </div>
      </div>
    </div>
  </AppLayout>
</template>

<style scoped>
.toast-enter-active,
.toast-leave-active {
  transition: all 0.35s ease;
}
.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateY(1rem);
}
.slide-enter-active,
.slide-leave-active {
  transition: all 0.3s ease;
}
.slide-enter-from,
.slide-leave-to {
  opacity: 0;
  transform: translateY(-0.5rem);
}
</style>
