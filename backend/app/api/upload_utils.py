"""上传文件安全工具 — 类型校验与限量流式读取。"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import HTTPException, UploadFile


DOCUMENT_SUFFIXES = {".pdf", ".docx", ".txt", ".md"}
DOCUMENT_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
    "text/markdown",
    "application/octet-stream",
}
PHOTO_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
PHOTO_MIME_TYPES = {"image/jpeg", "image/png", "image/webp", "application/octet-stream"}


def validate_upload(
    filename: str | None,
    content_type: str | None,
    allowed_suffixes: set[str],
    allowed_mime_types: set[str],
) -> str:
    """校验文件扩展名与 MIME 类型，返回小写扩展名。"""
    suffix = Path(filename or "").suffix.lower()
    if suffix not in allowed_suffixes:
        raise HTTPException(status_code=415, detail=f"不支持的文件类型: {suffix or '未知'}")

    normalized_mime = (content_type or "").split(";", 1)[0].strip().lower()
    if normalized_mime and normalized_mime not in allowed_mime_types:
        raise HTTPException(status_code=415, detail=f"不支持的文件格式: {normalized_mime}")
    return suffix


async def read_upload_limited(file: UploadFile, max_bytes: int) -> bytes:
    """分块读取上传内容，超过上限立即拒绝，避免整文件进入内存。"""
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(64 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(status_code=413, detail=f"文件不能超过 {max_bytes // (1024 * 1024)}MB")
        chunks.append(chunk)
    if total == 0:
        raise HTTPException(status_code=400, detail="上传文件为空")
    return b"".join(chunks)


async def save_upload_limited(file: UploadFile, target_path: Path, max_bytes: int) -> int:
    """分块保存上传文件，超过上限删除临时文件并拒绝请求。"""
    target_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = target_path.with_name(f"{target_path.name}.part")
    total = 0
    try:
        with temp_path.open("wb") as output:
            while True:
                chunk = await file.read(64 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_bytes:
                    raise HTTPException(status_code=413, detail=f"文件不能超过 {max_bytes // (1024 * 1024)}MB")
                output.write(chunk)
        if total == 0:
            raise HTTPException(status_code=400, detail="上传文件为空")
        os.replace(temp_path, target_path)
        return total
    finally:
        if temp_path.exists():
            temp_path.unlink()
