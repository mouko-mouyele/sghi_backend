<script setup>
import { ref, computed, onMounted } from 'vue'
import PatientLayout from '../../components/PatientLayout.vue'
import { patientApi } from '../../api/patient.js'

const loading = ref(true)
const medications = ref([])
const categories = ref([])
const myRequests = ref([])
const search = ref('')
const filterCat = ref('')
const cart = ref({})
const notes = ref('')
const submitting = ref(false)
const tab = ref('catalogue')
const toast = ref({ show: false, text: '', type: 'success' })

const filteredMeds = computed(() => {
  const q = search.value.trim().toLowerCase()
  return medications.value.filter((m) => {
    if (filterCat.value && m.categorie !== filterCat.value) return false
    if (!q) return true
    return m.nom.toLowerCase().includes(q) || m.code.toLowerCase().includes(q)
  })
})

const cartItems = computed(() =>
  Object.entries(cart.value)
    .filter(([, qty]) => qty > 0)
    .map(([id, qty]) => {
      const med = medications.value.find((m) => m.id === Number(id))
      return med ? { ...med, qty } : null
    })
    .filter(Boolean),
)

const cartTotal = computed(() =>
  cartItems.value.reduce((s, i) => s + Number(i.prix_unitaire) * i.qty, 0),
)

const cartCount = computed(() => cartItems.value.reduce((s, i) => s + i.qty, 0))

function fmt(n) {
  return Number(n || 0).toLocaleString('fr-FR')
}

function fmtDate(d) {
  if (!d) return '—'
  return new Date(d).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' })
}

function showToast(text, type = 'success') {
  toast.value = { show: true, text, type }
  setTimeout(() => { toast.value.show = false }, 4000)
}

function getQty(id) {
  return cart.value[id] || 0
}

function addToCart(med) {
  if (!med.disponible) return
  const current = getQty(med.id)
  if (current >= med.stock_disponible) {
    showToast(`Stock limité : ${med.stock_disponible} disponible(s)`, 'error')
    return
  }
  cart.value = { ...cart.value, [med.id]: current + 1 }
}

function setQty(med, qty) {
  const n = Math.max(0, Math.min(Number(qty) || 0, med.stock_disponible))
  if (n === 0) {
    const next = { ...cart.value }
    delete next[med.id]
    cart.value = next
  } else {
    cart.value = { ...cart.value, [med.id]: n }
  }
}

function statutClass(s) {
  const map = {
    SOUMISE: 'bg-blue-100 text-blue-800',
    EN_PREPARATION: 'bg-amber-100 text-amber-800',
    PRETE: 'bg-emerald-100 text-emerald-800',
    RETIREE: 'bg-slate-100 text-slate-600',
    ANNULEE: 'bg-red-100 text-red-700',
  }
  return map[s] || 'bg-slate-100'
}

async function load() {
  loading.value = true
  try {
    const [meds, reqs] = await Promise.all([
      patientApi.pharmacyCatalog({}),
      patientApi.pharmacyRequests(),
    ])
    medications.value = meds.data
    myRequests.value = reqs.data
    const cats = {}
    for (const m of meds.data) {
      if (!cats[m.categorie]) cats[m.categorie] = { code: m.categorie, label: m.categorie_label, count: 0 }
      cats[m.categorie].count += 1
    }
    categories.value = Object.values(cats).sort((a, b) => a.label.localeCompare(b.label))
  } finally {
    loading.value = false
  }
}

async function submitOrder() {
  if (!cartItems.value.length) {
    showToast('Ajoutez au moins un produit', 'error')
    return
  }
  submitting.value = true
  try {
    const { data } = await patientApi.submitPharmacyRequest({
      lignes: cartItems.value.map((i) => ({ medicament_id: i.id, quantite: i.qty })),
      notes: notes.value.trim(),
    })
    myRequests.value = [data, ...myRequests.value]
    cart.value = {}
    notes.value = ''
    tab.value = 'demandes'
    showToast(`Demande ${data.reference} envoyée à la pharmacie`)
    await load()
  } catch (e) {
    showToast(e.response?.data?.detail || 'Erreur lors de l\'envoi', 'error')
  } finally {
    submitting.value = false
  }
}

onMounted(load)
</script>

