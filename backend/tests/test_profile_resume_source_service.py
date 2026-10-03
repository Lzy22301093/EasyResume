"""统一简历画像数据源测试。"""

from __future__ import annotations

import json
from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models.database import Base
from app.models.orm import ProfileItem, User
from app.services.profile_resume_source_service import ProfileResumeSourceService


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestSession()
    session.add(User(username="u1", email="u1@test.com", hashed_password="x"))
    session.commit()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def _item(db: Session, category: str, title: str, content: str = "", payload: dict | None = None, status: str = "confirmed") -> ProfileItem:
    item = ProfileItem(
        user_id=1,
        category=category,
        title=title,
        content=content,
        payload_json=json.dumps(payload, ensure_ascii=False) if payload is not None else None,
        status=status,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def test_maps_basic_education_skill_and_split_experiences(db_session: Session):
    _item(db_session, "basic_info", "电话", "13800000000")
    _item(db_session, "basic_info", "出生日期", "1998-01-02")
    _item(db_session, "education", "北京交通大学", "旧文本", {
        "school": "北京交通大学", "degree": "本科", "major": "软件工程",
        "start": "2020-09", "end": "2024-06", "current": False, "gpa": "3.8",
        "rank": "10%", "courses": "数据结构",
    })
    _item(db_session, "skill", "Python", "熟练", {"name": "Python", "level": "熟练", "notes": "FastAPI"})
    _item(db_session, "experience", "后端实习生", "旧文本", {
        "exp_type": "internship", "company": "某公司", "title": "后端实习生",
        "start": "2023-01", "end": "2023-06", "current": False, "duration": "6 个月",
        "tech_stack": "Python", "duty": "接口开发", "achievement": "性能提升 20%",
        "situation": "接口慢", "task": "优化", "action": "重构", "result": "性能提升",
    })
    _item(db_session, "experience", "简历平台", "旧文本", {
        "exp_type": "project", "company": "", "title": "简历平台",
        "start": "2024-01", "end": "2024-03", "current": False, "duration": "3 个月",
        "tech_stack": "Vue", "duty": "前端开发", "achievement": "完成 8 个页面",
        "situation": "缺少工具", "task": "建设", "action": "开发", "result": "上线",
    })
    _item(db_session, "target", "后端开发", "理由", {
        "title": "后端开发", "reason": "理由", "detail": "匹配点", "source_type": "user_manual",
    })

    out = ProfileResumeSourceService().load(db_session, 1)
    assert out.basic_info["phone"] == "13800000000"
    assert out.basic_info["birthday"] == "1998-01-02"
    assert out.educations[0].courses == "数据结构"
    assert out.skills[0].name == "Python"
    assert out.internships[0].company == "某公司"
    assert out.projects[0].title == "简历平台"
    assert out.directions[0].source_type == "user_manual"
    assert len(out.source_item_ids) == 7
    assert out.profile_updated_at is not None


def test_phone_title_aliases(db_session: Session):
    _item(db_session, "basic_info", "手机号", "13900000000")
    out = ProfileResumeSourceService().load(db_session, 1)
    assert out.basic_info["phone"] == "13900000000"


def test_excludes_non_confirmed_items(db_session: Session):
    _item(db_session, "skill", "Python", status="suggested")
    out = ProfileResumeSourceService().load(db_session, 1)
    assert out.skills == []
    assert out.source_item_ids == []
    assert out.profile_updated_at is None


def test_legacy_items_are_mapped(db_session: Session):
    _item(db_session, "education", "北京交通大学", "学历：本科\n专业：软件工程\n主修课程：数据结构\n开始时间：2020-09\n结束时间：2024-06")
    _item(db_session, "skill", "Python", "熟练使用 FastAPI")
    _item(db_session, "experience", "项目负责人 | 某项目", "负责整体设计与交付")
    out = ProfileResumeSourceService().load(db_session, 1)
    assert out.educations[0].degree == "本科"
    assert out.educations[0].courses == "数据结构"
    assert out.skills[0].notes == "熟练使用 FastAPI"
    assert out.projects[0].company == "某项目"
    assert out.projects[0].duty == "负责整体设计与交付"


def test_soft_info_is_exposed_for_self_eval_import(db_session: Session):
    _item(db_session, "soft", "性格特点", "沉稳、有责任心")
    _item(db_session, "soft", "职业愿景", "成长为独立负责模块的工程师")
    _item(db_session, "soft", "不感兴趣的方向", "纯销售岗位")
    _item(db_session, "soft", "自我评价", "重视工程质量和长期价值")
    out = ProfileResumeSourceService().load(db_session, 1)
    assert out.soft_info == {
        "personality": "沉稳、有责任心",
        "vision": "成长为独立负责模块的工程师",
        "disinterested": "纯销售岗位",
        "self_eval": "重视工程质量和长期价值",
    }


def test_legacy_project_is_not_misclassified_as_internship(db_session: Session):
    _item(db_session, "experience", "智能简历平台", "使用 Vue 与 FastAPI 设计实现完整系统")
    out = ProfileResumeSourceService().load(db_session, 1)
    assert out.projects[0].title == "智能简历平台"
    assert out.internships == []
