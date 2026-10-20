<template>
  <el-dialog
    v-model="visible"
    :title="mode === 'fill' ? '从简历一键填充' : '导入简历到个人画像'"
    width="820px"
    :append-to-body="true"
    :close-on-click-modal="false"
    class="resume-import-dialog"
    @closed="reset"
  >
    <!-- 选择来源 -->
    <template v-if="stage === 'upload'">
      <p class="ri-hint">
        {{ mode === 'fill'
          ? '识别结果会先填入向导表单，你可在各步骤继续修改，最后点「完成」保存。'
          : '可上传简历文件，或直接选简历库已有文档。识别结果仅作草稿，需你逐项确认后才会写入画像。' }}
      </p>

      <el-radio-group v-model="source" class="ri-source">
        <el-radio-button value="upload">上传文件</el-radio-button>
        <el-radio-button value="library">从简历库选择</el-radio-button>
      </el-radio-group>

      <div
        v-if="source === 'upload'"
        class="ri-drop"
        :class="{ over: dragOver, busy: loading }"
        @dragover.prevent="dragOver = true"
        @dragleave.prevent="dragOver = false"
        @drop.prevent="onDrop"
        @click="fileInput?.click()"
      >
        <input
          ref="fileInput"
          type="file"
          accept=".pdf,.docx,.txt,.md"
          hidden
          @change="onFileChange"
        />
        <UploadCloud :size="36" class="ri-drop-icon" />
        <p class="ri-drop-title">{{ loading ? '正在识别简历信息…' : '点击选择或拖入简历文件' }}</p>
        <p class="ri-drop-sub">支持 PDF / DOCX / TXT / MD，单个文件不超过 20MB</p>
      </div>

      <div v-else class="ri-lib">
        <SkeletonLoader v-if="libLoading" variant="card" :lines="3" />
        <el-empty v-else-if="!libDocs.length" description="简历库暂无文档，可先上传或到简历工作台导入" :image-size="60" />
        <div v-else class="ri-lib-list">
          <button
            v-for="d in libDocs"
            :key="d.id"
            type="button"
            class="ri-lib-item"
            :class="{ active: selectedDocId === d.id }"
            @click="selectedDocId = d.id"
          >
            <span class="ri-lib-title">{{ d.title }}</span>
            <span class="ri-lib-meta">{{ d.source || 'upload' }} · {{ d.updated_at?.slice(0, 10) }}</span>
          </button>
        </div>
        <el-button
          type="primary"
          class="ri-lib-go"
          :loading="loading"
          :disabled="!selectedDocId"
          @click="onPreviewFromLibrary"
        >
          识别这份简历
        </el-button>
      </div>

      <el-alert
        v-if="uploadError"
        type="error"
        :title="uploadError"
        show-icon
        :closable="false"
        class="ri-alert"
      />
    </template>

    <!-- 确认阶段 -->
    <template v-else>
      <div class="ri-bar">
        <div class="ri-bar-text">
          <span class="ri-file">{{ preview?.filename }}</span>
          <span class="ri-meta">已识别 {{ totalCount }} 项 · 请核对后确认</span>
        </div>
        <el-button text size="small" @click="stage = 'upload'">重新上传</el-button>
      </div>

      <el-alert
        v-for="(w, i) in warnings"
        :key="i"
        type="warning"
        :title="w"
        show-icon
        :closable="false"
        class="ri-alert"
      />

      <!-- 基本信息 -->
      <section v-if="basicRows.length" class="ri-sec">
        <header class="ri-sec-head">
          <el-checkbox
            :model-value="basicRows.every((r) => r.checked)"
            :indeterminate="basicRows.some((r) => r.checked) && !basicRows.every((r) => r.checked)"
            @change="toggleAll(basicRows, $event)"
          >
            <b>基本信息</b>
          </el-checkbox>
          <span class="ri-sec-count">{{ basicRows.filter((r) => r.checked).length }}/{{ basicRows.length }}</span>
        </header>
        <div v-for="row in basicRows" :key="row.key" class="ri-row" :class="{ off: !row.checked }">
          <el-checkbox v-model="row.checked" class="ri-check" />
          <div class="ri-row-body">
            <div class="ri-row-main">
              <span class="ri-label">{{ row.label }}</span>
              <el-input v-model="row.value" size="small" class="ri-input" :disabled="!row.checked" />
              <el-tag v-if="row.confidence < 0.6" size="small" type="warning">存疑</el-tag>
              <el-tag v-else-if="row.conflict" size="small" type="info">覆盖已有</el-tag>
            </div>
            <div v-if="row.quote" class="ri-quote">简历原文：{{ row.quote }}</div>
            <div v-if="row.conflict" class="ri-conflict">当前画像：{{ row.conflict }}</div>
          </div>
        </div>
      </section>

      <!-- 自我评价 -->
      <section v-if="summaryText || summaryQuote" class="ri-sec">
        <header class="ri-sec-head">
          <el-checkbox v-model="summaryChecked"><b>自我评价</b></el-checkbox>
        </header>
        <div class="ri-row" :class="{ off: !summaryChecked }">
          <div class="ri-row-body">
            <el-input
              v-model="summaryText"
              type="textarea"
              :rows="3"
              :disabled="!summaryChecked"
              placeholder="自我评价 / 个人简介"
            />
            <div v-if="summaryQuote" class="ri-quote">简历原文：{{ summaryQuote }}</div>
          </div>
        </div>
      </section>

      <!-- 教育经历 -->
      <section v-if="eduRows.length" class="ri-sec">
        <header class="ri-sec-head">
          <el-checkbox
            :model-value="eduRows.every((r) => r.checked)"
            :indeterminate="eduRows.some((r) => r.checked) && !eduRows.every((r) => r.checked)"
            @change="toggleAll(eduRows, $event)"
          >
            <b>教育经历</b>
          </el-checkbox>
          <span class="ri-sec-count">{{ eduRows.filter((r) => r.checked).length }}/{{ eduRows.length }}</span>
        </header>
        <div v-for="row in eduRows" :key="row.uid" class="ri-row" :class="{ off: !row.checked }">
          <el-checkbox v-model="row.checked" class="ri-check" />
          <div class="ri-row-body">
            <div class="ri-row-main wrap">
              <el-input v-model="row.data.school" size="small" class="ri-input w-school" placeholder="学校" :disabled="!row.checked" />
              <el-input v-model="row.data.degree" size="small" class="ri-input w-sm" placeholder="学历" :disabled="!row.checked" />
              <el-input v-model="row.data.major" size="small" class="ri-input w-sm" placeholder="专业" :disabled="!row.checked" />
              <el-input v-model="row.data.gpa" size="small" class="ri-input w-xs" placeholder="GPA" :disabled="!row.checked" />
              <el-input v-model="row.data.start" size="small" class="ri-input w-xs" placeholder="开始" :disabled="!row.checked" />
              <el-input v-model="row.data.end" size="small" class="ri-input w-xs" placeholder="结束" :disabled="!row.checked" />
            </div>
            <el-input
              v-model="row.data.courses"
              size="small"
              type="textarea"
              :rows="2"
              :disabled="!row.checked"
              placeholder="主修课程（可选）"
            />
            <div v-if="row.data.quote" class="ri-quote">简历原文：{{ row.data.quote }}</div>
          </div>
        </div>
      </section>

      <!-- 实习 / 项目 -->
      <section v-if="expRows.length" class="ri-sec">
        <header class="ri-sec-head">
          <el-checkbox
            :model-value="expRows.every((r) => r.checked)"
            :indeterminate="expRows.some((r) => r.checked) && !expRows.every((r) => r.checked)"
            @change="toggleAll(expRows, $event)"
          >
            <b>实习 / 项目经历</b>
          </el-checkbox>
          <span class="ri-sec-count">{{ expRows.filter((r) => r.checked).length }}/{{ expRows.length }}</span>
        </header>
        <div v-for="row in expRows" :key="row.uid" class="ri-row" :class="{ off: !row.checked }">
          <el-checkbox v-model="row.checked" class="ri-check" />
          <div class="ri-row-body">
            <div class="ri-row-main wrap">
              <el-tag size="small" :type="row.data.exp_type === 'project' ? 'success' : 'info'">
                {{ row.data.exp_type === 'project' ? '项目' : '实习' }}
              </el-tag>
              <el-input v-model="row.data.company" size="small" class="ri-input w-school" placeholder="公司 / 项目名" :disabled="!row.checked" />
              <el-input v-model="row.data.role" size="small" class="ri-input w-sm" placeholder="岗位 / 角色" :disabled="!row.checked" />
              <el-input v-model="row.data.start" size="small" class="ri-input w-xs" placeholder="开始" :disabled="!row.checked" />
              <el-input v-model="row.data.end" size="small" class="ri-input w-xs" placeholder="结束" :disabled="!row.checked" />
            </div>
            <el-input
              v-model="row.data.duty"
              size="small"
              type="textarea"
              :rows="2"
              :disabled="!row.checked"
              placeholder="职责描述"
            />
            <el-input
              v-model="row.data.achievement"
              size="small"
              type="textarea"
              :rows="2"
              :disabled="!row.checked"
              placeholder="成果（可选）"
            />
            <div v-if="row.data.quote" class="ri-quote">简历原文：{{ row.data.quote }}</div>
          </div>
        </div>
      </section>

      <!-- 技能 -->
      <section v-if="skillRows.length" class="ri-sec">
        <header class="ri-sec-head">
          <el-checkbox
            :model-value="skillRows.every((r) => r.checked)"
            :indeterminate="skillRows.some((r) => r.checked) && !skillRows.every((r) => r.checked)"
            @change="toggleAll(skillRows, $event)"
          >
            <b>技能</b>
          </el-checkbox>
          <span class="ri-sec-count">{{ skillRows.filter((r) => r.checked).length }}/{{ skillRows.length }}</span>
        </header>
        <div class="ri-tags">
          <el-check-tag
            v-for="row in skillRows"
            :key="row.uid"
            :checked="row.checked"
            class="ri-skill-tag"
            @change="row.checked = $event"
          >
            {{ row.data.name }}
            <span v-if="row.data.quote" class="ri-tag-quote" :title="row.data.quote">源</span>
          </el-check-tag>
        </div>
      </section>

      <!-- 奖项 -->
      <section v-if="awardRows.length" class="ri-sec">
        <header class="ri-sec-head">
          <el-checkbox
            :model-value="awardRows.every((r) => r.checked)"
            :indeterminate="awardRows.some((r) => r.checked) && !awardRows.every((r) => r.checked)"
            @change="toggleAll(awardRows, $event)"
          >
            <b>奖项与荣誉</b>
          </el-checkbox>
          <span class="ri-sec-count">{{ awardRows.filter((r) => r.checked).length }}/{{ awardRows.length }}</span>
        </header>
        <div v-for="row in awardRows" :key="row.uid" class="ri-row compact" :class="{ off: !row.checked }">
          <el-checkbox v-model="row.checked" class="ri-check" />
          <el-input v-model="row.text" size="small" :disabled="!row.checked" />
        </div>
      </section>

      <el-alert
        v-if="applyError"
        type="error"
        :title="applyError"
        show-icon
        :closable="false"
        class="ri-alert"
      />
    </template>

    <template #footer>
      <template v-if="stage === 'upload'">
        <el-button @click="visible = false">取消</el-button>
        <el-button
          v-if="source === 'upload'"
          type="primary"
          :loading="loading"
          @click="fileInput?.click()"
        >
          选择简历文件
        </el-button>
      </template>
      <template v-else>
        <span class="ri-foot-note">
          已选 {{ selectedCount }} 项 ·
          {{ mode === 'fill' ? '填入向导后仍可修改' : '确认后写入个人画像' }}
        </span>
        <el-button @click="visible = false">{{ mode === 'fill' ? '取消' : '暂不导入' }}</el-button>
        <el-button
          type="primary"
          :loading="applying"
          :disabled="selectedCount === 0"
          @click="mode === 'fill' ? onFill() : onApply()"
        >
          {{ mode === 'fill' ? '填入表单' : `确认导入${selectedCount ? ` ${selectedCount} 项` : ''}` }}
        </el-button>
      </template>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { UploadCloud } from 'lucide-vue-next'
