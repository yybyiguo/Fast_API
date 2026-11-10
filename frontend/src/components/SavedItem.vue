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
      <svg v-if="action === 'heart'" viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
        <path
          d="M12 20.2S4.6 15.6 4.6 10.4A4.35 4.35 0 0 1 12 7.1a4.35 4.35 0 0 1 7.4 3.3c0 5.2-7.4 9.8-7.4 9.8z"
          fill="currentColor"
          stroke="currentColor"
          stroke-width="1.2"
          stroke-linejoin="round"
        />
      </svg>
      <svg v-else viewBox="0 0 24 24" width="14" height="14" aria-hidden="true">
        <path d="M7 7l10 10M17 7 7 17" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
      </svg>
    </button>
  </div>
</template>

<style scoped>
.saved-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 18px 0;
  border-bottom: 1px solid var(--line);
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
  font-family: var(--font-serif);
  font-size: 19px;
  font-weight: 600;
  line-height: 1.32;
  letter-spacing: -0.012em;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.desc {
  display: -webkit-box;
  overflow: hidden;
  color: var(--ink-soft);
  font-size: 12.5px;
  line-height: 1.6;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 1;
}

.meta {
  color: var(--muted);
  font-size: 11px;
}

.action {
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  width: 32px;
  height: 32px;
  border: 1px solid var(--line);
  color: var(--muted);
  background: transparent;
  transition: border-color 0.18s ease, color 0.18s ease;
}

.action.liked {
  border-color: var(--red);
  color: var(--red);
}

.action:active {
  border-color: var(--red);
}
</style>
