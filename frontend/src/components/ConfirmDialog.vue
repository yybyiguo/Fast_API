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
          <span class="kicker no-rule">{{ danger ? 'CONFIRM DELETE' : 'CONFIRM' }}</span>

          <h2>{{ title }}</h2>
          <p>{{ message }}</p>

          <div class="actions">
            <button type="button" class="btn ghost" :disabled="busy" @click="emit('cancel')">
              {{ cancelText }}
            </button>
            <button type="button" class="btn solid" :disabled="busy" @click="emit('confirm')">
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
  background: rgba(24, 24, 27, 0.55);
}

.dialog {
  width: min(100%, 340px);
  padding: 22px 20px 18px;
  border: 1px solid var(--line);
  border-top: 3px solid var(--red);
  background: var(--white);
}

.kicker {
  margin-bottom: 14px;
}

h2 {
  color: var(--ink);
  font-family: var(--font-serif);
  font-size: 24px;
  font-weight: 600;
  line-height: 1.2;
  letter-spacing: -0.025em;
}

p {
  margin-top: 10px;
  color: var(--muted);
  font-size: 13px;
  line-height: 1.7;
  word-break: break-word;
}

.actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-top: 24px;
}

.btn {
  height: 44px;
  font-size: 13px;
  font-weight: 500;
  transition: background 0.18s ease, color 0.18s ease;
}

.ghost {
  border: 1px solid var(--ink);
  color: var(--ink);
  background: transparent;
}

.ghost:active:not(:disabled) {
  color: var(--white);
  background: var(--ink);
}

.solid {
  border: 1px solid var(--red);
  color: var(--white);
  background: var(--red);
}

.solid:active:not(:disabled) {
  background: var(--red-dark);
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
  transform: translateY(6px);
  opacity: 0;
}
</style>
