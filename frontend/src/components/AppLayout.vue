<script setup>

import { ref, onMounted, computed } from 'vue'

import { useRouter, useRoute } from 'vue-router'

import { auth, getRole } from '../api/client'

import { clearSession } from '../utils/auth.js'

import ThemeToggle from './ThemeToggle.vue'



const router = useRouter()

const route = useRoute()

const user = ref(null)

const ready = ref(false)

const role = computed(() => getRole())



const allNav = [

  { to: '/', label: 'Tableau de bord', icon: '📊', roles: ['*'] },

  { to: '/soins-infirmiers', label: 'Soins infirmiers', icon: '💉', roles: ['INFIRMIER', 'ADMIN'] },

  { to: '/rendez-vous', label: 'Rendez-vous', icon: '📅', roles: ['ADMIN', 'RECEPTIONNISTE'] },

  { to: '/laboratoire', label: 'Laboratoire', icon: '🔬', roles: ['ADMIN', 'MEDECIN', 'BIOLOGISTE', 'INFIRMIER', 'PHARMACIEN', 'COMPTABLE', 'RECEPTIONNISTE'] },

  { to: '/medecins', label: 'Médecins', icon: '👨‍⚕️', roles: ['ADMIN', 'RECEPTIONNISTE', 'MEDECIN'] },

  { to: '/patients', label: 'Patients', icon: '👥', roles: ['ADMIN', 'MEDECIN', 'INFIRMIER', 'RECEPTIONNISTE'] },

  { to: '/hospitalisation', label: 'Hospitalisation', icon: '🏥', roles: ['ADMIN', 'MEDECIN', 'RECEPTIONNISTE', 'INFIRMIER'] },

  { to: '/pharmacie', label: 'Pharmacie', icon: '💊', roles: ['ADMIN', 'PHARMACIEN', 'MEDECIN', 'INFIRMIER', 'RECEPTIONNISTE', 'COMPTABLE', 'BIOLOGISTE'] },

  { to: '/facturation', label: 'Facturation', icon: '💰', roles: ['ADMIN', 'COMPTABLE', 'RECEPTIONNISTE'] },

  { to: '/planning-gardes', label: 'Planning gardes', icon: '📋', roles: ['ADMIN', 'MEDECIN', 'INFIRMIER'] },

  { to: '/admin', label: 'Panneau Admin', icon: '⚙️', roles: ['ADMIN'] },

]



const nav = computed(() =>

  allNav.filter((item) =>

    item.roles.includes('*') || item.roles.includes(role.value) || role.value === 'ADMIN',

  ),

)



onMounted(async () => {

  try {

    const { data } = await auth.me()

    user.value = data

    localStorage.setItem('role', data.role)

    ready.value = true

  } catch {

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

    <div class="text-center">

      <div class="mx-auto mb-4 h-10 w-10 animate-spin rounded-full border-4 border-primary-200 border-t-primary-600 dark:border-slate-700 dark:border-t-primary-400" />

      <p class="text-sm text-slate-500 dark:text-slate-400">Chargement...</p>

    </div>

  </div>



  <div v-else class="app-shell flex min-h-screen">

    <aside class="app-sidebar fixed inset-y-0 left-0 z-30 flex w-64 flex-col">

      <div class="flex items-center gap-3 border-b border-slate-100 dark:border-slate-700 px-6 py-5 dark:border-slate-700/80">

        <div class="flex h-10 w-10 items-center justify-center rounded-xl bg-primary-600 text-lg text-white shadow-glow dark:shadow-glow-dark">+</div>

        <div>

          <h1 class="font-display text-lg font-bold text-primary-900 dark:text-primary-100">SGHL</h1>

          <p class="text-xs text-slate-500 dark:text-slate-400">ERP Médical</p>

        </div>

      </div>

      <nav class="flex-1 space-y-1 overflow-y-auto px-3 py-4">

        <router-link

          v-for="item in nav" :key="item.to" :to="item.to"

          class="flex items-center gap-3 rounded-xl px-4 py-2.5 text-sm font-medium transition"

          :class="(route.path === item.to || (item.to === '/' && route.path === '/'))

            ? 'bg-primary-600 text-white shadow-lg shadow-primary-600/30 dark:shadow-primary-900/50'

            : 'text-slate-600 dark:text-slate-400 hover:bg-primary-50 dark:hover:bg-slate-800 dark:bg-primary-950/40 hover:text-primary-700 dark:text-primary-300 dark:text-slate-300 dark:hover:bg-slate-800 dark:hover:text-primary-300'"

        >

          <span>{{ item.icon }}</span>{{ item.label }}

        </router-link>

      </nav>

      <div class="border-t border-slate-100 dark:border-slate-700 p-4 dark:border-slate-700/80">

        <div v-if="user" class="mb-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 px-3 py-2 dark:bg-slate-800/80">

          <p class="text-sm font-semibold text-slate-900 dark:text-white">{{ user.first_name }} {{ user.last_name }}</p>

          <p class="text-xs text-primary-600 dark:text-primary-400">{{ user.role }}</p>

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


