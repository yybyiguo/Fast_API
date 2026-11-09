<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import ConfirmDialog from '../components/ConfirmDialog.vue'
import { fetchFavorites } from '../api/favorite'
import { fetchHistory } from '../api/history'
import { useAuth } from '../stores/auth'
import { useToast } from '../composables/useToast'
import { initialOf } from '../utils/format'
import { resolveAvatar } from '../utils/media'

const auth = useAuth()
const router = useRouter()
const toast = useToast()

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

watch(
  user,
  (value) => {
    brokenAvatar.value = false
    if (!value) return
    form.nickname = value.nickname || ''
    form.bio = value.bio || ''
    form.gender = value.gender || 'unknown'
  },
  { immediate: true }
)

onMounted(async () => {
  await auth.ensureReady()
  if (auth.isLoggedIn.value) loadStats()
})

async function loadStats() {
  try {
    const [favorites, history] = await Promise.all([
      fetchFavorites(1, 1),
      fetchHistory(1, 1)
    ])
    stats.favorites = favorites.total
    stats.history = history.total
    stats.loaded = true
  } catch (error) {
    if (error.status === 401) auth.logout()
  }
}

function goLogin() {
  router.push({ name: 'login', query: { redirect: '/profile' } })
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
  toast.success('已退出登录')
}
</script>

<template>
  <div class="page">
    <header class="profile-hero">
      <div class="glow" aria-hidden="true"></div>

      <div class="hero-top">
        <h1>我的</h1>
      </div>

      <div v-if="!user" class="guest">
        <div class="avatar guest-avatar" aria-hidden="true">?</div>
        <h2>登录后更精彩</h2>
        <p>收藏喜欢的资讯，自动同步浏览历史</p>
        <button type="button" class="login-btn" @click="goLogin">登录 / 注册</button>
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
        <button type="button" class="edit-btn" @click="openEdit">编辑</button>
      </div>
    </header>

    <div class="scroll">
      <div v-if="user" class="stats">
        <button type="button" class="stat" @click="router.push('/favorites')">
          <b>{{ stats.loaded ? stats.favorites : '–' }}</b>
          <span>收藏</span>
        </button>
        <i class="divider" aria-hidden="true"></i>
        <button type="button" class="stat" @click="router.push('/history')">
          <b>{{ stats.loaded ? stats.history : '–' }}</b>
          <span>浏览历史</span>
        </button>
      </div>

      <div class="menu">
        <button type="button" class="menu-item" @click="router.push('/favorites')">
          <span class="menu-icon heart" aria-hidden="true">
            <svg viewBox="0 0 24 24" width="19" height="19">
              <path
                d="M12 20.2S4.6 15.6 4.6 10.4A4.35 4.35 0 0 1 12 7.1a4.35 4.35 0 0 1 7.4 3.3c0 5.2-7.4 9.8-7.4 9.8z"
                fill="none"
                stroke="currentColor"
                stroke-width="1.7"
                stroke-linejoin="round"
              />
            </svg>
          </span>
          <span class="menu-label">我的收藏</span>
          <svg class="chevron" viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
            <path d="m9.5 5 7 7-7 7" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
        </button>

        <button type="button" class="menu-item" @click="router.push('/history')">
          <span class="menu-icon clock" aria-hidden="true">
            <svg viewBox="0 0 24 24" width="19" height="19">
              <circle cx="12" cy="12" r="8.4" fill="none" stroke="currentColor" stroke-width="1.7" />
              <path d="M12 7.3V12l3.1 1.9" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" />
            </svg>
          </span>
          <span class="menu-label">浏览历史</span>
          <svg class="chevron" viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
            <path d="m9.5 5 7 7-7 7" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
        </button>

        <button type="button" class="menu-item" @click="router.push('/rss')">
          <span class="menu-icon rss" aria-hidden="true">
            <svg viewBox="0 0 24 24" width="19" height="19">
              <path
                d="M6 6.5a11.5 11.5 0 0 1 11.5 11.5M6 11.6a6.4 6.4 0 0 1 6.4 6.4"
                fill="none"
                stroke="currentColor"
                stroke-width="1.7"
                stroke-linecap="round"
              />
              <circle cx="7.1" cy="17.4" r="1.5" fill="currentColor" />
            </svg>
          </span>
          <span class="menu-label">订阅源</span>
          <svg class="chevron" viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
            <path d="m9.5 5 7 7-7 7" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
        </button>

        <button v-if="user" type="button" class="menu-item" @click="openEdit">
          <span class="menu-icon edit" aria-hidden="true">
            <svg viewBox="0 0 24 24" width="19" height="19">
              <path
                d="m14.6 5.4 4 4M4.8 19.2l1-4.2L15.6 5.2a1.6 1.6 0 0 1 2.3 0l.9.9a1.6 1.6 0 0 1 0 2.3L9 18.2z"
                fill="none"
                stroke="currentColor"
                stroke-width="1.7"
                stroke-linecap="round"
                stroke-linejoin="round"
              />
            </svg>
          </span>
          <span class="menu-label">编辑资料</span>
          <svg class="chevron" viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
            <path d="m9.5 5 7 7-7 7" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
        </button>
      </div>

      <button v-if="user" type="button" class="logout" @click="confirmLogout.open = true">
        退出登录
      </button>

      <div class="about">
        <p>今日资讯 · 移动端演示</p>
        <p>Vue 3 + Vite · FastAPI</p>
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
              <h3>编辑资料</h3>
              <button type="button" class="close" aria-label="关闭" :disabled="saving" @click="editOpen = false">
                <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
                  <path d="M6 6l12 12M18 6 6 18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
                </svg>
              </button>
            </div>

            <label class="field">
              <span>昵称</span>
              <input v-model="form.nickname" type="text" maxlength="50" placeholder="给自己起个昵称" />
              <em>{{ form.nickname.length }}/50</em>
            </label>

            <label class="field">
              <span>个人简介</span>
              <textarea v-model="form.bio" rows="3" maxlength="500" placeholder="介绍一下自己"></textarea>
              <em>{{ form.bio.length }}/500</em>
            </label>

            <div class="field">
              <span>性别</span>
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
            </button>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<style scoped>
