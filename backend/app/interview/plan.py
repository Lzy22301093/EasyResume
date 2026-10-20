"""结构化面试计划：面试开始时一次性生成可复用的题目、考察目标和追问。"""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.interview.context import (
    format_profile_supplement,
    format_resume_for_prompt,
)
from app.llm.structured import ainvoke_json_with_schema


class InterviewPlanItem(BaseModel):
    """单道面试题及其评价依据。"""

    topic: str = Field(min_length=1, max_length=120)
    category: Literal["technical", "project_deep_dive", "behavioral", "situational"]
    difficulty: Literal["easy", "medium", "hard"]
    question: str = Field(min_length=1, max_length=500)
    answer_points: list[str] = Field(default_factory=list, max_length=8)
    evidence_refs: list[str] = Field(default_factory=list, max_length=8)
    follow_ups: list[str] = Field(default_factory=list, max_length=4)


class InterviewPlanOutput(BaseModel):
    """LLM 输出的面试计划。"""

    items: list[InterviewPlanItem] = Field(min_length=1, max_length=12)


PLAN_SYSTEM_PROMPT = """你是一位资深技术面试官，为一场模拟面试制定紧凑、连贯的面试计划。

## 输入材料优先级
1. 岗位 JD：决定考察重点、难度和题目比例。
2. 候选人简历：优先围绕真实项目、实习、工作经历追问。
3. 个人画像：只补充简历未覆盖的信息，不得覆盖或改写简历事实。
4. 已参考题目：避免重复出题。

## 计划要求
- 题目数量控制在 4-10 道，按 JD 重要性排序。
- 每道题只问一个问题，题目要自然、具体，像真实面试。
- technical / project_deep_dive / behavioral 的比例根据 JD 调整；没有明确技术要求时不要堆砌算法题。
- project_deep_dive 必须引用简历中可识别的项目、实习或工作经历，不得编造细节。
- 每道题给出 2-5 个 answer_points，供后续评价使用；不要写完整参考答案。
- evidence_refs 写材料中的来源提示，例如“简历：xxx 项目”或“JD：并发设计”，没有来源就返回空数组。
- follow_ups 是当前题的可选追问，必须承接题目和候选人可能的回答，不要另起话题。
- 题目难度从 easy/medium/hard 中选择，整体逐步推进，不要一开始全部 hard。

严格输出 JSON 对象，不要 Markdown 代码块或解释文字：
{
  "items": [
    {
      "topic": "稳定的考察主题",
      "category": "technical|project_deep_dive|behavioral|situational",
      "difficulty": "easy|medium|hard",
      "question": "一个面试问题",
      "answer_points": ["要点1", "要点2"],
      "evidence_refs": ["简历：xxx 项目"],
      "follow_ups": ["追问1", "追问2"]
    }
  ]
}"""


def _clean_items(raw: InterviewPlanOutput) -> list[dict[str, Any]]:
    """补齐稳定的计划 ID，避免用题目文本作为状态标识。"""
    items: list[dict[str, Any]] = []
    seen_topics: set[str] = set()
    for index, item in enumerate(raw.items, start=1):
        topic = re.sub(r"\s+", " ", item.topic).strip()
        question = re.sub(r"\s+", " ", item.question).strip()
        if not topic or not question:
            continue
        topic_key = topic.casefold()
        if topic_key in seen_topics:
            topic = f"{topic}（补充）"
        seen_topics.add(topic_key)
        items.append(
            {
                "topic_id": f"topic-{index}",
                "question_id": f"q-{index}",
                "topic": topic,
                "category": item.category,
                "difficulty": item.difficulty,
                "question": question,
                "answer_points": [
                    re.sub(r"\s+", " ", point).strip()
                    for point in item.answer_points
                    if point and point.strip()
                ],
                "evidence_refs": [
                    re.sub(r"\s+", " ", ref).strip()
                    for ref in item.evidence_refs
                    if ref and ref.strip()
                ],
                "follow_ups": [
                    re.sub(r"\s+", " ", follow_up).strip()
                    for follow_up in item.follow_ups
                    if follow_up and follow_up.strip()
                ],
            }
        )
    return items


async def build_interview_plan(
    llm: Any,
    state: dict[str, Any],
    *,
    model: str | None = None,
) -> list[dict[str, Any]]:
    """生成结构化面试计划，失败时抛出异常由调用方降级。"""
    jd = state.get("jd_analysis") or {}
    resume = state.get("resume") or {}
    profile = state.get("profile") or {}
    target = state.get("target_position") or jd.get("job_title") or "目标岗位"
    max_turns = int(state.get("max_turns") or 10)
    count = max(4, min(10, max_turns))

    jd_summary = str(jd.get("summary") or "").strip()
    requirements = jd.get("requirements") or []
    requirement_lines: list[str] = []
    for requirement in requirements[:12]:
        if isinstance(requirement, dict):
            content = str(requirement.get("content") or requirement.get("text") or "").strip()
            importance = str(requirement.get("importance") or "").strip()
        else:
            content = str(requirement).strip()
            importance = ""
        if content:
            requirement_lines.append(f"- {content}{f'（重要性：{importance}）' if importance else ''}")

    referenced = state.get("referenced_questions") or []
    referenced_items = state.get("referenced_question_items") or []
    reference_lines: list[str] = []
    for item in referenced_items[:10]:
        if not isinstance(item, dict):
            continue
        question = str(item.get("question") or "").strip()
        if not question:
            continue
        points = "、".join(
            str(point).strip()
            for point in (item.get("answer_points") or [])
            if str(point).strip()
        )
        difficulty = str(item.get("difficulty") or "").strip()
        suffix = f"；要点：{points}" if points else ""
        suffix += f"；难度：{difficulty}" if difficulty else ""
        reference_lines.append(f"- {question[:180]}{suffix}")
    for item in referenced[:10]:
        text = str(item).strip()
        if text:
            reference_lines.append(f"- {text[:180]}")

    user_content = (
        f"## 目标岗位\n{target}\n\n"
        f"## JD 摘要\n{jd_summary or '未提供'}\n\n"
        f"## JD 要求\n{chr(10).join(requirement_lines) or '未提供'}\n\n"
        f"## 候选人简历（主材料）\n{format_resume_for_prompt(resume) or '未提供'}\n\n"
        f"## 个人画像补充（次要）\n{format_profile_supplement(profile) or '未提供'}\n\n"
        f"## 已参考题目（避免重复，可参考其 answer_points）\n"
        f"{chr(10).join(reference_lines) or '无'}\n\n"
        f"请生成 {count} 道面试题的计划。"
    )

    result = await ainvoke_json_with_schema(
        llm,
        PLAN_SYSTEM_PROMPT,
        user_content,
        InterviewPlanOutput,
        model=model,
        temperature=0.35,
        max_attempts=2,
    )
    items = _clean_items(result)
    if not items:
        raise ValueError("面试计划为空")
    return items
