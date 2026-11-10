<script setup>
import { useRoute } from 'vue-router'

const route = useRoute()

const items = [
  { to: '/', label: '首页', icon: 'home' },
  { to: '/rss', label: '订阅源', icon: 'rss' },
  { to: '/profile', label: '我的', icon: 'user' }
]

function isActive(to) {
  return to === '/' ? route.path === '/' : route.path.startsWith(to)
}
</script>

<template>
  <nav class="tabbar" aria-label="主导航">
    <router-link
      v-for="item in items"
      :key="item.to"
      :to="item.to"
      class="tab"
      :class="{ active: isActive(item.to) }"
    >
      <svg v-if="item.icon === 'home'" viewBox="0 0 24 24" width="21" height="21" aria-hidden="true">
        <path
          d="M4 10.8 12 4l8 6.8V20a1 1 0 0 1-1 1h-4.6v-6.2H9.6V21H5a1 1 0 0 1-1-1z"
          fill="none"
          stroke="currentColor"
          stroke-width="1.6"
          stroke-linejoin="round"
        />
      </svg>
      <svg v-else-if="item.icon === 'rss'" viewBox="0 0 24 24" width="21" height="21" aria-hidden="true">
        <path
          d="M5 5a14 14 0 0 1 14 14M5 11a8 8 0 0 1 8 8"
          fill="none"
          stroke="currentColor"
          stroke-width="1.6"
          stroke-linecap="round"
        />
        <circle cx="6" cy="18" r="1.8" fill="currentColor" />
      </svg>
      <svg v-else viewBox="0 0 24 24" width="21" height="21" aria-hidden="true">
        <circle cx="12" cy="8.2" r="3.6" fill="none" stroke="currentColor" stroke-width="1.6" />
        <path
          d="M4.8 20c.5-3.5 3.4-5.5 7.2-5.5s6.7 2 7.2 5.5"
          fill="none"
          stroke="currentColor"
          stroke-width="1.6"
          stroke-linecap="round"
        />
      </svg>
      <span>{{ item.label }}</span>
    </router-link>
  </nav>
</template>

<style scoped>
.tabbar {
  position: relative;
  display: flex;
  flex: 0 0 auto;
  align-items: stretch;
  padding-bottom: var(--safe-bottom);
  border-top: 1px solid var(--line);
  background: rgba(10, 10, 16, 0.86);
  backdrop-filter: blur(22px) saturate(150%);
}

.tab {
  position: relative;
  display: flex;
  flex: 1;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 5px;
  height: var(--tabbar-h);
  color: var(--muted);
  font-size: 10px;
  font-weight: 500;
  letter-spacing: 0.03em;
  text-decoration: none;
  transition: color 0.18s ease;
}

.tab.active {
  color: var(--red);
  font-weight: 700;
}

.tab.active::before {
  position: absolute;
  top: 0;
  left: 50%;
  width: 18px;
  height: 3px;
  border-radius: 0 0 3px 3px;
  background: var(--red);
  box-shadow: 0 0 14px rgba(254, 44, 85, 0.7);
  content: '';
  transform: translateX(-50%);
}

.tab:active {
  color: var(--red);
}
</style>
