<template>
  <div class="tailor-panel">
    <div class="tailor-toolbar">
      <div class="source-control">
        <span class="control-label">基础简历</span>
        <el-select v-model="sourceKey" class="source-select" placeholder="请选择基础简历" :loading="docsLoading">
          <el-option
            v-for="option in sourceOptions"
            :key="option.value"
            :label="option.label"
            :value="option.value"
          />
        </el-select>
      </div>

      <div class="mode-control">
        <span class="control-label">定制方式</span>
        <el-radio-group v-model="mode" size="small">
          <el-radio-button value="conservative">保守润色</el-radio-button>
          <el-radio-button value="focused">岗位重点</el-radio-button>
          <el-radio-button value="one_page">一页精简</el-radio-button>
        </el-radio-group>
      </div>

      <el-button
        type="primary"
        :loading="generating"
        :disabled="!canGenerate"
        @click="generate"
      >
        <Sparkles :size="16" style="margin-right: 6px" />
        生成岗位定制版
      </el-button>
    </div>

    <el-alert
      class="fact-guard"
      type="info"
      :closable="false"
      title="只调整已有事实的表达、顺序和重点"
      description="不会新增经历、公司、奖项、数字或成果；生成后请逐模块确认，再保存为新的简历版本。"
    />

    <el-alert
      v-if="errorMessage"
      type="error"
      :closable="true"
      :title="errorMessage"
      style="margin-bottom: 12px"
      @close="errorMessage = ''"
    />

    <div v-if="!session.jdAnalysis" class="empty-state">
      <FileSearch :size="30" />
      <p class="empty-title">请先完成 JD 分析</p>
      <p class="empty-desc">在左侧输入目标岗位 JD，岗位定制会根据分析结果调整已有简历。</p>
    </div>

    <div v-else-if="!sourceContent" class="empty-state">
      <FileText :size="30" />
      <p class="empty-title">请选择基础简历</p>
      <p class="empty-desc">可以选择当前分析中的简历，或从简历工作台选择一份已有简历。</p>
      <el-button size="small" plain type="primary" @click="router.push('/resume-library')">前往简历工作台</el-button>
    </div>

    <div v-else class="tailor-layout">
      <section class="resume-pane source-pane">
        <div class="pane-header">
          <div>
            <p class="pane-kicker">SOURCE</p>
            <h3>原简历</h3>
          </div>
          <el-tag size="small" type="info">{{ sourceContent.sections.length }} 个模块</el-tag>
        </div>
        <div class="resume-scroll">
          <article v-for="(section, i) in sourceContent.sections" :key="`source-${i}`" class="resume-section">
            <h4>{{ section.title }}</h4>
            <p class="section-content">{{ section.content }}</p>
          </article>
        </div>
      </section>

      <section class="resume-pane result-pane">
        <div class="pane-header">
          <div>
            <p class="pane-kicker">TAILORED</p>
            <h3>岗位定制稿</h3>
          </div>
          <div v-if="result" class="result-actions">
            <el-button size="small" :loading="generating" @click="generate">
              <RefreshCw :size="14" style="margin-right: 4px" />换个版本
            </el-button>
            <el-button size="small" type="primary" :loading="saving" @click="save">
              <Save :size="14" style="margin-right: 4px" />保存为新版本
            </el-button>
          </div>
        </div>

        <div v-if="generating" class="generating-state">
          <Loader2 :size="24" class="spin" />
          <p>正在根据目标岗位调整简历…</p>
          <span>会保留原有事实，并控制篇幅和表达重点。</span>
        </div>

        <template v-else-if="result">
          <div class="change-summary">
            <el-tag
              v-for="change in result.changes"
              :key="change.title"
              size="small"
              :type="changeTagType(change.action)"
              effect="plain"
            >
              {{ change.title }} · {{ changeActionLabel(change.action) }}
            </el-tag>
          </div>
          <div class="resume-scroll">
            <article v-for="(section, i) in result.content.sections" :key="`result-${i}`" class="resume-section">
              <div class="section-heading">
                <h4>{{ section.title }}</h4>
                <el-tag size="small" :type="changeTagType(changeByTitle(section.title)?.action)" effect="plain">
                  {{ changeActionLabel(changeByTitle(section.title)?.action) }}
                </el-tag>
              </div>
              <p class="section-content">{{ section.content }}</p>
              <p v-if="changeByTitle(section.title)?.reason" class="change-reason">
                {{ changeByTitle(section.title)?.reason }}
              </p>
            </article>
          </div>
        </template>

        <div v-else class="empty-state result-empty">
          <Sparkles :size="30" />
          <p class="empty-title">等待生成岗位定制稿</p>
          <p class="empty-desc">选择定制方式后点击右上角生成，生成结果不会覆盖原简历。</p>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import {
  FileSearch,
  FileText,
  Loader2,
  RefreshCw,
  Save,
  Sparkles,
} from 'lucide-vue-next'
import { ElMessage } from 'element-plus'
import { useSessionStore } from '../../stores/session'
import { addResumeVersion, getResumeDoc, listResumeDocs } from '../../api/resumeLibrary'
import { importGeneratedResume, tailorResume } from '../../api/resumeGeneration'
import type {
  ResumeContent,
  ResumeLibraryDoc,
  TailoredResumeMode,
  TailoredResumeResult,
  TailoredSectionChange,
} from '../../types'

