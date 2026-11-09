<template>
  <div class="skeleton" aria-hidden="true">
    <div v-for="n in count" :key="n" class="row">
      <div class="lines">
        <div class="line title shimmer"></div>
        <div class="line desc shimmer"></div>
        <div class="line meta shimmer"></div>
      </div>
      <div class="thumb shimmer"></div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  count: { type: Number, default: 3 }
})
</script>

<style scoped>
.skeleton {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px;
}

.row {
  display: flex;
  gap: 12px;
  padding: 14px;
  border-radius: var(--radius-lg);
  background: #fff;
}

.lines {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 9px;
  padding-top: 2px;
}

.line {
  height: 11px;
  border-radius: 6px;
}

.title {
  width: 88%;
  height: 15px;
}

.desc {
  width: 68%;
}

.meta {
  width: 42%;
  height: 9px;
}

.thumb {
  flex: 0 0 auto;
  width: 104px;
  height: 78px;
  border-radius: 10px;
}

.shimmer {
  background: linear-gradient(100deg, #eef0f3 20%, #f7f8fa 40%, #eef0f3 60%);
  background-size: 220% 100%;
  animation: shimmer 1.3s linear infinite;
}

@keyframes shimmer {
  from {
    background-position: 140% 0;
  }
  to {
    background-position: -40% 0;
  }
}
</style>
