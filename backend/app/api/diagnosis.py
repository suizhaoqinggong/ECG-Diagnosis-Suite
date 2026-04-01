"""
Diagnosis API endpoints
"""

import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from fastapi import APIRouter, File, HTTPException, UploadFile
from PIL import Image
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.upload import sanitize_filename, save_upload, validate_extension
from app.models.db_models import DiagnosisRecord
from app.services.diagnosis_report_service import (
    DiagnosisEnhancedReport, get_diagnosis_report_service)
from app.services.ecg_dat_loader import ECGDataLoader
from ml.cardioformer_service import CardioFormerService
from ml.image_decoder import (
    ImageDecodeError,
    ImageProcessingError,
    safe_decode_image,
)

router = APIRouter()


class DiagnosisResponse(BaseModel):
    prediction: str
    confidence: float
    severity: Optional[str] = None
    icd_code: Optional[str] = None
    description: Optional[str] = None
    recommendations: Optional[List[str]] = None
    timestamp: str
    all_probabilities: Optional[Dict[str, float]] = None
    top3_predictions: Optional[List[Dict[str, Any]]] = None
    detected_labels: Optional[List[str]] = None  # All labels above threshold
    secondary_findings: Optional[List[str]] = None  # Non-primary detected labels
    quality_warning: Optional[str] = None  # "pass", "warn", or "fail"
    pipeline_warnings: List[str] = Field(default_factory=list)  # Human-readable quality messages
    report: DiagnosisEnhancedReport
    disclaimer: str = "本结果仅供参考，不作为临床诊断依据"


# Initialize CardioFormer service (singleton)
_model_service = None


def get_model_service():
    """Get or create CardioFormer service instance"""
    global _model_service
    if _model_service is None:
        checkpoint_path = settings.get_model_checkpoint_path()

        if checkpoint_path is None:
            print("⚠️  No model checkpoint found in configured locations.")
            print("   Falling back to random initialization (for testing only).")
        else:
            print(f"✅ Found checkpoint: {checkpoint_path}")

        _model_service = CardioFormerService(
            checkpoint_path=str(checkpoint_path) if checkpoint_path else None,
            num_classes=5,
            signal_length=1000,
            input_channels=12,
            device=settings.DEVICE,
        )

    return _model_service


# 症状数据库 - 基于PTB-XL超类
SYMPTOM_DATABASE = {
    "正常": {
        "severity": "正常",
        "icd_code": "R00.0",
        "description": "心电图波形正常，未发现明显异常。",
        "recommendations": [
            "保持健康的生活方式",
            "定期体检",
            "适量运动",
        ],
    },
    "心肌梗死": {
        "severity": "严重",
        "icd_code": "I21.0",
        "description": "心电图提示可能存在心肌梗死，这是由于冠状动脉阻塞导致心肌缺血坏死。",
        "recommendations": [
            "立即就医急诊科",
            "需要紧急冠脉造影评估",
            "遵医嘱服用抗血小板药物",
            "卧床休息，避免剧烈活动",
            "控制血压、血糖、血脂",
        ],
    },
    "ST-T改变": {
        "severity": "中等",
        "icd_code": "I20.0",
        "description": "ST段或T波出现异常改变，可能提示心肌缺血、电解质紊乱或其他心脏问题。",
        "recommendations": [
            "建议心内科专科就诊",
            "进一步完善心脏超声检查",
            "监测血压和心率",
            "避免剧烈运动和情绪激动",
            "定期复查心电图",
        ],
    },
    "传导障碍": {
        "severity": "中等",
        "icd_code": "I44.0",
        "description": "心脏传导系统出现异常，可能导致心跳过缓或不规则。",
        "recommendations": [
            "建议心内科就诊",
            "必要时进行24小时动态心电图监测",
            "评估是否需要起搏器植入",
            "避免使用影响心率的药物",
            "定期复查心电图",
        ],
    },
    "心室肥大": {
        "severity": "中等",
        "icd_code": "I42.0",
        "description": "心室壁增厚，可能由于高血压、心脏瓣膜病等原因导致。",
        "recommendations": [
            "建议心内科就诊",
            "完善心脏超声检查",
            "控制血压在正常范围",
            "限制钠盐摄入",
            "定期随访心脏功能",
        ],
    },
}


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


