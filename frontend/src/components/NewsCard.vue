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
    :class="[{ featured }, `tone-${index % 3}`]"
    :style="{ '--i': Math.min(index, 8) }"
    @click="$emit('open', item)"
  >
    <span class="media">
      <img v-if="image" :src="image" alt="" loading="lazy" @error="broken = true" />

      <span v-else class="fallback" aria-hidden="true">
        <span class="fallback-index">{{ indexLabel }}</span>
      </span>

      <span class="shade" aria-hidden="true"></span>
      <span v-if="featured" class="badge">头条</span>
      <span v-else class="index" aria-hidden="true">{{ indexLabel }}</span>

      <span class="hero-copy" :class="{ 'hero-copy--small': !featured }">
        <span class="hero-cat">{{ categoryName || '推荐' }}</span>
        <span class="hero-title">{{ item.title || '无标题' }}</span>
      </span>
    </span>

    <span class="body">
      <span v-if="item.description" class="desc">{{ item.description }}</span>

      <span class="meta">
        <span v-if="item.author" class="author">{{ item.author }}</span>
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
  </button>
</template>

<style scoped>
.story {
  display: flex;
  flex-direction: column;
  width: 100%;
  padding: 7px;
  overflow: hidden;
  border: 1px solid var(--line);
  border-radius: 22px;
  background: var(--surface);
  box-shadow: 0 14px 34px rgba(0, 0, 0, 0.28);
  text-align: left;
  transition: transform 0.2s ease, border-color 0.2s ease;
}

.story:active {
  border-color: rgba(254, 44, 85, 0.45);
  transform: scale(0.985);
}

.media {
  position: relative;
  flex: 0 0 auto;
  width: 100%;
  height: 172px;
  overflow: hidden;
  border-radius: 17px;
  background: #1b1b26;
}

.featured .media {
  height: 280px;
  border-radius: 18px;
}

.media img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.45s ease;
}

.shade {
  position: absolute;
  inset: 0;
  z-index: 1;
  background: linear-gradient(180deg, rgba(0, 0, 0, 0.05) 35%, rgba(0, 0, 0, 0.78));
  pointer-events: none;
}

.hero-copy {
  position: absolute;
  right: 16px;
  bottom: 16px;
  left: 16px;
  z-index: 3;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.hero-cat {
  color: var(--cyan);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.16em;
  text-transform: uppercase;
}

.hero-title {
  display: -webkit-box;
  overflow: hidden;
  color: #fff;
  font-size: clamp(23px, 7vw, 28px);
  font-weight: 800;
  line-height: 1.24;
  letter-spacing: -0.03em;
  text-shadow: 0 2px 24px rgba(0, 0, 0, 0.55);
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 4;
}

.fallback {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 16px;
  background:
    radial-gradient(circle at 18% 18%, rgba(254, 44, 85, 0.55), transparent 48%),
    radial-gradient(circle at 82% 82%, rgba(37, 244, 238, 0.24), transparent 52%),
    linear-gradient(135deg, #1d1d29, #0d0d14);
}

.tone-1 .fallback {
  background:
    radial-gradient(circle at 82% 20%, rgba(254, 44, 85, 0.45), transparent 45%),
    radial-gradient(circle at 15% 80%, rgba(37, 244, 238, 0.3), transparent 48%),
    linear-gradient(135deg, #151d27, #0b0c12);
}

.tone-2 .fallback {
  background:
    radial-gradient(circle at 50% 0%, rgba(37, 244, 238, 0.24), transparent 45%),
    radial-gradient(circle at 90% 90%, rgba(254, 44, 85, 0.4), transparent 50%),
    linear-gradient(160deg, #1a1620, #0b0b10);
}

.hero-copy--small {
  right: 12px;
  bottom: 12px;
  left: 12px;
  gap: 5px;
}

.hero-copy--small .hero-title {
  font-size: 17px;
  line-height: 1.35;
  letter-spacing: -0.015em;
  -webkit-line-clamp: 2;
}

.hero-copy--small .hero-cat {
  font-size: 9px;
  letter-spacing: 0.12em;
}

.fallback-index {
  position: absolute;
  right: 10px;
  bottom: -6px;
  color: rgba(255, 255, 255, 0.1);
  font-size: 92px;
  font-weight: 800;
  line-height: 0.8;
  letter-spacing: -0.08em;
}

.badge {
  position: absolute;
  top: 10px;
  left: 10px;
  z-index: 2;
  padding: 4px 10px;
  border-radius: 999px;
  color: #fff;
  background: var(--red);
  box-shadow: 0 6px 18px rgba(254, 44, 85, 0.4);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.08em;
}

.index {
  position: absolute;
  top: 10px;
  right: 10px;
  z-index: 2;
  min-width: 26px;
  padding: 4px 7px;
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 8px;
  color: rgba(255, 255, 255, 0.9);
  background: rgba(0, 0, 0, 0.45);
  backdrop-filter: blur(10px);
  font-family: var(--font-mono);
  font-size: 9px;
  text-align: center;
}

.body {
  display: flex;
  flex-direction: column;
  gap: 7px;
  min-width: 0;
  padding: 12px 7px 7px;
}

.cat {
  color: var(--red);
  font-size: 9.5px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.title {
  display: -webkit-box;
  overflow: hidden;
  color: var(--ink);
  font-size: 17px;
  font-weight: 700;
  line-height: 1.38;
  letter-spacing: -0.015em;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
}

.featured .title {
  font-size: clamp(24px, 7.2vw, 30px);
  line-height: 1.24;
  letter-spacing: -0.03em;
  -webkit-line-clamp: 4;
}

.featured .fallback-cat {
  display: none;
}

.desc {
  display: -webkit-box;
  overflow: hidden;
  color: var(--muted);
  font-size: 12.5px;
  line-height: 1.65;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.featured .desc {
  font-size: 14px;
  line-height: 1.7;
  -webkit-line-clamp: 3;
}

.meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 1px;
  color: var(--muted);
  font-size: 10.5px;
  line-height: 1.5;
}

.author {
  color: var(--ink-soft);
}

.sep {
  color: rgba(255, 255, 255, 0.24);
}

.read-more {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-top: 3px;
  color: var(--red);
  font-size: 12.5px;
  font-weight: 700;
}

@media (min-width: 960px) {
  .media {
    height: 190px;
  }

  .featured .media {
    height: 400px;
  }

  .hero-title {
    font-size: clamp(30px, 3.2vw, 40px);
  }

  .title {
    font-size: 18px;
  }

  .featured .title {
    font-size: clamp(30px, 3.2vw, 40px);
    -webkit-line-clamp: 3;
  }

  .featured .desc {
    font-size: 15px;
    -webkit-line-clamp: 4;
  }

  .story:hover {
    border-color: rgba(255, 255, 255, 0.18);
    transform: translateY(-2px);
  }

  .story:hover .media img {
    transform: scale(1.035);
  }
}
</style>
