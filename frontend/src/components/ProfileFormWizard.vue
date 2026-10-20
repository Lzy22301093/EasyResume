<template>
  <el-dialog
    v-model="visible"
    title="完善画像"
    width="880px"
    :append-to-body="true"
    :close-on-click-modal="false"
    class="profile-wizard-dialog"
    @closed="reset"
  >
    <!-- 顶部：4 步进度（身份 / 教育 / 经历 / 能力） -->
    <div class="wiz-steps" role="tablist">
      <button
        v-for="(s, i) in STEPS"
        :key="s.key"
        class="wiz-step"
        :class="{ active: step === i + 1, done: stepDone[i] }"
        type="button"
        @click="step = i + 1"
      >
        <span class="wiz-step-no" :class="{ done: stepDone[i] && step !== i + 1 }">
          <Check v-if="stepDone[i] && step !== i + 1" :size="14" />
          <span v-else>{{ i + 1 }}</span>
        </span>
        <span class="wiz-step-info">
          <b>{{ s.label }}</b>
          <small>{{ s.sub }}</small>
        </span>
      </button>
    </div>

    <div class="wiz-fill-bar">
      <span class="wiz-fill-hint">已有简历？可识别后填入表单，再逐项核对</span>
      <el-button size="small" @click="fillOpen = true">
        <FileUp :size="14" style="margin-right: 4px" />从简历一键填充
      </el-button>
    </div>

    <div class="wiz-body">
      <!-- ========== 01 基本信息：身份 + 头像 + 社交 ========== -->
      <template v-if="step === 1">
        <div class="sec-head">
          <h3>身份与联系方式</h3>
          <p>用于简历页眉、投递与联系方式展示</p>
        </div>
        <div class="wiz-grid">
          <div class="wiz-field" v-for="f in BASIC_FIELDS" :key="f.key">
            <label :class="{ req: f.required }">{{ f.label }}<span v-if="f.required" class="req-mark">*</span></label>
            <el-date-picker
              v-if="f.key === 'birthday'"
              v-model="form.basic_info[f.key]"
              type="date"
              value-format="YYYY-MM-DD"
              placeholder="选择出生日期"
              style="width: 100%"
            />
            <el-input v-else v-model="form.basic_info[f.key]" :placeholder="f.placeholder" clearable />
          </div>
        </div>

        <div class="sec-head tight">
          <h3>个人头像</h3>
          <p>展示在画像节点图中心，支持 JPG / PNG / WEBP</p>
        </div>
        <div class="avatar-row">
          <div class="avatar-preview" :class="{ empty: !avatarPreview }">
            <img v-if="avatarPreview" :src="avatarPreview" alt="头像" />
            <UserRound v-else :size="28" />
          </div>
          <div class="avatar-actions">
            <el-button size="small" type="primary" :loading="avatarUploading" @click="fileInput?.click()">
              <Upload :size="14" style="margin-right: 4px" />{{ avatarPreview ? '更换头像' : '上传头像' }}
            </el-button>
            <el-button v-if="avatarPreview" size="small" text @click="clearAvatar">移除</el-button>
            <span class="avatar-hint">自动居中裁剪为 256×256</span>
          </div>
          <input ref="fileInput" type="file" accept="image/jpeg,image/png,image/webp" hidden @change="onAvatarChange" />
        </div>

        <div class="sec-head tight">
          <h3>社交账号</h3>
          <p>可选，便于内推或作品展示</p>
        </div>
        <div v-for="(soc, i) in form.social" :key="i" class="row-line">
          <el-input v-model="soc.platform" placeholder="平台，如：GitHub" class="row-platform" />
          <el-input v-model="soc.account" placeholder="账号 / 链接" class="row-account" />
          <button class="row-del" type="button" title="删除" @click="form.social.splice(i, 1)">
            <Trash2 :size="14" />
          </button>
        </div>
        <button class="wiz-add ghost" type="button" @click="form.social.push({ platform: '', account: '' })">
          <Plus :size="14" style="margin-right: 4px" />添加社交账号
        </button>
      </template>

      <!-- ========== 02 教育与奖项 ========== -->
      <template v-else-if="step === 2">
        <div class="sec-head">
          <h3>教育经历</h3>
          <p>按最高学历优先填写，可添加多段</p>
        </div>
        <div v-for="(edu, i) in form.education" :key="i" class="wiz-card">
          <div class="wiz-card-head">
            <span class="idx">EDU · {{ String(i + 1).padStart(2, '0') }}</span>
            <el-button text type="danger" size="small" @click="form.education.splice(i, 1)">
              <Trash2 :size="14" /> 删除
            </el-button>
          </div>
          <div class="wiz-grid">
            <div class="wiz-field">
              <label class="req">学校<span class="req-mark">*</span></label>
              <el-input v-model="edu.school" placeholder="如：北京交通大学" />
            </div>
            <div class="wiz-field">
              <label class="req">学历<span class="req-mark">*</span></label>
              <el-select v-model="edu.degree" placeholder="选择学历" style="width: 100%">
                <el-option v-for="d in DEGREES" :key="d" :label="d" :value="d" />
              </el-select>
            </div>
            <div class="wiz-field">
              <label>专业</label>
              <el-input v-model="edu.major" placeholder="如：软件工程" />
            </div>
            <div class="wiz-field">
              <label>GPA</label>
              <el-input v-model="edu.gpa" placeholder="0.0 - 5.0" />
            </div>
            <div class="wiz-field">
              <label>开始时间</label>
              <el-date-picker v-model="edu.start" type="month" value-format="YYYY-MM" placeholder="如：2020-09" style="width: 100%" />
            </div>
            <div class="wiz-field">
              <label>结束时间</label>
              <el-date-picker v-model="edu.end" type="month" value-format="YYYY-MM" placeholder="如：2024-06" style="width: 100%" />
            </div>
          </div>
          <div class="wiz-field">
            <label>主修课程</label>
            <el-input v-model="edu.courses" type="textarea" :rows="2" placeholder="如：数据结构、计算机网络" />
          </div>
        </div>
        <button class="wiz-add" type="button" @click="addEducation">
          <Plus :size="14" style="margin-right: 4px" /> 新增教育经历
        </button>

        <div class="sec-head">
          <h3>奖项与荣誉</h3>
          <p>每行一条，写清奖项名称即可</p>
        </div>
        <el-input
          v-model="form.awards"
          type="textarea"
          :rows="4"
          placeholder="每行一条，如：&#10;国家奖学金&#10;全国大学生数学建模竞赛一等奖"
        />
      </template>

      <!-- ========== 03 实践经历：实习 / 项目 ========== -->
      <template v-else-if="step === 3">
        <div class="sec-head">
          <h3>实习经历</h3>
          <p>公司、岗位、时间、职责与可量化成果</p>
        </div>
        <template v-if="internships.length">
          <div v-for="ext in internships" :key="ext._id" class="wiz-card">
            <div class="wiz-card-head">
              <span class="idx">INT · {{ ext._seq }}</span>
              <el-button text type="danger" size="small" @click="removeExtra(ext._id)">
                <Trash2 :size="14" /> 删除
              </el-button>
            </div>
            <div class="wiz-grid two">
              <div class="wiz-field">
                <label class="req">公司名称<span class="req-mark">*</span></label>
                <el-input v-model="ext.title" placeholder="如：某科技公司" />
              </div>
              <div class="wiz-field">
                <label>实习岗位</label>
                <el-input v-model="ext.role" placeholder="如：后端实习生" />
              </div>
              <div class="wiz-field">
                <label>开始时间</label>
                <el-date-picker v-model="ext.start" type="month" value-format="YYYY-MM" placeholder="选择开始月份" style="width: 100%" />
              </div>
              <div class="wiz-field">
                <label>结束时间</label>
                <div class="period-end">
                  <el-checkbox v-model="ext.current">至今</el-checkbox>
                  <el-date-picker v-model="ext.end" type="month" value-format="YYYY-MM" placeholder="选择结束月份" :disabled="ext.current" style="flex: 1" />
                </div>
              </div>
            </div>
            <div class="wiz-field">
              <label>实习职责</label>
              <el-input v-model="ext.duty" type="textarea" :rows="3" placeholder="完整描述工作内容、使用的方法与承担的责任" />
            </div>
            <div class="wiz-field">
              <label>实习成果</label>
              <el-input v-model="ext.achievement" type="textarea" :rows="2" placeholder="尽量量化：完成了什么、提升了什么、结果如何" />
            </div>
          </div>
        </template>
        <div v-else class="empty-slot">暂无实习经历，可跳过</div>
        <button class="wiz-add" type="button" @click="addExperience('internship')">
          <Plus :size="14" style="margin-right: 4px" /> 新增实习经历
        </button>

        <div class="sec-head">
          <h3>项目经历</h3>
          <p>项目背景、负责模块、技术方案与成果</p>
        </div>
        <template v-if="projects.length">
          <div v-for="ext in projects" :key="ext._id" class="wiz-card">
            <div class="wiz-card-head">
              <span class="idx">PRJ · {{ ext._seq }}</span>
              <el-button text type="danger" size="small" @click="removeExtra(ext._id)">
                <Trash2 :size="14" /> 删除
              </el-button>
            </div>
            <div class="wiz-grid two">
              <div class="wiz-field">
                <label class="req">项目名称<span class="req-mark">*</span></label>
                <el-input v-model="ext.title" placeholder="如：智能简历平台" />
              </div>
              <div class="wiz-field">
                <label>项目角色</label>
                <el-input v-model="ext.role" placeholder="如：后端负责人" />
              </div>
              <div class="wiz-field">
                <label>技术栈</label>
                <el-input v-model="ext.tech_stack" placeholder="如：Vue3、FastAPI、MySQL" />
              </div>
              <div class="wiz-field">
                <label>开始时间</label>
                <el-date-picker v-model="ext.start" type="month" value-format="YYYY-MM" placeholder="选择开始月份" style="width: 100%" />
              </div>
              <div class="wiz-field">
                <label>结束时间</label>
                <div class="period-end">
                  <el-checkbox v-model="ext.current">至今</el-checkbox>
                  <el-date-picker v-model="ext.end" type="month" value-format="YYYY-MM" placeholder="选择结束月份" :disabled="ext.current" style="flex: 1" />
                </div>
              </div>
            </div>
            <div class="wiz-field">
              <label>项目职责</label>
              <el-input v-model="ext.duty" type="textarea" :rows="3" placeholder="完整描述项目背景、负责模块、技术方案与关键实现" />
            </div>
            <div class="wiz-field">
              <label>项目成果</label>
              <el-input v-model="ext.achievement" type="textarea" :rows="2" placeholder="尽量量化：完成了什么、提升了什么、结果如何" />
            </div>
          </div>
        </template>
        <div v-else class="empty-slot">暂无项目经历，可跳过</div>
        <button class="wiz-add" type="button" @click="addExperience('project')">
          <Plus :size="14" style="margin-right: 4px" /> 新增项目经历
        </button>
      </template>

      <!-- ========== 04 能力与方向：轻量技能/目标/软性 ========== -->
      <template v-else-if="step === 4">
        <div class="sec-head">
          <h3>专业技能</h3>
          <p>输入后回车添加，点标签可删除</p>
        </div>
        <div class="tag-input">
          <el-tag
            v-for="(s, i) in form.skills"
            :key="s + i"
            closable
            size="large"
            @close="form.skills.splice(i, 1)"
          >{{ s }}</el-tag>
          <el-input
            v-model="skillDraft"
            class="tag-draft"
            placeholder="如：Python、Vue、机器学习"
            @keydown.enter.prevent="pushTag(form.skills, 'skill')"
          />
        </div>

        <div class="sec-head">
          <h3>目标岗位</h3>
          <p>可填 1–3 个方向，便于匹配与推荐</p>
        </div>
        <div class="tag-input">
          <el-tag
            v-for="(t, i) in form.targets"
            :key="t + i"
            closable
            size="large"
            type="success"
            @close="form.targets.splice(i, 1)"
          >{{ t }}</el-tag>
          <el-input
            v-model="targetDraft"
            class="tag-draft"
            placeholder="如：后端开发工程师"
            @keydown.enter.prevent="pushTag(form.targets, 'target')"
          />
        </div>

        <div class="sec-head">
          <h3>软性信息</h3>
          <p>性格、愿景与自我评价，后续简历与面试会自动复用</p>
        </div>
        <div class="soft-grid">
          <div class="wiz-field">
            <label>性格特点</label>
            <el-input v-model="form.soft.personality" placeholder="如：沉稳、有责任心" />
          </div>
          <div class="wiz-field">
            <label>职业愿景</label>
            <el-input v-model="form.soft.vision" placeholder="如：成长为能独立负责模块的后端工程师" />
          </div>
          <div class="wiz-field">
            <label>不感兴趣的方向</label>
            <el-input v-model="form.soft.disinterested" placeholder="如：纯销售岗、频繁出差" />
          </div>
          <div class="wiz-field span-2">
            <label>自我评价</label>
            <el-input
              v-model="form.soft.self_eval"
              type="textarea"
              :rows="3"
              placeholder="一段真诚的自我评价，概括优势与做事风格"
            />
          </div>
        </div>

        <!-- 少量其他条目（面试反馈等）折叠收纳，不干扰主流程 -->
        <template v-if="otherExtras.length">
          <button class="fold-toggle" type="button" @click="showOther = !showOther">
            <ChevronDown v-if="!showOther" :size="14" />
            <ChevronUp v-else :size="14" />
            其他补充（{{ otherExtras.length }}）
          </button>
          <div v-if="showOther" class="other-list">
            <div v-for="ext in otherExtras" :key="ext._id" class="wiz-card compact">
              <div class="wiz-card-head">
                <span class="idx">{{ ext.category === 'interview_feedback' ? 'FB' : 'OTH' }} · {{ ext._seq }}</span>
                <el-button text type="danger" size="small" @click="removeExtra(ext._id)">
                  <Trash2 :size="14" /> 删除
                </el-button>
              </div>
              <div class="wiz-grid two">
                <div class="wiz-field">
                  <label class="req">分类<span class="req-mark">*</span></label>
                  <el-select v-model="ext.category" placeholder="选择分类" style="width: 100%">
                    <el-option v-for="c in OTHER_CATEGORIES" :key="c.value" :label="c.label" :value="c.value" />
                  </el-select>
                </div>
                <div class="wiz-field">
                  <label class="req">标题<span class="req-mark">*</span></label>
                  <el-input v-model="ext.title" placeholder="条目标题" />
                </div>
              </div>
              <div class="wiz-field">
                <label>内容</label>
                <el-input v-model="ext.content" type="textarea" :rows="2" placeholder="具体事实 / 经历描述" />
              </div>
            </div>
            <button class="wiz-add ghost" type="button" @click="addOther">
              <Plus :size="14" style="margin-right: 4px" /> 添加其他条目
            </button>
          </div>
        </template>
        <button v-else class="wiz-add ghost" type="button" @click="addOther">
          <Plus :size="14" style="margin-right: 4px" /> 添加其他条目
        </button>
      </template>
    </div>

    <template #footer>
      <div class="wiz-foot">
        <div class="wiz-progress">
          <span class="done-count">{{ doneCount }} / {{ STEPS.length }} 已完成</span>
          <span class="wiz-req">带 * 为必填，其余可跳过</span>
        </div>
        <div class="wiz-foot-actions">
          <el-button v-if="step > 1" @click="step--">上一步</el-button>
          <el-button v-if="step < STEPS.length" type="primary" @click="next">
            下一步
            <ArrowRight :size="14" style="margin-left: 4px" />
          </el-button>
          <el-button v-else type="primary" :loading="saving" @click="saveAll">完成</el-button>
        </div>
      </div>
    </template>
  </el-dialog>

  <ProfileResumeImportDialog v-model="fillOpen" mode="fill" @filled="applyFillDraft" />
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import {
  ArrowRight, Check, ChevronDown, ChevronUp, FileUp, Plus, Trash2, Upload, UserRound,
} from 'lucide-vue-next'
import { saveProfileForm, getProfileForm } from '../api/profile'
import { getPhotoInfo, uploadPhotoFile } from '../api/resumeGeneration'
import ProfileResumeImportDialog from './ProfileResumeImportDialog.vue'
import type { ProfileEducationEntry, ProfileExtraEntry, ProfileFormSave, ProfileSocialEntry, ResumeImportFormDraft } from '../types'

