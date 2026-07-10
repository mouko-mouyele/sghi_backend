<script setup>
import { ref, onMounted } from 'vue'
import AdminLayout from '../../components/AdminLayout.vue'
import PaginationBar from '../../components/PaginationBar.vue'
import { adminApi } from '../../api/admin.js'
import { patients } from '../../api/client.js'
import { usePagination } from '../../composables/usePagination.js'

const list = ref([])
const search = ref('')
const loading = ref(true)
const pagination = usePagination(10)
const showForm = ref(false)
const showEdit = ref(false)
const form = ref({
  numero_dossier: '', nom: '', prenom: '', date_naissance: '', sexe: 'M', telephone: '', email: '', adresse: '', groupe_sanguin: '',
})
const editForm = ref({ id: null, numero_dossier: '', nom: '', prenom: '', date_naissance: '', sexe: 'M', telephone: '', email: '', adresse: '', groupe_sanguin: '' })
const message = ref('')
const errorMsg = ref('')

async function load() {
  loading.value = true
  try {
    const { data } = await patients.list(pagination.params({ search: search.value }))
    list.value = data.items
    pagination.applyMeta(data)
  } finally {
    loading.value = false
  }
}

function onSearch() {
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

async function createPatient() {
  try {
    await patients.create(form.value)
    message.value = 'Patient créé'
    showForm.value = false
    load()
  } catch (e) {
    errorMsg.value = e.response?.data?.detail || 'Erreur'
  }
}

function openEdit(p) {
  editForm.value = { ...p, id: p.id }
  showEdit.value = true
}

async function saveEdit() {
  try {
    const { id, ...data } = editForm.value
    await adminApi.updatePatient(id, data)
    message.value = 'Patient modifié'
    showEdit.value = false
    load()
  } catch (e) {
    errorMsg.value = e.response?.data?.detail || 'Erreur modification'
  }
}

async function deletePatient(p) {
  if (!confirm(`Supprimer le patient ${p.prenom} ${p.nom} (${p.numero_dossier}) ?`)) return
  try {
    await adminApi.deletePatient(p.id)
    message.value = 'Patient supprimé'
    load()
  } catch (e) {
    errorMsg.value = e.response?.data?.detail || 'Impossible de supprimer (hospitalisation active ?)'
  }
}

onMounted(load)
</script>

<template>
  <AdminLayout>
    <header class="mb-6 flex flex-wrap items-center justify-between gap-4">
      <div>
        <h1 class="font-display text-3xl font-bold text-slate-900 dark:text-white">Gestion des patients</h1>
        <p class="mt-1 text-slate-600 dark:text-slate-400">Créer, modifier et supprimer les dossiers patients</p>
      </div>
      <div class="flex gap-2">
        <input v-model="search" class="input-field w-48" placeholder="Rechercher..." @keyup.enter="onSearch" />
        <button class="rounded-xl border px-4 py-2 text-sm" @click="onSearch">Rechercher</button>
        <button class="btn-primary" @click="showForm = !showForm">+ Nouveau</button>
      </div>
    </header>

    <div v-if="showForm" class="mb-6 rounded-2xl bg-white dark:bg-slate-800 p-6 shadow-sm dark:shadow-none">
      <h2 class="mb-3 font-semibold">Nouveau patient</h2>
      <div class="grid gap-3 sm:grid-cols-3">
        <input v-model="form.numero_dossier" v-input-filter="'alnum'" class="input-field" placeholder="N° dossier" />
        <input v-model="form.nom" v-input-filter="'letters'" class="input-field" placeholder="Nom" />
        <input v-model="form.prenom" v-input-filter="'letters'" class="input-field" placeholder="Prénom" />
        <input v-model="form.date_naissance" type="date" class="input-field" />
        <select v-model="form.sexe" class="input-field"><option value="M">M</option><option value="F">F</option></select>
        <input v-model="form.telephone" v-input-filter="'phone'" inputmode="tel" class="input-field" placeholder="Téléphone" />
        <input v-model="form.email" class="input-field" placeholder="Email" />
        <input v-model="form.groupe_sanguin" class="input-field" placeholder="Groupe sanguin" />
      </div>
      <button class="btn-primary mt-4" @click="createPatient">Enregistrer</button>
    </div>

    <div v-if="showEdit" class="mb-6 rounded-2xl border-2 border-amber-200 bg-amber-50 dark:bg-amber-950/40 p-6">
      <h2 class="mb-3 font-semibold text-amber-900">Modifier — {{ editForm.prenom }} {{ editForm.nom }}</h2>
      <div class="grid gap-3 sm:grid-cols-3">
        <input v-model="editForm.numero_dossier" v-input-filter="'alnum'" class="input-field" placeholder="N° dossier" />
        <input v-model="editForm.nom" v-input-filter="'letters'" class="input-field" />
        <input v-model="editForm.prenom" v-input-filter="'letters'" class="input-field" />
        <input v-model="editForm.date_naissance" type="date" class="input-field" />
        <select v-model="editForm.sexe" class="input-field"><option value="M">M</option><option value="F">F</option></select>
        <input v-model="editForm.telephone" v-input-filter="'phone'" inputmode="tel" class="input-field" />
        <input v-model="editForm.email" class="input-field" />
        <input v-model="editForm.groupe_sanguin" v-input-filter="'letters'" class="input-field" />
        <input v-model="editForm.adresse" v-input-filter="'text'" class="input-field sm:col-span-2" placeholder="Adresse" />
      </div>
      <div class="mt-4 flex gap-2">
        <button class="btn-primary" @click="saveEdit">Sauvegarder</button>
        <button class="rounded-xl border px-4 py-2 text-sm" @click="showEdit = false">Annuler</button>
      </div>
    </div>

    <p v-if="message" class="mb-4 text-sm text-emerald-600">{{ message }}</p>
    <p v-if="errorMsg" class="mb-4 text-sm text-red-600 dark:text-red-400">{{ errorMsg }}</p>

    <div class="overflow-x-auto rounded-2xl bg-white dark:bg-slate-800 shadow-sm dark:shadow-none">
      <table class="w-full min-w-[700px] text-sm">
        <thead class="bg-slate-50 dark:bg-slate-800/60">
          <tr>
            <th class="px-4 py-3 text-left">N° Dossier</th>
            <th class="px-4 py-3 text-left">Nom complet</th>
            <th class="px-4 py-3 text-left">Téléphone</th>
            <th class="px-4 py-3 text-left">Email</th>
            <th class="px-4 py-3 text-left">Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="p in list" :key="p.id" class="border-t hover:bg-slate-50 dark:hover:bg-slate-800/50 dark:bg-slate-800/60">
            <td class="px-4 py-3 font-mono text-xs text-primary-700 dark:text-primary-300">{{ p.numero_dossier }}</td>
            <td class="px-4 py-3 font-medium">{{ p.prenom }} {{ p.nom }}</td>
            <td class="px-4 py-3">{{ p.telephone || '—' }}</td>
            <td class="px-4 py-3 text-slate-500 dark:text-slate-400">{{ p.email || '—' }}</td>
            <td class="px-4 py-3">
              <button class="mr-2 rounded bg-amber-100 px-2 py-1 text-xs text-amber-800 dark:text-amber-200" @click="openEdit(p)">Modifier</button>
              <button class="rounded bg-red-100 px-2 py-1 text-xs text-red-700 dark:text-red-300" @click="deletePatient(p)">Supprimer</button>
            </td>
          </tr>
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
  </AdminLayout>
</template>
