<script setup>
import { useToast } from '../composables/useToast'

const { toast } = useToast()
</script>

<template>
  <Teleport to="body">
    <div class="toast-layer" aria-live="polite" aria-atomic="true">
      <Transition name="toast">
        <div v-if="toast" class="toast" :class="toast.type">
          <svg v-if="toast.type === 'success'" viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
            <path
              d="M20 6 9 17l-5-5"
              fill="none"
              stroke="currentColor"
              stroke-width="2.4"
              stroke-linecap="round"
              stroke-linejoin="round"
            />
          </svg>
          <svg v-else-if="toast.type === 'error'" viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
            <circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" stroke-width="2" />
            <path d="M12 7.5v5.2" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" />
            <circle cx="12" cy="16.2" r="1.2" fill="currentColor" />
          </svg>
          <span>{{ toast.text }}</span>
        </div>
      </Transition>
    </div>
  </Teleport>
</template>

<style scoped>
.toast-layer {
  position: fixed;
  top: calc(var(--safe-top) + 12px);
  right: 0;
  left: 0;
  z-index: 90;
  display: flex;
  justify-content: center;
  padding: 0 20px;
  pointer-events: none;
}

.toast {
  display: flex;
  align-items: center;
  gap: 8px;
  max-width: min(100%, 420px);
  padding: 9px 15px;
  border-radius: 999px;
  color: #fff;
  background: rgba(24, 26, 30, 0.93);
  box-shadow: 0 8px 24px rgba(20, 22, 26, 0.24);
  font-size: 13.5px;
  line-height: 1.4;
  backdrop-filter: blur(8px);
}

.toast.success svg {
  flex: 0 0 auto;
  color: #4ade80;
}

.toast.error svg {
  flex: 0 0 auto;
  color: #fca5a5;
}

.toast-enter-active,
.toast-leave-active {
  transition: opacity 0.22s ease, transform 0.22s ease;
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateY(-10px) scale(0.96);
}
</style>
