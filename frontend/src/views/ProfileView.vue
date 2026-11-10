<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import ConfirmDialog from '../components/ConfirmDialog.vue'
import EmptyState from '../components/EmptyState.vue'
import ListFooter from '../components/ListFooter.vue'
import ListSkeleton from '../components/ListSkeleton.vue'
import SavedItem from '../components/SavedItem.vue'
import { clearFavorites, fetchFavorites, shiftFavorite } from '../api/favorite'
import { clearHistory, fetchHistory, removeHistory } from '../api/history'
import { useAuth } from '../stores/auth'
import { useToast } from '../composables/useToast'
import { usePagedList } from '../composables/usePagedList'
import { useInfiniteScroll } from '../composables/useInfiniteScroll'
import { formatRelativeTime, initialOf } from '../utils/format'
import { resolveAvatar } from '../utils/media'

const auth = useAuth()
const router = useRouter()
const route = useRoute()
const toast = useToast()

const profileScroll = ref(null)
const sentinel = ref(null)
const activeTab = ref(route.query.tab === 'history' ? 'history' : 'favorites')
const clearing = ref(false)
const removingId = ref(0)
let clearTimer = 0

const stats = reactive({ favorites: 0, history: 0, loaded: false })
const editOpen = ref(false)
const saving = ref(false)
const brokenAvatar = ref(false)
const confirmLogout = reactive({ open: false })

const form = reactive({ nickname: '', bio: '', gender: 'unknown' })

const user = computed(() => auth.user.value)
const avatar = computed(() =>
  user.value && !brokenAvatar.value ? resolveAvatar(user.value.avatar) : ''
)
const displayName = computed(() => user.value?.nickname || user.value?.username || '未登录')

const genders = [
  { value: 'male', label: '男' },
  { value: 'female', label: '女' },
  { value: 'unknown', label: '保密' }
]

function handleAuthError(error) {
  if (error?.status !== 401) return false
  auth.logout()
  router.replace({
    name: 'login',
    query: { redirect: `/profile?tab=${activeTab.value}` }
  })
  return true
}

async function fetchFavoritePage(page, pageSize) {
  try {
    return await fetchFavorites(page, pageSize)
  } catch (error) {
    handleAuthError(error)
    throw error
  }
}

async function fetchHistoryPage(page, pageSize) {
  try {
    return await fetchHistory(page, pageSize)
  } catch (error) {
    handleAuthError(error)
    throw error
  }
}

const favorites = usePagedList(fetchFavoritePage)
const history = usePagedList(fetchHistoryPage)

const active = computed(() => (activeTab.value === 'favorites' ? favorites : history))
const listItems = computed(() => active.value.items.value)
const listTotal = computed(() => active.value.total.value)
const listHasMore = computed(() => active.value.hasMore.value)
const listLoading = computed(() => active.value.loading.value)
const listLoadingMore = computed(() => active.value.loadingMore.value)
const listError = computed(() => active.value.error.value)
const isFavorites = computed(() => activeTab.value === 'favorites')

function listFor(tab) {
  return tab === 'favorites' ? favorites : history
}

function ensureLoaded(tab) {
  const list = listFor(tab)
  if (list.page.value === 0 && !list.loading.value) {
    list.reload().catch(() => {})
  }
}

function switchTab(tab) {
  if (tab === activeTab.value) return
  activeTab.value = tab
  clearing.value = false
  clearTimeout(clearTimer)
  router.replace({ name: 'profile', query: { ...route.query, tab } })
  if (auth.isLoggedIn.value) ensureLoaded(tab)
}

function reloadActive() {
  active.value.reload().catch(() => {})
}

function loadMoreActive() {
  active.value.loadMore().catch(() => {})
}

watch(
  () => route.query.tab,
  (tab) => {
    if (tab !== 'favorites' && tab !== 'history') return
    if (tab === activeTab.value) return
    activeTab.value = tab
    clearing.value = false
    if (auth.isLoggedIn.value) ensureLoaded(tab)
  }
)

