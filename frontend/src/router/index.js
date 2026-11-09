import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import DetailView from '../views/DetailView.vue'
import FavoritesView from '../views/FavoritesView.vue'
import HistoryView from '../views/HistoryView.vue'
import ProfileView from '../views/ProfileView.vue'
import RssView from '../views/RssView.vue'
import LoginView from '../views/LoginView.vue'
import { useAuth } from '../stores/auth'

const routes = [
  { path: '/', name: 'home', component: HomeView, meta: { tab: true } },
  { path: '/news/:id', name: 'detail', component: DetailView },
  { path: '/favorites', name: 'favorites', component: FavoritesView, meta: { tab: true, auth: true } },
  { path: '/history', name: 'history', component: HistoryView, meta: { tab: true, auth: true } },
  { path: '/profile', name: 'profile', component: ProfileView, meta: { tab: true } },
  { path: '/rss', name: 'rss', component: RssView, meta: { auth: true } },
  { path: '/login', name: 'login', component: LoginView },
  { path: '/:pathMatch(.*)*', redirect: '/' }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 })
})

router.beforeEach((to) => {
  if (!to.meta.auth) return true

  const { isLoggedIn } = useAuth()
  if (isLoggedIn.value) return true

  return { name: 'login', query: { redirect: to.fullPath } }
})

export default router
