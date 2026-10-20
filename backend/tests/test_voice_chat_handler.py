"""语音对话处理器的归属与资源清理测试。"""

from __future__ import annotations

import json

import pytest

from app.llm.base import Response
from app.voice.chat_handler import VoiceChatHandler


class FakeProvider:
    def __init__(self, content: str = '{"overall_score": 88}'):
        self.content = content

    async def chat(self, messages, **kwargs) -> Response:
        return Response(content=self.content)


def make_handler() -> VoiceChatHandler:
    return VoiceChatHandler(provider=FakeProvider())


@pytest.mark.asyncio
async def test_feedback_enforces_user_and_source_session():
    handler = make_handler()
    result = handler.start_chat(
        {"job_title": "后端工程师"},
        {"name": "张三"},
        user_id=7,
        source_session_id="main-1",
    )
    session_id = result["session_id"]

    with pytest.raises(ValueError):
        await handler.get_feedback(session_id, user_id=8, source_session_id="main-1")
    with pytest.raises(ValueError):
        await handler.get_feedback(session_id, user_id=7, source_session_id="main-2")


@pytest.mark.asyncio
async def test_feedback_accepts_owner_and_parses_schema():
    handler = VoiceChatHandler(provider=FakeProvider(json.dumps({
        "overall_score": 91,
        "overall_assessment": {
            "strengths": ["表达清晰"],
            "weaknesses": ["深度不足"],
            "summary": "整体表现良好",
        },
        "dimension_scores": {"专业知识": 90},
        "suggestions": ["补充项目量化结果"],
    })))
    result = handler.start_chat({}, {}, user_id=7, source_session_id="main-1")
    report = await handler.get_feedback(
        result["session_id"], user_id=7, source_session_id="main-1"
    )
    assert report["overall_score"] == 91
    assert report["overall_assessment"]["summary"] == "整体表现良好"


def test_cleanup_expired_removes_old_sessions():
    handler = make_handler()
    result = handler.start_chat({}, {}, user_id=7)
    session = handler._sessions[result["session_id"]]
    session.created_at -= 3601

    handler.cleanup_expired()
    assert result["session_id"] not in handler._sessions
