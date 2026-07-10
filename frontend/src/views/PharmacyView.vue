<script setup>
import { ref, computed, onMounted } from 'vue'
import AppLayout from '../components/AppLayout.vue'
import { pharmacy, getRole } from '../api/client'

const role = computed(() => getRole())
const isPharmacist = computed(() => ['PHARMACIEN', 'ADMIN'].includes(role.value))

const tab = ref('catalogue')
const loading = ref(true)
const medications = ref([])
const categories = ref([])
const stocks = ref([])
const alerts = ref([])
const requests = ref([])
const search = ref('')
const filterCat = ref('')
const filterStatut = ref('')
const toast = ref('')

const tabs = computed(() => {
  const t = [{ id: 'catalogue', label: 'Catalogue', icon: '📋' }]
  if (isPharmacist.value) {
    t.push({ id: 'stocks', label: 'Stocks & lots', icon: '📦' })
    t.push({ id: 'demandes', label: 'Demandes patients', icon: '🛒' })
  } else {
    t.push({ id: 'stocks', label: 'Stocks', icon: '📦' })
  }
  return t
})

const filteredMeds = computed(() => {
  const q = search.value.trim().toLowerCase()
  return medications.value.filter((m) => {
    if (filterCat.value && m.categorie !== filterCat.value) return false
    if (!q) return true
    return m.nom.toLowerCase().includes(q) || m.code.toLowerCase().includes(q)
  })
})

const stats = computed(() => ({
  total: medications.value.length,
  disponibles: medications.value.filter((m) => m.disponible).length,
  alertes: alerts.value.length,
  demandes: requests.value.filter((r) => r.statut === 'SOUMISE').length,
}))

function fmt(n) {
  return Number(n || 0).toLocaleString('fr-FR')
}

function fmtDate(d) {
  if (!d) return '—'
  return new Date(d).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' })
}

function showToast(msg) {
  toast.value = msg
  setTimeout(() => { toast.value = '' }, 3500)
}

function statutClass(s) {
  const map = {
    SOUMISE: 'bg-blue-100 text-blue-800 dark:bg-blue-950/40 dark:text-blue-200',
    EN_PREPARATION: 'bg-amber-100 text-amber-800 dark:bg-amber-950/40',
    PRETE: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/40',
    RETIREE: 'bg-slate-100 text-slate-600 dark:bg-slate-800',
    ANNULEE: 'bg-red-100 text-red-700 dark:bg-red-950/40',
  }
  return map[s] || 'bg-slate-100 text-slate-600'
}

const statutActions = {
  SOUMISE: { next: 'EN_PREPARATION', label: 'Prendre en charge' },
  EN_PREPARATION: { next: 'PRETE', label: 'Marquer prête' },
  PRETE: { next: 'RETIREE', label: 'Confirmer retrait' },
}

async function loadCatalogue() {
  const params = {}
  if (filterCat.value) params.categorie = filterCat.value
  if (search.value.trim()) params.q = search.value.trim()
  const { data } = await pharmacy.medications(params)
  medications.value = data
}

async function loadAll() {
  loading.value = true
  try {
    const tasks = [pharmacy.medications({}), pharmacy.categories()]
    if (isPharmacist.value) {
      tasks.push(pharmacy.stocks(), pharmacy.alerts(), pharmacy.requests({}))
    } else {
      tasks.push(pharmacy.stocks().catch(() => ({ data: [] })))
    }
    const results = await Promise.all(tasks)
    medications.value = results[0].data
    categories.value = results[1].data
    if (isPharmacist.value) {
      stocks.value = results[2].data
      alerts.value = results[3].data
      requests.value = results[4].data
    } else {
      stocks.value = results[2]?.data || []
    }
  } finally {
    loading.value = false
  }
}

async function searchCatalogue() {
  await loadCatalogue()
}

async function updateStatus(req) {
  const action = statutActions[req.statut]
  if (!action) return
  try {
    const { data } = await pharmacy.updateRequestStatus(req.id, action.next)
    const idx = requests.value.findIndex((r) => r.id === req.id)
    if (idx >= 0) requests.value[idx] = data
    showToast(`Demande ${data.reference} → ${data.statut_label}`)
  } catch (e) {
    showToast(e.response?.data?.detail || 'Erreur')
  }
}

async function cancelRequest(req) {
  try {
    const { data } = await pharmacy.updateRequestStatus(req.id, 'ANNULEE')
    const idx = requests.value.findIndex((r) => r.id === req.id)
    if (idx >= 0) requests.value[idx] = data
    showToast('Demande annulée')
  } catch (e) {
    showToast(e.response?.data?.detail || 'Erreur')
  }
}

