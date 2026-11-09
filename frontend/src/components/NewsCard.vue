<script setup>
import { computed, ref } from 'vue'
import { formatRelativeTime, formatViews } from '../utils/format'
import { resolveImage } from '../utils/media'

const props = defineProps({
  item: { type: Object, required: true },
  showTime: { type: Boolean, default: false }
})

defineEmits(['open'])

const broken = ref(false)
const image = computed(() => (broken.value ? '' : resolveImage(props.item.image)))
const time = computed(() => {
  if (!props.showTime) return props.item.publishTime
  return props.item.viewedAt || props.item.createdAt || props.item.publishTime
})
</script>

<template>
  <button type="button" class="news-card" @click="$emit('open', item)">
    <span class="body">
      <span class="title">{{ item.title || '无标题' }}</span>
      <span v-if="item.description" class="desc">{{ item.description }}</span>
      <span class="meta">
        <span v-if="item.author" class="author">{{ item.author }}</span>
        <span v-if="item.author" class="dot">·</span>
        <span>{{ formatViews(item.views) }} 阅读</span>
        <template v-if="time">
          <span class="dot">·</span>
          <span>{{ formatRelativeTime(time) }}</span>
        </template>
      </span>
    </span>

    <span v-if="image" class="thumb">
      <img :src="image" alt="" loading="lazy" @error="broken = true" />
    </span>
  </button>
</template>

<style scoped>
.news-card {
  display: flex;
  align-items: stretch;
  gap: 12px;
  width: 100%;
  padding: 14px;
  border-radius: var(--radius-lg);
  background: var(--c-card);
  box-shadow: var(--shadow-card);
  text-align: left;
  transition: transform 0.16s ease, box-shadow 0.16s ease;
}

.news-card:active {
  transform: scale(0.988);
}

.body {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  justify-content: space-between;
  gap: 6px;
  min-width: 0;
}

.title {
  display: -webkit-box;
  overflow: hidden;
  color: var(--c-ink);
  font-size: 16.5px;
  font-weight: 600;
  line-height: 1.42;
  letter-spacing: 0.1px;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.desc {
  display: -webkit-box;
  overflow: hidden;
  color: #6f757e;
  font-size: 13px;
  line-height: 1.5;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  margin-top: 1px;
  color: var(--c-muted);
  font-size: 11.5px;
  line-height: 1.4;
}

.author {
  color: #7d838d;
}

.thumb {
  flex: 0 0 auto;
  align-self: center;
  width: 104px;
  height: 78px;
  overflow: hidden;
  border-radius: 10px;
  background: #f1f2f5;
}

.thumb img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
}
</style>
