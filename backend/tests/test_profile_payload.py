"""ProfileItem 结构化 payload 与旧数据兼容解析测试。"""

from types import SimpleNamespace

import pytest

from app.services.profile_payload import (
    dump_profile_payload,
    load_profile_payload,
    parse_legacy_profile_payload,
)


def test_dump_and_load_profile_payload():
    payload = {
        "school": "北京交通大学",
        "degree": "本科",
        "major": "软件工程",
        "start": "2020-09",
        "end": "2024-06",
        "gpa": "3.8",
    }
    item = SimpleNamespace(payload_json=dump_profile_payload(payload), category="education", title="北京交通大学", content="")
    assert load_profile_payload(item) == payload


def test_rejects_non_dict_payload():
    with pytest.raises(ValueError, match="payload 必须是对象"):
        dump_profile_payload(["不是对象"])


def test_legacy_education_multiline_format():
    parsed = parse_legacy_profile_payload(
        "education",
        "北京交通大学",
        "学历：本科\n专业：软件工程\n开始时间：2020-09\n结束时间：2024-06\nGPA：3.8",
    )
    assert parsed == {
        "school": "北京交通大学",
        "degree": "本科",
        "major": "软件工程",
        "start": "2020-09",
        "end": "2024-06",
        "gpa": "3.8",
    }


def test_legacy_education_dot_format():
    parsed = parse_legacy_profile_payload("education", "", "北京交通大学·本科·软件工程")
    assert parsed["school"] == "北京交通大学"
    assert parsed["degree"] == "本科"
    assert parsed["major"] == "软件工程"


def test_legacy_skill_and_experience_fallback():
    skill = parse_legacy_profile_payload("skill", "Python", "熟练使用 FastAPI")
    assert skill == {"name": "Python", "level": "", "notes": "熟练使用 FastAPI"}

    experience = parse_legacy_profile_payload(
        "experience",
        "后端实习生 | 某科技公司",
        "负责接口开发与性能优化",
    )
    assert experience["title"] == "后端实习生"
    assert experience["company"] == "某科技公司"
    assert experience["duty"] == "负责接口开发与性能优化"
    assert experience["exp_type"] == "experience"


def test_load_invalid_json_falls_back_to_legacy():
    item = SimpleNamespace(
        payload_json="{坏 JSON",
        category="education",
        title="清华大学",
        content="学历：硕士\n专业：计算机",
    )
    assert load_profile_payload(item)["school"] == "清华大学"
    assert load_profile_payload(item)["degree"] == "硕士"