interface SourceOption {
  label: string
  value: string
}

const router = useRouter()
const session = useSessionStore()

const mode = ref<TailoredResumeMode>('focused')
const sourceKey = ref('session')
const sourceOptions = ref<SourceOption[]>([])
const libraryDocs = ref<ResumeLibraryDoc[]>([])
const sourceContent = ref<ResumeContent | null>(null)
const sourceRenderConfig = ref<Record<string, unknown> | null>(null)
const sourceDocId = ref<number | null>(null)
const docsLoading = ref(false)
const generating = ref(false)
const saving = ref(false)
const errorMessage = ref('')
const result = ref<TailoredResumeResult | null>(null)

const canGenerate = computed(
  () => Boolean(session.jdAnalysis && sourceContent.value && !generating.value),
)

function normalizeContent(raw: unknown): ResumeContent | null {
  if (!raw || typeof raw !== 'object') return null
  const value = raw as { sections?: unknown; raw_text?: unknown }
  const sections = Array.isArray(value.sections)
    ? value.sections
        .filter((item): item is Record<string, unknown> => Boolean(item) && typeof item === 'object')
        .map((item) => ({
          title: String(item.title ?? '').trim(),
          content: String(item.content ?? '').trim(),
        }))
        .filter((item) => item.title || item.content)
    : []
  if (!sections.length) return null
  return {
    sections,
    raw_text:
      typeof value.raw_text === 'string' && value.raw_text.trim()
        ? value.raw_text
        : sections.map((item) => `${item.title}\n${item.content}`).join('\n\n'),
  }
}

async function loadLibraryDocs() {
  docsLoading.value = true
  try {
    libraryDocs.value = await listResumeDocs()
    sourceOptions.value = [
      ...(session.resumeContent ? [{ label: '当前分析中的简历', value: 'session' }] : []),
      ...libraryDocs.value.map((doc) => ({
        label: `简历库 · ${doc.title}`,
        value: `doc:${doc.id}`,
      })),
    ]
    if (!sourceOptions.value.some((option) => option.value === sourceKey.value)) {
      sourceKey.value = sourceOptions.value[0]?.value || ''
      await loadSource()
    }
  } catch (err) {
    errorMessage.value = extractError(err, '简历列表加载失败')
  } finally {
    docsLoading.value = false
  }
}

async function loadSource() {
  result.value = null
  errorMessage.value = ''
  if (sourceKey.value === 'session') {
    sourceDocId.value = null
    sourceContent.value = normalizeContent(session.resumeContent)
    sourceRenderConfig.value = session.renderConfig
      ? { ...(session.renderConfig as unknown as Record<string, unknown>) }
      : null
    return
  }

  if (!sourceKey.value || !sourceKey.value.startsWith('doc:')) {
    sourceDocId.value = null
    sourceContent.value = null
    sourceRenderConfig.value = null
    return
  }

  const docId = Number(sourceKey.value.replace('doc:', ''))
  if (!Number.isInteger(docId) || docId <= 0) {
    sourceDocId.value = null
    sourceContent.value = null
    sourceRenderConfig.value = null
    return
  }

  docsLoading.value = true
  try {
    const doc = await getResumeDoc(docId)
    const version = doc.current_version
    sourceDocId.value = doc.id
    sourceContent.value = normalizeContent(version?.content)
    sourceRenderConfig.value = version?.render_config ? { ...version.render_config } : null
    if (!sourceContent.value) {
      errorMessage.value = '这份简历还没有可调整的模块内容'
    }
  } catch (err) {
    errorMessage.value = extractError(err, '基础简历加载失败')
  } finally {
    docsLoading.value = false
  }
}

async function generate() {
  if (!canGenerate.value || !sourceContent.value || !session.jdAnalysis) return
  generating.value = true
  errorMessage.value = ''
  result.value = null
  try {
    result.value = await tailorResume({
      source_resume: sourceContent.value,
      jd_analysis: session.jdAnalysis as unknown as Record<string, unknown>,
      gap_analysis: session.gapAnalysis
        ? (session.gapAnalysis as unknown as Record<string, unknown>)
        : null,
      mode: mode.value,
    })
    ElMessage.success('岗位定制稿已生成，请确认后保存')
  } catch (err) {
    errorMessage.value = extractError(err, '岗位定制失败')
  } finally {
    generating.value = false
  }
}

