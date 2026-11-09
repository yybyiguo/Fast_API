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
      <div class="glow" aria-hidden="true"></div>

      <div class="hero-top">
        <div class="brand">
          <span class="logo" aria-hidden="true">讯</span>
          <div class="brand-text">
            <h1>今日资讯</h1>
            <p>{{ today }} · 发现新鲜事</p>
          </div>
        </div>

        <button
          type="button"
          class="icon-btn"
          aria-label="刷新当前分类"
          :disabled="refreshing || !activeCategory"
          @click="refreshTop"
        >
          <svg :class="{ spin: refreshing }" viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
            <path
              d="M20 11.5A8 8 0 1 0 18.4 16M20 5v5h-5"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
            />
          </svg>
        </button>
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
        <span class="chip-skeleton shimmer short"></span>
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
  position: relative;
  flex: 0 0 auto;
  padding: calc(10px + var(--safe-top)) 16px 12px;
  overflow: hidden;
  color: #fff;
  background: linear-gradient(145deg, #ff6b57 0%, #ef3b34 52%, #dc2b25 100%);
}

.glow {
  position: absolute;
  top: -140px;
  right: -80px;
  width: 260px;
  height: 260px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(255, 232, 214, 0.45), transparent 66%);
  pointer-events: none;
}

.hero-top {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.logo {
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  width: 40px;
  height: 40px;
  border: 1px solid rgba(255, 255, 255, 0.34);
  border-radius: 13px;
  background: rgba(255, 255, 255, 0.18);
  font-size: 19px;
  font-weight: 700;
  backdrop-filter: blur(6px);
}

.brand-text {
  min-width: 0;
}

h1 {
  font-size: 19px;
  font-weight: 700;
  letter-spacing: 0.4px;
}

.brand-text p {
  margin-top: 2px;
  overflow: hidden;
  color: rgba(255, 255, 255, 0.82);
  font-size: 11.5px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.icon-btn {
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  width: 38px;
  height: 38px;
  border: 1px solid rgba(255, 255, 255, 0.26);
  border-radius: 50%;
  color: #fff;
  background: rgba(255, 255, 255, 0.14);
  transition: transform 0.15s ease;
}

.icon-btn:active {
  transform: scale(0.92);
}

.cats {
  position: relative;
  display: flex;
  gap: 8px;
  margin-top: 12px;
  padding-bottom: 1px;
  overflow-x: auto;
}

.cat {
  flex: 0 0 auto;
  height: 32px;
  padding: 0 15px;
  border: 1px solid rgba(255, 255, 255, 0.22);
  border-radius: 999px;
  color: #fff;
  background: rgba(255, 255, 255, 0.16);
  font-size: 13.5px;
  white-space: nowrap;
  transition: background 0.16s ease, color 0.16s ease;
}

.cat.active {
  border-color: #fff;
  color: #e5352c;
  background: #fff;
  box-shadow: 0 4px 12px rgba(120, 12, 8, 0.18);
  font-weight: 700;
}

.chip-skeleton {
  width: 62px;
  height: 32px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.22);
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
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.35), transparent);
  content: '';
  transform: translateX(-100%);
  animation: sweep 1.4s infinite;
}

@keyframes sweep {
  to {
    transform: translateX(100%);
  }
}
</style>
