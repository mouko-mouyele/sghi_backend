<script setup>
import { ref, onMounted, computed } from 'vue'
import AppLayout from '../components/AppLayout.vue'
import PaginationBar from '../components/PaginationBar.vue'
import { hospitalization, patients, medecins } from '../api/client'
import { parseApiError } from '../utils/errors.js'
import { usePagination } from '../composables/usePagination.js'

const list = ref([])
const beds = ref([])
const patientList = ref([])
const medecinList = ref([])
const loading = ref(true)
const showForm = ref(false)
const showEdit = ref(false)
const filterStatut = ref('ACTIVE')
const message = ref('')
const errorMsg = ref('')
const pagination = usePagination(15)

const form = ref({
  patient_id: '',
  lit_id: '',
  medecin_referent_id: '',
  date_entree: '',
  date_sortie_prevue: '',
  motif_admission: '',
})

const editForm = ref({
  id: null,
  date_sortie_prevue: '',
  motif_admission: '',
  notes: '',
})

const statuts = [
  { value: 'ACTIVE', label: 'En cours' },
  { value: 'TRANSFERT', label: 'Transfert' },
  { value: 'SORTIE', label: 'Sortie' },
  { value: '', label: 'Tous' },
]

const activeCount = computed(() => pagination.total.value && filterStatut.value === 'ACTIVE'
  ? pagination.total.value
  : list.value.filter((h) => h.statut === 'ACTIVE').length)

function statutLabel(s) {
  return { ACTIVE: 'En cours', SORTIE: 'Sortie', TRANSFERT: 'Transfert' }[s] || s
}

function statutClass(s) {
  return {
    ACTIVE: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300',
    SORTIE: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400',
    TRANSFERT: 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300',
  }[s] || 'bg-slate-100 text-slate-600'
}

function fmt(d) {
  if (!d) return '—'
  return new Date(d).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' })
}

