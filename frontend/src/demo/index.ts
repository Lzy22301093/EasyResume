/**
 * 演示模式安装入口。
 * 在 GitHub Pages / VITE_DEMO_MODE 下启用：免登录进入「林知远」演示账号，
 * API / SSE / WebSocket 全部走本地 Mock，不连接真实后端。
 */
import type { App } from 'vue'
import type { AxiosInstance } from 'axios'
import { demoAdapter, installDemoFetch, installDemoWebSocket } from './mockAdapter'
import { DEMO_TOKEN, DEMO_USER } from './mockDb'

export function isDemoMode(): boolean {
  if (import.meta.env.VITE_DEMO_MODE === '1' || import.meta.env.VITE_DEMO_MODE === 'true') {
    return true
  }
  if (typeof window !== 'undefined') {
    const host = window.location.hostname
    if (host.endsWith('.github.io')) return true
  }
  return false
}

/** 演示模式下保证已以演示身份登录，并预置演示会话 */
export function ensureDemoAuth() {
  localStorage.setItem('token', DEMO_TOKEN)
  localStorage.setItem('user', JSON.stringify(DEMO_USER))
  // 预置求职分析演示会话，进入 /workspace 即可看到完整 Mock 旅程
  localStorage.setItem('current_session_id:1', 'sess-demo-1')
}

/** 给 axios 安装 Mock 适配器 */
export function installDemoAxios(client: AxiosInstance) {
  client.defaults.adapter = demoAdapter
}

export function installDemo(client: AxiosInstance, _app?: App) {
  if (!isDemoMode()) return
  ensureDemoAuth()
  installDemoAxios(client)
  installDemoFetch()
  installDemoWebSocket()
  // 标记演示模式，供导航/页脚展示
  document.documentElement.dataset.demoMode = '1'
}
