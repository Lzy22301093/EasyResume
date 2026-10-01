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
