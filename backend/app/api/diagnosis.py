"""
Diagnosis API endpoints.

Thin route layer that validates inputs, delegates to DiagnosisService,
and returns responses.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile

from app.core.auth_dependencies import get_optional_user
from app.core.rate_limit import (
    check_diagnosis_anonymous_limit,
    check_diagnosis_authenticated_limit,
)
from app.core.upload import sanitize_filename, validate_extension
from app.models.user import User
from app.services.diagnosis_service import (
    DiagnosisResponse,
    DiagnosisService,
    SYMPTOM_DATABASE,
    get_model_service,
)
from app.services.ecg_dat_loader import ECGDataLoader
from ml.image_decoder import safe_decode_image

logger = logging.getLogger(__name__)

router = APIRouter()
IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg")

# Global semaphore to limit concurrent CPU-intensive tasks across all requests.
# This prevents CPU oversubscription when multiple requests run model inference
# simultaneously. The limit is shared across all DiagnosisService instances.
_global_inference_semaphore = asyncio.Semaphore(4)


def _get_diagnosis_service() -> DiagnosisService:
    """Build a DiagnosisService wired to the current module-level hooks.

    The injected callables are resolved lazily from this module's
    namespace, so that existing test patches targeting
    ``app.api.diagnosis.<name>`` intercept the calls.
    """
    return DiagnosisService(
        get_model_service_fn=get_model_service,
        ecg_loader_cls=ECGDataLoader,
        decode_image_fn=safe_decode_image,
        semaphore=_global_inference_semaphore,
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/diagnose", response_model=DiagnosisResponse)
async def diagnose_ecg(
    request: Request,
    file: UploadFile = File(...),
    current_user: User | None = Depends(get_optional_user),
):
    """
    上传ECG数据并获取诊断结果

    支持的格式：
    - 图片格式: .png, .jpg, .jpeg
    - ECG数据双文件格式请使用 /api/diagnose-dat
    """
    # Rate limiting
    if current_user:
        await check_diagnosis_authenticated_limit(current_user.id)
    else:
        await check_diagnosis_anonymous_limit(request)

    user_id = current_user.id if current_user else None
    safe_name = sanitize_filename(file.filename)
    validate_extension(safe_name)

    # 验证文件类型
    if safe_name.lower().endswith(".dat"):
        raise HTTPException(
            status_code=400,
            detail="单个 .dat 文件无法独立诊断，请使用 /api/diagnose-dat 同时上传同名的 .dat 和 .hea 文件。",
        )
    elif safe_name.lower().endswith(IMAGE_EXTENSIONS):
        service = _get_diagnosis_service()
        return await service.diagnose_image(file, safe_name, user_id=user_id)
    else:
        raise HTTPException(
            status_code=400,
            detail="不支持的文件格式。支持的格式：图片(.png, .jpg, .jpeg) 或 ECG数据(.dat)",
        )


@router.post("/diagnose-dat", response_model=DiagnosisResponse)
async def diagnose_ecg_dat_files(
    request: Request,
    files: List[UploadFile] = File(...),
    current_user: User | None = Depends(get_optional_user),
):
    """
    上传.dat和.hea文件进行诊断

    需要同时上传两个文件：
    - .dat文件：ECG信号数据
    - .hea文件：头文件（元数据）

    两个文件必须文件名相同（只有扩展名不同）
    """
    # Rate limiting
    if current_user:
        await check_diagnosis_authenticated_limit(current_user.id)
    else:
        await check_diagnosis_anonymous_limit(request)

    user_id = current_user.id if current_user else None
    # 验证文件数量
    if len(files) != 2:
        raise HTTPException(status_code=400, detail="请同时上传.dat和.hea两个文件")

    # 识别.dat和.hea文件
    dat_file: UploadFile | None = None
    hea_file: UploadFile | None = None
    dat_safe: str | None = None
    hea_safe: str | None = None

    for file in files:
        safe_name = sanitize_filename(file.filename)
        validate_extension(safe_name)
        if safe_name.lower().endswith(".dat"):
            dat_file = file
            dat_safe = safe_name
        elif safe_name.lower().endswith(".hea"):
            hea_file = file
            hea_safe = safe_name

    if not dat_file or not hea_file or not dat_safe or not hea_safe:
        raise HTTPException(
            status_code=400, detail="必须包含一个.dat文件和一个.hea文件"
        )

    # 验证文件名匹配（仅比较去掉扩展名后的基名）
    # 用 Path.stem 而不是 .replace()，避免类似 "my.dat.summary.dat" 的多次替换错误
    dat_name = Path(dat_safe).stem
    hea_name = Path(hea_safe).stem

    if dat_name != hea_name:
        raise HTTPException(
            status_code=400,
            detail=f".dat和.hea文件名必须相同（不含扩展名）。.dat: {dat_name}, .hea: {hea_name}",
        )

    service = _get_diagnosis_service()
    return await service.diagnose_dat_pair(
        dat_file=dat_file,
        hea_file=hea_file,
        dat_safe=dat_safe,
        hea_safe=hea_safe,
        user_id=user_id,
    )
