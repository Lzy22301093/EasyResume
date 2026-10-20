"""InterviewState — 模拟面试状态定义。"""

from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict


class InterviewState(TypedDict, total=False):
    """模拟面试状态。total=False 表示所有字段都是可选的。"""

    # ── 会话标识 ──
    session_id: str                    # 面试会话 ID
    interview_id: str                  # 本次面试唯一 ID

    # ── 面试配置（初始化时注入，只读）──
    jd_analysis: dict[str, Any]        # JD 分析结果（主）
    profile: dict[str, Any]            # 候选人画像（补充）
    resume: dict[str, Any]             # 本场选用简历（主）{document_id,version_id,title,sections,raw_text}
    use_profile_as_supplement: bool    # 是否用画像补充
    target_position: str               # 目标岗位
    referenced_questions: list[str]    # 用户已参考的面试题（避免重复出题）
    referenced_question_items: list[dict[str, Any]]  # 参考题目 + answer_points

    # ── 面试计划（开始时生成，题目与评价依据复用）──
    interview_plan: list[dict[str, Any]]  # [{topic_id,question_id,topic,question,...}]
    current_plan_item: dict[str, Any]     # 当前正在考察的计划项
    asked_question_ids: list[str]         # 已经问过的稳定题目 ID
    pending_topic_ids: list[str]          # 待考察主题 ID
    covered_topic_ids: list[str]          # 已充分考察主题 ID

    # ── 动态配置（Evaluator 修改）──
    difficulty_level: str              # easy / medium / hard
    interview_mode: str                # technical / behavioral / mixed

    # ── 面试进程 ──
    phase: str                         # opening / core_probing / closing
    opening_text: str                  # 开场白，可与第一题并行播报
    current_question: str              # 当前面试官问题（Interviewer/计划写入）
    current_question_category: str     # 当前问题类别
    current_question_id: str            # 当前问题稳定 ID（含追问 ID）
    current_answer: str                # 用户当前回答（Voice Layer 写入）
    turn_count: int                    # 已完成问答轮数
    max_turns: int                     # 最大轮数（默认 10）

    # ── 历史记录 ──
    conversation_history: list[dict[str, Any]]  # [{role, content, timestamp}]

    # ── 评价数据（Evaluator 写入）──
    dimension_scores: dict[str, float] # 维度评分 {"专业知识": 7.5, ...}
    current_evaluation: dict[str, Any] # 当前轮评价
    evaluation_evidence: list[dict[str, Any]]  # 每轮证据与缺失要点，供最终报告复用
    strengths: list[str]               # 累积优势
    weaknesses: list[str]              # 累积薄弱点

    # ── 策略（Evaluator 写入，Graph 读取做路由）──
    next_action: str                   # 追问 / 切换话题 / 提高难度 / 降低难度 / 结束面试
    covered_topics: list[str]          # 兼容旧状态的问题文本
    pending_topics: list[str]          # 兼容旧状态的话题文本

    # ── 状态标记 ──
    is_active: bool
    is_complete: bool
    completion_reason: str             # max_turns / all_topics_covered / user_ended

    # ── 最终报告 ──
    final_report: dict[str, Any]

    # ── 打断恢复 ──
    interrupt_checkpoint: str          # 已完成的步骤标记

    # ── 可观测 ──
    workflow_trace: Annotated[list[dict[str, Any]], operator.add]