import {
  applyResumeImport,
  previewResumeImport,
  previewResumeImportFromLibrary,
} from '../api/profile'
import { listResumeDocs } from '../api/resumeLibrary'
import SkeletonLoader from './SkeletonLoader.vue'
import type {
  ResumeImportApplyRequest,
  ResumeImportEducation,
  ResumeImportExperience,
  ResumeImportFormDraft,
  ResumeImportPreview,
  ResumeImportSkill,
} from '../types'

const props = withDefaults(
  defineProps<{ modelValue: boolean; mode?: 'apply' | 'fill' }>(),
  { mode: 'apply' },
)
const emit = defineEmits<{
  (e: 'update:modelValue', v: boolean): void
  (e: 'imported', written: Record<string, number>): void
  (e: 'filled', draft: ResumeImportFormDraft): void
}>()

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const source = ref<'upload' | 'library'>('upload')
const libDocs = ref<{ id: number; title: string; source?: string; updated_at?: string }[]>([])
const libLoading = ref(false)
const selectedDocId = ref<number | null>(null)

const BASIC_LABELS: Record<string, string> = {
  name: '姓名',
  phone: '手机',
  email: '邮箱',
  location: '所在地点',
  gender: '性别',
  birthday: '出生日期',
  nationality: '国籍',
  hometown: '家乡',
}

