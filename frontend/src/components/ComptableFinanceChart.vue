<script setup>

import { ref, computed, onMounted, watch } from 'vue'

import { Line } from 'vue-chartjs'

import {

  Chart as ChartJS,

  CategoryScale,

  LinearScale,

  PointElement,

  LineElement,

  Title,

  Tooltip,

  Legend,

  Filler,

} from 'chart.js'

import { dashboard } from '../api/client.js'



ChartJS.register(

  CategoryScale,

  LinearScale,

  PointElement,

  LineElement,

  Title,

  Tooltip,

  Legend,

  Filler,

)



const props = defineProps({

  jours: { type: Number, default: 14 },

})



const loading = ref(true)

const error = ref('')

const series = ref(null)



const COLORS = {

  recettes: { line: '#22c55e', fill: 'rgba(34, 197, 94, 0.25)' },

  impayes: { line: '#ef4444', fill: 'rgba(239, 68, 68, 0.2)' },

  payees: { line: '#3b82f6', fill: 'rgba(59, 130, 246, 0.2)' },

  brouillons: { line: '#eab308', fill: 'rgba(234, 179, 8, 0.2)' },

  operations: { line: '#ffffff', fill: 'rgba(255, 255, 255, 0.08)' },

}



async function loadChart() {

  loading.value = true

  error.value = ''

  try {

    const { data } = await dashboard.comptableChart(props.jours)

    series.value = data

  } catch (e) {

    error.value = e.response?.data?.detail || 'Graphique indisponible'

    series.value = {

      labels: [],

      recettes: [],

      impayes: [],

      payees: [],

      brouillons: [],

      operations: [],

    }

  } finally {

    loading.value = false

  }

}



onMounted(loadChart)

watch(() => props.jours, loadChart)



const chartData = computed(() => {

  const s = series.value

  if (!s?.labels?.length) return null

  return {

    labels: s.labels,

    datasets: [

      {

        label: 'Recettes (FCFA)',

        data: s.recettes,

        borderColor: COLORS.recettes.line,

        backgroundColor: COLORS.recettes.fill,

        borderWidth: 3,

        tension: 0.4,

        fill: true,

        yAxisID: 'y',

        pointRadius: 4,

        pointHoverRadius: 6,

      },

      {

        label: 'Impayés (FCFA)',

        data: s.impayes,

        borderColor: COLORS.impayes.line,

        backgroundColor: COLORS.impayes.fill,

        borderWidth: 3,

        tension: 0.4,

        fill: true,

        yAxisID: 'y',

        pointRadius: 4,

      },

      {

        label: 'Factures payées (FCFA)',

        data: s.payees,

        borderColor: COLORS.payees.line,

        backgroundColor: COLORS.payees.fill,

        borderWidth: 3,

        tension: 0.4,

        fill: true,

        yAxisID: 'y',

        pointRadius: 4,

      },

      {

        label: 'Brouillons (FCFA)',

        data: s.brouillons,

        borderColor: COLORS.brouillons.line,

        backgroundColor: COLORS.brouillons.fill,

        borderWidth: 3,

        tension: 0.4,

        fill: true,

        yAxisID: 'y',

        pointRadius: 4,

      },

      {

        label: 'Opérations (nb)',

        data: s.operations,

        borderColor: COLORS.operations.line,

        backgroundColor: COLORS.operations.fill,

        borderWidth: 2,

        borderDash: [6, 4],

        tension: 0.35,

        fill: false,

        yAxisID: 'y1',

        pointRadius: 3,

        pointBackgroundColor: '#ffffff',

        pointBorderColor: '#94a3b8',

      },

    ],

  }

})



const chartOptions = computed(() => ({

  responsive: true,

  maintainAspectRatio: false,

  interaction: { mode: 'index', intersect: false },

  plugins: {

    legend: {

      position: 'top',

      labels: {

        color: '#e2e8f0',

        usePointStyle: true,

        padding: 16,

        font: { size: 12, weight: '500' },

      },

    },

    tooltip: {

      backgroundColor: 'rgba(15, 23, 42, 0.95)',

      titleColor: '#f8fafc',

      bodyColor: '#e2e8f0',

      borderColor: '#334155',

      borderWidth: 1,

      callbacks: {

        label(ctx) {

          const v = ctx.parsed.y

          if (ctx.dataset.yAxisID === 'y1') return `${ctx.dataset.label}: ${v}`

          return `${ctx.dataset.label}: ${Number(v).toLocaleString('fr-FR')} FCFA`

        },

      },

    },

  },

  scales: {

    x: {

      grid: { color: 'rgba(148, 163, 184, 0.15)' },

      ticks: { color: '#94a3b8', maxRotation: 45 },

    },

    y: {

      type: 'linear',

      position: 'left',

      grid: { color: 'rgba(148, 163, 184, 0.12)' },

      ticks: {

        color: '#94a3b8',

        callback: (v) => `${Number(v).toLocaleString('fr-FR')}`,

      },

      title: { display: true, text: 'Montants FCFA', color: '#94a3b8' },

    },

    y1: {

      type: 'linear',

      position: 'right',

      grid: { drawOnChartArea: false },

      ticks: { color: '#f8fafc', stepSize: 1 },

      title: { display: true, text: 'Nb opérations', color: '#f8fafc' },

      min: 0,

    },

  },

}))



const legendItems = [

  { color: '#22c55e', label: 'Vert — Recettes encaissées' },

  { color: '#ef4444', label: 'Rouge — Montants impayés' },

  { color: '#3b82f6', label: 'Bleu — Factures soldées' },

  { color: '#eab308', label: 'Jaune — Factures brouillon' },

  { color: '#ffffff', label: 'Blanc — Nombre d\'opérations' },

]

</script>



<template>

  <div class="overflow-hidden rounded-2xl bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-6 shadow-xl ring-1 ring-slate-700/50">

    <div class="mb-6 flex flex-wrap items-start justify-between gap-4">

      <div>

        <h2 class="font-display text-xl font-bold text-white">Évolution financière</h2>

        <p class="mt-1 text-sm text-slate-400">Courbes en temps réel — {{ jours }} derniers jours</p>

      </div>

      <div class="flex flex-wrap gap-3 text-xs">

        <span

          v-for="item in legendItems"

          :key="item.label"

          class="flex items-center gap-1.5 rounded-full bg-slate-800/80 px-3 py-1 text-slate-300"

        >

          <span

            class="h-2.5 w-2.5 rounded-full ring-2 ring-slate-600"

            :style="{ backgroundColor: item.color }"

          />

          {{ item.label }}

        </span>

      </div>

    </div>



    <div v-if="loading" class="flex h-80 items-center justify-center">

      <div class="h-10 w-10 animate-spin rounded-full border-4 border-slate-600 border-t-emerald-400" />

    </div>



    <div v-else-if="error" class="flex h-80 items-center justify-center text-amber-400">{{ error }}</div>



    <div v-else-if="chartData" class="h-80 w-full">

      <Line :data="chartData" :options="chartOptions" />

    </div>



    <p v-else class="py-12 text-center text-slate-500">Aucune donnée financière sur cette période.</p>

  </div>

</template>


