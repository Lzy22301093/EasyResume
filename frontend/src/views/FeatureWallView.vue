<template>
  <div class="wall-page">
    <AppNav />

    <main class="wall-main">
      <header class="home-hero">
        <div class="hero-copy">
          <p class="eyebrow">EasyResume</p>
          <h1 class="home-title">Home</h1>
          <p class="home-subtitle">
            AI 求职助手：建立个人画像、生成与打磨简历、对岗分析与模拟面试，并登记每次投递进展。
          </p>
          <div class="hero-actions">
            <RouterLink to="/resume-generation" class="hero-btn hero-btn-primary">开始生成简历</RouterLink>
            <RouterLink to="/knowledge-base" class="hero-btn">完善个人画像</RouterLink>
            <RouterLink to="/features" class="hero-btn hero-btn-ghost">功能介绍</RouterLink>
          </div>
        </div>
        <div class="hero-aside" aria-hidden="true">
          <div class="hero-card">
            <div class="hero-card-label">产品主线</div>
            <ol class="hero-line">
              <li v-for="(s, i) in journey" :key="s.route">
                <span class="step-no">{{ i + 1 }}</span>
                <span class="step-text">
                  <b>{{ s.label }}</b>
                  <small>{{ s.hint }}</small>
                </span>
              </li>
            </ol>
          </div>
        </div>
      </header>

      <nav class="journey-strip" aria-label="产品主线">
        <template v-for="(s, i) in journey" :key="s.route">
          <RouterLink :to="s.route" class="journey-item">
            <span class="journey-num">{{ String(i + 1).padStart(2, '0') }}</span>
            <span>{{ s.label }}</span>
          </RouterLink>
          <span v-if="i < journey.length - 1" class="journey-arrow" aria-hidden="true">→</span>
        </template>
      </nav>

      <section class="module-section">
        <div class="section-head">
          <h2>工作区</h2>
          <p>
            按当前要做的事进入对应模块，各模块共用同一份个人画像。
            <RouterLink to="/features" class="inline-link">查看完整功能介绍 →</RouterLink>
          </p>
        </div>

        <div class="wall-grid">
          <component
            :is="RouterLink"
            v-for="(card, i) in cards"
            :key="card.label"
            :to="card.route"
            class="wall-card"
            :style="{ '--accent': card.accent, '--delay': `${i * 60}ms` }"
          >
            <span class="card-accent" aria-hidden="true"></span>
            <div class="card-content">
              <div class="card-icon">
                <component :is="card.icon" :size="20" />
              </div>
              <div class="card-text">
                <div class="card-label">{{ card.label }}</div>
                <div class="card-desc">{{ card.desc }}</div>
                <div class="card-cta">进入 →</div>
              </div>
            </div>
          </component>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup lang="ts">
import {
  User,
  FileText,
  MessagesSquare,
  Megaphone,
  Code2,
  Sparkles,
} from 'lucide-vue-next'
import { RouterLink } from 'vue-router'
import AppNav from '../components/AppNav.vue'

type Card = {
  label: string
  desc: string
  icon: any
  route: string
  accent: string
}

const journey = [
  { label: '个人画像', route: '/knowledge-base', hint: '事实 · 教育 · 技能 · 投递方向' },
  { label: '简历生成', route: '/resume-generation', hint: '8 步向导，从画像到成品' },
  { label: '简历工作台', route: '/resume-library', hint: '改写 · 多版本 · 导出' },
  { label: '求职分析', route: '/workspace', hint: '贴 JD · 对话式差距分析' },
  { label: '模拟面试', route: '/mock-interview', hint: '语音演练 · 反馈报告' },
  { label: '投递记录', route: '/applications', hint: '登记投递 · 跟进状态' },
]

