import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import DetailView from '../views/DetailView.vue'
import ProfileView from '../views/ProfileView.vue'
import RssView from '../views/RssView.vue'
import LoginView from '../views/LoginView.vue'
import { useAuth } from '../stores/auth'

const routes = [
  { path: '/', name: 'home', component: HomeView, meta: { tab: true, auth: true } },
  { path: '/news/:id', name: 'detail', component: DetailView, meta: { auth: true } },
  // 收藏 / 浏览记录已并入「我的」页内联展示，旧链接做重定向
  {
    path: '/favorites',
    redirect: { name: 'profile', query: { tab: 'favorites' } }
  },
  {
    path: '/history',
    redirect: { name: 'profile', query: { tab: 'history' } }
  },
  { path: '/profile', name: 'profile', component: ProfileView, meta: { tab: true, auth: true } },
  { path: '/rss', name: 'rss', component: RssView, meta: { tab: true, auth: true } },
  { path: '/login', name: 'login', component: LoginView, meta: { guest: true } },
  { path: '/:pathMatch(.*)*', redirect: '/' }
]

function safeRedirect(value) {
  return typeof value === 'string' &&
    value.startsWith('/') &&
    !value.startsWith('//') &&
    !value.startsWith('/login')
    ? value
    : ''
}

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 })
})

router.beforeEach(async (to) => {
  const auth = useAuth()
  // 本地有 token 也先校验一次，避免过期 token 直接进入内容页
  await auth.ensureReady()

  if (to.name === 'login') {
    if (!auth.isLoggedIn.value) return true
    return safeRedirect(to.query.redirect) || { name: 'home' }
  }

  if (!auth.isLoggedIn.value) {
    return {
      name: 'login',
      query: to.fullPath === '/' ? {} : { redirect: to.fullPath }
    }
  }

  return true
})

export default router
