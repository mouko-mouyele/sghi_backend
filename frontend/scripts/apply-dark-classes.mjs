/**
 * Ajoute les variantes Tailwind dark: aux classes communes (idempotent).
 * Usage: node scripts/apply-dark-classes.mjs
 */
import { readFileSync, writeFileSync, readdirSync, statSync } from 'fs'
import { join, dirname } from 'path'
import { fileURLToPath } from 'url'

const root = join(dirname(fileURLToPath(import.meta.url)), '..', 'src')

const REPLACEMENTS = [
  ['text-slate-900 dark:text-white', 'text-slate-900'],
  ['text-slate-800 dark:text-slate-100', 'text-slate-800'],
  ['text-slate-700 dark:text-slate-300', 'text-slate-700'],
  ['text-slate-600 dark:text-slate-400', 'text-slate-600'],
  ['text-slate-500 dark:text-slate-400', 'text-slate-500'],
  ['text-slate-400 dark:text-slate-500', 'text-slate-400'],
  ['text-primary-900 dark:text-primary-100', 'text-primary-900'],
  ['text-primary-700 dark:text-primary-300', 'text-primary-700'],
  ['text-primary-600 dark:text-primary-400', 'text-primary-600'],
  ['text-teal-900 dark:text-teal-100', 'text-teal-900'],
  ['text-teal-600 dark:text-teal-400', 'text-teal-600'],
  ['text-violet-900 dark:text-violet-100', 'text-violet-900'],
  ['text-emerald-900 dark:text-emerald-100', 'text-emerald-900'],
  ['text-emerald-800 dark:text-emerald-200', 'text-emerald-800'],
  ['text-emerald-700 dark:text-emerald-300', 'text-emerald-700'],
  ['text-orange-900 dark:text-orange-100', 'text-orange-900'],
  ['text-orange-800 dark:text-orange-200', 'text-orange-800'],
  ['text-orange-700 dark:text-orange-300', 'text-orange-700'],
  ['text-amber-800 dark:text-amber-200', 'text-amber-800'],
  ['text-red-700 dark:text-red-300', 'text-red-700'],
  ['text-red-600 dark:text-red-400', 'text-red-600'],
  ['bg-white dark:bg-slate-800', 'bg-white'],
  ['bg-white/90 dark:bg-slate-900/95', 'bg-white/90'],
  ['bg-white/80 dark:bg-slate-900/90', 'bg-white/80'],
  ['bg-white/20 dark:bg-white/10', 'bg-white/20'],
  ['bg-slate-50 dark:bg-slate-800/60', 'bg-slate-50'],
  ['bg-slate-100 dark:bg-slate-800', 'bg-slate-100'],
  ['bg-slate-200 dark:bg-slate-700', 'bg-slate-200'],
  ['bg-primary-50 dark:bg-primary-950/40', 'bg-primary-50'],
  ['bg-primary-100 dark:bg-primary-900/40', 'bg-primary-100'],
  ['bg-violet-50 dark:bg-violet-950/40', 'bg-violet-50'],
  ['bg-violet-100 dark:bg-violet-900/40', 'bg-violet-100'],
  ['bg-emerald-50 dark:bg-emerald-950/40', 'bg-emerald-50'],
  ['bg-emerald-100 dark:bg-emerald-900/40', 'bg-emerald-100'],
  ['bg-teal-50 dark:bg-teal-950/40', 'bg-teal-50'],
  ['bg-blue-50 dark:bg-blue-950/40', 'bg-blue-50'],
  ['bg-amber-50 dark:bg-amber-950/40', 'bg-amber-50'],
  ['bg-orange-50 dark:bg-orange-950/40', 'bg-orange-50'],
  ['bg-red-50 dark:bg-red-950/40', 'bg-red-50'],
  ['border-slate-100 dark:border-slate-700', 'border-slate-100'],
  ['border-slate-200 dark:border-slate-600', 'border-slate-200'],
  ['border-slate-300 dark:border-slate-600', 'border-slate-300'],
  ['border-violet-100 dark:border-violet-800/60', 'border-violet-100'],
  ['border-violet-200 dark:border-violet-700', 'border-violet-200'],
  ['border-emerald-200 dark:border-emerald-800', 'border-emerald-200'],
  ['border-orange-200 dark:border-orange-800', 'border-orange-200'],
  ['border-teal-50 dark:border-slate-700/80', 'border-teal-50'],
  ['border-teal-100 dark:border-slate-700', 'border-teal-100'],
  ['hover:bg-slate-50 dark:hover:bg-slate-800/50', 'hover:bg-slate-50'],
  ['hover:bg-slate-100 dark:hover:bg-slate-700', 'hover:bg-slate-100'],
  ['hover:bg-primary-50 dark:hover:bg-slate-800', 'hover:bg-primary-50'],
  ['hover:border-primary-200 dark:hover:border-primary-700', 'hover:border-primary-200'],
  ['from-orange-50 dark:from-orange-950/30', 'from-orange-50'],
  ['to-amber-50 dark:to-amber-950/20', 'to-amber-50'],
  ['to-white dark:to-slate-900', 'to-white'],
  ['via-white dark:via-slate-900', 'via-white'],
  ['ring-orange-100 dark:ring-orange-900/50', 'ring-orange-100'],
  ['ring-red-100 dark:ring-red-900/50', 'ring-red-100'],
  ['shadow-sm dark:shadow-none', 'shadow-sm'],
]

function walk(dir, files = []) {
  for (const name of readdirSync(dir)) {
    const p = join(dir, name)
    if (statSync(p).isDirectory()) walk(p, files)
    else if (p.endsWith('.vue')) files.push(p)
  }
  return files
}

function patch(content) {
  let out = content
  for (const [replacement, token] of REPLACEMENTS) {
    if (out.includes(replacement)) continue
    out = out.split(token).join(replacement)
  }
  return out
}

let count = 0
for (const file of walk(root)) {
  const before = readFileSync(file, 'utf8')
  const after = patch(before)
  if (after !== before) {
    writeFileSync(file, after)
    count++
    console.log('updated', file.replace(root, ''))
  }
}
console.log(`Done — ${count} file(s) updated.`)
