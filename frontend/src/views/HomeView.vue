<script setup>
import { computed, onMounted, ref } from 'vue'
import EmptyState from '../components/EmptyState.vue'
import ListSkeleton from '../components/ListSkeleton.vue'
import NewsFeed from '../components/NewsFeed.vue'
import { useCategories } from '../stores/categories'
import { formatToday } from '../utils/format'

const { categories, loading: catLoading, error: catError, load } = useCategories()

const activeCategory = ref(0)
const feedRef = ref(null)
const refreshing = ref(false)
const today = formatToday()

const activeName = computed(
  () => categories.value.find((item) => item.id === activeCategory.value)?.name || ''
)

async function loadCategories() {
  try {
    // 强制刷新：新增/删除订阅源后，tab 要和后端保持一致
    const list = await load(true)
    if (!list.length) {
      activeCategory.value = 0
      return
    }
    if (!list.some((item) => item.id === activeCategory.value)) {
      activeCategory.value = list[0].id
    }
  } catch {
    /* 错误已写入 catError */
  }
}

onMounted(loadCategories)

function selectCategory(id) {
  if (id === activeCategory.value) return
  activeCategory.value = id
}

async function refreshTop() {
  if (refreshing.value) return
  refreshing.value = true
  try {
    await feedRef.value?.refresh()
  } finally {
    refreshing.value = false
  }
}
</script>

<template>
  <div class="page">
    <header class="masthead">
      <div class="topline">
        <span class="date">{{ today }}</span>
        <span class="edition">MORNING EDITION</span>
        <button
          type="button"
          class="refresh"
          aria-label="刷新当前分类"
          :disabled="refreshing || !activeCategory"
          @click="refreshTop"
        >
          <svg :class="{ spin: refreshing }" viewBox="0 0 24 24" width="15" height="15" aria-hidden="true">
            <path
              d="M20 11.5A8 8 0 1 0 18.4 16M20 5v5h-5"
              fill="none"
              stroke="currentColor"
              stroke-width="1.6"
              stroke-linecap="round"
              stroke-linejoin="round"
            />
          </svg>
        </button>
      </div>

      <div class="brand">
        <h1>今日资讯</h1>
        <p>DAILY BRIEFING · 把信息流收束成一条线</p>
      </div>

      <nav v-if="categories.length" class="sections no-scrollbar" role="tablist" aria-label="订阅源">
        <button
          v-for="item in categories"
          :key="item.id"
          type="button"
          role="tab"
          class="section"
          :class="{ active: item.id === activeCategory }"
          :aria-selected="item.id === activeCategory"
          @click="selectCategory(item.id)"
        >
          {{ item.name }}
        </button>
      </nav>

      <nav v-else-if="catLoading" class="sections" aria-hidden="true">
        <span class="chip-skeleton shimmer"></span>
        <span class="chip-skeleton short shimmer"></span>
      </nav>
    </header>

    <NewsFeed
      v-if="activeCategory"
      ref="feedRef"
      :key="activeCategory"
      :category-id="activeCategory"
      :category-name="activeName"
    />

    <div v-else-if="catLoading" class="scroll feed-loading">
      <ListSkeleton :count="4" />
    </div>

    <div v-else-if="catError" class="scroll feed-loading">
      <EmptyState
        icon="error"
        title="分类加载失败"
        :description="catError"
        action-text="重新加载"
        @action="loadCategories"
      />
    </div>

    <div v-else class="scroll feed-loading">
      <EmptyState
        icon="news"
        title="还没有订阅源"
        description="去「我的 → 订阅源」添加一个 RSS 源，首页会自动生成同名分类"
      />
    </div>
  </div>
</template>

<style scoped>
.masthead {
  flex: 0 0 auto;
  padding: calc(8px + var(--safe-top)) 16px 0;
  border-top: 3px solid var(--red);
  background: var(--paper);
}

.topline {
  display: flex;
  align-items: center;
  gap: 10px;
  height: 30px;
  color: var(--muted);
  font-size: 9.5px;
  font-weight: 500;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.date {
  flex: 1 1 auto;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.edition {
  flex: 0 0 auto;
  color: #8a8f98;
  font-size: 9px;
}

.refresh {
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  width: 30px;
  height: 30px;
  border: 1px solid var(--ink);
  color: var(--ink);
  background: transparent;
  transition: background 0.18s ease, color 0.18s ease;
}

.refresh:active {
  color: var(--white);
  background: var(--ink);
}

.brand {
  padding: 16px 0 12px;
  text-align: center;
}

h1 {
  color: var(--ink);
  font-family: var(--font-serif);
  font-size: clamp(36px, 10.5vw, 44px);
  font-weight: 700;
  line-height: 1;
  letter-spacing: -0.03em;
}

.brand p {
  margin-top: 9px;
  color: var(--muted);
  font-size: 9px;
  font-weight: 500;
  letter-spacing: 0.16em;
  text-transform: uppercase;
}

.sections {
  display: flex;
  gap: 0;
  overflow-x: auto;
  border-bottom: 1px solid var(--ink);
}

.section {
  position: relative;
  flex: 0 0 auto;
  height: 43px;
  padding: 0 15px;
  color: var(--ink-soft);
  background: transparent;
  font-size: 13px;
  white-space: nowrap;
  transition: color 0.18s ease;
}

.section:first-child {
  padding-left: 0;
}

.section.active {
  color: var(--red);
  border-bottom: 2px solid var(--red);
  font-weight: 500;
}

.section:active {
  color: var(--red);
}

.chip-skeleton {
  width: 64px;
  height: 12px;
  margin: 16px 12px 16px 0;
  background: #ececef;
}

.chip-skeleton.short {
  width: 48px;
}

.shimmer {
  position: relative;
  overflow: hidden;
}

.shimmer::after {
  position: absolute;
  inset: 0;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.7), transparent);
  content: '';
  transform: translateX(-100%);
  animation: sweep 1.5s infinite;
}

.feed-loading {
  background: var(--white);
}

@keyframes sweep {
  to {
    transform: translateX(100%);
  }
}
</style>