onMounted(loadAll)
</script>

<template>
  <AppLayout>
    <header class="mb-8 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 class="font-display text-3xl font-bold">Pharmacie CHU</h1>
        <p class="mt-1 text-slate-500 dark:text-slate-400">
          Catalogue des produits, prix publics et gestion des stocks
        </p>
      </div>
      <div class="flex flex-wrap gap-3 text-sm">
        <span class="rounded-xl bg-emerald-50 px-3 py-1.5 font-medium text-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-200">
          {{ stats.total }} produits
        </span>
        <span class="rounded-xl bg-blue-50 px-3 py-1.5 font-medium text-blue-800 dark:bg-blue-950/40">
          {{ stats.disponibles }} disponibles
        </span>
        <span v-if="stats.alertes" class="rounded-xl bg-amber-50 px-3 py-1.5 font-medium text-amber-800 dark:bg-amber-950/40">
          {{ stats.alertes }} alerte(s) stock
        </span>
      </div>
    </header>

    <div class="mb-6 flex flex-wrap gap-2 border-b border-slate-200 dark:border-slate-700">
      <button
        v-for="t in tabs"
        :key="t.id"
        type="button"
        class="border-b-2 px-4 py-2.5 text-sm font-medium transition"
        :class="tab === t.id ? 'border-primary-600 text-primary-700 dark:text-primary-300' : 'border-transparent text-slate-500 hover:text-slate-700'"
        @click="tab = t.id"
      >
        {{ t.icon }} {{ t.label }}
        <span v-if="t.id === 'demandes' && stats.demandes" class="ml-1 rounded-full bg-red-500 px-1.5 text-xs text-white">{{ stats.demandes }}</span>
      </button>
    </div>

    <div v-if="toast" class="fixed bottom-6 right-6 z-50 rounded-xl bg-slate-900 px-4 py-3 text-sm text-white shadow-lg">{{ toast }}</div>

    <div v-if="loading" class="py-16 text-center text-slate-400">Chargement du catalogue…</div>

    <!-- CATALOGUE -->
    <div v-else-if="tab === 'catalogue'">
      <div class="mb-6 flex flex-wrap gap-3">
        <input
          v-model="search"
          type="search"
          class="input-field min-w-[220px] flex-1"
          placeholder="Rechercher un médicament…"
          @keyup.enter="searchCatalogue"
        />
        <select v-model="filterCat" class="input-field w-auto" @change="searchCatalogue">
          <option value="">Toutes catégories</option>
          <option v-for="c in categories" :key="c.code" :value="c.code">{{ c.label }} ({{ c.count }})</option>
        </select>
        <button type="button" class="btn-primary" @click="searchCatalogue">Rechercher</button>
      </div>

      <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        <article
          v-for="m in filteredMeds"
          :key="m.id"
          class="flex flex-col rounded-2xl border border-slate-200 bg-white p-4 shadow-sm transition hover:shadow-md dark:border-slate-700 dark:bg-slate-800/80"
        >
          <div class="mb-2 flex items-start justify-between gap-2">
            <span class="rounded-lg bg-slate-100 px-2 py-0.5 font-mono text-xs text-slate-600 dark:bg-slate-700 dark:text-slate-300">{{ m.code }}</span>
            <span
              class="rounded-full px-2 py-0.5 text-xs font-medium"
              :class="m.disponible ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/40' : 'bg-red-100 text-red-700 dark:bg-red-950/40'"
            >
              {{ m.disponible ? 'En stock' : 'Rupture' }}
            </span>
          </div>
          <h3 class="font-semibold leading-snug text-slate-900 dark:text-white">{{ m.nom }}</h3>
          <p class="mt-1 text-xs text-slate-500">{{ m.forme }} · {{ m.categorie_label }}</p>
          <p v-if="m.description" class="mt-2 line-clamp-2 text-xs text-slate-500 dark:text-slate-400">{{ m.description }}</p>
          <div class="mt-auto flex items-end justify-between pt-4">
            <div>
              <p class="text-xl font-bold text-primary-700 dark:text-primary-300">{{ fmt(m.prix_unitaire) }} <span class="text-xs font-normal">FCFA</span></p>
              <p class="text-xs text-slate-400">Stock : {{ m.stock_disponible }}</p>
            </div>
          </div>
        </article>
      </div>
      <p v-if="!filteredMeds.length" class="py-12 text-center text-slate-400">Aucun produit trouvé</p>
    </div>

    <!-- STOCKS -->
    <div v-else-if="tab === 'stocks'">
      <div v-if="alerts.length" class="mb-6 rounded-xl border border-amber-200 bg-amber-50 p-4 dark:border-amber-800 dark:bg-amber-950/30">
        <p class="font-semibold text-amber-800 dark:text-amber-200">{{ alerts.length }} alerte(s) stock critique</p>
        <ul class="mt-2 space-y-1 text-sm text-amber-700 dark:text-amber-300">
          <li v-for="(a, i) in alerts.slice(0, 5)" :key="i">{{ a.medicament }} — lot {{ a.lot }} : {{ a.quantite }} restant(s)</li>
        </ul>
      </div>

      <div class="card overflow-hidden p-0">
        <table class="w-full text-sm">
          <thead class="bg-slate-50 dark:bg-slate-800/60">
            <tr>
              <th class="px-4 py-3 text-left">Produit</th>
              <th class="px-4 py-3 text-left">Prix unitaire</th>
              <th class="px-4 py-3 text-left">Lot</th>
              <th class="px-4 py-3 text-left">Quantité</th>
              <th class="px-4 py-3 text-left">Péremption</th>
              <th class="px-4 py-3 text-left">Statut</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="s in stocks" :key="s.id" class="border-t dark:border-slate-700">
              <td class="px-4 py-3">
                <p class="font-medium">{{ s.medicament }}</p>
                <p class="text-xs text-slate-500">{{ s.forme }} · {{ s.code }}</p>
              </td>
              <td class="px-4 py-3 font-medium">{{ fmt(s.prix_unitaire) }} FCFA</td>
              <td class="px-4 py-3 font-mono text-xs">{{ s.lot }}</td>
              <td class="px-4 py-3">{{ s.quantite }}</td>
              <td class="px-4 py-3">{{ s.peremption?.slice(0, 10) }}</td>
              <td class="px-4 py-3">
                <span :class="s.alerte ? 'bg-red-100 text-red-700' : 'bg-emerald-100 text-emerald-700'" class="rounded-full px-2 py-0.5 text-xs">
                  {{ s.alerte ? 'Alerte' : 'OK' }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
        <p v-if="!stocks.length" class="py-8 text-center text-slate-400">Aucun lot en stock</p>
      </div>
    </div>

    <!-- DEMANDES PATIENTS -->
    <div v-else-if="tab === 'demandes' && isPharmacist">
      <div class="mb-4 flex gap-2">
        <select v-model="filterStatut" class="input-field w-auto" @change="pharmacy.requests({ statut: filterStatut || undefined }).then(r => requests = r.data)">
          <option value="">Tous statuts</option>
          <option value="SOUMISE">Soumises</option>
          <option value="EN_PREPARATION">En préparation</option>
          <option value="PRETE">Prêtes</option>
          <option value="RETIREE">Retirées</option>
        </select>
      </div>

      <div class="space-y-4">
        <article v-for="req in requests" :key="req.id" class="card">
          <div class="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p class="font-mono text-sm text-primary-600">{{ req.reference }}</p>
              <p class="font-semibold">{{ req.patient_nom }}</p>
              <p class="text-xs text-slate-500">Dossier {{ req.patient_dossier }} · {{ fmtDate(req.created_at) }}</p>
            </div>
            <div class="text-right">
              <span class="rounded-full px-3 py-1 text-xs font-medium" :class="statutClass(req.statut)">{{ req.statut_label }}</span>
              <p class="mt-1 text-lg font-bold">{{ fmt(req.montant_total) }} FCFA</p>
            </div>
          </div>

          <ul class="mt-4 divide-y rounded-xl border dark:border-slate-700">
            <li v-for="l in req.lignes" :key="l.id" class="flex justify-between px-4 py-2 text-sm">
              <span>{{ l.medicament_nom }} × {{ l.quantite }}</span>
              <span class="font-medium">{{ fmt(l.sous_total) }} FCFA</span>
            </li>
          </ul>
          <p v-if="req.notes" class="mt-2 text-xs italic text-slate-500">Note : {{ req.notes }}</p>

          <div v-if="statutActions[req.statut]" class="mt-4 flex flex-wrap gap-2">
            <button type="button" class="btn-primary text-sm" @click="updateStatus(req)">{{ statutActions[req.statut].label }}</button>
            <button v-if="req.statut === 'SOUMISE'" type="button" class="rounded-xl border px-4 py-2 text-sm text-red-600 dark:border-slate-600" @click="cancelRequest(req)">Annuler</button>
          </div>
        </article>
        <p v-if="!requests.length" class="py-12 text-center text-slate-400">Aucune demande patient</p>
      </div>
    </div>
  </AppLayout>
</template>
