"""Interview Graph 节点实现。"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from app.interview.state import InterviewState

logger = logging.getLogger(__name__)


def build_opening(jd_analysis: dict[str, Any] | None, target_position: str | None = None) -> str:
    """构建确定性开场白，供图节点与 WebSocket 提前播报复用。"""
    jd = jd_analysis or {}
    target = (target_position or str(jd.get("job_title") or "该岗位")).strip() or "该岗位"
    company = str(jd.get("company") or "我们公司").strip() or "我们公司"
    return f"你好，我是{company}的面试官，今天面试{target}这个岗位。我们开始吧。"


async def open_interview_node(
    state: InterviewState, agents: dict[str, Any]
) -> dict[str, Any]:
    """生成面试开场白和结构化面试计划，初始化面试状态。"""
    from app.interview.context import (
        extract_resume_topics,
        format_profile_supplement,
        format_resume_for_prompt,
    )
    from app.interview.plan import build_interview_plan

    jd = state.get("jd_analysis", {})
    profile = state.get("profile", {})
    resume = state.get("resume") or {}
    target = state.get("target_position", jd.get("job_title", "该岗位"))

    # 兼容旧状态：无结构化计划时仍保留 JD/简历话题列表。
    pending_topics = _extract_topics(jd)
    for t in extract_resume_topics(resume):
        if t not in pending_topics:
            pending_topics.append(t)
    pending_topics = pending_topics[:15]

    dimension_scores = {
        "专业知识": 0.0,
        "问题分析": 0.0,
        "沟通表达": 0.0,
        "实践经验": 0.0,
        "学习能力": 0.0,
    }

    opening = build_opening(jd, target)
    plan_items: list[dict[str, Any]] = []
    interviewer = agents.get("interviewer")
    if interviewer and getattr(interviewer, "llm", None):
        try:
            plan_items = await build_interview_plan(
                interviewer.llm,
                state,
                model=getattr(interviewer, "model", None),
            )
        except Exception as e:
            logger.warning(f"[open_interview] 结构化面试计划生成失败，回退单题生成: {e}")

    if plan_items:
        first_item = plan_items[0]
        first_question = first_item["question"]
        first_category = first_item["category"]
        asked_question_ids = [first_item["question_id"]]
        pending_topic_ids = [
            item["topic_id"] for item in plan_items[1:]
        ]
        current_plan_item = dict(first_item)
    else:
        if interviewer:
            result = await interviewer.run(
                target_position=target,
                difficulty_level=state.get("difficulty_level", "medium"),
                decision={"next_action": "切换话题", "reason": "面试开始"},
                pending_topics=pending_topics,
                covered_topics=[],
                referenced_questions=state.get("referenced_questions", []),
                resume_text=format_resume_for_prompt(resume),
                profile_supplement=format_profile_supplement(profile),
                jd_summary=str(jd.get("summary") or jd.get("job_title") or ""),
            )
            first_question = result.get("question", "请介绍一下你自己。")
            first_category = result.get("category", "behavioral")
        else:
            first_question = "请介绍一下你自己。"
            first_category = "behavioral"
        asked_question_ids = []
        pending_topic_ids = []
        current_plan_item = {}

    return {
        "phase": "opening",
        "opening_text": opening,
        "current_question": first_question,
        "current_question_id": (
            current_plan_item.get("question_id", "") if current_plan_item else ""
        ),
        "current_question_category": first_category,
        "current_plan_item": current_plan_item,
        "interview_plan": plan_items,
        "asked_question_ids": asked_question_ids,
        "pending_topic_ids": pending_topic_ids,
        "covered_topic_ids": [],
        "pending_topics": pending_topics,
        "dimension_scores": dimension_scores,
        "is_active": True,
        "turn_count": 0,
        "conversation_history": [
            {"role": "assistant", "content": opening, "timestamp": _now()},
            {"role": "assistant", "content": first_question, "timestamp": _now()},
        ],
    }


async def evaluate_node(
    state: InterviewState, agents: dict[str, Any]
) -> dict[str, Any]:
    """Evaluator 评价用户回答并输出下一步策略，不生成问题文本。"""
    evaluator = agents.get("evaluator")
    if not evaluator:
        logger.error("[evaluate] evaluator agent not found")
        return {"current_evaluation": {"score": 0, "next_action": "结束面试"}}

    current_plan_item = state.get("current_plan_item") or {}
    result = await evaluator.run(
        current_question=state.get("current_question", ""),
        current_answer=state.get("current_answer", ""),
        difficulty_level=state.get("difficulty_level", "medium"),
        turn_count=state.get("turn_count", 0),
        max_turns=state.get("max_turns", 10),
        covered_topics=state.get("covered_topics", []),
        pending_topics=state.get("pending_topics", []),
        covered_topic_ids=state.get("covered_topic_ids", []),
        pending_topic_ids=state.get("pending_topic_ids", []),
        current_plan_item=current_plan_item,
        answer_points=current_plan_item.get("answer_points", []),
        dimension_scores=state.get("dimension_scores", {}),
        conversation_history=state.get("conversation_history", []),
        referenced_questions=state.get("referenced_questions", []),
        resume_text=_resume_brief(state),
        target_position=state.get("target_position", ""),
    )

    # 更新维度评分（加权平均）
    old_scores = state.get("dimension_scores", {})
    new_dim_scores = result.get("dimension_scores", {})
    turn = state.get("turn_count", 0)
    updated_scores = {}
    all_dims = set(old_scores) | set(new_dim_scores)
    for dim in all_dims:
        old = old_scores.get(dim, 0)
        new = new_dim_scores.get(dim, 0)
        if turn > 0:
            updated_scores[dim] = round(old * 0.7 + new * 0.3, 1)
        else:
            updated_scores[dim] = new

    strengths = state.get("strengths", []) + list(result.get("strengths", []) or [])
    weaknesses = state.get("weaknesses", []) + list(result.get("weaknesses", []) or [])

    # 兼容旧字段：保留问题文本历史。
    covered = list(state.get("covered_topics", []))
    current_q = state.get("current_question", "")
    if current_q and current_q not in covered:
        covered.append(current_q)

    # 新的稳定主题状态：只有明确切换话题或回答充分时才标记覆盖。
    covered_topic_ids = list(state.get("covered_topic_ids", []))
    pending_topic_ids = list(state.get("pending_topic_ids", []))
    current_topic_id = current_plan_item.get("topic_id")
    action = result.get("next_action", "切换话题")
    score = _number(result.get("score"), default=5.0)
    if current_topic_id and action == "切换话题" and current_topic_id not in covered_topic_ids:
        covered_topic_ids.append(current_topic_id)
    if current_topic_id and action != "追问" and score >= 8.0 and current_topic_id not in covered_topic_ids:
        covered_topic_ids.append(current_topic_id)
    next_topic_id = result.get("next_topic_id")
    if next_topic_id and next_topic_id in pending_topic_ids:
        pending_topic_ids.remove(next_topic_id)

    pending = list(state.get("pending_topics", []))
    next_topic = result.get("next_topic")
    if next_topic and next_topic in pending:
        pending.remove(next_topic)

    return {
        "current_evaluation": result,
        "evaluation_evidence": (
            list(state.get("evaluation_evidence") or [])
            + [{
                "topic_id": current_plan_item.get("topic_id"),
                "question_id": state.get("current_question_id"),
                "question": state.get("current_question", ""),
                "evidence": list(result.get("evidence", []) or []),
                "missing_points": list(result.get("missing_points", []) or []),
                "answer_relevance": result.get("answer_relevance"),
                "confidence": result.get("confidence"),
            }]
        )[-30:],
        "dimension_scores": updated_scores,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "next_action": result.get("next_action", "切换话题"),
        "covered_topics": covered,
        "pending_topics": pending,
        "covered_topic_ids": covered_topic_ids,
        "pending_topic_ids": pending_topic_ids,
        "turn_count": turn + 1,
        "conversation_history": _append_history(
            state.get("conversation_history", []),
            {"role": "user", "content": state.get("current_answer", ""), "timestamp": _now()},
        ),
        "interrupt_checkpoint": "evaluate",
    }


async def ask_question_node(
    state: InterviewState, agents: dict[str, Any]
) -> dict[str, Any]:
    """优先复用结构化计划，计划缺失时回退 Interviewer 单题生成。"""
    from app.interview.context import format_profile_supplement, format_resume_for_prompt

    evaluation = state.get("current_evaluation", {})
    plan_items = _plan_items(state)
    if plan_items:
        selected = _select_plan_question(state, evaluation)
        if selected:
            question = selected["question"]
            category = selected.get("category", "technical")
            updates = _question_updates(state, question, category, selected)
            new_difficulty = evaluation.get("new_difficulty")
            if new_difficulty and new_difficulty != state.get("difficulty_level"):
                updates["difficulty_level"] = new_difficulty
            return updates

    interviewer = agents.get("interviewer")
    if not interviewer:
        logger.error("[ask_question] interviewer agent not found")
        return {"current_question": "请继续。"}

    result = await interviewer.run(
        target_position=state.get("target_position", ""),
        difficulty_level=state.get("difficulty_level", "medium"),
        decision=evaluation,
        pending_topics=state.get("pending_topics", []),
        covered_topics=state.get("covered_topics", []),
        pending_topic_ids=state.get("pending_topic_ids", []),
        covered_topic_ids=state.get("covered_topic_ids", []),
        current_plan_item=state.get("current_plan_item") or {},
        answer_points=(state.get("current_plan_item") or {}).get("answer_points", []),
        referenced_questions=state.get("referenced_questions", []),
        current_question=state.get("current_question", ""),
        current_answer=state.get("current_answer", ""),
        resume_text=format_resume_for_prompt(state.get("resume")),
        profile_supplement=format_profile_supplement(state.get("profile")),
        jd_summary=str((state.get("jd_analysis") or {}).get("summary") or ""),
    )

    question = result.get("question", "请继续。")
    category = result.get("category", "technical")
    fallback_item = {
        "question_id": f"fallback-{int(state.get('turn_count', 0)) + 1}",
        "topic_id": (state.get("current_plan_item") or {}).get("topic_id", ""),
        "topic": (state.get("current_plan_item") or {}).get("topic", ""),
        "answer_points": (state.get("current_plan_item") or {}).get("answer_points", []),
    }
    updates = _question_updates(state, question, category, fallback_item)
    new_difficulty = evaluation.get("new_difficulty")
    if new_difficulty and new_difficulty != state.get("difficulty_level"):
        updates["difficulty_level"] = new_difficulty
    return updates


async def adjust_difficulty_node(
    state: InterviewState, agents: dict[str, Any]
) -> dict[str, Any]:
    """调整面试难度（纯状态更新，不调 LLM）。"""
    evaluation = state.get("current_evaluation", {})
    new_difficulty = evaluation.get("new_difficulty", state.get("difficulty_level", "medium"))
    return {
        "difficulty_level": new_difficulty,
    }


async def finish_node(
    state: InterviewState, agents: dict[str, Any]
) -> dict[str, Any]:
    """标记面试结束。"""
    turn = state.get("turn_count", 0)
    max_turns = state.get("max_turns", 10)
    pending = state.get("pending_topics", [])
    pending_topic_ids = state.get("pending_topic_ids", [])

    if turn >= max_turns:
        reason = "max_turns"
    elif not pending and not pending_topic_ids:
        reason = "all_topics_covered"
    else:
        reason = "evaluator_ended"

    return {
        "is_active": False,
        "is_complete": True,
        "completion_reason": reason,
    }


async def generate_report_node(
    state: InterviewState, agents: dict[str, Any]
) -> dict[str, Any]:
    """生成完整评价报告。"""
    evaluator = agents.get("evaluator")
    if not evaluator:
        return {"final_report": {"error": "evaluator not available"}}

    # 用 LLM 生成报告摘要（直接调用，不走 evaluator.build_messages 的评分 prompt）
    from app.llm import Message, Role
    from app.llm.retry import with_retry

    history_summary = _summarize_history(state.get("conversation_history", []))

    report_prompt = (
        f"请根据以下面试记录生成一份简洁的评价报告。\n\n"
        f"目标岗位：{state.get('target_position', '')}\n"
        f"面试轮数：{state.get('turn_count', 0)}\n"
        f"维度评分：{json.dumps(state.get('dimension_scores', {}), ensure_ascii=False)}\n"
        f"优势：{json.dumps(state.get('strengths', []), ensure_ascii=False)}\n"
        f"薄弱点：{json.dumps(state.get('weaknesses', []), ensure_ascii=False)}\n"
        f"结束原因：{state.get('completion_reason', '')}\n\n"
        f"对话摘要：\n{history_summary}\n\n"
        f"请输出 JSON（overall_score 为 0-10 的综合分）：\n"
        f'{{"overall_score": 7.5, "summary": "总体评价（2-3句话）", "suggestions": ["建议1", "建议2"]}}'
    )

    try:
        async def _call_llm():
            return await evaluator.llm.generate(report_prompt, temperature=0.3, max_tokens=1024)
        response = await with_retry(_call_llm)
        report = evaluator.extract_json(response) or {}
    except Exception as e:
        logger.error(f"[generate_report] LLM call failed: {e}")
        report = {}

    dimension_scores = state.get("dimension_scores", {})
    calculated_score = (
        sum(dimension_scores.values()) / len(dimension_scores)
        if dimension_scores
        else 0
    )
    # 统一为 0–10 分制（evaluator 维度即为 0–10）
    try:
        overall = float(report.get("overall_score", calculated_score))
    except (TypeError, ValueError):
        overall = float(calculated_score)
    if overall > 10:  # 若模型给了百分制，折算
        overall = overall / 10.0
    overall = max(0.0, min(10.0, round(overall, 1)))

    final_report = {
        "overall_score": overall,
        "score_scale": "0-10",
        "summary": report.get("summary", ""),
        "suggestions": report.get("suggestions", []),
        "dimension_scores": dimension_scores,
        "strengths": state.get("strengths", []),
        "weaknesses": state.get("weaknesses", []),
        "evaluation_evidence": state.get("evaluation_evidence", []),
        "turn_count": state.get("turn_count", 0),
        "completion_reason": state.get("completion_reason", ""),
        "target_position": state.get("target_position", ""),
    }

    return {
        "final_report": final_report,
        "phase": "closing",
    }


# --- 辅助函数 ---


def _number(value: Any, *, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _plan_items(state: InterviewState) -> list[dict[str, Any]]:
    return [
        item for item in (state.get("interview_plan") or [])
        if isinstance(item, dict) and item.get("question")
    ]


def _select_plan_question(
    state: InterviewState, evaluation: dict[str, Any]
) -> dict[str, Any] | None:
    """选择计划题或当前题的追问，保证 question_id 稳定且不重复。"""
    items = _plan_items(state)
    if not items:
        return None

    asked_ids = set(state.get("asked_question_ids") or [])
    current = state.get("current_plan_item") or {}
    action = str(evaluation.get("next_action") or "切换话题")

    if action == "追问":
        follow_up = _next_follow_up(current, asked_ids)
        if follow_up:
            return follow_up

    target_difficulty = evaluation.get("new_difficulty")
    if action in ("提高难度", "降低难度") and target_difficulty:
        for item in items:
            if (
                item.get("question_id") not in asked_ids
                and item.get("difficulty") == target_difficulty
            ):
                return dict(item)

    pending_ids = state.get("pending_topic_ids") or []
    pending_set = set(pending_ids)
    for item in items:
        if (
            item.get("topic_id") in pending_set
            and item.get("question_id") not in asked_ids
        ):
            return dict(item)

    for item in items:
        if item.get("question_id") not in asked_ids:
            return dict(item)

    follow_up = _next_follow_up(current, asked_ids)
    if follow_up:
        return follow_up
    return None


def _next_follow_up(
    current: dict[str, Any], asked_ids: set[str]
) -> dict[str, Any] | None:
    topic_id = str(current.get("topic_id") or "current")
    for index, text in enumerate(current.get("follow_ups") or [], start=1):
        question_id = f"{topic_id}-follow-{index}"
        if question_id in asked_ids:
            continue
        return {
            **current,
            "question_id": question_id,
            "question": str(text).strip(),
            "category": current.get("category", "technical"),
            "answer_points": current.get("answer_points", []),
            "is_follow_up": True,
        }
    return None


def _question_updates(
    state: InterviewState,
    question: str,
    category: str,
    selected: dict[str, Any],
) -> dict[str, Any]:
    question_id = str(selected.get("question_id") or f"fallback-{int(state.get('turn_count', 0)) + 1}")
    asked_ids = list(state.get("asked_question_ids") or [])
    if question_id not in asked_ids:
        asked_ids.append(question_id)

    pending_topic_ids = list(state.get("pending_topic_ids") or [])
    topic_id = selected.get("topic_id")
    if topic_id and topic_id in pending_topic_ids and not selected.get("is_follow_up"):
        pending_topic_ids.remove(topic_id)

    return {
        "current_question": question,
        "current_question_id": question_id,
        "current_question_category": category,
        "current_plan_item": {
            **(state.get("current_plan_item") or {}),
            **selected,
        },
        "asked_question_ids": asked_ids[-40:],
        "pending_topic_ids": pending_topic_ids,
        "phase": "core_probing",
        "conversation_history": _append_history(
            state.get("conversation_history", []),
            {"role": "assistant", "content": question, "timestamp": _now()},
        ),
        "interrupt_checkpoint": "ask_question",
    }


def _resume_brief(state: InterviewState) -> str:
    from app.interview.context import format_resume_for_prompt

    return format_resume_for_prompt(state.get("resume"))


def _append_history(history: list[dict] | None, entry: dict) -> list[dict]:
    """追加一条对话历史，避免整段替换导致上下文丢失。"""
    base = list(history or [])
    base.append(entry)
    # 防止异常场景下历史无限膨胀
    return base[-80:]


def _extract_topics(jd: dict) -> list[str]:
    """从 JD 分析结果提取待考察话题。"""
    topics = []
    requirements = jd.get("requirements", [])
    for req in requirements:
        if isinstance(req, dict):
            content = req.get("content", "")
        else:
            content = str(req)
        if content:
            topics.append(content)
    # 限制数量，避免话题过多
    return topics[:15]


def _summarize_history(history: list[dict]) -> str:
    """将对话历史压缩为摘要。"""
    lines = []
    for h in history[-20:]:  # 最多取最近 20 条
        role = h.get("role", "")
        content = h.get("content", "")
        if content:
            prefix = "面试官" if role == "assistant" else "候选人"
            lines.append(f"{prefix}：{content[:100]}")
    return "\n".join(lines)


def _now() -> str:
    return datetime.now().isoformat()
