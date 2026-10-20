<template>
  <div class="about-page">
    <AppNav />
    <main class="about-main">
      <header class="about-hero">
        <p class="eyebrow">公开演示 · 项目介绍</p>
        <h1>把一次求职输入，沉淀为可复用的求职资产</h1>
        <p class="lead">
          EasyResume 是一套以<strong>个人画像</strong>为核心的 AI 求职工作台。
          本页是 GitHub Pages 公开预览：界面与真实产品一致，数据为虚构演示人物「林知远」，
          点击生成 / 匹配 / 面试会走预设 Mock 流程，不连接真实 LLM。
        </p>
        <div class="hero-actions">
          <a class="btn btn-primary" :href="repoUrl" target="_blank" rel="noreferrer">
            <Github :size="16" /> 克隆完整项目
          </a>
          <RouterLink class="btn" to="/features">查看功能介绍</RouterLink>
        </div>
      </header>

      <section class="panel">
        <h2>如何克隆运行完整功能</h2>
        <p class="panel-hint">
          完整能力（真实 LLM、语音 ASR/TTS、WebSocket 面试、MySQL/Redis、简历导出）需要本地或服务器运行源码。
        </p>
        <ol class="steps">
          <li>
            <b>克隆仓库</b>
            <pre>git clone {{ repoUrl }}.git
cd EasyResume</pre>
          </li>
          <li>
            <b>配置环境变量</b>
            <pre>cp .env.example .env
# 填入 OPENAI_API_KEY、JWT_SECRET_KEY 等</pre>
          </li>
          <li>
            <b>Docker 启动（推荐）</b>
            <pre>docker compose up -d
docker compose logs -f backend</pre>
          </li>
          <li>
            <b>访问</b>
            <pre>前端 http://localhost:5173
后端 http://localhost:8000/docs</pre>
          </li>
        </ol>
      </section>

      <section class="panel">
        <h2>演示边界</h2>
        <ul class="bounds">
          <li>页面只运行在浏览器本地，不连接 EasyResume 后端、LLM、ASR、TTS 或数据库。</li>
          <li>人物「林知远」及学校、公司、项目、联系方式、岗位与分数均为虚构演示数据。</li>
          <li>不会上传、保存或发送访客输入。</li>
          <li>AI 生成、岗位匹配、面试评价等为预设 Mock；完整能力请克隆仓库运行。</li>
        </ul>
      </section>

      <section class="panel">
        <h2>产品闭环</h2>
        <div class="loop">
          <span>个人画像</span>
          <span class="arrow">→</span>
          <span>简历生成</span>
          <span class="arrow">→</span>
          <span>简历工作台</span>
          <span class="arrow">→</span>
          <span>求职分析 / 匹配</span>
          <span class="arrow">→</span>
          <span>模拟面试</span>
          <span class="arrow">→</span>
          <span>提案确认回写画像</span>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup lang="ts">
import { Github } from 'lucide-vue-next'
import { RouterLink } from 'vue-router'
import AppNav from '../components/AppNav.vue'

const repoUrl = 'https://github.com/Lzy22301093/EasyResume'
</script>

<style scoped>
.about-page {
  min-height: 100vh;
  min-height: 100dvh;
  display: flex;
  flex-direction: column;
  background: var(--color-bg-page);
}

.about-main {
  flex: 1;
  width: 100%;
  max-width: 880px;
  margin: 0 auto;
  padding: var(--space-8) var(--space-5) var(--space-10);
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
}

.eyebrow {
  margin: 0 0 var(--space-2);
  font-size: var(--text-xs);
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--color-accent-600);
}

.about-hero h1 {
  margin: 0 0 var(--space-3);
  font-family: var(--font-display);
  font-size: clamp(1.75rem, 3.5vw, 2.35rem);
  line-height: 1.25;
  color: var(--color-text-primary);
}

.lead {
  margin: 0 0 var(--space-5);
  color: var(--color-text-secondary);
  line-height: 1.75;
  font-size: var(--text-base);
}

.hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3);
}

.btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 0.7rem 1.15rem;
  border-radius: var(--radius-md);
  border: var(--border-medium);
  background: var(--color-white);
  color: var(--color-text-primary);
  font-weight: 600;
  font-size: var(--text-sm);
  text-decoration: none;
}

.btn-primary {
  background: var(--color-accent-600);
  border-color: var(--color-accent-600);
  color: #fff;
}

.btn-primary:hover {
  background: var(--color-accent-700);
}

.panel {
  padding: var(--space-5);
  border-radius: var(--radius-lg);
  background: var(--color-white);
  border: var(--border-light);
}

.panel h2 {
  margin: 0 0 var(--space-2);
  font-family: var(--font-display);
  font-size: var(--text-lg);
  color: var(--color-text-primary);
}

.panel-hint {
  margin: 0 0 var(--space-4);
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
}

.steps {
  margin: 0;
  padding-left: 1.2rem;
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  color: var(--color-text-secondary);
}

.steps b {
  display: block;
  margin-bottom: 6px;
  color: var(--color-text-primary);
}

.steps pre {
  margin: 0;
  padding: 0.85rem 1rem;
  border-radius: var(--radius-md);
  background: var(--color-gray-50);
  border: var(--border-light);
  font-size: 12.5px;
  line-height: 1.6;
  overflow-x: auto;
  color: var(--color-gray-900);
}

.bounds {
  margin: 0;
  padding-left: 1.15rem;
  color: var(--color-text-secondary);
  line-height: 1.75;
  font-size: var(--text-sm);
}

.loop {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  font-size: var(--text-sm);
  color: var(--color-text-primary);
}

.loop span:not(.arrow) {
  padding: 0.45rem 0.75rem;
  border-radius: var(--radius-full);
  background: var(--color-accent-50);
  border: 1px solid var(--color-accent-200);
}

.loop .arrow {
  color: var(--color-accent-600);
  font-weight: 700;
}
</style>
