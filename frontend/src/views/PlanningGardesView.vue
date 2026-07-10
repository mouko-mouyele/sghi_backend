<script setup>
import { ref, onMounted, computed } from 'vue'
import AppLayout from '../components/AppLayout.vue'
import { hr, getRole } from '../api/client'
import { adminApi } from '../api/admin.js'
import { parseApiError } from '../utils/errors.js'

const shifts = ref([])
const services = ref([])
const team = ref([])
const loading = ref(true)
const showForm = ref(false)
const message = ref('')
const errorMsg = ref('')
const filterService = ref('')

const isAdmin = computed(() => getRole() === 'ADMIN')

const form = ref({
  personnel_id: '',
  service_id: '',
  date_debut: '',
  date_fin: '',
  type_garde: 'JOUR',
  notes: '',
})

const gardeTypes = [
  { value: 'JOUR', label: 'Jour' },
  { value: 'NUIT', label: 'Nuit' },
  { value: 'ASTREINTE', label: 'Astreinte' },
]

function gardeLabel(t) {
  return gardeTypes.find((g) => g.value === t)?.label || t
}

function gardeClass(t) {
  return {
    JOUR: 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300',
    NUIT: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900/40 dark:text-indigo-300',
    ASTREINTE: 'bg-rose-100 text-rose-800 dark:bg-rose-900/40 dark:text-rose-300',
  }[t] || 'bg-slate-100 text-slate-600'
}

function fmt(d) {
  if (!d) return '—'
  return new Date(d).toLocaleString('fr-FR', {
    weekday: 'short', day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit',
  })
}

function toLocalInput(iso) {
  if (!iso) return ''
  const dt = new Date(iso)
  const pad = (n) => String(n).padStart(2, '0')
  return `${dt.getFullYear()}-${pad(dt.getMonth() + 1)}-${pad(dt.getDate())}T${pad(dt.getHours())}:${pad(dt.getMinutes())}`
}

async function loadShifts() {
  loading.value = true
  errorMsg.value = ''
  try {
    const params = filterService.value ? { service_id: filterService.value } : {}
    const { data } = await hr.shifts(params)
    shifts.value = data
  } catch (e) {
    errorMsg.value = parseApiError(e)
  } finally {
    loading.value = false
  }
}

async function loadMeta() {
  if (isAdmin.value) {
    try {
      const [svcRes, teamRes] = await Promise.all([
        adminApi.services(),
        adminApi.team({ page_size: 100 }),
      ])
      services.value = svcRes.data
      team.value = (teamRes.data.items || []).filter((m) => ['MEDECIN', 'INFIRMIER', 'PHARMACIEN'].includes(m.role))
    } catch {
      /* lecture seule si échec */
    }
  }
}

function openForm() {
  const start = new Date()
  start.setMinutes(0, 0, 0)
  const end = new Date(start.getTime() + 12 * 3600000)
  form.value = {
    personnel_id: team.value[0]?.id || '',
    service_id: services.value[0]?.id || '',
    date_debut: toLocalInput(start.toISOString()),
    date_fin: toLocalInput(end.toISOString()),
    type_garde: 'JOUR',
    notes: '',
  }
  showForm.value = true
}

async function submitForm() {
  message.value = ''
  errorMsg.value = ''
  try {
    await hr.createShift({
      personnel_id: Number(form.value.personnel_id),
      service_id: Number(form.value.service_id),
      date_debut: new Date(form.value.date_debut).toISOString(),
      date_fin: new Date(form.value.date_fin).toISOString(),
      type_garde: form.value.type_garde,
      notes: form.value.notes,
    })
    showForm.value = false
    message.value = 'Garde planifiée avec succès.'
    await loadShifts()
  } catch (e) {
    errorMsg.value = parseApiError(e)
  }
}

onMounted(async () => {
  await loadMeta()
  await loadShifts()
})
</script>

