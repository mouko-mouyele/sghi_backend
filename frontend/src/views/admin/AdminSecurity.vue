<script setup>

import { ref, onMounted } from 'vue'

import AdminLayout from '../../components/AdminLayout.vue'

import PaginationBar from '../../components/PaginationBar.vue'

import { adminApi } from '../../api/admin.js'

import { usePagination } from '../../composables/usePagination.js'



const journal = ref([])

const pagination = usePagination(15)

const mfa = ref({ mfa_enabled: true, hospital_email: '', hospital_email_masked: '', message: '' })
const emailDiag = ref(null)
const emailTestMsg = ref('')
const emailTestError = ref('')
const emailTesting = ref(false)

async function loadEmailDiag() {
  try {
    const { data } = await adminApi.emailDiagnostic()
    emailDiag.value = data
  } catch {
    emailDiag.value = null
  }
}

async function testEmail() {
  emailTesting.value = true
  emailTestMsg.value = ''
  emailTestError.value = ''
  try {
    const { data } = await adminApi.testEmail()
    emailTestMsg.value = data.detail
  } catch (e) {
    emailTestError.value = e.response?.data?.detail || 'Échec du test email'
  } finally {
    emailTesting.value = false
  }
}



async function loadMfa() {
  try {
    const { data } = await adminApi.mfaStatus()
    mfa.value = data
  } catch {
    /* ignore */
  }
}



async function load() {

  const { data } = await adminApi.loginJournal(pagination.params())

  journal.value = data.items

  pagination.applyMeta(data)

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



onMounted(() => {

  load()

  loadMfa()

  loadEmailDiag()

})

</script>



<template>

  <AdminLayout>

    <header class="mb-8">

      <h1 class="font-display text-3xl font-bold text-slate-900 dark:text-white">Sécurité & conformité</h1>

      <p class="mt-1 text-slate-600 dark:text-slate-400">Audit trail, JWT et protection des données</p>

    </header>



    <div class="mb-6 grid gap-4 sm:grid-cols-4">

      <div class="rounded-2xl border border-emerald-200 dark:border-emerald-800 bg-emerald-50 dark:bg-emerald-950/40 p-4">

        <p class="font-semibold text-emerald-800 dark:text-emerald-200">Authentification JWT</p>

        <p class="text-xs text-emerald-600">Tokens avec rotation automatique</p>

      </div>

      <div class="rounded-2xl border border-blue-200 bg-blue-50 dark:bg-blue-950/40 p-4">

        <p class="font-semibold text-blue-800">RBAC strict</p>

        <p class="text-xs text-blue-600">8 profils avec permissions dédiées</p>

      </div>

      <div class="rounded-2xl border border-amber-200 bg-amber-50 dark:bg-amber-950/40 p-4">

        <p class="font-semibold text-amber-800 dark:text-amber-200">Chiffrement AES-256</p>

        <p class="text-xs text-amber-600">Données sensibles protégées</p>

      </div>

      <div class="rounded-2xl border border-violet-200 bg-violet-50 dark:border-violet-800 dark:bg-violet-950/40 p-4">

        <p class="font-semibold text-violet-800 dark:text-violet-200">MFA par email</p>

        <p class="text-xs text-violet-600 dark:text-violet-300">Code envoyé à la connexion</p>

      </div>

    </div>



    <div class="mb-8 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-700 dark:bg-slate-800">

      <h2 class="text-lg font-semibold text-slate-900 dark:text-white">MFA par email à la connexion</h2>

      <p class="mt-2 text-sm text-slate-600 dark:text-slate-400">{{ mfa.message }}</p>

      <div class="mt-4 rounded-xl bg-violet-50 p-4 dark:bg-violet-950/30">

        <p class="text-xs font-medium uppercase text-violet-700 dark:text-violet-300">Boîte mail hôpital (personnel)</p>

        <p class="mt-1 font-mono text-sm">{{ mfa.hospital_email_masked || '—' }}</p>

        <p class="mt-3 text-xs text-slate-500">Patients : code envoyé sur leur email personnel enregistré.</p>

      </div>

      <div v-if="emailDiag" class="mt-4 rounded-xl border border-slate-200 p-4 dark:border-slate-600">
        <p class="text-sm font-medium text-slate-800 dark:text-slate-100">Configuration SMTP (Gmail)</p>
        <p class="mt-1 text-xs" :class="emailDiag.configured ? 'text-emerald-600' : 'text-amber-700 dark:text-amber-300'">
          {{ emailDiag.message }}
        </p>
        <ul class="mt-2 space-y-1 text-xs text-slate-500 dark:text-slate-400">
          <li>Serveur : {{ emailDiag.smtp_host }}:{{ emailDiag.smtp_port }}</li>
          <li>Compte : {{ emailDiag.smtp_user || '—' }}</li>
          <li>Mot de passe app : {{ emailDiag.password_set ? '✓ configuré' : '✗ manquant dans Render' }}</li>
        </ul>
        <button
          type="button"
          class="btn-primary mt-4"
          :disabled="emailTesting"
          @click="testEmail"
        >
          {{ emailTesting ? 'Envoi…' : '📧 Tester l\'envoi email' }}
        </button>
        <p v-if="emailTestMsg" class="mt-3 text-sm text-emerald-700 dark:text-emerald-300">{{ emailTestMsg }}</p>
        <p v-if="emailTestError" class="mt-3 text-sm text-red-600 dark:text-red-400">{{ emailTestError }}</p>
      </div>

    </div>



    <div class="overflow-hidden rounded-2xl bg-white dark:bg-slate-800 shadow-sm dark:shadow-none">

      <div class="border-b px-4 py-3 font-semibold">Dernières connexions</div>

      <table class="w-full text-sm">

        <thead class="bg-slate-50 dark:bg-slate-800/60">

          <tr>

            <th class="px-4 py-3 text-left">Utilisateur</th>

            <th class="px-4 py-3 text-left">IP</th>

            <th class="px-4 py-3 text-left">Statut</th>

            <th class="px-4 py-3 text-left">Date</th>

          </tr>

        </thead>

        <tbody>

          <tr v-for="(j, i) in journal" :key="i" class="border-t">

            <td class="px-4 py-3">{{ j.user__username || '—' }}</td>

            <td class="px-4 py-3 font-mono text-xs">{{ j.ip_address || '—' }}</td>

            <td class="px-4 py-3">

              <span :class="j.success ? 'text-emerald-600' : 'text-red-600 dark:text-red-400'">{{ j.success ? 'OK' : 'Échec' }}</span>

            </td>

            <td class="px-4 py-3 text-slate-500 dark:text-slate-400">{{ j.timestamp?.slice(0, 19).replace('T', ' ') }}</td>

          </tr>

        </tbody>

      </table>

      <PaginationBar

        :page="pagination.page.value"

        :page-size="pagination.pageSize.value"

        :total="pagination.total.value"

        :total-pages="pagination.totalPages.value"

        :size-options="[10, 15, 25, 50]"

        @update:page="onPageChange"

        @update:page-size="onPageSizeChange"

      />

    </div>

  </AdminLayout>

</template>

