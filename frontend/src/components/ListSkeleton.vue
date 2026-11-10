<template>
  <div class="skeleton" aria-hidden="true">
    <div v-for="n in count" :key="n" class="row">
      <div class="index shimmer"></div>
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
  padding: 0 16px;
  background: var(--white);
}

.row {
  display: flex;
  gap: 12px;
  padding: 18px 0;
  border-bottom: 1px solid var(--line);
}

.index {
  flex: 0 0 24px;
  height: 10px;
  margin-top: 5px;
}

.lines {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 10px;
}

.line {
  height: 10px;
}

.title {
  width: 86%;
  height: 16px;
}

.desc {
  width: 68%;
}

.meta {
  width: 40%;
  height: 8px;
}

.thumb {
  flex: 0 0 auto;
  width: 92px;
  height: 72px;
}

.shimmer {
  background: linear-gradient(100deg, #f1f1f3 20%, #fafafa 40%, #f1f1f3 60%);
  background-size: 220% 100%;
  animation: shimmer 1.4s linear infinite;
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
