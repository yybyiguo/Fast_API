<script setup>
import { useToast } from '../composables/useToast'

const { toast } = useToast()
</script>

<template>
  <Teleport to="body">
    <div class="toast-layer" aria-live="polite" aria-atomic="true">
      <Transition name="toast">
        <div v-if="toast" class="toast" :class="toast.type">
          <span class="label">{{ toast.type === 'error' ? 'ERR' : toast.type === 'success' ? 'OK' : 'INFO' }}</span>
          <span class="text">{{ toast.text }}</span>
        </div>
      </Transition>
    </div>
  </Teleport>
</template>

<style scoped>
.toast-layer {
  position: fixed;
  top: calc(var(--safe-top) + 14px);
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
  gap: 10px;
  max-width: min(100%, 440px);
  padding: 11px 14px;
  border: 1px solid var(--hairline);
  border-radius: 6px;
  color: var(--ink);
  background: rgba(16, 17, 19, 0.96);
  font-size: 12.5px;
  line-height: 1.45;
  backdrop-filter: blur(12px);
}

.label {
  flex: 0 0 auto;
  color: var(--mute);
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.16em;
}

.toast.error .label {
  color: var(--accent-soft);
}

.toast.success .label {
  color: var(--ink);
}

.text {
  color: var(--ink-dim);
}

.toast-enter-active,
.toast-leave-active {
  transition: opacity 0.22s ease, transform 0.22s ease;
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>
