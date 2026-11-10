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
      <div class="hero-top">
        <span class="eyebrow">ACCOUNT</span>
        <button v-if="user" type="button" class="edit-btn" @click="openEdit">编辑</button>
      </div>

      <div v-if="!user" class="guest">
        <div class="avatar guest-avatar" aria-hidden="true">?</div>
        <h2>未登录</h2>
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
      </div>
    </header>

    <div class="scroll">
      <div v-if="user" class="stats">
        <button type="button" class="stat" @click="router.push('/favorites')">
          <b>{{ stats.loaded ? stats.favorites : '–' }}</b>
          <span>SAVED</span>
        </button>
        <i class="divider" aria-hidden="true"></i>
        <button type="button" class="stat" @click="router.push('/history')">
          <b>{{ stats.loaded ? stats.history : '–' }}</b>
          <span>HISTORY</span>
        </button>
      </div>

      <div class="menu">
        <button type="button" class="menu-item" @click="router.push('/favorites')">
          <span class="index" aria-hidden="true">01</span>
          <span class="menu-label">我的收藏</span>
          <span class="chevron" aria-hidden="true">→</span>
        </button>

        <button type="button" class="menu-item" @click="router.push('/history')">
          <span class="index" aria-hidden="true">02</span>
          <span class="menu-label">浏览历史</span>
          <span class="chevron" aria-hidden="true">→</span>
        </button>

        <button type="button" class="menu-item" @click="router.push('/rss')">
          <span class="index" aria-hidden="true">03</span>
          <span class="menu-label">订阅源</span>
          <span class="chevron" aria-hidden="true">→</span>
        </button>

        <button v-if="user" type="button" class="menu-item" @click="openEdit">
          <span class="index" aria-hidden="true">04</span>
          <span class="menu-label">编辑资料</span>
          <span class="chevron" aria-hidden="true">→</span>
        </button>
      </div>

      <button v-if="user" type="button" class="logout" @click="confirmLogout.open = true">
        退出登录
      </button>

      <div class="about">
        <p>TOUTIAO · MOBILE</p>
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
                <span class="eyebrow no-dot">EDIT PROFILE</span>
                <h3>编辑资料</h3>
              </div>
              <button type="button" class="close" aria-label="关闭" :disabled="saving" @click="editOpen = false">
                <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
                  <path d="M6 6l12 12M18 6 6 18" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" />
                </svg>
              </button>
            </div>

            <label class="field">
              <span class="label">NICKNAME</span>
              <input v-model="form.nickname" type="text" maxlength="50" placeholder="给自己起个昵称" />
              <em>{{ form.nickname.length }}/50</em>
            </label>

            <label class="field">
              <span class="label">BIO</span>
              <textarea v-model="form.bio" rows="3" maxlength="500" placeholder="介绍一下自己"></textarea>
              <em>{{ form.bio.length }}/500</em>
            </label>

            <div class="field">
              <span class="label">GENDER</span>
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
  flex: 0 0 auto;
  padding: calc(16px + var(--safe-top)) 20px 24px;
  border-bottom: 1px solid var(--hairline);
  background: var(--canvas);
}

.hero-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.edit-btn {
  height: 30px;
  padding: 0 14px;
  border: 1px solid var(--pill-border);
  border-radius: var(--pill);
  color: var(--ink);
  background: transparent;
  font-size: 11.5px;
}

.guest,
.me {
  margin-top: 26px;
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
  border: 1px solid var(--pill-border);
  border-radius: 50%;
  color: var(--ink);
  background: #131416;
  font-size: 22px;
  font-weight: 400;
}

.avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.guest-avatar {
  width: 56px;
  height: 56px;
  color: var(--mute);
  font-family: var(--font-mono);
  font-size: 18px;
}

.guest h2 {
  margin-top: 22px;
  color: var(--ink);
  font-size: clamp(30px, 9vw, 38px);
  font-weight: 400;
  line-height: 1.04;
  letter-spacing: -0.045em;
}

.guest p {
  margin-top: 10px;
  color: var(--mute);
  font-size: 12.5px;
}

