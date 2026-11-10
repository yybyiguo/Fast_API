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
      <svg viewBox="0 0 24 24" width="14" height="14">
        <path
          d="M12 4v13m0 0 5-5m-5 5-5-5"
          fill="none"
          stroke="currentColor"
          stroke-width="1.6"
          stroke-linecap="round"
          stroke-linejoin="round"
        />
      </svg>
    </span>
    <span>{{ refreshing ? 'REFRESHING' : ready ? 'RELEASE' : 'PULL TO REFRESH' }}</span>
  </div>
</template>

<style scoped>
.pull {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  overflow: hidden;
  color: #5f646c;
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
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
