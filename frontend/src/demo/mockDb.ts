/**
 * 演示账号「林知远」工作台 Mock 数据。
 * 全部虚构，仅供 GitHub Pages 公开预览使用。
 */
import type {
  JobApplication,
  JobPostingVO,
  MatchTaskVO,
  ProfileCategory,
  ProfileItem,
  ProfileFormData,
  ResumeLibraryDoc,
  SessionListItem,
  Userinfo,
  UserPreferences,
} from '../types'

export const DEMO_USER: Userinfo = {
  id: 1,
  username: '林知远',
  email: 'resume-demo@example.com',
  is_active: true,
}

export const DEMO_TOKEN = 'demo-token-lin-zhiyuan'

export const DEMO_PREFERENCES: UserPreferences = {
  preferred_template: 'modern',
  resume_style: 'professional',
  job_preferences: {
    cities: ['上海', '杭州'],
    roles: ['前端工程师', '全栈工程师'],
  },
  extra: { demo: true },
}

export const DEMO_REPO_URL = 'https://github.com/Lzy22301093/EasyResume'

function evidence(id: number, source: string, quote: string) {
  return {
    id,
    source_type: source,
    source_id: `src-${id}`,
    quote,
    verified_by_user: true,
    created_at: '2026-09-01T10:00:00Z',
  }
}

let profileSeq = 100

function p(
  category: ProfileCategory,
  title: string,
  content: string,
  status: ProfileItem['status'] = 'confirmed',
  quote = '',
): ProfileItem {
  profileSeq += 1
  return {
    id: profileSeq,
    category,
    title,
    content,
    item_type: 'fact',
    confidence: 0.92,
    visibility: 'resume_interview',
    status,
    sort_order: profileSeq,
    evidences: quote ? [evidence(profileSeq, 'resume', quote)] : [],
    created_at: '2026-09-01T10:00:00Z',
    updated_at: '2026-10-12T08:00:00Z',
  }
}

export const DEMO_PROFILE_ITEMS: ProfileItem[] = [
  p('basic_info', '姓名', '林知远', 'confirmed', '林知远'),
  p('basic_info', '邮箱', 'resume-demo@example.com', 'confirmed'),
  p('basic_info', '手机', '+86 000 0000 0000', 'confirmed'),
  p('basic_info', '城市', '上海', 'confirmed', '上海'),
  p('education', '华东理工大学 · 计算机科学与技术 · 本科', '2022.09 – 2026.06\nGPA 3.7/4.0，专业前 15%\n主修：数据结构、操作系统、计算机网络、数据库', 'confirmed', '华东理工大学'),
  p('experience', '星河科技 · 前端开发实习生', '2025.06 – 2025.12\n负责 B 端工作台性能优化与组件库维护，推动首屏时间下降 38%。', 'confirmed', '星河科技'),
  p('experience', '校园开源社区 · 全栈项目负责人', '2024.10 – 2025.05\n主导「课程表协同」小程序，服务校内 2000+ 学生。', 'confirmed'),
  p('skill', '前端工程', 'Vue 3 / TypeScript / Vite / Element Plus，熟悉组合式 API 与组件库设计', 'confirmed'),
  p('skill', '工程化与质量', 'Vitest、Playwright 冒烟、ESLint、CI 构建与性能预算', 'confirmed'),
  p('skill', '全栈协作', 'Node.js、FastAPI 基础、MySQL、Docker Compose 联调', 'confirmed'),
  p('target', '前端工程师（上海 / 杭州）', '优先开发者工具与企业协作产品，接受校招全栈向', 'confirmed'),
  p('target', '全栈工程师（校招）', 'Web 端 + Node/Python 服务，重视工程化与项目闭环', 'confirmed'),
  p('target', '前端实习生（大厂 / 独角兽）', '已有星河科技实习，目标再补一段大厂经历', 'confirmed'),
  p('soft', '协作风格', '习惯先写验收标准再动手，文档与演示同步更新', 'confirmed'),
  p('soft', '表达偏好', '结构化表达：结论先行，再给证据与取舍', 'confirmed'),
  p('social', 'GitHub', 'github.com/lin-zhiyuan-demo', 'confirmed'),
]

