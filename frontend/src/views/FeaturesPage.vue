<template>
  <div class="features-page">
    <AppNav />

    <main class="features-main">
      <header class="feat-hero">
        <p class="eyebrow">产品能力</p>
        <h1 class="feat-title">功能介绍</h1>
        <p class="feat-lead">
          EasyResume 以<strong>个人画像</strong>为唯一事实源，把简历、匹配、面试、投递串成可复用的求职资产闭环。
          AI 只提议，你拍板；版本可回滚，证据可溯源。
        </p>
        <div class="hero-actions">
          <RouterLink to="/knowledge-base" class="btn btn-primary">从个人画像开始</RouterLink>
          <RouterLink to="/resume-generation" class="btn">试一试简历生成</RouterLink>
        </div>
      </header>

      <section class="principles" aria-label="产品原则">
        <article v-for="p in principles" :key="p.title" class="principle-card">
          <h2>{{ p.title }}</h2>
          <p>{{ p.desc }}</p>
        </article>
      </section>

      <section class="loop-section" aria-label="产品闭环">
        <div class="section-head">
          <h2>端到端闭环</h2>
          <p>一次输入，多处复用。画像确认后，下游模块自动受益。</p>
        </div>
        <div class="loop-flow" role="img" aria-label="个人画像驱动的简历、匹配、面试闭环">
          <div class="loop-node loop-root">
            <span class="loop-label">个人画像</span>
            <span class="loop-hint">事实源 · 证据 · 确认态</span>
          </div>
          <div class="loop-branch">
            <div class="loop-arrow" aria-hidden="true">→</div>
            <div class="loop-node">
              <span class="loop-label">简历生成向导</span>
              <span class="loop-hint">8 步出一版简历</span>
            </div>
            <div class="loop-node">
              <span class="loop-label">简历库</span>
              <span class="loop-hint">多版本 · 区域改写 · 回滚</span>
            </div>
          </div>
          <div class="loop-branch">
            <div class="loop-arrow" aria-hidden="true">→</div>
            <div class="loop-node">
              <span class="loop-label">求职分析 · 岗位匹配</span>
              <span class="loop-hint">贴 JD · 差距 · 定向草稿</span>
            </div>
          </div>
          <div class="loop-branch">
            <div class="loop-arrow" aria-hidden="true">→</div>
            <div class="loop-node">
              <span class="loop-label">模拟面试</span>
              <span class="loop-hint">JD + 本场简历 · 语音多轮</span>
            </div>
            <div class="loop-back">报告 / 画像提案 → 用户确认后回写画像</div>
          </div>
        </div>
      </section>

      <section class="modules-section" aria-label="模块详解">
        <div class="section-head">
          <h2>六大工作区</h2>
          <p>每个模块都直接可进入操作，共用同一份已确认画像。</p>
        </div>

        <div class="module-list">
          <article
            v-for="(m, i) in modules"
            :key="m.route"
            class="module-card"
            :style="{ '--accent': m.accent }"
          >
            <div class="module-index">{{ String(i + 1).padStart(2, '0') }}</div>
            <div class="module-body">
              <div class="module-head">
                <span class="module-icon">
                  <component :is="m.icon" :size="20" />
                </span>
                <div>
                  <h3>{{ m.label }}</h3>
                  <p class="module-route">{{ m.route }}</p>
                </div>
              </div>
              <p class="module-desc">{{ m.desc }}</p>
              <ul class="module-points">
                <li v-for="pt in m.points" :key="pt">{{ pt }}</li>
              </ul>
              <RouterLink :to="m.route" class="module-cta">进入模块 →</RouterLink>
            </div>
          </article>
        </div>
      </section>

      <section class="engine-section" aria-label="引擎能力">
        <div class="section-head">
          <h2>引擎能力</h2>
          <p>前端之下是一套可增量重算的 Agent 工作流。</p>
        </div>
        <div class="engine-grid">
          <article v-for="e in engine" :key="e.title" class="engine-card">
            <h3>{{ e.title }}</h3>
            <p>{{ e.desc }}</p>
          </article>
        </div>
      </section>

      <section class="cta-section">
        <div class="cta-card">
          <div>
            <h2>准备好开始了吗？</h2>
            <p>先完善个人画像，再生成简历、对岗分析与模拟面试。需要完整部署与本地运行，请克隆 GitHub 仓库。</p>
          </div>
          <div class="cta-actions">
            <RouterLink to="/" class="btn btn-primary">回到工作台</RouterLink>
            <a
              class="btn"
              href="https://github.com/Lzy22301093/EasyResume"
              target="_blank"
              rel="noreferrer"
            >查看 GitHub 仓库</a>
          </div>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup lang="ts">