const props = defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{ (e: 'update:modelValue', v: boolean): void; (e: 'saved'): void }>()

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

/** 4 步：身份 → 教育 → 经历 → 能力，轻重分离 */
const STEPS = [
  { key: 'basic', label: '基本信息', sub: '身份·头像·社交' },
  { key: 'education', label: '教育与奖项', sub: '学历·荣誉' },
  { key: 'experience', label: '实践经历', sub: '实习·项目' },
  { key: 'ability', label: '能力与方向', sub: '技能·目标·软性' },
]

const BASIC_FIELDS = [
  { key: 'name', label: '姓名', required: true, placeholder: '如：栗子' },
  { key: 'phone', label: '手机', required: true, placeholder: '如：19823342343' },
  { key: 'email', label: '邮箱', required: true, placeholder: '如：2378166881@qq.com' },
  { key: 'location', label: '所在地点', required: true, placeholder: '如：北京' },
  { key: 'gender', label: '性别', required: false, placeholder: '如：男' },
  { key: 'birthday', label: '出生日期', required: false, placeholder: '如：2004-04-08' },
  { key: 'nationality', label: '国籍', required: false, placeholder: '如：中国' },
  { key: 'hometown', label: '家乡', required: false, placeholder: '如：北京' },
]

const DEGREES = ['高中', '大专', '本科', '硕士', '博士']

