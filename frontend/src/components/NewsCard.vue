<script setup>
import { computed, ref } from 'vue'
import { formatRelativeTime, formatViews } from '../utils/format'
import { resolveImage } from '../utils/media'

const props = defineProps({
  item: { type: Object, required: true },
  index: { type: Number, default: 0 },
  featured: { type: Boolean, default: false },
  categoryName: { type: String, default: '' }
})

defineEmits(['open'])

const broken = ref(false)
const image = computed(() => (broken.value ? '' : resolveImage(props.item.image)))
const time = computed(
  () => props.item.viewedAt || props.item.createdAt || props.item.publishTime
)
const indexLabel = computed(() => String(props.index + 1).padStart(2, '0'))
</script>

<template>
  <button
    type="button"
    class="story stagger"
    :class="{ featured }"
    :style="{ '--i': Math.min(index, 8) }"
    @click="$emit('open', item)"
  >
    <span v-if="!featured" class="index" aria-hidden="true">{{ indexLabel }}</span>

    <span class="body">
      <span v-if="featured" class="kicker">{{ categoryName || 'LEAD STORY' }}</span>

      <span class="title">{{ item.title || '无标题' }}</span>

      <span v-if="item.description" class="desc">{{ item.description }}</span>

      <span class="meta">
        <span v-if="item.author">{{ item.author }}</span>
        <span v-if="item.author" class="sep">·</span>
        <span>{{ formatViews(item.views) }} 阅读</span>
        <template v-if="time">
          <span class="sep">·</span>
          <span>{{ formatRelativeTime(time) }}</span>
        </template>
      </span>

      <span v-if="featured" class="read-more">
        阅读全文
        <span aria-hidden="true">→</span>
      </span>
    </span>

    <span v-if="image" class="thumb">
      <img :src="image" alt="" loading="lazy" @error="broken = true" />
    </span>
  </button>
</template>

<style scoped>
.story {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  width: 100%;
  padding: 18px 0;
  border-bottom: 1px solid var(--line);
  background: transparent;
  text-align: left;
  transition: background 0.18s ease;
}

.story:active {
  background: var(--red-soft);
}

.story.featured {
  flex-direction: column;
  gap: 0;
  padding: 22px 0 24px;
  border-bottom: 2px solid var(--ink);
}

.index {
  flex: 0 0 24px;
  padding-top: 3px;
  color: var(--red);
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.06em;
}

.body {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  gap: 7px;
  min-width: 0;
}

.kicker {
  margin-bottom: 2px;
}

.title {
  display: -webkit-box;
  overflow: hidden;
  color: var(--ink);
  font-family: var(--font-serif);
  font-size: 19px;
  font-weight: 600;
  line-height: 1.32;
  letter-spacing: -0.012em;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
}

.featured .title {
  font-size: clamp(27px, 8vw, 33px);
  line-height: 1.16;
  letter-spacing: -0.03em;
  -webkit-line-clamp: 4;
}

.desc {
  display: -webkit-box;
  overflow: hidden;
  color: var(--ink-soft);
  font-size: 13px;
  line-height: 1.65;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.featured .desc {
  margin-top: 3px;
  font-size: 14px;
  line-height: 1.7;
  -webkit-line-clamp: 3;
}

.meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  margin-top: 2px;
  color: var(--muted);
  font-size: 11px;
  line-height: 1.5;
}

.sep {
  padding: 0 6px;
  color: #c4c4c8;
}

.read-more {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  margin-top: 6px;
  color: var(--red);
  font-size: 12px;
  font-weight: 500;
  letter-spacing: 0.02em;
}

.thumb {
  flex: 0 0 auto;
  width: 92px;
  height: 72px;
  overflow: hidden;
  border: 1px solid var(--line);
  background: var(--paper-warm);
}

.featured .thumb {
  width: 100%;
  height: 200px;
  margin-top: 16px;
  border-color: var(--line-strong);
}

.thumb img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

@media (min-width: 960px) {
  .story {
    padding: 22px 0;
  }

  .title {
    font-size: 21px;
  }

  .desc {
    font-size: 13.5px;
  }

  .featured {
    padding: 30px 0 34px;
  }

  .featured .title {
    font-size: clamp(38px, 4vw, 52px);
  }

  .featured .desc {
    max-width: 860px;
    font-size: 16px;
    -webkit-line-clamp: 4;
  }

  .featured .thumb {
    height: 360px;
    margin-top: 22px;
  }

  .thumb {
    width: 112px;
    height: 84px;
  }

  .meta {
    font-size: 11.5px;
  }

  .read-more {
    font-size: 13px;
  }
}
</style>