/** 投递方向候选（分析方向 / 从画像带入用） */
export const DEMO_DIRECTIONS = [
  {
    id: 501,
    title: '前端工程师（上海 / 杭州）',
    reason: '画像已确认目标岗位，匹配前端实习与工程化经历',
    detail: 'Vue3/TS/性能优化是优势；组件库与首屏优化可量化。',
    source_type: 'ai_recommendation' as const,
  },
  {
    id: 502,
    title: '全栈工程师（校招）',
    reason: '画像已确认目标岗位，课程表项目具备全栈闭环',
    detail: 'Vue + Node + MySQL + Docker；需补强服务端排障表达。',
    source_type: 'ai_recommendation' as const,
  },
  {
    id: 503,
    title: '前端实习生（大厂 / 独角兽）',
    reason: '已有星河科技实习，适合再冲一段大厂前端实习',
    detail: '突出性能指标与组件复用度，准备系统设计追问。',
    source_type: 'user_manual' as const,
  },
]

/** 一键填入 / 从画像导入 的结构化画像源 */
export const DEMO_RESUME_SOURCE = {
  basic_info: {
    name: '林知远',
    gender: '男',
    phone: '+86 000 0000 0000',
    email: 'resume-demo@example.com',
    location: '上海',
    birthday: '2004-03-12',
  },
  soft_info: {
    personality: '认真踏实，喜欢把问题拆到可验证的步骤',
    vision: '成为能独立交付体验的前端/全栈工程师',
    disinterested: '',
    self_eval:
      '结构化表达，结论先行；重视工程化与可量化结果。实习期间推动首屏 -38% 与组件复用。',
  },
  educations: [
    {
      school: '华东理工大学',
      degree: '本科',
      major: '计算机科学与技术',
      start: '2022-09',
      end: '2026-06',
      current: false,
      gpa: '3.7/4.0',
      rank: '前 15%',
      courses: '数据结构、操作系统、计算机网络、数据库系统',
    },
  ],
  skills: [
    { name: 'Vue 3', level: '精通', notes: '组合式 API / 组件库' },
    { name: 'TypeScript', level: '掌握', notes: '工程化实践' },
    { name: 'Vite', level: '掌握', notes: '构建与性能优化' },
    { name: 'Element Plus', level: '掌握', notes: 'B 端表单与表格' },
    { name: 'Vitest / Playwright', level: '熟悉', notes: '冒烟与回归' },
    { name: 'Node.js', level: '熟悉', notes: '接口与工具链' },
    { name: 'MySQL', level: '熟悉', notes: '表设计与索引基础' },
    { name: 'Docker', level: '熟悉', notes: 'Compose 联调' },
  ],
  internships: [
    {
      exp_type: 'internship',
      company: '星河科技',
      title: '前端开发实习生',
      start: '2025-06',
      end: '2025-12',
      current: false,
      duration: '2025.06 – 2025.12',
      tech_stack: 'Vue3 / TypeScript / Vite',
      duty: 'B 端工作台与组件库维护',
      achievement: '首屏 3.2s→2.0s（-38%），沉淀 12 个通用组件',
      situation: '工作台列表页首屏慢，业务页重复代码多',
      task: '定位性能瓶颈并推动组件化',
      action: '拆路由/懒加载、缓存策略、抽组件、加冒烟',
      result: '首屏 -38%，重复代码约 -30%，拦截 8 起回归',
    },
  ],
  projects: [
    {
      exp_type: 'project',
      company: '校园开源社区',
      title: '课程表协同小程序 · 项目负责人',
      start: '2024-10',
      end: '2025-05',
      current: false,
      duration: '2024.10 – 2025.05',
      tech_stack: 'Vue3 / Node.js / MySQL / Docker',
      duty: '产品设计、冲突检测与权限模型、前后端实现',
      achievement: '服务 2000+ 学生，周活跃 600+',
      situation: '同学手动对课表，冲突多、协作难',
      task: '做一个可共享可协同的课表工具',
      action: '设计冲突检测与权限分层，Vue+Node 落地',
      result: '上线一学期服务 2000+ 学生，周活跃 600+',
    },
  ],
  directions: [] as typeof DEMO_DIRECTIONS,
  source_item_ids: [101, 102, 103, 107, 108, 109, 110, 113, 114, 115],
  profile_updated_at: '2026-10-12T08:00:00Z',
}

