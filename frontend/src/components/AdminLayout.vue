<script setup>

import { ref, onMounted } from 'vue'

import { useRouter, useRoute } from 'vue-router'

import { auth } from '../api/client'

import { clearSession } from '../utils/auth.js'

import ThemeToggle from './ThemeToggle.vue'



const router = useRouter()

const route = useRoute()

const user = ref(null)

const ready = ref(false)



const nav = [

  { to: '/admin', label: 'Statistiques', icon: '📊', exact: true },

  { to: '/admin/rendez-vous', label: 'Rendez-vous', icon: '📅' },

  { to: '/admin/medecins', label: 'Médecins', icon: '👨‍⚕️' },

  { to: '/admin/secretaires', label: 'Secrétaires', icon: '📋' },

  { to: '/admin/patients', label: 'Patients', icon: '👥' },

  { to: '/admin/utilisateurs', label: 'Utilisateurs', icon: '👤' },

  { to: '/admin/equipe', label: 'Équipe médicale', icon: '🩺' },

  { to: '/admin/services', label: 'Services médicaux', icon: '🏢' },

  { to: '/admin/urgences', label: 'Urgences', icon: '🚨' },

  { to: '/admin/infos', label: 'Infos pratiques', icon: 'ℹ️' },

  { to: '/admin/securite', label: 'Sécurité', icon: '🔒' },

  { to: '/admin/creer-compte', label: 'Créer un compte', icon: '➕' },

]



function isActive(item) {

  if (item.exact) return route.path === item.to

  return route.path === item.to || route.path.startsWith(item.to + '/')

}



onMounted(async () => {

  try {

    const { data } = await auth.me()

    if (data.role !== 'ADMIN') {

      router.replace('/')

      return

    }

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

  <div v-if="!ready" class="flex min-h-screen items-center justify-center bg-slate-900">

    <div class="text-center text-white">

      <div class="mx-auto mb-4 h-10 w-10 animate-spin rounded-full border-4 border-slate-600 border-t-amber-400" />

      <p class="text-sm text-slate-400 dark:text-slate-500">Chargement du panneau admin...</p>

    </div>

  </div>



  <div v-else class="flex min-h-screen bg-slate-900 dark:bg-slate-950">

    <aside class="fixed inset-y-0 left-0 z-30 flex w-64 flex-col border-r border-slate-700 bg-slate-800 dark:border-slate-800 dark:bg-slate-900">

      <div class="border-b border-slate-700 px-6 py-5 dark:border-slate-800">

        <div class="flex items-center gap-3">

          <div class="flex h-10 w-10 items-center justify-center rounded-xl bg-amber-50 dark:bg-amber-950/400 text-lg font-bold text-slate-900 dark:text-white">A</div>

          <div>

            <h1 class="font-display text-lg font-bold text-white">SGHL Admin</h1>

            <p class="text-xs text-slate-400 dark:text-slate-500">Administration</p>

          </div>

        </div>

      </div>



      <nav class="flex-1 overflow-y-auto px-3 py-4">

        <router-link

          v-for="item in nav"

          :key="item.to"

          :to="item.to"

          class="mb-0.5 flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition"

          :class="isActive(item) ? 'bg-amber-50 dark:bg-amber-950/400 text-slate-900 dark:text-white' : 'text-slate-300 hover:bg-slate-700 hover:text-white dark:hover:bg-slate-800'"

        >

          <span>{{ item.icon }}</span>

          <span class="truncate">{{ item.label }}</span>

        </router-link>

      </nav>



      <div class="border-t border-slate-700 p-4 dark:border-slate-800">

        <div v-if="user" class="mb-3 rounded-lg bg-slate-700/50 px-3 py-2 dark:bg-slate-800/80">

          <p class="text-sm font-semibold text-white">{{ user.first_name }} {{ user.last_name }}</p>

          <p class="text-xs text-amber-400">Administrateur</p>

        </div>

        <ThemeToggle class="mb-3" />

        <button

          class="w-full rounded-lg border border-slate-600 py-2 text-sm text-slate-300 hover:border-red-500 hover:bg-red-950 hover:text-red-300"

          @click="logout"

        >

          Déconnexion

        </button>

      </div>

    </aside>



    <main class="admin-main ml-64">

      <slot />

    </main>

  </div>

</template>


