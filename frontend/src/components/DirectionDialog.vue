<template>
  <el-dialog
    v-model="visible"
    title="投递方向管理"
    width="820px"
    :append-to-body="true"
    class="dir-dialog"
  >
    <p class="dialog-hint">
      可手动添加、编辑或删除目标岗位，也可基于已确认画像 AI 推荐 3~8 个方向。保存后由简历生成、经历包装与岗位匹配统一复用。
    </p>

    <div class="manual-form">
      <div class="manual-title">手动添加投递方向</div>
      <div class="manual-grid">
        <el-input v-model="manual.title" maxlength="100" placeholder="方向名称，如：后端开发工程师" />
        <el-input v-model="manual.reason" maxlength="1000" placeholder="为什么想投这个方向（可选）" />
      </div>
      <el-input v-model="manual.detail" maxlength="2000" type="textarea" :rows="2" placeholder="目标岗位特点、准备计划或备注（可选）" />
      <div class="manual-actions">
        <span class="count-tip">画像最多保存 3 个方向</span>
        <el-button type="primary" :loading="manualSaving" :disabled="!manual.title.trim() || existing.length >= 3" @click="addManual">
          添加方向
        </el-button>
      </div>
    </div>

    <div v-if="existing.length" class="existing">
      <div class="existing-label">画像中已确认的方向（{{ existing.length }} / 3）</div>
      <div v-for="item in existing" :key="item.id" class="managed-card">
        <template v-if="editingId === item.id">
          <el-input v-model="editForm.title" maxlength="100" placeholder="方向名称" />
          <el-input v-model="editForm.reason" maxlength="1000" placeholder="推荐理由 / 求职动机" />
          <el-input v-model="editForm.detail" maxlength="2000" type="textarea" :rows="2" placeholder="方向详情" />
          <div class="manual-actions">
            <el-button text @click="cancelEdit">取消</el-button>
            <el-button type="primary" :loading="editingSaving" @click="saveEdit(item)">保存修改</el-button>
          </div>
        </template>
        <template v-else>
          <div class="managed-head">
            <div class="managed-title">{{ item.title }}</div>
            <el-tag size="small" :type="item.source_type === 'ai_recommendation' ? 'warning' : 'success'">
              {{ item.source_type === 'ai_recommendation' ? 'AI 推荐' : '手动添加' }}
            </el-tag>
            <span class="exp-spacer" />
            <el-button size="small" text @click="startEdit(item)">编辑</el-button>
            <el-button size="small" text type="danger" @click="removeExisting(item)">删除</el-button>
          </div>
          <div v-if="item.reason" class="managed-reason">{{ item.reason }}</div>
          <div v-if="item.detail" class="managed-detail">{{ item.detail }}</div>
        </template>
      </div>
    </div>

    <div v-if="generating" class="gen-block">
      <SkeletonLoader variant="card" :lines="2" />
      <div class="gen-label">
        <Compass :size="16" />
        <span>正在基于你的画像分析投递方向…</span>
      </div>
    </div>

    <div v-else-if="!candidates.length" class="empty-block">
      <p class="empty-text">点击「AI 分析」，基于画像生成岗位方向候选。</p>
    </div>

    <div v-else>
      <div class="ai-summary">
        <div><b>数据来源：</b>{{ dataSource }}</div>
        <div><b>判断逻辑：</b>{{ decisionLogic }}</div>
      </div>
      <div class="dir-grid">
        <div
          v-for="(c, i) in candidates"
          :key="c.title"
          class="dir-card"
          :class="{ selected: selected.includes(c.title) }"
          @click="toggle(c.title)"
        >
          <span class="dir-radio" :class="{ on: selected.includes(c.title) }" aria-hidden="true">
            <Check v-if="selected.includes(c.title)" :size="14" />
          </span>
          <div class="dir-card-body">
            <div class="dir-card-title">{{ c.title }}</div>
            <div class="dir-card-reason">{{ c.reason }}</div>
            <button class="dir-detail-toggle" type="button" @click.stop="expanded[i] = !expanded[i]">
              {{ expanded[i] ? '收起依据与详情' : '查看依据与详情' }}
              <ChevronUp v-if="expanded[i]" :size="14" />
              <ChevronDown v-else :size="14" />
            </button>
            <div v-if="expanded[i]" class="dir-detail">
              <div>{{ c.detail || '暂无更多详情' }}</div>
              <div class="basis-title">画像依据</div>
              <div v-if="basisFor(c).length" class="basis-list">
                <div v-for="b in basisFor(c)" :key="b.key" class="basis-item">
                  <el-tag size="small">{{ categoryLabel(b.category) }}</el-tag>
                  <span>{{ b.title }}</span>
                  <small>{{ b.summary }}</small>
                </div>
              </div>
              <div v-else class="basis-empty">该方向未建立精确条目关联，仅基于本次画像摘要综合判断。</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <el-alert v-if="errMsg" type="error" :title="errMsg" show-icon :closable="false" class="dialog-feedback" />
    <el-alert v-else-if="okMsg" type="success" :title="okMsg" show-icon :closable="false" class="dialog-feedback" />

    <template #footer>
      <span v-if="candidates.length" class="count-tip">{{ selected.length }} / 3 已选</span>
      <el-button text @click="visible = false">关闭</el-button>
      <el-button :disabled="generating || saving" @click="analyze">
        <Compass :size="14" style="margin-right: 4px" />AI 分析
      </el-button>
      <el-button type="primary" :loading="saving" :disabled="!selected.length || generating" @click="save">
        保存 AI 选择 ({{ selected.length }})
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Check, ChevronDown, ChevronUp, Compass } from 'lucide-vue-next'
import SkeletonLoader from './SkeletonLoader.vue'
import {
  confirmDirections,
  createManualDirection,
  deleteDirection,
  listDirections,
  recommendDirections,
  updateDirection,
} from '../api/profile'
import type {
  DirectionBasisItem,
  DirectionCandidate,
  DirectionRecommendationResult,
  ResumeDirectionData,
} from '../types'