DEMO_RESUME_SOURCE.directions = DEMO_DIRECTIONS

export const DEMO_PROFILE_FORM: ProfileFormData = {
  basic_info: {
    name: '林知远',
    email: 'resume-demo@example.com',
    phone: '+86 000 0000 0000',
    city: '上海',
    summary: '华东理工大学计算机本科，前端实习与全栈项目经验，关注工程化与体验指标。',
  },
  education: [
    {
      school: '华东理工大学',
      degree: '本科',
      major: '计算机科学与技术',
      start: '2022-09',
      end: '2026-06',
      gpa: '3.7/4.0',
      courses: '数据结构、操作系统、计算机网络、数据库系统',
    },
  ],
  awards: ['校级优秀学生干部', '开源之夏参与证书'],
  social: [{ platform: 'GitHub', account: 'lin-zhiyuan-demo' }],
  extra: [],
}

const resumeSections = [
  {
    title: '教育背景',
    content:
      '华东理工大学 · 计算机科学与技术 · 本科（2022.09 – 2026.06）\nGPA 3.7/4.0，专业前 15%；主修数据结构、操作系统、计算机网络、数据库。',
  },
  {
    title: '实习经历',
    content:
      '星河科技 · 前端开发实习生（2025.06 – 2025.12）\n• 负责 B 端工作台列表与详情页重构，首屏时间从 3.2s 降至 2.0s（-38%）\n• 抽取 12 个通用表单/表格组件，业务页重复代码下降约 30%\n• 推动关键路径 Playwright 冒烟，回归缺陷提前拦截 8 起',
  },
  {
    title: '项目经历',
    content:
      '课程表协同小程序 · 项目负责人（2024.10 – 2025.05）\n• 设计冲突检测算法与共享权限模型，支持 3 人协同编辑同一课表\n• 上线一学期服务 2000+ 学生，周活跃 600+\n• 使用 Vue3 + Node.js + MySQL，Docker 一键部署',
  },
  {
    title: '专业技能',
    content: 'Vue 3 / TypeScript / Vite / Element Plus；Vitest / Playwright；Node.js / FastAPI / MySQL / Docker',
  },
]

export const DEMO_RESUME_DOCS: ResumeLibraryDoc[] = [
  {
    id: 11,
    title: '前端实习 · 星河科技内推版',
    source: 'generated',
    current_version_id: 101,
    version_count: 3,
    deleted_at: null,
    notes: '针对前端实习 JD，突出性能优化与组件化。',
    created_at: '2026-09-20T09:00:00Z',
    updated_at: '2026-10-10T15:00:00Z',
    current_version: {
      id: 101,
      document_id: 11,
      session_id: null,
      version: 3,
      content: { sections: resumeSections, raw_text: resumeSections.map((s) => s.title + '\n' + s.content).join('\n\n') },
      render_config: { template: 'modern', page_preference: 'one_page' },
      sections: resumeSections.map((s, i) => ({
        id: 201 + i,
        resume_version_id: 101,
        page_number: 1,
        section_type: s.title === '专业技能' ? 'skills' : 'experience',
        title: s.title,
        content: s.content,
        bounding_box: { x: 40, y: 80 + i * 160, width: 515, height: 140, page: 1 },
        sort_order: i,
        created_at: '2026-10-10T15:00:00Z',
        updated_at: '2026-10-10T15:00:00Z',
      })),
      is_current: true,
      created_at: '2026-10-10T15:00:00Z',
    },
  },
  {
    id: 12,
    title: '全栈校招通用版',
    source: 'generated',
    current_version_id: 111,
    version_count: 1,
    deleted_at: null,
    notes: '突出全栈项目与工程协作。',
    created_at: '2026-10-01T11:00:00Z',
    updated_at: '2026-10-01T11:00:00Z',
    current_version: {
      id: 111,
      document_id: 12,
      session_id: null,
      version: 1,
      content: { sections: resumeSections, raw_text: '' },
      render_config: { template: 'classic', page_preference: 'two_pages' },
      sections: [],
      is_current: true,
      created_at: '2026-10-01T11:00:00Z',
    },
  },
]

