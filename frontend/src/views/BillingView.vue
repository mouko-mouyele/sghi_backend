<script setup>
import { ref, onMounted, computed } from 'vue'
import AppLayout from '../components/AppLayout.vue'
import PaginationBar from '../components/PaginationBar.vue'
import MobileMoneyCheckout from '../components/MobileMoneyCheckout.vue'
import { billing, dashboard, patients } from '../api/client'
import { parseApiError } from '../utils/errors.js'
import { usePagination } from '../composables/usePagination.js'

const invoices = ref([])
const journal = ref([])
const patientList = ref([])
const patientsLoading = ref(false)
const patientSearch = ref('')
const loading = ref(true)
const tab = ref('factures')
const filterStatut = ref('')
const search = ref('')
const message = ref('')
const errorMsg = ref('')
const selected = ref(null)
const showCreate = ref(false)
const showPay = ref(false)
const showMobile = ref(false)
const showEdit = ref(false)
const editLines = ref([])
const montantForm = ref({ montant_patient: '', motif: '' })
const resetPayments = ref(false)
const newLineForm = ref({ type_ligne: 'ACTE', libelle: '', quantite: 1, prix_unitaire: '' })
const pagination = usePagination(15)
const journalPagination = usePagination(20)

const createForm = ref({ patient_id: '', hospitalisation_id: '' })
const payForm = ref({ montant: '', mode: 'ESPECES', reference: '' })
const roleStats = ref(null)

const statuts = [
  { value: '', label: 'Toutes' },
  { value: 'BROUILLON', label: 'Brouillon' },
  { value: 'EMISE', label: 'Impayées' },
  { value: 'PARTIEL', label: 'Partielles' },
  { value: 'PAYEE', label: 'Payées' },
]

const stats = computed(() => ({
  impayees: invoices.value.filter((i) => i.est_impayee).length,
  payees: invoices.value.filter((i) => i.est_payee).length,
  totalDu: invoices.value.reduce((s, i) => s + Number(i.montant_restant || 0), 0),
}))

const canEdit = computed(() => selected.value && selected.value.statut !== 'ANNULEE')

const editHint = computed(() => {
  if (!selected.value) return ''
  if (Number(selected.value.montant_paye) > 0) {
    return `Encaissement enregistré : ${fmt(selected.value.montant_paye)} FCFA. Pour baisser le montant en dessous, cochez « Réinitialiser les encaissements » ou cliquez « Marquer impayée ».`
  }
  if (selected.value.statut === 'PAYEE') {
    return 'Facture soldée : vous pouvez augmenter le montant (ex. supplément) ou réinitialiser les encaissements pour corriger.'
  }
  return 'Modifiez les lignes ou ajustez directement le montant patient.'
})

function fmt(n) {
  return Number(n || 0).toLocaleString('fr-FR')
}

function statutBadge(i) {
  const map = {
    PAYEE: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300',
    EMISE: 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300',
    PARTIEL: 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300',
    BROUILLON: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400',
    ANNULEE: 'bg-slate-200 text-slate-500',
  }
  return map[i.statut] || map.BROUILLON
}

async function loadInvoices() {
  loading.value = true
  try {
    const { data } = await billing.invoices(pagination.params({
      statut: filterStatut.value || undefined,
      search: search.value || undefined,
    }))
    invoices.value = data.items
    pagination.applyMeta(data)
  } finally {
    loading.value = false
  }
}

async function loadJournal() {
  const { data } = await billing.journal(journalPagination.params())
  journal.value = data.items
  journalPagination.applyMeta(data)
}

async function loadPatients(search = patientSearch.value) {
  patientsLoading.value = true
  try {
    const { data } = await patients.list({
      page: 1,
      page_size: 100,
      search: search?.trim() || undefined,
    })
    patientList.value = data.items
  } catch (e) {
    patientList.value = []
    errorMsg.value = parseApiError(e, 'Impossible de charger la liste des patients')
  } finally {
    patientsLoading.value = false
  }
}

