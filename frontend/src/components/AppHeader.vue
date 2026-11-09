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
      <svg viewBox="0 0 24 24" width="21" height="21" aria-hidden="true">
        <path
          d="M14.5 5 8 12l6.5 7"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
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
  gap: 4px;
  height: calc(50px + var(--safe-top));
  padding: var(--safe-top) 8px 0;
  border-bottom: 1px solid var(--c-line);
  background: rgba(255, 255, 255, 0.96);
  backdrop-filter: blur(10px);
}

.back,
.back-placeholder {
  flex: 0 0 auto;
  width: 42px;
  height: 42px;
}

.back {
  display: grid;
  place-items: center;
  border-radius: 50%;
  color: var(--c-ink);
  transition: background 0.15s ease;
}

.back:active {
  background: #f2f3f5;
}

h1 {
  flex: 1 1 auto;
  overflow: hidden;
  font-size: 16.5px;
  font-weight: 600;
  letter-spacing: 0.2px;
  text-align: center;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  flex: 0 0 auto;
  min-width: 42px;
  height: 42px;
  padding-right: 4px;
}
</style>
