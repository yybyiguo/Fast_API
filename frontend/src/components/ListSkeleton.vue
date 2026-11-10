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
  gap: 14px;
  padding: 18px 16px;
  border: 1px solid var(--hairline);
  border-radius: var(--radius);
  background: var(--canvas-card);
}

.lines {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 10px;
  padding-top: 2px;
}

.line {
  height: 10px;
  border-radius: 3px;
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
  height: 8px;
}

.thumb {
  flex: 0 0 auto;
  width: 92px;
  height: 70px;
  border-radius: 6px;
}

.shimmer {
  background: linear-gradient(100deg, #16171a 20%, #202226 40%, #16171a 60%);
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
