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
        <span class="feed-label"><i class="live-dot" aria-hidden="true"></i>推荐</span>
        <span>{{ total }} 条</span>
      </div>

      <NewsCard
        v-for="(item, index) in items"
        :key="item.id"
        :item="item"
        :index="index"
        :featured="index === 0"
        :category-name="categoryName"
        @open="open"
      />

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
  padding-bottom: calc(14px + var(--safe-bottom));
  background: var(--paper);
}

.feed {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 10px 14px 0;
}

.feed-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 2px 2px 0;
  color: var(--muted);
  font-size: 11px;
  font-weight: 500;
  letter-spacing: 0.04em;
}

.feed-label {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: var(--ink);
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0;
}

.live-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--red);
  box-shadow: 0 0 0 4px rgba(254, 44, 85, 0.16);
}

.sentinel {
  height: 1px;
}

@media (min-width: 1200px) {
  .feed {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    gap: 22px;
    padding: 18px 40px 8px;
  }

  .feed-head {
    grid-column: 1 / -1;
    padding: 0 2px 2px;
  }

  .feed :deep(.story.featured) {
    grid-column: 1 / -1;
  }

  .feed :deep(.footer) {
    grid-column: 1 / -1;
  }
}

@media (min-width: 1800px) {
  .feed {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}
</style>
