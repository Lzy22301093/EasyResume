"""面试身份边界测试 — REST/WebSocket 不得越权访问他人面试。"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient


class FakeInterviewHandler:
    def __init__(self, state):
        self.state = state
        self.answer_calls = []

    async def get_state(self, interview_id: str):
        return self.state if interview_id == "interview-1" else None

    async def process_answer(self, interview_id: str, answer: str):
        self.answer_calls.append((interview_id, answer))
        return {"question": "下一题", "is_complete": False, "report": None}


@pytest.fixture
async def client():
    from app.api.auth import require_auth
    from app.main import app

    app.dependency_overrides[require_auth] = lambda: {"id": 777, "is_active": True}
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c
    finally:
        app.dependency_overrides.pop(require_auth, None)


async def test_interview_endpoints_enforce_ownership(client: AsyncClient):
    import app.api.interview as interview_api

    handler = FakeInterviewHandler({
        "user_id": 888,
        "is_complete": True,
        "is_active": False,
        "turn_count": 1,
        "phase": "done",
        "current_question": "",
        "dimension_scores": {},
        "difficulty_level": "medium",
        "final_report": {"overall_score": 80},
    })
    interview_api.set_handler(handler)
    try:
        assert (await client.get("/api/interview/interview-1")).status_code == 404
        assert (await client.get("/api/interview/interview-1/report")).status_code == 404
        answer = await client.post(
            "/api/interview/interview-1/answer",
            json={"answer": "我的回答"},
        )
        assert answer.status_code == 404
        assert handler.answer_calls == []
    finally:
        interview_api.set_handler(None)


async def test_interview_endpoints_allow_owner(client: AsyncClient):
    import app.api.interview as interview_api

    handler = FakeInterviewHandler({
        "user_id": 777,
        "is_complete": True,
        "is_active": False,
        "turn_count": 1,
        "phase": "done",
        "current_question": "",
        "dimension_scores": {},
        "difficulty_level": "medium",
        "final_report": {"overall_score": 80},
    })
    interview_api.set_handler(handler)
    try:
        assert (await client.get("/api/interview/interview-1")).status_code == 200
        assert (await client.get("/api/interview/interview-1/report")).status_code == 200
    finally:
        interview_api.set_handler(None)


class FakeWebSocket:
    def __init__(self, messages):
        self.messages = list(messages)
        self.sent = []
        self.closed_code = None

    async def receive_text(self):
        return self.messages.pop(0)

    async def send_text(self, text: str):
        self.sent.append(text)

    async def close(self, code: int = 1000):
        self.closed_code = code


async def test_ws_auth_reads_token_from_first_message():
    from app.voice.gateway import _authenticate_ws

    ws = FakeWebSocket(['{"type":"auth","token":"valid-token"}'])
    with (
        patch("app.voice.gateway.AuthService.decode_token", return_value={"sub": "7"}),
        patch("app.voice.gateway.AuthService.get_user_by_id", return_value={"id": 7, "is_active": True}),
    ):
        user = await _authenticate_ws(ws)

    assert user == {"id": 7, "is_active": True}
    assert ws.closed_code is None


async def test_ws_auth_rejects_missing_or_invalid_token():
    from app.voice.gateway import _authenticate_ws

    ws = FakeWebSocket(['{"type":"start"}'])
    user = await _authenticate_ws(ws)
    assert user is None
    assert ws.closed_code == 4401

    ws = FakeWebSocket(['{"type":"auth","token":"bad"}'])
    with patch("app.voice.gateway.AuthService.decode_token", return_value=None):
        user = await _authenticate_ws(ws)
    assert user is None
    assert ws.closed_code == 4401


class FakeJdLLM:
    def __init__(self, content: str):
        self.content = content

    async def chat(self, messages, **kwargs):
        from app.llm.base import Response

        return Response(content=self.content)


async def test_interview_jd_analysis_uses_real_schema(client: AsyncClient):
    import app.api.interview as interview_api

    payload = {
        "job_title": "后端开发实习生",
        "company": "示例公司",
        "requirements": [
            {"category": "skill", "content": "熟悉 Python", "importance": "high"}
        ],
        "nice_to_have": ["了解 Docker"],
        "summary": "负责后端服务开发",
    }
    with patch(
        "app.api.interview.create_llm_provider",
        return_value=FakeJdLLM(json.dumps(payload, ensure_ascii=False)),
    ):
        resp = await client.post(
            "/api/interview/jd-analysis",
            json={"jd_text": "岗位职责：开发接口", "job_title": "后端开发实习生", "company": "示例公司"},
        )

    assert resp.status_code == 200
    assert resp.json()["job_title"] == "后端开发实习生"


async def test_interview_jd_analysis_rejects_invalid_llm_output(client: AsyncClient):
    with patch(
        "app.api.interview.create_llm_provider",
        return_value=FakeJdLLM("不是合法 JSON"),
    ):
        resp = await client.post(
            "/api/interview/jd-analysis",
            json={"jd_text": "岗位职责：开发接口"},
        )

    assert resp.status_code == 502
    assert "JD 分析结果格式无效" in resp.json()["detail"]
