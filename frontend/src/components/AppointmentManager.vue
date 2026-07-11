<script setup>
import { ref, onMounted, computed } from 'vue'
import { adminApi } from '../api/admin.js'
import { patients } from '../api/client.js'
import { parseApiError } from '../utils/errors.js'
import PaginationBar from './PaginationBar.vue'
import { usePagination } from '../composables/usePagination.js'

const rdvList = ref([])
const medecins = ref([])
const patientList = ref([])
const loading = ref(true)
const showForm = ref(false)
const showEdit = ref(false)
const filterStatut = ref('')
const filterDate = ref('')
const form = ref({ patient_id: '', medecin_id: '', date_heure: '', motif: '', duree_minutes: 30 })
const editForm = ref({
  id: null, patient_id: '', medecin_id: '', date_heure: '', motif: '',
  statut: '', duree_minutes: 30, raison_modification: '',
})
const message = ref('')
const errorMsg = ref('')
const pendingTotal = ref(0)
const pagination = usePagination(10)

const statuts = [
  { value: 'PLANIFIE', label: 'En attente' },
  { value: 'CONFIRME', label: 'Confirmé' },
  { value: 'TERMINE', label: 'Terminé' },
  { value: 'ANNULE', label: 'Annulé' },
]

const pendingCount = computed(() => (
  filterStatut.value === 'PLANIFIE' ? pagination.total.value : pendingTotal.value
))

