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
    <AppHeader title="今日资讯" back />

    <div ref="scroller" class="scroll detail-scroll">
      <div v-if="loading" class="article-skeleton" aria-hidden="true">
        <div class="sk kicker-line"></div>
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
          <span class="kicker">{{ categoryName || 'NEWS' }}</span>
          <h1>{{ article.title }}</h1>

          <div class="byline">
            <span v-if="article.author" class="author">{{ article.author }}</span>
            <span v-if="article.author" class="sep">·</span>
            <span>{{ formatRelativeTime(article.publishTime) }}</span>
            <span class="sep">·</span>
            <span>{{ formatViews(article.views) }} 阅读</span>
          </div>

          <figure v-if="cover" class="cover">
            <img :src="cover" alt="" @error="brokenImage = true" />
          </figure>

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
            阅读原文
            <svg viewBox="0 0 24 24" width="13" height="13" aria-hidden="true">
              <path
                d="M14 5h5v5M19 5l-7.5 7.5M17.5 13.5V18a1.5 1.5 0 0 1-1.5 1.5H6A1.5 1.5 0 0 1 4.5 18V7.5A1.5 1.5 0 0 1 6 6h4.5"
                fill="none"
                stroke="currentColor"
                stroke-width="1.7"
                stroke-linecap="round"
                stroke-linejoin="round"
              />
            </svg>
          </a>
        </article>

        <section v-if="article.related.length" class="related">
          <span class="kicker">RELATED</span>
          <h2>相关阅读</h2>
          <button
            v-for="(item, index) in article.related"
            :key="item.id"
            type="button"
            class="related-item"
            @click="openRelated(item.id)"
          >
            <span class="related-index" aria-hidden="true">{{ String(index + 1).padStart(2, '0') }}</span>
            <span class="related-body">
              <span class="related-title">{{ item.title }}</span>
              <span class="related-meta">
                {{ item.author || '匿名' }} · {{ formatViews(item.views) }} 阅读
              </span>
            </span>
          </button>
        </section>

        <div class="footnote">END OF ARTICLE · 今日资讯</div>
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
        <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
          <path
            d="M12 20.2S4.6 15.6 4.6 10.4A4.35 4.35 0 0 1 12 7.1a4.35 4.35 0 0 1 7.4 3.3c0 5.2-7.4 9.8-7.4 9.8z"
            :fill="favorited ? 'currentColor' : 'none'"
            stroke="currentColor"
            stroke-width="1.6"
            stroke-linejoin="round"
          />
        </svg>
        <span>{{ favorited ? '已收藏' : '收藏' }}</span>
      </button>

      <span class="read-count">{{ formatViews(article.views) }} READS</span>
    </div>
  </div>
</template>

<style scoped>
.detail-scroll {
  padding-bottom: 24px;
  background: var(--white);
}

.article {
  padding: 24px 20px 30px;
  background: var(--white);
}

.kicker {
  margin-bottom: 14px;
}

h1 {
  color: var(--ink);
  font-family: var(--font-serif);
  font-size: clamp(30px, 8.8vw, 38px);
  font-weight: 700;
  line-height: 1.16;
  letter-spacing: -0.03em;
  word-break: break-word;
}

.byline {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  margin-top: 16px;
  padding-bottom: 14px;
  border-bottom: 1px solid var(--line);
  color: var(--muted);
  font-size: 11.5px;
  line-height: 1.5;
}

.author {
  color: var(--ink);
  font-weight: 500;
}

.sep {
  padding: 0 7px;
  color: #c4c4c8;
}

.cover {
  margin: 22px 0 0;
  padding: 0;
  border: 1px solid var(--ink);
  background: var(--paper-warm);
}

.cover img {
  display: block;
  width: 100%;
  max-height: 340px;
  object-fit: cover;
}

.content {
  max-width: 34em;
  margin-top: 24px;
}