.login-btn {
  height: 40px;
  margin-top: 22px;
  padding: 0 22px;
  border-radius: var(--pill);
  color: var(--canvas);
  background: var(--ink);
  font-size: 13px;
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
  font-size: clamp(26px, 8vw, 34px);
  font-weight: 400;
  line-height: 1.08;
  letter-spacing: -0.04em;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.username {
  margin-top: 7px;
  color: var(--mute);
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.1em;
}

.bio {
  display: -webkit-box;
  overflow: hidden;
  margin-top: 10px;
  color: #9ca1a8;
  font-size: 12.5px;
  line-height: 1.6;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.scroll {
  padding: 0 16px calc(26px + var(--safe-bottom));
}

.stats {
  display: flex;
  align-items: center;
  padding: 24px 0;
  border-bottom: 1px solid var(--hairline);
}

.stat {
  display: flex;
  flex: 1;
  flex-direction: column;
  align-items: flex-start;
  gap: 6px;
  padding-left: 4px;
}

.stat b {
  color: var(--ink);
  font-size: 32px;
  font-weight: 400;
  line-height: 1;
  letter-spacing: -0.04em;
  font-variant-numeric: tabular-nums;
}

.stat span {
  color: #666b73;
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.18em;
}

.divider {
  width: 1px;
  height: 38px;
  background: var(--hairline);
}

.menu {
  margin-top: 8px;
}

.menu-item {
  display: flex;
  align-items: center;
  gap: 14px;
  width: 100%;
  height: 56px;
  border-bottom: 1px solid var(--hairline);
  text-align: left;
}

.menu-item:active {
  background: rgba(255, 255, 255, 0.03);
}

.index {
  flex: 0 0 auto;
  width: 22px;
  color: #5f646c;
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.12em;
}

.menu-label {
  flex: 1;
  color: var(--ink);
  font-size: 14px;
}

.chevron {
  color: #5f646c;
  font-family: var(--font-mono);
  font-size: 13px;
}

.logout {
  width: 100%;
  height: 44px;
  margin-top: 28px;
  border: 1px solid var(--pill-border);
  border-radius: var(--pill);
  color: var(--ink);
  background: transparent;
  font-size: 12.5px;
}

.logout:active {
  background: rgba(255, 255, 255, 0.08);
}

.about {
  padding: 30px 0 0;
  color: #4d5158;
  font-family: var(--font-mono);
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
  background: rgba(0, 0, 0, 0.72);
  backdrop-filter: blur(4px);
}

.sheet {
  width: min(100%, 560px);
  max-height: 90dvh;
  padding: 10px 20px calc(20px + var(--safe-bottom));
  overflow-y: auto;
  border-top: 1px solid var(--hairline);
  border-radius: 14px 14px 0 0;
  background: #0f1012;
}

.grabber {
  width: 36px;
  height: 2px;
  margin: 4px auto 16px;
  border-radius: 2px;
  background: #2a2d31;
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
  font-size: 24px;
  font-weight: 400;
  letter-spacing: -0.03em;
}

.close {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border: 1px solid var(--pill-border);
  border-radius: 50%;
  color: var(--ink);
}

.field {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 9px;
  margin-bottom: 20px;
}

.label {
  color: #666b73;
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.18em;
}

.field input,
.field textarea {
  width: 100%;
  padding: 12px 14px;
  border: 1px solid var(--hairline);
  border-radius: 6px;
  background: #151619;
  color: var(--ink);
  outline: none;
  resize: none;
  transition: border-color 0.16s ease;
}

.field input {
  height: 48px;
}

.field input:focus,
.field textarea:focus {
  border-color: #3d4147;
}

.field em {
  position: absolute;
  right: 4px;
  bottom: -16px;
  color: #4d5158;
  font-family: var(--font-mono);
  font-size: 8.5px;
  font-style: normal;
  letter-spacing: 0.08em;
}

.segmented {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}

.segmented button {
  height: 42px;
  border: 1px solid var(--hairline);
  border-radius: 6px;
  color: var(--mute);
  background: transparent;
  font-size: 13px;
}

.segmented button.active {
  border-color: var(--ink);
  color: var(--canvas);
  background: var(--ink);
}

.save {
  width: 100%;
  height: 48px;
  margin-top: 10px;
  border-radius: var(--pill);
  color: var(--canvas);
  background: var(--ink);
  font-size: 13.5px;
}

.save:active:not(:disabled) {
  background: var(--ink-dim);
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
