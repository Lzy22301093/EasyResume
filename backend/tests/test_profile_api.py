"""个人画像 API 中的统一简历数据源测试。"""

from __future__ import annotations

import json

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.api import profile as profile_api
from app.models.database import Base, get_db
from app.models.orm import ProfileItem, User


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
async def client(db_session: Session):
    app = FastAPI()
    app.include_router(profile_api.router, prefix="/api/profile")
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[profile_api.require_auth] = lambda: {"id": 1}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def test_api_returns_resume_source(client: AsyncClient, db_session: Session):
    db_session.add(ProfileItem(
        user_id=1,
        category="basic_info",
        title="电话",
        content="13800000000",
        payload_json=json.dumps({"phone": "13800000000"}, ensure_ascii=False),
        status="confirmed",
    ))
    db_session.commit()

    resp = await client.get("/api/profile/resume-source")
    assert resp.status_code == 200
    data = resp.json()
    assert data["basic_info"]["phone"] == "13800000000"
    assert data["educations"] == []
    assert data["skills"] == []
    assert data["internships"] == []
    assert data["projects"] == []
    assert data["directions"] == []
    assert len(data["source_item_ids"]) == 1


async def test_direction_api_manual_crud(client: AsyncClient):
    created = await client.post("/api/profile/directions/manual", json={
        "title": "产品运营",
        "reason": "希望结合内容与用户增长",
        "detail": "重点投递内容运营岗位",
    })
    assert created.status_code == 201
    item = created.json()
    assert item["payload_json"]["source_type"] == "user_manual"

    listed = await client.get("/api/profile/directions")
    assert listed.status_code == 200
    assert listed.json()[0]["title"] == "产品运营"

    updated = await client.patch(f"/api/profile/directions/{item['id']}", json={
        "title": "用户运营",
        "reason": "结合用户增长经验",
        "detail": "更新详情",
    })
    assert updated.status_code == 200
    assert updated.json()["title"] == "用户运营"

    deleted = await client.delete(f"/api/profile/directions/{item['id']}")
    assert deleted.status_code == 204
    assert (await client.get("/api/profile/directions")).json() == []


async def test_resume_import_apply_writes_profile(client: AsyncClient, db_session: Session):
    resp = await client.post("/api/profile/resume-import/apply", json={
        "source_filename": "cv.pdf",
        "basic_fields": [
            {"key": "name", "value": "赵六", "quote": "赵六", "confidence": 0.9},
        ],
        "summary": "踏实靠谱",
        "education": [
            {"school": "复旦大学", "degree": "硕士", "major": "软件工程"},
        ],
        "skills": [{"name": "Go"}],
        "awards": ["优秀毕业生"],
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["written"]["basic_info"] == 1
    assert data["written"]["education"] == 1
    assert data["written"]["skill"] == 1
    assert "已导入" in data["message"]

    items = (await client.get("/api/profile/items")).json()
    titles = {i["title"] for i in items}
    assert "姓名" in titles
    assert "复旦大学" in titles
    assert "Go" in titles
    name = next(i for i in items if i["title"] == "姓名")
    assert name["content"] == "赵六"
    assert name["evidences"] and name["evidences"][0]["source_type"] == "resume"


async def test_resume_import_apply_empty_payload(client: AsyncClient):
    resp = await client.post("/api/profile/resume-import/apply", json={})
    assert resp.status_code == 201
    assert resp.json()["written"] == {}