type CheckRow<T> = { uid: string; checked: boolean; data: T }

const stage = ref<'upload' | 'confirm'>('upload')
const loading = ref(false)
const applying = ref(false)
const dragOver = ref(false)
const uploadError = ref('')
const applyError = ref('')
const fileInput = ref<HTMLInputElement | null>(null)
const preview = ref<ResumeImportPreview | null>(null)

const basicRows = ref<{ key: string; label: string; value: string; quote: string; confidence: number; conflict: string; checked: boolean }[]>([])
const summaryChecked = ref(false)
const summaryText = ref('')
const summaryQuote = ref('')
const eduRows = ref<CheckRow<ResumeImportEducation>[]>([])
const expRows = ref<CheckRow<ResumeImportExperience>[]>([])
const skillRows = ref<CheckRow<ResumeImportSkill>[]>([])
const awardRows = ref<{ uid: string; checked: boolean; text: string }[]>([])

const warnings = computed(() => preview.value?.extract.warnings || [])

const totalCount = computed(
  () =>
    basicRows.value.length +
    (summaryChecked.value || summaryText.value ? 1 : 0) +
    eduRows.value.length +
    expRows.value.length +
    skillRows.value.length +
    awardRows.value.length,
)

const selectedCount = computed(() => {
  let n = basicRows.value.filter((r) => r.checked).length
  if (summaryChecked.value && summaryText.value.trim()) n += 1
  n += eduRows.value.filter((r) => r.checked).length
  n += expRows.value.filter((r) => r.checked).length
  n += skillRows.value.filter((r) => r.checked).length
  n += awardRows.value.filter((r) => r.checked && r.text.trim()).length
  return n
})

