"""面试 REST API — 创建面试、提交回答、获取报告。"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.auth import require_auth
from app.llm import create_llm_provider
from app.models.database import get_db
from app.models.schemas import JDAnalysis
from app.services.jd_service import JDService

router = APIRouter()
logger = logging.getLogger(__name__)

# 全局 handler 实例（在 main.py startup 中初始化）
_handler = None


def set_handler(handler):
    """设置全局 InterviewHandler 实例。"""
    global _handler
    _handler = handler


def _get_handler():
    if _handler is None:
        raise HTTPException(status_code=503, detail="Interview service not initialized")
    return _handler


async def _get_owned_interview_state(
    handler,
    interview_id: str,
    user_id: int,
) -> dict[str, Any]:
    """读取面试状态并校验归属，无权访问统一返回 404。"""
    state = await handler.get_state(interview_id)
    if not state or state.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Interview not found")
    return state


# === Request/Response Models ===

class InterviewStartRequest(BaseModel):
    jd_analysis: dict[str, Any] = Field(..., description="JD 分析结果")
    profile: dict[str, Any] = Field(default_factory=dict, description="候选人画像（补充）")
    referenced_questions: list[str] = Field(default_factory=list, description="已参考的面试题")
    referenced_question_items: list[dict[str, Any]] = Field(
        default_factory=list,
        description="已参考的结构化面试题（含 answer_points）",
    )
    max_turns: int = Field(default=10, ge=3, le=30)
    resume: dict[str, Any] = Field(default_factory=dict, description="本场简历（主材料）")
    use_profile_as_supplement: bool = Field(default=True, description="是否用画像补充")


class InterviewStartResponse(BaseModel):
    interview_id: str
    question: str


class InterviewAnswerRequest(BaseModel):
    answer: str = Field(..., min_length=1, description="候选人回答")


class InterviewAnswerResponse(BaseModel):
    question: str | None = None
    is_complete: bool = False
    report: dict[str, Any] | None = None


class InterviewStateResponse(BaseModel):
    interview_id: str
    is_active: bool
    is_complete: bool
    turn_count: int
    phase: str
    current_question: str
    dimension_scores: dict[str, float]
    difficulty_level: str


# === Endpoints ===

class JdAnalysisRequest(BaseModel):
    """模拟面试准备阶段的 JD 分析请求。"""

    jd_text: str = Field(default="", max_length=20000, description="岗位 JD 文本（可为空，仅用岗位名开面）")
    job_title: str = Field(default="", max_length=120, description="用户填写的目标岗位")
    company: str = Field(default="", max_length=120, description="用户填写的公司名称")


@router.post("/jd-analysis", response_model=JDAnalysis)
async def analyze_interview_jd(
    req: JdAnalysisRequest,
    user: dict = Depends(require_auth),
):
    """真实分析面试 JD；过短/仅岗位名时走启发式，避免无 JD 阻断面试。"""
    title = req.job_title.strip()
    company = req.company.strip()
    jd = req.jd_text.strip()
    source_parts = []
    if title:
        source_parts.append(f"目标岗位：{title}")
    if company:
        source_parts.append(f"公司名称：{company}")
    if jd:
        source_parts.append(f"职位描述：{jd}")
    source_text = "\n".join(source_parts)

    # 无实质 JD（空 JD，或仅很短描述且已填岗位名）：构造基础分析，不调 LLM
    # 保留「有 JD 文本」时走 LLM 校验路径（安全/严格性测试依赖）
    if not jd or (len(jd) < 30 and title):
        job_title = title or (jd[:40] if jd else "目标岗位")
        return JDAnalysis(
            job_title=job_title,
            company=company,
            summary=jd or f"{job_title}岗位面试",
            requirements=[],
        )

    try:
        service = JDService(llm=create_llm_provider())
        return await service.analyze(source_text, strict=True)
    except ValueError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        logger.error(f"analyze_interview_jd failed: {e}", exc_info=True)
        raise HTTPException(status_code=502, detail=f"JD 分析失败: {e}")



@router.post("/start", response_model=InterviewStartResponse)
async def start_interview(
    req: InterviewStartRequest,
    user: dict = Depends(require_auth),
):
    """创建新的模拟面试。"""
    handler = _get_handler()
    try:
        result = await handler.start_interview(
            jd_analysis=req.jd_analysis,
            profile=req.profile,
            referenced_questions=req.referenced_questions,
            referenced_question_items=req.referenced_question_items,
            max_turns=req.max_turns,
            user_id=user["id"],
            resume=req.resume or None,
            use_profile_as_supplement=req.use_profile_as_supplement,
        )
        return InterviewStartResponse(
            interview_id=result["interview_id"],
            question=result["question"],
        )
    except Exception as e:
        logger.error(f"start_interview failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{interview_id}/answer", response_model=InterviewAnswerResponse)
async def submit_answer(
    interview_id: str,
    req: InterviewAnswerRequest,
    user: dict = Depends(require_auth),
):
    """提交候选人回答，获取下一个问题或报告。"""
    handler = _get_handler()
    await _get_owned_interview_state(handler, interview_id, user["id"])
    try:
        result = await handler.process_answer(
            interview_id=interview_id,
            answer=req.answer,
        )
        return InterviewAnswerResponse(
            question=result.get("question"),
            is_complete=result.get("is_complete", False),
            report=result.get("report"),
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"submit_answer failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def list_interview_history(
    user: dict = Depends(require_auth),
    db: Session = Depends(get_db),
    limit: int = 50,
):
    """当前用户的面试历史（已完成报告列表，按时间倒序）。"""
    from app.models.orm import InterviewReport

    user_id = user.get("id") if isinstance(user, dict) else None
    if user_id is None:
        raise HTTPException(status_code=401, detail="未认证，请先登录")

    try:
        q = db.query(InterviewReport)
        # 只查当前用户；历史数据 user_id 可能为空则不展示
        rows = (
            q.filter(InterviewReport.user_id == user_id)
            .order_by(InterviewReport.created_at.desc())
            .limit(max(1, min(int(limit or 50), 100)))
            .all()
        )
        return [
            {
                "interview_id": r.interview_id,
                "target_position": r.target_position or "",
                "turn_count": r.turn_count or 0,
                "completion_reason": r.completion_reason or "",
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "overall_score": _overall_from_report(r.final_report_json),
                "summary": _summary_from_report(r.final_report_json),
            }
            for r in rows
        ]
    except HTTPException:
        raise
    except Exception as e:
        # 旧库缺 proposal_ids 等列时自动补齐再试一次
        if "proposal_ids" in str(e) or "Unknown column" in str(e):
            _ensure_interview_report_columns(db)
            try:
                rows = (
                    db.query(InterviewReport)
                    .filter(InterviewReport.user_id == user_id)
                    .order_by(InterviewReport.created_at.desc())
                    .limit(max(1, min(int(limit or 50), 100)))
                    .all()
                )
                return [
                    {
                        "interview_id": r.interview_id,
                        "target_position": r.target_position or "",
                        "turn_count": r.turn_count or 0,
                        "completion_reason": r.completion_reason or "",
                        "created_at": r.created_at.isoformat() if r.created_at else None,
                        "overall_score": _overall_from_report(r.final_report_json),
                        "summary": _summary_from_report(r.final_report_json),
                    }
                    for r in rows
                ]
            except Exception as e2:
                e = e2
        logger.error(f"list_interview_history failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"加载面试历史失败: {e}")


def _ensure_interview_report_columns(db: Session) -> None:
    """幂等补列，兼容旧 MySQL 库。"""
    from sqlalchemy import inspect, text

    try:
        insp = inspect(db.get_bind())
        cols = {c["name"] for c in insp.get_columns("interview_reports")}
        if "proposal_ids" not in cols:
            db.execute(text("ALTER TABLE interview_reports ADD COLUMN proposal_ids TEXT NULL"))
            db.commit()
            logger.info("[InterviewReport] auto-added column proposal_ids")
    except Exception as e:
        logger.warning(f"[InterviewReport] auto alter failed: {e}")


@router.get("/history/{interview_id}")
async def get_interview_history_detail(
    interview_id: str,
    user: dict = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """面试历史详情：报告 + 对话记录。"""
    import json as _json

    from app.models.orm import InterviewReport

    user_id = user.get("id") if isinstance(user, dict) else None
    if user_id is None:
        raise HTTPException(status_code=401, detail="未认证，请先登录")

    try:
        row = (
            db.query(InterviewReport)
            .filter(
                InterviewReport.interview_id == interview_id,
                InterviewReport.user_id == user_id,
            )
            .first()
        )
        if row is None:
            raise HTTPException(status_code=404, detail="面试记录不存在")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"get_interview_history_detail failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"加载面试详情失败: {e}")

    def _loads(raw: str | None, default):
        if not raw:
            return default
        try:
            return _json.loads(raw)
        except Exception:
            return default

    return {
        "interview_id": row.interview_id,
        "target_position": row.target_position or "",
        "difficulty_level": row.difficulty_level,
        "turn_count": row.turn_count or 0,
        "completion_reason": row.completion_reason or "",
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "dimension_scores": _loads(row.dimension_scores_json, {}),
        "strengths": _loads(row.strengths_json, []),
        "weaknesses": _loads(row.weaknesses_json, []),
        "conversation_history": _loads(row.conversation_history_json, []),
        "final_report": _loads(row.final_report_json, {}),
    }


class TtsPreviewRequest(BaseModel):
    text: str = Field(default="你好，我是今天的面试官，我们开始吧。", max_length=200)
    voice: str = Field(default="", max_length=64)
    speed: float = Field(default=1.1, ge=0.7, le=1.6)
    style: str = Field(default="professional", max_length=40)


@router.get("/tts-voices")
async def tts_voices(user: dict = Depends(require_auth)):
    """可用音色列表（供准备页下拉）。"""
    from app.voice.tts_service import DEFAULT_VOICE, VOICE_OPTIONS

    return {
        "default": DEFAULT_VOICE,
        "voices": VOICE_OPTIONS,
    }


@router.post("/tts-preview")
async def tts_preview(
    data: TtsPreviewRequest,
    user: dict = Depends(require_auth),
):
    """试听 TTS：按音色/语速/风格合成一段 PCM16 音频返回。"""
    import logging

    from fastapi.responses import Response

    from app.config import settings
    from app.voice.tts_service import TTSService

    logger = logging.getLogger(__name__)

    if not settings.openai_api_key:
        raise HTTPException(
            status_code=503,
            detail="语音服务未配置 API Key（backend/.env 的 OPENAI_API_KEY）",
        )

    tts = TTSService()
    text = data.text or "你好，面试官已就绪。"
    try:
        pcm = await tts.synthesize(
            text,
            style=data.style or "professional",
            voice=data.voice or None,
            speed=data.speed,
        )
    except Exception as e:
        logger.error(f"[TTS-preview] failed: {e}", exc_info=True)
        raise HTTPException(status_code=502, detail=f"试听合成失败: {e}")

    if not pcm:
        logger.error(
            "[TTS-preview] empty pcm, model=%s base=%s style=%s speed=%s",
            tts.model,
            tts.base_url,
            data.style,
            data.speed,
        )
        raise HTTPException(
            status_code=502,
            detail="试听未返回音频：请检查 TTS 模型/网络，或查看 backend 日志 [TTS]",
        )

    return Response(
        content=pcm,
        media_type="audio/pcm",
        headers={
            "X-Sample-Rate": "24000",
            "X-Sample-Width": "16",
            "X-Channels": "1",
        },
    )


def _overall_from_report(raw: str | None) -> float | None:
    import json as _json
    if not raw:
        return None
    try:
        data = _json.loads(raw)
        score = data.get("overall_score")
        return float(score) if score is not None else None
    except Exception:
        return None


def _summary_from_report(raw: str | None) -> str:
    import json as _json
    if not raw:
        return ""
    try:
        data = _json.loads(raw)
        return str(data.get("summary") or "")
    except Exception:
        return ""


@router.get("/{interview_id}", response_model=InterviewStateResponse)
async def get_interview_state(
    interview_id: str,
    user: dict = Depends(require_auth),
):
    """获取面试当前状态。"""
    handler = _get_handler()
    state = await _get_owned_interview_state(handler, interview_id, user["id"])
    return InterviewStateResponse(
        interview_id=interview_id,
        is_active=state.get("is_active", False),
        is_complete=state.get("is_complete", False),
        turn_count=state.get("turn_count", 0),
        phase=state.get("phase", ""),
        current_question=state.get("current_question", ""),
        dimension_scores=state.get("dimension_scores", {}),
        difficulty_level=state.get("difficulty_level", "medium"),
    )


@router.get("/{interview_id}/report")
async def get_interview_report(
    interview_id: str,
    user: dict = Depends(require_auth),
):
    """获取面试报告。"""
    handler = _get_handler()
    state = await _get_owned_interview_state(handler, interview_id, user["id"])
    if not state.get("is_complete"):
        raise HTTPException(status_code=400, detail="Interview not yet completed")
    return state.get("final_report", {})
