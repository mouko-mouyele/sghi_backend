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

const list = ref([])
const loading = ref(true)
const pagination = usePagination(10)
const showEdit = ref(false)
const showCreate = ref(false)
const editForm = ref({ id: null, first_name: '', last_name: '', email: '', phone: '', password: '', photo_url: '' })
const createForm = ref({ username: '', password: '', email: '', first_name: '', last_name: '', role: 'RECEPTIONNISTE', phone: '' })
const createPhotoPreview = ref('')
const pendingCreatePhoto = ref(null)
const message = ref('')
const errorMsg = ref('')

async function load() {
  loading.value = true
  try {
    const { data } = await adminApi.secretaires(pagination.params())
    list.value = data.items
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

function openEdit(s) {
  editForm.value = {
    id: s.id, first_name: s.first_name, last_name: s.last_name,
    email: s.email, phone: s.phone || '', password: '',
    photo_url: s.photo_url || '',
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
    }
    if (editForm.value.password) payload.password = editForm.value.password
    await adminApi.updateSecretaire(editForm.value.id, payload)
    message.value = 'Secrétaire modifié(e)'
    showEdit.value = false
    load()
  } catch (e) {
    errorMsg.value = parseApiError(e, 'Erreur')
  }
}

async function deleteSecretaire(s) {
  if (!confirm(`Supprimer ${s.first_name} ${s.last_name} (${s.username}) ?`)) return
  try {
    await adminApi.deleteSecretaire(s.id)
    message.value = 'Secrétaire supprimé(e)'
    load()
  } catch (e) {
    errorMsg.value = parseApiError(e, 'Impossible de supprimer')
  }
}

async function createSecretaire() {
  if ((createForm.value.password || '').length < 10) {
    errorMsg.value = 'Le mot de passe doit contenir au moins 10 caractères (majuscule, minuscule et chiffre)'
    return
  }
  try {
    const { data } = await auth.registerStaff(createForm.value)
    if (pendingCreatePhoto.value) {
      await adminApi.uploadUserPhoto(data.id, pendingCreatePhoto.value)
    }
    message.value = 'Secrétaire créé(e) avec photo d\'identité'
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
        <h1 class="font-display text-3xl font-bold text-slate-900 dark:text-white">Gestion des secrétaires</h1>
        <p class="mt-1 text-slate-600 dark:text-slate-400">Réceptionnistes — modifier, supprimer et créer</p>
      </div>
      <button class="btn-primary" @click="showCreate = !showCreate">+ Nouveau secrétaire</button>
    </header>

    <div v-if="showCreate" class="mb-6 rounded-2xl bg-white dark:bg-slate-800 p-6 shadow-sm dark:shadow-none">
      <h2 class="mb-4 font-semibold">Nouveau secrétaire / réceptionniste</h2>
      <div class="grid gap-6 lg:grid-cols-[auto_1fr]">
        <ProfilePhotoUpload :photo-url="createPhotoPreview" @upload="onCreatePhoto" />
        <div class="grid gap-3 sm:grid-cols-2">
          <input v-model="createForm.username" v-input-filter="'alnum'" class="input-field" placeholder="Identifiant (ex: accueil)" />
          <PasswordField v-model="createForm.password" placeholder="Mot de passe" :minlength="10" autocomplete="new-password" required />
          <input v-model="createForm.email" type="email" class="input-field" placeholder="Email" />
          <input v-model="createForm.phone" v-input-filter="'phone'" inputmode="tel" class="input-field" placeholder="Téléphone" />
          <input v-model="createForm.first_name" v-input-filter="'letters'" class="input-field" placeholder="Prénom" />
          <input v-model="createForm.last_name" v-input-filter="'letters'" class="input-field" placeholder="Nom" />
        </div>
      </div>
      <p class="mt-2 text-xs text-slate-500 dark:text-slate-400">
        Mot de passe : minimum 10 caractères, avec au moins une majuscule, une minuscule et un chiffre (ex. Accueil@2026!)
      </p>
      <button class="btn-primary mt-4" @click="createSecretaire">Créer</button>
    </div>

    <div v-if="showEdit" class="mb-6 rounded-2xl border-2 border-violet-200 dark:border-violet-700 bg-violet-50 dark:bg-violet-950/40 p-6">
      <h2 class="mb-4 font-semibold">Modifier le secrétaire</h2>
      <div class="grid gap-6 lg:grid-cols-[auto_1fr]">
        <ProfilePhotoUpload :photo-url="editForm.photo_url" @upload="uploadEditPhoto" />
        <div class="grid gap-3 sm:grid-cols-2">
        <input v-model="editForm.first_name" v-input-filter="'letters'" class="input-field" placeholder="Prénom" />
        <input v-model="editForm.last_name" v-input-filter="'letters'" class="input-field" placeholder="Nom" />
        <input v-model="editForm.email" class="input-field" placeholder="Email" />
        <input v-model="editForm.phone" v-input-filter="'phone'" inputmode="tel" class="input-field" placeholder="Téléphone" />
        <div class="sm:col-span-2">
          <PasswordField v-model="editForm.password" placeholder="Nouveau mot de passe (optionnel, min. 10 car.)" :minlength="10" autocomplete="new-password" />
        </div>
        </div>
      </div>
      <div class="mt-4 flex gap-2">
        <button class="btn-primary" @click="saveEdit">Sauvegarder</button>
        <button class="rounded-xl border px-4 py-2 text-sm" @click="showEdit = false">Annuler</button>
      </div>
    </div>

    <p v-if="message" class="mb-4 text-sm text-emerald-600">{{ message }}</p>
    <p v-if="errorMsg" class="mb-4 text-sm text-red-600 dark:text-red-400">{{ errorMsg }}</p>

    <div class="overflow-hidden rounded-2xl bg-white dark:bg-slate-800 shadow-sm dark:shadow-none">
      <table class="w-full text-sm">
        <thead class="bg-slate-50 dark:bg-slate-800/60">
          <tr>
            <th class="px-4 py-3 text-left">Photo</th>
            <th class="px-4 py-3 text-left">Identifiant</th>
            <th class="px-4 py-3 text-left">Nom</th>
            <th class="px-4 py-3 text-left">Email</th>
            <th class="px-4 py-3 text-left">Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="s in list" :key="s.id" class="border-t hover:bg-slate-50 dark:hover:bg-slate-800/50 dark:bg-slate-800/60">
            <td class="px-4 py-3">
              <div class="h-14 w-[2.625rem] overflow-hidden rounded-lg border border-slate-200 dark:border-slate-600" style="aspect-ratio:3/4">
                <img v-if="s.photo_url" :src="s.photo_url" class="h-full w-full object-cover" alt="" />
                <div v-else class="flex h-full items-center justify-center bg-violet-50 text-lg dark:bg-violet-950/40">👤</div>
              </div>
            </td>
            <td class="px-4 py-3 font-medium">{{ s.username }}</td>
            <td class="px-4 py-3">{{ s.first_name }} {{ s.last_name }}</td>
            <td class="px-4 py-3 text-slate-500 dark:text-slate-400">{{ s.email }}</td>
            <td class="px-4 py-3">
              <button class="mr-2 rounded bg-amber-100 px-2 py-1 text-xs text-amber-800 dark:text-amber-200" @click="openEdit(s)">Modifier</button>
              <button class="rounded bg-red-100 px-2 py-1 text-xs text-red-700 dark:text-red-300" @click="deleteSecretaire(s)">Supprimer</button>
            </td>
          </tr>
          <tr v-if="!loading && !list.length"><td colspan="5" class="px-4 py-8 text-center text-slate-400 dark:text-slate-500">Aucun secrétaire</td></tr>
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
