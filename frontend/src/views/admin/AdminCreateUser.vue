<script setup>

import { ref } from 'vue'

import AdminLayout from '../../components/AdminLayout.vue'

import { auth } from '../../api/client'

import { adminApi } from '../../api/admin.js'

import { parseApiError } from '../../utils/errors.js'

import PasswordField from '../../components/PasswordField.vue'

import ProfilePhotoUpload from '../../components/ProfilePhotoUpload.vue'



const form = ref({

  username: '', password: '', email: '',

  first_name: '', last_name: '', role: 'MEDECIN',

  specialty: '', phone: '',

})

const createPhotoPreview = ref('')

const pendingCreatePhoto = ref(null)

const success = ref('')

const error = ref('')

const loading = ref(false)



const roles = [

  { value: 'MEDECIN', label: 'Médecin' },

  { value: 'INFIRMIER', label: 'Infirmier(ère)' },

  { value: 'BIOLOGISTE', label: 'Biologiste' },

  { value: 'PHARMACIEN', label: 'Pharmacien' },

  { value: 'COMPTABLE', label: 'Comptable' },

  { value: 'RECEPTIONNISTE', label: 'Réceptionniste' },

  { value: 'ADMIN', label: 'Administrateur' },

]



function onCreatePhoto(file) {

  pendingCreatePhoto.value = file

  createPhotoPreview.value = URL.createObjectURL(file)

}



function resetForm() {

  form.value = { username: '', password: '', email: '', first_name: '', last_name: '', role: 'MEDECIN', specialty: '', phone: '' }

  pendingCreatePhoto.value = null

  createPhotoPreview.value = ''

}



async function submit() {

  loading.value = true

  success.value = ''

  error.value = ''

  try {

    const { data } = await auth.registerStaff(form.value)

    if (pendingCreatePhoto.value) {

      await adminApi.uploadUserPhoto(data.id, pendingCreatePhoto.value)

    }

    success.value = `Compte « ${data.username || form.value.username} » créé avec photo d'identité`

    resetForm()

  } catch (e) {

    error.value = parseApiError(e, 'Erreur lors de la création')

  } finally {

    loading.value = false

  }

}

</script>



<template>

  <AdminLayout>

    <header class="mb-8">

      <h1 class="font-display text-3xl font-bold text-slate-900 dark:text-white">Créer un compte</h1>

      <p class="mt-1 text-slate-600 dark:text-slate-400">Ajouter un membre du personnel avec photo d'identité 3×4</p>

    </header>



    <form class="max-w-3xl rounded-2xl bg-white dark:bg-slate-800 p-6 shadow-sm dark:shadow-none" @submit.prevent="submit">

      <div class="grid gap-8 lg:grid-cols-[auto_1fr]">

        <ProfilePhotoUpload :photo-url="createPhotoPreview" @upload="onCreatePhoto" />



        <div class="space-y-4">

          <div class="grid gap-4 sm:grid-cols-2">

            <div>

              <label class="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">Prénom</label>

              <input v-model="form.first_name" v-input-filter="'letters'" class="input-field" required />

            </div>

            <div>

              <label class="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">Nom</label>

              <input v-model="form.last_name" v-input-filter="'letters'" class="input-field" required />

            </div>

          </div>

          <div>

            <label class="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">Identifiant</label>

            <input v-model="form.username" v-input-filter="'alnum'" class="input-field" required />

          </div>

          <div>

            <label class="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">Email</label>

            <input v-model="form.email" type="email" class="input-field" required />

          </div>

          <div>

            <label class="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">Téléphone</label>

            <input v-model="form.phone" v-input-filter="'phone'" inputmode="tel" class="input-field" placeholder="Optionnel" />

          </div>

          <div>

            <label class="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">Mot de passe</label>

            <PasswordField v-model="form.password" placeholder="Mot de passe" :minlength="10" autocomplete="new-password" required />

            <p class="mt-1 text-xs text-slate-400 dark:text-slate-500">10 caractères min., majuscule, minuscule et chiffre</p>

          </div>

          <div>

            <label class="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">Rôle</label>

            <select v-model="form.role" class="input-field">

              <option v-for="r in roles" :key="r.value" :value="r.value">{{ r.label }}</option>

            </select>

          </div>

          <div v-if="form.role === 'MEDECIN'">

            <label class="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">Spécialité</label>

            <input v-model="form.specialty" v-input-filter="'text'" class="input-field" placeholder="Ex: Cardiologie" />

          </div>

        </div>

      </div>



      <p v-if="success" class="mt-6 rounded-lg bg-emerald-50 dark:bg-emerald-950/40 px-3 py-2 text-sm text-emerald-700 dark:text-emerald-300">{{ success }}</p>

      <p v-if="error" class="mt-6 rounded-lg bg-red-50 dark:bg-red-950/40 px-3 py-2 text-sm text-red-600 dark:text-red-400">{{ error }}</p>

      <button type="submit" class="btn-primary mt-6" :disabled="loading">

        {{ loading ? 'Création...' : 'Créer le compte' }}

      </button>

    </form>

  </AdminLayout>

</template>

