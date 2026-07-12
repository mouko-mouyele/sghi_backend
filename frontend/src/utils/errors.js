/** Extrait un message lisible depuis une erreur API Django Ninja / Axios. */
export function parseApiError(error, fallback = 'Une erreur est survenue') {
  const detail = error?.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail.map((item) => item.msg || item.message || JSON.stringify(item)).join(' · ')
  }
  const status = error?.response?.status
  if (status === 401) return 'Identifiants incorrects — vérifiez le nom d\'utilisateur et le mot de passe.'
  if (status === 502 || status === 503) {
    return 'Le serveur Render démarre ou est occupé — attendez 30 secondes puis réessayez.'
  }
  if (error?.code === 'ECONNABORTED' || error?.message?.includes('timeout')) {
    return 'Délai dépassé — le serveur met trop de temps à répondre (Render gratuit : réessayez après le réveil du service).'
  }
  if (!error?.response) {
    return 'Impossible de joindre le serveur — vérifiez votre connexion internet ou réessayez dans un instant.'
  }
  return fallback
}
