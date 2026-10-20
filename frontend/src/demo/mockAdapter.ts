/**
 * Axios 适配器：把 /api/** 请求路由到本地 Mock。
 * 仅在演示模式安装，不影响真实后端联调。
 */
import type { AxiosAdapter, AxiosRequestConfig, AxiosResponse, InternalAxiosRequestConfig } from 'axios'
import {
  DEMO_APPLICATIONS,
  DEMO_DIRECTIONS,
  DEMO_INTERVIEW_REPORT,
  DEMO_JD_ANALYSIS,
  DEMO_MATCH_TASKS,
  DEMO_POSTINGS,
  DEMO_PROFILE_ITEMS,
  DEMO_PROPOSALS,
  DEMO_RESUME_DOCS,
  DEMO_RESUME_SOURCE,
  DEMO_SESSIONS,
  DEMO_USER,
  DEMO_TOKEN,
  DEMO_PREFERENCES,
  demoSessionDetail,
} from './mockDb'

const encoder = new TextEncoder()

function sleep(ms: number) {
  return new Promise((r) => setTimeout(r, ms))
}

function ok<T>(config: InternalAxiosRequestConfig | AxiosRequestConfig, data: T, status = 200): AxiosResponse<T> {
  return {
    data,
    status,
    statusText: 'OK',
    headers: {},
    config: config as InternalAxiosRequestConfig,
  }
}

function pathOf(config: AxiosRequestConfig): string {
  const url = config.url || ''
  return url.replace(/^\/api/, '').split('?')[0] || '/'
}

function methodOf(config: AxiosRequestConfig): string {
  return (config.method || 'get').toLowerCase()
}

function bodyOf(config: AxiosRequestConfig): any {
  const d = config.data
  if (typeof d === 'string') {
    try {
      return JSON.parse(d)
    } catch {
      return d
    }
  }
  return d
}

/** AI 类请求的预设延迟，模拟真实耗时 */
const AI_DELAY = 700
const FAST_DELAY = 120

