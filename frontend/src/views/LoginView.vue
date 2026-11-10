<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuth } from '../stores/auth'
import { useToast } from '../composables/useToast'

const route = useRoute()
const router = useRouter()
const auth = useAuth()
const toast = useToast()

const mode = ref('login')
const username = ref('')
const password = ref('')
const showPassword = ref(false)
const submitting = ref(false)
const errorMsg = ref('')

const isRegister = computed(() => mode.value === 'register')
const canSubmit = computed(
  () => username.value.trim().length >= 2 && password.value.length >= 6
)

onMounted(() => {
  if (auth.isLoggedIn.value) router.replace('/profile')
})

watch(mode, () => {
  errorMsg.value = ''
})

function switchMode(next) {
  if (submitting.value) return
  mode.value = next
}

function goBack() {
  if (window.history.length > 1) router.back()
  else router.push('/')
}

async function submit() {
  if (submitting.value) return
  errorMsg.value = ''

  const name = username.value.trim()
  if (name.length < 2) {
    errorMsg.value = '用户名至少 2 个字符'
    return
  }
  if (password.value.length < 6) {
    errorMsg.value = '密码至少 6 位'
    return
  }

  submitting.value = true
  try {
    if (isRegister.value) await auth.register(name, password.value)
    else await auth.login(name, password.value)

    toast.success(isRegister.value ? '注册成功' : '登录成功')

    let redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/profile'
    if (!redirect.startsWith('/') || redirect.startsWith('/login')) redirect = '/profile'
    router.replace(redirect)
  } catch (error) {
    errorMsg.value = error.message || '操作失败，请稍后再试'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="page login">
    <div class="login-scroll">
      <div class="topbar">
        <button type="button" class="back" aria-label="返回" @click="goBack">
          <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
            <path
              d="M14.5 5 8 12l6.5 7"
              fill="none"
              stroke="currentColor"
              stroke-width="1.8"
              stroke-linecap="round"
              stroke-linejoin="round"
            />
          </svg>
        </button>
        <span class="kicker no-rule">MEMBER ACCESS</span>
        <span class="est">EST. 2026</span>
      </div>

      <div class="intro">
        <h1>{{ isRegister ? '创建账号' : '登录' }}</h1>
        <p>登录后同步收藏与浏览历史</p>
      </div>

      <div class="card">
        <div class="tabs" role="tablist">
          <button
            type="button"
            role="tab"
            :class="{ active: mode === 'login' }"
            :aria-selected="mode === 'login'"
            @click="switchMode('login')"
          >
            登录
          </button>
          <button
            type="button"
            role="tab"
            :class="{ active: mode === 'register' }"
            :aria-selected="mode === 'register'"
            @click="switchMode('register')"
          >
            注册
          </button>
        </div>

        <form novalidate @submit.prevent="submit">
          <label class="field">
            <span class="label">USERNAME / 用户名</span>
            <input
              v-model="username"
              type="text"
              placeholder="至少 2 个字符"
              autocomplete="username"
              enterkeyhint="next"
              maxlength="50"
              @input="errorMsg = ''"
            />
          </label>

          <label class="field">
            <span class="label">PASSWORD / 密码</span>
            <span class="password">
              <input
                v-model="password"
                :type="showPassword ? 'text' : 'password'"
                :placeholder="isRegister ? '至少 6 位' : '输入密码'"
                :autocomplete="isRegister ? 'new-password' : 'current-password'"
                enterkeyhint="done"
                maxlength="64"
                @input="errorMsg = ''"
              />
              <button
                type="button"
                class="eye"
                :aria-label="showPassword ? '隐藏密码' : '显示密码'"
                @click="showPassword = !showPassword"
              >
                {{ showPassword ? 'HIDE' : 'SHOW' }}
              </button>
            </span>
          </label>

          <p v-if="errorMsg" class="error" role="alert">
            <span>ERR</span>
            {{ errorMsg }}
          </p>

          <button type="submit" class="submit" :disabled="submitting || !canSubmit">
            {{ submitting ? '请稍候…' : isRegister ? '注册并登录' : '登录' }}
            <span aria-hidden="true">→</span>
          </button>
        </form>

        <p class="tip">
          {{ isRegister ? '注册后会自动登录，密码由后端加密存储' : '还没有账号？切换到「注册」创建一个' }}
        </p>
      </div>

      <button type="button" class="skip" @click="router.push('/')">
        先随便逛逛
        <span aria-hidden="true">→</span>
      </button>

      <p class="colophon">今日资讯 · MOBILE EDITION</p>
    </div>
  </div>
</template>

<style scoped>
.login {
  background: var(--paper);
}

.login-scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 0 16px calc(28px + var(--safe-bottom));
  background: var(--paper);
}

.topbar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding-top: calc(14px + var(--safe-top));
  padding-bottom: 16px;
  border-bottom: 1px solid var(--line);
}

