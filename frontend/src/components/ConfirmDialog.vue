<script setup>
import { onBeforeUnmount, watch } from 'vue'

const props = defineProps({
  open: { type: Boolean, default: false },
  title: { type: String, default: '确认操作' },
  message: { type: String, default: '' },
  confirmText: { type: String, default: '确定' },
  cancelText: { type: String, default: '取消' },
  danger: { type: Boolean, default: true },
  busy: { type: Boolean, default: false }
})

const emit = defineEmits(['confirm', 'cancel'])

function onKeydown(event) {
  if (event.key === 'Escape' && props.open && !props.busy) emit('cancel')
}

watch(
  () => props.open,
  (open) => {
    if (open) window.addEventListener('keydown', onKeydown)
    else window.removeEventListener('keydown', onKeydown)
  }
)

onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))
</script>

<template>
  <Teleport to="body">
    <Transition name="dialog">
      <div v-if="open" class="mask" @click.self="!busy && emit('cancel')">
        <div class="dialog" role="alertdialog" aria-modal="true" :aria-label="title">
          <div class="icon" :class="{ danger }" aria-hidden="true">
            <svg v-if="danger" viewBox="0 0 24 24" width="24" height="24">
              <path
                d="M4 7h16M9.5 7V5.4c0-.8.7-1.4 1.5-1.4h2c.8 0 1.5.6 1.5 1.4V7M6.4 7l.8 12.1c0 .9.8 1.6 1.7 1.6h6.2c.9 0 1.6-.7 1.7-1.6L18.4 7"
                fill="none"
                stroke="currentColor"
                stroke-width="1.8"
                stroke-linecap="round"
                stroke-linejoin="round"
              />
            </svg>
            <svg v-else viewBox="0 0 24 24" width="24" height="24">
              <circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" stroke-width="1.8" />
              <path d="M12 7.6v5" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" />
              <circle cx="12" cy="16.2" r="1.2" fill="currentColor" />
            </svg>
          </div>

          <h2>{{ title }}</h2>
          <p>{{ message }}</p>

          <div class="actions">
            <button type="button" class="btn ghost" :disabled="busy" @click="emit('cancel')">
              {{ cancelText }}
            </button>
            <button
              type="button"
              class="btn solid"
              :class="danger ? 'danger' : 'primary'"
              :disabled="busy"
              @click="emit('confirm')"
            >
              {{ busy ? '处理中…' : confirmText }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.mask {
  position: fixed;
  inset: 0;
  z-index: 70;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: rgba(15, 17, 21, 0.46);
  backdrop-filter: blur(2px);
}

.dialog {
  width: min(100%, 320px);
  padding: 24px 20px 18px;
  border-radius: 22px;
  background: #fff;
  box-shadow: 0 24px 60px rgba(15, 17, 21, 0.28);
  text-align: center;
}

.icon {
  display: grid;
  place-items: center;
  width: 52px;
  height: 52px;
  margin: 0 auto 14px;
  border-radius: 50%;
  color: var(--c-primary);
  background: rgba(239, 59, 52, 0.1);
}

.icon.danger {
  color: var(--c-danger);
  background: rgba(224, 51, 43, 0.1);
}

h2 {
  font-size: 17px;
  font-weight: 600;
  letter-spacing: 0.2px;
}

p {
  margin-top: 8px;
  color: var(--c-ink-2);
  font-size: 14px;
  line-height: 1.6;
  word-break: break-word;
}

.actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-top: 22px;
}

.btn {
  height: 46px;
  border-radius: 13px;
  font-size: 15px;
  font-weight: 600;
  transition: transform 0.15s ease;
}

.btn:active:not(:disabled) {
  transform: scale(0.97);
}

.ghost {
  color: var(--c-ink-2);
  background: #f1f2f5;
}

.solid {
  color: #fff;
}

.solid.danger {
  background: var(--c-danger);
}

.solid.primary {
  background: var(--c-primary);
}

.dialog-enter-active,
.dialog-leave-active {
  transition: opacity 0.2s ease;
}

.dialog-enter-active .dialog,
.dialog-leave-active .dialog {
  transition: transform 0.22s ease, opacity 0.22s ease;
}

.dialog-enter-from,
.dialog-leave-to {
  opacity: 0;
}

.dialog-enter-from .dialog,
.dialog-leave-to .dialog {
  transform: scale(0.94);
  opacity: 0;
}
</style>
