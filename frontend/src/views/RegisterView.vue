<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { auth, setSession } from '../api/client'
import { patientApi } from '../api/patient.js'
import { HOSPITAL_EMERGENCY_PHONE } from '../utils/hospital.js'
import PasswordField from '../components/PasswordField.vue'
import ThemeToggle from '../components/ThemeToggle.vue'
import { parseApiError } from '../utils/errors.js'

const router = useRouter()
const etab = ref(null)
const form = ref({
  username: '', password: '', passwordConfirm: '', email: '', nom: '', prenom: '',
  date_naissance: '', sexe: 'M', telephone: '', adresse: '',
  consentement_traitement: true,
})
const error = ref('')
const loading = ref(false)

onMounted(async () => {
  try {
    const { data } = await patientApi.establishment()
    etab.value = data
  } catch { /* ignore */ }
})

async function handleRegister() {
  if (!form.value.telephone.trim()) {
    error.value = 'Le numéro de téléphone est obligatoire'
    return
  }
  if (form.value.password.length < 10) {
    error.value = 'Le mot de passe doit contenir au moins 10 caractères'
    return
  }
  if (form.value.password !== form.value.passwordConfirm) {
    error.value = 'Les mots de passe ne correspondent pas'
    return
  }
  loading.value = true
  error.value = ''
  try {
    const { passwordConfirm, ...payload } = form.value
    const { data } = await auth.registerPatient({
      ...payload,
      telephone: form.value.telephone.trim(),
    })
    setSession(data)
    router.push('/patient')
  } catch (e) {
    error.value = parseApiError(e, 'Erreur lors de l\'inscription')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="relative flex min-h-screen bg-slate-50 dark:bg-slate-950">
    <div class="absolute right-4 top-4 z-10 lg:right-8 lg:top-8">
      <ThemeToggle compact />
    </div>
    <div class="hidden w-1/2 flex-col justify-between bg-gradient-to-br from-teal-800 via-teal-700 to-teal-950 p-12 text-white lg:flex">
      <div>
        <div class="flex items-center gap-3">
          <div class="flex h-12 w-12 items-center justify-center rounded-2xl bg-white/20 text-2xl backdrop-blur">+</div>
          <span class="font-display text-2xl font-bold">SGHL Patient</span>
        </div>
        <h2 v-if="etab" class="mt-10 font-display text-3xl font-bold leading-tight">{{ etab.nom_etablissement }}</h2>
        <p v-if="etab" class="mt-3 text-teal-100">{{ etab.adresse }}</p>
      </div>
      <div v-if="etab" class="overflow-hidden rounded-2xl shadow-2xl">
        <iframe
          :src="etab.google_maps_embed_url"
          class="h-64 w-full border-0"
          loading="lazy"
          title="CHU Brazzaville — Google Maps"
        />
      </div>
      <p class="text-xs text-teal-300">Urgences : {{ etab?.urgences_telephone || HOSPITAL_EMERGENCY_PHONE }}</p>
    </div>

    <div class="flex flex-1 items-center justify-center p-8">
    <div class="w-full max-w-lg rounded-2xl border border-slate-100 bg-white dark:bg-slate-800/90 dark:border-slate-700 p-8 shadow-card backdrop-blur">
      <h1 class="font-display text-2xl font-bold text-slate-900 dark:text-white">Inscription patient</h1>
      <p class="mt-1 text-sm text-slate-500 dark:text-slate-400">Créez votre compte pour accéder au portail patient SGHL</p>

      <form class="mt-6 space-y-4" @submit.prevent="handleRegister">
        <div class="grid gap-4 sm:grid-cols-2">
          <div>
            <label class="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-400">Nom</label>
            <input v-model="form.nom" v-input-filter="'letters'" class="input-field" required />
          </div>
          <div>
            <label class="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-400">Prénom</label>
            <input v-model="form.prenom" v-input-filter="'letters'" class="input-field" required />
          </div>
        </div>
        <div>
          <label class="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-400">Identifiant</label>
          <input v-model="form.username" v-input-filter="'alnum'" class="input-field" required />
        </div>
        <div>
          <label class="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-400">Email</label>
          <input v-model="form.email" type="email" class="input-field" required />
        </div>
        <div class="grid gap-4 sm:grid-cols-2">
          <div>
            <label class="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-400">Mot de passe</label>
            <PasswordField
              v-model="form.password"
              placeholder="Min. 10 caractères"
              :minlength="10"
              autocomplete="new-password"
              required
            />
            <p class="mt-1 text-xs text-slate-400">Majuscule, minuscule et chiffre</p>
          </div>
          <div>
            <label class="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-400">Confirmer le mot de passe</label>
            <PasswordField
              v-model="form.passwordConfirm"
              placeholder="Retapez le mot de passe"
              :minlength="10"
              autocomplete="new-password"
              required
            />
          </div>
        </div>
        <div>
          <label class="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-400">Téléphone mobile</label>
          <input
            v-model="form.telephone"
            v-input-filter="'phone'"
            type="tel"
            inputmode="tel"
            class="input-field"
            placeholder="06 123 45 67 ou +242 066967236"
            autocomplete="tel"
            required
          />
          <p class="mt-1 text-xs text-slate-400">MTN : 06… · Airtel : 04… ou 05…</p>
        </div>
        <div>
          <label class="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-400">Adresse (optionnel)</label>
          <input v-model="form.adresse" v-input-filter="'text'" type="text" class="input-field" placeholder="Quartier, ville…" />
        </div>
        <div class="grid gap-4 sm:grid-cols-2">
          <div>
            <label class="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-400">Date de naissance</label>
            <input v-model="form.date_naissance" type="date" class="input-field" required />
          </div>
          <div>
            <label class="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-400">Sexe</label>
            <select v-model="form.sexe" class="input-field">
              <option value="M">Masculin</option>
              <option value="F">Féminin</option>
            </select>
          </div>
        </div>
        <label class="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-400">
          <input v-model="form.consentement_traitement" type="checkbox" class="rounded" />
          J'accepte le traitement de mes données médicales
        </label>
        <p v-if="error" class="rounded-lg bg-red-50 dark:bg-red-950/40 px-3 py-2 text-sm text-red-600 dark:text-red-400">{{ error }}</p>
        <button type="submit" class="btn-primary w-full" :disabled="loading">
          {{ loading ? 'Inscription...' : 'Créer mon compte' }}
        </button>
      </form>
      <p class="mt-4 text-center text-sm text-slate-500 dark:text-slate-400">
        Déjà inscrit ?
        <router-link to="/login" class="font-medium text-primary-600 dark:text-primary-400 hover:underline">Se connecter</router-link>
      </p>
    </div>
    </div>
  </div>
</template>
