/** Extrait un message lisible depuis une erreur API Django Ninja / Axios. */
export function parseApiError(error, fallback = 'Une erreur est survenue') {
  const detail = error?.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail.map((item) => item.msg || item.message || JSON.stringify(item)).join(' · ')
  }
  return fallback
}