const OTHER_CATEGORIES = [
  { value: 'interview_feedback', label: '面试反馈' },
  { value: 'soft', label: '软性信息' },
  { value: 'skill', label: '专业技能' },
  { value: 'target', label: '目标岗位' },
]

type ExtraDraft = ProfileExtraEntry & { _id: string; _seq: number }

const step = ref(1)
const saving = ref(false)
const avatarUploading = ref(false)
const avatarPreview = ref('')
const fileInput = ref<HTMLInputElement | null>(null)
const skillDraft = ref('')
const targetDraft = ref('')
const showOther = ref(false)
const fillOpen = ref(false)

const form = reactive({
  basic_info: {} as Record<string, string>,
  education: [] as ProfileEducationEntry[],
  awards: '',
  social: [] as ProfileSocialEntry[],
  experiences: [] as ExtraDraft[],
  skills: [] as string[],
  targets: [] as string[],
  soft: {
    personality: '',
    vision: '',
    disinterested: '',
    self_eval: '',
  },
  otherExtras: [] as ExtraDraft[],
})

let seq = 0
function withMeta(raw: ProfileExtraEntry, category: string): ExtraDraft {
  seq += 1
  return {
    exp_type: '',
    role: '',
    start: '',
    end: '',
    current: false,
    tech_stack: '',
    duty: '',
    achievement: '',
    ...raw,
    category,
    _id: `x${seq}`,
    _seq: seq,
  }
}

