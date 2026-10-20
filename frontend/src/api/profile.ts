import client from './client'
import type {
  CategorySummary,
  DirectionCandidate,
  ProfileEvidence,
  ProfileFormData,
  ProfileFormSave,
  ProfileItem,
  ProfileItemCreate,
  ProfileItemUpdate,
  ProfileResumeSource,
  ResumeDirectionData,
  DirectionManualInput,
  DirectionRecommendationResult,
  ProfileUpdateProposal,
  ResumeImportApplyRequest,
  ResumeImportApplyResult,
  ResumeImportPreview,
  SoftInfo,
} from '../types'

export function listProfileItems(category?: string, status?: string) {
  return client.get<ProfileItem[]>('/profile/items', { params: { category, status } })
}

export function getProfileItem(id: number) {
  return client.get<ProfileItem>(`/profile/items/${id}`)
}

export function createProfileItem(data: ProfileItemCreate) {
  return client.post<ProfileItem>('/profile/items', data)
}

export function updateProfileItem(id: number, data: ProfileItemUpdate) {
  return client.patch<ProfileItem>(`/profile/items/${id}`, data)
}

export function changeProfileStatus(id: number, status: string) {
  return client.post<ProfileItem>(`/profile/items/${id}/status`, { status })
}

export function deleteProfileItem(id: number) {
  return client.delete(`/profile/items/${id}`)
}

export function addProfileEvidence(
  id: number,
  data: { source_type: string; quote?: string; source_id?: string; verified_by_user?: boolean },
) {
  return client.post<ProfileEvidence>(`/profile/items/${id}/evidences`, data)
}

export function getCategorySummary() {
  return client.get<CategorySummary[]>('/profile/categories')
}

export function listProposals(reportId: string) {
  return client.get<ProfileUpdateProposal[]>(`/profile/proposals/${reportId}`)
}

export function actOnProposal(proposalId: number, action: string, after_value?: string) {
  return client.post<ProfileUpdateProposal>(`/profile/proposals/${proposalId}/action`, { action, after_value })
}

// 画像方向推荐（阶段3 指令3-1）
export function recommendDirections() {
  // 生成候选会调用 LLM（较慢），放宽超时
  return client.post<DirectionRecommendationResult>('/profile/directions/recommend', null, { timeout: 180000 })
}

export function listDirections() {
  return client.get<ResumeDirectionData[]>('/profile/directions')
}

export function createManualDirection(data: DirectionManualInput) {
  return client.post<ProfileItem>('/profile/directions/manual', data)
}

export function updateDirection(id: number, data: Partial<DirectionManualInput>) {
  return client.patch<ProfileItem>(`/profile/directions/${id}`, data)
}

export function deleteDirection(id: number) {
  return client.delete(`/profile/directions/${id}`)
}

export function confirmDirections(selected: DirectionCandidate[]) {
  return client.post<ProfileItem[]>('/profile/directions/confirm', { selected })
}

// 软性信息（阶段3 指令3-2）
export function generateSoftInfo() {
  // 生成会调用 LLM（较慢），放宽超时
  return client.post<SoftInfo>('/profile/soft-info/generate', null, { timeout: 180000 })
}

export function saveSoftInfo(data: { personality: string; vision: string; disinterested: string; self_eval: string }) {
  return client.post<ProfileItem[]>('/profile/soft-info/save', data)
}

// 结构化画像表单（知识库 分阶段向导，阶段3）
export function getResumeProfileSource() {
  return client.get<ProfileResumeSource>('/profile/resume-source')
}

export function getProfileForm() {
  return client.get<ProfileFormData>('/profile/form')
}

export function saveProfileForm(data: ProfileFormSave) {
  return client.post<ProfileFormData>('/profile/form', data)
}

// 简历附件导入个人画像：先预览抽取结果，用户确认后再写入
export function previewResumeImport(file: File) {
  const form = new FormData()
  form.append('file', file)
  return client.post<ResumeImportPreview>('/profile/resume-import/preview', form, { timeout: 180000 })
}

export function previewResumeImportFromLibrary(documentId: number, versionId?: number) {
  return client.post<ResumeImportPreview>('/profile/resume-import/preview-library', {
    document_id: documentId,
    version_id: versionId ?? null,
  }, { timeout: 180000 })
}

export function applyResumeImport(data: ResumeImportApplyRequest) {
  return client.post<ResumeImportApplyResult>('/profile/resume-import/apply', data)
}

export function syncProfileToLibrary(data: {
  document_id: number
  fields: Record<string, string>
  note?: string
}) {
  return client.post<{
    document_id: number
    version_id: number
    version: number
    changed_fields: string[]
    message: string
  }>('/profile/resume-import/sync-to-library', data)
}