<template>
  <AppLayout>
    <header class="mb-8 flex flex-wrap items-start justify-between gap-4">
      <div>
        <h1 class="font-display text-3xl font-bold text-slate-900 dark:text-white">Planning de gardes</h1>
        <p class="mt-1 text-slate-600 dark:text-slate-400">RH — plannings par service et type de garde</p>
      </div>
      <button v-if="isAdmin" type="button" class="btn-primary" @click="openForm">+ Nouvelle garde</button>
    </header>

    <div v-if="message" class="mb-4 rounded-xl bg-emerald-50 px-4 py-3 text-sm text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300">{{ message }}</div>
    <div v-if="errorMsg" class="mb-4 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-600 dark:bg-red-950/40 dark:text-red-400">{{ errorMsg }}</div>

    <div class="mb-6 flex flex-wrap items-end gap-4">
      <div>
        <label class="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">Filtrer par service</label>
        <select v-model="filterService" class="input-field min-w-[220px]" @change="loadShifts">
          <option value="">Tous les services</option>
          <option v-for="s in services" :key="s.id" :value="s.id">{{ s.nom }} ({{ s.code }})</option>
        </select>
      </div>
    </div>

    <div v-if="loading" class="py-12 text-center text-slate-500">Chargement...</div>

    <div v-else class="overflow-hidden rounded-2xl bg-white shadow-sm dark:bg-slate-800">
      <table class="w-full text-sm">
        <thead class="bg-slate-50 dark:bg-slate-800/60">
          <tr>
            <th class="px-4 py-3 text-left">Personnel</th>
            <th class="px-4 py-3 text-left">Service</th>
            <th class="px-4 py-3 text-left">Type</th>
            <th class="px-4 py-3 text-left">Début</th>
            <th class="px-4 py-3 text-left">Fin</th>
            <th class="px-4 py-3 text-left">Notes</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="!shifts.length">
            <td colspan="6" class="px-4 py-8 text-center text-slate-500">Aucune garde planifiée.</td>
          </tr>
          <tr v-for="g in shifts" :key="g.id" class="border-t border-slate-100 dark:border-slate-700">
            <td class="px-4 py-3 font-medium">{{ g.personnel_nom || `#${g.personnel_id}` }}</td>
            <td class="px-4 py-3">{{ g.service_nom }} <span class="text-slate-400">({{ g.service_code }})</span></td>
            <td class="px-4 py-3">
              <span class="rounded-full px-2.5 py-0.5 text-xs font-medium" :class="gardeClass(g.type_garde)">{{ gardeLabel(g.type_garde) }}</span>
            </td>
            <td class="px-4 py-3 text-slate-600 dark:text-slate-400">{{ fmt(g.date_debut) }}</td>
            <td class="px-4 py-3 text-slate-600 dark:text-slate-400">{{ fmt(g.date_fin) }}</td>
            <td class="px-4 py-3 text-slate-500">{{ g.notes || '—' }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="showForm" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" @click.self="showForm = false">
      <form class="w-full max-w-lg rounded-2xl bg-white p-6 shadow-xl dark:bg-slate-800" @submit.prevent="submitForm">
        <h2 class="font-display text-xl font-bold text-slate-900 dark:text-white">Planifier une garde</h2>
        <div class="mt-4 space-y-4">
          <div>
            <label class="mb-1 block text-sm font-medium">Personnel</label>
            <select v-model="form.personnel_id" class="input-field" required>
              <option v-for="m in team" :key="m.id" :value="m.id">{{ m.first_name }} {{ m.last_name }} — {{ m.role }}</option>
            </select>
          </div>
          <div>
            <label class="mb-1 block text-sm font-medium">Service</label>
            <select v-model="form.service_id" class="input-field" required>
              <option v-for="s in services" :key="s.id" :value="s.id">{{ s.nom }}</option>
            </select>
          </div>
          <div class="grid gap-4 sm:grid-cols-2">
            <div>
              <label class="mb-1 block text-sm font-medium">Début</label>
              <input v-model="form.date_debut" type="datetime-local" class="input-field" required />
            </div>
            <div>
              <label class="mb-1 block text-sm font-medium">Fin</label>
              <input v-model="form.date_fin" type="datetime-local" class="input-field" required />
            </div>
          </div>
          <div>
            <label class="mb-1 block text-sm font-medium">Type de garde</label>
            <select v-model="form.type_garde" class="input-field">
              <option v-for="t in gardeTypes" :key="t.value" :value="t.value">{{ t.label }}</option>
            </select>
          </div>
          <div>
            <label class="mb-1 block text-sm font-medium">Notes</label>
            <textarea v-model="form.notes" class="input-field" rows="2" />
          </div>
        </div>
        <div class="mt-6 flex justify-end gap-3">
          <button type="button" class="rounded-xl border px-4 py-2 text-sm" @click="showForm = false">Annuler</button>
          <button type="submit" class="btn-primary">Enregistrer</button>
        </div>
      </form>
    </div>
  </AppLayout>
</template>
