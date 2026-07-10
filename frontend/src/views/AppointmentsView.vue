<script setup>
import { computed } from 'vue'
import AdminLayout from '../components/AdminLayout.vue'
import AppLayout from '../components/AppLayout.vue'
import AppointmentManager from '../components/AppointmentManager.vue'
import { getRole } from '../api/client.js'

const role = computed(() => getRole())
</script>

<template>
  <AdminLayout v-if="role === 'ADMIN'">
    <AppointmentManager />
  </AdminLayout>
  <AppLayout v-else>
    <AppointmentManager />
  </AppLayout>
</template>
