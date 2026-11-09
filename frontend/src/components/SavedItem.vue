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
  return parts.join(' · ')
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
      <svg v-if="action === 'heart'" viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">
        <path
          d="M12 20.2S4.6 15.6 4.6 10.4A4.35 4.35 0 0 1 12 7.1a4.35 4.35 0 0 1 7.4 3.3c0 5.2-7.4 9.8-7.4 9.8z"
          fill="currentColor"
          stroke="currentColor"
          stroke-width="1.4"
          stroke-linejoin="round"
        />
      </svg>
      <svg v-else viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
        <path d="M7 7l10 10M17 7 7 17" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
      </svg>
    </button>
  </div>
</template>

<style scoped>
.saved-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 14px 10px 14px 14px;
  border-radius: var(--radius-lg);
  background: var(--c-card);
  box-shadow: var(--shadow-card);
}

.content {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
  text-align: left;
}

.title {
  display: -webkit-box;
  overflow: hidden;
  color: var(--c-ink);
  font-size: 16px;
  font-weight: 600;
  line-height: 1.42;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.desc {
  display: -webkit-box;
  overflow: hidden;
  color: #6f757e;
  font-size: 12.5px;
  line-height: 1.5;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 1;
}

.meta {
  color: var(--c-muted);
  font-size: 11.5px;
}

.action {
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  color: #b9bfc8;
  transition: background 0.15s ease, color 0.15s ease;
}

.action.liked {
  color: var(--c-primary);
}

.action:active {
  background: #f4f5f7;
}
</style>
