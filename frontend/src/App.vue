<script setup>
import { computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import SideNav from './components/SideNav.vue'
import TabBar from './components/TabBar.vue'
import ToastHost from './components/ToastHost.vue'
import { useAuth } from './stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuth()

const showSideNav = computed(() => route.name !== 'login')

watch(
  () => auth.isLoggedIn.value,
  (loggedIn) => {
    if (!loggedIn && route.name !== 'login') {
      router.replace({
        name: 'login',
        query: route.fullPath && route.fullPath !== '/' ? { redirect: route.fullPath } : {}
      })
    }
  }
)

onMounted(() => {
  // 用本地 token 校验一次登录态，失败会自动清掉
  auth.ensureReady()
})
</script>

<template>
  <div class="app">
    <SideNav v-if="showSideNav" />

    <div class="shell">
      <div class="view">
        <router-view v-slot="{ Component }">
          <component :is="Component" />
        </router-view>
      </div>

      <TabBar v-if="route.meta.tab" class="mobile-tab" />
    </div>

    <ToastHost />
  </div>
</template>

<style scoped>
.shell {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
}

@media (min-width: 960px) {
  .mobile-tab {
    display: none;
  }
}
</style>
