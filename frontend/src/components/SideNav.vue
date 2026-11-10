<script setup>
import { useRoute } from 'vue-router'
import { formatToday } from '../utils/format'

const route = useRoute()
const today = formatToday()

const items = [
  { to: '/', label: '首页', index: '01' },
  { to: '/rss', label: '订阅源', index: '02' },
  { to: '/profile', label: '我的', index: '03' }
]

function isActive(to) {
  if (to === '/') {
    return route.path === '/' || route.path.startsWith('/news')
  }
  return route.path.startsWith(to)
}
</script>

<template>
  <aside class="sidenav">
    <div class="brand">
      <span class="kicker no-rule">DAILY BRIEFING</span>
      <router-link to="/" class="wordmark">今日资讯</router-link>
      <p>把信息流收束成一条线</p>
    </div>

    <nav class="nav" aria-label="主导航">
      <router-link
        v-for="item in items"
        :key="item.to"
        :to="item.to"
        class="nav-item"
        :class="{ active: isActive(item.to) }"
      >
        <span class="index" aria-hidden="true">{{ item.index }}</span>
        <span class="label">{{ item.label }}</span>
        <span class="arrow" aria-hidden="true">→</span>
      </router-link>
    </nav>

    <div class="side-foot">
      <span>{{ today }}</span>
      <span>MOBILE / DESKTOP EDITION</span>
    </div>
  </aside>
</template>

<style scoped>
.sidenav {
  display: none;
  flex: 0 0 240px;
  flex-direction: column;
  width: 240px;
  height: 100%;
  padding: 24px 20px 20px;
  border-top: 3px solid var(--red);
  border-right: 1px solid var(--ink);
  background: var(--paper);
}

.brand {
  padding-bottom: 4px;
}

.wordmark {
  display: block;
  margin-top: 14px;
  color: var(--ink);
  font-family: var(--font-serif);
  font-size: 34px;
  font-weight: 700;
  line-height: 1.05;
  letter-spacing: -0.04em;
  text-decoration: none;
}

.brand p {
  margin-top: 10px;
  color: var(--muted);
  font-size: 10px;
  line-height: 1.6;
}

.nav {
  margin-top: 34px;
  border-top: 1px solid var(--line);
}

.nav-item {
  display: grid;
  grid-template-columns: 24px 1fr auto;
  align-items: center;
  gap: 8px;
  padding: 16px 4px 16px 10px;
  border-bottom: 1px solid var(--line);
  color: var(--ink);
  text-decoration: none;
  transition: color 0.18s ease, background 0.18s ease;
}

.nav-item .index {
  color: var(--red);
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.06em;
}

.nav-item .label {
  font-size: 14px;
}

.nav-item .arrow {
  color: var(--muted);
  font-size: 12px;
}

.nav-item.active {
  color: var(--red);
  background: var(--red-soft);
  box-shadow: inset 2px 0 0 var(--red);
}

.nav-item.active .label {
  font-weight: 500;
}

.nav-item:hover {
  color: var(--red);
}

.side-foot {
  display: flex;
  flex-direction: column;
  gap: 5px;
  margin-top: auto;
  padding-top: 16px;
  border-top: 1px solid var(--line);
  color: #9ca3af;
  font-family: var(--font-mono);
  font-size: 8px;
  letter-spacing: 0.1em;
  line-height: 1.6;
}

@media (min-width: 960px) {
  .sidenav {
    display: flex;
  }
}
</style>