const props = defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{
  (e: 'update:modelValue', v: boolean): void
  (e: 'saved'): void
}>()

const visible = computed({
  get: () => props.modelValue,
  set: (v: boolean) => emit('update:modelValue', v),
})

const candidates = ref<DirectionCandidate[]>([])
const basis = ref<DirectionBasisItem[]>([])
const dataSource = ref('个人画像（已确认条目）')
const decisionLogic = ref('画像证据匹配与职业赛道推断，不包含招聘市场统计或 JD 匹配')
const selected = ref<string[]>([])
const expanded = ref<Record<number, boolean>>({})
const existing = ref<ResumeDirectionData[]>([])
const generating = ref(false)
const saving = ref(false)
const okMsg = ref('')
const errMsg = ref('')
const manualSaving = ref(false)
const editingSaving = ref(false)
const editingId = ref<number | null>(null)
const manual = reactive({ title: '', reason: '', detail: '' })
const editForm = reactive({ title: '', reason: '', detail: '' })

watch(visible, async (open) => {
  if (!open) return
  okMsg.value = ''
  errMsg.value = ''
  candidates.value = []
  basis.value = []
  selected.value = []
  expanded.value = {}
  editingId.value = null
  Object.assign(manual, { title: '', reason: '', detail: '' })
  await prefillExisting()
})

function detailError(e: unknown, fallback: string): string {
  const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
  return typeof detail === 'string' && detail ? detail : fallback
}

function categoryLabel(category: string): string {
  const labels: Record<string, string> = {
    basic_info: '基本信息', education: '教育', skill: '技能', experience: '经历',
    target: '方向', soft: '软性信息', interview_feedback: '面试反馈', award: '奖项', social: '社交',
  }
  return labels[category] || category
}

function basisFor(candidate: DirectionCandidate): DirectionBasisItem[] {
  const keys = candidate.basis_keys || []
  return basis.value.filter((item) => keys.includes(item.key))
}

