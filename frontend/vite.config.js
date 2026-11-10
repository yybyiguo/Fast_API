import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'

// 前端默认走 /api 代理，浏览器只和 Vite 开发服务器同源通信，
// 因此不受后端 CORS 白名单（仅放行 5500 端口）限制。
// 注意：后端路由本身就以 /api 开头，所以代理不能重写前缀。
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const target = env.VITE_PROXY_TARGET || 'http://127.0.0.1:8000'

  return {
    plugins: [vue()],
    server: {
      host: '0.0.0.0',
      port: 5500,
      strictPort: true,
      proxy: {
        '/api': { target, changeOrigin: true }
      }
    },
    preview: {
      host: '0.0.0.0',
      port: 5500,
      proxy: {
        '/api': { target, changeOrigin: true }
      }
    },
    build: {
      outDir: 'dist',
      assetsDir: 'assets'
    }
  }
})
