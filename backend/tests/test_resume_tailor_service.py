"""Tests for ResumeTailorService（岗位定制：已有简历 + JD → 定向简历版本）。"""

import json

import pytest

from app.models.schemas import (
    JDAnalysis,
    ResumeContent,
    ResumeSection,
    TailoredResumeRequest,
)
from app.services.resume_tailor_service import (
    ResumeTailorService,
    TailorError,
    TailorGenerationError,
)


class MockLLM:
    def __init__(self, responses: list[str]):
        self._responses = responses
        self.call_count = 0

    async def chat(self, messages, **kwargs):
        response = self._responses[min(self.call_count, len(self._responses) - 1)]
        self.call_count += 1
        from app.llm import Response
        return Response(content=response)


def _request(mode: str = "focused") -> TailoredResumeRequest:
    return TailoredResumeRequest(
        source_resume=ResumeContent(
            sections=[
                ResumeSection(title="基本信息", content="张三 | 13800000000"),
                ResumeSection(title="项目经历", content="负责后台系统开发，服务 1000 名用户。"),
            ],
            raw_text="旧文本",
        ),
        jd_analysis=JDAnalysis(
            job_title="后端开发工程师",
            company="示例公司",
            summary="负责后端系统开发",
        ),
        mode=mode,
    )


def _result(extra_number: bool = False, hide_project: bool = False, omit_basic: bool = False):
    sections = []
    changes = []
    if not omit_basic:
        sections.append({"title": "基本信息", "content": "张三 | 13800000000"})
        changes.append({"title": "基本信息", "action": "kept", "reason": "保持联系方式原文"})
    if not hide_project:
        suffix = "，效率提升 90%" if extra_number else ""
        sections.append({"title": "项目经历", "content": f"负责后台系统开发{suffix}，服务 1000 名用户。"})
        changes.append({"title": "项目经历", "action": "rewritten", "reason": "突出后端开发经历"})
    else:
        changes.append({"title": "项目经历", "action": "hidden", "reason": "一页精简隐藏"})
    return {
        "content": {"sections": sections, "raw_text": "模型输出的旧 raw_text"},
        "changes": changes,
        "fact_guard": "仅调整已有事实",
    }


@pytest.mark.asyncio
async def test_tailor_resume_normalizes_raw_text_and_changes():
    llm = MockLLM([json.dumps(_result(), ensure_ascii=False)])
    result = await ResumeTailorService().tailor_resume(_request(), llm)
    assert [item.title for item in result.content.sections] == ["基本信息", "项目经历"]
    assert result.content.raw_text.startswith("基本信息\n")
    assert "项目经历" in result.content.raw_text
    assert {item.action for item in result.changes} == {"kept", "rewritten"}


@pytest.mark.asyncio
async def test_tailor_resume_allows_hidden_section_for_one_page():
    llm = MockLLM([json.dumps(_result(hide_project=True), ensure_ascii=False)])
    result = await ResumeTailorService().tailor_resume(_request("one_page"), llm)
    assert [item.title for item in result.content.sections] == ["基本信息"]
    project_change = next(item for item in result.changes if item.title == "项目经历")
    assert project_change.action == "hidden"


@pytest.mark.asyncio
async def test_tailor_resume_blocks_invented_numbers():
    llm = MockLLM([json.dumps(_result(extra_number=True), ensure_ascii=False)])
    with pytest.raises(TailorError, match="原始简历中不存在的数字"):
        await ResumeTailorService().tailor_resume(_request(), llm)


@pytest.mark.asyncio
async def test_tailor_resume_keeps_protected_sections():
    llm = MockLLM([json.dumps(_result(omit_basic=True, hide_project=False), ensure_ascii=False)])
    with pytest.raises(TailorError, match="缺失必要模块"):
        await ResumeTailorService().tailor_resume(_request(), llm)


@pytest.mark.asyncio
async def test_tailor_resume_invalid_llm_output_raises_generation_error():
    llm = MockLLM(["这不是 JSON"])
    with pytest.raises(TailorGenerationError):
        await ResumeTailorService().tailor_resume(_request(), llm)