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
      <div class="hero-bg">
        <button type="button" class="back" aria-label="返回" @click="goBack">
          <svg viewBox="0 0 24 24" width="21" height="21" aria-hidden="true">
            <path
              d="M14.5 5 8 12l6.5 7"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
            />
          </svg>
        </button>

        <div class="brand">
          <span class="logo" aria-hidden="true">讯</span>
          <h1>今日资讯</h1>
          <p>登录后同步收藏与浏览历史</p>
        </div>
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
            <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
              <circle cx="12" cy="8.2" r="3.5" fill="none" stroke="currentColor" stroke-width="1.7" />
              <path
                d="M5 19.8c.5-3.4 3.3-5.4 7-5.4s6.5 2 7 5.4"
                fill="none"
                stroke="currentColor"
                stroke-width="1.7"
                stroke-linecap="round"
              />
            </svg>
            <input
              v-model="username"
              type="text"
              placeholder="用户名"
              autocomplete="username"
              enterkeyhint="next"
              maxlength="50"
              @input="errorMsg = ''"
            />
          </label>

          <label class="field">
            <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
              <rect x="5" y="10" width="14" height="9.4" rx="2.3" fill="none" stroke="currentColor" stroke-width="1.7" />
              <path d="M8.4 10V7.7a3.6 3.6 0 0 1 7.2 0V10" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" />
            </svg>
            <input
              v-model="password"
              :type="showPassword ? 'text' : 'password'"
              :placeholder="isRegister ? '设置密码（至少 6 位）' : '密码'"
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
              <svg v-if="!showPassword" viewBox="0 0 24 24" width="19" height="19" aria-hidden="true">
                <path
                  d="M2.6 12s3.4-5.6 9.4-5.6S21.4 12 21.4 12s-3.4 5.6-9.4 5.6S2.6 12 2.6 12z"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="1.6"
                />
                <circle cx="12" cy="12" r="2.4" fill="none" stroke="currentColor" stroke-width="1.6" />
              </svg>
              <svg v-else viewBox="0 0 24 24" width="19" height="19" aria-hidden="true">
                <path d="m4 4 16 16" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
                <path
                  d="M9.9 6.8A10.7 10.7 0 0 1 12 6.4c6 0 9.4 5.6 9.4 5.6a17 17 0 0 1-3 3.5M6.5 8.2A17.5 17.5 0 0 0 2.6 12S6 17.6 12 17.6c1.3 0 2.5-.3 3.5-.7"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="1.6"
                  stroke-linecap="round"
                />
              </svg>
            </button>
          </label>

          <p v-if="errorMsg" class="error" role="alert">{{ errorMsg }}</p>

          <button type="submit" class="submit" :disabled="submitting || !canSubmit">
            {{ submitting ? '请稍候…' : isRegister ? '注册并登录' : '登录' }}
          </button>
        </form>

        <p class="tip">
          {{ isRegister ? '注册后会自动登录，密码由后端加密存储' : '还没有账号？切换到「注册」创建一个' }}
        </p>
      </div>

      <button type="button" class="skip" @click="router.push('/')">先随便逛逛</button>
    </div>
  </div>
</template>

<style scoped>
.login {
  background: #f4f5f7;
}

.login-scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
}

.hero-bg {
  min-height: 250px;
  padding: calc(14px + var(--safe-top)) 18px 0;
  color: #fff;
  background: linear-gradient(150deg, #ff6b57 0%, #ef3b34 55%, #dc2b25 100%);
}

.back {
  display: grid;
  place-items: center;
  width: 38px;
  height: 38px;
  margin-left: -8px;
  border-radius: 50%;
  color: #fff;
  background: rgba(255, 255, 255, 0.16);
}

.brand {
  padding: 26px 4px 0;
}

.logo {
  display: grid;
  place-items: center;
  width: 46px;
  height: 46px;
  border: 1px solid rgba(255, 255, 255, 0.4);
  border-radius: 15px;
  background: rgba(255, 255, 255, 0.18);
  font-size: 22px;
  font-weight: 700;
}

.brand h1 {
  margin-top: 12px;
  font-size: 26px;
  font-weight: 700;
  letter-spacing: 0.5px;
}

.brand p {
  margin-top: 6px;
  color: rgba(255, 255, 255, 0.84);
  font-size: 12.5px;
}

.card {
  position: relative;
  z-index: 1;
  margin: -46px 18px 0;
  padding: 8px 20px 20px;
  border-radius: var(--radius-xl);
  background: #fff;
  box-shadow: 0 18px 40px rgba(20, 22, 26, 0.12);
}

.tabs {
  display: flex;
  gap: 22px;
  padding: 12px 2px 4px;
}

.tabs button {
  position: relative;
  padding: 8px 2px;
  color: var(--c-muted);
  font-size: 16px;
  font-weight: 500;
  transition: color 0.16s ease;
}

.tabs button.active {
  color: var(--c-ink);
  font-weight: 700;
}

.tabs button.active::after {
  position: absolute;
  right: 2px;
  bottom: 0;
  left: 2px;
  height: 3px;
  border-radius: 2px;
  background: var(--c-primary);
  content: '';
}

form {
  padding-top: 18px;
}

.field {
  display: flex;
  align-items: center;
  gap: 10px;
  height: 52px;
  margin-bottom: 12px;
  padding: 0 14px;
  border: 1.5px solid #e6e8ec;
  border-radius: 14px;
  color: #a5abb5;
  background: #f8f9fb;
  transition: border-color 0.16s ease, background 0.16s ease;
}

.field:focus-within {
  border-color: rgba(239, 59, 52, 0.6);
  background: #fff;
  box-shadow: 0 0 0 3px rgba(239, 59, 52, 0.1);
}

.field input {
  flex: 1;
  min-width: 0;
  height: 100%;
  border: 0;
  background: transparent;
  color: var(--c-ink);
  outline: none;
}

.field input::placeholder {
  color: #b3b9c2;
}

.eye {
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  margin-right: -6px;
  border-radius: 50%;
  color: #a5abb5;
}

.error {
  margin: -2px 2px 10px;
  color: var(--c-danger);
  font-size: 12.5px;
  line-height: 1.5;
}

.submit {
  width: 100%;
  height: 50px;
  margin-top: 4px;
  border-radius: 14px;
  color: #fff;
  background: linear-gradient(135deg, #ff6b57, var(--c-primary));
  box-shadow: 0 10px 22px rgba(239, 59, 52, 0.26);
  font-size: 16px;
  font-weight: 600;
  transition: transform 0.15s ease, opacity 0.15s ease;
}

.submit:active:not(:disabled) {
  transform: scale(0.98);
}

.tip {
  margin-top: 14px;
  color: var(--c-muted);
  font-size: 11.5px;
  line-height: 1.6;
  text-align: center;
}

.skip {
  display: block;
  margin: 18px auto calc(24px + var(--safe-bottom));
  padding: 8px 16px;
  color: #8b919b;
  font-size: 13px;
}
</style>
