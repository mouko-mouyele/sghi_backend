import { ref, computed } from 'vue'
import { auth, dashboard } from '../api/client.js'

const EMPTY_STATS = {
  patients_total: 0,
  lits_disponibles: 0,
  lits_total: 0,
  taux_occupation: 0,
  hospitalisations_actives: 0,
  examens_en_attente: 0,
  recettes_mois: 0,
  recettes_jour: 0,
  doses_omises: 0,
  alertes_stock: 0,
  factures_impayees: 0,
  factures_payees_mois: 0,
  factures_brouillon: 0,
  montant_impaye_total: 0,
  paiements_jour: 0,
  soins_en_attente: 0,
  soins_en_retard: 0,
  soins_realises_jour: 0,
  rdv_aujourdhui: 0,
  rdv_en_attente: 0,
  demandes_pharmacie: 0,
  labo_a_valider: 0,
  labo_publies_jour: 0,
  mes_rdv_jour: 0,
  role_label: '',
}

function fmtMoney(n) {
  return `${Number(n || 0).toLocaleString('fr-FR')} FCFA`
}

function num(n) {
  return Number(n || 0)
}

/** Cartes statistiques par rôle — toujours au moins 8 indicateurs */
function cardsForRole(role, s) {
  const occ = `${s.taux_occupation}%`
  const lits = `/ ${s.lits_total}`
  switch (role) {
    case 'ADMIN':
      return [
        [
          { title: 'Recettes du mois', value: fmtMoney(s.recettes_mois), icon: '💰', color: 'accent' },
          { title: 'Recettes du jour', value: fmtMoney(s.recettes_jour), icon: '📈', color: 'primary' },
          { title: 'Factures impayées', value: s.factures_impayees, subtitle: fmtMoney(s.montant_impaye_total), icon: '📋', color: 'warning' },
          { title: 'Paiements aujourd\'hui', value: s.paiements_jour, icon: '✅', color: 'primary' },
        ],
        [
          { title: 'Hospitalisations', value: s.hospitalisations_actives, icon: '🏥', color: 'primary' },
          { title: 'Taux d\'occupation', value: occ, subtitle: `${s.lits_total - s.lits_disponibles} / ${s.lits_total} lits`, icon: '🛏️', color: 'primary' },
          { title: 'Soins en attente', value: s.soins_en_attente, icon: '📋', color: 'primary' },
          { title: 'RDV aujourd\'hui', value: s.rdv_aujourdhui, icon: '📅', color: 'primary' },
        ],
        [
          { title: 'Labo à valider', value: s.labo_a_valider, icon: '🔬', color: 'warning' },
          { title: 'Alertes stock', value: s.alertes_stock, icon: '💊', color: 'warning' },
          { title: 'Patients', value: s.patients_total, icon: '👥', color: 'accent' },
          { title: 'Doses omises', value: s.doses_omises, icon: '⚠️', color: 'warning' },
        ],
      ]
    case 'COMPTABLE':
      return [
        [
          { title: 'Recettes du mois', value: fmtMoney(s.recettes_mois), icon: '💰', color: 'accent' },
          { title: 'Recettes du jour', value: fmtMoney(s.recettes_jour), icon: '📈', color: 'primary' },
          { title: 'Factures impayées', value: s.factures_impayees, subtitle: fmtMoney(s.montant_impaye_total), icon: '📋', color: 'warning' },
          { title: 'Paiements aujourd\'hui', value: s.paiements_jour, icon: '✅', color: 'primary' },
        ],
        [
          { title: 'Factures payées (mois)', value: s.factures_payees_mois, icon: '🧾', color: 'accent' },
          { title: 'Factures brouillon', value: s.factures_brouillon, icon: '📝', color: 'primary' },
          { title: 'Montant impayé total', value: fmtMoney(s.montant_impaye_total), icon: '💳', color: 'warning' },
          { title: 'Patients enregistrés', value: s.patients_total, icon: '👥', color: 'primary' },
        ],
      ]
    case 'INFIRMIER':
      return [
        [
          { title: 'Soins en attente', value: s.soins_en_attente, icon: '📋', color: 'primary' },
          { title: 'Soins en retard', value: s.soins_en_retard, icon: '⏰', color: 'warning' },
          { title: 'Soins réalisés aujourd\'hui', value: s.soins_realises_jour, icon: '✅', color: 'accent' },
          { title: 'Doses omises', value: s.doses_omises, icon: '⚠️', color: 'warning' },
        ],
        [
          { title: 'Hospitalisations actives', value: s.hospitalisations_actives, icon: '🏥', color: 'primary' },
          { title: 'Patients', value: s.patients_total, icon: '👥', color: 'accent' },
          { title: 'Lits disponibles', value: s.lits_disponibles, subtitle: lits, icon: '🛏️', color: 'primary' },
          { title: 'Taux d\'occupation', value: occ, icon: '📊', color: 'primary' },
        ],
      ]
    case 'PHARMACIEN':
      return [
        [
          { title: 'Alertes stock', value: s.alertes_stock, icon: '💊', color: 'warning' },
          { title: 'Demandes patients', value: s.demandes_pharmacie, icon: '📦', color: 'primary' },
          { title: 'Hospitalisations', value: s.hospitalisations_actives, icon: '🏥', color: 'primary' },
          { title: 'Patients', value: s.patients_total, icon: '👥', color: 'accent' },
        ],
        [
          { title: 'Examens en attente', value: s.examens_en_attente, icon: '🔬', color: 'purple' },
          { title: 'Doses omises', value: s.doses_omises, icon: '⚠️', color: 'warning' },
          { title: 'Lits disponibles', value: s.lits_disponibles, subtitle: lits, icon: '🛏️', color: 'primary' },
          { title: 'Recettes du mois', value: fmtMoney(s.recettes_mois), icon: '💰', color: 'accent' },
        ],
      ]
    case 'RECEPTIONNISTE':
      return [
        [
          { title: 'RDV aujourd\'hui', value: s.rdv_aujourdhui, icon: '📅', color: 'primary' },
          { title: 'RDV en attente', value: s.rdv_en_attente, icon: '⏳', color: 'warning' },
          { title: 'Patients', value: s.patients_total, icon: '👥', color: 'accent' },
          { title: 'Lits disponibles', value: s.lits_disponibles, subtitle: lits, icon: '🛏️', color: 'primary' },
        ],
        [
          { title: 'Hospitalisations', value: s.hospitalisations_actives, icon: '🏥', color: 'primary' },
          { title: 'Taux d\'occupation', value: occ, icon: '📊', color: 'primary' },
          { title: 'Factures impayées', value: s.factures_impayees, icon: '📋', color: 'warning' },
          { title: 'Recettes du mois', value: fmtMoney(s.recettes_mois), icon: '💰', color: 'accent' },
        ],
      ]
    case 'MEDECIN':
      return [
        [
          { title: 'Mes RDV du jour', value: s.mes_rdv_jour, icon: '📅', color: 'primary' },
          { title: 'Hospitalisations', value: s.hospitalisations_actives, icon: '🏥', color: 'primary' },
          { title: 'Examens en attente', value: s.examens_en_attente, icon: '🔬', color: 'purple' },
          { title: 'Doses omises', value: s.doses_omises, icon: '⚠️', color: 'warning' },
        ],
        [
          { title: 'Patients', value: s.patients_total, icon: '👥', color: 'accent' },
          { title: 'Lits disponibles', value: s.lits_disponibles, subtitle: lits, icon: '🛏️', color: 'primary' },
          { title: 'Taux d\'occupation', value: occ, icon: '📊', color: 'primary' },
          { title: 'Soins en attente', value: s.soins_en_attente, icon: '📋', color: 'primary' },
        ],
      ]
    case 'BIOLOGISTE':
      return [
        [
          { title: 'À valider', value: s.labo_a_valider, icon: '🔬', color: 'warning' },
          { title: 'Publiés aujourd\'hui', value: s.labo_publies_jour, icon: '✅', color: 'accent' },
          { title: 'En attente LIS', value: s.examens_en_attente, icon: '📋', color: 'primary' },
          { title: 'Patients', value: s.patients_total, icon: '👥', color: 'primary' },
        ],
        [
          { title: 'Hospitalisations', value: s.hospitalisations_actives, icon: '🏥', color: 'primary' },
          { title: 'Lits disponibles', value: s.lits_disponibles, subtitle: lits, icon: '🛏️', color: 'primary' },
          { title: 'Alertes stock', value: s.alertes_stock, icon: '💊', color: 'warning' },
          { title: 'Recettes du mois', value: fmtMoney(s.recettes_mois), icon: '💰', color: 'accent' },
        ],
      ]
    default:
      return [[
        { title: 'Taux d\'occupation', value: occ, subtitle: `${s.lits_total - s.lits_disponibles} / ${s.lits_total} lits`, icon: '🛏️', color: 'primary' },
        { title: 'Hospitalisations actives', value: s.hospitalisations_actives, icon: '🏥', color: 'primary' },
        { title: 'Examens en attente', value: s.examens_en_attente, icon: '🔬', color: 'purple' },
        { title: 'Recettes du mois', value: fmtMoney(s.recettes_mois), icon: '💰', color: 'accent' },
      ]]
  }
}