function toggleCreateForm() {
  showCreate.value = !showCreate.value
  if (showCreate.value) {
    createForm.value = { patient_id: '', hospitalisation_id: '' }
    patientSearch.value = ''
    loadPatients()
  }
}

async function openDetail(id) {
  const { data } = await billing.get(id)
  selected.value = data
  showEdit.value = false
}

function startEdit() {
  if (!selected.value) return
  editLines.value = selected.value.lignes.map((l) => ({
    id: l.id,
    libelle: l.libelle,
    quantite: l.quantite,
    prix_unitaire: l.prix_unitaire,
    montant: l.montant,
  }))
  montantForm.value = {
    montant_patient: String(selected.value.montant_patient),
    motif: '',
  }
  resetPayments.value = false
  showEdit.value = true
}

async function saveLine(line) {
  errorMsg.value = ''
  if (!Number.isFinite(Number(line.prix_unitaire)) || Number(line.prix_unitaire) < 0) {
    errorMsg.value = 'Prix unitaire invalide'
    return
  }
  try {
    const { data } = await billing.updateLine(selected.value.id, line.id, {
      libelle: line.libelle,
      quantite: Number(line.quantite),
      prix_unitaire: Number(line.prix_unitaire),
      reinitialiser_paiements: resetPayments.value,
    })
    selected.value = data
    editLines.value = data.lignes.map((l) => ({
      id: l.id, libelle: l.libelle, quantite: l.quantite,
      prix_unitaire: l.prix_unitaire, montant: l.montant,
    }))
    message.value = 'Ligne mise à jour'
    loadInvoices()
  } catch (e) {
    errorMsg.value = parseApiError(e)
  }
}

async function removeLine(line) {
  if (!confirm('Supprimer cette ligne ?')) return
  try {
    const { data } = await billing.deleteLine(selected.value.id, line.id, resetPayments.value)
    selected.value = data
    editLines.value = data.lignes.map((l) => ({
      id: l.id, libelle: l.libelle, quantite: l.quantite,
      prix_unitaire: l.prix_unitaire, montant: l.montant,
    }))
    message.value = 'Ligne supprimée'
    loadInvoices()
  } catch (e) {
    errorMsg.value = parseApiError(e)
  }
}

async function saveMontantPatient() {
  errorMsg.value = ''
  const montant = Number(montantForm.value.montant_patient)
  if (!Number.isFinite(montant) || montant < 0) {
    errorMsg.value = 'Saisissez un montant valide (nombre positif)'
    return
  }
  try {
    const { data } = await billing.updateMontant(selected.value.id, {
      montant_patient: montant,
      motif: montantForm.value.motif,
      reinitialiser_paiements: resetPayments.value,
    })
    selected.value = data
    message.value = 'Montant patient ajusté'
    loadInvoices()
  } catch (e) {
    errorMsg.value = parseApiError(e)
  }
}

async function addLine() {
  errorMsg.value = ''
  try {
    const { data } = await billing.addLine(selected.value.id, {
      type_ligne: newLineForm.value.type_ligne,
      libelle: newLineForm.value.libelle,
      quantite: Number(newLineForm.value.quantite),
      prix_unitaire: Number(newLineForm.value.prix_unitaire),
      reinitialiser_paiements: resetPayments.value,
    })
    selected.value = data
    editLines.value = data.lignes.map((l) => ({
      id: l.id, libelle: l.libelle, quantite: l.quantite,
      prix_unitaire: l.prix_unitaire, montant: l.montant,
    }))
    newLineForm.value = { type_ligne: 'ACTE', libelle: '', quantite: 1, prix_unitaire: '' }
    message.value = 'Ligne ajoutée'
    loadInvoices()
  } catch (e) {
    errorMsg.value = parseApiError(e)
  }
}

async function createInvoice() {
  errorMsg.value = ''
  if (!createForm.value.patient_id) {
    errorMsg.value = 'Veuillez sélectionner un patient à facturer'
    return
  }
  try {
    await billing.createInvoice({
      patient_id: Number(createForm.value.patient_id),
      hospitalisation_id: createForm.value.hospitalisation_id ? Number(createForm.value.hospitalisation_id) : null,
    })
    message.value = 'Facture créée (brouillon)'
    showCreate.value = false
    loadInvoices()
  } catch (e) {
    errorMsg.value = parseApiError(e)
  }
}

