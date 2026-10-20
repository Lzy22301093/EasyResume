"""生成基本信息格式：联系方式标签、年龄误入出生日期、导出标题兜底。"""

from __future__ import annotations

from app.services.resume_export_service import _normalized_sections, _parse_contact_fields
from app.services.resume_template import assemble_with_template


def test_basic_info_contact_no_double_prefix_and_age():
    assembled = assemble_with_template(
        basic={
            "name": "张三",
            "phone": "电话：13800000000",
            "email": "a@b.com",
            "birthday": "21岁",
            "location": "北京",
        },
        directions=[],
        soft={},
    )
    sec = assembled.to_content()["sections"][0]
    assert sec["title"] == "基本信息"
    assert "联系方式：电话：" not in sec["content"]
    assert "电话：13800000000" in sec["content"]
    assert "年龄：21岁" in sec["content"]
    assert "出生日期：21岁" not in sec["content"]


def test_export_renames_body_title_when_basic_info_like():
    secs = _normalized_sections(
        {"sections": [{"title": "正文", "content": "姓名：张三\n电话：138 · 邮箱：a@b.com"}]}
    )
    assert secs[0]["title"] == "基本信息"


def test_parse_contact_new_and_old_styles():
    pairs_new = _parse_contact_fields(["电话：138 · 邮箱：a@b.com · 城市：北京"])
    assert ("电话", "138") in pairs_new
    assert ("邮箱", "a@b.com") in pairs_new

    pairs_old = _parse_contact_fields(["联系方式：电话：138 · 邮箱：a@b.com"])
    assert ("电话", "138") in pairs_old
    assert ("邮箱", "a@b.com") in pairs_old
