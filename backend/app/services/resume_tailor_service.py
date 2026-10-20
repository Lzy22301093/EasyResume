"""ResumeTailorService — 针对目标岗位调整已有简历，生成岗位定制稿。

复用简历生成的内容结构、表达规则与事实约束，但不复用八步录入流程。
输出只做表达、排序、重点和篇幅调整，不新增经历、公司、奖项或数字。
"""

from __future__ import annotations

import json
import logging
import re
from collections import Counter
from typing import Any

from app.models.schemas import TailoredResumeRequest, TailoredResumeResult, TailoredSectionChange
from app.tools.context import compact_gap, compact_jd

logger = logging.getLogger(__name__)

MODE_LABELS = {
    "conservative": "保守润色：只优化表达，不改变模块与重点",
    "focused": "岗位重点优化：调整模块顺序、表达重点与篇幅，突出与 JD 相关的已有事实",
    "one_page": "一页精简：压缩篇幅并隐藏非必要模块，保留联系方式、教育与核心经历",
}

TAILOR_SYSTEM_PROMPT = """你是专业中文简历编辑。请根据目标岗位分析和匹配诊断，把用户已有简历调整为岗位定制稿。

硬性约束：
1. 只能使用原始简历中已经存在的事实；禁止新增公司、学校、项目、职责、奖项、技能熟练度、数字、百分比、金额、时间或成果。
2. 可以改写表达、调整模块顺序、突出相关经历、压缩重复内容、隐藏低相关内容；不得改变事实。
3. 保留原有模块标题。除一页精简模式可隐藏非必要模块外，不要增删模块。
4. 不使用 Markdown 语法，不输出 #、**、- 列表符号；保持纯文本和原有换行风格。
5. raw_text 必须由 sections 完整拼接生成。
6. changes 必须逐模块说明 kept/rewritten/compressed/hidden 和原因。
7. 只返回 JSON。

输出格式：
{
  "content": {
    "sections": [{"title": "模块标题", "content": "模块正文"}],
    "raw_text": "完整纯文本"
  },
  "changes": [
    {"title": "模块标题", "action": "kept|rewritten|compressed|hidden", "reason": "变化原因"}
  ],
  "fact_guard": "事实边界说明"
}
"""

_NUMBER_RE = re.compile(r"\d+(?:\.\d+)?")
_PROTECTED_TITLE_KEYWORDS = ("基本", "联系", "教育", "学历")


class TailorError(ValueError):
    """岗位定制业务错误。"""


class TailorGenerationError(TailorError):
    """LLM 输出未能生成可用岗位定制稿。"""


def _text_numbers(content: dict[str, Any]) -> Counter[str]:
    parts: list[str] = []
    for section in content.get("sections") or []:
        parts.append(str(section.get("title") or ""))
        parts.append(str(section.get("content") or ""))
    return Counter(_NUMBER_RE.findall("\n".join(parts)))


def _assert_no_new_numbers(source: dict[str, Any], output: dict[str, Any]) -> None:
    source_numbers = _text_numbers(source)
    output_numbers = _text_numbers(output)
    invented = sorted(
        number for number, count in output_numbers.items() if count > source_numbers.get(number, 0)
    )
    if invented:
        raise TailorError(
            "生成稿出现了原始简历中不存在的数字，已阻止保存："
            + "、".join(invented[:8])
        )


def _is_protected_title(title: str) -> bool:
    normalized = title.strip().lower()
    return any(keyword in normalized for keyword in _PROTECTED_TITLE_KEYWORDS)


def _validate_structure(
    request: TailoredResumeRequest,
    result: TailoredResumeResult,
) -> TailoredResumeResult:
    source_sections = request.source_resume.sections
    output_sections = result.content.sections
    if not source_sections:
        raise TailorError("原始简历没有可调整的模块")
    if not output_sections:
        raise TailorError("岗位定制稿没有生成有效模块")

    source_titles = [section.title.strip() for section in source_sections]
    output_titles = [section.title.strip() for section in output_sections]
    unknown_titles = [title for title in output_titles if title not in source_titles]
    if unknown_titles:
        raise TailorError("岗位定制稿新增了原始简历中不存在的模块：" + "、".join(unknown_titles[:5]))

    missing_protected = [
        title for title in source_titles if _is_protected_title(title) and title not in output_titles
    ]
    if missing_protected:
        raise TailorError("岗位定制稿缺失必要模块：" + "、".join(missing_protected[:5]))

    source_by_title = {section.title.strip(): section for section in source_sections}
    changes_by_title = {change.title.strip(): change for change in result.changes}
    changes: list[TailoredSectionChange] = []
    for title in source_titles:
        source_section = source_by_title[title]
        output_section = next((s for s in output_sections if s.title.strip() == title), None)
        change = changes_by_title.get(title)
        if output_section is None:
            action = "hidden"
            reason = change.reason.strip() if change else "一页精简时隐藏低相关内容"
        elif change:
            action = change.action
            reason = change.reason.strip()
        elif output_section.content.strip() == source_section.content.strip():
            action = "kept"
            reason = "内容保持原文"
        else:
            action = "rewritten"
            reason = "根据目标岗位优化表达与重点"
        changes.append(TailoredSectionChange(title=title, action=action, reason=reason))

    raw_text = "\n\n".join(
        f"{section.title}\n{section.content}".strip() for section in output_sections
    )
    normalized_content = result.content.model_copy(update={"raw_text": raw_text})
    _assert_no_new_numbers(request.source_resume.model_dump(), normalized_content.model_dump())
    return result.model_copy(update={"content": normalized_content, "changes": changes})


class ResumeTailorService:
    """已有简历 + 岗位分析 → 岗位定制稿。"""

    async def tailor_resume(
        self,
        request: TailoredResumeRequest,
        llm: Any,
    ) -> TailoredResumeResult:
        """生成岗位定制稿，并执行结构与事实边界校验。"""
        if not request.source_resume.sections:
            raise TailorError("请先选择一份包含模块内容的已有简历")
        if not request.jd_analysis.job_title and not request.jd_analysis.summary:
            raise TailorError("目标岗位分析不足，请先完成 JD 分析")

        from app.llm.structured import ainvoke_json_with_schema

        gap = request.gap_analysis.model_dump() if request.gap_analysis else None
        user_content = (
            f"【定制方式】\n{MODE_LABELS[request.mode]}\n\n"
            f"【原始简历】\n{json.dumps(request.source_resume.model_dump(), ensure_ascii=False, indent=2)}\n\n"
            f"【目标岗位分析】\n{json.dumps(compact_jd(request.jd_analysis.model_dump()), ensure_ascii=False, indent=2)}\n\n"
            f"【匹配诊断】\n{json.dumps(compact_gap(gap or {}), ensure_ascii=False, indent=2)}\n\n"
            "请生成岗位定制稿。"
        )
        try:
            result = await ainvoke_json_with_schema(
                llm,
                system_prompt=TAILOR_SYSTEM_PROMPT,
                user_content=user_content,
                schema=TailoredResumeResult,
                max_attempts=2,
                temperature=0.25,
                max_tokens=8192,
            )
            return _validate_structure(request, result)
        except TailorError:
            raise
        except ValueError as e:
            logger.warning("[ResumeTailor] 结构化输出校验失败: %s", e)
            raise TailorGenerationError("岗位定制稿生成失败，请重试") from e