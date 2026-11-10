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
    <div class="frame" aria-hidden="true">
      <svg v-if="icon === 'heart'" viewBox="0 0 24 24" width="24" height="24">
        <path
          d="M12 20.3S4.5 15.6 4.5 10.4A4.4 4.4 0 0 1 12 7a4.4 4.4 0 0 1 7.5 3.4c0 5.2-7.5 9.9-7.5 9.9z"
          fill="none"
          stroke="currentColor"
          stroke-width="1.4"
          stroke-linejoin="round"
        />
      </svg>
      <svg v-else-if="icon === 'clock'" viewBox="0 0 24 24" width="24" height="24">
        <circle cx="12" cy="12" r="8.4" fill="none" stroke="currentColor" stroke-width="1.4" />
        <path d="M12 7.4V12l3 1.8" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" />
      </svg>
      <svg v-else-if="icon === 'lock'" viewBox="0 0 24 24" width="24" height="24">
        <rect x="5" y="10" width="14" height="9.5" rx="2.4" fill="none" stroke="currentColor" stroke-width="1.4" />
        <path d="M8.4 10V7.6a3.6 3.6 0 0 1 7.2 0V10" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" />
      </svg>
      <svg v-else-if="icon === 'error'" viewBox="0 0 24 24" width="24" height="24">
        <circle cx="12" cy="12" r="8.4" fill="none" stroke="currentColor" stroke-width="1.4" />
        <path d="M12 7.6v5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" />
        <circle cx="12" cy="16.2" r="1.1" fill="currentColor" />
      </svg>
      <svg v-else-if="icon === 'rss'" viewBox="0 0 24 24" width="24" height="24">
        <path
          d="M6 6.5a11.5 11.5 0 0 1 11.5 11.5M6 11.6a6.4 6.4 0 0 1 6.4 6.4"
          fill="none"
          stroke="currentColor"
          stroke-width="1.5"
          stroke-linecap="round"
        />
        <circle cx="7.1" cy="17.4" r="1.6" fill="currentColor" />
      </svg>
      <svg v-else viewBox="0 0 24 24" width="24" height="24">
        <path d="M5 5.5h11.5a2 2 0 0 1 2 2v11H7a2 2 0 0 1-2-2z" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round" />
        <path d="M8.6 9h6.4M8.6 12.4h6.4M8.6 15.8h4" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" />
      </svg>
    </div>

    <span class="eyebrow no-dot">
      {{ icon === 'error' ? 'ERROR' : icon === 'lock' ? 'LOCKED' : 'EMPTY' }}
    </span>

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
  align-items: center;
  padding: 56px 30px 44px;
  text-align: center;
  animation: fade-up 0.3s ease both;
}

.frame {
  display: grid;
  place-items: center;
  width: 62px;
  height: 62px;
  margin-bottom: 18px;
  border: 1px solid var(--hairline);
  border-radius: var(--radius);
  color: var(--ink);
  background: transparent;
}

.eyebrow {
  margin-bottom: 12px;
}

h3 {
  color: var(--ink);
  font-size: 20px;
  font-weight: 400;
  letter-spacing: -0.02em;
}

p {
  max-width: 280px;
  margin-top: 8px;
  color: var(--mute);
  font-size: 12.5px;
  line-height: 1.7;
  word-break: break-word;
}

.action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  height: 38px;
  margin-top: 22px;
  padding: 0 20px;
  border: 1px solid var(--pill-border);
  border-radius: var(--pill);
  color: var(--ink);
  background: transparent;
  font-size: 12.5px;
  transition: background 0.16s ease;
}

.action:active {
  background: rgba(255, 255, 255, 0.08);
}
</style>
