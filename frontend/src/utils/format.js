const MINUTE = 60 * 1000
const HOUR = 60 * MINUTE
const DAY = 24 * HOUR

const pad = (value) => String(value).padStart(2, '0')

/** 后端时间是不带时区的本地时间，按本地时间解析 */
export function parseTime(value) {
  if (!value) return null
  const date = new Date(String(value).replace(' ', 'T'))
  return Number.isNaN(date.getTime()) ? null : date
}

function startOfDay(date) {
  const copy = new Date(date)
  copy.setHours(0, 0, 0, 0)
  return copy
}

/** 刚刚 / 12 分钟前 / 3 小时前 / 昨天 / 10-21 */
export function formatRelativeTime(value) {
  const date = parseTime(value)
  if (!date) return ''

  const diff = Date.now() - date.getTime()
  if (diff < MINUTE) return '刚刚'
  if (diff < HOUR) return `${Math.floor(diff / MINUTE)} 分钟前`
  if (diff < DAY) return `${Math.floor(diff / HOUR)} 小时前`

  const days = Math.round((startOfDay(new Date()) - startOfDay(date)) / DAY)
  if (days === 1) return '昨天'
  if (days > 1 && days < 7) return `${days} 天前`
  return formatDate(date)
}

/** 2020-02-02 */
export function formatDate(value) {
  const date = value instanceof Date ? value : parseTime(value)
  if (!date) return ''
  const month = pad(date.getMonth() + 1)
  const day = pad(date.getDate())
  if (date.getFullYear() === new Date().getFullYear()) return `${month}-${day}`
  return `${date.getFullYear()}-${month}-${day}`
}

/** 10月21日 星期二 */
export function formatToday(date = new Date()) {
  const week = '日一二三四五六'[date.getDay()]
  return `${date.getMonth() + 1}月${date.getDate()}日 星期${week}`
}

/** 34 -> 34，12345 -> 1.2 万 */
export function formatViews(value) {
  const views = Number(value) || 0
  if (views >= 100000000) return `${(views / 100000000).toFixed(1).replace(/\.0$/, '')} 亿`
  if (views >= 10000) return `${(views / 10000).toFixed(1).replace(/\.0$/, '')} 万`
  return String(views)
}

/** 取名称首字作为头像占位 */
export function initialOf(value, fallback = '读') {
  const text = String(value || '').trim()
  if (!text) return fallback
  const first = Array.from(text)[0]
  return /[a-z]/i.test(first) ? first.toUpperCase() : first
}
