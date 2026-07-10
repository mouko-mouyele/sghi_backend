import { applyInputFilter } from '../utils/inputFilters.js'

function onInput(el, kind) {
  const filtered = applyInputFilter(el.value, kind)
  if (filtered !== el.value) {
    el.value = filtered
    el.dispatchEvent(new Event('input', { bubbles: true }))
  }
}

export default {
  mounted(el, binding) {
    const kind = binding.value || binding.arg || 'text'
    const handler = () => onInput(el, kind)
    el.addEventListener('input', handler)
    el._inputFilterKind = kind
    el._inputFilterHandler = handler
    onInput(el, kind)
  },
  updated(el, binding) {
    const kind = binding.value || binding.arg || 'text'
    if (kind !== el._inputFilterKind) {
      el.removeEventListener('input', el._inputFilterHandler)
      const handler = () => onInput(el, kind)
      el.addEventListener('input', handler)
      el._inputFilterKind = kind
      el._inputFilterHandler = handler
    }
  },
  unmounted(el) {
    if (el._inputFilterHandler) {
      el.removeEventListener('input', el._inputFilterHandler)
    }
  },
}
