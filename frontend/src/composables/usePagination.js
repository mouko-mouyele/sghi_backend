import { ref, computed } from 'vue'

export function usePagination(initialPageSize = 10) {
  const page = ref(1)
  const pageSize = ref(initialPageSize)
  const total = ref(0)
  const totalPages = ref(0)

  const from = computed(() => (total.value ? (page.value - 1) * pageSize.value + 1 : 0))
  const to = computed(() => Math.min(page.value * pageSize.value, total.value))

  function applyMeta(data) {
    total.value = data.total ?? 0
    totalPages.value = data.total_pages ?? 0
    page.value = data.page ?? 1
    pageSize.value = data.page_size ?? pageSize.value
  }

  function resetPage() {
    page.value = 1
  }

  function params(extra = {}) {
    return { page: page.value, page_size: pageSize.value, ...extra }
  }

  return { page, pageSize, total, totalPages, from, to, applyMeta, resetPage, params }
}
