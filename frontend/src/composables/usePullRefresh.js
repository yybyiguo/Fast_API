import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

/**
 * 自定义下拉刷新：只在滚动容器顶部且向下拖动时接管手势，
 * 避免和浏览器自带的刷新/回弹冲突。
 */
export function usePullRefresh(scrollerRef, onRefresh, { threshold = 62, max = 92 } = {}) {
  const pull = ref(0)
  const dragging = ref(false)
  const refreshing = ref(false)
  const ready = computed(() => pull.value >= threshold)

  let startY = 0
  let tracking = false

  function onTouchStart(event) {
    const el = scrollerRef.value
    if (!el || refreshing.value) return
    if (el.scrollTop > 0) return
    startY = event.touches[0].clientY
    tracking = true
  }

  function onTouchMove(event) {
    if (!tracking) return
    const el = scrollerRef.value
    if (!el) return

    const dy = event.touches[0].clientY - startY
    if (dy <= 0 || el.scrollTop > 0) {
      if (pull.value !== 0) pull.value = 0
      if (dy < -6) tracking = false
      return
    }

    dragging.value = true
    if (event.cancelable) event.preventDefault()
    // 阻尼：越拉越沉
    pull.value = Math.min(max, dy * 0.5)
  }

  async function onTouchEnd() {
    if (!tracking) return
    tracking = false
    dragging.value = false

    if (pull.value >= threshold) {
      pull.value = 52
      refreshing.value = true
      try {
        await onRefresh()
      } finally {
        refreshing.value = false
        pull.value = 0
      }
    } else {
      pull.value = 0
    }
  }

  onMounted(() => {
    const el = scrollerRef.value
    if (!el) return
    el.addEventListener('touchstart', onTouchStart, { passive: true })
    el.addEventListener('touchmove', onTouchMove, { passive: false })
    el.addEventListener('touchend', onTouchEnd)
    el.addEventListener('touchcancel', onTouchEnd)
  })

  onBeforeUnmount(() => {
    const el = scrollerRef.value
    if (!el) return
    el.removeEventListener('touchstart', onTouchStart)
    el.removeEventListener('touchmove', onTouchMove)
    el.removeEventListener('touchend', onTouchEnd)
    el.removeEventListener('touchcancel', onTouchEnd)
  })

  return { pull, dragging, refreshing, ready, threshold }
}