import {
  User,
  Sparkles,
  FileText,
  Code2,
  MessagesSquare,
  Megaphone,
} from 'lucide-vue-next'
import { RouterLink } from 'vue-router'
import AppNav from '../components/AppNav.vue'

const principles = [
  {
    title: '画像先于生成',
    desc: '简历与面试都基于可追溯的已确认画像，而不是每次重新粘贴文本。',
  },
  {
    title: 'AI 只提议，你拍板',
    desc: '改写候选、画像提案不直接覆盖原文；确认后才写入，拒绝则原样保留。',
  },
  {
    title: '一次输入，多处复用',
    desc: '同一段经历可服务简历生成、岗位匹配、面试追问与求职分析。',
  },
  {
    title: '版本可回滚',
    desc: '简历改动产生新版本，旧版永远可回去；证据链保留来源与确认状态。',
  },
]

const modules = [
  {
    label: '个人画像',
    route: '/knowledge-base',
    accent: '#c15f3c',
    icon: User,
    desc: '求职资产的事实源。维护教育、实习/项目、技能、投递方向与软性信息，条目带证据与确认状态。',
    points: [
      '分类管理：基本信息 / 教育 / 经历 / 技能 / 方向 / 软性信息',
      '从已有简历导入，导入前逐项确认后写入',
      '面试反馈经提案闭环安全回写画像',
    ],
  },
  {
    label: '简历生成',
    route: '/resume-generation',
    accent: '#c15f3c',
    icon: Sparkles,
    desc: '8 步向导：从画像结构化填表，到 AI 表达包装、模板选择与 Word/HTML 导出。',
    points: [
      '向导一键填充画像与简历识别草稿',
      '经历 AI 结构化与表达包装，可逐条采纳',
      '模板、篇幅偏好与照片，生成完整专业简历',
    ],
  },
  {
    label: '简历工作台',
    route: '/resume-library',
    accent: '#b57b1f',
    icon: FileText,
    desc: '管理已有简历版本。区域改写、对比采纳、多版本回滚与回收站。',
    points: [
      '多文档多版本，改动可回滚',
      '选中区域发起 AI 改写，逐条采纳候选',
      '导出保排版或统一模板',
    ],
  },
  {
    label: '求职分析',
    route: '/workspace',
    accent: '#4c7f7d',
    icon: Code2,
    desc: '对话式协作：贴 JD 分析、差距诊断、岗位定制、面试题与求职信，结果沉淀到右侧面板。',
    points: [
      'JD 分析 / 个人画像 / Gap 分析 / 岗位定制',
      '面试准备与调试面板',
      '一次录入 JD 与简历，全流程复用',
    ],
  },
  {
    label: 'AI 模拟面试',
    route: '/mock-interview',
    accent: '#5b6b9e',
    icon: MessagesSquare,
    desc: '按公司/岗位与 JD 进行语音多轮面试，结束后生成反馈报告与画像更新提案。',
    points: [
      '本场简历 + JD 驱动结构化面试计划',
      '语音问答、追问与实时评价',
      '报告沉淀证据，提案确认后回写画像',
    ],
  },
  {
    label: '投递记录',
    route: '/applications',
    accent: '#6f8f5f',
    icon: Megaphone,
    desc: '手动登记与跟踪每次投递：公司、岗位、状态、结果与备注，支持筛选与汇总。',
    points: [
      '状态流转：投递 / 笔试 / 面试 / Offer / 未通过',
      '搜索筛选与进行中/通过/未通过汇总',
      '与简历、面试记录形成完整求职轨迹',
    ],
  },
]

