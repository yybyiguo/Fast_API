import { request } from './http'

export const userApi = {
  register: (username, password) =>
    request('/api/user/register', { method: 'POST', body: { username, password } }),

  login: (username, password) =>
    request('/api/user/login', { method: 'POST', body: { username, password } }),

  info: () => request('/api/user/info', { auth: true }),

  // 后端 userUpdateRequest 要求四个字段都传，缺一个会 422
  update: (payload) => request('/api/user/update', { method: 'PUT', body: payload, auth: true })
}