const TITLES = {
  ADMIN: 'Tableau de bord administrateur',
  COMPTABLE: 'Tableau de bord comptable',
  INFIRMIER: 'Tableau de bord infirmier(ère)',
  MEDECIN: 'Tableau de bord médical',
  PHARMACIEN: 'Tableau de bord pharmacie',
  RECEPTIONNISTE: 'Tableau de bord secrétariat',
  BIOLOGISTE: 'Tableau de bord laboratoire',
}

export function useRoleDashboard() {
  const roleStats = ref(null)
  const kpis = ref(null)
  const userRole = ref('')
  const loading = ref(true)
  const loadError = ref('')

  const effectiveRole = computed(() => roleStats.value?.role || userRole.value || '')

  const stats = computed(() => {
    const k = kpis.value || {}
    const r = roleStats.value || {}
    const merged = { ...EMPTY_STATS }
    for (const key of Object.keys(EMPTY_STATS)) {
      if (r[key] !== undefined && r[key] !== null) merged[key] = r[key]
      else if (k[key] !== undefined && k[key] !== null) merged[key] = k[key]
    }
    merged.role_label = r.role_label || ''
    return merged
  })

  const cardGroups = computed(() => cardsForRole(effectiveRole.value, stats.value))

  const pageTitle = computed(() => TITLES[effectiveRole.value] || 'Tableau de bord')

  const quickLinks = computed(() => {
    const links = []
    const r = effectiveRole.value
    if (r === 'ADMIN') links.push({ to: '/admin', label: 'Panneau d\'administration' })
    if (['ADMIN', 'COMPTABLE', 'RECEPTIONNISTE'].includes(r)) links.push({ to: '/facturation', label: 'Facturation & journal' })
    if (['ADMIN', 'PHARMACIEN', 'COMPTABLE', 'MEDECIN', 'INFIRMIER', 'RECEPTIONNISTE', 'BIOLOGISTE'].includes(r)) links.push({ to: '/pharmacie', label: 'Pharmacie' })
    if (['ADMIN', 'MEDECIN', 'BIOLOGISTE'].includes(r)) links.push({ to: '/laboratoire', label: 'Laboratoire LIS' })
    if (['ADMIN', 'INFIRMIER', 'MEDECIN'].includes(r)) links.push({ to: '/soins-infirmiers', label: 'Soins infirmiers' })
    if (['ADMIN', 'MEDECIN', 'INFIRMIER', 'RECEPTIONNISTE'].includes(r)) links.push({ to: '/hospitalisation', label: 'Hospitalisation' })
    if (['ADMIN', 'RECEPTIONNISTE'].includes(r)) links.push({ to: '/rendez-vous', label: 'Rendez-vous' })
    if (['ADMIN', 'MEDECIN', 'INFIRMIER', 'RECEPTIONNISTE'].includes(r)) links.push({ to: '/patients', label: 'Patients' })
    if (['ADMIN', 'MEDECIN', 'INFIRMIER'].includes(r)) links.push({ to: '/planning-gardes', label: 'Planning de gardes' })
    if (['ADMIN', 'RECEPTIONNISTE'].includes(r)) links.push({ to: '/medecins', label: 'Médecins' })
    return links
  })

  async function load() {
    loading.value = true
    loadError.value = ''
    try {
      const { data: me } = await auth.me()
      userRole.value = me.role
      localStorage.setItem('role', me.role)
    } catch {
      userRole.value = localStorage.getItem('role') || ''
    }

    let moiOk = false
    let kpisOk = false
    try {
      const { data } = await dashboard.moi()
      roleStats.value = data
      moiOk = true
    } catch (e) {
      loadError.value = e.response?.data?.detail || ''
    }
    try {
      const { data } = await dashboard.kpis()
      kpis.value = data
      kpisOk = true
    } catch (e) {
      if (!loadError.value) loadError.value = e.response?.data?.detail || ''
    }
    if (!moiOk && !kpisOk && !loadError.value) {
      loadError.value = 'Impossible de charger les statistiques. Réessayez ou contactez l\'administrateur.'
    }
    loading.value = false
  }

  return {
    stats,
    cardGroups,
    pageTitle,
    quickLinks,
    effectiveRole,
    roleStats,
    loading,
    loadError,
    load,
    fmtMoney,
    num,
  }
}
