# EasyResume

**把一次求职输入，沉淀为可复用的个人求职资产。**

EasyResume 是一款面向求职全流程的 AI 工作台。以**个人画像**为唯一事实源，串联简历生成与版本管理、岗位匹配与定向改写、语音模拟面试与投递跟踪，让每一次准备都可追溯、可复用、可回滚。

[在线体验](https://lzy22301093.github.io/) · [GitHub 仓库](https://github.com/Lzy22301093/EasyResume) · [功能介绍](https://lzy22301093.github.io/#/features)

---

## 在线预览

无需注册，打开即可体验产品界面：

**https://lzy22301093.github.io/**

| 项目 | 说明 |
|------|------|
| 演示账号 | 预置虚构人物「林知远」，免登录直接进入工作台 |
| 界面还原 | 与源码产品一致的路由、模块与交互（个人画像 / 简历生成 / 简历工作台 / 求职分析 / 模拟面试 / 投递记录） |
| 演示数据 | 画像、多版本简历、匹配报告、面试结果、投递记录均为预设 Mock |
| 演示边界 | 不连接真实后端、LLM 与语音服务；不采集访客输入               |
|          |                                                              |

> 完整能力（真实模型、语音面试、Word 导出等）需克隆源码本地运行。预览站导航中的「克隆运行」页提供了启动步骤。

---

## 核心能力

- **个人画像** — 基本信息、教育、实习 / 项目、技能、投递方向与软性信息；条目带证据与确认状态，支持从已有简历导入（逐项确认后写入）
- **简历生成** — 8 步向导：从画像到可导出的专业简历（Word / HTML），支持 AI 表达包装与模板选择
- **简历工作台** — 多版本管理、区域框选改写、对比采纳、一键回滚与回收站
- **岗位匹配** — 贴 JD 生成匹配任务，查看分数与差距维度，导出定向草稿
- **模拟面试** — 选定本场简历 + JD，语音多轮面试，输出评估报告与画像更新提案
- **求职分析** — 对话式协作：JD 分析、差距诊断、岗位定制、面试题与求职信
- **投递跟踪** — 登记公司、岗位与进展，筛选汇总投递状态

---

## 产品原则

1. **画像先于生成** — 简历与面试都基于可追溯的已确认画像
2. **AI 只提议，你拍板** — 改写候选与画像提案不直接覆盖原文，确认后才生效
3. **一次输入，多处复用** — 同一段经历可服务简历、匹配、面试追问与求职分析
4. **版本可回滚** — 简历改动产生新版本，历史版本随时可回退

---

## 端到端闭环

```text
个人画像（证据溯源 · 确认后生效）
    │
    ├─► 简历生成向导 ──► 简历库（多版本 / 区域改写）
    │                        │
    ├─► 求职分析 · 岗位匹配 ──┤
    │                        │
    └─► 模拟面试（JD + 简历）──► 报告 / 画像提案 ──用户确认──┘
```

产品主形态是**个人画像驱动的资产工作台**；求职分析是其中的对话式协作模块，不是全局聊天入口。

---

## 模块一览

| 模块 | 路由 | 说明 |
|------|------|------|
| 个人画像 | `/knowledge-base` | 事实源：条目、证据、投递方向、软性信息；可从简历导入并确认 |
| 简历生成 | `/resume-generation` | 8 步向导，从画像生成可导出简历 |
| 简历工作台 | `/resume-library` | 多版本、区域改写、回滚与回收站 |
| 求职分析 | `/workspace` | 对话协作：JD 分析、差距、岗位定制、面试题、求职信 |
| 模拟面试 | `/mock-interview` | JD + 本场简历驱动的语音面试与报告 |
| 投递记录 | `/applications` | 跟踪投递状态与结果 |
| 功能介绍 | `/features` | 产品能力、闭环与模块说明 |

---

## 快速开始



### Docker 部署（推荐）

```bash
git clone https://github.com/Lzy22301093/EasyResume.git
cd EasyResume

# 配置环境变量
cp .env.example .env
# 编辑 .env，填入 OPENAI_API_KEY、JWT_SECRET_KEY 等

docker compose up -d
docker compose logs -f backend

# 已有数据库时执行一次性迁移（新库表会自动创建）
docker compose exec backend python -m scripts.migrate_profile --apply
docker compose exec backend python -m scripts.migrate_resume_library --apply
```

服务地址：

- 前端：http://localhost:5173
- 后端 API：http://localhost:8000
- API 文档：http://localhost:8000/docs

### 本地开发

```bash
# 后端
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# 前端（另开终端；需 frontend/.env.local 设 VITE_API_TARGET=http://localhost:8000）
cd frontend
npm install
npm run dev
```

### 运行测试

```bash
# 后端（排除需真实 LLM 的集成测试）
cd backend
python -m pytest tests/ -v --ignore=tests/test_tools_integration.py

# 前端类型检查 + 构建
cd frontend
npm run build
```

---

## 技术架构

| 层级 | 技术 |
|------|------|
| 后端 | Python · FastAPI · LangGraph · SQLAlchemy · MySQL · Redis（可选） |
| 前端 | Vue 3 · TypeScript · Element Plus · Pinia · Vite |
| LLM | OpenAI 兼容协议（生成 / 提取双模型分层） |
| 语音 | ASR + TTS · WebSocket（模拟面试、语音对话） |
| 部署 | Docker Compose：backend / frontend / redis / mysql |

前端之下是一套可增量重算的 Agent 工作流：

- **意图分类** — 理解「贴 JD / 补材料 / 改内容 / 出题 / 写求职信」等意图并编排执行链
- **增量重算** — 输入变化时只重跑受影响环节，保留模板等无关状态
- **结构化输出** — LLM 结果经 schema 校验后再落库
- **流式反馈** — SSE 实时推送进度与中间产物
- **跨会话记忆** — 画像条目与证据沉淀，供后续生成与面试复用

---

## 路线图

| 阶段 | 方向 | 说明 |
|------|------|------|
| 近期 | Web 体验持续打磨 | 完善在线预览数据旅程、导出保真度与匹配 / 面试报告可读性 |
| 规划中 | **桌面客户端** | 面向本地文件与多版本简历管理的桌面端，强化离线草稿、系统级导入导出与本地隐私存储 |
| 规划中 | **移动端** | 覆盖投递跟踪、面试练习与进度提醒等高频场景，支持移动端适配的轻量工作台 |

> 路线图表示产品方向，具体排期以仓库迭代为准。



---

## 许可

MIT
