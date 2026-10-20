"""LLM 结构化调用 Agent。"""

from __future__ import annotations

from app.agents.base import BaseAgent
from app.llm import LLMProvider, Message, Role


class _StructuredCallAgent(BaseAgent):
    """内部结构化调用 Agent（无工具，单次调用）。"""

    name = "structured_call"

    def __init__(
        self,
        llm: LLMProvider,
        system_prompt: str,
        model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 2048,
    ):
        super().__init__(llm, model=model)
        self._system_prompt = system_prompt
        self.temperature = temperature
        self.max_tokens = max_tokens
        # 强制 LLM 输出合法 JSON，避免散文或 markdown 导致 schema 校验失败。
        self.json_mode = True

    def build_messages(self, **kwargs) -> list[Message]:
        return [
            Message(role=Role.SYSTEM, content=self._system_prompt),
            Message(role=Role.USER, content=kwargs["user_content"]),
        ]

    def parse_response(self, content: str) -> dict:
        return {"_content": content}