.back {
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  width: 34px;
  height: 34px;
  border: 1px solid var(--line);
  border-radius: 11px;
  color: var(--ink);
  background: rgba(255, 255, 255, 0.04);
}

.back:active {
  color: #fff;
  background: var(--red);
}

.kicker {
  flex: 1;
}

.est {
  color: var(--muted);
  font-size: 9px;
  letter-spacing: 0.12em;
}

.intro {
  padding: 34px 4px 0;
}

.intro h1 {
  color: var(--ink);
  font-family: var(--font-serif);
  font-size: clamp(42px, 12vw, 52px);
  font-weight: 700;
  line-height: 1;
  letter-spacing: -0.035em;
}

.intro p {
  margin-top: 12px;
  color: var(--muted);
  font-size: 13px;
}

.card {
  margin-top: 26px;
  padding: 22px 20px 20px;
  border: 1px solid var(--line);
  border-top: 3px solid var(--red);
  border-radius: 0 0 20px 20px;
  background: var(--surface);
  box-shadow: 0 20px 46px rgba(0, 0, 0, 0.35);
}

.tabs {
  display: flex;
  gap: 24px;
  border-bottom: 1px solid var(--line);
}

.tabs button {
  position: relative;
  padding: 0 2px 12px;
  color: var(--muted);
  font-family: var(--font-serif);
  font-size: 18px;
  font-weight: 600;
  transition: color 0.18s ease;
}

.tabs button.active {
  color: var(--ink);
}

.tabs button.active::after {
  position: absolute;
  right: 0;
  bottom: -1px;
  left: 0;
  height: 2px;
  background: var(--red);
  content: '';
}

form {
  padding-top: 6px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 20px;
}

.label {
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
  border-bottom: 1px solid var(--line-strong);
  color: var(--ink);
  background: transparent;
  outline: none;
  transition: border-color 0.18s ease;
}

.field input:focus {
  border-bottom-color: var(--red);
}

.password {
  display: flex;
  align-items: center;
  gap: 10px;
  border-bottom: 1px solid var(--line-strong);
  transition: border-color 0.18s ease;
}

.password:focus-within {
  border-bottom-color: var(--red);
}

.password input {
  flex: 1;
  min-width: 0;
  border-bottom: 0;
}

.eye {
  flex: 0 0 auto;
  padding: 8px 0;
  color: var(--red);
  font-family: var(--font-sans);
  font-size: 9px;
  font-weight: 600;
  letter-spacing: 0.1em;
}

.error {
  display: flex;
  gap: 8px;
  margin-top: 18px;
  color: var(--red-dark);
  font-size: 12px;
  line-height: 1.5;
}

.error span {
  flex: 0 0 auto;
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.12em;
  line-height: 1.9;
}

.submit {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  height: 48px;
  margin-top: 24px;
  padding: 0 18px;
  border: 1px solid var(--red);
  border-radius: 12px;
  color: #fff;
  background: var(--red);
  font-size: 13.5px;
  font-weight: 600;
  transition: background 0.18s ease;
}

.submit:active:not(:disabled) {
  background: var(--red-dark);
}

.submit:disabled {
  border-color: var(--line);
  color: var(--muted);
  background: rgba(255, 255, 255, 0.06);
}

.tip {
  margin-top: 16px;
  color: var(--muted);
  font-size: 11px;
  line-height: 1.6;
}

.skip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  margin: 24px 0 0 2px;
  padding-bottom: 3px;
  border-bottom: 1px solid var(--line-strong);
  color: var(--ink);
  font-size: 12px;
}

.colophon {
  margin-top: 40px;
  color: #9ca3af;
  font-size: 9px;
  letter-spacing: 0.16em;
  text-align: center;
}

@media (min-width: 960px) {
  .login-scroll {
    width: 100%;
    max-width: 620px;
    margin: 0 auto;
    padding-bottom: 48px;
  }

  .intro {
    padding-top: 40px;
  }

  .intro h1 {
    font-size: 58px;
  }

  .card {
    padding: 26px 24px 22px;
  }

  .colophon {
    margin-top: 52px;
  }
}
</style>
