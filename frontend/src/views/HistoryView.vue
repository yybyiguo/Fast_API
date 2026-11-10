<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import AppHeader from '../components/AppHeader.vue'
import ConfirmDialog from '../components/ConfirmDialog.vue'
import EmptyState from '../components/EmptyState.vue'
import ListFooter from '../components/ListFooter.vue'
import ListSkeleton from '../components/ListSkeleton.vue'
import PullIndicator from '../components/PullIndicator.vue'
import SavedItem from '../components/SavedItem.vue'
import { clearHistory, fetchHistory, removeHistory } from '../api/history'
import { useInfiniteScroll } from '../composables/useInfiniteScroll'
import { usePagedList } from '../composables/usePagedList'
import { usePullRefresh } from '../composables/usePullRefresh'
import { useToast } from '../composables/useToast'
import { useAuth } from '../stores/auth'
import { formatRelativeTime } from '../utils/format'

const router = useRouter()
const auth = useAuth()
const toast = useToast()

const scroller = ref(null)
const sentinel = ref(null)
const removingId = ref(0)
const confirmState = reactive({ open: false, busy: false })

function handleAuthError(error) {
  if (error?.status !== 401) return false
  auth.logout()
  router.replace({ name: 'login', query: { redirect: '/history' } })
  return true
}

async function fetchPage(page, pageSize) {
  try {
    return await fetchHistory(page, pageSize)
  } catch (error) {
    handleAuthError(error)
    throw error
  }
}

const { items, total, hasMore, loading, loadingMore, error, reload, loadMore } = usePagedList(
  fetchPage
)

const { pull, dragging, refreshing, ready } = usePullRefresh(scroller, async () => {
  try {
    await reload()
  } catch {
    /* error 已记录 */
  }
})

useInfiniteScroll(scroller, sentinel, () => {
  if (loading.value || loadingMore.value || error.value || !hasMore.value) return
  loadMore().catch(() => {})
})

onMounted(() => {
  reload().catch(() => {})
})

function openItem(item) {
  router.push({ name: 'detail', params: { id: item.id } })
}

async function remove(item) {
  if (removingId.value) return
  removingId.value = item.id

  try {
    await removeHistory(item.id)
    items.value = items.value.filter((entry) => entry.id !== item.id)
    total.value = Math.max(0, total.value - 1)
    toast.success('已删除这条历史')
  } catch (err) {
    if (!handleAuthError(err)) toast.error(err.message)
  } finally {
    removingId.value = 0
  }
}

function askClear() {
  if (!items.value.length) return
  confirmState.open = true
}

async function doClear() {
  if (confirmState.busy) return
  confirmState.busy = true

  try {
    await clearHistory()
    toast.success('已清空浏览历史')
    confirmState.open = false
    items.value = []
    total.value = 0
    hasMore.value = false
  } catch (err) {
    if (!handleAuthError(err)) toast.error(err.message)
  } finally {
    confirmState.busy = false
  }
}
</script>

<template>
  <div class="page">
    <AppHeader title="历史">
      <button type="button" class="header-action" :disabled="!items.length" @click="askClear">
        清空
      </button>
    </AppHeader>

    <div ref="scroller" class="scroll">
      <PullIndicator
        :pull="pull"
        :ready="ready"
        :refreshing="refreshing"
        :dragging="dragging"
        :threshold="62"
      />

      <div class="page-head">
        <span class="kicker">READING HISTORY</span>
        <div class="head-row">
          <h1>浏览历史</h1>
          <span class="count">{{ total }} 篇</span>
        </div>
      </div>

      <ListSkeleton v-if="loading && !items.length" :count="4" />

      <EmptyState
        v-else-if="error && !items.length"
        icon="error"
        title="加载失败"
        :description="error"
        action-text="重新加载"
        @action="reload().catch(() => {})"
      />

      <EmptyState
        v-else-if="!items.length"
        icon="clock"
        title="还没有浏览记录"
        description="看过的资讯会自动记录在这里，方便回头再找"
        action-text="去首页看看"
        @action="router.push('/')"
      />

      <div v-else class="list">
        <SavedItem
          v-for="item in items"
          :key="item.id"
          :item="item"
          action="close"
          :time-text="item.viewedAt ? `${formatRelativeTime(item.viewedAt)}浏览` : ''"
          @open="openItem"
          @remove="remove"
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

    <ConfirmDialog
      :open="confirmState.open"
      title="清空历史"
      message="确定清空全部浏览历史吗？清空后无法恢复。"
      confirm-text="清空"
      :busy="confirmState.busy"
      @cancel="confirmState.open = false"
      @confirm="doClear"
    />
  </div>
</template>

<style scoped>
.scroll {
  background: var(--white);
}

.header-action {
  height: 30px;
  padding: 0 10px;
  border: 1px solid var(--red);
  color: var(--red);
  background: transparent;
  font-size: 11px;
  font-weight: 500;
}

.header-action:disabled {
  border-color: var(--line);
  color: #9ca3af;
}

.page-head {
  padding: 22px 16px 16px;
  border-bottom: 1px solid var(--ink);
}

.head-row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  margin-top: 10px;
}

h1 {
  color: var(--ink);
  font-family: var(--font-serif);
  font-size: 32px;
  font-weight: 700;
  line-height: 1.05;
  letter-spacing: -0.03em;
}

.count {
  flex: 0 0 auto;
  color: var(--muted);
  font-size: 11px;
}

.list {
  padding: 0 16px 8px;
}

.sentinel {
  height: 1px;
}
</style>
