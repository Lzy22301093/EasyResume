"""结构化面试计划与计划驱动出题测试。"""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.agents.evaluator import EvaluatorAgent
from app.interview.nodes import (
    ask_question_node,
    build_opening,
    evaluate_node,
    open_interview_node,
)
from app.interview.plan import InterviewPlanOutput, _clean_items
from app.llm.structured import parse_structured_json


PLAN_ITEMS = [
    {
        "topic_id": "topic-1",
        "question_id": "q-1",
        "topic": "项目鉴权",
        "category": "project_deep_dive",
        "difficulty": "medium",
        "question": "请介绍你在项目中设计的鉴权方案。",
        "answer_points": ["认证方式", "权限边界"],
        "evidence_refs": ["简历：权限项目"],
        "follow_ups": ["如果 token 被盗用，你如何处理？"],
    },
    {
        "topic_id": "topic-2",
        "question_id": "q-2",
        "topic": "TypeScript 类型设计",
        "category": "technical",
        "difficulty": "hard",
        "question": "如何为复杂表单设计可维护的 TypeScript 类型？",
        "answer_points": ["泛型", "收窄", "约束"],
        "evidence_refs": ["JD：TypeScript"],
        "follow_ups": ["类型体操会不会影响可维护性？"],
    },
]


def test_plan_schema_and_stable_ids():
    raw = """
    {
      "items": [
        {
          "topic": "项目鉴权",
          "category": "project_deep_dive",
          "difficulty": "medium",
          "question": "请介绍你在项目中设计的鉴权方案。",
          "answer_points": ["认证方式", "权限边界"],
          "evidence_refs": ["简历：权限项目"],
          "follow_ups": ["token 被盗用后如何处理？"]
        }
      ]
    }
    """
    parsed = parse_structured_json(raw, InterviewPlanOutput)
    items = _clean_items(parsed)

    assert items[0]["topic_id"] == "topic-1"
    assert items[0]["question_id"] == "q-1"
    assert items[0]["answer_points"] == ["认证方式", "权限边界"]


@pytest.mark.asyncio
async def test_open_interview_uses_plan_without_second_question_call(monkeypatch):
    async def fake_plan(llm, state, *, model=None):
        assert model == "test-model"
        return [dict(PLAN_ITEMS[0]), dict(PLAN_ITEMS[1])]

    monkeypatch.setattr("app.interview.plan.build_interview_plan", fake_plan)
    interviewer = SimpleNamespace(
        llm=object(),
        model="test-model",
        run=AsyncMock(),
    )

    result = await open_interview_node(
        {
            "jd_analysis": {"job_title": "前端工程师", "company": "测试公司"},
            "profile": {},
            "resume": {},
            "target_position": "前端工程师",
            "referenced_questions": [],
            "difficulty_level": "medium",
            "max_turns": 8,
        },
        {"interviewer": interviewer},
    )

    assert result["opening_text"] == "你好，我是测试公司的面试官，今天面试前端工程师这个岗位。我们开始吧。"
    assert result["current_question"] == PLAN_ITEMS[0]["question"]
    assert result["current_question_id"] == "q-1"
    assert result["asked_question_ids"] == ["q-1"]
    assert result["pending_topic_ids"] == ["topic-2"]
    interviewer.run.assert_not_called()


@pytest.mark.asyncio
async def test_plan_driven_switch_and_follow_up_do_not_repeat_questions():
    base_state = {
        "interview_plan": [dict(PLAN_ITEMS[0]), dict(PLAN_ITEMS[1])],
        "current_plan_item": dict(PLAN_ITEMS[0]),
        "asked_question_ids": ["q-1"],
        "pending_topic_ids": ["topic-2"],
        "covered_topic_ids": [],
        "conversation_history": [],
        "difficulty_level": "medium",
        "turn_count": 1,
    }

    switched = await ask_question_node(
        base_state,
        {"interviewer": SimpleNamespace(run=AsyncMock())},
    )
    assert switched["current_question_id"] == "q-2"
    assert switched["current_question"] == PLAN_ITEMS[1]["question"]
    assert switched["pending_topic_ids"] == []

    followed = await ask_question_node(
        {
            **base_state,
            "current_evaluation": {"next_action": "追问"},
        },
        {"interviewer": SimpleNamespace(run=AsyncMock())},
    )
    assert followed["current_question_id"] == "topic-1-follow-1"
    assert followed["current_question"] == PLAN_ITEMS[0]["follow_ups"][0]
    assert followed["asked_question_ids"] == ["q-1", "topic-1-follow-1"]


