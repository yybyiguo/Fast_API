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
import { clearFavorites, fetchFavorites, shiftFavorite } from '../api/favorite'
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
  router.replace({ name: 'login', query: { redirect: '/favorites' } })
  return true
}

async function fetchPage(page, pageSize) {
  try {
    return await fetchFavorites(page, pageSize)
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
    await shiftFavorite(item.id)
    items.value = items.value.filter((entry) => entry.id !== item.id)
    total.value = Math.max(0, total.value - 1)
    toast.success('已取消收藏')
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
    await clearFavorites()
    toast.success('已清空收藏')
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
    <AppHeader title="我的收藏">
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
        icon="heart"
        title="还没有收藏"
        description="看到喜欢的资讯，在详情页点一下收藏，就会出现在这里"
        action-text="去首页看看"
        @action="router.push('/')"
      />

      <div v-else class="list">
        <SavedItem
          v-for="item in items"
          :key="item.id"
          :item="item"
          action="heart"
          :time-text="item.createdAt ? `收藏于 ${formatRelativeTime(item.createdAt)}` : ''"
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
      title="清空收藏"
      message="确定清空全部收藏吗？清空后无法恢复。"
      confirm-text="清空"
      :busy="confirmState.busy"
      @cancel="confirmState.open = false"
      @confirm="doClear"
    />
  </div>
</template>

<style scoped>
.header-action {
  height: 30px;
  padding: 0 14px;
  border: 1px solid var(--pill-border);
  border-radius: var(--pill);
  color: var(--ink);
  background: transparent;
  font-size: 11.5px;
  letter-spacing: 0.02em;
}

.header-action:disabled {
  border-color: var(--hairline);
  color: #4d5158;
}

.list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 14px 12px 0;
}

.sentinel {
  height: 1px;
}
</style>
