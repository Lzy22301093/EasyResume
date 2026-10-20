"""ProfileResumeImportService — 从已有简历附件抽取个人画像并写入。

流程（准确性优先）：
1. preview：解析附件 → LLM 结构化抽取（带原文摘录 quote）→ 仅返回预览，不落库
2. apply：仅写入用户勾选/改过的字段，merge 进现有画像（不清空已有条目）
3. 每条写入挂 resume 证据（source_type=resume），便于溯源

与向导 `ProfileFormService.save` 的快照覆盖语义不同：导入是增量合并，
避免用户只导入部分字段时误删已有画像。
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session as DBSession

from app.models.schemas import (
    EvidenceCreate,
    ProfileEducationEntry,
    ProfileExtraEntry,
    ProfileFormOut,
    ProfileItemCreate,
    ResumeImportApplyRequest,
    ResumeImportApplyResult,
    ResumeImportBasicField,
    ResumeImportEducation,
    ResumeImportExperience,
    ResumeImportExtract,
    ResumeImportPreviewOut,
    ResumeImportSkill,
)
from app.services.profile_form_service import BASIC_INFO_FIELDS, ProfileFormService
from app.services.profile_service import ProfileService

logger = logging.getLogger(__name__)

# 基本信息识别键（与 BASIC_INFO_FIELDS 对齐）
_ALLOWED_BASIC_KEYS = set(BASIC_INFO_FIELDS.keys())

# LLM 抽取：整体置信度低于该阈值时，在 warnings 中提醒用户仔细核对
_LOW_CONFIDENCE = 0.55

# 预览阶段送给 LLM 的简历正文上限（约 3000 tokens）
_MAX_RESUME_CHARS = 12000

SYSTEM_PROMPT = """你是严谨的简历信息识别助手。只从给定简历文本中抽取真实出现的信息，禁止编造、猜测或补全。

输出 JSON，结构如下：
{
  "basic_fields": [
    {"key": "name|phone|email|location|gender|birthday|nationality|hometown",
     "value": "识别到的值", "quote": "简历中对应的原文摘录", "confidence": 0.0到1.0}
  ],
  "summary": "自我评价/个人简介原文概括（没有则空字符串）",
  "summary_quote": "对应原文摘录",
  "education": [
    {"school":"","degree":"","major":"","start":"","end":"","gpa":"","courses":"",
     "quote":"","confidence":0.7}
  ],
  "experiences": [
    {"exp_type":"internship|project","company":"公司名或项目名","role":"岗位/角色",
     "start":"","end":"","current":false,"tech_stack":"","duty":"","achievement":"",
     "quote":"","confidence":0.7}
  ],
  "skills": [
    {"name":"技能名","level":"","notes":"","quote":"","confidence":0.7}
  ],
  "awards": ["奖项名称"],
  "warnings": ["识别风险，如字段模糊、日期缺失等"],
  "confidence": 0.0到1.0
}

