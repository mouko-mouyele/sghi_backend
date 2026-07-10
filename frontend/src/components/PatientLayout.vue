<script setup>

import { ref, onMounted, computed } from 'vue'

import { useRouter, useRoute } from 'vue-router'

import { auth } from '../api/client.js'

import { clearSession, isJustLoggedIn, isLoggedIn } from '../utils/auth.js'

import ThemeToggle from './ThemeToggle.vue'



const router = useRouter()

const route = useRoute()

const user = ref(null)

const ready = ref(false)



const nav = [

  { to: '/patient', label: 'Tableau de bord', icon: '📊' },

  { to: '/patient/rendez-vous', label: 'Rendez-vous', icon: '📅' },

  { to: '/patient/dossier', label: 'Mon dossier', icon: '📋' },

  { to: '/patient/laboratoire', label: 'Résultats labo', icon: '🔬' },

  { to: '/patient/pharmacie', label: 'Pharmacie', icon: '💊' },

  { to: '/patient/soins', label: 'Plan de soins', icon: '🩺' },

  { to: '/patient/messages', label: 'Messages', icon: '💬' },

  { to: '/patient/factures', label: 'Factures', icon: '💳' },

  { to: '/patient/etablissement', label: 'Localisation', icon: '📍' },

]



const pageTitle = computed(() => nav.find((n) => n.to === route.path)?.label || 'Espace patient')



onMounted(async () => {
  if (!isLoggedIn()) {
    router.replace('/login')
    return
  }

  const loadProfile = async () => {
    const { data } = await auth.me()
    user.value = data
    localStorage.setItem('role', data.role)
    ready.value = true
  }

  try {
    await loadProfile()
  } catch {
    if (isJustLoggedIn()) {
      await new Promise((r) => setTimeout(r, 400))
      try {
        await loadProfile()
        return
      } catch { /* fall through */ }
    }
    clearSession()
    router.replace('/login')
  }
})



async function logout() {

  try { await auth.logout() } catch { /* ignore */ }

  clearSession()

  router.push('/login')

}

</script>



<template>

  <div v-if="!ready" class="flex min-h-screen items-center justify-center bg-slate-50 dark:bg-slate-800/60 dark:bg-slate-950">

    <div class="h-10 w-10 animate-spin rounded-full border-4 border-teal-200 border-t-teal-600 dark:border-slate-700 dark:border-t-teal-400" />

  </div>



  <div v-else class="patient-shell flex min-h-screen">

    <aside class="patient-sidebar fixed inset-y-0 left-0 z-30 flex w-64 flex-col">

      <div class="border-b border-teal-50 dark:border-slate-700/80 px-6 py-5 dark:border-slate-700/80">

        <div class="flex items-center gap-3">

          <div class="flex h-10 w-10 items-center justify-center rounded-xl bg-teal-600 text-lg text-white dark:bg-teal-700">+</div>

          <div>

            <h1 class="font-display text-lg font-bold text-teal-900 dark:text-teal-100">SGHL Patient</h1>

            <p class="text-xs text-teal-600 dark:text-teal-400">CHU Brazzaville</p>

          </div>

        </div>

      </div>



      <nav class="flex-1 space-y-1 overflow-y-auto px-3 py-4">

        <router-link

          v-for="item in nav" :key="item.to" :to="item.to"

          class="flex items-center gap-3 rounded-xl px-4 py-2.5 text-sm font-medium transition"

          :class="route.path === item.to

            ? 'bg-teal-600 text-white shadow-lg shadow-teal-600/25 dark:bg-teal-700 dark:shadow-teal-900/40'

            : 'text-slate-600 dark:text-slate-400 hover:bg-teal-50 dark:bg-teal-950/40 hover:text-teal-700 dark:text-slate-300 dark:hover:bg-slate-800 dark:hover:text-teal-300'"

        >

          <span>{{ item.icon }}</span>{{ item.label }}

        </router-link>

      </nav>



      <div class="border-t border-teal-50 dark:border-slate-700/80 p-4 dark:border-slate-700/80">

        <div v-if="user" class="mb-3 rounded-xl bg-teal-50 dark:bg-teal-950/40 px-3 py-2 dark:bg-slate-800/80">

          <p class="text-sm font-semibold text-teal-900 dark:text-white">{{ user.first_name }} {{ user.last_name }}</p>

          <p class="text-xs text-teal-600 dark:text-teal-400">Espace sécurisé</p>

        </div>

        <ThemeToggle class="mb-3" />

        <button

          class="w-full rounded-xl border border-slate-200 dark:border-slate-600 py-2 text-sm text-slate-600 dark:text-slate-400 transition hover:border-red-200 hover:bg-red-50 dark:bg-red-950/40 hover:text-red-600 dark:text-red-400 dark:border-slate-600 dark:text-slate-300 dark:hover:border-red-500/50 dark:hover:bg-red-950/50 dark:hover:text-red-300"

          @click="logout"

        >

          Déconnexion

        </button>

      </div>

    </aside>



    <main class="ml-64 flex-1 p-8"><slot /></main>

  </div>

</template>