export const DEMO_APPLICATIONS: JobApplication[] = [
  {
    id: 1,
    company: '星河科技',
    job_title: '前端开发实习生',
    status: 'offer',
    result: 'passed',
    notes: '已口头 offer，等待正式函。',
    applied_at: '2026-10-08',
    created_at: '2026-10-08T10:00:00Z',
  },
  {
    id: 2,
    company: '云帆数据',
    job_title: '全栈工程师（校招）',
    status: 'interview',
    result: 'ongoing',
    notes: '二面技术面，准备项目深挖。',
    applied_at: '2026-10-05',
    created_at: '2026-10-05T10:00:00Z',
  },
  {
    id: 3,
    company: '青梧科技',
    job_title: '前端工程师',
    status: 'written_test',
    result: 'ongoing',
    notes: '在线笔试 10/18。',
    applied_at: '2026-10-02',
    created_at: '2026-10-02T10:00:00Z',
  },
  {
    id: 4,
    company: '岚山互娱',
    job_title: 'Web 前端',
    status: 'rejected',
    result: 'failed',
    notes: '一面后未通过，反馈系统设计不足。',
    applied_at: '2026-09-25',
    created_at: '2026-09-25T10:00:00Z',
  },
]

export const DEMO_POSTINGS: JobPostingVO[] = [
  {
    id: 21,
    company: '云帆数据',
    title: '全栈工程师（校招）',
    jd_text:
      '职位描述：\n1. 参与数据协作平台 Web 端开发（Vue/React）\n2. 参与 Node/Python 服务接口开发\n3. 关注性能、可访问性与工程质量\n任职要求：\n- 熟悉 TypeScript 与现代前端工程化\n- 有完整项目经历，能讲清取舍\n- 了解数据库与部署基础',
    source: 'manual',
    task_count: 1,
    created_at: '2026-10-04T09:00:00Z',
    updated_at: '2026-10-11T09:00:00Z',
  },
  {
    id: 22,
    company: '星河科技',
    title: '前端开发实习生',
    jd_text:
      '负责 B 端产品前端开发，要求 Vue3/TS 熟练，有组件库或性能优化经验优先，能独立推进需求。',
    source: 'manual',
    task_count: 1,
    created_at: '2026-09-18T09:00:00Z',
    updated_at: '2026-10-08T09:00:00Z',
  },
]

export const DEMO_MATCH_TASKS: MatchTaskVO[] = [
  {
    id: 31,
    job_posting_id: 21,
    company: '云帆数据',
    posting_title: '全栈工程师（校招）',
    resume_version_id: 101,
    page_preference: 'one_page',
    score: 82,
    stage: 'completed',
    summary: {
      company: '云帆数据',
      posting_title: '全栈工程师（校招）',
      score: 82,
      overall: 82,
      strengths: ['TypeScript 与 Vue 工程化扎实', '有可量化的性能优化成果', '全栈项目完整闭环'],
      gaps: [
        {
          category: '后端深度',
          requirement: 'Node/Python 服务设计与排障',
          current_level: '项目级了解',
          gap_severity: 'medium',
          suggestion: '补充接口设计、鉴权与慢查询排查案例',
        },
        {
          category: '系统设计',
          requirement: '协作并发与权限模型',
          current_level: '课程表项目有实践，深度一般',
          gap_severity: 'low',
          suggestion: '准备冲突检测与权限分层的取舍说明',
        },
      ],
      recommendations: [
        '简历中把「首屏 -38%」与组件复用度放在更前位置',
        '面试准备 Node 接口鉴权与索引优化问答',
      ],
      draft: {
        sections: [
          { title: '匹配摘要', content: '与全栈校招 JD 高度匹配，工程化与项目闭环是优势。' },
          { title: '优势', content: 'TypeScript、性能优化、组件化实践。' },
          { title: '待补强', content: '后端服务设计与系统设计表达。' },
        ],
        raw_text: '',
      },
      stage_history: [
        { step: '解析 JD', status: 'ok', at: '2026-10-11T10:00:00Z' },
        { step: '对照画像', status: 'ok', at: '2026-10-11T10:00:05Z' },
        { step: '生成差距与草稿', status: 'ok', at: '2026-10-11T10:00:12Z' },
      ],
      finished_at: '2026-10-11T10:00:12Z',
    },
    created_at: '2026-10-11T09:55:00Z',
    updated_at: '2026-10-11T10:00:12Z',
  },
]

