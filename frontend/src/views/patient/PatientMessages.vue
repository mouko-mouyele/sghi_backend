<script setup>
import { ref, onMounted, nextTick } from 'vue'
import PatientLayout from '../../components/PatientLayout.vue'
import { patientApi } from '../../api/patient.js'

const conversations = ref([])
const medecins = ref([])
const activeConv = ref(null)
const messages = ref([])
const newMsg = ref('')
const loading = ref(true)
const chatBox = ref(null)

async function load() {
  loading.value = true
  try {
    const [conv, med] = await Promise.all([patientApi.conversations(), patientApi.medecins()])
    conversations.value = conv.data
    medecins.value = med.data
  } finally {
    loading.value = false
  }
}

async function openConv(conv) {
  activeConv.value = conv
  const { data } = await patientApi.messages(conv.id)
  messages.value = data
  await nextTick()
  chatBox.value?.scrollTo({ top: chatBox.value.scrollHeight })
}

async function startWith(medecinId) {
  const { data } = await patientApi.startConversation(medecinId)
  await load()
  const conv = conversations.value.find((c) => c.id === data.conversation_id)
  if (conv) openConv(conv)
}

async function send() {
  if (!newMsg.value.trim() || !activeConv.value) return
  await patientApi.sendMessage(activeConv.value.id, newMsg.value.trim())
  newMsg.value = ''
  openConv(activeConv.value)
}

function fmt(d) {
  return new Date(d).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' })
}

onMounted(load)
</script>

<template>
  <PatientLayout>
    <header class="mb-6">
      <h1 class="font-display text-3xl font-bold text-slate-900 dark:text-white">Messagerie médecin-patient</h1>
      <p class="mt-1 text-slate-600 dark:text-slate-400">Conversation sécurisée en temps réel avec votre médecin</p>
    </header>

    <div class="grid gap-6 lg:grid-cols-3">
      <div class="rounded-2xl bg-white dark:bg-slate-800 p-4 shadow-sm dark:shadow-none lg:col-span-1">
        <h2 class="mb-3 text-sm font-semibold text-slate-500 dark:text-slate-400">Conversations</h2>
        <button
          v-for="c in conversations" :key="c.id"
          class="mb-2 w-full rounded-xl px-3 py-2 text-left text-sm transition"
          :class="activeConv?.id === c.id ? 'bg-teal-100 text-teal-900 dark:text-teal-100' : 'hover:bg-slate-50 dark:hover:bg-slate-800/50 dark:bg-slate-800/60'"
          @click="openConv(c)"
        >
          <p class="font-medium">{{ c.medecin_nom }}</p>
          <p class="truncate text-xs text-slate-500 dark:text-slate-400">{{ c.dernier_message || 'Nouvelle conversation' }}</p>
          <span v-if="c.non_lus" class="text-xs text-red-600 dark:text-red-400">{{ c.non_lus }} non lu(s)</span>
        </button>

        <h2 class="mb-2 mt-6 text-sm font-semibold text-slate-500 dark:text-slate-400">Nouveau contact</h2>
        <button
          v-for="m in medecins" :key="m.id"
          class="mb-1 w-full rounded-lg px-3 py-2 text-left text-sm hover:bg-teal-50 dark:bg-teal-950/40"
          @click="startWith(m.id)"
        >
          Dr {{ m.first_name }} {{ m.last_name }}
        </button>
      </div>

      <div class="flex flex-col rounded-2xl bg-white dark:bg-slate-800 shadow-sm dark:shadow-none lg:col-span-2">
        <div v-if="activeConv" class="border-b px-4 py-3">
          <p class="font-semibold">{{ activeConv.medecin_nom }}</p>
          <p class="text-xs text-teal-600 dark:text-teal-400">{{ activeConv.medecin_specialty }}</p>
        </div>
        <div v-else class="flex flex-1 items-center justify-center p-8 text-slate-400 dark:text-slate-500">
          Sélectionnez ou démarrez une conversation
        </div>

        <div v-if="activeConv" ref="chatBox" class="flex-1 space-y-3 overflow-y-auto p-4" style="max-height: 400px">
          <div
            v-for="msg in messages" :key="msg.id"
            class="max-w-[80%] rounded-2xl px-4 py-2 text-sm"
            :class="msg.auteur_id === activeConv.medecin_id
              ? 'bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-100'
              : 'ml-auto bg-teal-600 text-white'"
          >
            <p>{{ msg.contenu }}</p>
            <p class="mt-1 text-xs opacity-70">{{ fmt(msg.created_at) }}</p>
          </div>
        </div>

        <div v-if="activeConv" class="flex gap-2 border-t p-4">
          <input v-model="newMsg" class="input-field flex-1" placeholder="Votre message..." @keyup.enter="send" />
          <button class="rounded-xl bg-teal-600 px-4 py-2 text-white" @click="send">Envoyer</button>
        </div>
      </div>
    </div>
  </PatientLayout>
</template>
