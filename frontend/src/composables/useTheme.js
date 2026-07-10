import { ref, readonly } from 'vue'

const STORAGE_KEY = 'sghl-theme'
/** @type {import('vue').Ref<'light' | 'dark' | 'system'>} */
const mode = ref('system')
const isDark = ref(false)
let initialized = false
let mediaQuery = null

function systemPrefersDark() {
  return window.matchMedia('(prefers-color-scheme: dark)').matches
}

function readStoredMode() {
  const saved = localStorage.getItem(STORAGE_KEY)
  if (saved === 'light' || saved === 'dark' || saved === 'system') return saved
  return 'system'
}

function effectiveDark(themeMode) {
  if (themeMode === 'dark') return true
  if (themeMode === 'light') return false
  return systemPrefersDark()
}

function applyEffective(themeMode) {
  const dark = effectiveDark(themeMode)
  isDark.value = dark
  document.documentElement.classList.toggle('dark', dark)
  document.documentElement.style.colorScheme = dark ? 'dark' : 'light'
}

function applyMode(themeMode) {
  mode.value = themeMode
  applyEffective(themeMode)
  localStorage.setItem(STORAGE_KEY, themeMode)
}

function onSystemPreferenceChange() {
  if (mode.value === 'system') applyEffective('system')
}

function setupSystemListener() {
  if (mediaQuery || typeof window === 'undefined') return
  mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
  if (mediaQuery.addEventListener) {
    mediaQuery.addEventListener('change', onSystemPreferenceChange)
  } else {
    mediaQuery.addListener(onSystemPreferenceChange)
  }
}

/** Appelé avant le montage Vue (main.js + index.html) pour éviter le flash. */
export function initTheme() {
  if (initialized) return
  initialized = true
  applyMode(readStoredMode())
  setupSystemListener()
}

const CYCLE_ORDER = ['light', 'system', 'dark']

export function useTheme() {
  initTheme()

  function setTheme(themeMode) {
    if (themeMode === 'light' || themeMode === 'dark' || themeMode === 'system') {
      applyMode(themeMode)
    }
  }

  function cycleTheme() {
    const idx = CYCLE_ORDER.indexOf(mode.value)
    applyMode(CYCLE_ORDER[(idx + 1) % CYCLE_ORDER.length])
  }

  return {
    mode: readonly(mode),
    isDark: readonly(isDark),
    setTheme,
    cycleTheme,
    /** @deprecated utiliser cycleTheme */
    toggleTheme: cycleTheme,
  }
}

export const THEME_OPTIONS = [
  { value: 'light', label: 'Clair', icon: '☀️', short: 'Clair' },
  { value: 'system', label: 'Système', icon: '💻', short: 'Auto' },
  { value: 'dark', label: 'Sombre', icon: '🌙', short: 'Sombre' },
]