要求：
1. value/字段内容必须来自简历原文语义，不得发明不存在的公司、学校、技能或成果。
2. quote 尽量摘录简历中支撑该条的短句（不超过 80 字），便于用户核对。
3. 日期尽量规范为 YYYY-MM 或 YYYY；无法确定就留空，不要猜。
4. exp_type：全职/实习/工作经历写 internship，课程设计/个人项目/竞赛项目写 project。
5. skills 只列简历中明确写出的技能，不要从经历里泛化扩写。
6. 若简历文本过短、扫描质量差或关键信息缺失，写入 warnings 并降低 confidence。
7. 只返回 JSON。"""


class ProfileResumeImportError(ValueError):
    """简历导入业务错误。"""


class ProfileResumeImportService:
    """简历附件 → 画像抽取预览 / 确认写入。"""

    def __init__(self) -> None:
        self._profile = ProfileService()
        self._form = ProfileFormService()

    # ---- 预览：解析 + 抽取（不落库） ----

    async def preview(
        self,
        db: DBSession,
        user_id: int,
        llm: Any,
        *,
        file_content_b64: str,
        filename: str,
        model: str | None = None,
    ) -> ResumeImportPreviewOut:
        """解析简历附件并抽取结构化信息，返回待确认预览。"""
        text = await self._parse_text(file_content_b64, filename)
        return await self.preview_from_text(
            db, user_id, llm, text=text, filename=filename or "", model=model
        )

    async def preview_from_document(
        self,
        db: DBSession,
        user_id: int,
        llm: Any,
        *,
        document_id: int,
        version_id: int | None = None,
        model: str | None = None,
    ) -> ResumeImportPreviewOut:
        """以简历库已有文档正文为源抽取（免重新上传）。"""
        from app.services.resume_library_service import (
            ResumeLibraryError,
            ResumeLibraryService,
            parse_json_object,
        )

        lib = ResumeLibraryService()
        try:
            doc = lib.get_document(db, user_id, document_id)
        except ResumeLibraryError as e:
            raise ProfileResumeImportError(str(e)) from e

        if version_id is not None:
            try:
                version = lib.get_version(db, user_id, version_id)
            except ResumeLibraryError as e:
                raise ProfileResumeImportError(str(e)) from e
            if version.document_id != doc.id:
                raise ProfileResumeImportError("该版本不属于此简历文档")
        else:
            if not doc.current_version_id:
                raise ProfileResumeImportError("该简历文档还没有版本内容")
            version = lib.get_version(db, user_id, doc.current_version_id)

        content = parse_json_object(version.content_json) or {}
        text = str(content.get("raw_text") or "").strip()
        if not text:
            # 兜底：拼接 sections
            parts = []
            for sec in content.get("sections") or []:
                if isinstance(sec, dict):
                    parts.append(str(sec.get("content") or ""))
            text = "\n".join(p for p in parts if p).strip()
        if len(text) < 40:
            raise ProfileResumeImportError("简历库文档正文过短，无法识别画像信息")

        return await self.preview_from_text(
            db,
            user_id,
            llm,
            text=text,
            filename=f"简历库·{doc.title}",
            model=model,
        )

    async def preview_from_text(
        self,
        db: DBSession,
        user_id: int,
        llm: Any,
        *,
        text: str,
        filename: str,
        model: str | None = None,
    ) -> ResumeImportPreviewOut:
        """从纯文本抽取预览（附件 / 简历库共用）。"""
        extract = await self._extract(llm, text, model=model)

        basic_items = self._profile.list_by_category(db, user_id, "basic_info")
        title_to_content = {i.title: i.content for i in basic_items if i.content}
        existing_basic: dict[str, str] = {}
        for form_key, title in BASIC_INFO_FIELDS.items():
            if title_to_content.get(title):
                existing_basic[form_key] = title_to_content[title]

        existing_titles: list[str] = []
        for category in ("skill", "experience", "education"):
            for item in self._profile.list_by_category(db, user_id, category):
                if item.title:
                    existing_titles.append(item.title)

        return ResumeImportPreviewOut(
            filename=filename or "",
            text_length=len(text),
            extract=extract,
            existing_basic=existing_basic,
            existing_titles=existing_titles,
        )

    @staticmethod
    def build_form_draft(extract: ResumeImportExtract) -> dict[str, Any]:
        """把抽取结果映射为 ProfileFormSave 形态草稿（供向导一键填充，不落库）。"""
        basic_info = {f.key: f.value for f in extract.basic_fields if f.value}
        education = [
            {
                "school": e.school,
                "degree": e.degree,
                "major": e.major,
                "courses": e.courses,
                "start": e.start,
                "end": e.end,
                "gpa": e.gpa,
            }
            for e in extract.education
        ]
        extra: list[dict[str, Any]] = []
        for x in extract.experiences:
            cat = "project" if x.exp_type == "project" else "internship"
            extra.append(
                {
                    "category": cat,
                    "exp_type": cat,
                    "title": x.company or x.role,
                    "role": x.role,
                    "start": x.start,
                    "end": x.end,
                    "current": x.current,
                    "tech_stack": x.tech_stack,
                    "duty": x.duty,
                    "achievement": x.achievement,
                    "content": "",
                }
            )
        for s in extract.skills:
            extra.append({"category": "skill", "title": s.name, "content": s.notes or s.level})
        return {
            "basic_info": basic_info,
            "education": education,
            "awards": "\n".join(extract.awards),
            "social": [],
            "extra": extra,
            "summary": extract.summary,
            "warnings": list(extract.warnings),
            "confidence": extract.confidence,
        }

    async def _parse_text(self, file_content_b64: str, filename: str) -> str:
        from app.tools.file_tools import FileParserTool

        result = await FileParserTool().execute(file_content=file_content_b64, filename=filename)
        if not result.success:
            raise ProfileResumeImportError(f"文件解析失败: {result.error}")
        text = (result.data.get("text") or "").strip()
        if len(text) < 40:
            raise ProfileResumeImportError("文件未提取到足够的文本内容，无法识别画像信息")
        return text

    async def _extract(self, llm: Any, text: str, *, model: str | None = None) -> ResumeImportExtract:
        from app.llm.structured import ainvoke_json_with_schema

        body = text[:_MAX_RESUME_CHARS]
        if len(text) > _MAX_RESUME_CHARS:
            body += "\n\n... (文本过长，已截断)"

        try:
            extract = await ainvoke_json_with_schema(
                llm,
                system_prompt=SYSTEM_PROMPT,
                user_content=f"请从以下简历中识别个人信息：\n\n{body}",
                schema=ResumeImportExtract,
                max_attempts=2,
                model=model,
                temperature=0.2,
                max_tokens=8192,
            )
        except ValueError as e:
            raise ProfileResumeImportError(f"简历信息识别失败: {e}") from e

        self._sanitize_extract(extract)
        return extract

    @staticmethod
    def _sanitize_extract(extract: ResumeImportExtract) -> None:
        """清洗非法/空字段，压低低置信度，避免把噪声写进画像。"""
        cleaned_basic: list[ResumeImportBasicField] = []
        for f in extract.basic_fields:
            key = (f.key or "").strip().lower()
            value = (f.value or "").strip()
            if key not in _ALLOWED_BASIC_KEYS or not value:
                continue
            f.key = key
            f.value = value
            f.quote = (f.quote or "").strip()[:120]
            cleaned_basic.append(f)
        extract.basic_fields = cleaned_basic

        cleaned_edu: list[ResumeImportEducation] = []
        for e in extract.education:
            if not (e.school or e.major or e.degree):
                continue
            e.quote = (e.quote or "").strip()[:120]
            cleaned_edu.append(e)
        extract.education = cleaned_edu

        cleaned_exp: list[ResumeImportExperience] = []
        for x in extract.experiences:
            if not (x.company or x.role or x.duty):
                continue
            if (x.exp_type or "").strip() not in {"internship", "project"}:
                x.exp_type = "internship"
            x.quote = (x.quote or "").strip()[:120]
            cleaned_exp.append(x)
        extract.experiences = cleaned_exp

        cleaned_skills: list[ResumeImportSkill] = []
        seen_skills: set[str] = set()
        for s in extract.skills:
            name = (s.name or "").strip()
            if not name or name in seen_skills:
                continue
            seen_skills.add(name)
            s.name = name
            s.quote = (s.quote or "").strip()[:120]
            cleaned_skills.append(s)
        extract.skills = cleaned_skills

        extract.awards = [a.strip() for a in extract.awards if a and a.strip()]
        extract.summary = (extract.summary or "").strip()
        extract.summary_quote = (extract.summary_quote or "").strip()[:120]

        if extract.confidence < _LOW_CONFIDENCE:
            extract.warnings.append("识别置信度偏低，请逐项核对后再导入")
        if not extract.basic_fields and not extract.education and not extract.experiences:
            extract.warnings.append("几乎未识别到结构化信息，建议检查简历是否为可选中文字")

    # ---- 确认写入：增量 merge ----

    def apply(self, db: DBSession, user_id: int, data: ResumeImportApplyRequest) -> ResumeImportApplyResult:
        """把用户确认的字段写入画像（增量，不清空已有）。"""
        source_id = (data.source_filename or "").strip() or "resume_upload"
        written: dict[str, int] = {}
        skipped = 0

        for field in data.basic_fields:
            key = (field.key or "").strip().lower()
            value = (field.value or "").strip()
            if key not in _ALLOWED_BASIC_KEYS or not value:
                skipped += 1
                continue
            title = BASIC_INFO_FIELDS[key]
            item, _created = self._profile.upsert_item(
                db,
                user_id,
                ProfileItemCreate(
                    category="basic_info",
                    title=title,
                    content=value,
                    payload_json={key: value},
                    item_type="fact",
                    status="confirmed",
                    visibility="resume_interview",
                ),
            )
            self._attach_evidence(db, user_id, item.id, source_id, field.quote or f"{title}：{value}")
            written["basic_info"] = written.get("basic_info", 0) + 1

        summary = (data.summary or "").strip()
        if summary:
            item, _ = self._profile.upsert_item(
                db,
                user_id,
                ProfileItemCreate(
                    category="soft",
                    title="自我评价",
                    content=summary,
                    item_type="fact",
                    status="confirmed",
                    visibility="resume_interview",
                ),
            )
            self._attach_evidence(db, user_id, item.id, source_id, data.summary_quote or summary)
            written["soft"] = written.get("soft", 0) + 1

        for edu in data.education:
            if not (edu.school or edu.major or edu.degree):
                skipped += 1
                continue
            item = self._form._upsert_education(
                db,
                user_id,
                ProfileEducationEntry(
                    school=edu.school.strip(),
                    degree=edu.degree.strip(),
                    major=edu.major.strip(),
                    courses=edu.courses.strip(),
                    start=edu.start.strip(),
                    end=edu.end.strip(),
                    gpa=edu.gpa.strip(),
                ),
            )
            self._attach_evidence(db, user_id, item.id, source_id, edu.quote or f"教育经历·{edu.school or item.title}")
            written["education"] = written.get("education", 0) + 1

        for exp in data.experiences:
            company = (exp.company or "").strip()
            role = (exp.role or "").strip()
            if not company and not role:
                skipped += 1
                continue
            exp_type = "project" if exp.exp_type == "project" else "internship"
            ext = ProfileExtraEntry(
                category=exp_type,
                exp_type=exp_type,
                title=company or role,
                role=role,
                start=(exp.start or "").strip(),
                end=(exp.end or "").strip(),
                current=bool(exp.current),
                tech_stack=(exp.tech_stack or "").strip(),
                duty=(exp.duty or "").strip(),
                achievement=(exp.achievement or "").strip(),
            )
            content = self._form._format_experience(ext)
            cat = "experience"
            payload = {
                "exp_type": ext.exp_type,
                "company": ext.title,
                "title": ext.role or ext.title,
                "role": ext.role,
                "start": ext.start,
                "end": ext.end,
                "current": ext.current,
                "tech_stack": ext.tech_stack,
                "duty": ext.duty,
                "achievement": ext.achievement,
            }
            item, _ = self._profile.upsert_item(
                db,
                user_id,
                ProfileItemCreate(
                    category=cat,
                    title=ext.title,
                    content=content,
                    payload_json=payload,
                    item_type="fact",
                    status="confirmed",
                    visibility="resume_interview",
                ),
            )
            self._attach_evidence(db, user_id, item.id, source_id, exp.quote or f"经历·{ext.title}")
            written["experience"] = written.get("experience", 0) + 1

        for skill in data.skills:
            name = (skill.name or "").strip()
            if not name:
                skipped += 1
                continue
            notes = (skill.notes or "").strip()
            level = (skill.level or "").strip()
            content_parts = [p for p in (level, notes) if p]
            item, _ = self._profile.upsert_item(
                db,
                user_id,
                ProfileItemCreate(
                    category="skill",
                    title=name,
                    content="；".join(content_parts) if content_parts else "",
                    item_type="fact",
                    status="confirmed",
                    visibility="resume_interview",
                ),
            )
            self._attach_evidence(db, user_id, item.id, source_id, skill.quote or f"技能·{name}")
            written["skill"] = written.get("skill", 0) + 1

        award_lines = [a.strip() for a in (data.awards or []) if a and a.strip()]
        if award_lines:
            unique_awards = list(dict.fromkeys(award_lines))
            self._merge_awards(db, user_id, unique_awards, source_id)
            written["award"] = written.get("award", 0) + len(unique_awards)

        total = sum(written.values())
        return ResumeImportApplyResult(
            written=written,
            skipped=skipped,
            message=f"已导入 {total} 项到个人画像" if total else "未导入任何信息",
        )

    def _merge_awards(self, db: DBSession, user_id: int, lines: list[str], source_id: str) -> None:
        """奖项合并进「个人奖项」条目，按行去重追加。"""
        existing = next(
            (
                i
                for i in self._profile.list_by_category(db, user_id, "award")
                if i.title == "个人奖项"
            ),
            None,
        )
        current_lines = [ln.strip() for ln in (existing.content or "").splitlines() if ln.strip()] if existing else []
        merged = list(current_lines)
        for line in lines:
            if line not in merged:
                merged.append(line)
        if not merged:
            return
        item, _ = self._profile.upsert_item(
            db,
            user_id,
            ProfileItemCreate(
                category="award",
                title="个人奖项",
                content="\n".join(merged),
                item_type="fact",
                status="confirmed",
                visibility="resume_interview",
            ),
        )
        self._attach_evidence(db, user_id, item.id, source_id, "；".join(lines[:5]))

    def _attach_evidence(
        self,
        db: DBSession,
        user_id: int,
        item_id: int,
        source_id: str,
        quote: str,
    ) -> None:
        try:
            self._profile.add_evidence(
                db,
                user_id,
                item_id,
                EvidenceCreate(
                    source_type="resume",
                    source_id=source_id,
                    quote=(quote or "")[:200],
                    verified_by_user=True,
                ),
            )
        except Exception as e:  # 证据失败不阻断主写入
            logger.warning(f"[ResumeImport] 挂证据失败 item={item_id}: {e}")

    # ---- 画像 → 简历库：联系方式回写（新版本，可回滚） ----

    def sync_to_library(
        self,
        db: DBSession,
        user_id: int,
        *,
        document_id: int,
        fields: dict[str, str],
        note: str = "",
    ) -> dict[str, Any]:
        """把画像基本信息合并进简历库文档，生成新版本（不覆盖历史）。"""
        from app.services.resume_library_service import (
            ResumeLibraryError,
            ResumeLibraryService,
            parse_json_object,
        )
        from app.models.schemas import ResumeVersionCreate

        cleaned: dict[str, str] = {}
        for key, value in (fields or {}).items():
            k = (key or "").strip().lower()
            v = (value or "").strip()
            if k in _ALLOWED_BASIC_KEYS and v:
                cleaned[k] = v
        if not cleaned:
            raise ProfileResumeImportError("没有可同步的基本信息字段")

        lib = ResumeLibraryService()
        try:
            doc = lib.get_document(db, user_id, document_id)
        except ResumeLibraryError as e:
            raise ProfileResumeImportError(str(e)) from e
        if not doc.current_version_id:
            raise ProfileResumeImportError("该简历文档还没有版本内容")
        try:
            version = lib.get_version(db, user_id, doc.current_version_id)
        except ResumeLibraryError as e:
            raise ProfileResumeImportError(str(e)) from e

        content = parse_json_object(version.content_json) or {"sections": [], "raw_text": ""}
        new_content = self._merge_contact_into_content(content, cleaned)
        if note.strip():
            new_content["sync_note"] = note.strip()

        new_version = lib.add_version(
            db,
            user_id,
            doc.id,
            ResumeVersionCreate(content=new_content),
        )
        return {
            "document_id": doc.id,
            "version_id": new_version.id,
            "version": new_version.version,
            "changed_fields": sorted(cleaned.keys()),
            "message": f"已同步 {len(cleaned)} 项到「{doc.title}」v{new_version.version}",
        }

    @staticmethod
    def _merge_contact_into_content(content: dict[str, Any], fields: dict[str, str]) -> dict[str, Any]:
        """把联系方式合并进简历 content 的首段/页眉，并重算 raw_text。"""
        labels = {
            "name": "姓名",
            "phone": "手机",
            "email": "邮箱",
            "location": "所在地",
            "gender": "性别",
            "birthday": "出生日期",
            "nationality": "国籍",
            "hometown": "家乡",
        }
        order = ["name", "phone", "email", "location", "gender", "birthday", "nationality", "hometown"]
        contact_line = " | ".join(
            fields[k] if k == "name" else f"{labels[k]}:{fields[k]}"
            for k in order
            if fields.get(k)
        )

        sections = [dict(s) if isinstance(s, dict) else {"title": "正文", "content": str(s)}
                    for s in (content.get("sections") or [])]
        if not sections:
            raw = str(content.get("raw_text") or "").strip()
            sections = [{"title": "正文", "content": raw}] if raw else []

        if sections:
            first = sections[0]
            title = str(first.get("title") or "")
            body_lines = [ln for ln in str(first.get("content") or "").splitlines() if ln.strip()]
            # 去掉旧的同类联系行（含姓名/手机/邮箱关键词或 | 分隔的短行）
            kept: list[str] = []
            for ln in body_lines:
                if "|" in ln and len(ln) < 120 and any(k in ln for k in ("姓名", "手机", "邮箱", "电话", "@")):
                    continue
                if any(ln.strip().startswith(p) for p in ("姓名：", "手机：", "邮箱：", "电话：", "所在地：")):
                    continue
                kept.append(ln)
            first["content"] = "\n".join([contact_line] + kept) if contact_line else "\n".join(kept)
            first.setdefault("title", title or "基本信息")
            sections[0] = first
        elif contact_line:
            sections = [{"title": "基本信息", "content": contact_line}]

        raw_text = "\n\n".join(
            (f"{s.get('title')}\n{s.get('content')}" if s.get("title") else str(s.get("content") or "")).strip()
            for s in sections
        ).strip()
        return {"sections": sections, "raw_text": raw_text}


__all__ = [
    "ProfileResumeImportService",
    "ProfileResumeImportError",
]
