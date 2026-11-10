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
      RETRY
    </button>
    <span v-else-if="loadingMore" class="loading">
      <i class="spinner" aria-hidden="true"></i>
      LOADING
    </span>
    <span v-else-if="!hasMore" class="end">END OF FEED · {{ total }}</span>
    <span v-else class="end">SCROLL FOR MORE</span>
  </div>
</template>

<style scoped>
.footer {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 56px;
  padding: 12px 0 26px;
  color: #5f646c;
  font-family: var(--font-mono);
  font-size: 9.5px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
}

.loading {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.spinner {
  width: 12px;
  height: 12px;
  border: 1px solid #3a3e44;
  border-top-color: var(--ink);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.retry {
  height: 30px;
  padding: 0 14px;
  border: 1px solid var(--pill-border);
  border-radius: var(--pill);
  color: var(--ink);
  background: transparent;
  font-family: var(--font-mono);
  font-size: 9.5px;
  letter-spacing: 0.14em;
}
</style>