.content p {
  margin-top: 17px;
  color: #27272a;
  font-size: 16.5px;
  line-height: 1.9;
  text-align: justify;
  word-break: break-word;
}

.content p:first-child {
  margin-top: 0;
}

.content p:first-child::first-letter {
  float: left;
  padding: 5px 8px 0 0;
  color: var(--red);
  font-family: var(--font-serif);
  font-size: 3.2em;
  font-weight: 700;
  line-height: 0.82;
}

.source-link {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  margin-top: 26px;
  padding-bottom: 3px;
  border-bottom: 1px solid var(--red);
  color: var(--red);
  font-size: 12.5px;
  font-weight: 500;
  text-decoration: none;
}

.related {
  padding: 22px 20px 8px;
  border-top: 1px solid var(--ink);
  background: var(--white);
}

.related h2 {
  margin-top: 10px;
  color: var(--ink);
  font-family: var(--font-serif);
  font-size: 24px;
  font-weight: 600;
  letter-spacing: -0.02em;
}

.related-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  width: 100%;
  padding: 16px 0;
  border-bottom: 1px solid var(--line);
  text-align: left;
}

.related-item:first-of-type {
  margin-top: 10px;
  border-top: 1px solid var(--line);
}

.related-index {
  flex: 0 0 22px;
  padding-top: 3px;
  color: var(--red);
  font-family: var(--font-mono);
  font-size: 10px;
}

.related-body {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 5px;
  min-width: 0;
}

.related-title {
  display: -webkit-box;
  overflow: hidden;
  color: var(--ink);
  font-family: var(--font-serif);
  font-size: 17px;
  font-weight: 600;
  line-height: 1.35;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.related-meta {
  color: var(--muted);
  font-size: 10.5px;
}

.footnote {
  padding: 28px 0 10px;
  border-top: 1px solid var(--line);
  color: #9ca3af;
  font-family: var(--font-sans);
  font-size: 9px;
  font-weight: 500;
  letter-spacing: 0.16em;
  text-align: center;
}

.actionbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex: 0 0 auto;
  gap: 12px;
  padding: 10px 16px calc(10px + var(--safe-bottom));
  border-top: 1px solid var(--ink);
  background: var(--white);
}

.fav {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  height: 42px;
  padding: 0 20px;
  border: 1px solid var(--red);
  color: var(--red);
  background: transparent;
  font-size: 12.5px;
  font-weight: 500;
  transition: background 0.18s ease, color 0.18s ease;
}

.fav.on {
  color: var(--white);
  background: var(--red);
}

.fav:active {
  color: var(--white);
  background: var(--red);
}

.read-count {
  color: var(--muted);
  font-family: var(--font-sans);
  font-size: 9px;
  font-weight: 500;
  letter-spacing: 0.14em;
}

.article-skeleton {
  padding: 26px 20px;
  background: var(--white);
}

.sk {
  background: linear-gradient(100deg, #f1f1f3 20%, #fafafa 40%, #f1f1f3 60%);
  background-size: 220% 100%;
  animation: shimmer 1.4s linear infinite;
}

.kicker-line {
  width: 72px;
  height: 9px;
  margin-bottom: 18px;
}

.line {
  height: 26px;
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

@media (min-width: 960px) {
  .article {
    max-width: 860px;
    margin: 0 auto;
    padding: 40px 48px 48px;
  }

  h1 {
    font-size: 48px;
  }

  .byline {
    font-size: 12px;
  }

  .content p {
    font-size: 18px;
    line-height: 1.95;
  }

  .cover img {
    max-height: 460px;
  }

  .related {
    max-width: 860px;
    margin: 0 auto;
    padding: 28px 48px 14px;
  }

  .related h2 {
    font-size: 28px;
  }

  .related-title {
    font-size: 18px;
  }

  .footnote {
    max-width: 860px;
    margin: 0 auto;
  }

  .actionbar {
    padding: 12px 48px;
  }
}
</style>
