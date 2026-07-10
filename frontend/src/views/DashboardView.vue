<script setup>

import { onMounted, ref } from 'vue'

import AppLayout from '../components/AppLayout.vue'

import StatCard from '../components/StatCard.vue'

import ComptableFinanceChart from '../components/ComptableFinanceChart.vue'

import { useRoleDashboard } from '../composables/useRoleDashboard.js'



const {

  stats,

  cardGroups,

  pageTitle,

  quickLinks,

  effectiveRole,

  roleStats,

  loading,

  loadError,

  load,

} = useRoleDashboard()



const chartDays = ref(14)



onMounted(load)

</script>



<template>

  <AppLayout>

    <header class="mb-8">

      <h1 class="font-display text-3xl font-bold text-slate-900 dark:text-white">{{ pageTitle }}</h1>

      <p class="mt-1 text-slate-500 dark:text-slate-400">

        {{ roleStats?.role_label || effectiveRole }} — statistiques en temps réel

      </p>

    </header>



    <div v-if="loading" class="flex h-64 items-center justify-center">

      <div class="h-10 w-10 animate-spin rounded-full border-4 border-primary-200 border-t-primary-600" />

    </div>



    <template v-else>

      <div v-if="loadError" class="mb-6 rounded-xl bg-amber-50 px-4 py-3 text-sm text-amber-800 dark:bg-amber-950/40 dark:text-amber-200">

        {{ loadError }} — affichage avec les valeurs disponibles.

      </div>



      <div v-for="(group, gi) in cardGroups" :key="gi" class="mb-8 grid gap-5 sm:grid-cols-2 xl:grid-cols-4">

        <StatCard

          v-for="(card, ci) in group"

          :key="`${gi}-${ci}`"

          :title="card.title"

          :value="card.value"

          :subtitle="card.subtitle"

          :icon="card.icon"

          :color="card.color"

        />

      </div>



      <div v-if="effectiveRole === 'COMPTABLE' || effectiveRole === 'ADMIN'" class="mb-8">

        <div class="mb-4 flex flex-wrap items-center justify-between gap-3">

          <p class="text-sm font-medium text-slate-600 dark:text-slate-400">Courbes financières (données réelles)</p>

          <select v-model.number="chartDays" class="input-field w-40 text-sm">

            <option :value="7">7 jours</option>

            <option :value="14">14 jours</option>

            <option :value="30">30 jours</option>

          </select>

        </div>

        <ComptableFinanceChart :key="chartDays" :jours="chartDays" />

      </div>



      <div class="grid gap-6 lg:grid-cols-3">

        <div class="card lg:col-span-2">

          <h2 class="font-display text-lg font-semibold text-slate-800 dark:text-slate-100">Activité hospitalière</h2>

          <div class="mt-6 grid grid-cols-2 gap-4 text-center sm:grid-cols-4">

            <div class="rounded-xl bg-primary-50 p-4 dark:bg-primary-950/40">

              <p class="text-2xl font-bold text-primary-700 dark:text-primary-300">{{ stats.patients_total }}</p>

              <p class="text-xs text-slate-500">Patients</p>

            </div>

            <div class="rounded-xl bg-emerald-50 p-4 dark:bg-emerald-950/40">

              <p class="text-2xl font-bold text-emerald-700 dark:text-emerald-300">{{ stats.lits_disponibles }}</p>

              <p class="text-xs text-slate-500">Lits libres</p>

            </div>

            <div class="rounded-xl bg-violet-50 p-4 dark:bg-violet-950/40">

              <p class="text-2xl font-bold text-violet-700">{{ stats.hospitalisations_actives }}</p>

              <p class="text-xs text-slate-500">Hospitalisations</p>

            </div>

            <div class="rounded-xl bg-amber-50 p-4 dark:bg-amber-950/40">

              <p class="text-2xl font-bold text-amber-700">{{ stats.doses_omises }}</p>

              <p class="text-xs text-slate-500">Doses omises</p>

            </div>

          </div>

        </div>



        <div class="card">

          <h2 class="font-display text-lg font-semibold text-slate-800 dark:text-slate-100">Accès rapide</h2>

          <ul v-if="quickLinks.length" class="mt-4 space-y-2 text-sm">

            <li v-for="link in quickLinks" :key="link.to">

              <router-link :to="link.to" class="text-primary-600 hover:underline">→ {{ link.label }}</router-link>

            </li>

          </ul>

          <p v-else class="mt-4 text-sm text-slate-400">Utilisez le menu à gauche pour naviguer.</p>

        </div>

      </div>

    </template>

  </AppLayout>

</template>


