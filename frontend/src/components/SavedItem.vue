<script setup>
import { computed } from 'vue'
import { formatViews } from '../utils/format'

const props = defineProps({
  item: { type: Object, required: true },
  action: { type: String, default: 'heart' },
  timeText: { type: String, default: '' }
})

defineEmits(['open', 'remove'])

const meta = computed(() => {
  const parts = []
  if (props.item.author) parts.push(props.item.author)
  parts.push(`${formatViews(props.item.views)} 阅读`)
  if (props.timeText) parts.push(props.timeText)
  return parts.join(' / ')
})
</script>

<template>
  <div class="saved-item">
    <button type="button" class="content" @click="$emit('open', item)">
      <span class="title">{{ item.title || '无标题' }}</span>
      <span v-if="item.description" class="desc">{{ item.description }}</span>
      <span class="meta">{{ meta }}</span>
    </button>

    <button
      type="button"
      class="action"
      :class="{ liked: action === 'heart' }"
      :aria-label="action === 'heart' ? '取消收藏' : '删除这条历史'"
      @click="$emit('remove', item)"
    >
      <svg v-if="action === 'heart'" viewBox="0 0 24 24" width="17" height="17" aria-hidden="true">
        <path
          d="M12 20.2S4.6 15.6 4.6 10.4A4.35 4.35 0 0 1 12 7.1a4.35 4.35 0 0 1 7.4 3.3c0 5.2-7.4 9.8-7.4 9.8z"
          fill="currentColor"
          stroke="currentColor"
          stroke-width="1.2"
          stroke-linejoin="round"
        />
      </svg>
      <svg v-else viewBox="0 0 24 24" width="15" height="15" aria-hidden="true">
        <path d="M7 7l10 10M17 7 7 17" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" />
      </svg>
    </button>
  </div>
</template>

<style scoped>
.saved-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 18px 12px 18px 16px;
  border: 1px solid var(--hairline);
  border-radius: var(--radius);
  background: var(--canvas-card);
}

.content {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  gap: 7px;
  min-width: 0;
  text-align: left;
}

.title {
  display: -webkit-box;
  overflow: hidden;
  color: var(--ink);
  font-size: 16px;
  font-weight: 400;
  line-height: 1.45;
  letter-spacing: -0.01em;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.desc {
  display: -webkit-box;
  overflow: hidden;
  color: var(--mute);
  font-size: 12.5px;
  line-height: 1.55;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 1;
}

.meta {
  color: #666b73;
  font-family: var(--font-mono);
  font-size: 9.5px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.action {
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  width: 34px;
  height: 34px;
  border: 1px solid transparent;
  border-radius: 50%;
  color: #6b7078;
  transition: color 0.16s ease, border-color 0.16s ease, background 0.16s ease;
}

.action:active {
  border-color: var(--hairline);
  background: rgba(255, 255, 255, 0.06);
}

.action.liked {
  color: var(--ink);
}
</style>
