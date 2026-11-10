<template>
  <div class="skeleton" aria-hidden="true">
    <div v-for="n in count" :key="n" class="card">
      <div class="cover shimmer"></div>
      <div class="line title shimmer"></div>
      <div class="line desc shimmer"></div>
      <div class="line meta shimmer"></div>
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
  gap: 14px;
  padding: 12px 14px;
  background: var(--paper);
}

.card {
  padding: 7px;
  border: 1px solid var(--line);
  border-radius: 22px;
  background: var(--surface);
}

.cover {
  height: 172px;
  border-radius: 17px;
  background: #1c1c26;
}

.line {
  height: 11px;
  margin: 12px 7px 0;
  border-radius: 6px;
  background: #1c1c26;
}

.title {
  width: 74%;
  height: 17px;
}

.desc {
  width: 52%;
}

.meta {
  width: 34%;
  height: 9px;
  margin-bottom: 8px;
}

.shimmer {
  position: relative;
  overflow: hidden;
}

.shimmer::after {
  position: absolute;
  inset: 0;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.07), transparent);
  content: '';
  transform: translateX(-100%);
  animation: sweep 1.5s infinite;
}

@keyframes sweep {
  to {
    transform: translateX(100%);
  }
}
</style>