watch(visible, (v) => {
  if (v) {
    if (props.mode === 'fill') source.value = 'upload'
    void loadLibraryDocs()
  } else {
    reset()
  }
})

function reset() {
  stage.value = 'upload'
  loading.value = false
  applying.value = false
  dragOver.value = false
  uploadError.value = ''
  applyError.value = ''
  preview.value = null
  basicRows.value = []
  summaryChecked.value = false
  summaryText.value = ''
  summaryQuote.value = ''
  eduRows.value = []
  expRows.value = []
  skillRows.value = []
  awardRows.value = []
  source.value = 'upload'
  selectedDocId.value = null
  if (fileInput.value) fileInput.value.value = ''
}

async function loadLibraryDocs() {
  libLoading.value = true
  try {
    libDocs.value = await listResumeDocs()
  } catch {
    libDocs.value = []
  } finally {
    libLoading.value = false
  }
}

async function onPreviewFromLibrary() {
  if (!selectedDocId.value) return
  uploadError.value = ''
  applyError.value = ''
  loading.value = true
  try {
    const res = await previewResumeImportFromLibrary(selectedDocId.value)
    preview.value = res.data
    fillRows(res.data)
    stage.value = 'confirm'
  } catch (err) {
    uploadError.value = extractError(err, '识别失败，请确认简历库文档含可读正文')
  } finally {
    loading.value = false
  }
}

function extractError(err: unknown, fallback: string): string {
  const anyErr = err as {
    response?: { data?: { detail?: string | { msg?: string }[] } }
    message?: string
  }
  const detail = anyErr?.response?.data?.detail
  if (typeof detail === 'string' && detail.trim()) return detail
  if (Array.isArray(detail) && detail.length) {
    return detail.map((d) => d?.msg || '').filter(Boolean).join('; ') || fallback
  }
  if (anyErr?.message && /timeout|Network Error/i.test(anyErr.message)) {
    return anyErr.message.includes('timeout')
      ? '识别超时，请稍后重试或换用文本更清晰的简历'
      : '网络异常，请检查后端服务是否可用'
  }
  return fallback
}

function onFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (file) void startPreview(file)
  input.value = ''
}

function onDrop(e: DragEvent) {
  dragOver.value = false
  const file = e.dataTransfer?.files?.[0]
  if (file) void startPreview(file)
}