async function save() {
  if (!result.value || !sourceContent.value) return
  saving.value = true
  errorMessage.value = ''
  try {
    const title = [
      session.jdAnalysis?.company,
      session.jdAnalysis?.job_title,
      '岗位定制版',
    ]
      .filter(Boolean)
      .join('·')

    if (sourceDocId.value) {
      await addResumeVersion(sourceDocId.value, {
        content: result.value.content as unknown as Record<string, unknown>,
        render_config: sourceRenderConfig.value || undefined,
      })
    } else {
      await importGeneratedResume({
        title,
        content: result.value.content,
        page_preference: mode.value === 'one_page' ? 'one_page' : 'two_pages',
      })
    }
    ElMessage.success('已保存为新的简历版本')
    void router.push('/resume-library')
  } catch (err) {
    errorMessage.value = extractError(err, '保存岗位定制版失败')
  } finally {
    saving.value = false
  }
}

function changeByTitle(title: string): TailoredSectionChange | undefined {
  return result.value?.changes.find((change) => change.title === title)
}

function changeActionLabel(action?: TailoredSectionChange['action']) {
  const labels: Record<TailoredSectionChange['action'], string> = {
    kept: '保持原文',
    rewritten: '已调整',
    compressed: '已压缩',
    hidden: '已隐藏',
  }
  return action ? labels[action] : '待确认'
}

function changeTagType(action?: TailoredSectionChange['action']) {
  if (action === 'hidden') return 'info'
  if (action === 'compressed') return 'warning'
  if (action === 'rewritten') return 'success'
  return 'info'
}

function extractError(err: unknown, fallback: string): string {
  const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
  return detail || fallback
}

watch(sourceKey, loadSource)

onMounted(async () => {
  await loadLibraryDocs()
  if (sourceContent.value === null && sourceKey.value) {
    await loadSource()
  }
})
</script>

<style scoped>
.tailor-panel {
  display: flex;
  flex-direction: column;
  min-height: 0;
  height: 100%;
}

.tailor-toolbar {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  padding: var(--space-3);
  border: var(--border-light);
  border-radius: var(--radius-lg);
  background: var(--color-bg-elevated);
  margin-bottom: var(--space-3);
}

.source-control,
.mode-control {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.control-label {
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
  white-space: nowrap;
}

.source-select {
  width: 240px;
}

.tailor-toolbar > :last-child {
  margin-left: auto;
}

.fact-guard {
  margin-bottom: var(--space-3);
}

.tailor-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: var(--space-3);
  min-height: 0;
  flex: 1;
}

.resume-pane {
  min-height: 0;
  display: flex;
  flex-direction: column;
  border: var(--border-light);
  border-radius: var(--radius-lg);
  background: var(--color-bg-elevated);
  overflow: hidden;
}

.pane-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  border-bottom: var(--border-light);
}

.pane-header h3 {
  margin: 2px 0 0;
  font-size: var(--text-lg);
}

.pane-kicker {
  margin: 0;
  color: var(--color-text-tertiary);
  font-size: var(--text-xs);
  letter-spacing: 0.08em;
}

.result-actions {
  display: flex;
  align-items: center;
}

.resume-scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: var(--space-3) var(--space-4) var(--space-5);
}

.resume-section {
  padding: var(--space-3) 0;
  border-bottom: var(--border-light);
}

.resume-section:last-child {
  border-bottom: none;
}

.resume-section h4 {
  margin: 0 0 var(--space-2);
  color: var(--color-text-primary);
  font-size: var(--text-md);
}

.section-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
}

.section-content {
  margin: 0;
  color: var(--color-text-secondary);
  font-size: var(--text-resume);
  line-height: var(--leading-relaxed);
  white-space: pre-wrap;
}

.change-reason {
  margin: var(--space-2) 0 0;
  color: var(--color-text-tertiary);
  font-size: var(--text-xs);
}

.change-summary {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-4) 0;
}

.generating-state,
.empty-state {
  display: flex;
  flex: 1;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  padding: var(--space-7) var(--space-4);
  color: var(--color-text-secondary);
  text-align: center;
}

.generating-state p,
.empty-title {
  margin: 0;
  color: var(--color-text-primary);
  font-size: var(--text-md);
  font-weight: var(--weight-semibold);
}

.generating-state span,
.empty-desc {
  margin: 0;
  color: var(--color-text-tertiary);
  font-size: var(--text-sm);
}

.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 1100px) {
  .tailor-toolbar {
    flex-wrap: wrap;
  }

  .tailor-toolbar > :last-child {
    margin-left: 0;
  }

  .tailor-layout {
    grid-template-columns: 1fr;
  }

  .resume-pane {
    min-height: 420px;
  }
}
</style>