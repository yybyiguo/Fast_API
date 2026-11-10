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
    <header class="hero">
      <div class="hero-top">
        <span class="eyebrow">FEED · {{ today }}</span>

        <button
          type="button"
          class="icon-btn"
          aria-label="刷新当前分类"
          :disabled="refreshing || !activeCategory"
          @click="refreshTop"
        >
          <svg :class="{ spin: refreshing }" viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
            <path
              d="M20 11.5A8 8 0 1 0 18.4 16M20 5v5h-5"
              fill="none"
              stroke="currentColor"
              stroke-width="1.5"
              stroke-linecap="round"
              stroke-linejoin="round"
            />
          </svg>
        </button>
      </div>

      <div class="brand">
        <h1>今日资讯</h1>
        <p>把信息流收束成一条线</p>
      </div>

      <div v-if="categories.length" class="cats no-scrollbar" role="tablist" aria-label="订阅源">
        <button
          v-for="item in categories"
          :key="item.id"
          type="button"
          role="tab"
          class="cat"
          :class="{ active: item.id === activeCategory }"
          :aria-selected="item.id === activeCategory"
          @click="selectCategory(item.id)"
        >
          {{ item.name }}
        </button>
      </div>

      <div v-else-if="catLoading" class="cats" aria-hidden="true">
        <span class="chip-skeleton shimmer"></span>
        <span class="chip-skeleton short shimmer"></span>
      </div>
    </header>

    <NewsFeed
      v-if="activeCategory"
      ref="feedRef"
      :key="activeCategory"
      :category-id="activeCategory"
      :category-name="activeName"
    />

    <div v-else-if="catLoading" class="scroll">
      <ListSkeleton :count="4" />
    </div>

    <div v-else-if="catError" class="scroll">
      <EmptyState
        icon="error"
        title="分类加载失败"
        :description="catError"
        action-text="重新加载"
        @action="loadCategories"
      />
    </div>

    <div v-else class="scroll">
      <EmptyState
        icon="news"
        title="还没有订阅源"
        description="去「我的 → 订阅源」添加一个 RSS 源，首页会自动生成同名分类"
      />
    </div>
  </div>
</template>

<style scoped>
.hero {
  flex: 0 0 auto;
  padding: calc(14px + var(--safe-top)) 16px 0;
  background: var(--canvas);
}

.hero-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.icon-btn {
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  width: 36px;
  height: 36px;
  border: 1px solid var(--pill-border);
  border-radius: 50%;
  color: var(--ink);
  background: transparent;
  transition: background 0.16s ease;
}

.icon-btn:active {
  background: rgba(255, 255, 255, 0.08);
}

.brand {
  margin-top: 18px;
}

h1 {
  color: var(--ink);
  font-size: clamp(34px, 10vw, 42px);
  font-weight: 400;
  line-height: 1.05;
  letter-spacing: -0.045em;
}

.brand p {
  margin-top: 9px;
  color: var(--mute);
  font-size: 12.5px;
  letter-spacing: 0.01em;
}

.cats {
  display: flex;
  gap: 8px;
  margin-top: 20px;
  padding-bottom: 14px;
  overflow-x: auto;
  border-bottom: 1px solid var(--hairline);
}

.cat {
  flex: 0 0 auto;
  height: 32px;
  padding: 0 14px;
  border: 1px solid var(--pill-border);
  border-radius: var(--pill);
  color: var(--ink);
  background: transparent;
  font-size: 12.5px;
  letter-spacing: 0.01em;
  white-space: nowrap;
  transition: background 0.16s ease, color 0.16s ease, border-color 0.16s ease;
}

.cat.active {
  border-color: var(--ink);
  color: var(--canvas);
  background: var(--ink);
}

.chip-skeleton {
  width: 62px;
  height: 32px;
  border-radius: var(--pill);
  background: #17181b;
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
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.06), transparent);
  content: '';
  transform: translateX(-100%);
  animation: sweep 1.5s infinite;
}

@keyframes sweep {
  to {
    transform: translateX(100%);
  }
}
</style>
