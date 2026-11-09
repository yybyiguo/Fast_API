<script setup>
import { onMounted } from 'vue'
import { useRoute } from 'vue-router'
import TabBar from './components/TabBar.vue'
import ToastHost from './components/ToastHost.vue'
import { useAuth } from './stores/auth'

const route = useRoute()
const auth = useAuth()

onMounted(() => {
  // 用本地 token 校验一次登录态，失败会自动清掉
  auth.ensureReady()
})
</script>

<template>
  <div class="app">
    <div class="view">
      <router-view v-slot="{ Component }">
        <component :is="Component" />
      </router-view>
    </div>

    <TabBar v-if="route.meta.tab" />
    <ToastHost />
  </div>
</template>
