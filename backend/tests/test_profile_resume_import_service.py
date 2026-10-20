"""简历附件导入个人画像：抽取清洗 + 确认写入（增量 merge）。"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models.database import Base
from app.models.orm import ProfileItem, User
from app.models.schemas import (
    ResumeImportApplyRequest,
    ResumeImportBasicField,
    ResumeImportEducation,
    ResumeImportExperience,
    ResumeImportExtract,
    ResumeImportSkill,
)
from app.services.profile_resume_import_service import (
    ProfileResumeImportError,
    ProfileResumeImportService,
)


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


@pytest.fixture
def svc():
    return ProfileResumeImportService()


def test_sanitize_extract_drops_invalid_and_duplicates(svc: ProfileResumeImportService):
    extract = ResumeImportExtract(
        basic_fields=[
            ResumeImportBasicField(key="name", value="张三", quote="张三", confidence=0.9),
            ResumeImportBasicField(key="not_a_key", value="x"),
            ResumeImportBasicField(key="phone", value="  "),
        ],
        education=[ResumeImportEducation(school=""), ResumeImportEducation(school="北大")],
        experiences=[
            ResumeImportExperience(company="A", exp_type="weird"),
            ResumeImportExperience(role=""),
        ],
        skills=[
            ResumeImportSkill(name="Python"),
            ResumeImportSkill(name="Python"),
            ResumeImportSkill(name="  "),
        ],
        awards=["", " 国家奖学金 "],
        summary="  靠谱  ",
    )
    svc._sanitize_extract(extract)

    assert [f.key for f in extract.basic_fields] == ["name"]
    assert [e.school for e in extract.education] == ["北大"]
    assert extract.experiences[0].exp_type == "internship"
    assert len(extract.experiences) == 1
    assert [s.name for s in extract.skills] == ["Python"]
    assert extract.awards == ["国家奖学金"]
    assert extract.summary == "靠谱"


def test_apply_writes_confirmed_fields_with_resume_evidence(db_session: Session, svc: ProfileResumeImportService):
    result = svc.apply(
        db_session,
        1,
        ResumeImportApplyRequest(
            source_filename="我的简历.pdf",
            basic_fields=[
                ResumeImportBasicField(key="name", value="李四", quote="李四 / 男"),
                ResumeImportBasicField(key="bad_key", value="x"),
            ],
            summary="认真负责",
            summary_quote="自我评价：认真负责",
            education=[
                ResumeImportEducation(school="清华大学", degree="本科", major="计算机", quote="清华大学 计算机")
            ],
            experiences=[
                ResumeImportExperience(
                    exp_type="internship",
                    company="某公司",
                    role="后端实习生",
                    duty="负责接口开发",
                    quote="某公司 后端实习生",
                )
            ],
            skills=[ResumeImportSkill(name="Python", quote="熟悉 Python")],
            awards=["国家奖学金", "国家奖学金"],
        ),
    )

    assert result.written["basic_info"] == 1
    assert result.written["education"] == 1
    assert result.written["experience"] == 1
    assert result.written["skill"] == 1
    assert result.written["award"] == 1
    assert result.skipped == 1

    items = db_session.query(ProfileItem).filter(ProfileItem.user_id == 1).all()
    by_cat = {}
    for i in items:
        by_cat.setdefault(i.category, []).append(i)

    name_item = next(i for i in by_cat["basic_info"] if i.title == "姓名")
    assert name_item.content == "李四"
    assert name_item.status == "confirmed"
    assert name_item.evidences and name_item.evidences[0].source_type == "resume"
    assert name_item.evidences[0].source_id == "我的简历.pdf"

    soft = next(i for i in by_cat["soft"] if i.title == "自我评价")
    assert soft.content == "认真负责"

    award = next(i for i in by_cat["award"] if i.title == "个人奖项")
    assert award.content == "国家奖学金"

    skill = by_cat["skill"][0]
    assert skill.title == "Python"

    exp = by_cat["experience"][0]
    from app.services.profile_payload import load_profile_payload

    payload = load_profile_payload(exp)
    assert "公司" in (payload.get("company") or "")


def test_apply_merges_awards_and_skips_empty(db_session: Session, svc: ProfileResumeImportService):
    first = svc.apply(
        db_session,
        1,
        ResumeImportApplyRequest(awards=["国家奖学金"], skills=[ResumeImportSkill(name="")]),
    )
    assert first.skipped == 1
    assert first.written["award"] == 1

    result = svc.apply(
        db_session,
        1,
        ResumeImportApplyRequest(awards=["国家奖学金", "挑战杯一等奖"]),
    )
    assert result.written["award"] == 2
    award = (
        db_session.query(ProfileItem)
        .filter(ProfileItem.user_id == 1, ProfileItem.category == "award")
        .one()
    )
    lines = award.content.splitlines()
    assert lines.count("国家奖学金") == 1
    assert "挑战杯一等奖" in lines
    assert result.skipped == 0


async def test_parse_text_rejects_short_file(svc: ProfileResumeImportService):
    import base64

    with pytest.raises(ProfileResumeImportError, match="足够的文本"):
        await svc._parse_text(base64.b64encode(b"hi").decode(), "a.txt")


async def test_preview_parses_txt_and_calls_llm(db_session: Session, svc: ProfileResumeImportService):
    import base64

    class FakeLLM:
        pass

    extract = ResumeImportExtract(
        basic_fields=[ResumeImportBasicField(key="name", value="王五", quote="王五")],
        confidence=0.9,
    )

    async def fake_extract(llm, text, model=None):
        assert "王五" in text
        return extract

    svc._extract = fake_extract  # type: ignore[method-assign]
    out = await svc.preview(
        db_session,
        1,
        FakeLLM(),
        file_content_b64=base64.b64encode(
            "个人简历\n姓名：王五\n电话：13800000000\n邮箱：w@t.com\n教育经历：北京大学 计算机本科".encode()
        ).decode(),
        filename="cv.txt",
    )
    assert out.filename == "cv.txt"
    assert out.text_length > 0
    assert out.extract.basic_fields[0].value == "王五"


def test_build_form_draft_maps_extract_for_wizard(svc: ProfileResumeImportService):
    extract = ResumeImportExtract(
        basic_fields=[ResumeImportBasicField(key="name", value="赵一"), ResumeImportBasicField(key="phone", value="139")],
        summary="踏实",
        education=[ResumeImportEducation(school="北大", degree="本科", major="CS")],
        experiences=[
            ResumeImportExperience(exp_type="project", company="X 平台", role="开发", duty="写代码"),
            ResumeImportExperience(exp_type="internship", company="Y 公司", role="实习生"),
        ],
        skills=[ResumeImportSkill(name="Python", notes="熟悉")],
        awards=["国奖"],
    )
    draft = svc.build_form_draft(extract)
    assert draft["basic_info"]["name"] == "赵一"
    assert draft["education"][0]["school"] == "北大"
    assert draft["awards"] == "国奖"
    cats = [e["category"] for e in draft["extra"]]
    assert "project" in cats and "internship" in cats and "skill" in cats
    assert draft["summary"] == "踏实"


def test_merge_contact_into_content_replaces_old_contact_lines():
    content = {
        "sections": [
            {
                "title": "基本信息",
                "content": "张三\n手机：111\n邮箱：old@x.com\n熟悉 Vue",
            }
        ],
        "raw_text": "",
    }
    out = ProfileResumeImportService._merge_contact_into_content(
        content, {"name": "李四", "phone": "222", "email": "new@x.com"}
    )
    body = out["sections"][0]["content"]
    assert "李四" in body and "222" in body and "new@x.com" in body
    assert "old@x.com" not in body
    assert "熟悉 Vue" in body
    assert out["raw_text"]


def test_sync_to_library_creates_new_version(db_session: Session, svc: ProfileResumeImportService):
    import json

    from app.models.orm import ResumeDocument, ResumeVersion
    from app.services.resume_library_service import ResumeLibraryService

    doc = ResumeDocument(user_id=1, title="投递版", source="upload")
    db_session.add(doc)
    db_session.flush()
    ver = ResumeVersion(
        document_id=doc.id,
        user_id=1,
        version=1,
        content_json=json.dumps(
            {"sections": [{"title": "基本信息", "content": "王五\n手机：000"}], "raw_text": "王五\n手机：000"},
            ensure_ascii=False,
        ),
    )
    db_session.add(ver)
    db_session.flush()
    doc.current_version_id = ver.id
    db_session.commit()

    result = svc.sync_to_library(
        db_session,
        1,
        document_id=doc.id,
        fields={"name": "王五", "email": "w@t.com", "bad": "x"},
    )
    assert result["version"] == 2
    assert set(result["changed_fields"]) == {"name", "email"}

    lib = ResumeLibraryService()
    v2 = lib.get_version(db_session, 1, result["version_id"])
    content = json.loads(v2.content_json)
    assert "w@t.com" in content["raw_text"]
    assert doc.current_version_id == v2.id


async def test_preview_from_document_uses_library_text(db_session: Session, svc: ProfileResumeImportService):
    import json

    from app.models.orm import ResumeDocument, ResumeVersion

    doc = ResumeDocument(user_id=1, title="库内简历", source="upload")
    db_session.add(doc)
    db_session.flush()
    long_text = "姓名：钱六\n电话：13700001111\n邮箱：q@t.com\n教育经历：清华大学 计算机科学与技术 本科\n" + "项目经历描述" * 10
    ver = ResumeVersion(
        document_id=doc.id,
        user_id=1,
        version=1,
        content_json=json.dumps({"sections": [], "raw_text": long_text}, ensure_ascii=False),
    )
    db_session.add(ver)
    db_session.flush()
    doc.current_version_id = ver.id
    db_session.commit()

    extract = ResumeImportExtract(
        basic_fields=[ResumeImportBasicField(key="name", value="钱六")],
        confidence=0.8,
    )

    async def fake_extract(llm, text, model=None):
        assert "钱六" in text
        return extract

    svc._extract = fake_extract  # type: ignore[method-assign]

    preview = await svc.preview_from_document(db_session, 1, object(), document_id=doc.id)
    assert preview.filename.startswith("简历库")
    assert preview.extract.basic_fields[0].value == "钱六"