async function emitInvoice(i) {
  try {
    await billing.emit(i.id)
    message.value = `Facture ${i.numero} émise — impayée`
    loadInvoices()
    if (selected.value?.id === i.id) openDetail(i.id)
  } catch (e) {
    errorMsg.value = parseApiError(e)
  }
}

async function submitPay() {
  try {
    await billing.pay(selected.value.id, {
      montant: Number(payForm.value.montant),
      mode: payForm.value.mode,
      reference: payForm.value.reference,
    })
    message.value = 'Paiement enregistré'
    showPay.value = false
    loadInvoices()
    openDetail(selected.value.id)
  } catch (e) {
    errorMsg.value = parseApiError(e)
  }
}

async function markUnpaid(i) {
  if (!confirm(`Marquer ${i.numero} comme impayée ?`)) return
  try {
    await billing.markUnpaid(i.id)
    message.value = 'Facture marquée impayée'
    loadInvoices()
    if (selected.value?.id === i.id) openDetail(i.id)
  } catch (e) {
    errorMsg.value = parseApiError(e)
  }
}

async function markPaid(i) {
  try {
    await billing.markPaid(i.id)
    message.value = 'Facture marquée payée'
    loadInvoices()
    if (selected.value?.id === i.id) openDetail(i.id)
  } catch (e) {
    errorMsg.value = parseApiError(e)
  }
}

function onFilter() {
  pagination.resetPage()
  loadInvoices()
}

function onMobileSuccess() {
  showMobile.value = false
  message.value = 'Paiement Mobile Money confirmé'
  loadInvoices()
  if (selected.value) openDetail(selected.value.id)
}

function openPayModal(i) {
  selected.value = i
  payForm.value = { montant: String(i.montant_restant), mode: 'ESPECES', reference: '' }
  showPay.value = true
}

onMounted(async () => {
  try {
    const { data } = await dashboard.moi()
    roleStats.value = data
  } catch { /* ignore */ }
  await Promise.all([loadInvoices(), loadPatients(), loadJournal()])
})
</script>

