<script setup>

import { ref, computed, onUnmounted } from 'vue'

import { useRouter } from 'vue-router'

import { auth, setSession } from '../api/client'

import { clearSession, getHomeRoute } from '../utils/auth.js'
import { parseApiError } from '../utils/errors.js'

import PasswordField from '../components/PasswordField.vue'

import ThemeToggle from '../components/ThemeToggle.vue'



const router = useRouter()



function resetSession() {

  clearSession()

  window.location.reload()

}



const username = ref('admin')

const password = ref('Admin@2026!')

const mfaCode = ref('')

const pendingToken = ref('')

const mfaStep = ref(false)

const mfaHint = ref('')
const mfaDevCode = ref('')
const mfaEmailError = ref('')
const mfaExpired = ref(false)

const mfaSecondsLeft = ref(0)

const error = ref('')

const loading = ref(false)



let mfaTimer = null



const mfaCountdownLabel = computed(() => {

  const s = mfaSecondsLeft.value

  const m = Math.floor(s / 60)

  const sec = s % 60

  return `${m}:${String(sec).padStart(2, '0')}`

})



function stopMfaTimer() {

  if (mfaTimer) {

    clearInterval(mfaTimer)

    mfaTimer = null

  }

}



function startMfaTimer(seconds, expiresAtIso) {

  stopMfaTimer()

  mfaExpired.value = false

  const expiresAt = expiresAtIso ? new Date(expiresAtIso) : new Date(Date.now() + seconds * 1000)

  const tick = () => {

    const left = Math.max(0, Math.floor((expiresAt.getTime() - Date.now()) / 1000))

    mfaSecondsLeft.value = left

    if (left <= 0) {

      stopMfaTimer()

      mfaExpired.value = true

      error.value = 'Code expiré — validité de 5 minutes dépassée. Reconnectez-vous pour un nouveau code.'

    }

  }

  tick()

  mfaTimer = setInterval(tick, 1000)

}



onUnmounted(stopMfaTimer)

function normalizeMfaInput(raw) {
  const digits = String(raw || '').replace(/\D/g, '')
  if (!digits) return ''
  if (digits.length > 6) return digits.slice(0, 6)
  return digits.padStart(6, '0')
}



function useScreenMfaCode() {
  if (!mfaDevCode.value || mfaExpired.value) return
  mfaCode.value = mfaDevCode.value
  error.value = ''
}



async function handleLogin() {

  loading.value = true

  error.value = ''

  try {

    const { data } = await auth.login(username.value, password.value)

    if (data.requires_mfa) {
      pendingToken.value = data.pending_token
      mfaHint.value = data.mfa_hint || `Code envoyé à ${data.mfa_sent_to || 'votre email'}`
      mfaDevCode.value = data.mfa_dev_code || ''
      mfaEmailError.value = data.mfa_email_error || ''
      mfaStep.value = true
      mfaCode.value = ''
      startMfaTimer(data.mfa_expires_in || 300, data.mfa_expires_at)
      return
    }

    clearSession()
    setSession(data)
    await router.replace(getHomeRoute(data.role))

  } catch (e) {
    error.value = parseApiError(e, 'Connexion impossible — vérifiez identifiant/mot de passe ou la configuration email (MFA)')

  } finally {

    loading.value = false

  }

}



async function handleMfa() {

  if (mfaExpired.value) {

    error.value = 'Code expiré. Reconnectez-vous pour recevoir un nouveau code.'

    return

  }

  loading.value = true

  error.value = ''

  try {
    const token = pendingToken.value.trim()
    const code = normalizeMfaInput(mfaCode.value)
    const { data } = await auth.loginMfa(token, code)

    stopMfaTimer()

    clearSession()
    setSession(data)
    await router.replace(getHomeRoute(data.role))

  } catch (e) {
    error.value = parseApiError(e, 'Code invalide ou expiré — utilisez le dernier code reçu par email')

  } finally {

    loading.value = false

  }

}



function backToPassword() {

  stopMfaTimer()

  mfaStep.value = false

  mfaExpired.value = false

  pendingToken.value = ''

  mfaCode.value = ''

  mfaDevCode.value = ''
  mfaEmailError.value = ''
  mfaSecondsLeft.value = 0

  error.value = ''

}

</script>