<template>
  <PatientLayout>
    <header class="mb-6 flex flex-wrap items-start justify-between gap-4">
      <div>
        <h1 class="font-display text-3xl font-bold text-slate-900 dark:text-white">Pharmacie</h1>
        <p class="mt-1 text-slate-600 dark:text-slate-400">
          Parcourez le catalogue, sélectionnez vos produits et envoyez votre demande au CHU
        </p>
      </div>
      <button
        v-if="cartCount"
        type="button"
        class="relative rounded-2xl bg-primary-600 px-5 py-3 font-semibold text-white shadow-lg"
        @click="tab = 'panier'"
      >
        🛒 Panier
        <span class="absolute -right-2 -top-2 flex h-6 w-6 items-center justify-center rounded-full bg-red-500 text-xs">{{ cartCount }}</span>
      </button>
    </header>

    <div class="mb-6 flex flex-wrap gap-2 border-b border-slate-200 dark:border-slate-700">
      <button
        type="button"
        class="border-b-2 px-4 py-2 text-sm font-medium"
        :class="tab === 'catalogue' ? 'border-primary-600 text-primary-700' : 'border-transparent text-slate-500'"
        @click="tab = 'catalogue'"
      >
        📋 Catalogue
      </button>
      <button
        type="button"
        class="border-b-2 px-4 py-2 text-sm font-medium"
        :class="tab === 'panier' ? 'border-primary-600 text-primary-700' : 'border-transparent text-slate-500'"
        @click="tab = 'panier'"
      >
        🛒 Mon panier <span v-if="cartCount" class="text-primary-600">({{ cartCount }})</span>
      </button>
      <button
        type="button"
        class="border-b-2 px-4 py-2 text-sm font-medium"
        :class="tab === 'demandes' ? 'border-primary-600 text-primary-700' : 'border-transparent text-slate-500'"
        @click="tab = 'demandes'"
      >
        📦 Mes demandes
      </button>
    </div>

    <div
      v-if="toast.show"
      class="fixed bottom-6 right-6 z-50 rounded-xl px-4 py-3 text-sm text-white shadow-lg"
      :class="toast.type === 'error' ? 'bg-red-600' : 'bg-emerald-600'"
    >
      {{ toast.text }}
    </div>

    <div v-if="loading" class="py-16 text-center text-slate-400">Chargement…</div>

    <!-- CATALOGUE -->
    <div v-else-if="tab === 'catalogue'">
      <div class="mb-6 flex flex-wrap gap-3">
        <input v-model="search" type="search" class="input-field min-w-[200px] flex-1" placeholder="Rechercher…" />
        <select v-model="filterCat" class="input-field w-auto">
          <option value="">Toutes catégories</option>
          <option v-for="c in categories" :key="c.code" :value="c.code">{{ c.label }}</option>
        </select>
      </div>

      <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <article
          v-for="m in filteredMeds"
          :key="m.id"
          class="flex flex-col rounded-2xl border bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-800/80"
        >
          <div class="mb-2 flex justify-between">
            <span class="font-mono text-xs text-slate-500">{{ m.code }}</span>
            <span
              class="rounded-full px-2 py-0.5 text-xs"
              :class="m.disponible ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-600'"
            >
              {{ m.disponible ? 'Disponible' : 'Rupture' }}
            </span>
          </div>
          <h3 class="font-semibold text-slate-900 dark:text-white">{{ m.nom }}</h3>
          <p class="text-xs text-slate-500">{{ m.forme }} · {{ m.categorie_label }}</p>
          <p v-if="m.description" class="mt-2 line-clamp-2 text-xs text-slate-500">{{ m.description }}</p>
          <p class="mt-3 text-xl font-bold text-primary-700 dark:text-primary-300">{{ fmt(m.prix_unitaire) }} <span class="text-xs font-normal">FCFA</span></p>

          <div class="mt-auto flex items-center gap-2 pt-4">
            <template v-if="getQty(m.id)">
              <button type="button" class="rounded-lg border px-3 py-1 dark:border-slate-600" @click="setQty(m, getQty(m.id) - 1)">−</button>
              <span class="w-8 text-center font-semibold">{{ getQty(m.id) }}</span>
              <button type="button" class="rounded-lg border px-3 py-1 dark:border-slate-600" @click="addToCart(m)">+</button>
            </template>
            <button
              v-else
              type="button"
              class="btn-primary w-full text-sm"
              :disabled="!m.disponible"
              @click="addToCart(m)"
            >
              {{ m.disponible ? 'Ajouter' : 'Indisponible' }}
            </button>
          </div>
        </article>
      </div>
    </div>

    <!-- PANIER -->
    <div v-else-if="tab === 'panier'">
      <div v-if="!cartItems.length" class="rounded-2xl bg-slate-50 py-16 text-center dark:bg-slate-800/60">
        <p class="text-4xl">🛒</p>
        <p class="mt-2 text-slate-500">Votre panier est vide</p>
        <button type="button" class="btn-primary mt-4" @click="tab = 'catalogue'">Parcourir le catalogue</button>
      </div>

      <div v-else class="grid gap-6 lg:grid-cols-3">
        <div class="space-y-3 lg:col-span-2">
          <div v-for="item in cartItems" :key="item.id" class="flex items-center justify-between rounded-2xl border bg-white p-4 dark:border-slate-700 dark:bg-slate-800">
            <div>
              <p class="font-semibold">{{ item.nom }}</p>
              <p class="text-xs text-slate-500">{{ item.forme }} · {{ fmt(item.prix_unitaire) }} FCFA / unité</p>
            </div>
            <div class="flex items-center gap-3">
              <button type="button" class="rounded-lg border px-2 py-1" @click="setQty(item, item.qty - 1)">−</button>
              <span class="font-semibold">{{ item.qty }}</span>
              <button type="button" class="rounded-lg border px-2 py-1" @click="setQty(item, item.qty + 1)">+</button>
              <span class="w-24 text-right font-bold">{{ fmt(item.prix_unitaire * item.qty) }}</span>
            </div>
          </div>
        </div>

        <div class="rounded-2xl border bg-gradient-to-br from-emerald-50 to-teal-50 p-5 dark:border-slate-700 dark:from-emerald-950/30 dark:to-teal-950/20">
          <h3 class="font-semibold">Récapitulatif</h3>
          <p class="mt-4 text-3xl font-bold text-emerald-800 dark:text-emerald-200">{{ fmt(cartTotal) }} <span class="text-sm font-normal">FCFA</span></p>
          <p class="mt-1 text-xs text-slate-500">{{ cartItems.length }} produit(s) · {{ cartCount }} unité(s)</p>

          <label class="mt-4 block text-xs font-medium text-slate-600">Note pour le pharmacien (optionnel)</label>
          <textarea v-model="notes" rows="2" class="input-field mt-1 text-sm" placeholder="Ex. ordonnance jointe au retrait…" />

          <button type="button" class="btn-primary mt-4 w-full" :disabled="submitting" @click="submitOrder">
            {{ submitting ? 'Envoi…' : 'Envoyer ma demande' }}
          </button>
          <p class="mt-3 text-xs text-slate-500">Retrait à la pharmacie du CHU après préparation. Paiement à la caisse.</p>
        </div>
      </div>
    </div>

    <!-- MES DEMANDES -->
    <div v-else-if="tab === 'demandes'">
      <div v-for="req in myRequests" :key="req.id" class="mb-4 rounded-2xl border bg-white p-5 dark:border-slate-700 dark:bg-slate-800">
        <div class="flex flex-wrap justify-between gap-2">
          <div>
            <p class="font-mono text-sm text-primary-600">{{ req.reference }}</p>
            <p class="text-xs text-slate-500">{{ fmtDate(req.created_at) }}</p>
          </div>
          <span class="rounded-full px-3 py-1 text-xs font-medium" :class="statutClass(req.statut)">{{ req.statut_label }}</span>
        </div>
        <ul class="mt-3 space-y-1 text-sm">
          <li v-for="l in req.lignes" :key="l.id" class="flex justify-between">
            <span>{{ l.medicament_nom }} × {{ l.quantite }}</span>
            <span>{{ fmt(l.sous_total) }} FCFA</span>
          </li>
        </ul>
        <p class="mt-2 text-right font-bold">{{ fmt(req.montant_total) }} FCFA</p>
        <p v-if="req.statut === 'PRETE'" class="mt-2 rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-800 dark:bg-emerald-950/40">
          ✅ Votre commande est prête — présentez-vous à la pharmacie avec cette référence.
        </p>
      </div>
      <p v-if="!myRequests.length" class="py-12 text-center text-slate-400">Aucune demande pour le moment</p>
    </div>
  </PatientLayout>
</template>
