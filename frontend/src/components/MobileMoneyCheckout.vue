<script setup>
import { ref, computed, watch, onUnmounted } from 'vue'

const props = defineProps({
  invoice: { type: Object, required: true },
  apiInit: { type: Function, required: true },
  apiConfirm: { type: Function, required: true },
  apiApprove: { type: Function, required: true },
  apiStatus: { type: Function, default: null },
  defaultPhone: { type: String, default: '' },
})

const emit = defineEmits(['success', 'close'])

const step = ref(1)
const phone = ref(props.defaultPhone || '')
const smsCode = ref('')
const loading = ref(false)
const error = ref('')
const tx = ref(null)
const pushSent = ref(false)
let pollTimer = null

const montant = computed(() => Number(props.invoice.montant_restant || 0))

const operateurPreview = computed(() => detectOperateur(phone.value))

function detectOperateur(raw) {
  const d = (raw || '').replace(/\D/g, '').replace(/^242/, '').replace(/^0/, '')
  const local = raw.replace(/\D/g, '').includes('242')
    ? (raw.replace(/\D/g, '').replace(/^242/, '').length === 8 ? `0${raw.replace(/\D/g, '').slice(-8)}` : `0${d}`)
    : (d.length === 8 ? `0${d}` : (d.startsWith('0') ? d : `0${d}`))
  const n = local.replace(/\D/g, '')
  const check = n.startsWith('0') ? n : `0${n}`
  if (check.startsWith('06')) return { code: 'MTN', label: 'MTN MoMo', color: 'from-yellow-400 to-amber-500', emoji: '📱', ussd: '*133*1#' }
  if (check.startsWith('04') || check.startsWith('05')) return { code: 'AIRTEL', label: 'Airtel Money', color: 'from-red-500 to-rose-600', emoji: '🔴', ussd: '*128*1#' }
  return null
}

function fmt(n) {
  return Number(n || 0).toLocaleString('fr-FR')
}

watch(phone, () => { error.value = '' })

watch(() => props.defaultPhone, (v) => {
  if (v && !phone.value) phone.value = v
}, { immediate: true })

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

function startPolling() {
  stopPolling()
  if (!props.apiStatus || !tx.value?.id) return
  pollTimer = setInterval(async () => {
    try {
      const { data } = await props.apiStatus(tx.value.id)
      if (data.statut === 'CONFIRME') {
        stopPolling()
        step.value = 4
        emit('success')
      }
    } catch { /* ignore poll errors */ }
  }, 2500)
}

onUnmounted(stopPolling)

async function startPayment() {
  if (!operateurPreview.value) {
    error.value = 'Numéro MTN (06…) ou Airtel (04… / 05…) requis'
    return
  }
  loading.value = true
  error.value = ''
  try {
    const { data } = await props.apiInit(props.invoice.id, {
      numero_mobile: phone.value,
      montant: montant.value,
    })
    tx.value = data
    pushSent.value = true
    step.value = 3
    startPolling()
  } catch (e) {
    error.value = e.response?.data?.detail || 'Impossible d\'initier le paiement'
  } finally {
    loading.value = false
  }
}

async function approveOnPhone() {
  loading.value = true
  error.value = ''
  try {
    await props.apiApprove(tx.value.id, { numero_mobile: phone.value })
    stopPolling()
    step.value = 4
    emit('success')
  } catch (e) {
    error.value = e.response?.data?.detail || 'Validation refusée — vérifiez le numéro saisi'
  } finally {
    loading.value = false
  }
}