.profile-hero {
  position: relative;
  flex: 0 0 auto;
  padding: calc(12px + var(--safe-top)) 18px 20px;
  overflow: hidden;
  color: #fff;
  background: linear-gradient(145deg, #ff6b57 0%, #ef3b34 55%, #dc2b25 100%);
}

.glow {
  position: absolute;
  top: -150px;
  right: -90px;
  width: 280px;
  height: 280px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(255, 232, 214, 0.5), transparent 66%);
  pointer-events: none;
}

.hero-top {
  position: relative;
}

.hero-top h1 {
  font-size: 18px;
  font-weight: 600;
  letter-spacing: 0.4px;
}

.guest,
.me {
  position: relative;
  display: flex;
  align-items: center;
  gap: 14px;
  margin-top: 18px;
}

.guest {
  flex-direction: column;
  align-items: flex-start;
  gap: 0;
}

.guest h2 {
  margin-top: 14px;
  font-size: 21px;
  font-weight: 700;
}

.guest p {
  margin-top: 6px;
  color: rgba(255, 255, 255, 0.82);
  font-size: 12.5px;
}

.avatar {
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  width: 64px;
  height: 64px;
  overflow: hidden;
  border: 2px solid rgba(255, 255, 255, 0.55);
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.22);
  font-size: 24px;
  font-weight: 700;
  backdrop-filter: blur(4px);
}

.avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.guest-avatar {
  width: 56px;
  height: 56px;
  font-size: 22px;
  opacity: 0.85;
}

.login-btn {
  height: 40px;
  margin-top: 18px;
  padding: 0 22px;
  border-radius: 999px;
  color: #e5352c;
  background: #fff;
  box-shadow: 0 8px 20px rgba(120, 12, 8, 0.18);
  font-size: 14px;
  font-weight: 600;
}

.me {
  align-items: flex-start;
}

.me-info {
  flex: 1;
  min-width: 0;
  padding-top: 2px;
}