export const demoAdapter: AxiosAdapter = async (config) => {
  const path = pathOf(config)
  const method = methodOf(config)
  const body = bodyOf(config)

  // 认证 / 用户
  if (path === '/auth/login' && method === 'post') {
    await sleep(FAST_DELAY)
    return ok(config, {
      access_token: DEMO_TOKEN,
      token_type: 'bearer',
      user: DEMO_USER,
    })
  }
  if (path === '/auth/register' && method === 'post') {
    await sleep(FAST_DELAY)
    return ok(config, {
      access_token: DEMO_TOKEN,
      token_type: 'bearer',
      user: DEMO_USER,
    })
  }
  if (path === '/auth/me' || path === '/users/me') {
    return ok(config, DEMO_USER)
  }

  // 偏好
  if (path === '/preferences' && method === 'get') return ok(config, DEMO_PREFERENCES)
  if (path === '/preferences' && method === 'put') {
    return ok(config, { ...DEMO_PREFERENCES, ...body })
  }
  if (path === '/preferences/template' || path === '/preferences/template-preference') {
    return ok(config, { preferred_template: DEMO_PREFERENCES.preferred_template })
  }

  // 个人画像
  if (path === '/profile/items' && method === 'get') {
    const category = (config.params?.category as string) || ''
    const status = (config.params?.status as string) || ''
    let items = DEMO_PROFILE_ITEMS
    if (category) items = items.filter((i) => i.category === category)
    if (status) items = items.filter((i) => i.status === status)
    return ok(config, items)
  }
  if (path === '/profile/categories') {
    const map: Record<string, number> = {}
    for (const item of DEMO_PROFILE_ITEMS) {
      map[item.category] = (map[item.category] || 0) + 1
    }
    return ok(config, Object.entries(map).map(([category, count]) => ({ category, count })))
  }
  if (path === '/profile/resume-source') {
    return ok(config, DEMO_RESUME_SOURCE)
  }
  if (path === '/profile/directions/recommend') {
    await sleep(AI_DELAY)
    return ok(config, {
      directions: DEMO_DIRECTIONS.map((d) => ({
        title: d.title,
        reason: d.reason,
        detail: d.detail,
      })),
      basis: [
        { key: 'target', item_id: 113, category: 'target', title: '目标岗位', summary: '前端 / 全栈（上海、杭州）' },
        { key: 'skill', item_id: 107, category: 'skill', title: '前端工程', summary: 'Vue3 / TypeScript / 性能优化' },
      ],
      data_source: 'demo',
      decision_logic: '演示模式：按画像目标岗位与技能匹配返回 3 个投递方向',
      profile_updated_at: '2026-10-12T08:00:00Z',
    })
  }
  if (path === '/profile/directions' && method === 'get') {
    return ok(config, DEMO_DIRECTIONS)
  }
  if (path === '/profile/form' && method === 'get') {
    return ok(config, {
      basic_info: {
        name: '林知远',
        email: 'resume-demo@example.com',
        phone: '+86 000 0000 0000',
        city: '上海',
        summary: '华东理工大学计算机本科，前端实习与全栈项目经验。',
      },
      education: [
        {
          school: '华东理工大学',
          degree: '本科',
          major: '计算机科学与技术',
          start: '2022-09',
          end: '2026-06',
          gpa: '3.7/4.0',
          courses: '数据结构、操作系统、计算机网络、数据库',
        },
      ],
      awards: [],
      social: [{ platform: 'GitHub', account: 'lin-zhiyuan-demo' }],
      extra: [],
    })
  }
  if (path === '/profile/form' && method === 'post') {
    return ok(config, body)
  }
  if (path === '/profile/soft-info/generate') {
    await sleep(AI_DELAY)
    return ok(config, {
      personality: '认真踏实，喜欢把问题拆到可验证的步骤',
      vision: '成为能独立交付体验的前端/全栈工程师',
      disinterested: '',
      self_eval:
        '结构化表达，结论先行；重视工程化与可量化结果。实习期间推动首屏 -38% 与组件复用。',
    })
  }
  // 文件上传（求职分析）
  if (path.includes('/upload') && method === 'post') {
    return ok(config, {
      message: '已上传（演示）',
      hint: '演示模式不会真正解析文件，完整能力请克隆 GitHub 仓库运行。',
      file: {
        filename: 'demo.txt',
        saved_name: 'demo.txt',
        file_path: '/tmp/demo.txt',
        file_type: 'txt',
        file_size: 12,
        uploaded_at: new Date().toISOString(),
      },
    })
  }
  if (path.startsWith('/profile/proposals')) {
    return ok(config, DEMO_PROPOSALS)
  }
  if (path.startsWith('/profile/items/')) {
    const id = Number(path.split('/').pop())
    return ok(config, DEMO_PROFILE_ITEMS.find((i) => i.id === id) || DEMO_PROFILE_ITEMS[0])
  }

  // 简历库
  if (path === '/resumes' && method === 'get') return ok(config, DEMO_RESUME_DOCS)
  if (path === '/resumes/recycle-bin') return ok(config, [])
  if (/^\/resumes\/\d+$/.test(path) && method === 'get') {
    const id = Number(path.split('/').pop())
    return ok(config, DEMO_RESUME_DOCS.find((d) => d.id === id) || DEMO_RESUME_DOCS[0])
  }
  if (/^\/resumes\/\d+\/versions$/.test(path)) {
    const id = Number(path.split('/')[2])
    const doc = DEMO_RESUME_DOCS.find((d) => d.id === id) || DEMO_RESUME_DOCS[0]
    return ok(config, doc.current_version ? [doc.current_version] : [])
  }
  if (/^\/resumes\/\d+\/has-layout-source$/.test(path)) {
    return ok(config, { has_source: false, is_docx: false, filename: null })
  }
  if (/^\/resumes\/sections\/\d+\/rewrite$/.test(path)) {
    await sleep(AI_DELAY)
    return ok(config, {
      section_id: Number(path.split('/')[3]),
      version_id: 101,
      candidates: [
        {
          rewrite: '将性能优化结果前置：首屏 3.2s→2.0s（-38%），并说明测量与回归方式。',
          approach: '结果前置 + 补证据',
          changes: ['量化结果前置', '补充验证方法'],
          new_numbers: ['-38%'],
        },
        {
          rewrite: '突出组件库贡献：沉淀 12 个通用组件，降低业务页重复代码约 30%。',
          approach: '组件化贡献强化',
          changes: ['强调复用收益'],
          new_numbers: ['12', '30%'],
        },
      ],
      needs_source_confirmation: true,
      new_numbers: ['-38%', '12', '30%'],
      new_claims: ['Playwright 冒烟拦截 8 起回归'],
      advice: '建议确认项目截图或周报中的原始数据后再定稿。',
    })
  }

  // 简历生成向导
  if (path === '/resume-generation/draft' && method === 'get') {
    return ok(config, {
      step: 3,
      data: {
        basic_info: { name: '林知远', email: 'resume-demo@example.com', city: '上海' },
        directions: ['前端 / 全栈工程师'],
      },
      updated_at: '2026-10-12T08:00:00Z',
    })
  }
  if (path === '/resume-generation/draft' && method === 'post') {
    return ok(config, { step: body?.step ?? null, data: body?.data ?? {}, updated_at: new Date().toISOString() })
  }
  if (path === '/resume-generation/generate' || path === '/resume-generation/tailor') {
    await sleep(AI_DELAY * 2)
    return ok(config, {
      content: {
        sections: DEMO_RESUME_DOCS[0].current_version?.content?.sections || [],
        raw_text: DEMO_RESUME_DOCS[0].current_version?.content?.raw_text || '',
      },
      document: DEMO_RESUME_DOCS[0],
      changes: [
        { section: '实习经历', change: '量化性能结果并前置' },
        { section: '项目经历', change: '补充服务规模与协同设计' },
      ],
    })
  }
  if (path === '/resume-generation/experiences/structure' || path === '/resume-generation/experiences/generate') {
    await sleep(AI_DELAY)
    return ok(config, [
      {
        exp_type: 'internship',
        company: '星河科技',
        title: '前端开发实习生',
        duration: '2025.06 – 2025.12',
        duty: 'B 端工作台与组件库',
        achievement: '首屏 3.2s→2.0s，组件 12 个',
      },
    ])
  }

  // 岗位匹配
  if (path === '/matching/postings' && method === 'get') return ok(config, DEMO_POSTINGS)
  if (path === '/matching/postings' && method === 'post') {
    return ok(config, {
      id: 30,
      company: body?.company || '演示公司',
      title: body?.title || '演示岗位',
      jd_text: body?.jd_text || '',
      source: 'manual',
      task_count: 0,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    })
  }
  if (path === '/matching/tasks' && method === 'get') return ok(config, DEMO_MATCH_TASKS)
  if (path === '/matching/tasks' && method === 'post') {
    return ok(config, {
      id: 32,
      job_posting_id: body?.job_posting_id || body?.posting_id || 21,
      company: body?.company || '云帆数据',
      posting_title: body?.posting_title || body?.title || '全栈工程师（校招）',
      resume_version_id: body?.resume_version_id || 101,
      page_preference: body?.page_preference || 'one_page',
      score: null,
      stage: 'pending',
      summary: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    })
  }
  if (/^\/matching\/tasks\/\d+\/run$/.test(path)) {
    await sleep(AI_DELAY * 2)
    return ok(config, {
      ...DEMO_MATCH_TASKS[0],
      stage: 'completed',
      summary: {
        ...DEMO_MATCH_TASKS[0].summary,
        stage_history: [
          { step: '解析 JD', status: 'ok', at: new Date().toISOString() },
          { step: '对照画像', status: 'ok', at: new Date().toISOString() },
          { step: '生成差距与草稿', status: 'ok', at: new Date().toISOString() },
        ],
        finished_at: new Date().toISOString(),
      },
    })
  }

  // 投递记录
  if (path === '/applications/summary') {
    const by_status: Record<string, number> = {}
    const by_result = { ongoing: 0, passed: 0, failed: 0 }
    for (const a of DEMO_APPLICATIONS) {
      by_status[a.status] = (by_status[a.status] || 0) + 1
      by_result[a.result] += 1
    }
    return ok(config, { total: DEMO_APPLICATIONS.length, by_status, by_result })
  }
  if (path === '/applications' && method === 'get') return ok(config, DEMO_APPLICATIONS)
  if (path === '/applications' && method === 'post') {
    return ok(config, {
      id: Date.now() % 10000,
      company: body?.company || '演示公司',
      job_title: body?.job_title || '演示岗位',
      status: body?.status || 'applied',
      result: 'ongoing',
      notes: body?.notes || null,
      applied_at: body?.applied_at || new Date().toISOString().slice(0, 10),
      created_at: new Date().toISOString(),
    })
  }

  // 会话（求职分析）
  if (path === '/sessions' && method === 'post') {
    return ok(config, { session_id: `sess-${Date.now()}`, created_at: new Date().toISOString() })
  }
  if (path === '/sessions' && method === 'get') return ok(config, DEMO_SESSIONS)
  if (/^\/sessions\/[^/]+$/.test(path) && method === 'get') {
    return ok(config, demoSessionDetail(path.split('/')[2]))
  }
  if (/^\/sessions\/[^/]+\/status$/.test(path)) {
    return ok(config, { stage: 'completed', running: false })
  }

  // 模拟面试（文字 REST 路径）
  if (path === '/interview/jd-analysis') {
    await sleep(AI_DELAY)
    return ok(config, DEMO_JD_ANALYSIS)
  }
  if (path === '/interview/start') {
    await sleep(AI_DELAY)
    return ok(config, {
      interview_id: `iv-${Date.now()}`,
      question:
        '请用 2 分钟介绍你最能体现工程能力的项目，并说明你的个人贡献。',
    })
  }
  if (/^\/interview\/[^/]+\/answer$/.test(path)) {
    await sleep(AI_DELAY)
    return ok(config, {
      question: '你提到首屏从 3.2s 降到 2.0s，具体定位过哪些瓶颈？如何验证优化有效？',
      is_complete: false,
      report: null,
    })
  }
  if (/^\/interview\/[^/]+\/report$/.test(path)) {
    return ok(config, DEMO_INTERVIEW_REPORT)
  }
  if (path === '/interview/history') {
    return ok(config, [
      {
        interview_id: 'iv-demo-1',
        target_position: '全栈工程师（校招）',
        turn_count: 4,
        completion_reason: '计划题目已覆盖',
        created_at: '2026-10-12T10:00:00Z',
        overall_score: 84,
        summary: '整体可过，建议补强系统设计案例。',
      },
    ])
  }
  if (/^\/interview\/history\/[^/]+$/.test(path)) {
    return ok(config, {
      interview_id: 'iv-demo-1',
      target_position: '全栈工程师（校招）',
      difficulty_level: 'medium',
      turn_count: 4,
      completion_reason: '计划题目已覆盖',
      created_at: '2026-10-12T10:00:00Z',
      dimension_scores: DEMO_INTERVIEW_REPORT.dimension_scores,
      strengths: DEMO_INTERVIEW_REPORT.strengths,
      weaknesses: DEMO_INTERVIEW_REPORT.weaknesses,
      conversation_history: [
        { role: 'assistant', content: '请用 2 分钟介绍你最能体现工程能力的项目。' },
        { role: 'user', content: '我在星河科技负责 B 端性能优化，首屏从 3.2s 降到 2.0s……' },
      ],
      final_report: DEMO_INTERVIEW_REPORT,
    })
  }
  if (path === '/interview/tts-voices') {
    return ok(config, [{ id: 'demo', name: '演示音色' }])
  }
  if (path === '/interview/tts-preview') {
    // 返回极短静音 WAV，避免演示站音频链路报错
    const wav = base64ToBuffer(
      'UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAIA+AAACABAAZGF0YQAAAAA=',
    )
    return ok(config, wav)
  }

  // 兜底：按集合语义给空结构，避免页面白屏
  if (method === 'get') {
    if (path.endsWith('s') || path.includes('list')) return ok(config, [])
    return ok(config, null)
  }
  return ok(config, { ok: true, demo: true })
}

