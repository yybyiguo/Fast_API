<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppHeader from '../components/AppHeader.vue'
import EmptyState from '../components/EmptyState.vue'
import { checkFavorite, shiftFavorite } from '../api/favorite'
import { fetchNewsDetail } from '../api/news'
import { recordHistory } from '../api/history'
import { useAuth } from '../stores/auth'
import { useCategories } from '../stores/categories'
import { useToast } from '../composables/useToast'
import { formatRelativeTime, formatViews } from '../utils/format'
import { resolveImage } from '../utils/media'

const route = useRoute()
const router = useRouter()
const auth = useAuth()
const toast = useToast()
const { nameOf, load: loadCategories } = useCategories()

const article = ref(null)
const loading = ref(true)
const error = ref('')
const favorited = ref(false)
const favBusy = ref(false)
const brokenImage = ref(false)
const scroller = ref(null)

const newsId = computed(() => Number(route.params.id))
const cover = computed(() =>
  article.value && !brokenImage.value ? resolveImage(article.value.image) : ''
)
const categoryName = computed(() => nameOf(article.value?.categoryId))
const paragraphs = computed(() => {
  const raw = String(article.value?.content ?? '')
    // 兼容清理前入库的旧文章：去掉摘要末尾的“查看全文”纯文本
    .replace(/[\s.…·]*(?:查看全文|查看原文|阅读原文|阅读更多)\s*$/, '')
    .replace(/\r\n/g, '\n')
    .trim()
  if (!raw) return ['暂无正文内容']
  return raw
    .split(/\n+/)
    .map((line) => line.trim())
    .filter(Boolean)
})

async function load() {
  loading.value = true
  error.value = ''
  article.value = null
  favorited.value = false
  brokenImage.value = false

  try {
    const data = await fetchNewsDetail(newsId.value)
    article.value = data
    scroller.value?.scrollTo({ top: 0 })

    loadCategories().catch(() => {})

    if (auth.isLoggedIn.value) {
      checkFavorite(data.id)
        .then((checked) => {
          favorited.value = checked
        })
        .catch((err) => {
          if (err.status === 401) auth.logout()
        })
      // 记录历史，失败（例如重复浏览触发唯一约束）不打扰用户
      recordHistory(data.id)
    }
  } catch (err) {
    error.value = err.message || '加载失败'
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(newsId, (value, oldValue) => {
  if (value && value !== oldValue) load()
})

async function toggleFavorite() {
  if (!auth.isLoggedIn.value) {
    router.push({ name: 'login', query: { redirect: route.fullPath } })
    return
  }
  if (favBusy.value) return

  favBusy.value = true
  try {
    await shiftFavorite(newsId.value)
    favorited.value = !favorited.value
    toast.success(favorited.value ? '已加入收藏' : '已取消收藏')
  } catch (err) {
    if (err.status === 401) {
      auth.logout()
      router.push({ name: 'login', query: { redirect: route.fullPath } })
      return
    }
    toast.error(err.message)
  } finally {
    favBusy.value = false
  }
}

function openRelated(id) {
  router.push({ name: 'detail', params: { id } })
}
</script>

<template>
  <div class="page">
    <AppHeader title="资讯详情" back />

    <div ref="scroller" class="scroll detail-scroll">
      <div v-if="loading" class="article-skeleton" aria-hidden="true">
        <div class="sk eyebrow-line"></div>
        <div class="sk line w-90"></div>
        <div class="sk line w-70"></div>
        <div class="sk meta"></div>
        <div class="sk para"></div>
        <div class="sk para"></div>
        <div class="sk para short"></div>
      </div>

      <EmptyState
        v-else-if="error"
        icon="error"
        title="内容加载失败"
        :description="error"
        action-text="重新加载"
        @action="load"
      />

      <template v-else-if="article">
        <article class="article">
          <div class="head">
            <span class="cat">/ {{ categoryName || 'ARTICLE' }}</span>
            <h1>{{ article.title }}</h1>
            <div class="meta">
              <span v-if="article.author">{{ article.author }}</span>
              <span v-if="article.author" class="sep">/</span>
              <span>{{ formatRelativeTime(article.publishTime) }}</span>
              <span class="sep">/</span>
              <span>{{ formatViews(article.views) }} 阅读</span>
            </div>
          </div>

          <div v-if="cover" class="cover">
            <img :src="cover" alt="" @error="brokenImage = true" />
          </div>

          <div class="content">
            <p v-for="(paragraph, index) in paragraphs" :key="index">{{ paragraph }}</p>
          </div>

          <a
            v-if="article.sourceUrl"
            class="source-link"
            :href="article.sourceUrl"
            target="_blank"
            rel="noopener noreferrer"
          >
            查看全文
            <svg viewBox="0 0 24 24" width="13" height="13" aria-hidden="true">
              <path
                d="M14 5h5v5M19 5l-7.5 7.5M17.5 13.5V18a1.5 1.5 0 0 1-1.5 1.5H6A1.5 1.5 0 0 1 4.5 18V7.5A1.5 1.5 0 0 1 6 6h4.5"
                fill="none"
                stroke="currentColor"
                stroke-width="1.5"
                stroke-linecap="round"
                stroke-linejoin="round"
              />
            </svg>
          </a>
        </article>

        <section v-if="article.related.length" class="related">
          <span class="eyebrow no-dot">RELATED</span>
          <h2>相关推荐</h2>
          <button
            v-for="item in article.related"
            :key="item.id"
            type="button"
            class="related-item"
            @click="openRelated(item.id)"
          >
            <span class="related-title">{{ item.title }}</span>
            <span class="related-meta">
              {{ item.author || '匿名' }} / {{ formatViews(item.views) }} 阅读
            </span>
          </button>
        </section>

        <div class="footnote">END OF ARTICLE</div>
      </template>
    </div>

    <div v-if="article && !loading" class="actionbar">
      <button
        type="button"
        class="fav"
        :class="{ on: favorited }"
        :disabled="favBusy"
        :aria-pressed="favorited"
        @click="toggleFavorite"
      >
        <svg viewBox="0 0 24 24" width="17" height="17" aria-hidden="true">
          <path
            d="M12 20.2S4.6 15.6 4.6 10.4A4.35 4.35 0 0 1 12 7.1a4.35 4.35 0 0 1 7.4 3.3c0 5.2-7.4 9.8-7.4 9.8z"
            :fill="favorited ? 'currentColor' : 'none'"
            stroke="currentColor"
            stroke-width="1.4"
            stroke-linejoin="round"
          />
        </svg>
        <span>{{ favorited ? '已收藏' : '收藏' }}</span>
      </button>

      <span class="read-count">READ {{ formatViews(article.views) }}</span>
    </div>
  </div>
</template>

<style scoped>
.detail-scroll {
  padding-bottom: 24px;
}

.article {
  padding: 26px 20px 30px;
  background: var(--canvas);
}

.head {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding-bottom: 20px;
  border-bottom: 1px solid var(--hairline);
}

.cat {
  color: var(--mute);
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
}

h1 {
  color: var(--ink);
  font-size: clamp(26px, 7.4vw, 32px);
  font-weight: 400;
  line-height: 1.24;
  letter-spacing: -0.035em;
  word-break: break-word;
}

.meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  color: #6b7078;
  font-family: var(--font-mono);
  font-size: 9.5px;
  letter-spacing: 0.09em;
  text-transform: uppercase;
}

.sep {
  padding: 0 7px;
  color: #3c4046;
}

.cover {
  margin-top: 22px;
  overflow: hidden;
  border: 1px solid var(--hairline);
  border-radius: var(--radius);
  background: var(--canvas-soft);
}

.cover img {
  display: block;
  width: 100%;
  max-height: 320px;
  object-fit: cover;
}

.content {
  margin-top: 24px;
}

.content p {
  margin-top: 18px;
  color: #c9cbd0;
  font-size: 16px;
  line-height: 1.9;
  text-align: justify;
  word-break: break-word;
}

.content p:first-child {
  margin-top: 0;
}

.source-link {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  height: 34px;
  margin-top: 24px;
  padding: 0 16px;
  border: 1px solid var(--pill-border);
  border-radius: var(--pill);
  color: var(--ink);
  font-size: 12px;
  text-decoration: none;
  transition: background 0.16s ease;
}

.source-link:active {
  background: rgba(255, 255, 255, 0.08);
}

.related {
  padding: 24px 20px 10px;
  border-top: 1px solid var(--hairline);
  background: var(--canvas);
}

.related h2 {
  margin-top: 10px;
  color: var(--ink);
  font-size: 20px;
  font-weight: 400;
  letter-spacing: -0.02em;
}

.related-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
  width: 100%;
  padding: 15px 0;
  border-top: 1px solid var(--hairline);
  text-align: left;
}

