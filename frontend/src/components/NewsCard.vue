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
        <span v-if="item.author" class="dot">/</span>
        <span>{{ formatViews(item.views) }} 阅读</span>
        <template v-if="time">
          <span class="dot">/</span>
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
  gap: 14px;
  width: 100%;
  padding: 18px 16px;
  border: 1px solid var(--hairline);
  border-radius: var(--radius);
  background: var(--canvas-card);
  text-align: left;
  transition: border-color 0.16s ease, background 0.16s ease;
}

.news-card:active {
  border-color: #303338;
  background: #1d1e21;
}

.body {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  gap: 7px;
  min-width: 0;
}

.title {
  display: -webkit-box;
  overflow: hidden;
  color: var(--ink);
  font-size: 17px;
  font-weight: 400;
  line-height: 1.45;
  letter-spacing: -0.012em;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
}

.desc {
  display: -webkit-box;
  overflow: hidden;
  color: var(--mute);
  font-size: 12.5px;
  line-height: 1.6;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  margin-top: 3px;
  color: #666b73;
  font-family: var(--font-mono);
  font-size: 9.5px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.author {
  color: #9ca1a8;
}

.thumb {
  flex: 0 0 auto;
  align-self: center;
  width: 92px;
  height: 70px;
  overflow: hidden;
  border: 1px solid var(--hairline);
  border-radius: 6px;
  background: var(--canvas-soft);
}

.thumb img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
  opacity: 0.92;
}
</style>