function base64ToBuffer(b64: string): ArrayBuffer {
  const bin = atob(b64)
  const buf = new Uint8Array(bin.length)
  for (let i = 0; i < bin.length; i++) buf[i] = bin.charCodeAt(i)
  return buf.buffer
}

/** 演示模式下拦截 fetch（SSE 发消息等） */
export function installDemoFetch() {
  const originalFetch = window.fetch.bind(window)

  window.fetch = async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
    const url =
      typeof input === 'string'
        ? input
        : input instanceof URL
          ? input.href
          : (input as Request).url

    if (!url.includes('/api/')) {
      return originalFetch(input as any, init)
    }

    const method = (init?.method || (typeof input === 'object' && 'method' in input ? input.method : 'GET') || 'GET').toUpperCase()
    const path = url.replace(/^.*\/api/, '').split('?')[0]

    // SSE 消息：按固定剧本流式返回（event: + data: 协议）
    if (path.includes('/sessions/') && path.endsWith('/messages') && method === 'POST') {
      const events: Array<{ event: string; data: Record<string, unknown> }> = [
        {
          event: 'progress',
          data: { message: '正在对照个人画像与 JD…' },
        },
        {
          event: 'intent',
          data: {
            intent: 'gap_analysis',
            plan: ['解析 JD', '对照画像', '生成差距与定制建议'],
          },
        },
        {
          event: 'gap_analysis',
          data: {
            items: [
              {
                requirement: 'TypeScript / 前端工程化',
                current_level: '熟练，有性能与组件化实践',
                gap_severity: 'low',
                suggestion: '保持并准备量化案例',
              },
              {
                requirement: 'Node/Python 服务设计',
                current_level: '项目级了解',
                gap_severity: 'medium',
                suggestion: '补充鉴权与慢查询排查案例',
              },
            ],
          },
        },
        {
          event: 'message',
          data: {
            role: 'assistant',
            content:
              '已完成分析：匹配度约 82。优势在 TypeScript 工程化与性能优化；差距在后端服务设计。完整能力请从 GitHub 克隆运行。',
          },
        },
        {
          event: 'done',
          data: { stage: 'completed', message: '分析完成' },
        },
      ]
      const stream = new ReadableStream({
        start(controller) {
          for (const ev of events) {
            controller.enqueue(encoder.encode(`event: ${ev.event}\ndata: ${JSON.stringify(ev.data)}\n\n`))
          }
          controller.close()
        },
      })
      return new Response(stream, {
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
      })
    }

    // 其它 fetch 也走 axios mock 逻辑会重复实现；这里给简单 JSON
    return new Response(JSON.stringify({ ok: true, demo: true }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    })
  }
}

