"""InterviewerAgent — 根据 Evaluator 决策生成面试问题。"""

from __future__ import annotations

import json

from app.agents.base import BaseAgent
from app.llm import Message, Role

SYSTEM_PROMPT = """你是一位专业的技术面试官，正在进行模拟面试。

你的任务是根据面试策略生成下一个面试问题。

## 上下文优先级（重要）
1. **岗位 JD**：决定考察重点与难度
2. **候选人简历**：项目/经历细节以简历为准，优先围绕简历追问
3. **当前题目计划项**：优先围绕计划主题、answer_points 和 evidence_refs 提问
4. **个人画像**：仅作补充（简历未覆盖的技能等），不要与简历冲突时用画像覆盖简历

## 提问规则
- 语气自然、专业，像真实面试对话
- 一次只问一个问题，不要连续抛出多个问题
- 追问必须引用候选人的回答、简历内容或当前计划项
- 不要重复 referenced_questions 中已经出现过的题目
- 技术问题要有明确考察目标；行为问题要有具体场景
- 不得编造简历中不存在的项目、数据或职责
- 题目尽量控制在 15-60 个汉字，除非必须说明必要背景

## 输出格式
严格输出以下 JSON，不要添加任何额外文字：
{
    "question": "面试问题文本",
    "category": "technical|project_deep_dive|behavioral|situational"
}"""


class InterviewerAgent(BaseAgent):
    """根据 Evaluator 决策生成面试问题。"""

    name = "interviewer"
    description = "生成面试提问"

    temperature: float = 0.4
    max_tokens: int = 2048
    max_parse_attempts: int = 2
    json_mode = True

    def build_messages(self, **kwargs) -> list[Message]:
        target_position = kwargs.get("target_position", "")
        difficulty = kwargs.get("difficulty_level", "medium")
        decision = kwargs.get("decision", {})
        pending_topics = kwargs.get("pending_topics", [])
        covered_topics = kwargs.get("covered_topics", [])
        pending_topic_ids = kwargs.get("pending_topic_ids", [])
        covered_topic_ids = kwargs.get("covered_topic_ids", [])
        current_plan_item = kwargs.get("current_plan_item", {}) or {}
        answer_points = kwargs.get("answer_points") or current_plan_item.get("answer_points", []) or []
        referenced_questions = kwargs.get("referenced_questions", [])
        current_question = kwargs.get("current_question", "")
        current_answer = kwargs.get("current_answer", "")
        resume_text = (kwargs.get("resume_text") or "").strip()
        profile_supplement = (kwargs.get("profile_supplement") or "").strip()
        jd_summary = (kwargs.get("jd_summary") or "").strip()

        user_content = (
            f"## 面试信息\n"
            f"- 目标岗位：{target_position}\n"
            f"- 当前难度：{difficulty}\n"
            f"- 已覆盖主题 ID：{json.dumps(covered_topic_ids, ensure_ascii=False)}\n"
            f"- 待考察主题 ID：{json.dumps(pending_topic_ids, ensure_ascii=False)}\n"
            f"- 已覆盖话题（兼容）：{', '.join(covered_topics) if covered_topics else '无'}\n"
            f"- 待考察话题（兼容）：{', '.join(pending_topics) if pending_topics else '无'}\n"
        )
        if current_plan_item:
            user_content += (
                f"\n## 当前题目计划项\n"
                f"- topic_id：{current_plan_item.get('topic_id', '')}\n"
                f"- 主题：{current_plan_item.get('topic', '')}\n"
                f"- 类别：{current_plan_item.get('category', '')}\n"
                f"- answer_points：{json.dumps(answer_points, ensure_ascii=False)}\n"
                f"- evidence_refs：{json.dumps(current_plan_item.get('evidence_refs', []), ensure_ascii=False)}\n"
            )
        if jd_summary:
            user_content += f"- JD 摘要：{jd_summary[:300]}\n"
        if resume_text:
            user_content += f"\n## 候选人简历（主材料，优先据此提问）\n{resume_text}\n"
        if profile_supplement:
            user_content += f"\n## 个人画像补充（次要）\n{profile_supplement}\n"

        if referenced_questions:
            user_content += f"- 候选人已参考过的题目（优先跳过）：{json.dumps(referenced_questions[:10], ensure_ascii=False)}\n"

        action = decision.get("next_action", "切换话题")
        user_content += f"\n## 面试官决策\n- 动作：{action}\n- 理由：{decision.get('reason', '')}\n"

        if decision.get("follow_up_focus"):
            user_content += f"- 追问方向：{decision['follow_up_focus']}\n"
        if action in ("提高难度", "降低难度"):
            user_content += f"- 新难度：{decision.get('new_difficulty', difficulty)}\n"

        if action == "追问" and current_question and current_answer:
            user_content += (
                f"\n## 上一轮对话\n"
                f"- 问题：{current_question}\n"
                f"- 回答：{current_answer}\n"
            )

        user_content += "\n请生成下一个面试问题。"

        return [
            Message(role=Role.SYSTEM, content=SYSTEM_PROMPT),
            Message(role=Role.USER, content=user_content),
        ]

    def parse_response(self, content: str) -> dict:
        result = self.extract_json(content)
        if result and "question" in result:
            valid_categories = {
                "technical",
                "project_deep_dive",
                "behavioral",
                "situational",
            }
            if result.get("category") not in valid_categories:
                result["category"] = "technical"
            return result
        return {
            "question": "请介绍一下你最近做的一个项目。",
            "category": "project_deep_dive",
            "_raw": content,
            "_parse_error": True,
        }