const cards: Card[] = [
  {
    label: '个人画像',
    desc: '基本信息、教育、技能、实习/项目、投递方向与软性信息，生成与面试共用',
    icon: User,
    route: '/knowledge-base',
    accent: '#c15f3c',
  },
  {
    label: '简历生成',
    desc: '8 步向导：填表与 AI 填充经历，生成结构化简历并导出 Word/HTML',
    icon: Sparkles,
    route: '/resume-generation',
    accent: '#c15f3c',
  },
  {
    label: '简历工作台',
    desc: '上传/管理简历，区域 AI 改写，多版本回滚，导出保排版或统一模板',
    icon: FileText,
    route: '/resume-library',
    accent: '#b57b1f',
  },
  {
    label: '求职分析',
    desc: '贴 JD 与简历，对话式分析差距与匹配度，沉淀到结果面板',
    icon: Code2,
    route: '/workspace',
    accent: '#4c7f7d',
  },
  {
    label: 'AI 模拟面试',
    desc: '按公司/岗位与 JD 进行语音多轮面试，结束后生成反馈报告',
    icon: MessagesSquare,
    route: '/mock-interview',
    accent: '#5b6b9e',
  },
  {
    label: '投递记录',
    desc: '登记公司、岗位与状态，搜索筛选并汇总进行中/通过/未通过',
    icon: Megaphone,
    route: '/applications',
    accent: '#6f8f5f',
  },
]
</script>

<style scoped>
.wall-page {
  min-height: 100vh;
  min-height: 100dvh;
  display: flex;
  flex-direction: column;
  background: var(--color-bg-page);
}

.wall-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: var(--space-8) var(--space-8) var(--space-10);
  width: 100%;
  max-width: 1120px;
  margin: 0 auto;
}

/* ---- Hero ---- */
.home-hero {
  display: grid;
  grid-template-columns: 1.2fr 0.8fr;
  gap: var(--space-8);
  align-items: stretch;
  margin-bottom: var(--space-6);
}

.hero-copy {
  padding: var(--space-8) var(--space-2);
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.eyebrow {
  margin: 0 0 var(--space-2);
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--color-accent-600);
}

.home-title {
  margin: 0;
  font-family: var(--font-display);
  font-size: clamp(36px, 5vw, 48px);
  font-weight: var(--weight-semibold);
  color: var(--color-text-primary);
  letter-spacing: -0.03em;
  line-height: 1.1;
}

.home-subtitle {
  margin: var(--space-4) 0 0;
  max-width: 42ch;
  color: var(--color-text-secondary);
  font-size: var(--text-md);
  line-height: 1.7;
}

.hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3);
  margin-top: var(--space-6);
}

.hero-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 44px;
  padding: 0 20px;
  border-radius: var(--radius-md);
  border: var(--border-light);
  background: var(--color-bg-elevated);
  color: var(--color-text-primary);
  font-size: var(--text-sm);
  font-weight: var(--weight-medium);
  text-decoration: none;
  transition:
    background var(--duration-fast) var(--ease-default),
    border-color var(--duration-fast) var(--ease-default),
    color var(--duration-fast) var(--ease-default);
}

.hero-btn:hover {
  border-color: var(--color-accent-400);
  color: var(--color-accent-700);
}

.hero-btn-primary {
  background: var(--color-accent-600);
  border-color: var(--color-accent-600);
  color: #fff;
}

.hero-btn-ghost {
  background: transparent;
  border-color: var(--color-gray-300);
  color: var(--color-text-secondary);
}

.hero-btn-ghost:hover {
  color: var(--color-accent-700);
  border-color: var(--color-accent-400);
  background: var(--color-accent-50);
}

.hero-btn-primary:hover {
  background: var(--color-accent-700);
  border-color: var(--color-accent-700);
  color: #fff;
}

.hero-aside {
  min-width: 0;
}

.hero-card {
  height: 100%;
  background: var(--color-bg-elevated);
  border: var(--border-light);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-card);
  padding: var(--space-5) var(--space-6);
}

.hero-card-label {
  font-size: var(--text-xs);
  font-weight: var(--weight-semibold);
  letter-spacing: 0.08em;
  color: var(--color-text-tertiary);
  margin-bottom: var(--space-4);
}