function toLocalDatetime(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

async function load() {
  loading.value = true
  errorMsg.value = ''
  try {
    const [rdv, med, pat, pending] = await Promise.all([
      adminApi.appointments(pagination.params({
        statut: filterStatut.value || undefined,
        date: filterDate.value || undefined,
      })),
      adminApi.medecins({ page: 1, page_size: 100 }),
      patients.list({ page: 1, page_size: 100 }),
      filterStatut.value !== 'PLANIFIE'
        ? adminApi.appointments({ statut: 'PLANIFIE', page: 1, page_size: 1 })
        : Promise.resolve(null),
    ])
    rdvList.value = rdv.data.items
    pagination.applyMeta(rdv.data)
    medecins.value = med.data.items
    patientList.value = pat.data.items
    if (pending) pendingTotal.value = pending.data.total
  } finally {
    loading.value = false
  }
}

function onFilterChange() {
  pagination.resetPage()
  load()
}

function onPageChange(p) {
  pagination.page.value = p
  load()
}

function onPageSizeChange(size) {
  pagination.pageSize.value = size
  pagination.page.value = 1
  load()
}

async function createRdv() {
  try {
    await adminApi.createAppointment({
      patient_id: Number(form.value.patient_id),
      medecin_id: Number(form.value.medecin_id),
      date_heure: form.value.date_heure.length === 16 ? `${form.value.date_heure}:00` : form.value.date_heure,
      motif: form.value.motif,
      duree_minutes: Number(form.value.duree_minutes),
    })
    message.value = 'Rendez-vous créé — emails envoyés au patient et au médecin'
    showForm.value = false
    load()
  } catch (e) {
    errorMsg.value = parseApiError(e, 'Erreur lors de la création')
  }
}

function openEdit(r) {
  editForm.value = {
    id: r.id,
    patient_id: r.patient_id,
    medecin_id: r.medecin_id,
    date_heure: toLocalDatetime(r.date_heure),
    motif: r.motif,
    statut: r.statut,
    duree_minutes: r.duree_minutes,
    raison_modification: '',
  }
  showEdit.value = true
}

async function saveEdit() {
  try {
    await adminApi.editAppointment(editForm.value.id, {
      patient_id: Number(editForm.value.patient_id),
      medecin_id: Number(editForm.value.medecin_id),
      date_heure: editForm.value.date_heure.length === 16 ? `${editForm.value.date_heure}:00` : editForm.value.date_heure,
      motif: editForm.value.motif,
      statut: editForm.value.statut,
      duree_minutes: Number(editForm.value.duree_minutes),
      raison_modification: editForm.value.raison_modification || undefined,
    })
    message.value = 'Rendez-vous modifié — patient et médecin notifiés par email'
    showEdit.value = false
    load()
  } catch (e) {
    errorMsg.value = parseApiError(e, 'Erreur lors de la modification')
  }
}

async function deleteRdv(id, patientNom) {
  if (!confirm(`Supprimer le RDV de ${patientNom} ? Un email d'annulation sera envoyé.`)) return
  try {
    await adminApi.deleteAppointment(id)
    message.value = 'Rendez-vous supprimé — notification email envoyée'
    load()
  } catch (e) {
    errorMsg.value = parseApiError(e, 'Erreur lors de la suppression')
  }
}

async function changeStatut(id, statut) {
  if (!statut) return
  errorMsg.value = ''
  try {
    await adminApi.updateAppointment(id, { statut })
    const labels = { CONFIRME: 'confirmé', ANNULE: 'annulé' }
    message.value = `RDV ${labels[statut] || 'mis à jour'} — emails envoyés au patient et au médecin`
    load()
  } catch (e) {
    errorMsg.value = parseApiError(e, 'Impossible de mettre à jour le rendez-vous')
  }
}

async function confirmRdv(id) {
  await changeStatut(id, 'CONFIRME')
}

async function rejectRdv(id, patientNom) {
  if (!confirm(`Annuler la demande de ${patientNom} ? Un email sera envoyé.`)) return
  await changeStatut(id, 'ANNULE')
}

function statutLabel(s) {
  return statuts.find((x) => x.value === s)?.label || s
}

function statutClass(s) {
  return {
    PLANIFIE: 'bg-amber-100 text-amber-800 dark:text-amber-200 ring-1 ring-amber-300',
    CONFIRME: 'bg-emerald-100 dark:bg-emerald-900/40 text-emerald-800 dark:text-emerald-200',
    ANNULE: 'bg-red-100 text-red-700 dark:text-red-300',
    TERMINE: 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400',
  }[s] || 'bg-slate-100 dark:bg-slate-800'
}

onMounted(load)
</script>

<template>
  <div>
    <header class="mb-6 flex flex-wrap items-center justify-between gap-4">
      <div>
        <h1 class="font-display text-3xl font-bold text-slate-900 dark:text-white">Gestion des rendez-vous</h1>
        <p class="mt-1 text-slate-600 dark:text-slate-400">Confirmer ou annuler les demandes patients — notification Gmail immédiate</p>
      </div>
      <div class="flex flex-wrap items-center gap-2">
        <span v-if="pendingCount" class="rounded-full bg-amber-100 px-3 py-1 text-sm font-medium text-amber-800 dark:text-amber-200">
          {{ pendingCount }} en attente
        </span>
        <input v-model="filterDate" type="date" class="input-field w-40" @change="onFilterChange" />
        <select v-model="filterStatut" class="input-field w-36" @change="onFilterChange">
          <option value="">Tous statuts</option>
          <option v-for="s in statuts" :key="s.value" :value="s.value">{{ s.label }}</option>
        </select>
        <button class="btn-primary" @click="showForm = !showForm">+ Nouveau RDV</button>
      </div>
    </header>

    <div v-if="showForm" class="mb-6 rounded-2xl bg-white dark:bg-slate-800 p-6 shadow-sm dark:shadow-none">
      <h2 class="mb-4 font-semibold">Nouveau rendez-vous</h2>
      <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <select v-model="form.patient_id" class="input-field">
          <option value="">Patient...</option>
          <option v-for="p in patientList" :key="p.id" :value="p.id">{{ p.prenom }} {{ p.nom }}</option>
        </select>
        <select v-model="form.medecin_id" class="input-field">
          <option value="">Médecin...</option>
          <option v-for="m in medecins" :key="m.id" :value="m.id">Dr {{ m.first_name }} {{ m.last_name }} — {{ m.specialty || 'Généraliste' }}</option>
        </select>
        <input v-model="form.date_heure" type="datetime-local" class="input-field" />
        <input v-model="form.motif" class="input-field sm:col-span-2" placeholder="Motif" />
        <input v-model="form.duree_minutes" type="number" min="15" step="15" class="input-field" placeholder="Durée (min)" />
      </div>
      <button class="btn-primary mt-4" @click="createRdv">Enregistrer</button>
    </div>

    <div v-if="showEdit" class="mb-6 rounded-2xl border-2 border-amber-200 bg-amber-50 dark:bg-amber-950/40 p-6">
      <h2 class="mb-4 font-semibold text-amber-900">Modifier le rendez-vous #{{ editForm.id }}</h2>
      <p class="mb-4 text-sm text-amber-800 dark:text-amber-200">Changez le médecin ou l'horaire si indisponible — le patient et le médecin recevront un email.</p>
      <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <select v-model="editForm.patient_id" class="input-field">
          <option v-for="p in patientList" :key="p.id" :value="p.id">{{ p.prenom }} {{ p.nom }}</option>
        </select>
        <select v-model="editForm.medecin_id" class="input-field">
          <option v-for="m in medecins" :key="m.id" :value="m.id">Dr {{ m.first_name }} {{ m.last_name }}</option>
        </select>
        <input v-model="editForm.date_heure" type="datetime-local" class="input-field" />
        <input v-model="editForm.motif" class="input-field sm:col-span-2" />
        <select v-model="editForm.statut" class="input-field">
          <option v-for="s in statuts" :key="s.value" :value="s.value">{{ s.label }}</option>
        </select>
        <input v-model="editForm.duree_minutes" type="number" class="input-field" />
        <input
          v-model="editForm.raison_modification"
          class="input-field sm:col-span-3"
          placeholder="Raison (ex: Dr Martin indisponible — report au Dr Leroy)"
        />
      </div>
      <div class="mt-4 flex gap-2">
        <button class="btn-primary" @click="saveEdit">Sauvegarder et notifier</button>
        <button class="rounded-xl border px-4 py-2 text-sm" @click="showEdit = false">Annuler</button>
      </div>
    </div>

    <p v-if="message" class="mb-4 rounded-lg bg-emerald-50 dark:bg-emerald-950/40 px-3 py-2 text-sm text-emerald-700 dark:text-emerald-300">{{ message }}</p>
    <p v-if="errorMsg" class="mb-4 rounded-lg bg-red-50 dark:bg-red-950/40 px-3 py-2 text-sm text-red-600 dark:text-red-400">{{ errorMsg }}</p>

    <p class="mb-2 text-xs text-slate-500 dark:text-slate-400">{{ pagination.total.value }} rendez-vous au total</p>

    <div class="overflow-x-auto rounded-2xl bg-white dark:bg-slate-800 shadow-sm dark:shadow-none">
      <table class="w-full min-w-[800px] text-sm">
        <thead class="bg-slate-50 dark:bg-slate-800/60">
          <tr>
            <th class="px-4 py-3 text-left">Date / Heure</th>
            <th class="px-4 py-3 text-left">Patient</th>
            <th class="px-4 py-3 text-left">Médecin</th>
            <th class="px-4 py-3 text-left">Motif</th>
            <th class="px-4 py-3 text-left">Durée</th>
            <th class="px-4 py-3 text-left">Statut</th>
            <th class="px-4 py-3 text-left">Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading"><td colspan="7" class="px-4 py-8 text-center text-slate-400 dark:text-slate-500">Chargement...</td></tr>
          <tr v-for="r in rdvList" :key="r.id" class="border-t hover:bg-slate-50 dark:hover:bg-slate-800/50 dark:bg-slate-800/60" :class="r.statut === 'PLANIFIE' ? 'bg-amber-50 dark:bg-amber-950/40/60' : ''">
            <td class="px-4 py-3 whitespace-nowrap">{{ toLocalDatetime(r.date_heure).replace('T', ' ') }}</td>
            <td class="px-4 py-3 font-medium">{{ r.patient_nom }}</td>
            <td class="px-4 py-3">{{ r.medecin_nom }}</td>
            <td class="px-4 py-3 text-slate-500 dark:text-slate-400">{{ r.motif }}</td>
            <td class="px-4 py-3">{{ r.duree_minutes }} min</td>
            <td class="px-4 py-3">
              <span class="rounded-full px-2 py-0.5 text-xs font-medium" :class="statutClass(r.statut)">{{ statutLabel(r.statut) }}</span>
            </td>
            <td class="px-4 py-3">
              <div class="flex flex-wrap gap-1">
                <template v-if="r.statut === 'PLANIFIE'">
                  <button class="rounded bg-emerald-600 px-2 py-1 text-xs text-white hover:bg-emerald-700" @click="confirmRdv(r.id)">✓ Confirmer</button>
                  <button class="rounded bg-red-600 px-2 py-1 text-xs text-white hover:bg-red-700" @click="rejectRdv(r.id, r.patient_nom)">✗ Annuler</button>
                </template>
                <button class="rounded bg-amber-100 px-2 py-1 text-xs text-amber-800 dark:text-amber-200 hover:bg-amber-200" @click="openEdit(r)">Modifier</button>
                <button class="rounded bg-red-100 px-2 py-1 text-xs text-red-700 dark:text-red-300 hover:bg-red-200" @click="deleteRdv(r.id, r.patient_nom)">Supprimer</button>
              </div>
            </td>
          </tr>
          <tr v-if="!loading && !rdvList.length"><td colspan="7" class="px-4 py-8 text-center text-slate-400 dark:text-slate-500">Aucun rendez-vous</td></tr>
        </tbody>
      </table>
      <PaginationBar
        :page="pagination.page.value"
        :page-size="pagination.pageSize.value"
        :total="pagination.total.value"
        :total-pages="pagination.totalPages.value"
        @update:page="onPageChange"
        @update:page-size="onPageSizeChange"
      />
    </div>
  </div>
</template>
