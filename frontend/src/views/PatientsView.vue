<script setup>

import { ref, onMounted } from 'vue'

import AppLayout from '../components/AppLayout.vue'

import PaginationBar from '../components/PaginationBar.vue'

import { patients } from '../api/client'

import { usePagination } from '../composables/usePagination.js'



const list = ref([])

const search = ref('')

const loading = ref(true)

const pagination = usePagination(15)



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



onMounted(load)

</script>



<template>

  <AppLayout>

    <header class="mb-8 flex flex-wrap items-center justify-between gap-4">

      <div>

        <h1 class="font-display text-3xl font-bold text-slate-900 dark:text-white">Patients</h1>

        <p class="mt-1 text-slate-500 dark:text-slate-400">Dossiers patients — confidentialité stricte</p>

      </div>

      <div class="flex gap-2">

        <input

          v-model="search"

          type="search"

          placeholder="Rechercher..."

          class="input-field w-64"

          @keyup.enter="onSearch"

        />

        <button class="btn-primary" @click="onSearch">Rechercher</button>

      </div>

    </header>



    <div class="card overflow-hidden p-0">

      <table class="w-full text-sm">

        <thead class="border-b border-slate-100 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/60/80">

          <tr>

            <th class="px-6 py-3 text-left font-semibold text-slate-600 dark:text-slate-400">N° Dossier</th>

            <th class="px-6 py-3 text-left font-semibold text-slate-600 dark:text-slate-400">Nom</th>

            <th class="px-6 py-3 text-left font-semibold text-slate-600 dark:text-slate-400">Prénom</th>

            <th class="px-6 py-3 text-left font-semibold text-slate-600 dark:text-slate-400">Naissance</th>

            <th class="px-6 py-3 text-left font-semibold text-slate-600 dark:text-slate-400">Groupe</th>

          </tr>

        </thead>

        <tbody>

          <tr v-if="loading">

            <td colspan="5" class="px-6 py-12 text-center text-slate-400 dark:text-slate-500">Chargement...</td>

          </tr>

          <tr v-else-if="!list.length">

            <td colspan="5" class="px-6 py-12 text-center text-slate-400 dark:text-slate-500">Aucun patient</td>

          </tr>

          <tr

            v-for="p in list"

            :key="p.id"

            class="border-b border-slate-50 transition hover:bg-primary-50 dark:hover:bg-slate-800 dark:bg-primary-950/40/30"

          >

            <td class="px-6 py-3 font-mono text-xs text-primary-700 dark:text-primary-300">{{ p.numero_dossier }}</td>

            <td class="px-6 py-3 font-medium">{{ p.nom }}</td>

            <td class="px-6 py-3">{{ p.prenom }}</td>

            <td class="px-6 py-3 text-slate-500 dark:text-slate-400">{{ p.date_naissance }}</td>

            <td class="px-6 py-3">

              <span v-if="p.groupe_sanguin" class="rounded-full bg-red-50 dark:bg-red-950/40 px-2 py-0.5 text-xs text-red-700 dark:text-red-300">

                {{ p.groupe_sanguin }}

              </span>

              <span v-else class="text-slate-300">—</span>

            </td>

          </tr>

        </tbody>

      </table>

      <PaginationBar

        :page="pagination.page.value"

        :page-size="pagination.pageSize.value"

        :total="pagination.total.value"

        :total-pages="pagination.totalPages.value"

        :size-options="[10, 15, 20, 30]"

        @update:page="onPageChange"

        @update:page-size="onPageSizeChange"

      />

    </div>

  </AppLayout>

</template>

