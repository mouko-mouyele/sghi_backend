import { createRouter, createWebHistory } from 'vue-router'
import LoginView from '../views/LoginView.vue'
import RegisterView from '../views/RegisterView.vue'
import DashboardView from '../views/DashboardView.vue'
import PatientsView from '../views/PatientsView.vue'
import LaboratoryView from '../views/LaboratoryView.vue'
import HospitalizationView from '../views/HospitalizationView.vue'
import MedecinsView from '../views/MedecinsView.vue'
import PharmacyView from '../views/PharmacyView.vue'
import BillingView from '../views/BillingView.vue'
import AdminOverview from '../views/admin/AdminOverview.vue'
import AdminAppointments from '../views/admin/AdminAppointments.vue'
import AppointmentsView from '../views/AppointmentsView.vue'
import AdminMedecins from '../views/admin/AdminMedecins.vue'
import AdminSecretaries from '../views/admin/AdminSecretaries.vue'
import AdminPatients from '../views/admin/AdminPatients.vue'
import AdminUsers from '../views/admin/AdminUsers.vue'
import AdminCreateUser from '../views/admin/AdminCreateUser.vue'
import AdminTeam from '../views/admin/AdminTeam.vue'
import AdminServices from '../views/admin/AdminServices.vue'
import AdminEmergencies from '../views/admin/AdminEmergencies.vue'
import AdminInfos from '../views/admin/AdminInfos.vue'
import AdminSecurity from '../views/admin/AdminSecurity.vue'
import NursingView from '../views/NursingView.vue'
import PlanningGardesView from '../views/PlanningGardesView.vue'
import PatientHome from '../views/patient/PatientHome.vue'
import PatientAppointments from '../views/patient/PatientAppointments.vue'
import PatientDossier from '../views/patient/PatientDossier.vue'
import PatientLab from '../views/patient/PatientLab.vue'
import PatientSoins from '../views/patient/PatientSoins.vue'
import PatientMessages from '../views/patient/PatientMessages.vue'
import PatientEtablissement from '../views/patient/PatientEtablissement.vue'
import PatientFacturation from '../views/patient/PatientFacturation.vue'
import PatientPharmacy from '../views/patient/PatientPharmacy.vue'
import PatientQrScan from '../views/patient/PatientQrScan.vue'
import { getHomeRoute, isLoggedIn } from '../utils/auth.js'

const routes = [
  { path: '/login', name: 'login', component: LoginView, meta: { guest: true } },
  { path: '/register', name: 'register', component: RegisterView, meta: { guest: true } },
  { path: '/qr/:token', component: PatientQrScan, meta: { publicQr: true } },
  { path: '/', name: 'dashboard', component: DashboardView },
  { path: '/patients', name: 'patients', component: PatientsView },
  { path: '/hospitalisation', name: 'hospitalization', component: HospitalizationView },
  { path: '/soins-infirmiers', name: 'nursing', component: NursingView, meta: { staffRoles: ['ADMIN', 'INFIRMIER', 'MEDECIN'] } },
  { path: '/medecins', name: 'medecins', component: MedecinsView, meta: { staffRoles: ['ADMIN', 'RECEPTIONNISTE'] } },
  { path: '/laboratoire', name: 'laboratory', component: LaboratoryView },
  { path: '/pharmacie', name: 'pharmacy', component: PharmacyView },
  { path: '/facturation', name: 'billing', component: BillingView },
  { path: '/planning-gardes', name: 'planning-gardes', component: PlanningGardesView, meta: { staffRoles: ['ADMIN', 'MEDECIN', 'INFIRMIER'] } },
  { path: '/rendez-vous', name: 'appointments', component: AppointmentsView, meta: { staffRoles: ['ADMIN', 'RECEPTIONNISTE'] } },
  { path: '/admin', name: 'admin', component: AdminOverview, meta: { adminOnly: true } },
  { path: '/admin/rendez-vous', component: AdminAppointments, meta: { adminOnly: true } },
  { path: '/admin/medecins', component: AdminMedecins, meta: { adminOnly: true } },
  { path: '/admin/secretaires', component: AdminSecretaries, meta: { adminOnly: true } },
  { path: '/admin/patients', component: AdminPatients, meta: { adminOnly: true } },
  { path: '/admin/utilisateurs', component: AdminUsers, meta: { adminOnly: true } },
  { path: '/admin/equipe', component: AdminTeam, meta: { adminOnly: true } },
  { path: '/admin/services', component: AdminServices, meta: { adminOnly: true } },
  { path: '/admin/urgences', component: AdminEmergencies, meta: { adminOnly: true } },
  { path: '/admin/infos', component: AdminInfos, meta: { adminOnly: true } },
  { path: '/admin/securite', component: AdminSecurity, meta: { adminOnly: true } },
  { path: '/admin/creer-compte', component: AdminCreateUser, meta: { adminOnly: true } },
  { path: '/patient', component: PatientHome, meta: { patientOnly: true } },
  { path: '/patient/rendez-vous', component: PatientAppointments, meta: { patientOnly: true } },
  { path: '/patient/dossier', component: PatientDossier, meta: { patientOnly: true } },
  { path: '/patient/laboratoire', component: PatientLab, meta: { patientOnly: true } },
  { path: '/patient/pharmacie', component: PatientPharmacy, meta: { patientOnly: true } },
  { path: '/patient/soins', component: PatientSoins, meta: { patientOnly: true } },
  { path: '/patient/messages', component: PatientMessages, meta: { patientOnly: true } },
  { path: '/patient/factures', component: PatientFacturation, meta: { patientOnly: true } },
  { path: '/patient/etablissement', component: PatientEtablissement, meta: { patientOnly: true } },
  { path: '/:pathMatch(.*)*', redirect: '/login' },
]

const router = createRouter({ history: createWebHistory(), routes })

router.beforeEach((to) => {
  const loggedIn = isLoggedIn()
  const role = localStorage.getItem('role') || ''

  if (to.meta.guest) {
    if (loggedIn && role && !to.meta.publicQr) return getHomeRoute(role)
    return true
  }

  if (to.meta.publicQr) return true

  if (!loggedIn) return '/login'

  if (to.meta.patientOnly && role !== 'PATIENT') return getHomeRoute(role)

  if (role === 'PATIENT' && !to.meta.guest && !to.meta.patientOnly) {
    return '/patient'
  }

  if (to.meta.adminOnly && role !== 'ADMIN') return getHomeRoute(role)

  if (to.meta.staffRoles && !to.meta.staffRoles.includes(role)) return getHomeRoute(role)

  return true
})

export default router