watch(
  user,
  (value) => {
    brokenAvatar.value = false
    if (!value) {
      stats.favorites = 0
      stats.history = 0
      stats.loaded = false
      favorites.items.value = []
      favorites.total.value = 0
      favorites.hasMore.value = false
      history.items.value = []
      history.total.value = 0
      history.hasMore.value = false
      return
    }
    form.nickname = value.nickname || ''
    form.bio = value.bio || ''
    form.gender = value.gender || 'unknown'
  },
  { immediate: true }
)

useInfiniteScroll(profileScroll, sentinel, () => {
  if (!auth.isLoggedIn.value) return
  const list = active.value
  if (list.loading.value || list.loadingMore.value || list.error.value || !list.hasMore.value) return
  list.loadMore().catch(() => {})
})

onMounted(async () => {
  await auth.ensureReady()
  if (!auth.isLoggedIn.value) return
  loadStats()
  ensureLoaded(activeTab.value)
})

onBeforeUnmount(() => clearTimeout(clearTimer))

async function loadStats() {
  try {
    const [favoritesRes, historyRes] = await Promise.all([
      fetchFavorites(1, 1),
      fetchHistory(1, 1)
    ])
    stats.favorites = favoritesRes.total
    stats.history = historyRes.total
    stats.loaded = true
  } catch (error) {
    if (error.status === 401) auth.logout()
  }
}

function goLogin() {
  router.push({ name: 'login', query: { redirect: `/profile?tab=${activeTab.value}` } })
}

function openItem(item) {
  router.push({ name: 'detail', params: { id: item.id } })
}

async function removeItem(item) {
  if (removingId.value) return
  removingId.value = item.id

  try {
    if (isFavorites.value) {
      await shiftFavorite(item.id)
      favorites.items.value = favorites.items.value.filter((entry) => entry.id !== item.id)
      favorites.total.value = Math.max(0, favorites.total.value - 1)
      stats.favorites = Math.max(0, stats.favorites - 1)
      toast.success('已取消收藏')
    } else {
      await removeHistory(item.id)
      history.items.value = history.items.value.filter((entry) => entry.id !== item.id)
      history.total.value = Math.max(0, history.total.value - 1)
      stats.history = Math.max(0, stats.history - 1)
      toast.success('已删除这条历史')
    }
  } catch (error) {
    if (!handleAuthError(error)) toast.error(error.message)
  } finally {
    removingId.value = 0
  }
}

function askClear() {
  if (!listTotal.value) return
  if (clearing.value) {
    doClear()
    return
  }
  clearing.value = true
  clearTimeout(clearTimer)
  clearTimer = setTimeout(() => {
    clearing.value = false
  }, 3200)
}

async function doClear() {
  clearing.value = false
  clearTimeout(clearTimer)

  try {
    if (isFavorites.value) {
      await clearFavorites()
      favorites.items.value = []
      favorites.total.value = 0
      favorites.hasMore.value = false
      stats.favorites = 0
      toast.success('已清空收藏')
    } else {
      await clearHistory()
      history.items.value = []
      history.total.value = 0
      history.hasMore.value = false
      stats.history = 0
      toast.success('已清空浏览记录')
    }
  } catch (error) {
    if (!handleAuthError(error)) toast.error(error.message)
  }
}

function openEdit() {
  if (!user.value) return
  form.nickname = user.value.nickname || ''
  form.bio = user.value.bio || ''
  form.gender = user.value.gender || 'unknown'
  editOpen.value = true
}

async function saveProfile() {
  if (saving.value) return
  if (form.nickname.trim().length > 50) {
    toast.error('昵称最多 50 个字符')
    return
  }
  if (form.bio.trim().length > 500) {
    toast.error('个人简介最多 500 个字符')
    return
  }

  saving.value = true
  try {
    await auth.updateProfile({
      nickname: form.nickname.trim(),
      // 后端没挂载静态目录，保留原值即可（默认值不能直接当图片用）
      avatar: user.value?.avatar ?? null,
      gender: form.gender,
      bio: form.bio.trim()
    })
    toast.success('资料已更新')
    editOpen.value = false
  } catch (error) {
    if (error.status === 401) {
      auth.logout()
      goLogin()
      return
    }
    toast.error(error.message)
  } finally {
    saving.value = false
  }
}

