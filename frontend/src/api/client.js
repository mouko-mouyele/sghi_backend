import axios from 'axios'
import { clearSession, isJustLoggedIn, isValidToken } from '../utils/auth.js'

const api = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' },
})

let isRefreshing = false
let pending = []

function processQueue(err, token = null) {
  pending.forEach((p) => (err ? p.reject(err) : p.resolve(token)))
  pending = []
}

const PUBLIC_AUTH_PATHS = [
  '/auth/login',
  '/auth/login/mfa',
  '/auth/register/patient',
  '/auth/refresh',
]

function isPublicAuthRoute(url = '') {
  return PUBLIC_AUTH_PATHS.some((path) => url.includes(path))
}

api.interceptors.request.use((config) => {
  const url = config.url || ''
  if (!isPublicAuthRoute(url)) {
    const token = localStorage.getItem('access_token')
    if (isValidToken(token)) config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

function redirectToLogin() {
  if (window.location.pathname.startsWith('/login') || window.location.pathname.startsWith('/register')) {
    return
  }
  clearSession()
  window.location.href = '/login'
}

api.interceptors.response.use(
  (r) => r,
  async (error) => {
    const original = error.config || {}
    const url = original.url || ''
    if (isPublicAuthRoute(url) || isJustLoggedIn()) {
      return Promise.reject(error)
    }
    if (error.response?.status === 401 && !original._retry) {
      const refresh = localStorage.getItem('refresh_token')
      if (!isValidToken(refresh)) {
        redirectToLogin()
        return Promise.reject(error)
      }
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          pending.push({ resolve, reject })
        }).then((token) => {
          original.headers.Authorization = `Bearer ${token}`
          return api(original)
        })
      }
      original._retry = true
      isRefreshing = true
      try {
        const { data } = await axios.post('/api/v1/auth/refresh', { refresh_token: refresh })
        localStorage.setItem('access_token', data.access_token)
        localStorage.setItem('refresh_token', data.refresh_token)
        processQueue(null, data.access_token)
        original.headers.Authorization = `Bearer ${data.access_token}`
        return api(original)
      } catch (e) {
        processQueue(e, null)
        redirectToLogin()
        return Promise.reject(e)
      } finally {
        isRefreshing = false
      }
    }
    return Promise.reject(error)
  },
)