async def _save_diagnosis_record(
    file_reference: str, result: DiagnosisResponse
) -> None:
    async with AsyncSessionLocal() as session:
        session.add(
            DiagnosisRecord(
                image_path=file_reference,
                prediction=result.prediction,
                confidence=result.confidence,
                severity=result.severity,
                icd_code=result.icd_code,
                description=result.description,
                recommendations=result.recommendations,
            )
        )
        await session.commit()


async def _create_diagnosis_response(
    *,
    file_reference: str,
    result: Dict[str, Any],
    input_mode: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> DiagnosisResponse:
    prediction = result["prediction"]
    confidence = result["confidence"]
    symptom_info = SYMPTOM_DATABASE.get(prediction, {})

    report = await get_diagnosis_report_service().generate_report(
        prediction=prediction,
        confidence=confidence,
        severity=symptom_info.get("severity"),
        icd_code=symptom_info.get("icd_code"),
        description=symptom_info.get("description"),
        recommendations=symptom_info.get("recommendations"),
        top3_predictions=result.get("top3_predictions"),
        all_probabilities=result.get("all_probabilities"),
        input_mode=input_mode,
        metadata=metadata,
    )

    response = DiagnosisResponse(
        prediction=prediction,
        confidence=confidence,
        severity=symptom_info.get("severity"),
        icd_code=symptom_info.get("icd_code"),
        description=symptom_info.get("description"),
        recommendations=symptom_info.get("recommendations"),
        timestamp=datetime.now().isoformat(),
        all_probabilities=result.get("all_probabilities"),
        top3_predictions=result.get("top3_predictions"),
        detected_labels=result.get("detected_labels"),
        secondary_findings=result.get("secondary_findings"),
        report=report,
    )
    await _save_diagnosis_record(file_reference, response)
    return response


@router.post("/diagnose", response_model=DiagnosisResponse)
async def diagnose_ecg(file: UploadFile = File(...)):
    """
    上传ECG数据并获取诊断结果

    支持的格式：
    - 图片格式: .png, .jpg, .jpeg
    - ECG数据格式: .dat (PTB-XL格式，需要配套.hea文件)
    """
    safe_name = sanitize_filename(file.filename)
    validate_extension(safe_name)

    # 验证文件类型
    if safe_name.lower().endswith(".dat"):
        # 处理.dat文件
        return await _diagnose_dat_file(file, safe_name)
    elif file.content_type and file.content_type.startswith("image/"):
        # 处理图片文件
        return await _diagnose_image_file(file, safe_name)
    else:
        raise HTTPException(
            status_code=400,
            detail="不支持的文件格式。支持的格式：图片(.png, .jpg, .jpeg) 或 ECG数据(.dat)",
        )


async def _diagnose_dat_file(file: UploadFile, safe_name: str) -> DiagnosisResponse:
    """
    处理.dat文件上传和诊断
    """
    settings.ensure_runtime_dirs()
    upload_dir = settings.upload_dir_path
    temp_dir = upload_dir / f"single_{_timestamp()}"
    temp_dir.mkdir(parents=True, exist_ok=True)

    dat_path = temp_dir / safe_name

    try:
        save_upload(file, dat_path)

        print(f"📁 Processing .dat file: {file.filename}")

        # 加载.dat文件
        loader = ECGDataLoader(target_length=1000, target_leads=12, normalize=True)

        # 尝试加载信号数据
        # 注意：需要配套的.hea文件
        try:
            signal_data, metadata = loader.load_dat_file(str(dat_path))
        except FileNotFoundError as e:
            # 如果找不到.hea文件，给出明确提示
            raise HTTPException(
                status_code=400,
                detail=f"缺少配套文件：{str(e)}。.dat文件需要同名的.hea头文件。",
            )

        # 验证信号格式
        if not loader.validate_signal(signal_data):
            raise HTTPException(
                status_code=400, detail="信号数据格式无效，请检查数据完整性"
            )

        print(f"✅ Signal loaded successfully")
        print(f"   Shape: {signal_data.shape}")
        print(f"   Sample rate: {metadata.get('fs', 'unknown')} Hz")

        # 获取模型服务
        service = get_model_service()

        # 直接从信号进行推理（跳过图像转换）
        print("🔮 Running CardioFormer inference on signal data...")
        result = service.predict_from_signal(signal_data)

        print(f"✅ Inference completed")
        print(f"   Prediction: {result['prediction']}")
        print(f"   Confidence: {result['confidence']:.2%}")

        return await _create_diagnosis_response(
            file_reference=file.filename,
            result=result,
            input_mode="signal",
            metadata=metadata,
        )

    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        print(f"❌ .dat diagnosis failed: {str(e)}")
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"诊断失败: {str(e)}")
    finally:
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)