function doLogout() {
  auth.logout()
  confirmLogout.open = false
  stats.favorites = 0
  stats.history = 0
  stats.loaded = false
  favorites.items.value = []
  favorites.total.value = 0
  favorites.hasMore.value = false
  history.items.value = []
  history.total.value = 0
  history.hasMore.value = false
  toast.success('已退出登录')
}
</script>

<template>
  <div class="page">
    <header class="profile-head">
      <div class="head-top">
        <span class="kicker no-rule">PROFILE</span>
        <button v-if="user" type="button" class="edit-btn" @click="openEdit">编辑资料</button>
      </div>

      <div v-if="!user" class="guest">
        <div class="avatar guest-avatar" aria-hidden="true">?</div>
        <h2>登录后更精彩</h2>
        <p>收藏喜欢的资讯，自动同步浏览历史</p>
        <button type="button" class="login-btn" @click="goLogin">
          登录 / 注册
          <span aria-hidden="true">→</span>
        </button>
      </div>

      <div v-else class="me">
        <div class="avatar">
          <img v-if="avatar" :src="avatar" alt="" @error="brokenAvatar = true" />
          <span v-else>{{ initialOf(displayName) }}</span>
        </div>
        <div class="me-info">
          <h2>{{ displayName }}</h2>
          <p class="username">@{{ user.username }}</p>
          <p class="bio">{{ user.bio || '这个人很懒，什么都没说' }}</p>
        </div>
      </div>
    </header>

    <div ref="profileScroll" class="scroll">
      <div class="tabs" role="tablist" aria-label="收藏与浏览记录">
        <button
          type="button"
          role="tab"
          class="tab"
          :class="{ active: activeTab === 'favorites' }"
          :aria-selected="activeTab === 'favorites'"
          @click="switchTab('favorites')"
        >
          <b>{{ stats.loaded ? stats.favorites : '–' }}</b>
          <span>收藏</span>
        </button>

        <button
          type="button"
          role="tab"
          class="tab"
          :class="{ active: activeTab === 'history' }"
          :aria-selected="activeTab === 'history'"
          @click="switchTab('history')"
        >
          <b>{{ stats.loaded ? stats.history : '–' }}</b>
          <span>浏览记录</span>
        </button>
      </div>

      <section class="panel">
        <div class="panel-head">
          <span class="panel-label">{{ isFavorites ? '我的收藏' : '浏览记录' }}</span>
          <div class="panel-actions">
            <span class="panel-count">{{ listTotal }} 篇</span>
            <button
              v-if="user && listTotal"
              type="button"
              class="clear"
              :class="{ confirm: clearing }"
              @click="askClear"
            >
              {{ clearing ? '确认清空' : '清空' }}
            </button>
          </div>
        </div>

        <div v-if="!user" class="login-note">
          <p>登录后可在这里查看收藏与浏览记录，使用上方按钮登录即可。</p>
        </div>

        <ListSkeleton v-else-if="listLoading && !listItems.length" :count="3" />

        <EmptyState
          v-else-if="listError && !listItems.length"
          icon="error"
          title="加载失败"
          :description="listError"
          action-text="重新加载"
          @action="reloadActive"
        />

        <EmptyState
          v-else-if="!listItems.length"
          :icon="isFavorites ? 'heart' : 'clock'"
          :title="isFavorites ? '还没有收藏' : '还没有浏览记录'"
          :description="
            isFavorites
              ? '看到喜欢的资讯，在详情页点一下收藏，就会出现在这里'
              : '看过的资讯会自动记录在这里，方便回头再找'
          "
          action-text="去首页看看"
          @action="router.push('/')"
        />

        <div v-else class="list">
          <SavedItem
            v-for="item in listItems"
            :key="item.id"
            :item="item"
            :action="isFavorites ? 'heart' : 'close'"
            :time-text="
              isFavorites
                ? item.createdAt
                  ? `收藏于 ${formatRelativeTime(item.createdAt)}`
                  : ''
                : item.viewedAt
                  ? `${formatRelativeTime(item.viewedAt)}浏览`
                  : ''
            "
            @open="openItem"
            @remove="removeItem"
          />

          <ListFooter
            :has-more="listHasMore"
            :loading-more="listLoadingMore"
            :error="listError"
            :total="listTotal"
            @retry="loadMoreActive"
          />
        </div>

        <div ref="sentinel" class="sentinel" aria-hidden="true"></div>
      </section>

      <div v-if="user" class="account-actions">
        <button type="button" class="logout" @click="confirmLogout.open = true">
          退出登录
        </button>
      </div>

      <div class="about">
        <p>今日资讯 · MOBILE EDITION</p>
        <p>VUE 3 / FASTAPI</p>
      </div>
    </div>

    <ConfirmDialog
      :open="confirmLogout.open"
      title="退出登录"
      message="退出后收藏和浏览历史仍会保留，下次登录可继续查看。"
      confirm-text="退出"
      :danger="false"
      @cancel="confirmLogout.open = false"
      @confirm="doLogout"
    />

    <Teleport to="body">
      <Transition name="sheet">
        <div v-if="editOpen" class="sheet-mask" @click.self="!saving && (editOpen = false)">
          <div class="sheet" role="dialog" aria-modal="true" aria-label="编辑资料">
            <div class="grabber" aria-hidden="true"></div>

            <div class="sheet-head">
              <div>
                <span class="kicker no-rule">EDIT PROFILE</span>
                <h3>编辑资料</h3>
              </div>
              <button type="button" class="close" aria-label="关闭" :disabled="saving" @click="editOpen = false">
                <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
                  <path d="M6 6l12 12M18 6 6 18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
                </svg>
              </button>
            </div>

            <label class="field">
              <span class="label">NICKNAME / 昵称</span>
              <input v-model="form.nickname" type="text" maxlength="50" placeholder="给自己起个昵称" />
              <em>{{ form.nickname.length }}/50</em>
            </label>

            <label class="field">
              <span class="label">BIO / 个人简介</span>
              <textarea v-model="form.bio" rows="3" maxlength="500" placeholder="介绍一下自己"></textarea>
              <em>{{ form.bio.length }}/500</em>
            </label>

            <div class="field">
              <span class="label">GENDER / 性别</span>
              <div class="segmented">
                <button
                  v-for="option in genders"
                  :key="option.value"
                  type="button"
                  :class="{ active: form.gender === option.value }"
                  @click="form.gender = option.value"
                >
                  {{ option.label }}
                </button>
              </div>
            </div>

            <button type="button" class="save" :disabled="saving" @click="saveProfile">
              {{ saving ? '保存中…' : '保存' }}
              <span aria-hidden="true">→</span>
            </button>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<style scoped>