<template>
  <AppLayout>
    <header class="relative mb-8 overflow-hidden rounded-3xl bg-gradient-to-br from-violet-900 via-primary-900 to-indigo-950 p-8 text-white">
      <div class="relative flex flex-wrap items-start justify-between gap-4">
        <div>
          <p class="text-sm text-violet-200">Finances · CHU Brazzaville</p>
          <h1 class="font-display text-3xl font-bold">Facturation</h1>
          <p class="mt-2 text-violet-100">Tiers-payant · Mobile Money · Statuts payé / impayé</p>
        </div>
        <button class="rounded-xl bg-white/15 px-4 py-2 text-sm font-semibold backdrop-blur hover:bg-white/25" @click="toggleCreateForm">
          + Nouvelle facture
        </button>
      </div>
      <div class="relative mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div class="rounded-2xl bg-white/10 px-4 py-3 backdrop-blur">
          <p class="text-2xl font-bold text-red-300">{{ roleStats?.factures_impayees ?? stats.impayees }}</p>
          <p class="text-xs text-violet-200">Factures impayées</p>
        </div>
        <div class="rounded-2xl bg-white/10 px-4 py-3 backdrop-blur">
          <p class="text-2xl font-bold">{{ fmt(roleStats?.montant_impaye_total ?? stats.totalDu) }}</p>
          <p class="text-xs text-violet-200">FCFA restants à encaisser</p>
        </div>
        <div class="rounded-2xl bg-white/10 px-4 py-3 backdrop-blur">
          <p class="text-2xl font-bold text-emerald-300">{{ fmt(roleStats?.recettes_mois ?? 0) }}</p>
          <p class="text-xs text-violet-200">Recettes du mois</p>
        </div>
        <div class="rounded-2xl bg-white/10 px-4 py-3 backdrop-blur">
          <p class="text-2xl font-bold">{{ roleStats?.paiements_jour ?? 0 }}</p>
          <p class="text-xs text-violet-200">Paiements aujourd'hui</p>
        </div>
      </div>
    </header>

    <div v-if="message" class="mb-4 rounded-xl bg-emerald-50 px-4 py-3 text-sm text-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-200">{{ message }}</div>
    <div v-if="errorMsg" class="mb-4 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-950/40">{{ errorMsg }}</div>

    <div v-if="showCreate" class="card mb-6">
      <h2 class="mb-4 font-semibold">Nouvelle facture</h2>
      <div class="grid gap-4 sm:grid-cols-2">
        <div class="sm:col-span-2">
          <label class="mb-1 block text-xs font-medium text-slate-500 dark:text-slate-400">Rechercher un patient</label>
          <div class="flex gap-2">
            <input
              v-model="patientSearch"
              type="search"
              class="input-field flex-1"
              placeholder="Nom, prénom ou n° dossier…"
              @keyup.enter="loadPatients()"
            />
            <button type="button" class="rounded-xl border px-4 py-2 text-sm dark:border-slate-600" @click="loadPatients()">
              Rechercher
            </button>
          </div>
        </div>
        <div>
          <label class="mb-1 block text-xs font-medium text-slate-500 dark:text-slate-400">Patient à facturer *</label>
          <select v-model="createForm.patient_id" class="input-field" :disabled="patientsLoading">
            <option value="">{{ patientsLoading ? 'Chargement…' : 'Choisir un patient…' }}</option>
            <option v-for="p in patientList" :key="p.id" :value="p.id">
              {{ p.prenom }} {{ p.nom }} — {{ p.numero_dossier }}
            </option>
          </select>
          <p v-if="!patientsLoading && !patientList.length" class="mt-2 text-xs text-amber-700 dark:text-amber-300">
            Aucun patient trouvé. Lancez une recherche ou contactez l'administrateur.
          </p>
        </div>
        <div>
          <label class="mb-1 block text-xs font-medium text-slate-500 dark:text-slate-400">Hospitalisation (optionnel)</label>
          <input v-model="createForm.hospitalisation_id" class="input-field" placeholder="ID hospitalisation" />
        </div>
      </div>
      <button class="btn-primary mt-4" @click="createInvoice">Créer le brouillon</button>
    </div>

    <div class="mb-4 flex gap-2">
      <button
        class="rounded-xl px-4 py-2 text-sm font-medium"
        :class="tab === 'factures' ? 'bg-primary-600 text-white' : 'bg-white ring-1 ring-slate-200 dark:bg-slate-800 dark:ring-slate-600'"
        @click="tab = 'factures'"
      >Factures</button>
      <button
        class="rounded-xl px-4 py-2 text-sm font-medium"
        :class="tab === 'journal' ? 'bg-primary-600 text-white' : 'bg-white ring-1 ring-slate-200 dark:bg-slate-800 dark:ring-slate-600'"
        @click="tab = 'journal'; loadJournal()"
      >Journal comptable</button>
    </div>

    <div v-if="tab === 'factures'" class="grid gap-6 xl:grid-cols-[1fr_360px]">
      <div class="card overflow-hidden p-0">
        <div class="flex flex-wrap gap-2 border-b p-4 dark:border-slate-700">
          <input v-model="search" class="input-field max-w-xs flex-1" placeholder="Rechercher…" @keyup.enter="onFilter" />
          <select v-model="filterStatut" class="input-field w-40" @change="onFilter">
            <option v-for="s in statuts" :key="s.value" :value="s.value">{{ s.label }}</option>
          </select>
          <button class="rounded-xl border px-3 py-2 text-sm dark:border-slate-600" @click="onFilter">Filtrer</button>
        </div>
        <table class="w-full text-sm">
          <thead class="table-head">
            <tr>
              <th class="px-4 py-3 text-left">N° / Patient</th>
              <th class="px-4 py-3 text-left">Total</th>
              <th class="px-4 py-3 text-left">Reste</th>
              <th class="px-4 py-3 text-left">Statut</th>
              <th class="px-4 py-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading"><td colspan="5" class="px-4 py-10 text-center text-slate-400">Chargement…</td></tr>
            <tr
              v-for="i in invoices"
              :key="i.id"
              class="table-row cursor-pointer"
              :class="selected?.id === i.id ? 'bg-primary-50 dark:bg-primary-950/30' : ''"
              @click="openDetail(i.id)"
            >
              <td class="px-4 py-3">
                <p class="font-mono text-xs text-primary-600 dark:text-primary-400">{{ i.numero }}</p>
                <p class="font-medium">{{ i.patient_nom || `#${i.patient_id}` }}</p>
              </td>
              <td class="px-4 py-3">{{ fmt(i.montant_total) }}</td>
              <td class="px-4 py-3 font-semibold" :class="i.est_impayee ? 'text-red-600 dark:text-red-400' : 'text-emerald-600'">
                {{ fmt(i.montant_restant) }}
              </td>
              <td class="px-4 py-3">
                <span class="rounded-full px-2 py-0.5 text-xs font-semibold" :class="statutBadge(i)">
                  {{ i.est_payee ? 'Payée' : i.statut_libelle || i.statut }}
                </span>
              </td>
              <td class="px-4 py-3 text-right" @click.stop>
                <button v-if="i.statut === 'BROUILLON'" class="text-xs text-primary-600 hover:underline" @click="emitInvoice(i)">Émettre</button>
              </td>
            </tr>
          </tbody>
        </table>
        <PaginationBar
          :page="pagination.page.value"
          :page-size="pagination.pageSize.value"
          :total="pagination.total.value"
          :total-pages="pagination.totalPages.value"
          @update:page="(p) => { pagination.page.value = p; loadInvoices() }"
          @update:page-size="(s) => { pagination.pageSize.value = s; pagination.page.value = 1; loadInvoices() }"
        />
      </div>

      <aside class="space-y-4">
        <div v-if="selected" class="card">
          <h3 class="font-display font-bold">{{ selected.numero }}</h3>
          <p class="text-sm text-slate-500">{{ selected.patient_nom }}</p>
          <span class="mt-2 inline-block rounded-full px-2 py-0.5 text-xs font-semibold" :class="statutBadge(selected)">
            {{ selected.est_payee ? '✓ Payée' : '○ Impayée' }}
          </span>

          <ul v-if="!showEdit" class="mt-4 space-y-2 border-t pt-4 text-sm dark:border-slate-700">
            <li v-for="l in selected.lignes" :key="l.id" class="flex justify-between">
              <span>{{ l.libelle }}</span>
              <span>{{ fmt(l.montant) }}</span>
            </li>
          </ul>

          <!-- Édition des montants -->
          <div v-else class="mt-4 space-y-3 border-t pt-4 dark:border-slate-700">
            <p class="text-xs font-semibold uppercase tracking-wide text-violet-600 dark:text-violet-400">Modifier les lignes</p>
            <p class="rounded-lg bg-blue-50 px-3 py-2 text-xs text-blue-800 dark:bg-blue-950/40 dark:text-blue-200">{{ editHint }}</p>
            <p v-if="errorMsg" class="rounded-lg bg-red-50 px-3 py-2 text-xs text-red-700 dark:bg-red-950/40 dark:text-red-300">{{ errorMsg }}</p>
            <label v-if="selected.montant_paye > 0" class="flex cursor-pointer items-start gap-2 rounded-lg border border-amber-200 bg-amber-50/80 px-3 py-2 text-xs dark:border-amber-900 dark:bg-amber-950/30">
              <input v-model="resetPayments" type="checkbox" class="mt-0.5" />
              <span><strong>Réinitialiser les encaissements</strong> (efface les {{ fmt(selected.montant_paye) }} FCFA déjà payés pour permettre la baisse du montant)</span>
            </label>
            <div
              v-for="line in editLines"
              :key="line.id"
              class="rounded-xl border border-violet-100 bg-violet-50/50 p-3 dark:border-violet-900/50 dark:bg-violet-950/20"
            >
              <input v-model="line.libelle" class="input-field mb-2 text-sm" placeholder="Libellé" />
              <div class="grid grid-cols-2 gap-2">
                <div>
                  <label class="text-xs text-slate-500">Qté</label>
                  <input v-model.number="line.quantite" type="number" min="1" class="input-field text-sm" />
                </div>
                <div>
                  <label class="text-xs text-slate-500">Prix unit. (FCFA)</label>
                  <input v-model.number="line.prix_unitaire" type="number" min="0" class="input-field text-sm" />
                </div>
              </div>
              <p class="mt-1 text-right text-xs font-medium text-slate-600 dark:text-slate-400">
                = {{ fmt(Number(line.quantite) * Number(line.prix_unitaire)) }} FCFA
              </p>
              <div class="mt-2 flex gap-2">
                <button type="button" class="flex-1 rounded-lg bg-primary-600 px-2 py-1 text-xs text-white" @click="saveLine(line)">Enregistrer</button>
                <button type="button" class="rounded-lg border px-2 py-1 text-xs text-red-600 dark:border-slate-600" @click="removeLine(line)">Suppr.</button>
              </div>
            </div>

            <div class="rounded-xl border border-dashed border-slate-300 p-3 dark:border-slate-600">
              <p class="mb-2 text-xs font-semibold text-slate-500">+ Nouvelle ligne</p>
              <input v-model="newLineForm.libelle" class="input-field mb-2 text-sm" placeholder="Libellé" />
              <div class="grid grid-cols-2 gap-2">
                <input v-model.number="newLineForm.quantite" type="number" min="1" class="input-field text-sm" placeholder="Qté" />
                <input v-model.number="newLineForm.prix_unitaire" type="number" min="0" class="input-field text-sm" placeholder="Prix FCFA" />
              </div>
              <button type="button" class="mt-2 w-full rounded-lg border border-primary-300 py-1.5 text-xs font-medium text-primary-700 dark:border-primary-700 dark:text-primary-300" @click="addLine">
                Ajouter la ligne
              </button>
            </div>

            <div class="rounded-xl border border-amber-200 bg-amber-50/60 p-3 dark:border-amber-900/50 dark:bg-amber-950/20">
              <p class="mb-2 text-xs font-semibold text-amber-800 dark:text-amber-200">Ajuster le montant patient</p>
              <input v-model="montantForm.montant_patient" type="number" min="0" class="input-field mb-2 text-sm" />
              <input v-model="montantForm.motif" class="input-field mb-2 text-sm" placeholder="Motif (remise, correction…)" />
              <p v-if="selected.montant_paye > 0" class="mb-2 text-xs text-amber-700 dark:text-amber-300">
                Minimum autorisé sans réinitialisation : {{ fmt(selected.montant_paye) }} FCFA
              </p>
              <button type="button" class="w-full rounded-lg bg-amber-600 py-1.5 text-xs font-semibold text-white" @click="saveMontantPatient">
                Appliquer le montant
              </button>
            </div>

            <button type="button" class="w-full text-xs text-slate-500 hover:underline" @click="showEdit = false">← Terminer l'édition</button>
          </div>

          <div class="mt-4 grid grid-cols-2 gap-2 text-sm">
            <div class="rounded-xl bg-slate-50 p-3 dark:bg-slate-900/50">
              <p class="text-xs text-slate-500">Patient</p>
              <p class="font-bold">{{ fmt(selected.montant_patient) }}</p>
            </div>
            <div class="rounded-xl bg-emerald-50 p-3 dark:bg-emerald-950/30">
              <p class="text-xs text-slate-500">Payé</p>
              <p class="font-bold text-emerald-700">{{ fmt(selected.montant_paye) }}</p>
            </div>
          </div>

          <div class="mt-4 flex flex-wrap gap-2">
            <button
              v-if="canEdit && !showEdit"
              type="button"
              class="rounded-xl bg-violet-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-violet-700"
              @click="startEdit"
            >
              ✏️ Modifier montants
            </button>
            <button v-if="selected.est_impayee && selected.statut !== 'BROUILLON'" class="rounded-xl bg-amber-500 px-3 py-1.5 text-xs font-semibold text-white" @click="showMobile = true; showPay = false">📱 Mobile Money</button>
            <button v-if="selected.est_impayee && selected.statut !== 'BROUILLON'" class="rounded-xl border px-3 py-1.5 text-xs dark:border-slate-600" @click="openPayModal(selected)">Encaisser</button>
            <button v-if="!selected.est_payee && selected.statut !== 'BROUILLON'" class="rounded-xl bg-emerald-600 px-3 py-1.5 text-xs text-white" @click="markPaid(selected)">Marquer payée</button>
            <button v-if="selected.montant_paye > 0 || selected.est_payee" class="rounded-xl bg-red-100 px-3 py-1.5 text-xs text-red-700 dark:bg-red-950/40" @click="markUnpaid(selected)">Marquer impayée</button>
          </div>

          <div v-if="selected.paiements?.length" class="mt-4 border-t pt-4 dark:border-slate-700">
            <p class="mb-2 text-xs font-semibold text-slate-500">Historique paiements</p>
            <div v-for="p in selected.paiements" :key="p.id" class="mb-2 rounded-lg bg-slate-50 px-3 py-2 text-xs dark:bg-slate-900/50">
              {{ fmt(p.montant) }} · {{ p.mode }} {{ p.operateur ? `(${p.operateur})` : '' }}
            </div>
          </div>
        </div>
        <p v-else class="card text-center text-sm text-slate-400">Sélectionnez une facture</p>

        <MobileMoneyCheckout
          v-if="showMobile && selected"
          :invoice="selected"
          :api-init="billing.initMobileMoney"
          :api-confirm="billing.confirmMobileMoney"
          :api-approve="billing.approveMobileMoney"
          :api-status="billing.mobileMoneyStatus"
          @success="onMobileSuccess"
          @close="showMobile = false"
        />

        <div v-if="showPay && selected" class="card">
          <h4 class="mb-3 font-semibold">Encaissement manuel</h4>
          <input v-model="payForm.montant" type="number" class="input-field mb-2" />
          <select v-model="payForm.mode" class="input-field mb-2">
            <option value="ESPECES">Espèces</option>
            <option value="CARTE">Carte bancaire</option>
            <option value="VIREMENT">Virement</option>
            <option value="CHEQUE">Chèque</option>
          </select>
          <input v-model="payForm.reference" class="input-field mb-3" placeholder="Référence" />
          <button class="btn-primary w-full" @click="submitPay">Enregistrer</button>
        </div>
      </aside>
    </div>

    <div v-else class="card overflow-hidden p-0">
      <table class="w-full text-sm">
        <thead class="table-head">
          <tr>
            <th class="px-4 py-3 text-left">Réf.</th>
            <th class="px-4 py-3 text-left">Opération</th>
            <th class="px-4 py-3 text-right">Débit</th>
            <th class="px-4 py-3 text-right">Crédit</th>
            <th class="px-4 py-3 text-left">Libellé</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="j in journal" :key="j.reference" class="table-row">
            <td class="px-4 py-3 font-mono text-xs">{{ j.reference }}</td>
            <td class="px-4 py-3">{{ j.type_operation }}</td>
            <td class="px-4 py-3 text-right">{{ fmt(j.debit) }}</td>
            <td class="px-4 py-3 text-right text-emerald-600">{{ fmt(j.credit) }}</td>
            <td class="px-4 py-3 text-slate-500">{{ j.libelle }}</td>
          </tr>
        </tbody>
      </table>
      <PaginationBar
        :page="journalPagination.page.value"
        :page-size="journalPagination.pageSize.value"
        :total="journalPagination.total.value"
        :total-pages="journalPagination.totalPages.value"
        @update:page="(p) => { journalPagination.page.value = p; loadJournal() }"
        @update:page-size="(s) => { journalPagination.pageSize.value = s; journalPagination.page.value = 1; loadJournal() }"
      />
    </div>
  </AppLayout>
</template>