const internships = computed(() => form.experiences.filter((e) => e.category === 'internship'))
const projects = computed(() => form.experiences.filter((e) => e.category === 'project'))
const otherExtras = computed(() => form.otherExtras)

function removeExtra(id: string) {
  form.experiences = form.experiences.filter((e) => e._id !== id)
  form.otherExtras = form.otherExtras.filter((e) => e._id !== id)
}

const stepDone = computed(() => {
  const bi = form.basic_info
  return [
    Boolean((bi.name || '').trim()) && (Boolean((bi.phone || '').trim()) || Boolean((bi.email || '').trim())),
    form.education.some((e) => (e.school || '').trim()) || Boolean(form.awards.trim()),
    form.experiences.some((e) => (e.title || '').trim()),
    form.skills.length > 0
      || form.targets.length > 0
      || Object.values(form.soft).some((v) => (v || '').trim()),
  ]
})

const doneCount = computed(() => stepDone.value.filter(Boolean).length)

watch(() => props.modelValue, async (open) => {
  if (open) await load()
})

async function load() {
  step.value = 1
  skillDraft.value = ''
  targetDraft.value = ''
  showOther.value = false
  Object.assign(form, {
    basic_info: {},
    education: [],
    awards: '',
    social: [],
    experiences: [],
    skills: [],
    targets: [],
    soft: { personality: '', vision: '', disinterested: '', self_eval: '' },
    otherExtras: [],
  })
  try {
    const res = await getProfileForm()
    const d = res.data || {}
    form.basic_info = { ...(d.basic_info || {}) }
    form.education = (d.education || []).map((e) => ({ ...e }))
    form.awards = (d.awards || []).join('\n')
    form.social = (d.social || []).map((s) => ({ ...s }))
    hydrateExtra(d.extra || [])
  } catch {
    // 加载失败时保留当前表单，避免已填内容被清空
  }
  try {
    const photo = await getPhotoInfo()
    if (photo.data) avatarPreview.value = `${photo.data.url}?t=${Date.now()}`
  } catch {
    avatarPreview.value = ''
  }
}

