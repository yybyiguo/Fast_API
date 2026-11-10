<script setup>
import { computed } from 'vue'

const props = defineProps({
  icon: { type: String, default: 'news' },
  title: { type: String, default: '暂无内容' },
  description: { type: String, default: '' },
  actionText: { type: String, default: '' }
})

defineEmits(['action'])

const label = computed(() => {
  if (props.icon === 'error') return 'ERROR'
  if (props.icon === 'lock') return 'LOCKED'
  if (props.icon === 'heart') return 'SAVED STORIES'
  if (props.icon === 'clock') return 'HISTORY'
  if (props.icon === 'rss') return 'RSS SOURCES'
  return 'NO STORIES'
})
</script>

<template>
  <div class="empty">
    <span class="mark" aria-hidden="true"></span>
    <span class="kicker no-rule">{{ label }}</span>
    <h3>{{ title }}</h3>
    <p v-if="description">{{ description }}</p>
    <button v-if="actionText" type="button" class="action" @click="$emit('action')">
      {{ actionText }}
      <span aria-hidden="true">→</span>
    </button>
  </div>
</template>

<style scoped>
.empty {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  padding: 48px 8px 52px;
  text-align: left;
  animation: story-rise 0.3s ease both;
}

.mark {
  width: 40px;
  height: 3px;
  margin-bottom: 18px;
  background: var(--red);
}

.kicker {
  margin-bottom: 14px;
}

h3 {
  color: var(--ink);
  font-family: var(--font-serif);
  font-size: 26px;
  font-weight: 600;
  line-height: 1.2;
  letter-spacing: -0.025em;
}

p {
  max-width: 30em;
  margin-top: 10px;
  color: var(--muted);
  font-size: 13px;
  line-height: 1.7;
  word-break: break-word;
}

.action {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  height: 42px;
  margin-top: 24px;
  padding: 0 20px;
  border: 1px solid var(--red);
  color: #fff;
  background: var(--red);
  font-size: 12.5px;
  font-weight: 500;
  transition: background 0.18s ease;
}

.action:active {
  background: var(--red-dark);
}
</style>