.hero-line {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.hero-line li {
  display: flex;
  gap: var(--space-3);
  align-items: flex-start;
}

.step-no {
  flex-shrink: 0;
  width: 24px;
  height: 24px;
  border-radius: var(--radius-full);
  background: var(--color-accent-600);
  color: #fff;
  font-size: var(--text-xs);
  font-weight: var(--weight-semibold);
  display: grid;
  place-items: center;
  margin-top: 2px;
}

.step-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.step-text b {
  font-weight: var(--weight-semibold);
  color: var(--color-text-primary);
  font-size: var(--text-sm);
}

.step-text small {
  color: var(--color-text-secondary);
  font-size: var(--text-xs);
}

/* ---- Journey strip ---- */
.journey-strip {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2) var(--space-3);
  padding: var(--space-3) var(--space-4);
  margin-bottom: var(--space-8);
  background: color-mix(in srgb, var(--color-accent-50) 80%, white);
  border: 1px solid var(--color-accent-200);
  border-radius: var(--radius-full);
}

.journey-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: var(--radius-full);
  text-decoration: none;
  color: var(--color-text-primary);
  font-size: var(--text-sm);
  font-weight: var(--weight-medium);
  transition: background var(--duration-fast) var(--ease-default), color var(--duration-fast) var(--ease-default);
}

.journey-item:hover {
  background: var(--color-accent-100);
  color: var(--color-accent-700);
}

.journey-num {
  font-family: var(--font-display);
  font-size: var(--text-xs);
  color: var(--color-accent-600);
}

.journey-arrow {
  color: var(--color-accent-400);
  font-size: var(--text-sm);
}

/* ---- Modules ---- */
.module-section {
  flex: 1;
}

.section-head {
  margin-bottom: var(--space-5);
}

.section-head h2 {
  margin: 0;
  font-family: var(--font-display);
  font-size: var(--text-xl);
  font-weight: var(--weight-semibold);
  color: var(--color-text-primary);
}

.section-head p {
  margin: var(--space-2) 0 0;
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
}

.inline-link {
  margin-left: 0.35rem;
  color: var(--color-accent-600);
  font-weight: 600;
  text-decoration: none;
}

.inline-link:hover {
  color: var(--color-accent-700);
  text-decoration: underline;
}

.wall-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-4);
  width: 100%;
}

.wall-card {
  position: relative;
  display: block;
  overflow: hidden;
  height: 100%;
  box-sizing: border-box;
  background: var(--color-bg-elevated);
  border: var(--border-light);
  border-radius: var(--radius-lg);
  padding: var(--space-5) var(--space-5) var(--space-5) var(--space-6);
  text-decoration: none;
  box-shadow: var(--shadow-card);
  opacity: 0;
  animation: rise 0.45s ease forwards;
  animation-delay: var(--delay, 0ms);
  transition:
    transform var(--duration-normal) var(--ease-out),
    box-shadow var(--duration-normal) var(--ease-out),
    border-color var(--duration-normal) var(--ease-out);
}

.wall-card:hover {
  transform: translateY(-3px);
  border-color: color-mix(in srgb, var(--accent) 40%, transparent);
  box-shadow: var(--shadow-md);
}

.card-accent {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  background: var(--accent);
}

.card-content {
  display: flex;
  gap: var(--space-4);
  align-items: flex-start;
}

.card-icon {
  flex-shrink: 0;
  display: grid;
  place-items: center;
  width: 42px;
  height: 42px;
  border-radius: var(--radius-md);
  background: color-mix(in srgb, var(--accent) 14%, white);
  color: var(--accent);
}

.card-text {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.card-label {
  font-family: var(--font-display);
  font-size: var(--text-md);
  font-weight: var(--weight-semibold);
  color: var(--color-text-primary);
  letter-spacing: -0.01em;
}

.card-desc {
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  line-height: var(--leading-relaxed);
}

.card-cta {
  margin-top: 6px;
  font-size: var(--text-sm);
  font-weight: var(--weight-medium);
  color: var(--accent);
}

@keyframes rise {
  from { opacity: 0; transform: translateY(14px); }
  to   { opacity: 1; transform: translateY(0); }
}

@media (max-width: 900px) {
  .home-hero {
    grid-template-columns: 1fr;
  }
  .wall-grid {
    grid-template-columns: 1fr 1fr;
  }
}

@media (max-width: 600px) {
  .wall-main {
    padding: var(--space-5) var(--space-4) var(--space-8);
  }
  .wall-grid {
    grid-template-columns: 1fr;
  }
}

@media (prefers-reduced-motion: reduce) {
  .wall-card {
    opacity: 1;
    animation: none;
  }
}
</style>
