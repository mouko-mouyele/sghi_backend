<script setup>
import { ref, onMounted } from 'vue'
import PatientLayout from '../../components/PatientLayout.vue'
import { patientApi } from '../../api/patient.js'

const profile = ref(null)
const consultations = ref([])
const documents = ref([])
const loading = ref(true)
const downloading = ref(false)
const downloadError = ref('')
const cardPdfInfo = ref(null)

onMounted(async () => {
  try {
    const prof = await patientApi.profile()
    profile.value = prof.data
    const [cons, docs] = await Promise.all([
      patientApi.consultations(),
      patientApi.documents(prof.data.id),
    ])
    consultations.value = cons.data
    documents.value = docs.data
  } finally {
    loading.value = false
  }
})

async function downloadPdf() {
  downloading.value = true
  downloadError.value = ''
  try {
    const result = await patientApi.downloadCardPdf()
    cardPdfInfo.value = {
      filename: result.filename,
      media_url: result.mediaUrl,
      chemin: result.chemin,
    }
  } catch (e) {
    downloadError.value = e.message || 'Impossible de telecharger le PDF'
  } finally {
    downloading.value = false
  }
}

function fmt(d) {
  return new Date(d).toLocaleDateString('fr-FR', { dateStyle: 'long' })
}
</script>

<template>
  <PatientLayout>
    <header class="mb-8 flex flex-wrap items-start justify-between gap-4">
      <div>
        <h1 class="font-display text-3xl font-bold text-slate-900 dark:text-white">Mon dossier médical</h1>
        <p class="mt-1 text-slate-600 dark:text-slate-400">Consultation sécurisée de l'historique médical (CIM-10, ordonnances)</p>
      </div>
      <button
        type="button"
        class="flex items-center gap-2 rounded-xl bg-red-600 px-5 py-3 text-sm font-semibold text-white shadow-lg hover:bg-red-700"
        :disabled="downloading"
        @click="downloadPdf"
      >
        📄 {{ downloading ? 'Génération…' : 'Télécharger ma carte PDF' }}
      </button>
      <a
        v-if="cardPdfInfo?.media_url"
        :href="cardPdfInfo.media_url"
        target="_blank"
        rel="noopener"
        class="flex items-center gap-2 rounded-xl border border-red-200 px-4 py-3 text-sm font-medium text-red-700 hover:bg-red-50 dark:border-red-900 dark:text-red-300"
      >
        🔗 Ouvrir le PDF
      </a>
    </header>

    <div class="mb-6 rounded-2xl border border-teal-200 bg-teal-50/80 p-4 text-sm text-teal-900 dark:border-teal-800 dark:bg-teal-950/30 dark:text-teal-100">
      <p class="font-medium">Carte patient avec QR code</p>
      <p class="mt-1 text-teal-800 dark:text-teal-200">
        Le PDF affiche uniquement votre <strong>nom, prénom, e-mail et adresse</strong>.
        Toutes les autres informations (hospitalisation, salle, ordonnances, médecin, factures…)
        sont accessibles en <strong>scannant le QR code</strong> sur le document.
      </p>
      <p v-if="cardPdfInfo?.chemin" class="mt-2 font-mono text-xs text-teal-700 dark:text-teal-300">
        Fichier enregistré : media/{{ cardPdfInfo.chemin }}
      </p>
      <p v-if="downloadError" class="mt-2 rounded-lg bg-red-100 px-3 py-2 text-red-700 dark:bg-red-950/40 dark:text-red-300">
        {{ downloadError }}
      </p>
    </div>

    <div v-if="profile" class="mb-8 rounded-2xl bg-white dark:bg-slate-800 p-6 shadow-sm dark:shadow-none">
      <h2 class="mb-3 font-semibold">Identité</h2>
      <div class="grid gap-2 text-sm sm:grid-cols-2">
        <p><span class="text-slate-500 dark:text-slate-400">Nom :</span> {{ profile.prenom }} {{ profile.nom }}</p>
        <p><span class="text-slate-500 dark:text-slate-400">N° dossier :</span> <span class="font-mono text-teal-700">{{ profile.numero_dossier }}</span></p>
        <p><span class="text-slate-500 dark:text-slate-400">Naissance :</span> {{ profile.date_naissance }}</p>
        <p><span class="text-slate-500 dark:text-slate-400">E-mail :</span> {{ profile.email || '—' }}</p>
        <p><span class="text-slate-500 dark:text-slate-400">Adresse :</span> {{ profile.adresse || '—' }}</p>
        <p><span class="text-slate-500 dark:text-slate-400">Groupe sanguin :</span> {{ profile.groupe_sanguin || '—' }}</p>
      </div>
    </div>

    <h2 class="mb-4 text-lg font-semibold">Consultations validées</h2>
    <div v-if="loading" class="text-slate-400 dark:text-slate-500">Chargement...</div>
    <div v-else class="space-y-4">
      <div v-for="c in consultations" :key="c.id" class="rounded-2xl bg-white dark:bg-slate-800 p-5 shadow-sm dark:shadow-none">
        <div class="flex flex-wrap items-start justify-between gap-2">
          <div>
            <p class="font-semibold">{{ c.diagnostic_libelle }}</p>
            <p class="text-xs text-slate-500 dark:text-slate-400">CIM-10 : {{ c.diagnostic_cim10 }}</p>
          </div>
          <p class="text-sm text-slate-500 dark:text-slate-400">{{ fmt(c.date_consultation) }}</p>
        </div>
        <p class="mt-2 text-sm text-teal-700">{{ c.medecin_nom }}</p>
        <div v-if="c.prescriptions.length" class="mt-4 border-t pt-3">
          <p class="mb-2 text-xs font-medium uppercase text-slate-400 dark:text-slate-500">Prescriptions</p>
          <div v-for="p in c.prescriptions" :key="p.id" class="mb-2 rounded-lg bg-slate-50 dark:bg-slate-800/60 px-3 py-2 text-sm">
            <strong>{{ p.medicament_nom }}</strong> — {{ p.posologie }}
            <span v-if="p.verrouillee" class="ml-2 text-xs text-emerald-600">✓ Validée</span>
          </div>
        </div>
      </div>
      <p v-if="!consultations.length" class="py-8 text-center text-slate-400 dark:text-slate-500">Aucune consultation publiée</p>
    </div>

    <h2 class="mb-4 mt-10 text-lg font-semibold">Documents archivés</h2>
    <div class="space-y-2">
      <div v-for="d in documents" :key="d.id" class="flex items-center justify-between rounded-xl bg-white dark:bg-slate-800 px-4 py-3 shadow-sm dark:shadow-none">
        <div>
          <p class="font-medium">{{ d.titre }}</p>
          <p class="text-xs text-slate-500 dark:text-slate-400">{{ d.mime_type }} · {{ Math.round(d.taille_octets / 1024) }} Ko</p>
        </div>
        <span v-if="d.signe_electroniquement" class="text-xs text-emerald-600">Signé électroniquement</span>
      </div>
      <p v-if="!documents.length" class="py-6 text-center text-slate-400 dark:text-slate-500">Aucun document</p>
    </div>
  </PatientLayout>
</template>