/** 把 extra[] 拆成经历 / 技能 / 目标 / 软性 / 其他，供轻量 UI 编辑 */
function hydrateExtra(items: ProfileExtraEntry[]) {
  for (const raw of items) {
    const category = (raw.category || '').trim()
    if (category === 'internship' || category === 'project' || category === 'experience') {
      const expType = category === 'experience' ? (raw.exp_type || 'project') : category
      form.experiences.push(withMeta({ ...raw, exp_type: expType }, expType === 'internship' ? 'internship' : 'project'))
      continue
    }
    if (category === 'skill' && raw.title) {
      if (!form.skills.includes(raw.title)) form.skills.push(raw.title)
      continue
    }
    if (category === 'target' && raw.title) {
      if (!form.targets.includes(raw.title)) form.targets.push(raw.title)
      continue
    }
    if (category === 'soft') {
      const field = softFieldOf(raw.title)
      if (field && !form.soft[field]) {
        form.soft[field] = raw.content || ''
        continue
      }
    }
    form.otherExtras.push(withMeta(raw, category || 'soft'))
  }
}

function softFieldOf(title: string): 'personality' | 'vision' | 'disinterested' | 'self_eval' | '' {
  if (title === '性格特点') return 'personality'
  if (title === '职业愿景') return 'vision'
  if (title === '不感兴趣的方向') return 'disinterested'
  if (title === '自我评价') return 'self_eval'
  return ''
}