.profile-head {
  flex: 0 0 auto;
  padding: calc(12px + var(--safe-top)) 16px 22px;
  border-top: 3px solid var(--red);
  border-bottom: 1px solid var(--line);
  background:
    radial-gradient(120% 80% at 50% -20%, rgba(254, 44, 85, 0.16), transparent 62%),
    var(--paper);
}

.head-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.edit-btn {
  height: 30px;
  padding: 0 14px;
  border: 1px solid var(--line);
  border-radius: 999px;
  color: var(--ink);
  background: rgba(255, 255, 255, 0.04);
  font-size: 11px;
  font-weight: 600;
  transition: background 0.18s ease, color 0.18s ease;
}

.edit-btn:active {
  color: #fff;
  background: var(--red);
}

.guest,
.me {
  margin-top: 24px;
}

.guest {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

.avatar {
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  width: 64px;
  height: 64px;
  overflow: hidden;
  border: 2px solid rgba(254, 44, 85, 0.7);
  border-radius: 50%;
  color: var(--ink);
  background: var(--surface-2);
  box-shadow: 0 0 0 4px rgba(254, 44, 85, 0.12);
  font-family: var(--font-serif);
  font-size: 26px;
  font-weight: 700;
}

.avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.guest-avatar {
  width: 56px;
  height: 56px;
  border-color: var(--line);
  color: var(--muted);
  box-shadow: none;
  font-family: var(--font-mono);
  font-size: 18px;
}

.guest h2 {
  margin-top: 22px;
  color: var(--ink);
  font-family: var(--font-serif);
  font-size: clamp(30px, 9vw, 38px);
  font-weight: 700;
  line-height: 1.1;
  letter-spacing: -0.03em;
}

.guest p {
  margin-top: 10px;
  color: var(--muted);
  font-size: 12.5px;
}

.login-btn {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  height: 42px;
  margin-top: 22px;
  padding: 0 20px;
  border: 1px solid var(--red);
  color: #fff;
  background: var(--red);
  font-size: 12.5px;
  font-weight: 500;
}

.login-btn:active {
  background: var(--red-dark);
}

.me {
  display: flex;
  align-items: flex-start;
  gap: 14px;
}

.me-info {
  flex: 1;
  min-width: 0;
  padding-top: 2px;
}

.me-info h2 {
  overflow: hidden;
  color: var(--ink);
  font-family: var(--font-serif);
  font-size: clamp(28px, 8vw, 36px);
  font-weight: 700;
  line-height: 1.08;
  letter-spacing: -0.03em;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.username {
  margin-top: 7px;
  color: var(--muted);
  font-size: 10.5px;
  letter-spacing: 0.02em;
}

.bio {
  display: -webkit-box;
  overflow: hidden;
  margin-top: 10px;
  color: var(--ink-soft);
  font-size: 12.5px;
  line-height: 1.6;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.scroll {
  background: var(--paper);
  padding-bottom: calc(24px + var(--safe-bottom));
}

.tabs {
  position: sticky;
  top: 0;
  z-index: 2;
  display: flex;
  background: var(--paper);
  border-bottom: 1px solid var(--line);
}

.tab {
  display: flex;
  flex: 1;
  flex-direction: column;
  align-items: flex-start;
  gap: 5px;
  padding: 16px 16px 13px;
  border-bottom: 2px solid transparent;
  color: var(--muted);
  text-align: left;
  transition: color 0.18s ease, border-color 0.18s ease;
}

.tab + .tab {
  border-left: 1px solid var(--line);
}

.tab b {
  color: var(--ink-soft);
  font-family: var(--font-serif);
  font-size: 34px;
  font-weight: 600;
  line-height: 1;
  letter-spacing: -0.03em;
  font-variant-numeric: tabular-nums;
}

.tab span {
  font-size: 10px;
  font-weight: 500;
  letter-spacing: 0.08em;
}

.tab.active {
  border-bottom-color: var(--red);
  color: var(--red);
}

.tab.active b {
  color: var(--red);
}

.panel {
  background: var(--paper);
}

.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 16px 10px;
  border-bottom: 1px solid var(--line);
}

.panel-label {
  color: var(--muted);
  font-size: 9px;
  font-weight: 500;
  letter-spacing: 0.14em;
}

.panel-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.panel-count {
  color: var(--muted);
  font-size: 11px;
}

.clear {
  height: 28px;
  padding: 0 10px;
  border: 1px solid var(--red);
  color: var(--red);
  background: transparent;
  font-size: 10.5px;
  font-weight: 500;
}

.clear.confirm {
  color: #fff;
  background: var(--red);
}

.login-note {
  padding: 28px 16px 32px;
}

.login-note p {
  color: var(--muted);
  font-size: 13px;
  line-height: 1.7;
}

.list {
  padding: 0 16px;
}

.sentinel {
  height: 1px;
}

.account-actions {
  padding: 24px 16px 0;
}

.logout {
  width: 100%;
  height: 44px;
  border: 1px solid var(--red);
  border-radius: 12px;
  color: var(--red);
  background: transparent;
  font-size: 12.5px;
  font-weight: 600;
}

.logout:active {
  color: #fff;
  background: var(--red);
}

.about {
  padding: 32px 0 0;
  color: #9ca3af;
  font-size: 9px;
  letter-spacing: 0.16em;
  line-height: 2;
  text-align: center;
}

/* 编辑资料弹层 */
.sheet-mask {
  position: fixed;
  inset: 0;
  z-index: 60;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  background: rgba(24, 24, 27, 0.55);
}

.sheet {
  width: min(100%, 560px);
  max-height: 90dvh;
  padding: 10px 20px calc(20px + var(--safe-bottom));
  overflow-y: auto;
  border-top: 3px solid var(--red);
  background: var(--white);
}

.grabber {
  width: 36px;
  height: 2px;
  margin: 4px auto 16px;
  background: var(--line);
}

.sheet-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 20px;
}

.sheet-head h3 {
  margin-top: 8px;
  color: var(--ink);
  font-family: var(--font-serif);
  font-size: 28px;
  font-weight: 700;
  letter-spacing: -0.03em;
}

.close {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border: 1px solid var(--ink);
  color: var(--ink);
  background: transparent;
}

.close:active {
  color: #fff;
  background: var(--ink);
}

.field {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 22px;
}

.label {
  color: var(--muted);
  font-size: 9px;
  font-weight: 500;
  letter-spacing: 0.14em;
}

.field input,
.field textarea {
  width: 100%;
  padding: 10px 2px;
  border: 0;
  border-bottom: 1px solid var(--line-strong);
  background: transparent;
  color: var(--ink);
  outline: none;
  resize: none;
  transition: border-color 0.18s ease;
}

.field input {
  height: 44px;
}

.field input:focus,
.field textarea:focus {
  border-bottom-color: var(--red);
}

.field em {
  position: absolute;
  right: 2px;
  bottom: -14px;
  color: #9ca3af;
  font-size: 9px;
  font-style: normal;
  letter-spacing: 0.06em;
}

.segmented {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}

.segmented button {
  height: 42px;
  border: 1px solid var(--line);
  color: var(--ink-soft);
  background: transparent;
  font-size: 13px;
}

.segmented button.active {
  border-color: var(--red);
  color: #fff;
  background: var(--red);
}

.save {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  height: 48px;
  margin-top: 10px;
  padding: 0 18px;
  border: 1px solid var(--red);
  color: #fff;
  background: var(--red);
  font-size: 13.5px;
  font-weight: 500;
}

.save:active:not(:disabled) {
  background: var(--red-dark);
}

.sheet-enter-active,
.sheet-leave-active {
  transition: opacity 0.24s ease;
}

.sheet-enter-active .sheet,
.sheet-leave-active .sheet {
  transition: transform 0.3s cubic-bezier(0.32, 0.72, 0, 1);
}

.sheet-enter-from,
.sheet-leave-to {
  opacity: 0;
}

.sheet-enter-from .sheet,
.sheet-leave-to .sheet {
  transform: translateY(100%);
}

@media (min-width: 960px) {
  .profile-head {
    padding: 24px 40px 30px;
  }

  .head-top,
  .guest,
  .me {
    max-width: none;
    margin-right: 0;
    margin-left: 0;
  }

  .me {
    align-items: center;
  }

  .avatar {
    width: 80px;
    height: 80px;
    font-size: 32px;
  }

  .guest-avatar {
    width: 64px;
    height: 64px;
  }

  .me-info h2,
  .guest h2 {
    font-size: 44px;
  }

  .scroll {
    width: 100%;
    max-width: none;
    margin: 0;
  }

  .tab {
    padding: 18px 40px 15px;
  }

  .tab b {
    font-size: 40px;
  }

  .panel-head {
    padding: 16px 40px 12px;
  }

  .list {
    padding: 0 40px;
  }

  .account-actions {
    padding: 28px 40px 0;
  }

  .logout {
    display: block;
    max-width: 320px;
    margin: 0 auto;
  }

  .about {
    padding-top: 38px;
  }
}
</style>