async def _diagnose_image_file(file: UploadFile, safe_name: str) -> DiagnosisResponse:
    """
    处理图片文件上传和诊断（原有逻辑）
    """
    settings.ensure_runtime_dirs()
    upload_dir = settings.upload_dir_path

    file_path = upload_dir / f"{_timestamp()}_{safe_name}"

    save_upload(file, file_path)

    try:
        # 使用安全图像解码器（防御压缩炸弹、损坏图像等）
        try:
            decoded = safe_decode_image(
                str(file_path),
                max_pixels=settings.IMAGE_MAX_PIXELS,
                max_dimension=settings.IMAGE_MAX_DIMENSION,
                processing_max_dimension=settings.IMAGE_PROCESSING_MAX_DIMENSION,
            )
            image_array = decoded.image_rgb
        except ImageDecodeError as e:
            raise HTTPException(
                status_code=400,
                detail=f"图像文件无效或损坏: {str(e)}",
            )
        except ImageProcessingError as e:
            raise HTTPException(
                status_code=500,
                detail=f"图像处理失败: {str(e)}",
            )

        print(f"📸 Processing image: {file.filename}")
        print(f"   Image shape: {image_array.shape}")

        # 获取模型服务
        service = get_model_service()

        # --- Signal extraction with QC ---
        extraction = service.image_converter.extract_with_result(image_array)
        signal_np = extraction.signals

        # --- Inter-lead collapse quality gate (P0) ---
        from ml.signal_quality import analyze_signal_quality

        quality_report = analyze_signal_quality(signal_np)

        # Collect pipeline warnings from extraction QC
        from ml.pipeline_types import ExtractionResult

        extraction_qc: ExtractionResult | None = extraction
        quality_warning = None
        pipeline_warnings: list[str] = []

        if extraction_qc is not None:
            quality_warning = extraction_qc.overall_quality
            for qc in extraction_qc.per_lead_qc:
                if qc.quality in ("fail", "poor"):
                    pipeline_warnings.append(
                        f"导联 {qc.lead_index} 信号提取质量较差 "
                        f"(覆盖率: {qc.coverage:.1%}, 质量: {qc.quality})"
                    )
            if extraction_qc.interpolated_ratio > 0.3:
                pipeline_warnings.append(
                    f"信号插值比例较高 ({extraction_qc.interpolated_ratio:.1%})"
                )
            pipeline_warnings.extend(extraction_qc.warnings)
            for issue in extraction_qc.issues:
                pipeline_warnings.append(issue.message)

        # --- If collapsed, skip model inference ---
        if quality_report.is_collapsed:
            print(f"⚠️  Signal quality gate FAILED — skipping inference")
            if quality_report.warning:
                print(f"   {quality_report.warning}")

            pipeline_warnings.insert(0, quality_report.warning or "信号质量不足")

            # Build a minimal result without running the model
            from app.services.diagnosis_report_service import DiagnosisEnhancedReport

            report = DiagnosisEnhancedReport(
                source="template",
                summary="信号质量不足，无法进行可靠诊断",
                clinical_interpretation=(
                    "图像转换提取的导联信号高度相似或过于平坦，"
                    "无法进行有效的心电图分析。"
                    "请尝试上传更清晰的ECG图像。"
                ),
            )
            response = DiagnosisResponse(
                prediction="信号质量不足",
                confidence=0.0,
                severity=None,
                icd_code=None,
                description=None,
                recommendations=None,
                timestamp=datetime.now().isoformat(),
                all_probabilities=None,
                top3_predictions=None,
                detected_labels=None,
                secondary_findings=None,
                quality_warning=quality_warning,
                pipeline_warnings=pipeline_warnings,
                report=report,
            )
            # Persist collapsed uploads to history (Codex review fix #1)
            await _save_diagnosis_record(file.filename, response)
            return response

        # --- Normal inference path ---
        print("🔮 Running CardioFormer inference...")
        result = service.predict_from_signal(signal_np)
        result["extraction_qc"] = extraction

        print(f"✅ Inference completed")
        print(f"   Prediction: {result['prediction']}")
        print(f"   Confidence: {result['confidence']:.2%}")

        response = await _create_diagnosis_response(
            file_reference=file.filename,
            result=result,
            input_mode="image",
        )
        response.quality_warning = quality_warning
        response.pipeline_warnings = pipeline_warnings
        return response

    except HTTPException:
        # 重新抛出 HTTP 异常（包括图像解码错误 400）
        raise
    except Exception as e:
        print(f"❌ Image diagnosis failed: {str(e)}")
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"诊断失败: {str(e)}")
    finally:
        file_path.unlink(missing_ok=True)


