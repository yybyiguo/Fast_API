import { request } from './http'
import { normalizeNewsItem } from './news'

export const historyApi = {
  // 后端 prefix=/api/history，路由是 /add_history
  add: (newsId) =>
    request('/api/history/add_history', { method: 'POST', query: { news_id: newsId }, auth: true }),

  list: ({ page = 1, pageSize = 10 }) =>
    request('/api/history/list', { query: { page, pagesize: pageSize }, auth: true }),

  remove: (newsId) =>
    request('/api/history/delete', { method: 'DELETE', query: { news_id: newsId }, auth: true }),

  clear: () => request('/api/history/clear', { method: 'DELETE', auth: true })
}

function normalizeHistoryItem(raw = {}) {
  const news = normalizeNewsItem(raw)
  return {
    ...news,
    id: Number(raw.news_id ?? news.id),
    historyId: Number(raw.id ?? 0),
    viewedAt: raw.update_time ?? raw.updateTime ?? null
  }
}

export async function fetchHistory(page = 1, pageSize = 10) {
  const res = await historyApi.list({ page, pageSize })
  const data = res?.data ?? {}
  return {
    list: (data.list ?? []).map(normalizeHistoryItem),
    total: Number(data.total ?? 0),
    hasMore: Boolean(data.has_more ?? data.hasMore)
  }
}

/** 记录浏览历史。重复浏览会触发唯一约束（400），前端静默忽略即可 */
export async function recordHistory(newsId) {
  try {
    await historyApi.add(newsId)
    return true
  } catch {
    return false
  }
}

export async function removeHistory(newsId) {
  return historyApi.remove(newsId)
}

export async function clearHistory() {
  return historyApi.clear()
}
