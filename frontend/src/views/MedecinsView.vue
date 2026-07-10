<script setup>

import { ref, onMounted } from 'vue'

import AppLayout from '../components/AppLayout.vue'

import PaginationBar from '../components/PaginationBar.vue'

import { medecins as medecinsApi } from '../api/client'

import { parseApiError } from '../utils/errors.js'

import { usePagination } from '../composables/usePagination.js'



const list = ref([])

const loading = ref(true)

const filter = ref('')

const toast = ref('')

const disponibles = ref(0)

const indisponibles = ref(0)

const pagination = usePagination(12)

let searchTimer = null



async function load() {

  loading.value = true

  try {

    const { data } = await medecinsApi.list(pagination.params({ search: filter.value.trim() }))

    list.value = data.items

    pagination.applyMeta(data)

    disponibles.value = data.disponibles_total ?? 0

    indisponibles.value = data.indisponibles_total ?? 0

  } finally {

    loading.value = false

  }

}



function onSearchInput() {

  clearTimeout(searchTimer)

  searchTimer = setTimeout(() => {

    pagination.resetPage()

    load()

  }, 350)

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



async function toggleDispo(m) {

  try {

    await medecinsApi.setDisponibilite(m.id, !m.disponible_rdv)

    m.disponible_rdv = !m.disponible_rdv

    toast.value = m.disponible_rdv

      ? `Dr ${m.last_name} — disponible pour les RDV`

      : `Dr ${m.last_name} — marqué indisponible`

    setTimeout(() => { toast.value = '' }, 3500)

    load()

  } catch (e) {

    toast.value = parseApiError(e)

  }

}



onMounted(load)

</script>



<template>

  <AppLayout>

    <header class="relative mb-8 overflow-hidden rounded-3xl bg-gradient-to-br from-sky-800 via-primary-800 to-indigo-900 p-8 text-white">

      <div class="relative flex flex-wrap items-start justify-between gap-4">

        <div>

          <p class="mb-2 text-sm text-sky-200">Accueil · Planning médical</p>

          <h1 class="font-display text-3xl font-bold">Équipe médicale</h1>

          <p class="mt-2 max-w-lg text-sky-100">

            Consultez tous les médecins et configurez leur disponibilité pour les rendez-vous

          </p>

        </div>

        <div class="flex gap-4">

          <div class="rounded-2xl bg-white/10 px-5 py-3 text-center backdrop-blur">

            <p class="text-2xl font-bold text-emerald-300">{{ disponibles }}</p>

            <p class="text-xs text-sky-200">Disponibles</p>

          </div>

          <div class="rounded-2xl bg-white/10 px-5 py-3 text-center backdrop-blur">

            <p class="text-2xl font-bold text-amber-300">{{ indisponibles }}</p>

            <p class="text-xs text-sky-200">Indisponibles</p>

          </div>

        </div>

      </div>

    </header>



    <div v-if="toast" class="mb-4 rounded-xl bg-emerald-50 px-4 py-3 text-sm text-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-200">

      {{ toast }}

    </div>



    <div class="mb-6 flex flex-wrap items-center gap-3">

      <div class="relative min-w-[240px] flex-1 sm:max-w-sm">

        <span class="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400">🔍</span>

        <input v-model="filter" class="input-field pl-10" placeholder="Rechercher un médecin..." @input="onSearchInput" />

      </div>

      <button class="text-sm font-medium text-primary-600 hover:underline dark:text-primary-400" @click="load">

        ↻ Actualiser

      </button>

    </div>



    <div v-if="loading" class="flex h-48 items-center justify-center">

      <div class="h-10 w-10 animate-spin rounded-full border-4 border-primary-200 border-t-primary-600 dark:border-slate-700 dark:border-t-primary-400" />

    </div>



    <template v-else>

      <div class="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">

        <article

          v-for="m in list"

          :key="m.id"

          class="card flex gap-4 p-5 transition hover:shadow-lg"

          :class="m.disponible_rdv ? 'ring-1 ring-emerald-200 dark:ring-emerald-900/50' : 'opacity-90 ring-1 ring-amber-200 dark:ring-amber-900/40'"

        >

          <div class="shrink-0">

            <div

              class="h-24 w-[4.5rem] overflow-hidden rounded-xl border-2 bg-slate-100 shadow-inner dark:border-slate-600 dark:bg-slate-900"

              style="aspect-ratio: 3/4"

            >

              <img

                v-if="m.photo_url"

                :src="m.photo_url"

                :alt="m.first_name"

                class="h-full w-full object-cover"

              />

              <div v-else class="flex h-full items-center justify-center text-2xl text-slate-400">👨‍⚕️</div>

            </div>

          </div>



          <div class="min-w-0 flex-1">

            <h3 class="font-display font-bold text-slate-900 dark:text-white">

              Dr {{ m.first_name }} {{ m.last_name }}

            </h3>

            <p class="text-sm text-primary-600 dark:text-primary-400">{{ m.specialty || 'Médecine générale' }}</p>

            <p v-if="m.phone" class="mt-1 text-xs text-slate-500 dark:text-slate-400">📞 {{ m.phone }}</p>



            <div class="mt-4 flex items-center justify-between gap-2">

              <span

                class="rounded-full px-2.5 py-0.5 text-xs font-semibold"

                :class="m.disponible_rdv

                  ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300'

                  : 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300'"

              >

                {{ m.disponible_rdv ? '● Disponible' : '○ Indisponible' }}

              </span>

              <button

                type="button"

                class="rounded-xl px-3 py-1.5 text-xs font-semibold transition"

                :class="m.disponible_rdv

                  ? 'bg-amber-100 text-amber-800 hover:bg-amber-200 dark:bg-amber-900/40 dark:text-amber-200'

                  : 'bg-emerald-600 text-white hover:bg-emerald-700'"

                @click="toggleDispo(m)"

              >

                {{ m.disponible_rdv ? 'Marquer absent' : 'Rendre disponible' }}

              </button>

            </div>

          </div>

        </article>

      </div>



      <div v-if="!list.length" class="card py-12 text-center text-slate-400">Aucun médecin trouvé</div>



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

    </template>

  </AppLayout>

</template>