/** 向导一键填充：空字段优先写入，已有内容不覆盖（避免误清用户手填） */
function applyFillDraft(draft: ResumeImportFormDraft) {
  for (const [k, v] of Object.entries(draft.basic_info || {})) {
    const val = (v || '').trim()
    if (!val) continue
    const prev = (form.basic_info[k] || '').trim()
    if (!prev) form.basic_info[k] = val
  }
  if (!form.education.length && draft.education?.length) {
    form.education = draft.education.map((e) => ({ ...e }))
  }
  if (!form.awards.trim() && draft.awards?.trim()) {
    form.awards = draft.awards.trim()
  }
  for (const ext of draft.extra || []) {
    const category = (ext.category || '').trim()
    const title = (ext.title || '').trim()
    if (!title) continue
    if (category === 'internship' || category === 'project') {
      const exists = form.experiences.some(
        (e) => (e.title || '').trim() === title && e.category === category,
      )
      if (!exists) {
        form.experiences.push(
          withMeta({ ...ext, exp_type: category }, category === 'internship' ? 'internship' : 'project'),
        )
      }
      continue
    }
    if (category === 'skill' && !form.skills.includes(title)) {
      form.skills.push(title)
      continue
    }
    if (category === 'target' && !form.targets.includes(title)) {
      form.targets.push(title)
    }
  }
  if (!form.soft.self_eval.trim() && (draft.summary || '').trim()) {
    form.soft.self_eval = draft.summary!.trim()
  }
  step.value = 1
}

/** 保存时把轻量字段拼回后端 extra[]，保持接口契约不变 */
function buildExtra(): ProfileExtraEntry[] {
  const list: ProfileExtraEntry[] = []

  for (const e of form.experiences) {
    const title = (e.title || '').trim()
    if (!title) continue
    const category = e.category === 'internship' ? 'internship' : 'project'
    list.push({
      category,
      title,
      content: e.content || '',
      exp_type: category,
      role: e.role || '',
      start: e.start || '',
      end: e.end || '',
      current: Boolean(e.current),
      tech_stack: e.tech_stack || '',
      duty: e.duty || '',
      achievement: e.achievement || '',
    })
  }

  for (const s of form.skills) {
    const title = s.trim()
    if (title) list.push({ category: 'skill', title, content: '' })
  }
  for (const t of form.targets) {
    const title = t.trim()
    if (title) list.push({ category: 'target', title, content: '' })
  }

  const softMap: Array<[string, string]> = [
    ['性格特点', form.soft.personality],
    ['职业愿景', form.soft.vision],
    ['不感兴趣的方向', form.soft.disinterested],
    ['自我评价', form.soft.self_eval],
  ]
  for (const [title, content] of softMap) {
    const text = (content || '').trim()
    if (text) list.push({ category: 'soft', title, content: text })
  }

  for (const e of form.otherExtras) {
    const title = (e.title || '').trim()
    if (!title) continue
    list.push({
      category: e.category || 'soft',
      title,
      content: e.content || '',
    })
  }

  return list
}

