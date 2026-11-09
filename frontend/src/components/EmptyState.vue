<script setup>
defineProps({
  icon: { type: String, default: 'news' },
  title: { type: String, default: '暂无内容' },
  description: { type: String, default: '' },
  actionText: { type: String, default: '' }
})

defineEmits(['action'])
</script>

<template>
  <div class="empty">
    <div class="art" :class="icon" aria-hidden="true">
      <svg v-if="icon === 'heart'" viewBox="0 0 24 24" width="30" height="30">
        <path
          d="M12 20.3S4.5 15.6 4.5 10.4A4.4 4.4 0 0 1 12 7a4.4 4.4 0 0 1 7.5 3.4c0 5.2-7.5 9.9-7.5 9.9z"
          fill="none"
          stroke="currentColor"
          stroke-width="1.7"
          stroke-linejoin="round"
        />
      </svg>
      <svg v-else-if="icon === 'clock'" viewBox="0 0 24 24" width="30" height="30">
        <circle cx="12" cy="12" r="8.4" fill="none" stroke="currentColor" stroke-width="1.7" />
        <path d="M12 7.4V12l3 1.8" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" />
      </svg>
      <svg v-else-if="icon === 'lock'" viewBox="0 0 24 24" width="30" height="30">
        <rect x="5" y="10" width="14" height="9.5" rx="2.4" fill="none" stroke="currentColor" stroke-width="1.7" />
        <path d="M8.4 10V7.6a3.6 3.6 0 0 1 7.2 0V10" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" />
      </svg>
      <svg v-else-if="icon === 'error'" viewBox="0 0 24 24" width="30" height="30">
        <circle cx="12" cy="12" r="8.4" fill="none" stroke="currentColor" stroke-width="1.7" />
        <path d="M12 7.6v5" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
        <circle cx="12" cy="16.2" r="1.1" fill="currentColor" />
      </svg>
      <svg v-else-if="icon === 'rss'" viewBox="0 0 24 24" width="30" height="30">
        <path
          d="M6 6.5a11.5 11.5 0 0 1 11.5 11.5M6 11.6a6.4 6.4 0 0 1 6.4 6.4"
          fill="none"
          stroke="currentColor"
          stroke-width="1.9"
          stroke-linecap="round"
        />
        <circle cx="7.1" cy="17.4" r="1.7" fill="currentColor" />
      </svg>
      <svg v-else viewBox="0 0 24 24" width="30" height="30">
        <path d="M5 5.5h11.5a2 2 0 0 1 2 2v11H7a2 2 0 0 1-2-2z" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round" />
        <path d="M8.6 9h6.4M8.6 12.4h6.4M8.6 15.8h4" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" />
      </svg>
    </div>

    <h3>{{ title }}</h3>
    <p v-if="description">{{ description }}</p>

    <button v-if="actionText" type="button" class="action" @click="$emit('action')">
      {{ actionText }}
    </button>
  </div>
</template>

<style scoped>
.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 52px 30px 40px;
  text-align: center;
  animation: fade-up 0.3s ease both;
}

.art {
  display: grid;
  place-items: center;
  width: 72px;
  height: 72px;
  margin-bottom: 16px;
  border-radius: 24px;
  color: var(--c-primary);
  background: linear-gradient(145deg, #fff1ef, #ffe1de);
}

.art.error {
  color: #b0621c;
  background: linear-gradient(145deg, #fff4e6, #ffe7cc);
}

.art.lock {
  color: #5b6472;
  background: linear-gradient(145deg, #f1f3f6, #e6e9ee);
}

h3 {
  font-size: 16.5px;
  font-weight: 600;
}

p {
  max-width: 270px;
  margin-top: 8px;
  color: var(--c-muted);
  font-size: 13px;
  line-height: 1.65;
  word-break: break-word;
}

.action {
  height: 42px;
  margin-top: 20px;
  padding: 0 22px;
  border-radius: 999px;
  color: #fff;
  background: linear-gradient(135deg, #ff6b57, var(--c-primary));
  box-shadow: 0 8px 20px rgba(239, 59, 52, 0.26);
  font-size: 14px;
  font-weight: 600;
  transition: transform 0.15s ease;
}

.action:active {
  transform: scale(0.97);
}
</style>