const engine = [
  {
    title: '意图分类',
    desc: '理解「贴 JD / 补材料 / 改内容 / 出题 / 写求职信」等意图，编排执行链。',
  },
  {
    title: '增量重算',
    desc: '输入变化时只重跑受影响环节，保留模板等无关状态。',
  },
  {
    title: '结构化输出',
    desc: 'LLM 结果经 schema 校验后再落库，避免裸 JSON 直接入库。',
  },
  {
    title: '流式反馈',
    desc: 'SSE 实时推送进度与中间产物，会话内消息串行可靠处理。',
  },
  {
    title: '跨会话记忆',
    desc: '画像条目与证据沉淀，供后续生成、匹配与面试复用。',
  },
  {
    title: '可控写回',
    desc: '画像变更走提案 → 用户确认闭环，保证用户拥有最终写入权。',
  },
]
</script>

<style scoped>
.features-page {
  min-height: 100vh;
  min-height: 100dvh;
  display: flex;
  flex-direction: column;
  background: var(--color-bg-page);
}

.features-main {
  flex: 1;
  width: 100%;
  max-width: 1120px;
  margin: 0 auto;
  padding: var(--space-8) var(--space-8) var(--space-10);
  display: flex;
  flex-direction: column;
  gap: var(--space-10);
}

.eyebrow {
  margin: 0 0 var(--space-2);
  font-size: var(--text-xs);
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--color-accent-600);
}

.feat-hero {
  padding: var(--space-6) 0 var(--space-2);
}

.feat-title {
  margin: 0 0 var(--space-3);
  font-family: var(--font-display);
  font-size: clamp(2rem, 4vw, 2.75rem);
  line-height: 1.15;
  color: var(--color-text-primary);
}

.feat-lead {
  margin: 0 0 var(--space-5);
  max-width: 42rem;
  font-size: var(--text-lg);
  line-height: 1.7;
  color: var(--color-text-secondary);
}

.hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3);
}

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  padding: 0.7rem 1.15rem;
  border-radius: var(--radius-md);
  border: var(--border-medium);
  background: var(--color-white);
  color: var(--color-text-primary);
  font-size: var(--text-sm);
  font-weight: 600;
  text-decoration: none;
  transition: background 0.15s ease, border-color 0.15s ease, color 0.15s ease;
}

.btn:hover {
  background: var(--color-bg-hover);
  border-color: var(--color-border-strong);
}

.btn-primary {
  background: var(--color-accent-600);
  border-color: var(--color-accent-600);
  color: #fff;
}

.btn-primary:hover {
  background: var(--color-accent-700);
  border-color: var(--color-accent-700);
}

.principles {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-4);
}

.principle-card {
  padding: var(--space-5);
  border-radius: var(--radius-lg);
  background: var(--color-white);
  border: var(--border-light);
}

.principle-card h2 {
  margin: 0 0 var(--space-2);
  font-size: var(--text-base);
  font-weight: 700;
  color: var(--color-text-primary);
}

.principle-card p {
  margin: 0;
  font-size: var(--text-sm);
  line-height: 1.65;
  color: var(--color-text-secondary);
}

.section-head {
  margin-bottom: var(--space-5);
}

.section-head h2 {
  margin: 0 0 var(--space-2);
  font-family: var(--font-display);
  font-size: var(--text-xl);
  color: var(--color-text-primary);
}

.section-head p {
  margin: 0;
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
}

.loop-flow {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding: var(--space-5);
  border-radius: var(--radius-lg);
  background: var(--color-white);
  border: var(--border-light);
}

.loop-branch {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-3);
  padding-left: var(--space-4);
}

.loop-node {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 0.75rem 1rem;
  border-radius: var(--radius-md);
  background: var(--color-accent-50);
  border: 1px solid var(--color-accent-200);
  min-width: 10rem;
}

