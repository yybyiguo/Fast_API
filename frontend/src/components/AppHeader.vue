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
          stroke-width="1.8"
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
  gap: 8px;
  height: calc(52px + var(--safe-top));
  padding: var(--safe-top) 14px 0;
  border-bottom: 1px solid var(--line);
  background: rgba(10, 10, 16, 0.86);
  backdrop-filter: blur(18px) saturate(150%);
}

.back,
.back-placeholder {
  flex: 0 0 auto;
  width: 34px;
  height: 34px;
}

.back {
  display: grid;
  place-items: center;
  border: 1px solid var(--line);
  border-radius: 11px;
  color: var(--ink);
  background: rgba(255, 255, 255, 0.04);
  transition: background 0.18s ease, color 0.18s ease;
}

.back:active {
  color: #fff;
  background: var(--red);
}

h1 {
  flex: 1 1 auto;
  overflow: hidden;
  color: var(--ink);
  font-family: var(--font-serif);
  font-size: 16px;
  font-weight: 700;
  letter-spacing: -0.01em;
  text-align: center;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  flex: 0 0 auto;
  min-width: 34px;
  height: 34px;
}

@media (min-width: 960px) {
  .topbar {
    height: calc(60px + var(--safe-top));
    border-top: 3px solid var(--red);
    padding: var(--safe-top) 40px 0;
  }

  h1 {
    font-size: 17px;
  }
}
</style>
