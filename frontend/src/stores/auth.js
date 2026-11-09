import { computed, ref } from 'vue'
import { userApi } from '../api/user'
import { getToken, setToken } from '../api/http'

const USER_KEY = 'toutiao_user'

function readCachedUser() {
  try {
    const raw = localStorage.getItem(USER_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

function writeCachedUser(next) {
  try {
    if (next) localStorage.setItem(USER_KEY, JSON.stringify(next))
    else localStorage.removeItem(USER_KEY)
  } catch {
    /* ignore */
  }
}

export function normalizeUser(raw = {}) {
  return {
    id: Number(raw.id ?? 0),
    username: raw.username ?? '',
    nickname: raw.nickname ?? '',
    avatar: raw.avatar ?? '',
    gender: raw.gender ?? 'unknown',
    bio: raw.bio ?? ''
  }
}

const token = ref(getToken())
const user = ref(readCachedUser())
const ready = ref(false)
let initPromise = null

const isLoggedIn = computed(() => Boolean(token.value))

function applyAuth(payload) {
  const nextToken = payload?.token ?? ''
  const nextUser = normalizeUser(payload?.userInfo ?? payload?.user_info ?? payload ?? {})

  token.value = nextToken
  setToken(nextToken)
  user.value = nextUser
  writeCachedUser(nextUser)
  ready.value = true
  return nextUser
}

export function useAuth() {
  async function login(username, password) {
    const res = await userApi.login(username, password)
    return applyAuth(res?.data)
  }

  async function register(username, password) {
    const res = await userApi.register(username, password)
    return applyAuth(res?.data)
  }

  function logout() {
    token.value = ''
    user.value = null
    setToken('')
    writeCachedUser(null)
    ready.value = true
  }

  /** 用本地 token 拉一次最新资料，401 视为登录过期 */
  async function refresh() {
    if (!token.value) {
      ready.value = true
      return null
    }

    try {
      const res = await userApi.info()
      const next = normalizeUser(res?.data)
      user.value = next
      writeCachedUser(next)
      return next
    } catch (error) {
      if (error.status === 401) logout()
      return null
    } finally {
      ready.value = true
    }
  }

  function ensureReady() {
    if (!initPromise) initPromise = refresh()
    return initPromise
  }

  async function updateProfile(payload) {
    const res = await userApi.update(payload)
    const next = normalizeUser(res?.data)
    user.value = next
    writeCachedUser(next)
    return next
  }

  return {
    token,
    user,
    ready,
    isLoggedIn,
    login,
    register,
    logout,
    refresh,
    ensureReady,
    updateProfile
  }
}
