"""ProfileItem 结构化 payload 的序列化与旧文本兼容解析。"""

from __future__ import annotations

import json
from typing import Any

from app.models.orm import ProfileItem


def dump_profile_payload(payload: dict[str, Any]) -> str:
    """把结构化画像字段序列化为 JSON 字符串。"""
    if not isinstance(payload, dict):
        raise ValueError("payload 必须是对象")
    try:
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    except (TypeError, ValueError) as exc:
        raise ValueError("payload 必须可序列化为 JSON") from exc


def load_profile_payload(item: ProfileItem) -> dict[str, Any]:
    """读取结构化 payload；旧数据或非法 JSON 回退到文本解析。"""
    raw = getattr(item, "payload_json", None)
    if raw:
        try:
            parsed = json.loads(raw)
        except (TypeError, ValueError):
            parsed = None
        if isinstance(parsed, dict):
            return parsed
    return parse_legacy_profile_payload(item.category, item.title, item.content or "")


def parse_legacy_profile_payload(category: str, title: str, content: str) -> dict[str, Any]:
    """把旧的 title/content 形态解析为结构化字段。"""
    if category == "education":
        return _parse_legacy_education(title, content)
    if category == "skill":
        return {"name": title.strip(), "level": "", "notes": content.strip()}
    if category == "experience":
        return _parse_legacy_experience(title, content)
    return {"title": title.strip(), "content": content.strip()}


def _parse_legacy_education(title: str, content: str) -> dict[str, Any]:
    result: dict[str, Any] = {
        "school": title.strip(),
        "degree": "",
        "major": "",
        "start": "",
        "end": "",
        "gpa": "",
    }
    if "·" in content:
        parts = [part.strip() for part in content.split("·")]
        if len(parts) >= 3:
            result.update({"school": title.strip() or parts[0], "degree": parts[1], "major": parts[2]})
        return result

    labels = {
        "学校": "school",
        "学历": "degree",
        "专业": "major",
        "开始时间": "start",
        "结束时间": "end",
        "GPA": "gpa",
    }
    for line in content.splitlines():
        if "：" not in line:
            continue
        label, value = line.split("：", 1)
        key = labels.get(label.strip())
        if key:
            result[key] = value.strip()
    return result


def _parse_legacy_experience(title: str, content: str) -> dict[str, Any]:
    company = ""
    entry_title = title.strip()
    if "|" in entry_title:
        entry_title, company = [part.strip() for part in entry_title.split("|", 1)]
    return {
        "exp_type": "experience",
        "company": company,
        "title": entry_title,
        "start": "",
        "end": "",
        "current": False,
        "duration": "",
        "tech_stack": "",
        "duty": content.strip(),
        "achievement": "",
        "situation": "",
        "task": "",
        "action": "",
        "result": "",
    }