@pytest.mark.asyncio
async def test_evaluator_receives_answer_points_and_tracks_topic():
    evaluator = SimpleNamespace(
        run=AsyncMock(return_value={
            "topic_id": "topic-1",
            "score": 8.5,
            "dimension_scores": {"专业知识": 8.0},
            "evidence": ["说明了 JWT"],
            "missing_points": ["未说明刷新机制"],
            "strengths": ["结构清晰"],
            "weaknesses": ["细节不足"],
            "next_action": "切换话题",
            "next_topic_id": "topic-2",
        })
    )
    state = {
        "current_question": PLAN_ITEMS[0]["question"],
        "current_answer": "我使用了 JWT，并在网关统一校验。",
        "current_plan_item": dict(PLAN_ITEMS[0]),
        "difficulty_level": "medium",
        "turn_count": 0,
        "max_turns": 8,
        "covered_topics": [],
        "pending_topics": [],
        "covered_topic_ids": [],
        "pending_topic_ids": ["topic-2"],
        "dimension_scores": {},
        "conversation_history": [],
        "referenced_questions": [],
    }

    result = await evaluate_node(state, {"evaluator": evaluator})

    kwargs = evaluator.run.await_args.kwargs
    assert kwargs["answer_points"] == ["认证方式", "权限边界"]
    assert kwargs["current_plan_item"]["topic_id"] == "topic-1"
    assert result["covered_topic_ids"] == ["topic-1"]
    assert result["current_evaluation"]["missing_points"] == ["未说明刷新机制"]
    assert result["evaluation_evidence"][0]["evidence"] == ["说明了 JWT"]
    assert result["evaluation_evidence"][0]["question_id"] is None


def test_evaluator_prompt_requires_evidence_and_forbids_question_generation():
    evaluator = EvaluatorAgent(llm=SimpleNamespace())
    messages = evaluator.build_messages(
        current_question="请介绍鉴权方案。",
        current_answer="使用 JWT。",
        current_plan_item=dict(PLAN_ITEMS[0]),
        answer_points=PLAN_ITEMS[0]["answer_points"],
        target_position="前端工程师",
    )

    prompt = messages[1].content
    assert "answer_points" in prompt
    assert "evidence" in prompt
    assert "不要生成下一题" in prompt


def test_build_opening_is_shared_and_deterministic():
    text = build_opening({"company": "示例公司", "job_title": "后端工程师"})
    assert text == "你好，我是示例公司的面试官，今天面试后端工程师这个岗位。我们开始吧。"


@pytest.mark.asyncio
async def test_build_interview_plan_passes_reference_answer_points(monkeypatch):
    captured = {}

    async def fake_structured(llm, system_prompt, user_content, schema, **kwargs):
        captured["user_content"] = user_content
        return InterviewPlanOutput.model_validate({
            "items": [{
                "topic": "React 性能优化",
                "category": "technical",
                "difficulty": "medium",
                "question": "如何定位 React 页面的重渲染问题？",
                "answer_points": ["Profiler", "memo"],
                "evidence_refs": [],
                "follow_ups": [],
            }]
        })

    monkeypatch.setattr("app.interview.plan.ainvoke_json_with_schema", fake_structured)
    from app.interview.plan import build_interview_plan

    items = await build_interview_plan(
        SimpleNamespace(),
        {
            "jd_analysis": {"job_title": "前端工程师"},
            "resume": {},
            "profile": {},
            "target_position": "前端工程师",
            "max_turns": 8,
            "referenced_questions": ["如何优化 React 性能？"],
            "referenced_question_items": [{
                "question": "如何优化 React 性能？",
                "answer_points": ["识别瓶颈", "减少重渲染"],
                "difficulty": "medium",
            }],
        },
    )

    assert items[0]["question_id"] == "q-1"
    assert "要点：识别瓶颈、减少重渲染" in captured["user_content"]
