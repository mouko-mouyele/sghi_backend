<script setup>
import { ref, onMounted } from 'vue'
import AdminLayout from '../../components/AdminLayout.vue'
import PaginationBar from '../../components/PaginationBar.vue'
import { adminApi } from '../../api/admin.js'
import { auth } from '../../api/client.js'
import { parseApiError } from '../../utils/errors.js'
import PasswordField from '../../components/PasswordField.vue'
import ProfilePhotoUpload from '../../components/ProfilePhotoUpload.vue'
import { usePagination } from '../../composables/usePagination.js'

const medecins = ref([])
const loading = ref(true)
const pagination = usePagination(9)
const showEdit = ref(false)
const showCreate = ref(false)
const editForm = ref({ id: null, first_name: '', last_name: '', email: '', phone: '', specialty: '', password: '', photo_url: '' })
const createForm = ref({ username: '', password: '', email: '', first_name: '', last_name: '', role: 'MEDECIN', specialty: '', phone: '' })
const createPhotoPreview = ref('')
const message = ref('')
const errorMsg = ref('')
const pendingCreatePhoto = ref(null)

async function load() {
  loading.value = true
  try {
    const { data } = await adminApi.medecins(pagination.params())
    medecins.value = data.items
    pagination.applyMeta(data)
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

function openEdit(m) {
  editForm.value = {
    id: m.id, first_name: m.first_name, last_name: m.last_name,
    email: m.email, phone: m.phone || '', specialty: m.specialty === '—' ? '' : m.specialty, password: '',
    photo_url: m.photo_url || '',
  }
  showEdit.value = true
}

async function uploadEditPhoto(file) {
  try {
    const { data } = await adminApi.uploadUserPhoto(editForm.value.id, file)
    editForm.value.photo_url = data.photo_url
    message.value = 'Photo d\'identité enregistrée'
    load()
  } catch (e) {
    errorMsg.value = parseApiError(e, 'Erreur photo')
  }
}

function onCreatePhoto(file) {
  pendingCreatePhoto.value = file
  createPhotoPreview.value = URL.createObjectURL(file)
}

async function saveEdit() {
  try {
    const payload = {
      first_name: editForm.value.first_name,
      last_name: editForm.value.last_name,
      email: editForm.value.email,
      phone: editForm.value.phone,
      specialty: editForm.value.specialty,
    }
    if (editForm.value.password) payload.password = editForm.value.password
    await adminApi.updateMedecin(editForm.value.id, payload)
    message.value = 'Médecin modifié'
    showEdit.value = false
    load()
  } catch (e) {
    errorMsg.value = parseApiError(e, 'Erreur')
  }
}

async function deleteMedecin(m) {
  if (!confirm(`Supprimer Dr ${m.first_name} ${m.last_name} ?`)) return
  try {
    await adminApi.deleteMedecin(m.id)
    message.value = 'Médecin supprimé'
    load()
  } catch (e) {
    errorMsg.value = parseApiError(e, 'Impossible de supprimer')
  }
}

async function createMedecin() {
  if ((createForm.value.password || '').length < 10) {
    errorMsg.value = 'Le mot de passe doit contenir au moins 10 caractères (majuscule, minuscule et chiffre)'
    return
  }
  try {
    const { data } = await auth.registerStaff(createForm.value)
    if (pendingCreatePhoto.value) {
      await adminApi.uploadUserPhoto(data.id, pendingCreatePhoto.value)
    }
    message.value = 'Médecin créé avec photo d\'identité'
    showCreate.value = false
    pendingCreatePhoto.value = null
    createPhotoPreview.value = ''
    load()
  } catch (e) {
    errorMsg.value = parseApiError(e, 'Erreur création')
  }
}

onMounted(load)
</script>

<template>
  <AdminLayout>
    <header class="mb-6 flex flex-wrap items-center justify-between gap-4">
      <div>
        <h1 class="font-display text-3xl font-bold text-slate-900 dark:text-white">Gestion des médecins</h1>
        <p class="mt-1 text-slate-600 dark:text-slate-400">Modifier, supprimer et ajouter des médecins</p>
      </div>
      <button class="btn-primary" @click="showCreate = !showCreate">+ Nouveau médecin</button>
    </header>

    <div v-if="showCreate" class="mb-6 rounded-2xl bg-white dark:bg-slate-800 p-6 shadow-sm dark:shadow-none">
      <h2 class="mb-4 font-semibold">Nouveau médecin</h2>
      <div class="grid gap-6 lg:grid-cols-[auto_1fr]">
        <ProfilePhotoUpload :photo-url="createPhotoPreview" @upload="onCreatePhoto" />
        <div class="grid gap-3 sm:grid-cols-2">
          <input v-model="createForm.username" v-input-filter="'alnum'" class="input-field" placeholder="Identifiant" />
          <PasswordField v-model="createForm.password" placeholder="Mot de passe" autocomplete="new-password" />
          <input v-model="createForm.email" class="input-field" placeholder="Email" />
          <input v-model="createForm.phone" v-input-filter="'phone'" inputmode="tel" class="input-field" placeholder="Téléphone" />
          <input v-model="createForm.first_name" v-input-filter="'letters'" class="input-field" placeholder="Prénom" />
          <input v-model="createForm.last_name" v-input-filter="'letters'" class="input-field" placeholder="Nom" />
          <input v-model="createForm.specialty" class="input-field sm:col-span-2" placeholder="Spécialité" />
        </div>
      </div>
      <button class="btn-primary mt-4" @click="createMedecin">Créer le médecin</button>
    </div>

    <div v-if="showEdit" class="mb-6 rounded-2xl border-2 border-primary-200 bg-primary-50 dark:bg-primary-950/40 p-6">
      <h2 class="mb-4 font-semibold">Modifier le médecin</h2>
      <div class="grid gap-6 lg:grid-cols-[auto_1fr]">
        <ProfilePhotoUpload :photo-url="editForm.photo_url" @upload="uploadEditPhoto" />
        <div class="grid gap-3 sm:grid-cols-2">
        <input v-model="editForm.first_name" v-input-filter="'letters'" class="input-field" placeholder="Prénom" />
        <input v-model="editForm.last_name" v-input-filter="'letters'" class="input-field" placeholder="Nom" />
        <input v-model="editForm.email" class="input-field" placeholder="Email" />
        <input v-model="editForm.phone" v-input-filter="'phone'" inputmode="tel" class="input-field" placeholder="Téléphone" />
        <input v-model="editForm.specialty" class="input-field" placeholder="Spécialité" />
        <PasswordField v-model="editForm.password" placeholder="Nouveau mot de passe (optionnel)" autocomplete="new-password" />
        </div>
      </div>
      <div class="mt-4 flex gap-2">
        <button class="btn-primary" @click="saveEdit">Sauvegarder</button>
        <button class="rounded-xl border px-4 py-2 text-sm" @click="showEdit = false">Annuler</button>
      </div>
    </div>

    <p v-if="message" class="mb-4 text-sm text-emerald-600">{{ message }}</p>
    <p v-if="errorMsg" class="mb-4 text-sm text-red-600 dark:text-red-400">{{ errorMsg }}</p>

    <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <div v-for="m in medecins" :key="m.id" class="rounded-2xl bg-white dark:bg-slate-800 p-5 shadow-sm dark:shadow-none">
        <div class="flex gap-4">
          <div class="h-20 w-[3.75rem] shrink-0 overflow-hidden rounded-xl border-2 border-slate-100 dark:border-slate-600" style="aspect-ratio:3/4">
            <img v-if="m.photo_url" :src="m.photo_url" class="h-full w-full object-cover" alt="" />
            <div v-else class="flex h-full items-center justify-center bg-primary-50 text-xl dark:bg-primary-900/40">👨‍⚕️</div>
          </div>
          <div class="min-w-0 flex-1">
            <div class="flex items-start justify-between gap-2">
              <h3 class="font-semibold">Dr {{ m.first_name }} {{ m.last_name }}</h3>
              <span class="shrink-0 rounded-full bg-emerald-100 dark:bg-emerald-900/40 px-2 py-0.5 text-xs text-emerald-700 dark:text-emerald-300">{{ m.rdv_count }} RDV</span>
            </div>
            <p class="text-sm text-primary-600 dark:text-primary-400">{{ m.specialty }}</p>
            <span
              class="mt-1 inline-block rounded-full px-2 py-0.5 text-[10px] font-semibold"
              :class="m.disponible_rdv ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40' : 'bg-amber-100 text-amber-700 dark:bg-amber-900/40'"
            >
              {{ m.disponible_rdv ? 'Disponible' : 'Indisponible' }}
            </span>
          </div>
        </div>
        <p class="mt-2 text-xs text-slate-500 dark:text-slate-400">📧 {{ m.email }}</p>
        <p class="text-xs text-slate-500 dark:text-slate-400">🔑 {{ m.username }}</p>
        <div class="mt-4 flex gap-2">
          <button class="rounded bg-amber-100 px-3 py-1 text-xs text-amber-800 dark:text-amber-200" @click="openEdit(m)">Modifier</button>
          <button class="rounded bg-red-100 px-3 py-1 text-xs text-red-700 dark:text-red-300" @click="deleteMedecin(m)">Supprimer</button>
        </div>
      </div>
    </div>

    <div class="mt-4 overflow-hidden rounded-2xl bg-white shadow-sm dark:bg-slate-800 dark:shadow-none">
      <PaginationBar
        :page="pagination.page.value"
        :page-size="pagination.pageSize.value"
        :total="pagination.total.value"
        :total-pages="pagination.totalPages.value"
        :size-options="[6, 9, 12, 18]"
        @update:page="onPageChange"
        @update:page-size="onPageSizeChange"
      />
    </div>
  </AdminLayout>
</template>