async function addManual() {
  const title = manual.title.trim()
  if (!title || existing.value.length >= 3) return
  manualSaving.value = true
  errMsg.value = ''
  try {
    await createManualDirection({ title, reason: manual.reason.trim(), detail: manual.detail.trim() })
    Object.assign(manual, { title: '', reason: '', detail: '' })
    okMsg.value = `已添加目标岗位「${title}」`
    await prefillExisting()
    emit('saved')
  } catch (e) {
    errMsg.value = detailError(e, '添加失败，请重试')
  } finally {
    manualSaving.value = false
  }
}

async function prefillExisting() {
  try {
    const res = await listDirections()
    existing.value = res.data || []
  } catch {
    existing.value = []
  }
}

function startEdit(item: ResumeDirectionData) {
  editingId.value = item.id
  Object.assign(editForm, { title: item.title, reason: item.reason, detail: item.detail })
}

function cancelEdit() {
  editingId.value = null
}

async function saveEdit(item: ResumeDirectionData) {
  editingSaving.value = true
  errMsg.value = ''
  try {
    await updateDirection(item.id, {
      title: editForm.title.trim(),
      reason: editForm.reason.trim(),
      detail: editForm.detail.trim(),
    })
    editingId.value = null
    okMsg.value = '投递方向已更新'
    await prefillExisting()
    emit('saved')
  } catch (e) {
    errMsg.value = detailError(e, '修改失败，请重试')
  } finally {
    editingSaving.value = false
  }
}

function toggle(title: string) {
  const idx = selected.value.indexOf(title)
  if (idx >= 0) selected.value.splice(idx, 1)
  else if (selected.value.length < 3) selected.value.push(title)
  else ElMessage.warning('最多选择 3 个方向')
}

async function analyze() {
  generating.value = true
  errMsg.value = ''
  okMsg.value = ''
  candidates.value = []
  basis.value = []
  selected.value = []
  expanded.value = {}
  try {
    const res = await recommendDirections()
    const data = res.data as DirectionRecommendationResult
    candidates.value = data.directions || []
    basis.value = data.basis || []
    dataSource.value = data.data_source || dataSource.value
    decisionLogic.value = data.decision_logic || decisionLogic.value
    if (!candidates.value.length) errMsg.value = '画像分析未生成有效方向，请完善画像后重试'
  } catch (e) {
    errMsg.value = detailError(e, '画像方向推荐失败，请稍后重试')
  } finally {
    generating.value = false
  }
}

async function save() {
  if (!selected.value.length) return
  saving.value = true
  errMsg.value = ''
  okMsg.value = ''
  try {
    const chosen = candidates.value.filter((c) => selected.value.includes(c.title))
    const res = await confirmDirections(chosen)
    ElMessage.success(`已保存 ${res.data.length} 个投递方向到个人画像`)
    emit('saved')
    visible.value = false
  } catch (e) {
    errMsg.value = detailError(e, '保存失败，请重试')
  } finally {
    saving.value = false
  }
}