async function startPreview(file: File) {
  uploadError.value = ''
  applyError.value = ''
  loading.value = true
  try {
    const res = await previewResumeImport(file)
    preview.value = res.data
    fillRows(res.data)
    stage.value = 'confirm'
  } catch (err) {
    uploadError.value = extractError(err, '简历识别失败，请确认文件为可选中文字的 PDF/Word')
  } finally {
    loading.value = false
  }
}

function fillRows(p: ResumeImportPreview) {
  const ex = p.extract
  basicRows.value = ex.basic_fields.map((f) => ({
    key: f.key,
    label: BASIC_LABELS[f.key] || f.key,
    value: f.value,
    quote: f.quote || '',
    confidence: f.confidence ?? 0.8,
    conflict: p.existing_basic[f.key] && p.existing_basic[f.key] !== f.value ? p.existing_basic[f.key] : '',
    checked: (f.confidence ?? 0.8) >= 0.6,
  }))

  summaryText.value = ex.summary || ''
  summaryQuote.value = ex.summary_quote || ''
  summaryChecked.value = Boolean(ex.summary)

  eduRows.value = ex.education.map((e, i) => ({
    uid: `edu-${i}`,
    checked: (e.confidence ?? 0.7) >= 0.55,
    data: { ...e },
  }))
  expRows.value = ex.experiences.map((e, i) => ({
    uid: `exp-${i}`,
    checked: (e.confidence ?? 0.7) >= 0.55,
    data: { ...e },
  }))
  skillRows.value = ex.skills.map((s, i) => ({
    uid: `skill-${i}`,
    checked: (s.confidence ?? 0.7) >= 0.55,
    data: { ...s },
  }))
  awardRows.value = ex.awards.map((a, i) => ({
    uid: `award-${i}`,
    checked: true,
    text: a,
  }))
}

function toggleAll(rows: { checked: boolean }[], val: string | number | boolean) {
  const on = Boolean(val)
  rows.forEach((r) => {
    r.checked = on
  })
}

async function onApply() {
  if (!preview.value || selectedCount.value === 0) return
  applying.value = true
  applyError.value = ''
  const payload: ResumeImportApplyRequest = {
    source_filename: preview.value.filename,
    basic_fields: basicRows.value
      .filter((r) => r.checked && r.value.trim())
      .map((r) => ({ key: r.key, value: r.value.trim(), quote: r.quote, confidence: r.confidence })),
    summary: summaryChecked.value ? summaryText.value.trim() : '',
    summary_quote: summaryChecked.value ? summaryQuote.value : '',
    education: eduRows.value.filter((r) => r.checked).map((r) => r.data),
    experiences: expRows.value.filter((r) => r.checked).map((r) => r.data),
    skills: skillRows.value.filter((r) => r.checked && r.data.name.trim()).map((r) => r.data),
    awards: awardRows.value.filter((r) => r.checked && r.text.trim()).map((r) => r.text.trim()),
  }
  try {
    const res = await applyResumeImport(payload)
    ElMessage.success(res.data.message || '已写入个人画像')
    emit('imported', res.data.written || {})
    visible.value = false
  } catch (err) {
    applyError.value = extractError(err, '写入画像失败，请稍后重试')
  } finally {
    applying.value = false
  }
}

/** 向导一键填充：把勾选项映射为表单草稿，不调用 apply */
function onFill() {
  if (selectedCount.value === 0) return
  const basic_info: Record<string, string> = {}
  for (const r of basicRows.value) {
    if (r.checked && r.value.trim()) basic_info[r.key] = r.value.trim()
  }
  const draft: ResumeImportFormDraft = {
    basic_info,
    education: eduRows.value.filter((r) => r.checked).map((r) => ({
      school: r.data.school,
      degree: r.data.degree,
      major: r.data.major,
      courses: r.data.courses,
      start: r.data.start,
      end: r.data.end,
      gpa: r.data.gpa,
    })),
    awards: awardRows.value
      .filter((r) => r.checked && r.text.trim())
      .map((r) => r.text.trim())
      .join('\n'),
    social: [],
    extra: [
      ...expRows.value
        .filter((r) => r.checked)
        .map((r) => ({
          category: r.data.exp_type === 'project' ? 'project' : 'internship',
          exp_type: r.data.exp_type,
          title: r.data.company || r.data.role,
          role: r.data.role,
          start: r.data.start,
          end: r.data.end,
          current: r.data.current,
          tech_stack: r.data.tech_stack,
          duty: r.data.duty,
          achievement: r.data.achievement,
          content: '',
        })),
      ...skillRows.value
        .filter((r) => r.checked && r.data.name.trim())
        .map((r) => ({
          category: 'skill',
          title: r.data.name.trim(),
          content: r.data.notes || r.data.level || '',
        })),
    ],
    summary: summaryChecked.value ? summaryText.value.trim() : '',
    warnings: preview.value?.extract.warnings || [],
    confidence: preview.value?.extract.confidence,
  }
  emit('filled', draft)
  ElMessage.success('已填入向导，请核对后点「完成」保存')
  visible.value = false
}
</script>