function addEducation() {
  form.education.push({ school: '', degree: '', major: '', courses: '', start: '', end: '', gpa: '' })
}

function emptyExperience(category: 'internship' | 'project'): ExtraDraft {
  return withMeta(
    {
      category,
      title: '',
      content: '',
      exp_type: category,
      role: '',
      start: '',
      end: '',
      current: false,
      tech_stack: '',
      duty: '',
      achievement: '',
    },
    category,
  )
}

function addExperience(category: 'internship' | 'project') {
  form.experiences.push(emptyExperience(category))
}

function addOther() {
  form.otherExtras.push(withMeta({ category: 'interview_feedback', title: '', content: '' }, 'interview_feedback'))
  showOther.value = true
}

function pushTag(list: string[], kind: 'skill' | 'target') {
  const draft = kind === 'skill' ? skillDraft : targetDraft
  const val = draft.value.trim()
  if (!val) return
  if (list.includes(val)) {
    ElMessage.warning(`${kind === 'skill' ? '技能' : '目标岗位'}已存在`)
    return
  }
  list.push(val)
  draft.value = ''
}

function next() {
  if (step.value === 1) {
    const required = ['name', 'phone', 'email']
    const missing = required.filter((k) => !(form.basic_info[k] || '').trim())
    if (missing.length) {
      ElMessage.warning('请先填写必填的基本信息（姓名 / 手机 / 邮箱）')
      return
    }
  }
  step.value = Math.min(STEPS.length, step.value + 1)
}

async function onAvatarChange(ev: Event) {
  const input = ev.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  avatarUploading.value = true
  try {
    const res = await uploadPhotoFile(file)
    avatarPreview.value = `${res.data.url}?t=${Date.now()}`
    ElMessage.success('头像已上传')
  } catch {
    ElMessage.error('上传失败（支持 JPG/PNG/WEBP）')
  } finally {
    avatarUploading.value = false
    input.value = ''
  }
}

function clearAvatar() {
  avatarPreview.value = ''
}

function reset() {
  step.value = 1
}

async function saveAll() {
  saving.value = true
  try {
    await saveProfileForm({
      basic_info: form.basic_info,
      education: form.education.map((e) => ({ ...e })),
      awards: form.awards,
      social: form.social.map((s) => ({ ...s })),
      extra: buildExtra(),
    } as ProfileFormSave)
    ElMessage.success('画像已保存')
    visible.value = false
    emit('saved')
  } catch (e: any) {
    const detail = e?.response?.data?.detail
    ElMessage.error(typeof detail === 'string' ? detail : '保存失败，请重试')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
/* ---- 步骤条：4 列更舒展 ---- */
.wiz-steps {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
  margin-bottom: var(--space-5);
}
.wiz-fill-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin: -8px 0 16px;
  padding: 8px 12px;
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg-soft, var(--color-bg));
}
.wiz-fill-hint {
  font-size: 12px;
  color: var(--color-text-secondary, var(--color-gray-500));
}
.wiz-step {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 14px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg);
  cursor: pointer;
  text-align: left;
  transition: all var(--duration-fast) var(--ease-default);
}
.wiz-step:hover { border-color: var(--color-accent-300); }
.wiz-step.active {
  border-color: var(--color-accent-600);
  background: var(--color-accent-50);
  box-shadow: 0 0 0 1px var(--color-accent-600) inset;
}
.wiz-step.done { border-color: var(--color-accent-200); }
.wiz-step-no {
  flex-shrink: 0;
  display: grid;
  place-items: center;
  width: 26px;
  height: 26px;
  border-radius: 50%;
  font-size: var(--text-xs);
  font-weight: var(--weight-semibold);
  color: var(--color-text-secondary);
  background: var(--color-gray-100);
}
.wiz-step.active .wiz-step-no { background: var(--color-accent-600); color: #fff; }
.wiz-step-no.done { background: var(--color-success-600); color: #fff; }
.wiz-step-info b { font-size: var(--text-sm); color: var(--color-text-primary); display: block; }
.wiz-step-info small { font-size: var(--text-2xs); color: var(--color-text-tertiary); }

/* ---- 正文 ---- */
.wiz-body {
  max-height: 56vh;
  overflow-y: auto;
  padding: var(--space-1) var(--space-2) var(--space-3);
}
.sec-head {
  margin: var(--space-4) 0 var(--space-3);
}
.sec-head.tight { margin-top: var(--space-5); }
.sec-head:first-child { margin-top: 0; }
.sec-head h3 {
  margin: 0;
  font-size: var(--text-base);
  font-weight: var(--weight-semibold);
  color: var(--color-text-primary);
}
.sec-head p {
  margin: 4px 0 0;
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}

.wiz-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-3) var(--space-4);
}
.wiz-grid.two { grid-template-columns: 1fr 1fr; }
.wiz-field { display: flex; flex-direction: column; gap: 6px; margin-bottom: var(--space-3); }
.wiz-field label { font-size: var(--text-xs); color: var(--color-text-secondary); }
.wiz-field label.req { font-weight: var(--weight-medium); }
.req-mark { color: var(--color-danger-600); margin-left: 2px; }

