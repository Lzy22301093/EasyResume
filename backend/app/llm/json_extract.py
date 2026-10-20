"""LLM JSON 输出提取工具。"""

from __future__ import annotations

import json
import re


def extract_json_object(text: str) -> dict | None:
    """从 LLM 响应中提取 JSON 对象。"""
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        pass

    # 尝试提取 ```json ... ``` 代码块。
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except (json.JSONDecodeError, TypeError):
            pass

    # 使用括号匹配提取最外层 JSON 对象（支持任意深度嵌套）。
    def extract_balanced_json(s: str) -> str | None:
        start = None
        depth = 0
        for i, char in enumerate(s):
            if char in ("{", "["):
                if depth == 0:
                    start = i
                depth += 1
            elif char in ("}", "]"):
                depth -= 1
                if depth == 0 and start is not None:
                    return s[start : i + 1]
        return None

    json_str = extract_balanced_json(text)
    if json_str:
        try:
            return json.loads(json_str)
        except (json.JSONDecodeError, TypeError):
            pass

    return None
