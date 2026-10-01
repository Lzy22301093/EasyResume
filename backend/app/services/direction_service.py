"""DirectionService — 画像方向推荐、依据追踪与手工管理。"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session as DBSession

from app.models.orm import ProfileItem
from app.models.schemas import (
    DirectionCandidate,
    DirectionManualCreate,
    DirectionRecommendation,
    DirectionRecommendationResult,
    DirectionUpdate,
    EvidenceCreate,
    ProfileItemCreate,
    ProfileItemUpdate,
)
from app.services.profile_payload import dump_profile_payload, load_profile_payload
from app.services.profile_service import ProfileService, build_profile_context

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "你是资深职业规划师。请根据候选人的个人画像，分析并推荐 3~8 个适合他的岗位投递方向。\n"
    "要求：\n"
    "1. 每个方向给出岗位名称 title、推荐理由 reason、方向详情/匹配点说明 detail、依据 key basis_keys。\n"
    "2. reason 要结合画像中的技能、经历、教育、软性信息等，具体且可解释，不要空泛；"
    "detail 给出该方向的核心要求与候选人匹配点。\n"
    "3. basis_keys 只能使用输入中给出的 category:id key，不能编造来源；没有精确依据时返回空数组。\n"
    "4. 候选方向互不重复，覆盖不同职业赛道（技术/产品/数据/咨询/运营等）。\n"
    "5. 只输出 JSON，不要任何额外文字。JSON 结构："
    '{"directions": [{"title": "...", "reason": "...", "detail": "...", "basis_keys": ["skill:1"]}]}'
)

MAX_SELECT = 3
MAX_MANUAL_DIRECTIONS = 3


class DirectionError(ValueError):
    """方向业务错误。"""


class DirectionService:
    """画像方向推荐、保存选择与手工 CRUD。"""

    def __init__(self) -> None:
        self._profile = ProfileService()

    async def recommend_directions(
        self,
        db: DBSession,
        user_id: int,
        llm: Any,
    ) -> DirectionRecommendationResult:
        """基于已确认画像生成方向候选，并返回可解释依据。"""
        profile_ctx = build_profile_context(db, user_id)
        if not profile_ctx:
            raise DirectionError("暂无已确认画像，请先到个人画像完善并确认条目")

        from app.llm.structured import ainvoke_json_with_schema

        items = self._profile.list_items(db, user_id, status="confirmed")
        basis_map = {
            f"{item.category}:{item.id}": {
                "key": f"{item.category}:{item.id}",
                "item_id": item.id,
                "category": item.category,
                "title": item.title,
                "summary": item.content or item.title,
            }
            for item in items
        }
        user_content = (
            "候选人画像：\n"
            f"{_format_profile(profile_ctx)}\n\n"
            "可引用的画像依据 key：\n"
            + "\n".join(f"- {key}: {value['title']}" for key, value in basis_map.items())
            + "\n\n请给出 3~8 个适合的岗位投递方向。"
        )
        result = await ainvoke_json_with_schema(
            llm,
            system_prompt=SYSTEM_PROMPT,
            user_content=user_content,
            schema=DirectionRecommendation,
            max_attempts=2,
            temperature=0.5,
            max_tokens=2048,
        )

        seen: set[str] = set()
        candidates: list[dict[str, Any]] = []
        used_basis: dict[str, dict[str, Any]] = {}
        for d in result.directions:
            title = (d.title or "").strip()
            if not title or title in seen:
                continue
            seen.add(title)
            valid_keys = []
            for key in d.basis_keys or []:
                if key in basis_map and key not in valid_keys:
                    valid_keys.append(key)
                    used_basis[key] = basis_map[key]
            candidates.append({
                "title": title,
                "reason": (d.reason or "").strip(),
                "detail": (d.detail or "").strip(),
                "basis_keys": valid_keys,
            })
        if not candidates:
            raise DirectionError("画像分析未生成有效的岗位方向，请重试")
        return DirectionRecommendationResult(
            directions=candidates,
            basis=list(used_basis.values()),
            profile_updated_at=max((i.updated_at for i in items if i.updated_at), default=None),
        )

    def confirm_directions(
        self,
        db: DBSession,
        user_id: int,
        selected: list[DirectionCandidate],
    ) -> list[ProfileItem]:
        """把用户选中的 AI 方向写成 target 分类的 confirmed 画像条目。"""
        cleaned = self._clean_candidates(selected, require_reason=False)
        if not cleaned:
            raise DirectionError("请至少选择一个岗位方向")
        if len(cleaned) > MAX_SELECT:
            raise DirectionError(f"最多只能选择 {MAX_SELECT} 个方向")

        saved: list[ProfileItem] = []
        for sel in cleaned:
            exists = self._find_target(db, user_id, sel.title)
            if exists:
                saved.append(exists)
                continue
            item = self._profile.create_item(
                db,
                user_id,
                ProfileItemCreate(
                    category="target",
                    title=sel.title,
                    content=(sel.reason or None),
                    payload_json={
                        "title": sel.title,
                        "reason": sel.reason,
                        "detail": sel.detail,
                        "source_type": "ai_recommendation",
                        "basis_keys": sel.basis_keys,
                    },
                    item_type="fact",
                    status="confirmed",
                    visibility="resume_interview",
                ),
            )
            self._profile.add_evidence(
                db,
                user_id,
                item.id,
                EvidenceCreate(
                    source_type="user_input",
                    quote=f"选择投递方向：{sel.title}",
                    verified_by_user=True,
                ),
            )
            saved.append(item)
        return saved

    def list_directions(self, db: DBSession, user_id: int) -> list[dict[str, Any]]:
        """列出 confirmed 投递方向，供前端统一管理。"""
        output = []
        for item in self._profile.list_items(db, user_id, category="target", status="confirmed"):
            payload = load_profile_payload(item)
            output.append({
                "id": item.id,
                "title": item.title,
                "reason": payload.get("reason") or item.content or "",
                "detail": payload.get("detail") or "",
                "source_type": payload.get("source_type") or "user_manual",
                "basis_keys": payload.get("basis_keys") or [],
            })
        return output

    def create_manual_direction(
        self,
        db: DBSession,
        user_id: int,
        data: DirectionManualCreate | dict[str, Any],
    ) -> ProfileItem:
        """新增用户手动投递方向。"""
        title, reason, detail = self._manual_values(data)
        self._ensure_unique_target(db, user_id, title)
        count = self._active_target_count(db, user_id)
        if count >= MAX_MANUAL_DIRECTIONS:
            raise DirectionError(f"最多只能保存 {MAX_MANUAL_DIRECTIONS} 个方向")
        item = self._profile.create_item(
            db,
            user_id,
            ProfileItemCreate(
                category="target",
                title=title,
                content=reason or None,
                payload_json={"title": title, "reason": reason, "detail": detail, "source_type": "user_manual", "basis_keys": []},
                item_type="fact",
                status="confirmed",
                visibility="resume_interview",
            ),
        )
        self._profile.add_evidence(
            db,
            user_id,
            item.id,
            EvidenceCreate(source_type="user_input", quote=f"手动添加投递方向：{title}", verified_by_user=True),
        )
        return item

    def update_direction(
        self,
        db: DBSession,
        user_id: int,
        item_id: int,
        data: DirectionUpdate | dict[str, Any],
    ) -> ProfileItem:
        """编辑已有投递方向，保留 AI/手动来源。"""
        item = self._profile.get_item(db, user_id, item_id)
        if item.category != "target":
            raise DirectionError("该画像条目不是投递方向")
        current = load_profile_payload(item)
        values = data.model_dump(exclude_unset=True) if isinstance(data, DirectionUpdate) else dict(data or {})
        title = str(values.get("title") or item.title).strip()
        reason = values.get("reason", current.get("reason") or item.content or "")
        detail = values.get("detail", current.get("detail") or "")
        self._ensure_unique_target(db, user_id, title, exclude_id=item_id)
        payload = {
            **current,
            "title": title,
            "reason": str(reason or "").strip(),
            "detail": str(detail or "").strip(),
            "source_type": current.get("source_type") or "user_manual",
            "basis_keys": current.get("basis_keys") or [],
        }
        return self._profile.update_item(
            db,
            user_id,
            item_id,
            ProfileItemUpdate(title=title, content=payload["reason"] or None, payload_json=payload),
        )

    def delete_direction(self, db: DBSession, user_id: int, item_id: int) -> None:
        """删除投递方向。"""
        item = self._profile.get_item(db, user_id, item_id)
        if item.category != "target":
            raise DirectionError("该画像条目不是投递方向")
        self._profile.delete_item(db, user_id, item_id)

    @staticmethod
    def _clean_candidates(selected: list[DirectionCandidate], require_reason: bool) -> list[DirectionCandidate]:
        cleaned: list[DirectionCandidate] = []
        seen: set[str] = set()
        for sel in selected or []:
            title = (sel.title or "").strip()
            if not title or title in seen:
                continue
            if require_reason and not (sel.reason or "").strip():
                continue
            seen.add(title)
            cleaned.append(sel.model_copy(update={
                "title": title,
                "reason": (sel.reason or "").strip(),
                "detail": (sel.detail or "").strip(),
                "basis_keys": [str(k) for k in (sel.basis_keys or [])],
            }))
        return cleaned

    @staticmethod
    def _manual_values(data: DirectionManualCreate | dict[str, Any]) -> tuple[str, str, str]:
        values = data.model_dump() if isinstance(data, DirectionManualCreate) else dict(data or {})
        title = str(values.get("title") or "").strip()
        if not title:
            raise DirectionError("方向名称不能为空")
        return title, str(values.get("reason") or "").strip(), str(values.get("detail") or "").strip()

    def _active_target_count(self, db: DBSession, user_id: int) -> int:
        return len(self._profile.list_items(db, user_id, category="target", status="confirmed"))

    def _ensure_unique_target(self, db: DBSession, user_id: int, title: str, exclude_id: int | None = None) -> None:
        for item in self._profile.list_items(db, user_id, category="target", status="confirmed"):
            if item.id != exclude_id and item.title == title:
                raise DirectionError("已存在同名投递方向")

    def _find_target(self, db: DBSession, user_id: int, title: str) -> ProfileItem | None:
        return next((i for i in self._profile.list_items(db, user_id, category="target", status="confirmed") if i.title == title), None)


def _format_profile(ctx: dict[str, Any]) -> str:
    """把 profile 形态上下文格式化为可读文本（供 LLM 分析）。"""
    parts: list[str] = []
    if ctx.get("name"):
        parts.append(f"姓名：{ctx['name']}")
    if ctx.get("summary"):
        parts.append(f"个人简介：{ctx['summary']}")
    if ctx.get("skills"):
        parts.append(f"技能：{', '.join(str(s) for s in ctx['skills'])}")
    if ctx.get("education"):
        parts.append(f"教育经历：{'; '.join(str(e) for e in ctx['education'])}")
    if ctx.get("experience"):
        parts.append("项目/工作经历：\n" + "\n".join(f"- {e}" for e in ctx["experience"]))
    if ctx.get("certifications"):
        parts.append(f"证书/奖项：{'; '.join(str(c) for c in ctx['certifications'])}")
    if ctx.get("social"):
        parts.append(f"社交账号：{'; '.join(str(s) for s in ctx['social'])}")
    if ctx.get("target_roles"):
        parts.append(f"现有目标方向：{', '.join(str(t) for t in ctx['target_roles'])}")
    if ctx.get("gaps"):
        parts.append(f"待补强：{', '.join(str(g) for g in ctx['gaps'])}")
    return "\n".join(parts)


__all__ = ["DirectionService", "DirectionError"]
