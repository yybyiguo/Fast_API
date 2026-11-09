<script setup>
import { computed } from 'vue'

const props = defineProps({
  pull: { type: Number, default: 0 },
  ready: { type: Boolean, default: false },
  refreshing: { type: Boolean, default: false },
  dragging: { type: Boolean, default: false },
  threshold: { type: Number, default: 62 }
})

const rotation = computed(
  () => `rotate(${Math.min(props.pull / props.threshold, 1) * 180}deg)`
)
</script>

<template>
  <div class="pull" :class="{ dragging }" :style="{ height: `${pull}px` }" aria-hidden="true">
    <span class="icon" :class="{ spin: refreshing }" :style="refreshing ? null : { transform: rotation }">
      <svg viewBox="0 0 24 24" width="18" height="18">
        <path
          d="M12 4v13m0 0 5-5m-5 5-5-5"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        />
      </svg>
    </span>
    <span>{{ refreshing ? '正在刷新…' : ready ? '松开刷新' : '下拉刷新' }}</span>
  </div>
</template>

<style scoped>
.pull {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  overflow: hidden;
  color: var(--c-muted);
  font-size: 12px;
  transition: height 0.28s cubic-bezier(0.32, 0.72, 0, 1);
}

.pull.dragging {
  transition: none;
}

.icon {
  display: grid;
  place-items: center;
  transition: transform 0.12s linear;
}

.icon.spin svg {
  animation: spin 0.8s linear infinite;
}
</style>
