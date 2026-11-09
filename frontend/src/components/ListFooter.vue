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
      加载中…
    </span>
    <span v-else-if="!hasMore" class="end">已经到底了 · 共 {{ total }} 条</span>
    <span v-else class="end">上拉加载更多</span>
  </div>
</template>

<style scoped>
.footer {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 52px;
  padding: 10px 0 22px;
  color: #b1b7c0;
  font-size: 12px;
}

.loading {
  display: inline-flex;
  align-items: center;
  gap: 7px;
}

.spinner {
  width: 14px;
  height: 14px;
  border: 2px solid #e3e5e9;
  border-top-color: var(--c-primary);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

.retry {
  padding: 8px 16px;
  border-radius: 999px;
  color: var(--c-primary);
  background: var(--c-primary-soft);
  font-size: 12.5px;
}
</style>
