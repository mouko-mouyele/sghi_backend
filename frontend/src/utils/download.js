/**
 * Téléchargement de fichier (PDF, CSV…) — compatible Chrome / Edge / Firefox.
 */
export async function downloadBlob(blob, filename, mime = 'application/octet-stream') {
  const data = blob instanceof Blob ? blob : new Blob([blob], { type: mime })
  const url = window.URL.createObjectURL(data)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.style.display = 'none'
  document.body.appendChild(a)
  a.click()
  setTimeout(() => {
    document.body.removeChild(a)
    window.URL.revokeObjectURL(url)
  }, 200)
}

export function parseFilename(contentDisposition, fallback = 'document.pdf') {
  if (!contentDisposition) return fallback
  const utf8 = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i)
  if (utf8) return decodeURIComponent(utf8[1])
  const simple = contentDisposition.match(/filename="?([^";\n]+)"?/i)
  return simple ? simple[1].trim() : fallback
}

/**
 * GET authentifié via fetch (évite les soucis axios + blob).
 */
export async function downloadAuthenticated(apiPath, fallbackName = 'document.pdf') {
  const token = localStorage.getItem('access_token')
  const res = await fetch(`/api/v1${apiPath}`, {
    method: 'GET',
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })

  const contentType = res.headers.get('Content-Type') || ''

  if (!res.ok) {
    let detail = `Erreur ${res.status}`
    try {
      if (contentType.includes('json')) {
        const err = await res.json()
        detail = err.detail || detail
      } else {
        const text = await res.text()
        if (text) detail = text.slice(0, 200)
      }
    } catch { /* ignore */ }
    throw new Error(detail)
  }

  const blob = await res.blob()
  if (contentType.includes('json') || blob.type.includes('json')) {
    const text = await blob.text()
    try {
      const err = JSON.parse(text)
      throw new Error(err.detail || 'Réponse invalide')
    } catch (e) {
      if (e.message && !e.message.includes('JSON')) throw e
      throw new Error('Le serveur n\'a pas renvoyé un PDF valide')
    }
  }

  const filename = parseFilename(res.headers.get('Content-Disposition'), fallbackName)
  await downloadBlob(blob, filename, contentType.includes('pdf') ? 'application/pdf' : blob.type)
  return {
    filename,
    mediaUrl: res.headers.get('X-PDF-Media-Url') || '',
    chemin: res.headers.get('X-PDF-Path') || '',
  }
}