async function removeExisting(item: ResumeDirectionData) {
  try {
    await ElMessageBox.confirm(`从画像中删除目标方向「${item.title}」？`, '删除方向', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch {
    return
  }
  try {
    await deleteDirection(item.id)
    existing.value = existing.value.filter((row) => row.id !== item.id)
    ElMessage.success('已从画像删除')
    emit('saved')
  } catch (e) {
    errMsg.value = detailError(e, '删除失败，请重试')
  }
}
</script>

<style scoped>
.dialog-hint {
  margin: 0 0 var(--space-4);
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  line-height: var(--leading-relaxed);
}
.manual-add {
  display: flex;
  gap: var(--space-2);
  margin-bottom: var(--space-4);
}
.existing {
  margin-bottom: var(--space-4);
  padding: var(--space-3) var(--space-4);
  border: var(--border-light);
  border-radius: var(--radius-md);
  background: var(--color-accent-50);
}
.existing-label {
  font-size: var(--text-xs);
  color: var(--color-text-secondary);
  margin-bottom: var(--space-2);
}
.existing-tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}
.gen-block {
  padding: var(--space-4);
  border: var(--border-light);
  border-radius: var(--radius-lg);
  background: var(--color-accent-50);
}
.gen-label {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-top: var(--space-3);
  color: var(--color-accent-600);
  font-size: var(--text-sm);
  font-weight: var(--weight-medium);
}
.empty-block {
  padding: var(--space-6) 0;
  text-align: center;
}
.empty-text {
  margin: 0;
  color: var(--color-text-disabled);
  font-size: var(--text-sm);
}
.dir-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: var(--space-3);
  max-height: 360px;
  overflow-y: auto;
}
.dir-card {
  position: relative;
  display: flex;
  gap: var(--space-3);
  padding: var(--space-4);
  border: var(--border-light);
  border-radius: var(--radius-lg);
  background: var(--color-bg);
  cursor: pointer;
  transition: border-color var(--duration-normal) var(--ease-default),
    box-shadow var(--duration-normal) var(--ease-default);
}
.dir-card:hover {
  border-color: var(--color-accent-400);
  box-shadow: var(--shadow-md);
}
.dir-card.selected {
  border-color: var(--color-accent-600);
  box-shadow: 0 0 0 1px var(--color-accent-600) inset;
  background: var(--color-accent-50);
}
.dir-radio {
  flex-shrink: 0;
  width: 18px;
  height: 18px;
  border-radius: var(--radius-full);
  border: 1.5px solid var(--color-gray-300);
  display: grid;
  place-items: center;
  color: var(--color-bg-elevated);
  margin-top: 2px;
}
.dir-radio.on {
  background: var(--color-accent-600);
  border-color: var(--color-accent-600);
}
.dir-card-title {
  font-family: var(--font-display);
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
  color: var(--color-text-primary);
}
.dir-card-reason {
  margin-top: var(--space-1);
  font-size: var(--text-xs);
  color: var(--color-text-secondary);
  line-height: var(--leading-relaxed);
}
.dir-detail-toggle {
  margin-top: var(--space-2);
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 0;
  border: none;
  background: transparent;
  font-size: var(--text-xs);
  color: var(--color-accent-600);
  cursor: pointer;
}
.dir-detail {
  margin-top: var(--space-2);
  font-size: var(--text-xs);
  color: var(--color-text-secondary);
  line-height: var(--leading-relaxed);
}
.dialog-feedback {
  margin-top: var(--space-4);
  border-radius: var(--radius-md);
}
.count-tip {
  float: left;
  line-height: 32px;
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  margin-right: var(--space-3);
}
</style>

.manual-form,
.existing {
  margin-bottom: var(--space-4);
  padding: var(--space-4);
  border: var(--border-light);
  border-radius: var(--radius-md);
  background: var(--color-bg-elevated);
}
.manual-title,
.existing-label {
  margin-bottom: var(--space-3);
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
}
.manual-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-3);
  margin-bottom: var(--space-3);
}
.manual-actions {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: var(--space-3);
  margin-top: var(--space-3);
}
.managed-card {
  padding: var(--space-3) 0;
  border-bottom: var(--border-light);
}
.managed-card:last-child {
  border-bottom: none;
}
.managed-card > * + * {
  margin-top: var(--space-2);
}
.managed-head {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
.managed-title {
  font-weight: var(--weight-semibold);
}
.managed-reason {
  color: var(--color-text-secondary);
  line-height: var(--leading-relaxed);
}
.managed-detail {
  color: var(--color-text-tertiary);
  font-size: var(--text-sm);
  line-height: var(--leading-relaxed);
}
.ai-summary {
  margin-bottom: var(--space-3);
  padding: var(--space-3);
  border-radius: var(--radius-md);
  background: var(--color-info-light);
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
  line-height: var(--leading-relaxed);
}
.basis-title {
  margin-top: var(--space-3);
  font-weight: var(--weight-semibold);
}
.basis-list {
  display: grid;
  gap: var(--space-2);
  margin-top: var(--space-2);
}
.basis-item {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 2px var(--space-2);
  align-items: center;
  color: var(--color-text-secondary);
}
.basis-item small {
  grid-column: 2;
  color: var(--color-text-tertiary);
}
.basis-empty {
  margin-top: var(--space-2);
  color: var(--color-text-tertiary);
}
.exp-spacer {
  flex: 1;
}
@media (max-width: 640px) {
  .manual-grid {
    grid-template-columns: 1fr;
  }
}
