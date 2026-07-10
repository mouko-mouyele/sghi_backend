<script setup>

import { ref, onMounted } from 'vue'

import AdminLayout from '../../components/AdminLayout.vue'

import PaginationBar from '../../components/PaginationBar.vue'

import { auth } from '../../api/client.js'

import { adminApi } from '../../api/admin.js'

import { usePagination } from '../../composables/usePagination.js'



const users = ref([])

const journal = ref([])

const filter = ref('')

const usersPagination = usePagination(10)

const journalPagination = usePagination(15)



const roleLabels = {

  ADMIN: 'Administrateur', MEDECIN: 'Médecin', INFIRMIER: 'Infirmier(ère)',

  BIOLOGISTE: 'Biologiste', PHARMACIEN: 'Pharmacien', COMPTABLE: 'Comptable',

  RECEPTIONNISTE: 'Réceptionniste', PATIENT: 'Patient',

}



async function deactivateUser(id, username) {

  if (!confirm(`Désactiver le compte "${username}" ?`)) return

  try {

    await adminApi.deactivateUser(id)

    await loadUsers()

  } catch (e) {

    alert(e.response?.data?.detail || 'Erreur')

  }

}



async function loadUsers() {

  const { data } = await auth.listUsers(usersPagination.params({ role: filter.value || undefined }))

  users.value = data.items

  usersPagination.applyMeta(data)

}



async function loadJournal() {

  const { data } = await adminApi.loginJournal(journalPagination.params())

  journal.value = data.items

  journalPagination.applyMeta(data)

}



function onFilterChange() {

  usersPagination.resetPage()

  loadUsers()

}



function onUsersPageChange(p) {

  usersPagination.page.value = p

  loadUsers()

}



function onUsersPageSizeChange(size) {

  usersPagination.pageSize.value = size

  usersPagination.page.value = 1

  loadUsers()

}



function onJournalPageChange(p) {

  journalPagination.page.value = p

  loadJournal()

}



function onJournalPageSizeChange(size) {

  journalPagination.pageSize.value = size

  journalPagination.page.value = 1

  loadJournal()

}



onMounted(async () => {

  await Promise.all([loadUsers(), loadJournal()])

})

</script>



<template>

  <AdminLayout>

    <header class="mb-6 flex flex-wrap items-center justify-between gap-4">

      <div>

        <h1 class="font-display text-3xl font-bold text-slate-900 dark:text-white">Gestion des utilisateurs</h1>

        <p class="mt-1 text-slate-600 dark:text-slate-400">Comptes, rôles RBAC et journal de connexion</p>

      </div>

      <div class="flex gap-2">

        <select v-model="filter" class="input-field w-44" @change="onFilterChange">

          <option value="">Tous les rôles</option>

          <option v-for="(label, key) in roleLabels" :key="key" :value="key">{{ label }}</option>

        </select>

        <router-link to="/admin/creer-compte" class="btn-primary">+ Créer un compte</router-link>

      </div>

    </header>



    <div class="mb-8 overflow-hidden rounded-2xl bg-white dark:bg-slate-800 shadow-sm dark:shadow-none">

      <div class="border-b px-4 py-3 font-semibold text-slate-700 dark:text-slate-300">Utilisateurs actifs</div>

      <table class="w-full text-sm">

        <thead class="bg-slate-50 dark:bg-slate-800/60">

          <tr>

            <th class="px-4 py-3 text-left">Identifiant</th>

            <th class="px-4 py-3 text-left">Nom</th>

            <th class="px-4 py-3 text-left">Email</th>

            <th class="px-4 py-3 text-left">Rôle</th>

            <th class="px-4 py-3 text-left">Actions</th>

          </tr>

        </thead>

        <tbody>

          <tr v-for="u in users" :key="u.id" class="border-t hover:bg-slate-50 dark:hover:bg-slate-800/50 dark:bg-slate-800/60">

            <td class="px-4 py-3 font-medium">{{ u.username }}</td>

            <td class="px-4 py-3">{{ u.first_name }} {{ u.last_name }}</td>

            <td class="px-4 py-3 text-slate-500 dark:text-slate-400">{{ u.email }}</td>

            <td class="px-4 py-3">

              <span class="rounded-full bg-amber-100 px-2 py-0.5 text-xs text-amber-800 dark:text-amber-200">{{ roleLabels[u.role] || u.role }}</span>

            </td>

            <td class="px-4 py-3">

              <button

                class="rounded bg-red-50 dark:bg-red-950/40 px-2 py-1 text-xs text-red-600 dark:text-red-400 hover:bg-red-100"

                @click="deactivateUser(u.id, u.username)"

              >

                Désactiver

              </button>

            </td>

          </tr>

          <tr v-if="!users.length">

            <td colspan="5" class="px-4 py-8 text-center text-slate-400">Aucun utilisateur</td>

          </tr>

        </tbody>

      </table>

      <PaginationBar

        :page="usersPagination.page.value"

        :page-size="usersPagination.pageSize.value"

        :total="usersPagination.total.value"

        :total-pages="usersPagination.totalPages.value"

        @update:page="onUsersPageChange"

        @update:page-size="onUsersPageSizeChange"

      />

    </div>



    <div class="overflow-hidden rounded-2xl bg-white dark:bg-slate-800 shadow-sm dark:shadow-none">

      <div class="border-b px-4 py-3 font-semibold text-slate-700 dark:text-slate-300">Journal des connexions</div>

      <table class="w-full text-sm">

        <thead class="bg-slate-50 dark:bg-slate-800/60">

          <tr>

            <th class="px-4 py-3 text-left">Utilisateur</th>

            <th class="px-4 py-3 text-left">IP</th>

            <th class="px-4 py-3 text-left">Statut</th>

            <th class="px-4 py-3 text-left">Date</th>

          </tr>

        </thead>

        <tbody>

          <tr v-for="(j, i) in journal" :key="i" class="border-t">

            <td class="px-4 py-3">{{ j.user__username || '—' }}</td>

            <td class="px-4 py-3 font-mono text-xs">{{ j.ip_address || '—' }}</td>

            <td class="px-4 py-3">

              <span :class="j.success ? 'bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-300' : 'bg-red-100 text-red-700 dark:text-red-300'" class="rounded-full px-2 py-0.5 text-xs">

                {{ j.success ? 'Réussi' : 'Échec' }}

              </span>

            </td>

            <td class="px-4 py-3 text-slate-500 dark:text-slate-400">{{ j.timestamp?.slice(0, 19).replace('T', ' ') }}</td>

          </tr>

        </tbody>

      </table>

      <PaginationBar

        :page="journalPagination.page.value"

        :page-size="journalPagination.pageSize.value"

        :total="journalPagination.total.value"

        :total-pages="journalPagination.totalPages.value"

        :size-options="[10, 15, 25, 50]"

        @update:page="onJournalPageChange"

        @update:page-size="onJournalPageSizeChange"

      />

    </div>

  </AdminLayout>

</template>