async function confirmWithSmsCode() {
  if (!smsCode.value || smsCode.value.length < 4) {
    error.value = 'Entrez le code reçu sur votre téléphone'
    return
  }
  loading.value = true
  error.value = ''
  try {
    await props.apiConfirm(props.invoice.id, {
      transaction_id: tx.value.id,
      code_push: smsCode.value.trim(),
    })
    stopPolling()
    step.value = 4
    emit('success')
  } catch (e) {
    error.value = e.response?.data?.detail || 'Code incorrect'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-xl dark:border-slate-700 dark:bg-slate-900">
    <div class="bg-gradient-to-r from-emerald-700 via-teal-700 to-cyan-800 px-6 py-5 text-white">
      <p class="text-sm text-emerald-100">Paiement sécurisé CHU Brazzaville</p>
      <h3 class="font-display text-xl font-bold">Mobile Money</h3>
      <p class="mt-1 text-2xl font-bold">{{ fmt(montant) }} <span class="text-sm font-normal">FCFA</span></p>
      <p class="text-xs text-emerald-100">{{ invoice.numero }}</p>
    </div>

    <div class="p-6">
      <!-- Étape 1 : téléphone -->
      <div v-if="step === 1">
        <label class="mb-2 block text-sm font-medium text-slate-700 dark:text-slate-300">Votre numéro Mobile Money</label>
        <input
          v-model="phone"
          v-input-filter="'phone'"
          type="tel"
          inputmode="tel"
          class="input-field text-lg tracking-wide"
          placeholder="06 123 45 67"
          autocomplete="tel"
        />
        <p class="mt-2 text-xs text-slate-500 dark:text-slate-400">
          MTN MoMo : <strong>06</strong> · Airtel Money : <strong>04</strong> ou <strong>05</strong>
          · Formats acceptés : 06…, +242 06…, 061234567
        </p>

        <div
          v-if="operateurPreview"
          class="mt-4 flex items-center gap-3 rounded-2xl bg-gradient-to-r p-4 text-white shadow-md"
          :class="operateurPreview.color"
        >
          <span class="text-2xl">{{ operateurPreview.emoji }}</span>
          <div>
            <p class="font-semibold">{{ operateurPreview.label }}</p>
            <p class="text-xs opacity-90">La demande sera envoyée à ce numéro</p>
          </div>
        </div>

        <p v-if="error" class="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600 dark:bg-red-950/40 dark:text-red-300">{{ error }}</p>

        <div class="mt-6 flex gap-2">
          <button type="button" class="flex-1 rounded-xl border px-4 py-2.5 text-sm dark:border-slate-600" @click="emit('close')">Annuler</button>
          <button type="button" class="btn-primary flex-1" :disabled="!operateurPreview" @click="step = 2">Continuer</button>
        </div>
      </div>

      <!-- Étape 2 : récap -->
      <div v-else-if="step === 2">
        <div class="rounded-2xl bg-slate-50 p-4 dark:bg-slate-800/60">
          <p class="text-sm text-slate-500">Montant à débiter</p>
          <p class="text-2xl font-bold text-slate-900 dark:text-white">{{ fmt(montant) }} FCFA</p>
          <p class="mt-2 text-sm font-medium">{{ operateurPreview?.label }}</p>
          <p class="font-mono text-sm text-primary-600 dark:text-primary-400">{{ phone }}</p>
        </div>
        <p class="mt-4 text-sm text-slate-600 dark:text-slate-400">
          Une notification sera envoyée <strong>en temps réel</strong> sur ce numéro. Validez-la sur votre téléphone, puis confirmez ici.
        </p>
        <p v-if="error" class="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600 dark:bg-red-950/40">{{ error }}</p>
        <div class="mt-6 flex gap-2">
          <button type="button" class="rounded-xl border px-4 py-2.5 text-sm dark:border-slate-600" @click="step = 1">← Retour</button>
          <button type="button" class="btn-primary flex-1" :disabled="loading" @click="startPayment">
            {{ loading ? 'Envoi en cours…' : '📲 Envoyer sur mon numéro' }}
          </button>
        </div>
      </div>

      <!-- Étape 3 : notification téléphone simulée + confirmation -->
      <div v-else-if="step === 3 && tx">
        <div class="mb-4 flex items-center gap-2 rounded-xl bg-emerald-50 px-3 py-2 text-xs text-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-200">
          <span class="inline-flex h-2 w-2 animate-pulse rounded-full bg-emerald-500" />
          Demande envoyée au {{ tx.numero_mobile_affiche }}
        </div>

        <!-- Simulation notification sur le téléphone -->
        <div class="mx-auto max-w-[280px] overflow-hidden rounded-3xl border-4 border-slate-800 bg-slate-900 shadow-2xl">
          <div class="bg-slate-800 px-3 py-1 text-center text-[10px] text-slate-400">12:{{ new Date().getMinutes().toString().padStart(2, '0') }}</div>
          <div
            class="p-4 text-white"
            :class="tx.operateur === 'MTN' ? 'bg-gradient-to-br from-yellow-500 to-amber-600' : 'bg-gradient-to-br from-red-600 to-rose-700'"
          >
            <p class="text-xs font-bold opacity-90">{{ tx.operateur === 'MTN' ? 'MTN Mobile Money' : 'Airtel Money' }}</p>
            <p class="mt-2 text-sm font-semibold">CHU Brazzaville</p>
            <p class="mt-1 text-lg font-bold">{{ fmt(tx.montant) }} FCFA</p>
            <p class="mt-1 text-xs opacity-90">Réf. {{ tx.reference }}</p>
            <p v-if="tx.code_push" class="mt-2 rounded-lg bg-black/20 px-2 py-1 text-center font-mono text-sm tracking-widest">
              Code : {{ tx.code_push }}
            </p>
          </div>
          <div class="flex bg-slate-100 dark:bg-slate-800">
            <button
              type="button"
              class="flex-1 border-r py-3 text-sm font-semibold text-red-600"
              @click="error = 'Paiement refusé sur le téléphone'"
            >
              Refuser
            </button>
            <button
              type="button"
              class="flex-1 py-3 text-sm font-bold text-emerald-700"
              :disabled="loading"
              @click="approveOnPhone"
            >
              {{ loading ? '…' : 'Approuver' }}
            </button>
          </div>
        </div>

        <p class="mt-4 text-center text-xs text-slate-500 dark:text-slate-400">
          Sur votre téléphone {{ tx.numero_mobile_affiche }} : appuyez sur <strong>Approuver</strong> ci-dessus
          (simulation de la notification MoMo reçue sur le numéro saisi).
        </p>
        <p class="mt-1 text-center text-xs text-slate-400">{{ tx.instruction_ussd }}</p>

        <div class="mt-5 border-t pt-4 dark:border-slate-700">
          <p class="mb-2 text-xs font-medium text-slate-600 dark:text-slate-400">Ou saisissez le code reçu par SMS :</p>
          <div class="flex gap-2">
            <input
              v-model="smsCode"
              type="text"
              inputmode="numeric"
              maxlength="6"
              class="input-field flex-1 text-center font-mono tracking-widest"
              :placeholder="tx.code_push ? 'Code SMS' : '••••••'"
            />
            <button type="button" class="btn-primary shrink-0 px-4" :disabled="loading" @click="confirmWithSmsCode">
              OK
            </button>
          </div>
        </div>

        <p v-if="error" class="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600 dark:bg-red-950/40">{{ error }}</p>
      </div>

      <!-- Étape 4 : succès -->
      <div v-else-if="step === 4" class="py-6 text-center">
        <div class="mx-auto mb-4 flex h-20 w-20 items-center justify-center rounded-full bg-emerald-100 text-4xl dark:bg-emerald-900/40">✓</div>
        <h4 class="font-display text-xl font-bold text-emerald-700 dark:text-emerald-300">Paiement confirmé</h4>
        <p class="mt-2 text-sm text-slate-600 dark:text-slate-400">
          Validé depuis <strong>{{ tx?.numero_mobile_affiche }}</strong> — facture payée.
        </p>
        <button type="button" class="btn-primary mt-6" @click="emit('close')">Fermer</button>
      </div>
    </div>
  </div>
</template>
