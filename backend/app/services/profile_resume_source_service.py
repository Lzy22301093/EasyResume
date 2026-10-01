"""ProfileResumeSourceService — 把已确认个人画像映射为简历生成数据源。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session as DBSession

from app.models.orm import ProfileItem
from app.models.schemas import (
    ProfileResumeSource,
    ResumeDirectionData,
    ResumeEducationData,
    ResumeExperienceData,
    ResumeSkillData,
)
from app.services.profile_payload import load_profile_payload


def _text_field(content: str | None, label: str) -> str:
    for line in (content or "").splitlines():
        key, sep, value = line.partition("：")
        if sep and key.strip() == label:
            return value.strip()
    return ""


class ProfileResumeSourceService:
    """统一读取并规范化简历生成所需的画像字段。"""

    BASIC_TITLES = {
        "姓名": "name",
        "电话": "phone",
        "手机号": "phone",
        "邮箱": "email",
        "所在地": "location",
        "性别": "gender",
        "出生日期": "birthday",
        "国籍": "nationality",
        "家乡": "hometown",
    }

    def load(self, db: DBSession, user_id: int) -> ProfileResumeSource:
        items = (
            db.query(ProfileItem)
            .filter(
                ProfileItem.user_id == user_id,
                ProfileItem.status == "confirmed",
                ProfileItem.visibility.in_(["resume", "resume_interview"]),
            )
            .order_by(ProfileItem.sort_order.asc(), ProfileItem.id.asc())
            .all()
        )
        included: list[ProfileItem] = []
        basic_info: dict[str, str] = {}
        educations: list[ResumeEducationData] = []
        skills: list[ResumeSkillData] = []
        experiences: list[ResumeExperienceData] = []
        directions: list[ResumeDirectionData] = []

        for item in items:
            payload = load_profile_payload(item)
            if item.category == "basic_info":
                included.append(item)
                self._merge_basic_info(basic_info, item, payload)
            elif item.category == "education":
                included.append(item)
                educations.append(self._education(item, payload))
            elif item.category == "skill":
                included.append(item)
                skills.append(self._skill(item, payload))
            elif item.category == "experience":
                included.append(item)
                experiences.append(self._experience(item, payload))
            elif item.category == "target":
                included.append(item)
                directions.append(self._direction(item, payload))

        internships = [e for e in experiences if e.exp_type != "project"]
        projects = [e for e in experiences if e.exp_type == "project"]
        updated_values = [i.updated_at for i in included if i.updated_at is not None]
        return ProfileResumeSource(
            basic_info=basic_info,
            educations=educations,
            skills=skills,
            internships=internships,
            projects=projects,
            directions=directions,
            source_item_ids=[i.id for i in included],
            profile_updated_at=max(updated_values) if updated_values else None,
        )

    def _merge_basic_info(self, target: dict[str, str], item: ProfileItem, payload: dict[str, Any]) -> None:
        for key, value in payload.items():
            if key in {"name", "phone", "email", "location", "gender", "birthday", "nationality", "hometown"} and value:
                target[key] = str(value)
        key = self.BASIC_TITLES.get(item.title)
        if key and item.content and not target.get(key):
            target[key] = item.content

    @staticmethod
    def _education(item: ProfileItem, payload: dict[str, Any]) -> ResumeEducationData:
        return ResumeEducationData(
            school=str(payload.get("school") or (item.title if item.title != "教育经历" else "")),
            degree=str(payload.get("degree") or ""),
            major=str(payload.get("major") or ""),
            start=str(payload.get("start") or ""),
            end=str(payload.get("end") or ""),
            current=bool(payload.get("current", False)),
            gpa=str(payload.get("gpa") or ""),
            rank=str(payload.get("rank") or _text_field(item.content, "排名")),
            courses=str(payload.get("courses") or _text_field(item.content, "主修课程")),
        )

    @staticmethod
    def _skill(item: ProfileItem, payload: dict[str, Any]) -> ResumeSkillData:
        return ResumeSkillData(
            name=str(payload.get("name") or item.title or ""),
            level=str(payload.get("level") or ""),
            notes=str(payload.get("notes") or item.content or ""),
        )

    @staticmethod
    def _experience(item: ProfileItem, payload: dict[str, Any]) -> ResumeExperienceData:
        exp_type = str(payload.get("exp_type") or "").strip()
        if not exp_type or exp_type == "experience":
            exp_type = "project" if "项目" in f"{item.title}{item.content}" else "internship"
        return ResumeExperienceData(
            exp_type=exp_type,
            company=str(payload.get("company") or ""),
            title=str(payload.get("title") or item.title or ""),
            start=str(payload.get("start") or ""),
            end=str(payload.get("end") or ""),
            current=bool(payload.get("current", False)),
            duration=str(payload.get("duration") or ""),
            tech_stack=str(payload.get("tech_stack") or ""),
            duty=str(payload.get("duty") or item.content or ""),
            achievement=str(payload.get("achievement") or ""),
            situation=str(payload.get("situation") or ""),
            task=str(payload.get("task") or ""),
            action=str(payload.get("action") or ""),
            result=str(payload.get("result") or ""),
        )

    @staticmethod
    def _direction(item: ProfileItem, payload: dict[str, Any]) -> ResumeDirectionData:
        return ResumeDirectionData(
            id=item.id,
            title=str(payload.get("title") or item.title or ""),
            reason=str(payload.get("reason") or item.content or ""),
            detail=str(payload.get("detail") or ""),
            source_type=str(payload.get("source_type") or "user_manual"),
        )


__all__ = ["ProfileResumeSourceService"]