@router.post("/diagnose-dat", response_model=DiagnosisResponse)
async def diagnose_ecg_dat_files(files: List[UploadFile] = File(...)):
    """
    上传.dat和.hea文件进行诊断

    需要同时上传两个文件：
    - .dat文件：ECG信号数据
    - .hea文件：头文件（元数据）

    两个文件必须文件名相同（只有扩展名不同）
    """
    # 验证文件数量
    if len(files) != 2:
        raise HTTPException(status_code=400, detail="请同时上传.dat和.hea两个文件")

    # 识别.dat和.hea文件
    dat_file = None
    hea_file = None

    for file in files:
        safe_name = sanitize_filename(file.filename)
        validate_extension(safe_name)
        if safe_name.lower().endswith(".dat"):
            dat_file = file
        elif safe_name.lower().endswith(".hea"):
            hea_file = file

    if not dat_file or not hea_file:
        raise HTTPException(
            status_code=400, detail="必须包含一个.dat文件和一个.hea文件"
        )

    # 验证文件名匹配
    dat_name = dat_file.filename.replace(".dat", "").replace(".DAT", "")
    hea_name = hea_file.filename.replace(".hea", "").replace(".HEA", "")

    if dat_name != hea_name:
        raise HTTPException(
            status_code=400,
            detail=f".dat和.hea文件名必须相同（不含扩展名）。.dat: {dat_name}, .hea: {hea_name}",
        )

    print(f"📁 Processing .dat + .hea files: {dat_file.filename} + {hea_file.filename}")

    settings.ensure_runtime_dirs()
    upload_dir = settings.upload_dir_path
    temp_dir = upload_dir / f"session_{_timestamp()}"
    temp_dir.mkdir(parents=True, exist_ok=True)

    # 使用安全文件名（wfdb需要文件名与.hea中的记录名匹配）
    dat_safe = sanitize_filename(dat_file.filename)
    hea_safe = sanitize_filename(hea_file.filename)
    dat_path = temp_dir / dat_safe
    hea_path = temp_dir / hea_safe

    try:
        save_upload(dat_file, dat_path)
        save_upload(hea_file, hea_path)

        print(f"✅ Files saved:")
        print(f"   .dat: {dat_path}")
        print(f"   .hea: {hea_path}")

        # 加载.dat文件
        loader = ECGDataLoader(target_length=1000, target_leads=12, normalize=True)

        signal_data, metadata = loader.load_dat_file(str(dat_path))

        # 验证信号格式
        if not loader.validate_signal(signal_data):
            raise HTTPException(
                status_code=400, detail="信号数据格式无效，请检查数据完整性"
            )

        print(f"✅ Signal loaded successfully")
        print(f"   Shape: {signal_data.shape}")
        print(f"   Sample rate: {metadata.get('fs', 'unknown')} Hz")

        # 获取模型服务
        service = get_model_service()

        # 直接从信号进行推理
        print("🔮 Running CardioFormer inference on signal data...")
        result = service.predict_from_signal(signal_data)

        print(f"✅ Inference completed")
        print(f"   Prediction: {result['prediction']}")
        print(f"   Confidence: {result['confidence']:.2%}")

        return await _create_diagnosis_response(
            file_reference=dat_file.filename,
            result=result,
            input_mode="signal",
            metadata=metadata,
        )

    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        print(f"❌ .dat diagnosis failed: {str(e)}")
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"诊断失败: {str(e)}")
    finally:
        # 清理整个临时目录
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
            print(f"🧹 Cleaned up temp directory: {temp_dir}")


@router.get("/history")
async def get_diagnosis_history(limit: int = 20):
    """
    获取诊断历史记录
    """
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=400, detail="limit 必须在 1 到 100 之间")

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(DiagnosisRecord)
            .order_by(DiagnosisRecord.created_at.desc())
            .limit(limit)
        )
        records = result.scalars().all()

    return {
        "items": [record.to_dict() for record in records],
        "count": len(records),
    }
