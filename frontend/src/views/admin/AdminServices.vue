<script setup>
import { ref, onMounted } from 'vue'
import AdminLayout from '../../components/AdminLayout.vue'
import { adminApi } from '../../api/admin.js'

const services = ref([])
const loading = ref(true)
const showForm = ref(false)
const form = ref({ code: '', nom: '', building_id: 1 })
const message = ref('')

async function load() {
  loading.value = true
  try {
    const { data } = await adminApi.services()
    services.value = data
  } finally {
    loading.value = false
  }
}

async function createService() {
  try {
    await adminApi.createService(form.value)
    message.value = 'Service créé'
    showForm.value = false
    load()
  } catch (e) {
    message.value = e.response?.data?.detail || 'Erreur'
  }
}

onMounted(load)
</script>

<template>
  <AdminLayout>
    <header class="mb-6 flex flex-wrap items-center justify-between gap-4">
      <div>
        <h1 class="font-display text-3xl font-bold text-slate-900 dark:text-white">Services médicaux</h1>
        <p class="mt-1 text-slate-600 dark:text-slate-400">Structure hospitalière : bâtiments, services, lits</p>
      </div>
      <button class="btn-primary" @click="showForm = !showForm">+ Nouveau service</button>
    </header>

    <div v-if="showForm" class="mb-6 flex gap-3 rounded-2xl bg-white dark:bg-slate-800 p-4 shadow-sm dark:shadow-none">
      <input v-model="form.code" class="input-field w-24" placeholder="Code" />
      <input v-model="form.nom" v-input-filter="'text'" class="input-field flex-1" placeholder="Nom du service" />
      <button class="btn-primary" @click="createService">Créer</button>
    </div>
    <p v-if="message" class="mb-4 text-sm text-emerald-600">{{ message }}</p>

    <div class="grid gap-4 sm:grid-cols-2">
      <div v-for="s in services" :key="s.id" class="rounded-2xl bg-white dark:bg-slate-800 p-5 shadow-sm dark:shadow-none">
        <div class="flex items-start justify-between">
          <div>
            <span class="rounded bg-primary-100 dark:bg-primary-900/40 px-2 py-0.5 font-mono text-xs text-primary-800">{{ s.code }}</span>
            <h3 class="mt-2 font-semibold text-slate-800 dark:text-slate-100">{{ s.nom }}</h3>
            <p class="text-sm text-slate-500 dark:text-slate-400">{{ s.building }}</p>
          </div>
          <span v-if="s.hospitalisations_actives" class="rounded-full bg-red-100 px-2 py-0.5 text-xs text-red-700 dark:text-red-300">
            {{ s.hospitalisations_actives }} hosp.
          </span>
        </div>
        <div class="mt-4 grid grid-cols-3 gap-2 text-center text-sm">
          <div class="rounded-lg bg-slate-50 dark:bg-slate-800/60 p-2">
            <p class="font-bold text-slate-800 dark:text-slate-100">{{ s.chambres }}</p>
            <p class="text-xs text-slate-500 dark:text-slate-400">Chambres</p>
          </div>
          <div class="rounded-lg bg-slate-50 dark:bg-slate-800/60 p-2">
            <p class="font-bold text-slate-800 dark:text-slate-100">{{ s.lits_total }}</p>
            <p class="text-xs text-slate-500 dark:text-slate-400">Lits</p>
          </div>
          <div class="rounded-lg bg-emerald-50 dark:bg-emerald-950/40 p-2">
            <p class="font-bold text-emerald-700 dark:text-emerald-300">{{ s.lits_disponibles }}</p>
            <p class="text-xs text-slate-500 dark:text-slate-400">Disponibles</p>
          </div>
        </div>
      </div>
    </div>
  </AdminLayout>
</template>
