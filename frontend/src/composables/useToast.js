import { ref } from 'vue'

// 模块级单例：任意组件调用 useToast() 都操作同一条提示
const toast = ref(null)
let timer = 0

function push(text, type = 'info') {
  if (!text) return
  clearTimeout(timer)
  toast.value = { text, type }
  timer = setTimeout(() => {
    toast.value = null
  }, 2200)
}

export function useToast() {
  return {
    toast,
    success: (text) => push(text, 'success'),
    error: (text) => push(text, 'error'),
    info: (text) => push(text, 'info')
  }
}
