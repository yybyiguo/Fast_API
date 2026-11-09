import { request } from './http'
import { normalizeNewsItem } from './news'

export const favoriteApi = {
  check: (newsId) =>
    request('/api/favorite/check', { query: { news_id: newsId }, auth: true }),

  // 已收藏则取消，未收藏则添加
  shift: (newsId) =>
    request('/api/favorite/shift', { method: 'POST', query: { news_id: newsId }, auth: true }),

  list: ({ page = 1, pageSize = 10 }) =>
    request('/api/favorite/list', { query: { page, pagesize: pageSize }, auth: true }),

  clear: () => request('/api/favorite/clear', { method: 'DELETE', auth: true })
}

function normalizeFavoriteItem(raw = {}) {
  const news = normalizeNewsItem(raw)
  return {
    ...news,
    // 收藏记录里的 id 是收藏表主键，跳转要用 news_id
    id: Number(raw.news_id ?? news.id),
    favoriteId: Number(raw.id ?? 0),
    // create_time 是数据库本地时间（naive），按本地解析，不能补 Z
    createdAt: raw.created_at ?? raw.create_time ?? null
  }
}

export async function fetchFavorites(page = 1, pageSize = 10) {
  const res = await favoriteApi.list({ page, pageSize })
  const data = res?.data ?? {}
  return {
    list: (data.list ?? []).map(normalizeFavoriteItem),
    total: Number(data.total ?? 0),
    hasMore: Boolean(data.has_more ?? data.hasMore)
  }
}

export async function checkFavorite(newsId) {
  const res = await favoriteApi.check(newsId)
  return Boolean(res?.data?.is_favorite)
}

export async function shiftFavorite(newsId) {
  const res = await favoriteApi.shift(newsId)
  return { message: res?.message ?? '', data: res?.data ?? null }
}

export async function clearFavorites() {
  return favoriteApi.clear()
}
