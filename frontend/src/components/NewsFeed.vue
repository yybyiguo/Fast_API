<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { fetchNewsList } from '../api/news'
import { useInfiniteScroll } from '../composables/useInfiniteScroll'
import { usePagedList } from '../composables/usePagedList'
import { usePullRefresh } from '../composables/usePullRefresh'
import EmptyState from './EmptyState.vue'
import ListFooter from './ListFooter.vue'
import ListSkeleton from './ListSkeleton.vue'
import NewsCard from './NewsCard.vue'
import PullIndicator from './PullIndicator.vue'

const props = defineProps({
  categoryId: { type: Number, required: true },
  categoryName: { type: String, default: '' }
})

const router = useRouter()
const scroller = ref(null)
const sentinel = ref(null)

const { items, total, hasMore, loading, loadingMore, error, reload, loadMore } = usePagedList(
  (page, pageSize) => fetchNewsList({ categoryId: props.categoryId, page, pageSize })
)

const { pull, dragging, refreshing, ready } = usePullRefresh(scroller, async () => {
  try {
    await reload()
  } catch {
    /* 错误状态由 error 呈现 */
  }
})

useInfiniteScroll(scroller, sentinel, () => {
  if (loading.value || loadingMore.value || error.value || !hasMore.value) return
  loadMore().catch(() => {})
})

onMounted(() => {
  reload().catch(() => {})
})

async function refresh() {
  try {
    await reload()
  } catch {
    /* ignore */
  }
}

function open(item) {
  router.push({ name: 'detail', params: { id: item.id } })
}

defineExpose({ refresh })
</script>

<template>
  <div ref="scroller" class="scroll feed-scroll">
    <PullIndicator
      :pull="pull"
      :ready="ready"
      :refreshing="refreshing"
      :dragging="dragging"
      :threshold="62"
    />

    <ListSkeleton v-if="loading && !items.length" :count="4" />

    <EmptyState
      v-else-if="error && !items.length"
      icon="error"
      title="加载失败"
      :description="error"
      action-text="重新加载"
      @action="refresh"
    />

    <EmptyState
      v-else-if="!items.length"
      icon="news"
      title="这个分类还没有内容"
      :description="categoryName ? `「${categoryName}」暂时没有资讯，下拉刷新或切换其他分类看看` : '下拉刷新或切换其他分类看看'"
    />

    <div v-else class="feed">
      <div class="feed-head">
        <span class="label">LATEST</span>
        <span class="count">{{ total }} ITEMS</span>
      </div>

      <NewsCard v-for="item in items" :key="item.id" :item="item" @open="open" />

      <ListFooter
        :has-more="hasMore"
        :loading-more="loadingMore"
        :error="error"
        :total="total"
        @retry="loadMore().catch(() => {})"
      />
    </div>

    <div ref="sentinel" class="sentinel" aria-hidden="true"></div>
  </div>
</template>

<style scoped>
.feed-scroll {
  background: var(--canvas);
}

.feed {
  padding: 14px 12px 0;
}

.feed-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 4px 12px;
  color: #5f646c;
  font-family: var(--font-mono);
  font-size: 9.5px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
}

.feed :deep(.news-card + .news-card) {
  margin-top: 10px;
}

.sentinel {
  height: 1px;
}
</style>
