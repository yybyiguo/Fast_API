import { ref } from 'vue'
import { fetchCategories } from '../api/news'

// 分类是全局共享的：首页用，详情页用来显示分类名
const categories = ref([])
const loading = ref(false)
const error = ref('')

let pending = null

export function useCategories() {
  async function load(force = false) {
    if (!force && categories.value.length) return categories.value
    if (pending) return pending

    loading.value = true
    error.value = ''

    pending = fetchCategories()
      .then((list) => {
        categories.value = list
        return list
      })
      .catch((err) => {
        error.value = err.message || '分类加载失败'
        throw err
      })
      .finally(() => {
        loading.value = false
        pending = null
      })

    return pending
  }

  function nameOf(id) {
    return categories.value.find((item) => item.id === Number(id))?.name || ''
  }

  return { categories, loading, error, load, nameOf }
}
