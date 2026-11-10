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
              stroke-width="1.6"
              stroke-linecap="round"
              stroke-linejoin="round"
            />
          </svg>
        </button>
      </div>

      <div class="intro">
        <span class="eyebrow">ACCESS · {{ isRegister ? 'NEW ACCOUNT' : 'SIGN IN' }}</span>
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
            <span class="label">USERNAME</span>
            <span class="input">
              <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
                <circle cx="12" cy="8.2" r="3.5" fill="none" stroke="currentColor" stroke-width="1.4" />
                <path
                  d="M5 19.8c.5-3.4 3.3-5.4 7-5.4s6.5 2 7 5.4"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="1.4"
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
            </span>
          </label>

          <label class="field">
            <span class="label">PASSWORD</span>
            <span class="input">
              <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
                <rect x="5" y="10" width="14" height="9.4" rx="2.3" fill="none" stroke="currentColor" stroke-width="1.4" />
                <path d="M8.4 10V7.7a3.6 3.6 0 0 1 7.2 0V10" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" />
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
                <svg v-if="!showPassword" viewBox="0 0 24 24" width="17" height="17" aria-hidden="true">
                  <path
                    d="M2.6 12s3.4-5.6 9.4-5.6S21.4 12 21.4 12s-3.4 5.6-9.4 5.6S2.6 12 2.6 12z"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="1.4"
                  />
                  <circle cx="12" cy="12" r="2.4" fill="none" stroke="currentColor" stroke-width="1.4" />
                </svg>
                <svg v-else viewBox="0 0 24 24" width="17" height="17" aria-hidden="true">
                  <path d="m4 4 16 16" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" />
                  <path
                    d="M9.9 6.8A10.7 10.7 0 0 1 12 6.4c6 0 9.4 5.6 9.4 5.6a17 17 0 0 1-3 3.5M6.5 8.2A17.5 17.5 0 0 0 2.6 12S6 17.6 12 17.6c1.3 0 2.5-.3 3.5-.7"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="1.4"
                    stroke-linecap="round"
                  />
                </svg>
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

      <button type="button" class="skip" @click="router.push('/')">先随便逛逛</button>
    </div>
  </div>
</template>

<style scoped>
.login {
  background: var(--canvas);
}

.login-scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding-bottom: calc(28px + var(--safe-bottom));
}

.topbar {
  padding: calc(14px + var(--safe-top)) 16px 0;
}

.back {
  display: grid;
  place-items: center;
  width: 36px;
  height: 36px;
  border: 1px solid var(--pill-border);
  border-radius: 50%;
  color: var(--ink);
  transition: background 0.16s ease;
}

.back:active {
  background: rgba(255, 255, 255, 0.08);
}

.intro {
  padding: 30px 20px 0;
}

.intro h1 {
  margin-top: 16px;
  color: var(--ink);
  font-size: clamp(38px, 11vw, 48px);
  font-weight: 400;
  line-height: 1.02;
  letter-spacing: -0.05em;
}

.intro p {
  margin-top: 12px;
  color: var(--mute);
  font-size: 12.5px;
}

.card {
  margin: 26px 16px 0;
  padding: 18px 18px 20px;
  border: 1px solid var(--hairline);
  border-radius: var(--radius);
  background: #101113;
}

.tabs {
  display: flex;
  gap: 26px;
  border-bottom: 1px solid var(--hairline);
}

.tabs button {
  position: relative;
  padding: 0 2px 13px;
  color: var(--mute);
  font-size: 13px;
  transition: color 0.16s ease;
}

.tabs button.active {
  color: var(--ink);
}

.tabs button.active::after {
  position: absolute;
  right: 0;
  bottom: -1px;
  left: 0;
  height: 1px;
  background: var(--ink);
  content: '';
}

form {
  padding-top: 6px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 9px;
  margin-top: 18px;
}

.label {
  color: #666b73;
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.18em;
}

.input {
  display: flex;
  align-items: center;
  gap: 10px;
  height: 48px;
  padding: 0 14px;
  border: 1px solid var(--hairline);
  border-radius: 6px;
  color: #6b7078;
  background: #151619;
  transition: border-color 0.16s ease;
}

.input:focus-within {
  border-color: #3d4147;
  color: var(--ink);
}

.input input {
  flex: 1;
  min-width: 0;
  height: 100%;
  border: 0;
  background: transparent;
  color: var(--ink);
  outline: none;
}

.eye {
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  margin-right: -4px;
  border-radius: 50%;
  color: #6b7078;
}

.error {
  display: flex;
  gap: 8px;
  margin: 16px 0 0;
  color: var(--accent-soft);
  font-size: 12px;
  line-height: 1.5;
}

.error span {
  flex: 0 0 auto;
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.14em;
  line-height: 1.9;
}

.submit {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  height: 48px;
  margin-top: 22px;
  padding: 0 20px;
  border-radius: var(--pill);
  color: var(--canvas);
  background: var(--ink);
  font-size: 13.5px;
  transition: background 0.16s ease;
}

.submit span {
  font-family: var(--font-mono);
  font-size: 13px;
}

.submit:active:not(:disabled) {
  background: var(--ink-dim);
}

.submit:disabled {
  border: 1px solid var(--hairline);
  color: var(--mute);
  background: transparent;
  opacity: 1;
}

.tip {
  margin-top: 16px;
  color: #5f646c;
  font-size: 11px;
  line-height: 1.6;
}

.skip {
  display: block;
  height: 34px;
  margin: 22px auto 0;
  padding: 0 18px;
  border: 1px solid var(--pill-border);
  border-radius: var(--pill);
  color: var(--ink);
  font-size: 12px;
}
</style>
