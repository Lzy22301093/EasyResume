"""LLM 结构化输出 — ainvoke_json_with_schema（schema 校验 + 自动重试）。

给需要强结构输出的能力单元（consolidate 等）使用：
- 复用 BaseAgent 的超时/重试/参数传递
- 输出经 Pydantic schema 校验，失败自动重试一次
- 校验失败抛出 ValueError，由调用方决定降级策略
"""

from __future__ import annotations

import logging
from typing import Any, Type, TypeVar

from pydantic import BaseModel, ValidationError

from app.llm import LLMProvider
from app.llm.json_extract import extract_json_object

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


def parse_structured_json(raw: str, schema: Type[T]) -> T:
    """解析 LLM JSON 输出并执行 Pydantic schema 校验。

    所有 LLM 结构化结果统一经过本入口，禁止调用方直接 json.loads 后裸用。
    """
    extracted = extract_json_object(raw)
    if extracted is None:
        raise ValueError("输出中未找到 JSON 对象")
    return schema.model_validate(extracted)


def __getattr__(name: str):
    """兼容历史测试/调用方按原路径获取内部结构化 Agent。"""
    if name == "_StructuredCallAgent":
        from app.llm.structured_call import _StructuredCallAgent

        return _StructuredCallAgent
    raise AttributeError(name)


async def ainvoke_json_with_schema(
    llm: LLMProvider,
    system_prompt: str,
    user_content: str,
    schema: Type[T],
    *,
    max_attempts: int = 2,
    model: str | None = None,
    temperature: float = 0.3,
    max_tokens: int = 2048,
) -> T:
    """调用 LLM 并返回通过 schema 校验的对象。

    Args:
        llm: LLMProvider 实例。
        system_prompt: 系统提示词。
        user_content: 用户消息内容。
        schema: Pydantic 输出模型。
        max_attempts: 最大尝试次数（含首次），解析/校验失败自动重试。
        model: 指定模型（None 用 provider 默认）。
        temperature / max_tokens: 调用参数。

    Returns:
        校验通过的对象。

    Raises:
        ValueError: 所有尝试均未通过校验。
    """
    from app.llm.structured_call import _StructuredCallAgent

    agent = _StructuredCallAgent(
        llm, system_prompt, model=model, temperature=temperature, max_tokens=max_tokens
    )
    last_error: Exception | None = None

    for attempt in range(max_attempts):
        try:
            result = await agent.run(user_content=user_content)
            raw = result.get("_content", "")
            return parse_structured_json(raw, schema)
        except ValidationError as e:
            last_error = e
            logger.warning(f"schema 校验失败 (attempt {attempt + 1}/{max_attempts}): {e}")
        except ValueError as e:
            last_error = e
            logger.warning(f"JSON 提取失败 (attempt {attempt + 1}/{max_attempts}): {e}")

    raise ValueError(f"LLM 输出无法通过 schema 校验: {last_error}")
