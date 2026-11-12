const API_BASE = (import.meta.env.VITE_API_BASE || '').replace(/\/$/, '')
const TOKEN_KEY = 'toutiao_token'

export class ApiError extends Error {
  constructor(message, { status = 0, code = 0, data = null, retryAfter = 0 } = {}) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.data = data
    // 429 时后端会带 Retry-After（秒）；Nginx 那层没有，所以可能是 0
    this.retryAfter = retryAfter
  }
}

export function getToken() {
  try {
    return localStorage.getItem(TOKEN_KEY) || ''
  } catch {
    return ''
  }
}

export function setToken(token) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token)
    else localStorage.removeItem(TOKEN_KEY)
  } catch {
    /* 隐私模式下 localStorage 可能不可用 */
  }
}

const FIELD_LABELS = {
  username: '用户名',
  password: '密码',
  nickname: '昵称',
  avatar: '头像',
  gender: '性别',
  bio: '个人简介',
  news_id: '新闻',
  page: '页码',
  pagesize: '每页数量',
  categoryId: '分类'
}

/** FastAPI 422 校验错误翻译成中文 */
function formatValidation(detail) {
  const messages = detail.slice(0, 3).map((item) => {
    const key = [...(item.loc || [])].reverse().find((part) => typeof part === 'string')
    const label = FIELD_LABELS[key] || '参数'

    switch (item.type) {
      case 'missing':
        return `${label}不能为空`
      case 'string_too_short':
      case 'too_short':
        return `${label}至少需要 ${item.ctx?.min_length ?? 1} 个字符`
      case 'string_too_long':
      case 'too_long':
        return `${label}最多 ${item.ctx?.max_length ?? ''} 个字符`
      case 'greater_than':
        return `${label}必须大于 ${item.ctx?.gt ?? 0}`
      case 'less_than':
      case 'less_than_equal':
        return `${label}超出允许范围`
      case 'bool_parsing':
      case 'int_parsing':
        return `${label}格式不正确`
      default:
        return `${label}格式不正确`
    }
  })
  return messages.join('；') || '提交的内容不符合要求'
}

function buildUrl(path, query) {
  let url = `${API_BASE}${path}`
  if (!query) return url

  const params = new URLSearchParams()
  Object.entries(query).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') return
    params.append(key, String(value))
  })
  const search = params.toString()
  return search ? `${url}?${search}` : url
}

/**
 * 统一请求入口。
 * 后端错误统一是 { code, message, data }，但 HTTP 状态码也是真实的，
 * 所以两处都要判断；另外 /api/news/* 成功时用的是 msg 字段。
 */
export async function request(
  path,
  { method = 'GET', query, body, auth = false, timeout = 15000 } = {}
) {
  const url = buildUrl(path, query)
  const headers = { Accept: 'application/json' }

  if (body !== undefined) headers['Content-Type'] = 'application/json'

  const token = getToken()
  if (auth && token) headers.Authorization = `Bearer ${token}`

  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeout)

  try {
    const response = await fetch(url, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: controller.signal
    })

    const text = await response.text()
    let data = null
    if (text) {
      try {
        data = JSON.parse(text)
      } catch {
        data = null
      }
    }

    if (!response.ok) {
      let message = data?.message || data?.msg
      if (!message && Array.isArray(data?.detail)) message = formatValidation(data.detail)
      if (!message && typeof data?.detail === 'string') message = data.detail

      // Retry-After 是“秒”形式的字符串；读不到就是 0（比如 Nginx 直接拒的 429）
      const retryAfter = Number(response.headers.get('Retry-After')) || 0

      throw new ApiError(message || `请求失败（${response.status}）`, {
        status: response.status,
        code: data?.code || response.status,
        data,
        retryAfter
      })
    }

    if (data && typeof data.code === 'number' && data.code >= 400) {
      throw new ApiError(data.message || data.msg || '操作失败', {
        status: data.code,
        code: data.code,
        data
      })
    }

    return data
  } catch (error) {
    if (error instanceof ApiError) throw error
    if (error.name === 'AbortError') {
      throw new ApiError('请求超时，请稍后再试', { status: 0 })
    }
    throw new ApiError('网络连接失败，请确认后端已在 8000 端口启动', { status: 0 })
  } finally {
    clearTimeout(timer)
  }
}