.wiz-card {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-4);
  margin-bottom: var(--space-3);
  background: var(--color-bg-elevated);
}
.wiz-card.compact { padding: var(--space-3); }
.wiz-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-2);
}
.idx {
  font-family: var(--font-display);
  font-size: var(--text-xs);
  letter-spacing: 0.06em;
  color: var(--color-text-tertiary);
}

.wiz-add {
  display: inline-flex;
  align-items: center;
  padding: 8px 14px;
  border: 1px dashed var(--color-accent-400);
  border-radius: var(--radius-md);
  background: transparent;
  color: var(--color-accent-600);
  font-size: var(--text-sm);
  font-weight: var(--weight-medium);
  cursor: pointer;
  margin-bottom: var(--space-2);
}
.wiz-add:hover { background: var(--color-accent-50); }
.wiz-add.ghost {
  border-color: var(--color-border-strong);
  color: var(--color-text-secondary);
}
.wiz-add.ghost:hover {
  border-color: var(--color-accent-400);
  color: var(--color-accent-600);
  background: var(--color-accent-50);
}

.period-end { display: flex; align-items: center; gap: var(--space-2); width: 100%; }

.empty-slot {
  padding: var(--space-4);
  border: 1px dashed var(--color-border-strong);
  border-radius: var(--radius-md);
  color: var(--color-text-tertiary);
  font-size: var(--text-sm);
  text-align: center;
  margin-bottom: var(--space-3);
}

/* ---- 头像行（轻量） ---- */
.avatar-row {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  padding: var(--space-3) 0;
}
.avatar-preview {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  overflow: hidden;
  display: grid;
  place-items: center;
  background: var(--color-gray-100);
  color: var(--color-text-tertiary);
  flex-shrink: 0;
  border: 1px solid var(--color-border);
}
.avatar-preview:not(.empty) img { width: 100%; height: 100%; object-fit: cover; }
.avatar-actions { display: flex; align-items: center; gap: var(--space-2); flex-wrap: wrap; }
.avatar-hint { font-size: var(--text-xs); color: var(--color-text-tertiary); }

/* ---- 社交账号行 ---- */
.row-line {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-2);
}
.row-platform { flex: 0 0 160px; }
.row-account { flex: 1; }
.row-del {
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--color-text-tertiary);
  cursor: pointer;
}
.row-del:hover { color: var(--color-danger-600); background: var(--color-danger-50); }

/* ---- 技能 / 目标 标签流 ---- */
.tag-input {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  min-height: 42px;
  padding: 8px 10px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg-elevated);
  margin-bottom: var(--space-2);
}
.tag-draft {
  flex: 1;
  min-width: 180px;
}
.tag-draft :deep(.el-input__wrapper) {
  box-shadow: none;
  background: transparent;
}

/* ---- 软性信息 ---- */
.soft-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-3) var(--space-4);
}
.soft-grid .span-2 { grid-column: 1 / -1; }

.fold-toggle {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin: var(--space-3) 0 var(--space-2);
  padding: 4px 0;
  border: none;
  background: transparent;
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
  cursor: pointer;
}
.fold-toggle:hover { color: var(--color-accent-600); }
.other-list { margin-top: var(--space-2); }

/* ---- 底栏 ---- */
.wiz-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}
.wiz-progress { display: flex; align-items: baseline; gap: var(--space-3); }
.done-count { font-size: var(--text-sm); font-weight: var(--weight-medium); color: var(--color-accent-600); }
.wiz-req { font-size: var(--text-xs); color: var(--color-text-tertiary); }
.wiz-foot-actions { display: flex; gap: var(--space-2); }
</style>
