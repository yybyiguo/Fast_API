<script setup>
defineProps({
  hasMore: { type: Boolean, default: false },
  loadingMore: { type: Boolean, default: false },
  error: { type: String, default: '' },
  total: { type: Number, default: 0 }
})

defineEmits(['retry'])
</script>

<template>
  <div class="footer">
    <button v-if="error" type="button" class="retry" @click="$emit('retry')">
      加载失败，点击重试
    </button>
    <span v-else-if="loadingMore" class="loading">
      <i class="spinner" aria-hidden="true"></i>
      LOADING
    </span>
    <span v-else-if="!hasMore" class="end">END OF EDITION · {{ total }}</span>
    <span v-else class="end">SCROLL FOR MORE</span>
  </div>
</template>

<style scoped>
.footer {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 58px;
  padding: 14px 0 28px;
  color: var(--muted);
  font-family: var(--font-sans);
  font-size: 9.5px;
  font-weight: 500;
  letter-spacing: 0.16em;
}

.loading {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.spinner {
  width: 10px;
  height: 10px;
  border: 1px solid #d4d4d8;
  border-top-color: var(--red);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.retry {
  height: 32px;
  padding: 0 14px;
  border: 1px solid var(--red);
  color: var(--red);
  background: transparent;
  font-size: 11px;
  font-weight: 500;
}
</style>
