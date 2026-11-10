<script setup>
import { useRouter } from 'vue-router'

defineProps({
  title: { type: String, default: '' },
  back: { type: Boolean, default: false }
})

const router = useRouter()

function goBack() {
  if (window.history.length > 1) router.back()
  else router.push('/')
}
</script>

<template>
  <header class="topbar">
    <button v-if="back" type="button" class="back" aria-label="返回" @click="goBack">
      <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
        <path
          d="M14.5 5 8 12l6.5 7"
          fill="none"
          stroke="currentColor"
          stroke-width="1.6"
          stroke-linecap="round"
          stroke-linejoin="round"
        />
      </svg>
    </button>
    <span v-else class="back-placeholder" aria-hidden="true"></span>

    <h1>{{ title }}</h1>

    <div class="actions">
      <slot />
    </div>
  </header>
</template>

<style scoped>
.topbar {
  display: flex;
  align-items: center;
  flex: 0 0 auto;
  gap: 6px;
  height: calc(54px + var(--safe-top));
  padding: var(--safe-top) 12px 0;
  border-bottom: 1px solid var(--hairline);
  background: rgba(10, 10, 10, 0.92);
  backdrop-filter: blur(14px);
}

.back,
.back-placeholder {
  flex: 0 0 auto;
  width: 36px;
  height: 36px;
}

.back {
  display: grid;
  place-items: center;
  border: 1px solid var(--pill-border);
  border-radius: 50%;
  color: var(--ink);
  transition: background 0.16s ease;
}

.back:active {
  background: rgba(255, 255, 255, 0.08);
}

h1 {
  flex: 1 1 auto;
  overflow: hidden;
  color: var(--ink);
  font-size: 13px;
  font-weight: 400;
  letter-spacing: 0.02em;
  text-align: center;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  flex: 0 0 auto;
  min-width: 36px;
  height: 36px;
}
</style>
