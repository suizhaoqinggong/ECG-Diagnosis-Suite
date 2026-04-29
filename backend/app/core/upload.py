"""
Upload file handling utilities.

Provides safe filename handling, extension validation, and file-size
enforcement for the file upload endpoints.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.core.config import settings


def sanitize_filename(filename: str | None) -> str:
    """Strip directory components and return a safe basename.

    Prevents path-traversal attacks by discarding any directory
    separators and rejecting obviously malicious names.
    """
    if not filename:
        raise HTTPException(
            status_code=400,
            detail="缺少文件名",
        )

    clean = Path(filename).name

    if not clean or clean in (".", ".."):
        raise HTTPException(
            status_code=400,
            detail="无效的文件名",
        )

    if any(ord(c) < 32 for c in clean) or "\x00" in clean:
        raise HTTPException(
            status_code=400,
            detail="文件名包含非法字符",
        )

    return clean


def validate_extension(filename: str) -> None:
    """Ensure the file extension is in the allowlist.

    Raises HTTPException 400 if the extension is not allowed.
    """
    ext = Path(filename).suffix.lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        allowed = ", ".join(settings.ALLOWED_EXTENSIONS)
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型。允许的扩展名：{allowed}",
        )


def save_upload(file: UploadFile, destination: Path) -> None:
    """Save an uploaded file to *destination* with size enforcement.

    Reads in 64 KB chunks and aborts with 413 if the total exceeds
    ``settings.MAX_UPLOAD_SIZE``.  Cleans up the partial file on failure.
    """
    destination.parent.mkdir(parents=True, exist_ok=True)
    max_bytes = settings.MAX_UPLOAD_SIZE
    total = 0

    with destination.open("wb") as out:
        while True:
            chunk = file.file.read(65_536)
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                out.close()
                destination.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=413,
                    detail=f"文件大小超过限制（最大 {max_bytes // (1024 * 1024)} MB）",
                )
            out.write(chunk)