.loop-root {
  align-self: flex-start;
  background: var(--color-accent-600);
  border-color: var(--color-accent-600);
}

.loop-root .loop-label,
.loop-root .loop-hint {
  color: #fff;
}

.loop-label {
  font-weight: 700;
  font-size: var(--text-sm);
  color: var(--color-text-primary);
}

.loop-hint {
  font-size: var(--text-xs);
  color: var(--color-text-secondary);
}

.loop-arrow {
  color: var(--color-accent-600);
  font-weight: 700;
}

.loop-back {
  font-size: var(--text-xs);
  color: var(--color-accent-700);
  background: var(--color-accent-50);
  border: 1px dashed var(--color-accent-200);
  border-radius: var(--radius-md);
  padding: 0.45rem 0.75rem;
}

.module-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.module-card {
  display: grid;
  grid-template-columns: 4.5rem 1fr;
  gap: var(--space-4);
  padding: var(--space-5);
  border-radius: var(--radius-lg);
  background: var(--color-white);
  border: var(--border-light);
  border-left: 4px solid var(--accent, var(--color-accent-600));
}

.module-index {
  font-family: var(--font-display);
  font-size: 1.75rem;
  font-weight: 700;
  color: var(--accent, var(--color-accent-600));
  line-height: 1;
  padding-top: 0.15rem;
}

.module-head {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-2);
}

.module-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2.25rem;
  height: 2.25rem;
  border-radius: var(--radius-md);
  background: color-mix(in srgb, var(--accent, var(--color-accent-600)) 12%, white);
  color: var(--accent, var(--color-accent-600));
}

.module-head h3 {
  margin: 0;
  font-size: var(--text-lg);
  color: var(--color-text-primary);
}

.module-route {
  margin: 0;
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  font-family: var(--font-mono, ui-monospace, monospace);
}

.module-desc {
  margin: 0 0 var(--space-3);
  color: var(--color-text-secondary);
  line-height: 1.65;
  font-size: var(--text-sm);
}

.module-points {
  margin: 0 0 var(--space-3);
  padding-left: 1.15rem;
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
  line-height: 1.7;
}

.module-cta {
  display: inline-flex;
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--color-accent-600);
  text-decoration: none;
}

.module-cta:hover {
  color: var(--color-accent-700);
  text-decoration: underline;
}

.engine-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-4);
}

.engine-card {
  padding: var(--space-5);
  border-radius: var(--radius-lg);
  background: var(--color-white);
  border: var(--border-light);
}

.engine-card h3 {
  margin: 0 0 var(--space-2);
  font-size: var(--text-base);
  color: var(--color-text-primary);
}

.engine-card p {
  margin: 0;
  font-size: var(--text-sm);
  line-height: 1.65;
  color: var(--color-text-secondary);
}

.cta-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-5);
  padding: var(--space-6);
  border-radius: var(--radius-lg);
  background: linear-gradient(135deg, var(--color-accent-50), var(--color-white));
  border: 1px solid var(--color-accent-200);
}

.cta-card h2 {
  margin: 0 0 var(--space-2);
  font-family: var(--font-display);
  font-size: var(--text-xl);
  color: var(--color-text-primary);
}

.cta-card p {
  margin: 0;
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
  line-height: 1.65;
  max-width: 36rem;
}

.cta-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3);
  flex-shrink: 0;
}

@media (max-width: 960px) {
  .principles {
    grid-template-columns: repeat(2, 1fr);
  }

  .engine-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .cta-card {
    flex-direction: column;
    align-items: flex-start;
  }
}

@media (max-width: 640px) {
  .features-main {
    padding: var(--space-5) var(--space-4) var(--space-8);
    gap: var(--space-8);
  }

  .principles,
  .engine-grid {
    grid-template-columns: 1fr;
  }

  .module-card {
    grid-template-columns: 1fr;
  }

  .module-index {
    font-size: 1.25rem;
  }
}
</style>
