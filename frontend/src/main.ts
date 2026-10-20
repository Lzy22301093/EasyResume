import './styles/reset.css'
import './styles/tokens.css'
import 'element-plus/dist/index.css'
import './styles/element-overrides.css'

import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'
import client from './api/client'
import { installDemo } from './demo'

const app = createApp(App)

app.use(createPinia())
app.use(router)

// 演示模式（GitHub Pages / VITE_DEMO_MODE）：Mock API + 免登录演示账号
installDemo(client)

app.mount('#app')
