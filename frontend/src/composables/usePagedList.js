import { ref } from 'vue'

/**
 * 分页列表：统一 loading / 上拉加载 / 是否还有更多 / 错误状态。
 * fetchPage(page, pageSize) 由页面提供，返回 { list, total, hasMore }。
 */
export function usePagedList(fetchPage, { pageSize = 10 } = {}) {
  const items = ref([])
  const total = ref(0)
  const page = ref(0)
  const hasMore = ref(true)
  const loading = ref(false)
  const loadingMore = ref(false)
  const error = ref('')

  async function run(target, reset) {
    if (loading.value || loadingMore.value) return
    if (!reset && !hasMore.value) return

    if (reset) {
      loading.value = true
    } else {
      loadingMore.value = true
    }
    error.value = ''

    try {
      const result = await fetchPage(target, pageSize)
      const list = result.list ?? []

      items.value = reset ? list : items.value.concat(list)
      page.value = target
      total.value = Number(result.total ?? items.value.length)
      hasMore.value = result.hasMore ?? list.length >= pageSize
    } catch (err) {
      error.value = err.message || '加载失败'
      if (reset) {
        items.value = []
        total.value = 0
        hasMore.value = true
      }
      throw err
    } finally {
      loading.value = false
      loadingMore.value = false
    }
  }

  const reload = () => run(1, true)
  const loadMore = () => run(page.value + 1, false)

  return {
    items,
    total,
    page,
    hasMore,
    loading,
    loadingMore,
    error,
    reload,
    loadMore
  }
}