.related-item:first-of-type {
  margin-top: 8px;
  border-top: 0;
}

.related-title {
  display: -webkit-box;
  overflow: hidden;
  color: var(--ink);
  font-size: 15px;
  font-weight: 400;
  line-height: 1.45;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.related-meta {
  color: #666b73;
  font-family: var(--font-mono);
  font-size: 9.5px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.footnote {
  padding: 30px 0 10px;
  color: #4d5158;
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.2em;
  text-align: center;
}

.actionbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex: 0 0 auto;
  gap: 12px;
  padding: 10px 16px calc(10px + var(--safe-bottom));
  border-top: 1px solid var(--hairline);
  background: rgba(10, 10, 10, 0.94);
  backdrop-filter: blur(14px);
}

.fav {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  height: 40px;
  padding: 0 18px;
  border: 1px solid var(--pill-border);
  border-radius: var(--pill);
  color: var(--ink);
  background: transparent;
  font-size: 12.5px;
  transition: background 0.16s ease, color 0.16s ease, border-color 0.16s ease;
}

.fav.on {
  border-color: var(--ink);
  color: var(--canvas);
  background: var(--ink);
}

.read-count {
  color: #666b73;
  font-family: var(--font-mono);
  font-size: 9.5px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.article-skeleton {
  padding: 28px 20px;
}

.sk {
  border-radius: 4px;
  background: linear-gradient(100deg, #16171a 20%, #202226 40%, #16171a 60%);
  background-size: 220% 100%;
  animation: shimmer 1.4s linear infinite;
}

.eyebrow-line {
  width: 80px;
  height: 9px;
  margin-bottom: 18px;
}

.line {
  height: 24px;
  margin-bottom: 12px;
}

.w-90 {
  width: 90%;
}

.w-70 {
  width: 70%;
}

.article-skeleton .meta {
  width: 45%;
  height: 10px;
  margin: 22px 0 30px;
}

.para {
  height: 13px;
  margin-bottom: 16px;
}

.para.short {
  width: 60%;
}

@keyframes shimmer {
  from {
    background-position: 140% 0;
  }
  to {
    background-position: -40% 0;
  }
}
</style>
