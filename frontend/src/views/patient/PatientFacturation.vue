<script setup>
import { ref, onMounted, computed } from 'vue'
import PatientLayout from '../../components/PatientLayout.vue'
import MobileMoneyCheckout from '../../components/MobileMoneyCheckout.vue'
import { patientApi } from '../../api/patient.js'

const invoices = ref([])
const loading = ref(true)
const payingInvoice = ref(null)
const patientPhone = ref('')

const impayees = computed(() => invoices.value.filter((i) => i.est_impayee))
const payees = computed(() => invoices.value.filter((i) => i.est_payee))
const totalDu = computed(() => impayees.value.reduce((s, i) => s + Number(i.montant_restant || 0), 0))

function fmt(n) {
  return Number(n || 0).toLocaleString('fr-FR')
}

function statutClass(i) {
  if (i.est_payee) return 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300'
  if (i.statut === 'PARTIEL') return 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300'
  return 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300'
}

async function load() {
  loading.value = true
  try {
    const [inv, prof] = await Promise.all([patientApi.invoices(), patientApi.profile()])
    invoices.value = inv.data
    patientPhone.value = prof.data.telephone || ''
  } finally {
    loading.value = false
  }
}

function onPaid() {
  payingInvoice.value = null
  load()
}

onMounted(load)
</script>

<template>
  <PatientLayout>
    <header class="relative mb-8 overflow-hidden rounded-3xl bg-gradient-to-br from-emerald-800 via-teal-800 to-cyan-900 p-8 text-white">
      <div class="relative">
        <p class="text-sm text-emerald-200">Espace patient · Finances</p>
        <h1 class="font-display text-3xl font-bold">Mes factures</h1>
        <p class="mt-2 max-w-xl text-emerald-100">Payez en ligne par MTN MoMo ou Airtel Money — confirmation depuis votre téléphone</p>
      </div>
      <div class="relative mt-6 flex flex-wrap gap-4">
        <div class="rounded-2xl bg-white/10 px-5 py-3 backdrop-blur">
          <p class="text-2xl font-bold">{{ impayees.length }}</p>
          <p class="text-xs text-emerald-200">Impayée(s)</p>
        </div>
        <div class="rounded-2xl bg-white/10 px-5 py-3 backdrop-blur">
          <p class="text-2xl font-bold text-amber-200">{{ fmt(totalDu) }}</p>
          <p class="text-xs text-emerald-200">FCFA dus</p>
        </div>
        <div class="rounded-2xl bg-white/10 px-5 py-3 backdrop-blur">
          <p class="text-2xl font-bold text-emerald-300">{{ payees.length }}</p>
          <p class="text-xs text-emerald-200">Payée(s)</p>
        </div>
      </div>
    </header>

    <div v-if="loading" class="flex h-40 items-center justify-center">
      <div class="h-10 w-10 animate-spin rounded-full border-4 border-teal-200 border-t-teal-600" />
    </div>

    <div v-else class="grid gap-6 lg:grid-cols-[1fr_380px]">
      <div class="space-y-4">
        <article
          v-for="inv in invoices"
          :key="inv.id"
          class="overflow-hidden rounded-2xl border bg-white shadow-sm transition hover:shadow-md dark:border-slate-700 dark:bg-slate-800"
          :class="inv.est_impayee ? 'border-red-200 dark:border-red-900/50' : 'border-emerald-200 dark:border-emerald-900/40'"
        >
          <div class="flex flex-wrap items-start justify-between gap-4 border-b px-5 py-4 dark:border-slate-700">
            <div>
              <p class="font-mono text-xs text-teal-600 dark:text-teal-400">{{ inv.numero }}</p>
              <p class="font-display text-lg font-bold text-slate-900 dark:text-white">{{ fmt(inv.montant_total) }} FCFA</p>
              <p class="text-sm text-slate-500">{{ inv.statut_libelle }}</p>
            </div>
            <span class="rounded-full px-3 py-1 text-xs font-semibold" :class="statutClass(inv)">
              {{ inv.est_payee ? '✓ Payée' : '○ Impayée' }}
            </span>
          </div>

          <ul class="divide-y px-5 dark:divide-slate-700">
            <li v-for="l in inv.lignes" :key="l.id" class="flex justify-between py-2 text-sm">
              <span class="text-slate-600 dark:text-slate-400">{{ l.libelle }}</span>
              <span class="font-medium">{{ fmt(l.montant) }}</span>
            </li>
          </ul>

          <div class="flex flex-wrap items-center justify-between gap-3 bg-slate-50 px-5 py-4 dark:bg-slate-900/40">
            <div class="text-sm">
              <span class="text-slate-500">Payé : </span>
              <strong>{{ fmt(inv.montant_paye) }}</strong>
              <span v-if="inv.est_impayee" class="ml-3 text-red-600 dark:text-red-400">
                Reste : <strong>{{ fmt(inv.montant_restant) }} FCFA</strong>
              </span>
            </div>
            <button
              v-if="inv.est_impayee"
              type="button"
              class="rounded-xl bg-gradient-to-r from-yellow-500 to-amber-500 px-4 py-2 text-sm font-semibold text-white shadow-md hover:from-yellow-600 hover:to-amber-600"
              @click="payingInvoice = inv"
            >
              📱 Payer en Mobile Money
            </button>
            <span v-else class="text-sm font-medium text-emerald-600 dark:text-emerald-400">Règlement confirmé</span>
          </div>
        </article>

        <p v-if="!invoices.length" class="rounded-2xl bg-white py-16 text-center text-slate-400 dark:bg-slate-800">
          Aucune facture pour le moment
        </p>
      </div>

      <aside class="lg:sticky lg:top-8 lg:self-start">
        <MobileMoneyCheckout
          v-if="payingInvoice"
          :invoice="payingInvoice"
          :default-phone="patientPhone"
          :api-init="patientApi.initMobileMoney"
          :api-confirm="patientApi.confirmMobileMoney"
          :api-approve="patientApi.approveMobileMoney"
          :api-status="patientApi.mobileMoneyStatus"
          @success="onPaid"
          @close="payingInvoice = null"
        />
        <div v-else class="rounded-2xl border border-dashed border-slate-300 p-8 text-center dark:border-slate-600">
          <p class="text-4xl">💳</p>
          <p class="mt-3 font-medium text-slate-700 dark:text-slate-300">Sélectionnez une facture impayée</p>
          <p class="mt-1 text-sm text-slate-500">MTN (06) · Airtel (04/05)</p>
        </div>

        <div class="mt-4 rounded-2xl bg-teal-50 p-4 text-xs text-teal-800 dark:bg-teal-950/40 dark:text-teal-200">
          <p class="font-semibold">Comment ça marche ?</p>
          <ol class="mt-2 list-inside list-decimal space-y-1 opacity-90">
            <li>Saisissez votre numéro Mobile Money</li>
            <li>Recevez la notification sur votre téléphone</li>
            <li>Confirmez puis entrez votre PIN</li>
          </ol>
        </div>
      </aside>
    </div>
  </PatientLayout>
</template>
