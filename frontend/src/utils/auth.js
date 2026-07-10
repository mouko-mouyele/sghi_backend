/** Redirection après connexion — tous les personnels arrivent sur le tableau de bord */

export function getHomeRoute(role) {

  switch (role) {

    case 'PATIENT':

      return '/patient'

    default:

      return '/'

  }

}



export function isValidToken(value) {

  return Boolean(value && value !== 'undefined' && value !== 'null')

}



export function clearSession() {

  localStorage.removeItem('access_token')

  localStorage.removeItem('refresh_token')

  localStorage.removeItem('role')

  localStorage.removeItem('user_id')

  sessionStorage.removeItem('just_logged_in')

}



export function setSession(data) {

  if (!data?.access_token || !data?.refresh_token) {

    throw new Error('Réponse de connexion incomplète (tokens manquants)')

  }

  localStorage.setItem('access_token', data.access_token)

  localStorage.setItem('refresh_token', data.refresh_token)

  localStorage.setItem('role', String(data.role || ''))

  localStorage.setItem('user_id', String(data.user_id ?? ''))

  sessionStorage.setItem('just_logged_in', String(Date.now()))

}



export function isLoggedIn() {

  return isValidToken(localStorage.getItem('access_token'))

}



export function isJustLoggedIn() {

  const ts = Number(sessionStorage.getItem('just_logged_in') || 0)

  return ts > 0 && Date.now() - ts < 15000

}


