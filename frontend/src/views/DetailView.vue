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

async function share() {
  const url = window.location.href
  const title = article.value?.title || '今日资讯'
  try {
    if (navigator.share) {
      await navigator.share({ title, url })
      return
    }
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(url)
      toast.success('链接已复制')
      return
    }
    toast.error('当前浏览器不支持分享')
  } catch (error) {
    if (error?.name !== 'AbortError') toast.error('分享失败')
  }
}

function scrollTop() {
  scroller.value?.scrollTo({ top: 0, behavior: 'smooth' })
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

    <div v-if="article && !loading" class="rail" aria-label="文章操作">
      <button
        type="button"
        class="rail-btn"
        :class="{ on: favorited }"
        :disabled="favBusy"
        :aria-pressed="favorited"
        aria-label="收藏"
        @click="toggleFavorite"
      >
        <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">
          <path
            d="M12 20.2S4.6 15.6 4.6 10.4A4.35 4.35 0 0 1 12 7.1a4.35 4.35 0 0 1 7.4 3.3c0 5.2-7.4 9.8-7.4 9.8z"
            :fill="favorited ? 'currentColor' : 'none'"
            stroke="currentColor"
            stroke-width="1.7"
            stroke-linejoin="round"
          />
        </svg>
        <span>{{ favorited ? '已收藏' : '收藏' }}</span>
      </button>

      <button type="button" class="rail-btn" aria-label="分享" @click="share">
        <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">
          <path
            d="M12 15V4m0 0L8 8m4-4 4 4M5 14v5.5A1.5 1.5 0 0 0 6.5 21h11a1.5 1.5 0 0 0 1.5-1.5V14"
            fill="none"
            stroke="currentColor"
            stroke-width="1.7"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
        </svg>
        <span>分享</span>
      </button>

      <button type="button" class="rail-btn" aria-label="回到顶部" @click="scrollTop">
        <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">
          <path
            d="M12 19V5m0 0-6 6m6-6 6 6"
            fill="none"
            stroke="currentColor"
            stroke-width="1.7"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
        </svg>
        <span>顶部</span>
      </button>
    </div>
  </div>
</template>

<style scoped>
.detail-scroll {
  padding-bottom: 56px;
  background: var(--paper);
}

.article {
  padding: 24px 64px 30px 20px;
  background: var(--paper);
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
  color: #6f6f7e;
}

.cover {
  margin: 22px 0 0;
  padding: 0;
  overflow: hidden;
  border: 1px solid var(--line);
  border-radius: 18px;
  background: var(--surface-2);
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
  color: var(--ink-soft);
  font-size: 16.5px;
  line-height: 1.95;
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
  padding: 22px 64px 8px 20px;
  border-top: 1px solid var(--line);
  background: var(--paper);
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

.actionbar,
.fav,
.read-count {
  display: none;
}

.rail {
  position: fixed;
  right: 10px;
  bottom: calc(86px + var(--safe-bottom));
  z-index: 40;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.rail-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  width: 48px;
  padding: 0;
  border: 0;
  color: #fff;
  background: transparent;
  font-size: 9px;
}

.rail-btn svg {
  box-sizing: content-box;
  width: 20px;
  height: 20px;
  padding: 12px;
  border: 1px solid var(--line);
  border-radius: 50%;
  color: #fff;
  background: rgba(22, 22, 30, 0.78);
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.35);
  backdrop-filter: blur(14px);
}

.rail-btn span {
  color: var(--muted);
  font-size: 9px;
  font-weight: 500;
}

.rail-btn.on svg {
  border-color: var(--red);
  color: #fff;
  background: var(--red);
  box-shadow: 0 0 22px rgba(254, 44, 85, 0.5);
}

.rail-btn.on span {
  color: var(--red);
}

.rail-btn:active svg {
  transform: scale(0.94);
}

.article-skeleton {
  padding: 26px 20px;
  background: var(--paper);
}

.sk {
  background: linear-gradient(100deg, #1a1a24 20%, #262631 40%, #1a1a24 60%);
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

  .rail {
    right: 32px;
    bottom: 40px;
  }
}
</style>
