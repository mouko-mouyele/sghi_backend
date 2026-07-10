/**
 * Filtres de saisie — respect du type attendu par champ :
 * - digits : chiffres uniquement
 * - letters : lettres uniquement (+ espaces, tirets, apostrophes)
 * - phone : téléphone (+ chiffres, espaces, tirets)
 * - text : chaîne de caractères (texte libre)
 * - alnum : lettres et chiffres (identifiants, dossiers)
 * - decimal : nombres décimaux
 */

const LETTERS_RE = /[^a-zA-ZÀ-ÿ\s'\-]/g
const DIGITS_RE = /\D/g
const PHONE_RE = /[^\d+\s\-]/g
const ALNUM_RE = /[^a-zA-Z0-9_\-.]/g
const DECIMAL_RE = /[^\d.,]/g

export function filterDigits(value) {
  return String(value ?? '').replace(DIGITS_RE, '')
}

export function filterLetters(value) {
  return String(value ?? '').replace(LETTERS_RE, '')
}

export function filterPhone(value) {
  const raw = String(value ?? '').trim()
  if (!raw) return ''
  let cleaned = raw.replace(PHONE_RE, '')
  const plus = cleaned.startsWith('+') ? '+' : ''
  cleaned = cleaned.replace(/\+/g, '')
  return plus + cleaned
}

export function filterText(value) {
  const allowed = new Set(" .,;:'\"()-/\\#@&°\n\r\t")
  return String(value ?? '')
    .split('')
    .filter((c) => c.match(/[a-zA-ZÀ-ÿ0-9]/) || allowed.has(c))
    .join('')
}

export function filterAlnum(value) {
  return String(value ?? '').replace(ALNUM_RE, '')
}

export function filterDecimal(value) {
  const raw = String(value ?? '').replace(DECIMAL_RE, '')
  const sep = raw.includes(',') && !raw.includes('.') ? ',' : '.'
  const parts = raw.replace(',', '.').split('.')
  if (parts.length <= 1) return parts[0]
  return parts[0] + sep + parts.slice(1).join('')
}

const FILTERS = {
  digits: filterDigits,
  letters: filterLetters,
  phone: filterPhone,
  text: filterText,
  alnum: filterAlnum,
  decimal: filterDecimal,
}

export function applyInputFilter(value, kind = 'text') {
  const fn = FILTERS[kind] || FILTERS.text
  return fn(value)
}
