import { onBeforeUnmount, watchEffect } from 'vue'

/**
 * 滚动容器内的“触底加载”：用 IntersectionObserver 监听哨兵元素。
 * rootRef 必须是真正滚动的那个元素。
 */
export function useInfiniteScroll(rootRef, targetRef, onReach, { rootMargin = '280px 0px' } = {}) {
  let observer = null

  const stop = watchEffect(() => {
    const root = rootRef.value
    const target = targetRef.value
    if (!root || !target) return

    observer?.disconnect()
    observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) onReach()
      },
      { root, rootMargin, threshold: 0 }
    )
    observer.observe(target)
  })

  onBeforeUnmount(() => {
    stop()
    observer?.disconnect()
    observer = null
  })
}
