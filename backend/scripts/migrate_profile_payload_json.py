"""CLI: 为 profile_items 增加 payload_json 列（非破坏性、幂等）。

用法（在 backend/ 目录下）：
    python -m scripts.migrate_profile_payload_json --dry-run
    python -m scripts.migrate_profile_payload_json --apply
"""

from __future__ import annotations

import argparse
import sys

from sqlalchemy import inspect, text


def _has_payload_column(engine) -> bool:
    columns = {column["name"] for column in inspect(engine).get_columns("profile_items")}
    return "payload_json" in columns


def main() -> int:
    parser = argparse.ArgumentParser(description="迁移 profile_items.payload_json")
    parser.add_argument("--dry-run", action="store_true", help="仅检查并输出计划")
    parser.add_argument("--apply", action="store_true", help="执行新增列")
    args = parser.parse_args()

    from app.models.database import engine

    exists = _has_payload_column(engine)
    if exists:
        print("profile_items.payload_json 已存在，无需迁移。")
        return 0
    if args.apply:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE profile_items ADD COLUMN payload_json TEXT NULL"))
        print("已新增 profile_items.payload_json。")
    else:
        print("待执行：ALTER TABLE profile_items ADD COLUMN payload_json TEXT NULL")
    return 0


if __name__ == "__main__":
    sys.exit(main())