<style scoped>
.ri-hint {
  margin: 0 0 16px;
  color: var(--el-text-color-regular);
  line-height: 1.7;
  font-size: 13px;
}
.ri-hint b {
  color: var(--el-color-primary);
  font-weight: 600;
}
.ri-source {
  margin-bottom: 14px;
}
.ri-lib {
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 12px;
  padding: 12px;
  background: var(--el-fill-color-lighter);
}
.ri-lib-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 260px;
  overflow: auto;
  margin-bottom: 12px;
}
.ri-lib-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border: 1px solid transparent;
  border-radius: 8px;
  background: var(--el-bg-color);
  cursor: pointer;
  text-align: left;
}
.ri-lib-item:hover {
  border-color: var(--el-color-primary-light-5);
}
.ri-lib-item.active {
  border-color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
}
.ri-lib-title {
  font-weight: 600;
  font-size: 13px;
  color: var(--el-text-color-primary);
}
.ri-lib-meta {
  font-size: 11px;
  color: var(--el-text-color-secondary);
  flex-shrink: 0;
}
.ri-lib-go {
  width: 100%;
}
.ri-drop {
  border: 1.5px dashed var(--el-border-color);
  border-radius: 12px;
  padding: 40px 20px;
  text-align: center;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
  background: var(--el-fill-color-lighter);
}
.ri-drop:hover,
.ri-drop.over {
  border-color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
}
.ri-drop.busy {
  pointer-events: none;
  opacity: 0.75;
}
.ri-drop-icon {
  color: var(--el-color-primary);
  margin-bottom: 8px;
}
.ri-drop-title {
  margin: 0 0 6px;
  font-size: 15px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}
.ri-drop-sub {
  margin: 0;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.ri-alert {
  margin-top: 12px;
}
.ri-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  padding: 10px 12px;
  background: var(--el-fill-color-light);
  border-radius: 8px;
}
.ri-bar-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}
.ri-file {
  font-weight: 600;
  font-size: 13px;
  color: var(--el-text-color-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ri-meta {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.ri-sec {
  margin-top: 18px;
}
.ri-sec-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
  padding-bottom: 6px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}
.ri-sec-count {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.ri-row {
  display: flex;
  gap: 8px;
  padding: 10px 8px;
  border-radius: 8px;
  transition: opacity 0.15s;
}
.ri-row:hover {
  background: var(--el-fill-color-lighter);
}
.ri-row.off {
  opacity: 0.45;
}
.ri-row.compact {
  align-items: center;
  padding: 6px 8px;
}
.ri-check {
  margin-top: 4px;
  flex-shrink: 0;
}
.ri-row-body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.ri-row-main {
  display: flex;
  align-items: center;
  gap: 8px;
}
.ri-row-main.wrap {
  flex-wrap: wrap;
}
.ri-label {
  flex-shrink: 0;
  width: 64px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.ri-input {
  flex: 1;
  min-width: 0;
}
.ri-input.w-school {
  flex: 1.4;
  min-width: 120px;
}
.ri-input.w-sm {
  flex: 1;
  min-width: 80px;
}
.ri-input.w-xs {
  flex: 0.7;
  min-width: 64px;
}
.ri-quote {
  font-size: 11px;
  color: var(--el-text-color-secondary);
  line-height: 1.5;
  padding: 4px 8px;
  background: var(--el-fill-color);
  border-radius: 4px;
}
.ri-conflict {
  font-size: 11px;
  color: var(--el-color-warning);
}
.ri-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.ri-skill-tag {
  cursor: pointer;
}
.ri-tag-quote {
  margin-left: 4px;
  font-size: 10px;
  opacity: 0.7;
}
.ri-foot-note {
  margin-right: 12px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
</style>
