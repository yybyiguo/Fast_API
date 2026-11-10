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
  right: 0;
  bottom: calc(var(--tabbar-h) + var(--safe-bottom) + 14px);
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
  padding: 11px 15px;
  border: 1px solid var(--line);
  border-left: 3px solid var(--red);
  color: #fff;
  background: rgba(29, 29, 39, 0.94);
  box-shadow: var(--shadow-float);
  backdrop-filter: blur(16px);
  font-size: 12.5px;
  line-height: 1.5;
}

.label {
  flex: 0 0 auto;
  color: #ff8fa3;
  font-family: var(--font-sans);
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.16em;
}

.toast.success .label {
  color: var(--cyan);
}

.text {
  color: #f4f4f7;
}

.toast-enter-active,
.toast-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateY(8px);
}

@media (min-width: 960px) {
  .toast-layer {
    right: 28px;
    bottom: 88px;
    left: auto;
    justify-content: flex-end;
    padding: 0;
  }
}
</style>
