<script setup>
import { onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import ConfirmDialog from '../components/ConfirmDialog.vue'
import EmptyState from '../components/EmptyState.vue'
import ListSkeleton from '../components/ListSkeleton.vue'
import { rssApi } from '../api/rss'
import { useAuth } from '../stores/auth'
import { useCategories } from '../stores/categories'
import { useToast } from '../composables/useToast'
import { formatRelativeTime } from '../utils/format'

const router = useRouter()
const auth = useAuth()
const toast = useToast()
const { load: loadCategories } = useCategories()

const feeds = ref([])
const loading = ref(true)
const denied = ref(false)
const loadError = ref('')
const formOpen = ref(false)
const submitting = ref(false)
const refreshingId = ref(0)
const togglingId = ref(0)
const confirmState = reactive({ open: false, feed: null, busy: false })

const form = reactive({ name: '', url: '', fetchInterval: 900 })

let reloadTimer = 0

function normalizeFeed(raw = {}) {
  return {
    id: Number(raw.id ?? 0),
    name: raw.name || '',
    url: raw.url || '',
    categoryId: Number(raw.categoryId ?? raw.category_id ?? 0),
    enabled: raw.enabled !== false,
    fetchInterval: Number(raw.fetchInterval ?? raw.fetch_interval ?? 900),
    lastFetchAt: raw.lastFetchAt ?? raw.last_fetch_at ?? null,
    lastStatus: raw.lastStatus ?? raw.last_status ?? null,
    lastError: raw.lastError ?? raw.last_error ?? '',
    errorCount: Number(raw.errorCount ?? raw.error_count ?? 0)
  }
}

function handleAuthError(error) {
  if (error?.status === 401) {
    auth.logout()
    router.replace({ name: 'login', query: { redirect: '/rss' } })
    return true
  }
  if (error?.status === 403) {
    denied.value = true
    return true
  }
  return false
}

async function load() {
  loading.value = true
  loadError.value = ''
  denied.value = false

  try {
    const res = await rssApi.list()
    feeds.value = (res?.data ?? []).map(normalizeFeed)
  } catch (error) {
    if (!handleAuthError(error)) loadError.value = error.message
  } finally {
    loading.value = false
  }
}

function statusText(feed) {
  if (!feed.enabled) return '已停用'
  if (feed.lastStatus === 'ok') return '正常'
  if (feed.lastStatus === 'not_modified') return '无更新'
  if (feed.lastStatus === 'error') return '失败'
  return '未抓取'
}

function statusClass(feed) {
  if (!feed.enabled) return 'off'
  if (feed.lastStatus === 'error') return 'error'
  if (feed.lastStatus === 'ok') return 'ok'
  return 'idle'
}

function intervalText(seconds) {
  const value = Number(seconds) || 900
  if (value % 3600 === 0) return `每 ${value / 3600} 小时`
  if (value % 60 === 0) return `每 ${value / 60} 分钟`
  return `每 ${value} 秒`
}

async function submit() {
  if (submitting.value) return

  const name = form.name.trim()
  const url = form.url.trim()
  if (!name) {
    toast.error('给这个源起个名字')
    return
  }
  if (!/^(https?:\/\/|\/)/i.test(url)) {
    toast.error('地址要以 http:// 或 https:// 开头，或以 / 开头的 RSSHub 路径')
    return
  }

  submitting.value = true
  try {
    await rssApi.create({
      name,
      url,
      fetchInterval: form.fetchInterval
    })
    toast.success('已添加，首页会自动生成同名分类')
    form.name = ''
    form.url = ''
    formOpen.value = false
    // 新源会建一个同名分类，刷新全局分类，回到首页就能看到新 tab
    await loadCategories(true).catch(() => {})
    await load()
  } catch (error) {
    if (!handleAuthError(error)) toast.error(error.message)
  } finally {
    submitting.value = false
  }
}

async function toggle(feed) {
  if (togglingId.value) return
  togglingId.value = feed.id
  try {
    await rssApi.update(feed.id, { enabled: !feed.enabled })
    feed.enabled = !feed.enabled
    toast.success(feed.enabled ? '已启用' : '已停用')
  } catch (error) {
    if (!handleAuthError(error)) toast.error(error.message)
  } finally {
    togglingId.value = 0
  }
}

function scheduleReload() {
  clearTimeout(reloadTimer)
  reloadTimer = setTimeout(() => {
    load().catch(() => {})
  }, 3000)
}

async function refresh(feed) {
  if (refreshingId.value) return
  refreshingId.value = feed.id
  try {
    await rssApi.refresh(feed.id)
    toast.success('已加入抓取队列，稍后自动刷新')
    scheduleReload()
  } catch (error) {
    if (!handleAuthError(error)) toast.error(error.message)
  } finally {
    refreshingId.value = 0
  }
}

function askRemove(feed) {
  confirmState.feed = feed
  confirmState.open = true
}

async function doRemove() {
  if (confirmState.busy || !confirmState.feed) return
  confirmState.busy = true
  const target = confirmState.feed
  try {
    await rssApi.remove(target.id)
    feeds.value = feeds.value.filter((item) => item.id !== target.id)
    confirmState.open = false
    confirmState.feed = null
    // 空分类可能被后端一并删掉，刷新首页 tab
    await loadCategories(true).catch(() => {})
    toast.success('已删除')
  } catch (error) {
    if (!handleAuthError(error)) toast.error(error.message)
  } finally {
    confirmState.busy = false
  }
}

onMounted(() => {
  load().catch(() => {})
})

onBeforeUnmount(() => clearTimeout(reloadTimer))
</script>

<template>
  <div class="page">
    <header class="page-head">
      <div class="head-top">
        <span class="kicker no-rule">RSS SOURCES</span>
        <button v-if="!denied" type="button" class="header-action" @click="formOpen = !formOpen">
          {{ formOpen ? '收起' : '添加' }}
        </button>
      </div>
      <div class="head-row">
        <h1>订阅源</h1>
        <span class="count">{{ feeds.length }} 个</span>
      </div>
    </header>

    <div class="scroll">
      <p class="hint">定时抓取 RSS；每个源会在首页生成一个同名分类，文章只在那个分类下展示。</p>

      <form v-if="formOpen" class="card form" @submit.prevent="submit">
        <label class="field">
          <span>名称</span>
          <input v-model="form.name" type="text" maxlength="100" placeholder="例如：少数派" />
        </label>

        <label class="field">
          <span>Feed 地址</span>
          <input
            v-model="form.url"
            type="text"
            maxlength="500"
            inputmode="url"
            placeholder="https://sspai.com/feed 或 /bilibili/hot-search"
          />
        </label>

        <label class="field">
          <span>抓取间隔（秒）</span>
          <input v-model.number="form.fetchInterval" type="number" min="300" step="60" />
        </label>

        <button type="submit" class="primary" :disabled="submitting">
          {{ submitting ? '添加中…' : '添加订阅源' }}
        </button>
      </form>

      <EmptyState
        v-if="denied"
        icon="lock"
        title="没有管理权限"
        description="当前账号不在订阅管理员白名单里。用 admin 账号登录，或调整 .env 的 rss_admin_users。"
        action-text="返回我的"
        @action="router.replace('/profile')"
      />

      <ListSkeleton v-else-if="loading" :count="3" />

      <EmptyState
        v-else-if="loadError"
        icon="error"
        title="加载失败"
        :description="loadError"
        action-text="重新加载"
        @action="load"
      />

      <EmptyState
        v-else-if="!feeds.length"
        icon="rss"
        title="还没有订阅源"
        description="添加一个 RSS 地址，首页会以源名称生成一个分类并展示抓取到的文章。"
        action-text="添加第一个源"
        @action="formOpen = true"
      />

      <ul v-else class="list">
        <li v-for="feed in feeds" :key="feed.id" class="feed" :class="{ off: !feed.enabled }">
          <div class="feed-head">
            <span class="name">{{ feed.name }}</span>
            <span class="status" :class="statusClass(feed)">{{ statusText(feed) }}</span>
          </div>

          <p class="url">{{ feed.url }}</p>

          <p class="meta">
            <span>
              {{ feed.lastFetchAt ? `${formatRelativeTime(feed.lastFetchAt)}抓取` : '尚未抓取' }}
            </span>
            <span class="dot">·</span>
            <span>{{ intervalText(feed.fetchInterval) }}</span>
          </p>

          <p v-if="feed.lastError" class="error">{{ feed.lastError }}</p>

          <div class="ops">
            <button type="button" :disabled="refreshingId === feed.id" @click="refresh(feed)">
              {{ refreshingId === feed.id ? '抓取中…' : '立即抓取' }}
            </button>
            <button type="button" :disabled="togglingId === feed.id" @click="toggle(feed)">
              {{ feed.enabled ? '停用' : '启用' }}
            </button>
            <button type="button" class="danger" @click="askRemove(feed)">删除</button>
          </div>
        </li>
      </ul>
    </div>

    <ConfirmDialog
      :open="confirmState.open"
      title="删除订阅源"
      :message="`删除「${confirmState.feed?.name || ''}」后不再抓取；如果这个分类下已经有文章，分类会保留。`"
      confirm-text="删除"
      :busy="confirmState.busy"
      @cancel="confirmState.open = false"
      @confirm="doRemove"
    />
  </div>
</template>

<style scoped>
.scroll {
  background: var(--white);
  padding-bottom: calc(24px + var(--safe-bottom));
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

.page-head {
  flex: 0 0 auto;
  padding: calc(12px + var(--safe-top)) 16px 18px;
  border-top: 3px solid var(--red);
  border-bottom: 1px solid var(--ink);
  background: var(--paper);
}

.head-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
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

.hint {
  padding: 14px 16px 0;
  color: var(--muted);
  font-size: 12px;
  line-height: 1.7;
}

.card {
  margin: 16px 16px 0;
  padding: 20px 18px;
  border: 1px solid var(--line);
  border-top: 3px solid var(--red);
  background: var(--white);
}

.field {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 20px;
}

.field > span {
  color: var(--muted);
  font-size: 9px;
  font-weight: 500;
  letter-spacing: 0.14em;
}

.field input {
  width: 100%;
  height: 44px;
  padding: 0 2px;
  border: 0;
  border-bottom: 1px solid #d4d4d8;
  background: transparent;
  color: var(--ink);
  outline: none;
  transition: border-color 0.18s ease;
}

.field input:focus {
  border-bottom-color: var(--red);
}

.row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.primary {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 46px;
  border: 1px solid var(--red);
  color: var(--white);
  background: var(--red);
  font-size: 13px;
  font-weight: 500;
}

.primary:active:not(:disabled) {
  background: var(--red-dark);
}

.list {
  display: flex;
  flex-direction: column;
  margin: 0;
  padding: 0 16px;
  list-style: none;
}

.feed {
  padding: 18px 0;
  border-bottom: 1px solid var(--line);
}

.feed.off {
  opacity: 0.5;
}

.feed-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px;
}

.name {
  overflow: hidden;
  color: var(--ink);
  font-family: var(--font-serif);
  font-size: 21px;
  font-weight: 600;
  letter-spacing: -0.01em;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.status {
  flex: 0 0 auto;
  font-size: 9px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.status.ok {
  color: var(--red);
}

.status.error {
  color: var(--red-dark);
}

.status.idle,
.status.off {
  color: var(--muted);
}

.url {
  margin-top: 6px;
  overflow: hidden;
  color: #9ca3af;
  font-family: var(--font-mono);
  font-size: 9.5px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  margin-top: 8px;
  color: var(--muted);
  font-size: 11px;
}

.error {
  margin-top: 10px;
  padding: 8px 10px;
  border-left: 2px solid var(--red);
  color: var(--red-dark);
  background: var(--red-soft);
  font-size: 11.5px;
  line-height: 1.6;
  word-break: break-word;
}

.ops {
  display: flex;
  gap: 8px;
  margin-top: 14px;
}

.ops button {
  flex: 1;
  height: 34px;
  border: 1px solid var(--ink);
  color: var(--ink);
  background: transparent;
  font-size: 11.5px;
}

.ops button.danger {
  border-color: var(--red);
  color: var(--red);
}

.ops button:active:not(:disabled) {
  background: var(--red-soft);
}
</style>