async function load() {
  loading.value = true
  errorMsg.value = ''
  try {
    const [h, b, p, m] = await Promise.all([
      hospitalization.list(pagination.params({ statut: filterStatut.value || undefined })),
      hospitalization.beds(),
      patients.list({ page: 1, page_size: 100 }),
      medecins.list({ page: 1, page_size: 100 }),
    ])
    list.value = h.data.items
    pagination.applyMeta(h.data)
    beds.value = b.data
    patientList.value = p.data.items
    medecinList.value = m.data.items
  } finally {
    loading.value = false
  }
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

function onFilterChange(statut) {
  filterStatut.value = statut
  pagination.resetPage()
  load()
}

async function admit() {
  try {
    await hospitalization.create({
      patient_id: Number(form.value.patient_id),
      lit_id: Number(form.value.lit_id),
      medecin_referent_id: Number(form.value.medecin_referent_id),
      date_entree: form.value.date_entree.length === 16
        ? `${form.value.date_entree}:00`
        : form.value.date_entree,
      date_sortie_prevue: form.value.date_sortie_prevue,
      motif_admission: form.value.motif_admission,
    })
    message.value = 'Patient admis avec succès'
    showForm.value = false
    form.value = { patient_id: '', lit_id: '', medecin_referent_id: '', date_entree: '', date_sortie_prevue: '', motif_admission: '' }
    load()
  } catch (e) {
    errorMsg.value = parseApiError(e)
  }
}

function openEdit(h) {
  editForm.value = {
    id: h.id,
    date_sortie_prevue: h.date_sortie_prevue,
    motif_admission: h.motif_admission,
    notes: h.notes || '',
  }
  showEdit.value = true
}

async function saveEdit() {
  try {
    await hospitalization.update(editForm.value.id, {
      date_sortie_prevue: editForm.value.date_sortie_prevue,
      motif_admission: editForm.value.motif_admission,
      notes: editForm.value.notes,
    })
    message.value = 'Hospitalisation mise à jour'
    showEdit.value = false
    load()
  } catch (e) {
    errorMsg.value = parseApiError(e)
  }
}

async function discharge(h) {
  if (!confirm(`Confirmer la sortie de ${h.patient_nom} ?`)) return
  try {
    await hospitalization.discharge(h.id, { notes: 'Sortie enregistrée par l\'accueil' })
    message.value = 'Sortie patient enregistrée — lit libéré'
    load()
  } catch (e) {
    errorMsg.value = parseApiError(e)
  }
}

onMounted(load)
</script>

<template>
  <AppLayout>
    <header class="mb-6 flex flex-wrap items-start justify-between gap-4">
      <div>
        <h1 class="page-title">Hospitalisation</h1>
        <p class="page-subtitle">Admissions, lits, sorties prévues et statuts — CHU Brazzaville</p>
      </div>
      <button class="btn-primary" @click="showForm = !showForm">+ Nouvelle admission</button>
    </header>

    <div v-if="message" class="mb-4 rounded-xl bg-emerald-50 px-4 py-3 text-sm text-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-200">
      {{ message }}
    </div>
    <div v-if="errorMsg" class="mb-4 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-950/40 dark:text-red-300">
      {{ errorMsg }}
    </div>

    <div class="mb-6 grid gap-4 sm:grid-cols-3">
      <div class="card text-center">
        <p class="text-3xl font-bold text-primary-700 dark:text-primary-300">{{ activeCount }}</p>
        <p class="text-sm text-slate-500 dark:text-slate-400">Hospitalisations actives</p>
      </div>
      <div class="card text-center">
        <p class="text-3xl font-bold text-emerald-600">{{ beds.length }}</p>
        <p class="text-sm text-slate-500 dark:text-slate-400">Lits disponibles</p>
      </div>
      <div class="card text-center">
        <p class="text-lg font-bold text-amber-600">1 lit = 1 patient</p>
        <p class="text-sm text-slate-500 dark:text-slate-400">Règle métier CHU</p>
      </div>
    </div>

    <!-- Formulaire admission -->
    <div v-if="showForm" class="card mb-6 border-primary-100 bg-primary-50/30 dark:border-primary-900 dark:bg-primary-950/20">
      <h2 class="mb-4 font-display text-lg font-bold text-slate-900 dark:text-white">Admission patient</h2>
      <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <div>
          <label class="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">Patient</label>
          <select v-model="form.patient_id" class="input-field">
            <option value="">— Choisir —</option>
            <option v-for="p in patientList" :key="p.id" :value="p.id">
              {{ p.prenom }} {{ p.nom }} ({{ p.numero_dossier }})
            </option>
          </select>
        </div>
        <div>
          <label class="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">Lit disponible</label>
          <select v-model="form.lit_id" class="input-field">
            <option value="">— Choisir —</option>
            <option v-for="b in beds" :key="b.id" :value="b.id">
              {{ b.numero_lit }} — Ch. {{ b.chambre_numero }} ({{ b.service_nom }})
            </option>
          </select>
        </div>
        <div>
          <label class="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">Médecin référent</label>
          <select v-model="form.medecin_referent_id" class="input-field">
            <option value="">— Choisir —</option>
            <option v-for="m in medecinList" :key="m.id" :value="m.id">
              Dr {{ m.first_name }} {{ m.last_name }} — {{ m.specialty }}
            </option>
          </select>
        </div>
        <div>
          <label class="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">Date et heure d'entrée</label>
          <input v-model="form.date_entree" type="datetime-local" class="input-field" />
        </div>
        <div>
          <label class="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">Sortie prévue</label>
          <input v-model="form.date_sortie_prevue" type="date" class="input-field" />
        </div>
        <div class="sm:col-span-2 lg:col-span-3">
          <label class="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">Motif d'admission</label>
          <input v-model="form.motif_admission" class="input-field" placeholder="Motif clinique..." />
        </div>
      </div>
      <button class="btn-primary mt-4" @click="admit">Enregistrer l'admission</button>
    </div>

    <!-- Édition -->
    <div v-if="showEdit" class="card mb-6 border-amber-200 bg-amber-50/50 dark:border-amber-800 dark:bg-amber-950/30">
      <h2 class="mb-4 font-semibold text-slate-900 dark:text-white">Modifier l'hospitalisation #{{ editForm.id }}</h2>
      <div class="grid gap-4 sm:grid-cols-2">
        <div>
          <label class="mb-1 block text-sm font-medium">Sortie prévue</label>
          <input v-model="editForm.date_sortie_prevue" type="date" class="input-field" />
        </div>
        <div>
          <label class="mb-1 block text-sm font-medium">Motif</label>
          <input v-model="editForm.motif_admission" class="input-field" />
        </div>
        <div class="sm:col-span-2">
          <label class="mb-1 block text-sm font-medium">Notes accueil</label>
          <textarea v-model="editForm.notes" class="input-field min-h-[80px]" />
        </div>
      </div>
      <div class="mt-4 flex gap-2">
        <button class="btn-primary" @click="saveEdit">Sauvegarder</button>
        <button class="rounded-xl border px-4 py-2 text-sm dark:border-slate-600" @click="showEdit = false">Annuler</button>
      </div>
    </div>

    <div class="mb-4 flex flex-wrap gap-2">
      <button
        v-for="s in statuts"
        :key="s.value"
        class="rounded-xl px-4 py-2 text-sm font-medium transition"
        :class="filterStatut === s.value
          ? 'bg-primary-600 text-white shadow-md'
          : 'bg-white text-slate-600 ring-1 ring-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:ring-slate-600'"
        @click="onFilterChange(s.value)"
      >
        {{ s.label }}
      </button>
    </div>

    <div class="card overflow-hidden p-0">
      <table class="w-full text-sm">
        <thead class="table-head">
          <tr>
            <th class="px-4 py-3 text-left">Patient</th>
            <th class="px-4 py-3 text-left">Lit / Service</th>
            <th class="px-4 py-3 text-left">Médecin</th>
            <th class="px-4 py-3 text-left">Entrée</th>
            <th class="px-4 py-3 text-left">Sortie prévue</th>
            <th class="px-4 py-3 text-left">Statut</th>
            <th class="px-4 py-3 text-right">Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading">
            <td colspan="7" class="px-4 py-10 text-center text-slate-400">Chargement...</td>
          </tr>
          <tr v-for="h in list" :key="h.id" class="table-row">
            <td class="px-4 py-3">
              <p class="font-medium text-slate-900 dark:text-white">{{ h.patient_nom }}</p>
              <p class="font-mono text-xs text-slate-500">{{ h.patient_dossier }}</p>
            </td>
            <td class="px-4 py-3">
              <p>{{ h.lit_label }}</p>
              <p class="text-xs text-slate-500">{{ h.service_nom }}</p>
            </td>
            <td class="px-4 py-3 text-slate-600 dark:text-slate-400">{{ h.medecin_nom }}</td>
            <td class="px-4 py-3 text-slate-500 dark:text-slate-400">{{ fmt(h.date_entree) }}</td>
            <td class="px-4 py-3">{{ h.date_sortie_prevue }}</td>
            <td class="px-4 py-3">
              <span :class="statutClass(h.statut)" class="rounded-full px-2 py-0.5 text-xs font-semibold">
                {{ statutLabel(h.statut) }}
              </span>
            </td>
            <td class="px-4 py-3 text-right">
              <button
                v-if="h.statut === 'ACTIVE'"
                class="mr-2 text-xs font-medium text-primary-600 hover:underline dark:text-primary-400"
                @click="openEdit(h)"
              >
                Modifier
              </button>
              <button
                v-if="h.statut === 'ACTIVE'"
                class="text-xs font-medium text-red-600 hover:underline dark:text-red-400"
                @click="discharge(h)"
              >
                Sortie
              </button>
            </td>
          </tr>
        </tbody>
      </table>
      <PaginationBar
        :page="pagination.page.value"
        :page-size="pagination.pageSize.value"
        :total="pagination.total.value"
        :total-pages="pagination.totalPages.value"
        :size-options="[10, 15, 20]"
        @update:page="onPageChange"
        @update:page-size="onPageSizeChange"
      />
    </div>
  </AppLayout>
</template>
