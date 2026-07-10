<script setup>
import { ref, onMounted } from 'vue'
import AdminLayout from '../../components/AdminLayout.vue'
import StatCard from '../../components/StatCard.vue'
import ProfilePhotoUpload from '../../components/ProfilePhotoUpload.vue'
import { adminApi } from '../../api/admin.js'
import { auth } from '../../api/client.js'
import { parseApiError } from '../../utils/errors.js'

const stats = ref(null)
const adminProfile = ref(null)
const loading = ref(true)
const exporting = ref(false)
const photoMsg = ref('')

async function exportPdf() {
  exporting.value = true
  try {
    await adminApi.exportStatsPdf()
  } catch {
    alert('Erreur lors de l\'export PDF')
  } finally {
    exporting.value = false
  }
}

const quickLinks = [
  { to: '/admin/rendez-vous', label: 'Rendez-vous', icon: '📅' },
  { to: '/admin/medecins', label: 'Médecins', icon: '👨‍⚕️' },
  { to: '/admin/secretaires', label: 'Secrétaires', icon: '📋' },
  { to: '/admin/patients', label: 'Patients', icon: '👥' },
  { to: '/admin/utilisateurs', label: 'Utilisateurs', icon: '👤' },
  { to: '/admin/equipe', label: 'Équipe médicale', icon: '🩺' },
  { to: '/admin/services', label: 'Services', icon: '🏢' },
  { to: '/admin/urgences', label: 'Urgences', icon: '🚨' },
  { to: '/admin/infos', label: 'Infos pratiques', icon: 'ℹ️' },
]

onMounted(async () => {
  try {
    const [s, me] = await Promise.all([adminApi.stats(), auth.me()])
    stats.value = s.data
    adminProfile.value = me.data
  } finally {
    loading.value = false
  }
})

async function uploadAdminPhoto(file) {
  try {
    const { data } = await auth.uploadMyPhoto(file)
    adminProfile.value = { ...adminProfile.value, photo_url: data.photo_url }
    photoMsg.value = 'Votre photo d\'identité a été enregistrée'
  } catch (e) {
    photoMsg.value = parseApiError(e, 'Erreur photo')
  }
}
</script>

<template>
  <AdminLayout>
    <header class="mb-8 flex flex-wrap items-start justify-between gap-4">
      <div>
        <h1 class="font-display text-3xl font-bold text-slate-900 dark:text-white">Tableau de bord administrateur</h1>
        <p class="mt-1 text-slate-600 dark:text-slate-400">Statistiques et accès rapide à la gestion de l'établissement</p>
      </div>
      <button
        class="inline-flex items-center gap-2 rounded-xl border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-800 px-4 py-2 text-sm font-medium shadow-sm dark:shadow-none hover:bg-slate-50 dark:hover:bg-slate-800/50 dark:bg-slate-800/60"
        :disabled="exporting || loading"
        @click="exportPdf"
      >
        📄 {{ exporting ? 'Export...' : 'Exporter PDF' }}
      </button>
    </header>

    <div v-if="adminProfile" class="card mb-8 flex flex-wrap items-center gap-8 border-amber-200/60 bg-gradient-to-r from-amber-50/80 to-white dark:from-slate-800 dark:to-slate-900 dark:border-amber-900/40">
      <ProfilePhotoUpload :photo-url="adminProfile.photo_url" compact @upload="uploadAdminPhoto" />
      <div>
        <p class="text-xs font-semibold uppercase tracking-wider text-amber-600 dark:text-amber-400">Mon profil administrateur</p>
        <h2 class="mt-1 font-display text-xl font-bold text-slate-900 dark:text-white">
          {{ adminProfile.first_name }} {{ adminProfile.last_name }}
        </h2>
        <p class="text-sm text-slate-500 dark:text-slate-400">{{ adminProfile.email }} · {{ adminProfile.username }}</p>
        <p v-if="photoMsg" class="mt-2 text-sm text-emerald-600 dark:text-emerald-400">{{ photoMsg }}</p>
      </div>
    </div>

    <div v-if="loading" class="flex h-48 items-center justify-center">
      <div class="h-10 w-10 animate-spin rounded-full border-4 border-amber-200 border-t-amber-500" />
    </div>

    <template v-else-if="stats">
      <div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard title="Patients" :value="stats.patients_total" icon="👥" />
        <StatCard title="Médecins" :value="stats.medecins_total" icon="👨‍⚕️" color="primary" />
        <StatCard title="RDV aujourd'hui" :value="stats.rdv_aujourdhui" icon="📅" color="accent" />
        <StatCard title="RDV à venir" :value="stats.rdv_en_attente" icon="⏰" color="warning" />
        <StatCard title="Urgences actives" :value="stats.urgences_actives" icon="🚨" color="warning" />
        <StatCard title="Occupation lits" :value="`${stats.taux_occupation}%`" icon="🛏️" />
        <StatCard title="Personnel" :value="stats.personnel_total" icon="🩺" color="purple" />
        <StatCard
          title="Recettes du mois"
          :value="`${Number(stats.recettes_mois).toLocaleString('fr-FR')} FCFA`"
          icon="💰"
          color="accent"
        />
      </div>

      <h2 class="mb-4 mt-10 font-display text-lg font-semibold text-slate-800 dark:text-slate-100">Accès rapide</h2>
      <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <router-link
          v-for="link in quickLinks"
          :key="link.to"
          :to="link.to"
          class="flex items-center gap-3 rounded-xl bg-white dark:bg-slate-800 p-4 shadow-sm dark:shadow-none transition hover:-translate-y-0.5 hover:shadow-md"
        >
          <span class="text-2xl">{{ link.icon }}</span>
          <span class="font-medium text-slate-700 dark:text-slate-300">{{ link.label }}</span>
        </router-link>
      </div>
    </template>
  </AdminLayout>
</template>