export const DEMO_SESSIONS: SessionListItem[] = [
  {
    session_id: 'sess-demo-1',
    stage: 'completed',
    message_count: 2,
    updated_at: '2026-10-12T09:30:00Z',
  },
]

export const DEMO_JD_ANALYSIS = {
  title: '全栈工程师（校招）',
  company: '云帆数据',
  requirements: [
    { skill: 'TypeScript / 前端工程化', importance: 'high', category: 'frontend' },
    { skill: 'Node 或 Python 服务', importance: 'medium', category: 'backend' },
    { skill: '性能与工程质量', importance: 'high', category: 'quality' },
    { skill: '项目表达与取舍', importance: 'high', category: 'communication' },
  ],
  keywords: ['TypeScript', 'Vue', 'Node', '性能', '协作'],
  summary: '需要能独立交付 Web 端并参与服务端接口的全栈人才，重视工程化与表达。',
}

export const DEMO_INTERVIEW_QUESTIONS = [
  {
    id: 'q1',
    question: '请用 2 分钟介绍你最能体现工程能力的项目，并说明你的个人贡献。',
    dimension: '项目深挖',
    answer_points: ['目标与约束', '个人职责', '量化结果', '取舍与复盘'],
  },
  {
    id: 'q2',
    question: '你提到首屏从 3.2s 降到 2.0s，具体定位过哪些瓶颈？如何验证优化有效？',
    dimension: '性能优化',
    answer_points: ['测量方法', '瓶颈定位', '优化手段', '回归验证'],
  },
  {
    id: 'q3',
    question: '如果多人同时编辑同一份课表，你会如何设计冲突检测？',
    dimension: '系统设计',
    answer_points: ['并发模型', '冲突定义', '合并策略', '权限边界'],
  },
  {
    id: 'q4',
    question: '当产品需求与工程质量冲突时，你如何推进？请举例。',
    dimension: '协作沟通',
    answer_points: ['识别风险', '给出选项', '对齐标准', '事后沉淀'],
  },
]

export const DEMO_INTERVIEW_REPORT = {
  overall_score: 84,
  dimension_scores: {
    项目深挖: 86,
    性能优化: 88,
    系统设计: 78,
    协作沟通: 84,
  },
  strengths: ['有量化结果意识', '性能排查路径清晰', '表达结构化'],
  weaknesses: ['系统设计深度可再补', '对服务端故障场景演练不足'],
  summary: '整体达到前端/全栈校招面试可过水平，建议补强系统设计案例与服务端排障。',
  suggestions: [
    '准备 1 个并发冲突/一致性完整案例',
    '把组件库贡献整理成可讲述的设计原则',
  ],
}

export const DEMO_PROPOSALS = [
  {
    id: 901,
    report_id: 'report-demo-1',
    change_type: 'update',
    target_profile_item_id: 104,
    before_value: '负责 B 端工作台性能优化与组件库维护，推动首屏时间下降 38%。',
    after_value:
      '负责 B 端工作台性能优化与组件库维护：首屏 3.2s→2.0s（-38%），沉淀 12 个通用组件，关键路径冒烟拦截 8 起回归。',
    reason: '面试报告建议补充可验证细节，便于复用到简历与追问。',
    status: 'pending',
    created_at: '2026-10-12T10:00:00Z',
  },
]

export function demoSessionDetail(id: string) {
  return {
    session_id: id,
    stage: 'completed' as const,
    render_config: { template: 'modern', page_preference: 'one_page' },
    jd_analysis: DEMO_JD_ANALYSIS,
    gap_analysis: {
      summary: '与全栈校招 JD 高度匹配，工程化与项目闭环是优势；后端服务设计与系统表达可再补。',
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
    messages: [
      {
        role: 'user',
        content: '帮我分析云帆数据全栈 JD，并对照我的经历给差距和定制建议。',
        timestamp: '2026-10-12T09:01:00Z',
      },
      {
        role: 'assistant',
        content:
          '已完成 JD 分析与差距对照：匹配度约 82。优势在 TypeScript 工程化与性能优化；差距在后端服务设计。右侧结果面板可查看结构化产出。完整能力请从 GitHub 克隆运行。',
        timestamp: '2026-10-12T09:02:00Z',
      },
    ],
    created_at: '2026-10-12T09:00:00Z',
    updated_at: '2026-10-12T09:30:00Z',
  }
}