.me-info h2 {
  overflow: hidden;
  font-size: 20px;
  font-weight: 700;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.username {
  margin-top: 3px;
  color: rgba(255, 255, 255, 0.76);
  font-size: 12px;
}

.bio {
  display: -webkit-box;
  overflow: hidden;
  margin-top: 6px;
  color: rgba(255, 255, 255, 0.9);
  font-size: 12.5px;
  line-height: 1.5;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.edit-btn {
  flex: 0 0 auto;
  height: 30px;
  padding: 0 13px;
  border: 1px solid rgba(255, 255, 255, 0.4);
  border-radius: 999px;
  color: #fff;
  background: rgba(255, 255, 255, 0.16);
  font-size: 12.5px;
}

.scroll {
  padding: 12px 12px calc(20px + var(--safe-bottom));
}

.stats {
  display: flex;
  align-items: center;
  margin-top: 12px;
  padding: 14px 0;
  border-radius: var(--radius-lg);
  background: #fff;
  box-shadow: 0 10px 26px rgba(20, 22, 26, 0.1);
}

.stat {
  display: flex;
  flex: 1;
  flex-direction: column;
  align-items: center;
  gap: 3px;
}

.stat b {
  color: var(--c-ink);
  font-size: 20px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.stat span {
  color: var(--c-muted);
  font-size: 11.5px;
}

.divider {
  width: 1px;
  height: 26px;
  background: var(--c-line);
}

.menu {
  margin-top: 12px;
  overflow: hidden;
  border-radius: var(--radius-lg);
  background: #fff;
  box-shadow: var(--shadow-card);
}

.menu-item {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  height: 54px;
  padding: 0 16px;
  text-align: left;
}

.menu-item + .menu-item {
  border-top: 1px solid #f4f5f7;
}

.menu-item:active {
  background: #fafbfc;
}

.menu-icon {
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  border-radius: 9px;
}

.menu-icon.heart {
  color: #ef3b34;
  background: #fff1ef;
}

.menu-icon.clock {
  color: #2f7dd1;
  background: #eef5fd;
}

.menu-icon.edit {
  color: #8a5ad6;
  background: #f4effd;
}

.menu-icon.rss {
  color: #e8622c;
  background: #fff2e8;
}

.menu-label {
  flex: 1;
  font-size: 15px;
}

.chevron {
  color: #c4c9d1;
}

.logout {
  width: 100%;
  height: 50px;
  margin-top: 12px;
  border-radius: var(--radius-lg);
  color: var(--c-danger);
  background: #fff;
  box-shadow: var(--shadow-card);
  font-size: 15px;
  font-weight: 500;
}

.logout:active {
  background: #fff6f5;
}

.about {
  padding: 26px 0 8px;
  color: #bcc2cb;
  font-size: 11px;
  line-height: 1.8;
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
  background: rgba(15, 17, 21, 0.44);
  backdrop-filter: blur(2px);
}

.sheet {
  width: min(100%, 560px);
  max-height: 90dvh;
  padding: 8px 20px calc(18px + var(--safe-bottom));
  overflow-y: auto;
  border-radius: 24px 24px 0 0;
  background: #f7f8fa;
  box-shadow: 0 -12px 40px rgba(15, 17, 21, 0.2);
}

.grabber {
  width: 38px;
  height: 4px;
  margin: 6px auto 10px;
  border-radius: 2px;
  background: #d5d9df;
}

.sheet-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}

.sheet-head h3 {
  font-size: 19px;
  font-weight: 700;
}

.close {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border-radius: 50%;
  color: var(--c-ink-2);
  background: #e9ebef;
}

.field {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 14px;
}

.field > span {
  padding-left: 2px;
  color: var(--c-ink-2);
  font-size: 13px;
  font-weight: 600;
}

.field input,
.field textarea {
  width: 100%;
  padding: 12px 14px;
  border: 1.5px solid #e3e6ea;
  border-radius: 13px;
  background: #fff;
  outline: none;
  resize: none;
  transition: border-color 0.16s ease, box-shadow 0.16s ease;
}

.field input {
  height: 48px;
}

.field input:focus,
.field textarea:focus {
  border-color: rgba(239, 59, 52, 0.6);
  box-shadow: 0 0 0 3px rgba(239, 59, 52, 0.1);
}

.field em {
  position: absolute;
  right: 4px;
  bottom: -16px;
  color: #b6bcc6;
  font-size: 10.5px;
  font-style: normal;
}

.segmented {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}

.segmented button {
  height: 42px;
  border: 1.5px solid #e3e6ea;
  border-radius: 12px;
  color: var(--c-ink-2);
  background: #fff;
  font-size: 14px;
}

.segmented button.active {
  border-color: var(--c-primary);
  color: var(--c-primary);
  background: var(--c-primary-soft);
  font-weight: 600;
}

.save {
  width: 100%;
  height: 50px;
  margin-top: 8px;
  border-radius: 14px;
  color: #fff;
  background: linear-gradient(135deg, #ff6b57, var(--c-primary));
  box-shadow: 0 8px 20px rgba(239, 59, 52, 0.26);
  font-size: 16px;
  font-weight: 600;
}

.save:active:not(:disabled) {
  transform: scale(0.98);
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
</style>
