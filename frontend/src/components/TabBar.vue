<script setup>
import { useRoute } from 'vue-router'

const route = useRoute()

const items = [
  { to: '/', label: '首页', icon: 'home' },
  { to: '/favorites', label: '收藏', icon: 'heart' },
  { to: '/history', label: '历史', icon: 'clock' },
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
          stroke-width="1.4"
          stroke-linejoin="round"
        />
      </svg>
      <svg v-else-if="item.icon === 'heart'" viewBox="0 0 24 24" width="21" height="21" aria-hidden="true">
        <path
          d="M12 20.2S4.6 15.6 4.6 10.4A4.35 4.35 0 0 1 12 7.1a4.35 4.35 0 0 1 7.4 3.3c0 5.2-7.4 9.8-7.4 9.8z"
          fill="none"
          stroke="currentColor"
          stroke-width="1.4"
          stroke-linejoin="round"
        />
      </svg>
      <svg v-else-if="item.icon === 'clock'" viewBox="0 0 24 24" width="21" height="21" aria-hidden="true">
        <circle cx="12" cy="12" r="8.4" fill="none" stroke="currentColor" stroke-width="1.4" />
        <path d="M12 7.3V12l3.1 1.9" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" />
      </svg>
      <svg v-else viewBox="0 0 24 24" width="21" height="21" aria-hidden="true">
        <circle cx="12" cy="8.2" r="3.6" fill="none" stroke="currentColor" stroke-width="1.4" />
        <path
          d="M4.8 20c.5-3.5 3.4-5.5 7.2-5.5s6.7 2 7.2 5.5"
          fill="none"
          stroke="currentColor"
          stroke-width="1.4"
          stroke-linecap="round"
        />
      </svg>
      <span>{{ item.label }}</span>
    </router-link>
  </nav>
</template>

<style scoped>
.tabbar {
  display: flex;
  flex: 0 0 auto;
  align-items: stretch;
  padding-bottom: var(--safe-bottom);
  border-top: 1px solid var(--hairline);
  background: rgba(10, 10, 10, 0.96);
  backdrop-filter: blur(14px);
}

.tab {
  display: flex;
  flex: 1;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  height: var(--tabbar-h);
  color: #6b7078;
  font-size: 9.5px;
  letter-spacing: 0.12em;
  text-decoration: none;
  transition: color 0.16s ease;
}

.tab.active {
  color: var(--ink);
}

.tab:active {
  color: var(--ink);
}
</style>