/** 演示模式下的 WebSocket 假实现：语音面试按剧本播放问答 */
export function installDemoWebSocket() {
  const OriginalWebSocket = window.WebSocket

  class DemoWebSocket extends OriginalWebSocket {
    constructor(url: string | URL, protocols?: string | string[]) {
      // 使用一个不会真正连接的 URL，再立刻覆盖行为
      void url
      super('ws://127.0.0.1/demo', protocols as any)
      queueMicrotask(() => {
        try {
          this.close()
        } catch {
          /* ignore */
        }
        this.simulate()
      })
    }

    private simulate() {
      const self = this as unknown as {
        onopen: ((ev: Event) => void) | null
        onmessage: ((ev: MessageEvent) => void) | null
        onclose: ((ev: CloseEvent) => void) | null
        onerror: ((ev: Event) => void) | null
        readyState: number
        send: (data: string) => void
      }

      // 模拟连接成功
      setTimeout(() => {
        self.readyState = 1
        self.onopen?.(new Event('open'))
        self.onmessage?.(
          new MessageEvent('message', {
            data: JSON.stringify({
              type: 'session_ready',
              interview_id: 'iv-demo-voice',
              message: '演示模式：语音链路为本地 Mock，完整语音面试请克隆 GitHub 仓库运行。',
            }),
          }),
        )
        setTimeout(() => {
          self.onmessage?.(
            new MessageEvent('message', {
              data: JSON.stringify({
                type: 'question',
                question: '请用 2 分钟介绍你最能体现工程能力的项目，并说明你的个人贡献。',
              }),
            }),
          )
        }, 400)
      }, 100)

      const send = self.send
      self.send = (data: string) => {
        try {
          const payload = JSON.parse(data)
          if (payload?.type === 'audio_chunk' || payload?.type === 'audio_end') return
          setTimeout(() => {
            self.onmessage?.(
              new MessageEvent('message', {
                data: JSON.stringify({
                  type: 'evaluation',
                  text: '回答结构清晰，量化结果到位。',
                  next_question: '你提到首屏从 3.2s 降到 2.0s，具体定位过哪些瓶颈？',
                }),
              }),
            )
          }, 500)
        } catch {
          /* ignore */
        }
        // 不真正发送
        void send
      }
    }
  }

  window.WebSocket = DemoWebSocket as unknown as typeof WebSocket
}
