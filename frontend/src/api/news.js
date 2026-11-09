import { request } from './http'

/** 兼容 snake_case / camelCase，列表和详情共用 */
export function normalizeNewsItem(raw = {}) {
  const categoryId = raw.categoryId ?? raw.category_id ?? 0
  const publishTime =
    raw.publishTime ?? raw.publishedTime ?? raw.publish_time ?? raw.create_time ?? null

  return {
    id: Number(raw.id ?? 0),
    title: raw.title ?? '',
    description: raw.description ?? '',
    content: raw.content ?? '',
    image: raw.image ?? null,
    author: raw.author ?? '',
    categoryId: Number(categoryId) || 0,
    views: Number(raw.views ?? 0),
    publishTime,
    sourceUrl: raw.sourceUrl ?? raw.source_url ?? ''
  }
}

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

export const newsApi = {
  categories: () => request('/api/news/categories'),
  list: ({ categoryId, page = 1, pageSize = 10 }) =>
    request('/api/news/list', { query: { categoryId, page, pagesize: pageSize } }),
  detail: (id) => request('/api/news/detail', { query: { id } })
}

export async function fetchCategories() {
  const res = await newsApi.categories()
  return (res?.data ?? [])
    .map((item) => ({
      id: Number(item.id),
      name: item.name || '',
      sortOrder: Number(item.sort_order ?? item.sortOrder ?? 0)
    }))
    .sort((a, b) => a.sortOrder - b.sortOrder)
}

export async function fetchNewsList({ categoryId, page = 1, pageSize = 10 }) {
  let res = await newsApi.list({ categoryId, page, pageSize })
  let raw = res?.data ?? {}
  let list = (raw.list ?? []).map(normalizeNewsItem)
  const total = Number(raw.totol ?? raw.total ?? 0)

  // main.py 的 get_news_list 在缓存未命中时会把 Result 消费两次，
  // 第一次返回空列表但已经把数据写进 Redis；这里补一次请求直接命中缓存。
  if (!list.length && total > 0) {
    await sleep(120)
    res = await newsApi.list({ categoryId, page, pageSize })
    raw = res?.data ?? {}
    list = (raw.list ?? []).map(normalizeNewsItem)
  }

  return {
    list,
    total,
    hasMore: Boolean(raw.hasmore ?? raw.has_more)
  }
}

export async function fetchNewsDetail(id) {
  const res = await newsApi.detail(id)
  const raw = res?.data ?? {}
  return {
    ...normalizeNewsItem(raw),
    content: raw.content ?? '',
    related: (raw.relatedNews ?? []).map(normalizeNewsItem)
  }
}