export const auth = {
  login: (username, password) => api.post('/auth/login', { username, password }),
  loginMfa: (pendingToken, code) => api.post('/auth/login/mfa', { pending_token: pendingToken, code }),
  registerPatient: (data) => api.post('/auth/register/patient', data),
  registerStaff: (data) => api.post('/auth/register/staff', data),
  logout: () => api.post('/auth/logout', { refresh_token: localStorage.getItem('refresh_token') }),
  me: () => api.get('/auth/me'),
  listUsers: (params) => api.get('/auth/users', { params }),
  uploadMyPhoto: (file) => {
    const fd = new FormData()
    fd.append('photo', file)
    return api.post('/auth/me/photo', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
  },
}

export const dashboard = {
  kpis: () => api.get('/dashboard/kpis'),
  moi: () => api.get('/dashboard/moi'),
  comptableChart: (jours = 14) => api.get('/dashboard/comptable-graphe', { params: { jours } }),
}
export const nursing = {
  planning: (params) => api.get('/soins/planning', { params }),
  missedDoses: () => api.get('/soins/alertes-doses-omises'),
  createCare: (data) => api.post('/soins', data),
  completeCare: (id) => api.post(`/soins/${id}/realiser`),
  recordVitals: (data) => api.post('/constantes', data),
  vitals: (hospId) => api.get(`/constantes/${hospId}`),
}
export const hr = {
  shifts: (params) => api.get('/gardes', { params }),
  createShift: (data) => api.post('/gardes', data),
}
export const patients = {
  list: (params) => api.get('/patients', { params }),
  create: (data) => api.post('/patients', data),
}
export const medecins = {
  list: (params) => api.get('/medecins', { params }),
  disponibles: () => api.get('/medecins/disponibles'),
  setDisponibilite: (id, disponible_rdv) =>
    api.patch(`/medecins/${id}/disponibilite`, { disponible_rdv }),
}
export const hospitalization = {
  beds: (serviceId) => api.get('/lits/disponibles', { params: { service_id: serviceId || 0 } }),
  create: (data) => api.post('/hospitalisations', data),
  list: (params) => api.get('/hospitalisations', { params }),
  active: () => api.get('/hospitalisations/actives'),
  update: (id, data) => api.patch(`/hospitalisations/${id}`, data),
  transfer: (id, data) => api.post(`/hospitalisations/${id}/transfert`, data),
  discharge: (id, data) => api.post(`/hospitalisations/${id}/sortie`, data),
}
export const laboratory = {
  dashboard: () => api.get('/laboratoire/tableau-de-bord'),
  exams: () => api.get('/laboratoire/examens'),
  orders: (statut) => api.get('/laboratoire/commandes', { params: { statut } }),
  createOrder: (data) => api.post('/laboratoire/commandes', data),
  advanceWorkflow: (orderId, statut) => api.post(`/laboratoire/commandes/${orderId}/workflow`, { statut }),
  submitResult: (orderId, data) => api.post(`/laboratoire/commandes/${orderId}/resultats`, data),
  validateResult: (id) => api.post(`/laboratoire/resultats/${id}/valider`),
  exportCsv: async (statut) => {
    const res = await api.get('/laboratoire/commandes/export/csv', {
      params: { statut: statut || undefined },
      responseType: 'blob',
    })
    const date = new Date().toISOString().slice(0, 10)
    const url = window.URL.createObjectURL(new Blob([res.data], { type: 'text/csv;charset=utf-8' }))
    const a = document.createElement('a')
    a.href = url
    a.download = `sghl-laboratoire-${date}.csv`
    document.body.appendChild(a)
    a.click()
    a.remove()
    window.URL.revokeObjectURL(url)
  },
}
export const pharmacy = {
  medications: (params) => api.get('/pharmacie/medicaments', { params }),
  categories: () => api.get('/pharmacie/medicaments/categories'),
  stocks: () => api.get('/pharmacie/stocks'),
  alerts: () => api.get('/pharmacie/alertes'),
  movements: () => api.get('/pharmacie/mouvements'),
  requests: (params) => api.get('/pharmacie/demandes', { params }),
  updateRequestStatus: (id, statut) => api.patch(`/pharmacie/demandes/${id}/statut`, { statut }),
}
export const billing = {
  invoices: (params) => api.get('/finances/factures', { params }),
  get: (id) => api.get(`/finances/factures/${id}`),
  createInvoice: (data) => api.post('/finances/factures', data),
  addLine: (id, data) => api.post(`/finances/factures/${id}/lignes`, data),
  updateLine: (invoiceId, lineId, data) => api.patch(`/finances/factures/${invoiceId}/lignes/${lineId}`, data),
  deleteLine: (invoiceId, lineId, reinitialiser = false) =>
    api.delete(`/finances/factures/${invoiceId}/lignes/${lineId}`, {
      params: { reinitialiser_paiements: reinitialiser || undefined },
    }),
  updateMontant: (id, data) => api.patch(`/finances/factures/${id}/montant`, data),
  emit: (id) => api.post(`/finances/factures/${id}/emettre`),
  pay: (id, data) => api.post(`/finances/factures/${id}/paiements`, data),
  markUnpaid: (id) => api.post(`/finances/factures/${id}/marquer-impayee`),
  markPaid: (id) => api.post(`/finances/factures/${id}/marquer-payee`),
  initMobileMoney: (id, data) => api.post(`/finances/factures/${id}/mobile-money/initier`, data),
  confirmMobileMoney: (id, data) => api.post(`/finances/factures/${id}/mobile-money/confirmer`, data),
  approveMobileMoney: (txId, data) => api.post(`/finances/mobile-money/${txId}/approuver`, data),
  mobileMoneyStatus: (txId) => api.get(`/finances/mobile-money/${txId}/statut`),
  journal: (params) => api.get('/finances/journal', { params }),
}

export function getRole() {
  return localStorage.getItem('role') || ''
}

export { setSession, clearSession } from '../utils/auth.js'

export default api
