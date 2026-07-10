<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import api from '../../api/client.js'

const route = useRoute()
const loading = ref(true)
const error = ref('')
const data = ref(null)

const identite = computed(() => data.value?.identite || {})
const etab = computed(() => data.value?.etablissement || {})

function fmt(n) {
  return Number(n || 0).toLocaleString('fr-FR')
}

function fmtDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('fr-FR', { dateStyle: 'medium', timeStyle: 'short' })
}

function fmtDateShort(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('fr-FR')
}

onMounted(async () => {
  try {
    const { data: payload } = await api.get(`/carte-patient/${route.params.token}`)
    data.value = payload
  } catch (e) {
    error.value = e.response?.data?.detail || 'QR code invalide ou expiré'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="min-h-screen bg-gradient-to-br from-slate-100 via-teal-50 to-cyan-50 dark:from-slate-950 dark:via-slate-900 dark:to-teal-950">
    <header class="bg-gradient-to-r from-teal-700 to-cyan-800 px-4 py-6 text-white shadow-lg">
      <div class="mx-auto max-w-3xl">
        <p class="text-sm text-teal-100">CHU Brazzaville — Dossier médical sécurisé</p>
        <h1 class="font-display text-2xl font-bold">Informations complètes du patient</h1>
        <p v-if="identite.nom_complet" class="mt-1 text-teal-100">{{ identite.prenom }} {{ identite.nom }} · {{ identite.numero_dossier }}</p>
      </div>
    </header>

    <main class="mx-auto max-w-3xl px-4 py-8">
      <div v-if="loading" class="py-20 text-center text-slate-500">Chargement du dossier…</div>

      <div v-else-if="error" class="rounded-2xl bg-red-50 p-8 text-center text-red-700 dark:bg-red-950/40 dark:text-red-300">
        <p class="text-4xl">⚠️</p>
        <p class="mt-3 font-medium">{{ error }}</p>
      </div>

      <div v-else-if="data" class="space-y-6">
        <!-- Identité complète (via QR) -->
        <section class="rounded-2xl bg-white p-5 shadow-sm dark:bg-slate-800">
          <h2 class="mb-3 flex items-center gap-2 font-semibold text-teal-800 dark:text-teal-300">🪪 Identité complète</h2>
          <div class="grid gap-2 text-sm sm:grid-cols-2">
            <p><span class="text-slate-500">Nom :</span> {{ identite.prenom }} {{ identite.nom }}</p>
            <p><span class="text-slate-500">N° dossier :</span> <span class="font-mono">{{ identite.numero_dossier }}</span></p>
            <p><span class="text-slate-500">Naissance :</span> {{ fmtDateShort(identite.date_naissance) }}</p>
            <p><span class="text-slate-500">Sexe :</span> {{ identite.sexe }}</p>
            <p><span class="text-slate-500">Groupe sanguin :</span> {{ identite.groupe_sanguin || '—' }}</p>
            <p><span class="text-slate-500">Téléphone :</span> {{ identite.telephone || '—' }}</p>
            <p class="sm:col-span-2"><span class="text-slate-500">E-mail :</span> {{ identite.email || '—' }}</p>
            <p class="sm:col-span-2"><span class="text-slate-500">Adresse :</span> {{ identite.adresse || '—' }}</p>
          </div>
        </section>

        <!-- Hospitalisation -->
        <section v-if="data.hospitalisations?.length" class="rounded-2xl bg-white p-5 shadow-sm dark:bg-slate-800">
          <h2 class="mb-3 font-semibold text-teal-800 dark:text-teal-300">🏥 Hospitalisation</h2>
          <div v-for="h in data.hospitalisations" :key="h.id" class="mb-4 rounded-xl border border-teal-100 bg-teal-50/50 p-4 dark:border-teal-900 dark:bg-teal-950/20">
            <div class="flex flex-wrap justify-between gap-2">
              <span class="rounded-full bg-teal-100 px-3 py-0.5 text-xs font-medium text-teal-800">{{ h.statut_label }}</span>
              <span class="text-xs text-slate-500">Entrée : {{ fmtDate(h.date_entree) }}</span>
            </div>
            <p class="mt-2 font-medium">{{ h.localisation }}</p>
            <p class="text-sm text-slate-600 dark:text-slate-400">Motif : {{ h.motif_admission }}</p>
            <div v-if="h.medecin_referent?.nom_complet" class="mt-3 rounded-lg bg-white/80 p-3 dark:bg-slate-800/80">
              <p class="text-xs font-medium uppercase text-slate-400">Médecin référent</p>
              <p class="font-semibold">{{ h.medecin_referent.nom_complet }}</p>
              <p class="text-sm text-slate-500">{{ h.medecin_referent.specialite }}</p>
              <p v-if="h.medecin_referent.email" class="text-xs text-teal-700">{{ h.medecin_referent.email }}</p>
            </div>
            <ul v-if="h.plan_soins?.length" class="mt-3 space-y-1 text-sm">
              <li v-for="(s, i) in h.plan_soins" :key="i" class="flex gap-2">
                <span>{{ s.realise_a ? '✅' : '⏳' }}</span>
                <span>{{ s.description }}</span>
              </li>
            </ul>
          </div>
        </section>

        <!-- Consultations & ordonnances -->
        <section v-if="data.consultations?.length" class="rounded-2xl bg-white p-5 shadow-sm dark:bg-slate-800">
          <h2 class="mb-3 font-semibold text-teal-800 dark:text-teal-300">📋 Consultations & ordonnances</h2>
          <div v-for="c in data.consultations" :key="c.id" class="mb-4 border-b pb-4 last:border-0 dark:border-slate-700">
            <div class="flex flex-wrap justify-between gap-2">
              <p class="font-medium">{{ c.diagnostic }}</p>
              <span class="text-xs text-slate-500">{{ fmtDate(c.date) }}</span>
            </div>
            <p class="text-xs text-slate-500">CIM-10 : {{ c.diagnostic_cim10 }}</p>
            <p v-if="c.medecin?.nom_complet" class="mt-1 text-sm text-teal-700">{{ c.medecin.nom_complet }} — {{ c.medecin.specialite }}</p>
            <div v-if="c.ordonnances?.length" class="mt-3 space-y-2">
              <p class="text-xs font-medium uppercase text-slate-400">Ordonnances</p>
              <div v-for="o in c.ordonnances" :key="o.id" class="rounded-lg bg-slate-50 px-3 py-2 text-sm dark:bg-slate-700/50">
                <strong>{{ o.medicament }}</strong> — {{ o.posologie }} ({{ o.duree_jours }} j)
                <p v-if="o.instructions" class="text-xs text-slate-500">{{ o.instructions }}</p>
              </div>
            </div>
          </div>
        </section>

        <!-- Factures -->
        <section v-if="data.factures?.length" class="rounded-2xl bg-white p-5 shadow-sm dark:bg-slate-800">
          <h2 class="mb-3 font-semibold text-teal-800 dark:text-teal-300">💳 Factures</h2>
          <div v-for="f in data.factures" :key="f.id" class="mb-4 rounded-xl border p-4 dark:border-slate-700">
            <div class="flex flex-wrap justify-between gap-2">
              <span class="font-mono text-sm">{{ f.numero }}</span>
              <span class="rounded-full px-2 py-0.5 text-xs" :class="f.est_payee ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-800'">{{ f.statut_libelle }}</span>
            </div>
            <p class="mt-1 text-lg font-bold">{{ fmt(f.montant_total) }} FCFA</p>
            <p class="text-xs text-slate-500">Reste : {{ fmt(f.montant_restant) }} FCFA</p>
            <ul v-if="f.lignes?.length" class="mt-2 space-y-1 text-sm">
              <li v-for="l in f.lignes" :key="l.id" class="flex justify-between">
                <span>{{ l.libelle }} × {{ l.quantite }}</span>
                <span>{{ fmt(l.montant) }} FCFA</span>
              </li>
            </ul>
          </div>
        </section>

        <!-- Labo -->
        <section v-if="data.resultats_laboratoire?.length" class="rounded-2xl bg-white p-5 shadow-sm dark:bg-slate-800">
          <h2 class="mb-3 font-semibold text-teal-800 dark:text-teal-300">🔬 Résultats laboratoire</h2>
          <div v-for="r in data.resultats_laboratoire" :key="r.id" class="mb-3 flex justify-between border-b pb-2 dark:border-slate-700">
            <div>
              <p class="font-medium">{{ r.examen }}</p>
              <p class="text-lg text-blue-800">{{ r.valeur }} {{ r.unite }}</p>
              <p class="text-xs text-slate-500">Réf. {{ r.reference }}</p>
            </div>
            <p class="text-xs text-slate-400">{{ fmtDate(r.date_validation) }}</p>
          </div>
        </section>

        <!-- RDV -->
        <section v-if="data.rendez_vous?.length" class="rounded-2xl bg-white p-5 shadow-sm dark:bg-slate-800">
          <h2 class="mb-3 font-semibold text-teal-800 dark:text-teal-300">📅 Rendez-vous</h2>
          <div v-for="r in data.rendez_vous.slice(0, 5)" :key="r.id" class="mb-2 text-sm">
            <span class="font-medium">{{ fmtDate(r.date_heure) }}</span> — {{ r.motif }}
            <span v-if="r.medecin?.nom_complet" class="text-teal-700"> · {{ r.medecin.nom_complet }}</span>
          </div>
        </section>

        <!-- Pharmacie -->
        <section v-if="data.demandes_pharmacie?.length" class="rounded-2xl bg-white p-5 shadow-sm dark:bg-slate-800">
          <h2 class="mb-3 font-semibold text-teal-800 dark:text-teal-300">💊 Demandes pharmacie</h2>
          <div v-for="d in data.demandes_pharmacie" :key="d.reference" class="mb-2 text-sm">
            <span class="font-mono">{{ d.reference }}</span> — {{ d.statut }} — {{ fmt(d.montant_total) }} FCFA
          </div>
        </section>

        <p class="text-center text-xs text-slate-400">
          Document généré le {{ fmtDate(data.genere_le) }} · {{ etab.nom }}
        </p>
      </div>
    </main>
  </div>
</template>
