import { request } from './http'

// 全部走管理员白名单接口，必须带 token
const auth = { auth: true }

export const rssApi = {
  list: () => request('/api/rss/feeds', auth),
  create: (body) => request('/api/rss/feeds', { ...auth, method: 'POST', body }),
  update: (id, body) =>
    request(`/api/rss/feeds/${id}`, { ...auth, method: 'PATCH', body }),
  remove: (id) => request(`/api/rss/feeds/${id}`, { ...auth, method: 'DELETE' }),
  refresh: (id) =>
    request(`/api/rss/feeds/${id}/refresh`, { ...auth, method: 'POST' }),
  preview: (url) => request('/api/rss/preview', { ...auth, query: { url } }),
  discover: (siteUrl) =>
    request('/api/rss/discover', { ...auth, method: 'POST', body: { siteUrl } })
}
