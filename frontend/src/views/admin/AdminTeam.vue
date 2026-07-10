<script setup>

import { ref, onMounted } from 'vue'

import AdminLayout from '../../components/AdminLayout.vue'

import PaginationBar from '../../components/PaginationBar.vue'

import { adminApi } from '../../api/admin.js'

import { usePagination } from '../../composables/usePagination.js'



const team = ref([])

const filter = ref('')

const loading = ref(true)

const pagination = usePagination(12)



const roleLabels = {

  ADMIN: 'Administrateur', MEDECIN: 'Médecin', INFIRMIER: 'Infirmier(ère)',

  BIOLOGISTE: 'Biologiste', PHARMACIEN: 'Pharmacien', COMPTABLE: 'Comptable',

  RECEPTIONNISTE: 'Réceptionniste',

}



async function load() {

  loading.value = true

  try {

    const { data } = await adminApi.team(pagination.params({ role: filter.value || undefined }))

    team.value = data.items

    pagination.applyMeta(data)

  } finally {

    loading.value = false

  }

}



function onFilterChange() {

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

  <AdminLayout>

    <header class="mb-6 flex flex-wrap items-center justify-between gap-4">

      <div>

        <h1 class="font-display text-3xl font-bold text-slate-900 dark:text-white">Équipe médicale</h1>

        <p class="mt-1 text-slate-600 dark:text-slate-400">Personnel hospitalier par fonction</p>

      </div>

      <select v-model="filter" class="input-field w-48" @change="onFilterChange">

        <option value="">Tous les rôles</option>

        <option v-for="(label, key) in roleLabels" :key="key" :value="key">{{ label }}</option>

      </select>

    </header>



    <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">

      <div v-for="m in team" :key="m.id" class="flex items-center gap-4 rounded-xl bg-white dark:bg-slate-800 p-4 shadow-sm dark:shadow-none">

        <div class="h-11 w-[2.0625rem] shrink-0 overflow-hidden rounded-lg border border-slate-200 dark:border-slate-600" style="aspect-ratio:3/4">

          <img v-if="m.photo_url" :src="m.photo_url" class="h-full w-full object-cover" alt="" />

          <div v-else class="flex h-full items-center justify-center bg-slate-100 text-lg dark:bg-slate-800">

            {{ m.role === 'MEDECIN' ? '👨‍⚕️' : m.role === 'INFIRMIER' ? '💉' : '👤' }}

          </div>

        </div>

        <div class="min-w-0 flex-1">

          <p class="truncate font-semibold text-slate-800 dark:text-slate-100">{{ m.first_name }} {{ m.last_name }}</p>

          <p class="text-xs text-primary-600 dark:text-primary-400">{{ roleLabels[m.role] }}</p>

          <p v-if="m.specialty" class="truncate text-xs text-slate-400 dark:text-slate-500">{{ m.specialty }}</p>

        </div>

      </div>

    </div>



    <div v-if="!loading && !team.length" class="mt-4 rounded-xl bg-white py-12 text-center text-slate-400 dark:bg-slate-800">

      Aucun membre trouvé

    </div>



    <div class="mt-4 overflow-hidden rounded-2xl bg-white shadow-sm dark:bg-slate-800 dark:shadow-none">

      <PaginationBar

        :page="pagination.page.value"

        :page-size="pagination.pageSize.value"

        :total="pagination.total.value"

        :total-pages="pagination.totalPages.value"

        :size-options="[6, 12, 18, 24]"

        @update:page="onPageChange"

        @update:page-size="onPageSizeChange"

      />

    </div>

  </AdminLayout>

</template>