<template>

  <div class="relative flex min-h-screen bg-slate-50 dark:bg-slate-950">

    <div class="absolute right-4 top-4 z-10 lg:right-8 lg:top-8">

      <ThemeToggle compact />

    </div>

    <div class="hidden w-1/2 flex-col justify-between bg-gradient-to-br from-primary-800 via-primary-700 to-primary-950 p-12 text-white lg:flex">

      <div class="flex items-center gap-3">

        <div class="flex h-12 w-12 items-center justify-center rounded-2xl bg-white/20 text-2xl backdrop-blur">+</div>

        <span class="font-display text-2xl font-bold">SGHL</span>

      </div>

      <div>

        <h2 class="font-display text-4xl font-bold leading-tight">ERP médical intégré</h2>

        <p class="mt-4 max-w-md text-primary-100">Hospitalisation · Labo · Pharmacie · Facturation</p>

      </div>

      <p class="text-xs text-primary-300">GI3 2025-2026</p>

    </div>



    <div class="flex flex-1 items-center justify-center p-8">

      <div class="w-full max-w-md">

        <h1 class="font-display text-3xl font-bold text-slate-900 dark:text-white">

          {{ mfaStep ? 'Code de vérification' : 'Connexion' }}

        </h1>

        <p class="mt-2 text-slate-500 dark:text-slate-400">

          {{ mfaStep ? mfaHint : 'Connexion au portail SGHL (pas l\'admin Django)' }}

        </p>



        <form v-if="!mfaStep" class="mt-8 space-y-5" @submit.prevent="handleLogin">

          <div>

            <label class="mb-1.5 block text-sm font-medium text-slate-700 dark:text-slate-300">Identifiant</label>

            <input v-model="username" type="text" class="input-field" required />

          </div>

          <div>

            <label class="mb-1.5 block text-sm font-medium text-slate-700 dark:text-slate-300">Mot de passe</label>

            <PasswordField v-model="password" placeholder="Mot de passe" required />

          </div>

          <p class="rounded-lg bg-blue-50 px-3 py-2 text-xs text-blue-800 dark:bg-blue-950/40 dark:text-blue-200">

            Personnel : code à la <strong>boîte mail de l'hôpital</strong> · Patient : code sur <strong>votre email</strong> — valide <strong>5 minutes</strong>

          </p>

          <p v-if="error" class="rounded-lg bg-red-50 px-4 py-2 text-sm text-red-600 dark:bg-red-950/40 dark:text-red-400">{{ error }}</p>

          <button type="submit" class="btn-primary w-full" :disabled="loading">

            {{ loading ? 'Connexion...' : 'Se connecter' }}

          </button>

        </form>



        <form v-else class="mt-8 space-y-5" @submit.prevent="handleMfa">
          <div v-if="mfaDevCode" class="rounded-xl border-2 border-teal-400 bg-teal-50 px-4 py-4 text-center dark:bg-teal-950/40">
            <p class="text-sm font-medium text-teal-900 dark:text-teal-100">Code de vérification — aussi envoyé par email</p>
            <p class="mt-2 font-mono text-4xl font-bold tracking-[0.35em] text-teal-800 dark:text-teal-100">{{ mfaDevCode }}</p>
            <p class="mt-2 text-xs text-teal-700 dark:text-teal-300">{{ mfaHint }}</p>
            <button
              type="button"
              class="mt-3 rounded-lg bg-teal-600 px-4 py-2 text-sm font-medium text-white hover:bg-teal-700"
              @click="useScreenMfaCode"
            >
              Utiliser ce code
            </button>
          </div>

          <div v-if="mfaEmailError" class="rounded-xl border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900 dark:border-amber-700 dark:bg-amber-950/40 dark:text-amber-100">
            Email non envoyé : {{ mfaEmailError }}
            <span v-if="mfaDevCode"> — utilisez le code affiché ci-dessus.</span>
          </div>

          <div

              ? 'bg-red-50 text-red-700 dark:bg-red-950/40 dark:text-red-300'

              : mfaSecondsLeft <= 60

                ? 'bg-amber-50 text-amber-800 dark:bg-amber-950/40 dark:text-amber-200'

                : 'bg-emerald-50 text-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-200'"

          >

            <template v-if="mfaExpired">Code expiré — reconnectez-vous</template>

            <template v-else>Code valide encore <span class="font-mono text-lg">{{ mfaCountdownLabel }}</span></template>

          </div>

          <div>

            <label class="mb-1.5 block text-sm font-medium text-slate-700 dark:text-slate-300">Code à 6 chiffres (email ou encadré ci-dessus)</label>

            <input
              v-model="mfaCode"
              v-input-filter="'digits'"
              type="text"
              inputmode="numeric"
              autocomplete="one-time-code"
              maxlength="6"
              class="input-field text-center text-2xl tracking-[0.4em]"
              placeholder="000000"
              :disabled="mfaExpired"
              required
              autofocus
            />

          </div>

          <p v-if="error" class="rounded-lg bg-red-50 px-4 py-2 text-sm text-red-600 dark:bg-red-950/40 dark:text-red-400">{{ error }}</p>

          <button type="submit" class="btn-primary w-full" :disabled="loading || mfaExpired">

            {{ loading ? 'Vérification...' : mfaExpired ? 'Code expiré' : 'Valider le code' }}

          </button>

          <button type="button" class="w-full text-sm text-slate-500 underline" @click="backToPassword">

            {{ mfaExpired ? 'Recevoir un nouveau code' : 'Retour' }}

          </button>

        </form>



        <p v-if="!mfaStep" class="mt-6 text-center text-sm text-slate-500 dark:text-slate-400">

          Patient ?

          <router-link to="/register" class="font-medium text-primary-600 dark:text-primary-400 hover:underline">Créer un compte</router-link>

        </p>

        <p v-if="!mfaStep" class="mt-2 text-center text-xs text-slate-400 dark:text-slate-500">Démo patient : patient.demo / Patient@2026!</p>

        <button type="button" class="mt-3 w-full text-center text-xs text-slate-400 underline hover:text-red-500" @click="resetSession">

          Page blanche ? Effacer la session

        </button>

      </div>

    </div>

  </div>

</template>


