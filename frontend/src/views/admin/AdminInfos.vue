<script setup>
import { ref, onMounted } from 'vue'
import AdminLayout from '../../components/AdminLayout.vue'
import { adminApi } from '../../api/admin.js'

const form = ref({
  nom_etablissement: '', adresse: '', telephone: '', email: '',
  horaires: '', urgences_telephone: '', description: '', site_web: '',
  latitude: -4.2594, longitude: 15.2847, google_maps_query: '',
})
const loading = ref(true)
const message = ref('')

onMounted(async () => {
  try {
    const { data } = await adminApi.infos()
    form.value = { ...data }
  } finally {
    loading.value = false
  }
})

async function save() {
  try {
    await adminApi.updateInfos(form.value)
    message.value = 'Informations enregistrées'
  } catch {
    message.value = 'Erreur lors de la sauvegarde'
  }
}
</script>

<template>
  <AdminLayout>
    <header class="mb-8">
      <h1 class="font-display text-3xl font-bold text-slate-900 dark:text-white">Informations pratiques</h1>
      <p class="mt-1 text-slate-600 dark:text-slate-400">Coordonnées et horaires de l'établissement (visibles patients)</p>
    </header>

    <form v-if="!loading" class="max-w-2xl space-y-4 rounded-2xl bg-white dark:bg-slate-800 p-6 shadow-sm dark:shadow-none" @submit.prevent="save">
      <div>
        <label class="mb-1 block text-sm font-medium">Nom de l'établissement</label>
        <input v-model="form.nom_etablissement" v-input-filter="'text'" class="input-field" />
      </div>
      <div>
        <label class="mb-1 block text-sm font-medium">Adresse</label>
        <textarea v-model="form.adresse" v-input-filter="'text'" class="input-field" rows="2" />
      </div>
      <div class="grid gap-4 sm:grid-cols-2">
        <div>
          <label class="mb-1 block text-sm font-medium">Téléphone</label>
          <input v-model="form.telephone" v-input-filter="'phone'" inputmode="tel" class="input-field" />
        </div>
        <div>
          <label class="mb-1 block text-sm font-medium">Urgences (24h/24)</label>
          <input v-model="form.urgences_telephone" v-input-filter="'phone'" inputmode="tel" class="input-field" placeholder="+242 066967236" />
        </div>
      </div>
      <div>
        <label class="mb-1 block text-sm font-medium">Email</label>
        <input v-model="form.email" type="email" class="input-field" />
      </div>
      <div>
        <label class="mb-1 block text-sm font-medium">Horaires</label>
        <textarea v-model="form.horaires" v-input-filter="'text'" class="input-field" rows="3" placeholder="Lun-Ven 7h-19h..." />
      </div>
      <div>
        <label class="mb-1 block text-sm font-medium">Description</label>
        <textarea v-model="form.description" v-input-filter="'text'" class="input-field" rows="3" />
      </div>
      <div>
        <label class="mb-1 block text-sm font-medium">Site web</label>
        <input v-model="form.site_web" class="input-field" placeholder="https://..." />
      </div>
      <div class="grid gap-4 sm:grid-cols-3">
        <div>
          <label class="mb-1 block text-sm font-medium">Latitude GPS</label>
          <input v-model.number="form.latitude" type="number" step="0.0001" class="input-field" />
        </div>
        <div>
          <label class="mb-1 block text-sm font-medium">Longitude GPS</label>
          <input v-model.number="form.longitude" type="number" step="0.0001" class="input-field" />
        </div>
        <div>
          <label class="mb-1 block text-sm font-medium">Requête Google Maps</label>
          <input v-model="form.google_maps_query" v-input-filter="'text'" class="input-field" />
        </div>
      </div>
      <p v-if="message" class="text-sm text-emerald-600">{{ message }}</p>
      <button type="submit" class="btn-primary">Enregistrer</button>
    </form>
  </AdminLayout>
</template>
