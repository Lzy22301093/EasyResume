import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'

// 代理目标：Docker 内用服务名 backend，本机开发用 localhost
// 通过环境变量 VITE_API_TARGET 覆盖，默认 Docker 模式
const apiTarget = process.env.VITE_API_TARGET || 'http://backend:8000'

export default defineConfig({
  plugins: [
    vue(),
    // 模板中的 el-* 组件按需注册，避免把整套 Element Plus 打进主包。
    // importStyle: false —— 主题 CSS 已在 main.ts 整包引入；
    // 若保持默认 true，resolver 会按需再注入 theme-chalk/base.css，
    // 把 --el-color-primary 重置回默认蓝，覆盖 element-overrides。
    Components({
      resolvers: [ElementPlusResolver({ importStyle: false })],
      dts: false,
    }),
  ],
  server: {
    port: 5173,
    host: '0.0.0.0',
    proxy: {
      '/api': {
        target: apiTarget,
        changeOrigin: true,
      },
      '/ws': {
        target: apiTarget,
        ws: true,
      },
    },
  },
})
