"""EvaluatorAgent — 评价候选人回答并决定面试下一步动作。"""

from __future__ import annotations

import json

from app.agents.base import BaseAgent
from app.llm import Message, Role

SYSTEM_PROMPT = """你是一位资深技术面试官，正在对模拟面试中的候选人回答做客观评价。

你的任务是：
1. 评价候选人的回答质量（0-10 分）
2. 判断下一步面试策略
3. 只输出决策和评价依据，不要生成下一道问题文本

## 材料优先级
1. 岗位 JD：决定能力要求和评价标准
2. 候选人简历：核对项目/经历真实性，简历事实优先
3. 当前题目计划项：提供本题考察主题和 answer_points
4. 个人画像：仅作补充，不得覆盖简历事实

## 评分要求
- 按当前题目计划的 answer_points 判断回答是否覆盖关键点。
- 评分要有证据：回答里说了什么、漏了什么，不要凭印象给精确分。
- 概念正确但没有案例时，专业知识可以得分，实践经验应扣分。
- 如果回答与简历明确冲突，记录到 weaknesses，不要自行编造解释。
- 如果题目没有提供 answer_points，再使用通用维度：专业知识、问题分析、沟通表达、实践经验、学习能力。

## 决策规则
- **追问**：回答正确但浅显、证据不足，或有明显错误需要澄清
- **切换话题**：当前主题已经充分考察，或回答与当前主题无关
- **提高难度**：回答准确、完整、有案例，当前难度偏简单
- **降低难度**：回答吃力、错误较多或没有展开
- **结束面试**：已达到最大轮数或核心主题均已充分考察

## 输出格式
严格输出以下 JSON，不要添加任何额外文字：
{
    "topic_id": "当前计划项的 topic_id，没有则为 null",
    "score": 7.5,
    "dimension_scores": {
        "专业知识": 8.0,
        "问题分析": 7.0,
        "沟通表达": 7.5,
        "实践经验": 6.0,
        "学习能力": 7.0
    },
    "answer_relevance": 0.8,
    "confidence": 0.75,
    "evidence": ["回答中可验证的依据1", "回答中可验证的依据2"],
    "missing_points": ["未覆盖的关键点1"],
    "strengths": ["优点1", "优点2"],
    "weaknesses": ["不足1"],
    "feedback": "简短的评价反馈（一句话）",
    "next_action": "追问",
    "reason": "决策理由",
    "follow_up_focus": "如果决定追问，这里写追问方向；否则为 null",
    "next_topic_id": "如果决定切换话题，这里写下一个计划主题 ID；否则为 null",
    "new_difficulty": "如果决定调整难度，写新的难度；否则为 null"
}"""


class EvaluatorAgent(BaseAgent):
    """评价面试回答并决策。"""

    name = "evaluator"
    description = "评价面试回答并决策"

    temperature: float = 0.3
    # max_tokens 需足够大：MIMO 模型可能有内部思考链消耗 token，过小会导致输出为空
    max_tokens: int = 8192
    max_parse_attempts: int = 2
    json_mode = True

    def build_messages(self, **kwargs) -> list[Message]:
        question = kwargs.get("current_question", "")
        answer = kwargs.get("current_answer", "")
        difficulty = kwargs.get("difficulty_level", "medium")
        turn_count = kwargs.get("turn_count", 0)
        max_turns = kwargs.get("max_turns", 10)
        covered_topics = kwargs.get("covered_topics", [])
        pending_topics = kwargs.get("pending_topics", [])
        covered_topic_ids = kwargs.get("covered_topic_ids", [])
        pending_topic_ids = kwargs.get("pending_topic_ids", [])
        current_plan_item = kwargs.get("current_plan_item", {}) or {}
        answer_points = kwargs.get("answer_points") or current_plan_item.get("answer_points", []) or []
        dimension_scores = kwargs.get("dimension_scores", {})
        conversation_history = kwargs.get("conversation_history", [])
        referenced_questions = kwargs.get("referenced_questions", [])
        resume_text = (kwargs.get("resume_text") or "").strip()
        target_position = kwargs.get("target_position", "")

        user_content = (
            f"## 当前面试状态\n"
            f"- 目标岗位：{target_position or '未提供'}\n"
            f"- 已完成轮数：{turn_count}/{max_turns}\n"
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
                f"- 难度：{current_plan_item.get('difficulty', '')}\n"
                f"- answer_points：{json.dumps(answer_points, ensure_ascii=False)}\n"
                f"- evidence_refs：{json.dumps(current_plan_item.get('evidence_refs', []), ensure_ascii=False)}\n"
            )
        if resume_text:
            user_content += f"\n## 候选人简历（用于核对经历真实性）\n{resume_text[:2000]}\n"

        if dimension_scores:
            user_content += f"- 历史维度评分：{json.dumps(dimension_scores, ensure_ascii=False)}\n"

        if referenced_questions:
            user_content += f"- 候选人已参考过的题目（避免重复出题）：{json.dumps(referenced_questions[:10], ensure_ascii=False)}\n"

        user_content += (
            f"\n## 当前问题\n{question}\n\n"
            f"## 候选人回答\n{answer}\n\n"
            f"请评价回答并决定下一步动作。不要生成下一题。"
        )

        return [
            Message(role=Role.SYSTEM, content=SYSTEM_PROMPT),
            Message(role=Role.USER, content=user_content),
        ]

    def parse_response(self, content: str) -> dict:
        result = self.extract_json(content)
        if result and "next_action" in result and "score" in result:
            valid_actions = {"追问", "切换话题", "提高难度", "降低难度", "结束面试"}
            if result["next_action"] not in valid_actions:
                result["next_action"] = "切换话题"
            result.setdefault("evidence", [])
            result.setdefault("missing_points", [])
            result.setdefault("answer_relevance", None)
            result.setdefault("confidence", None)
            return result
        return {
            "score": 5.0,
            "dimension_scores": {},
            "answer_relevance": None,
            "confidence": None,
            "evidence": [],
            "missing_points": [],
            "strengths": [],
            "weaknesses": [],
            "feedback": "",
            "next_action": "切换话题",
            "reason": "解析失败，默认切换话题",
            "follow_up_focus": None,
            "next_topic_id": None,
            "new_difficulty": None,
            "_raw": content,
            "_parse_error": True,
        }
