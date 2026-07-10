import api from './client.js'

function downloadBlob(data, filename) {
  const url = window.URL.createObjectURL(new Blob([data]))
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  window.URL.revokeObjectURL(url)
}

export const adminApi = {
  stats: () => api.get('/admin/statistiques'),
  exportStatsPdf: async () => {
    const res = await api.get('/admin/statistiques/pdf', { responseType: 'blob' })
    const date = new Date().toISOString().slice(0, 10)
    downloadBlob(res.data, `sghl-statistiques-${date}.pdf`)
  },
  appointments: (params) => api.get('/admin/rendez-vous', { params }),
  createAppointment: (data) => api.post('/admin/rendez-vous', data),
  updateAppointment: (id, data) => api.patch(`/admin/rendez-vous/${id}`, data),
  editAppointment: (id, data) => api.put(`/admin/rendez-vous/${id}`, data),
  deleteAppointment: (id) => api.delete(`/admin/rendez-vous/${id}`),
  // Patients
  updatePatient: (id, data) => api.put(`/admin/patients/${id}`, data),
  deletePatient: (id) => api.delete(`/admin/patients/${id}`),
  // Médecins
  medecins: (params) => api.get('/admin/medecins', { params }),
  updateMedecin: (id, data) => api.put(`/admin/medecins/${id}`, data),
  deleteMedecin: (id) => api.delete(`/admin/medecins/${id}`),
  // Secrétaires
  secretaires: (params) => api.get('/admin/secretaires', { params }),
  updateSecretaire: (id, data) => api.put(`/admin/secretaires/${id}`, data),
  deleteSecretaire: (id) => api.delete(`/admin/secretaires/${id}`),
  deactivateUser: (id) => api.patch(`/admin/utilisateurs/${id}/desactiver`),
  team: (params) => api.get('/admin/equipe', { params }),
  services: () => api.get('/admin/services'),
  createService: (data) => api.post('/admin/services', data),
  urgences: () => api.get('/admin/urgences'),
  infos: () => api.get('/admin/infos-pratiques'),
  updateInfos: (data) => api.put('/admin/infos-pratiques', data),
  loginJournal: (params) => api.get('/admin/journal-connexions', { params }),
  mfaStatus: () => api.get('/admin/mfa'),
  mfaEnable: () => api.post('/admin/mfa/enable'),
  mfaDisable: () => api.post('/admin/mfa/disable'),
  uploadUserPhoto: (userId, file) => {
    const fd = new FormData()
    fd.append('photo', file)
    return api.post(`/admin/utilisateurs/${userId}/photo`, fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
}
