"""
Diagnosis application service.

Orchestrates the full ECG diagnosis pipeline: image/signal processing,
model inference, quality gating, report generation, and persistence.

Dependency injection is used for key collaborators so that the route layer
can wire in patchable functions (enabling existing tests to keep targeting
``app.api.diagnosis.<name>`` without changes).
"""

import asyncio
import logging
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Type

import numpy as np
from fastapi import HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.upload import save_upload
from app.services.diagnosis_report_service import (
    DiagnosisEnhancedReport,
    get_diagnosis_report_service,
)
from ml.image_decoder import ImageDecodeError, ImageProcessingError

logger = logging.getLogger(__name__)


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
    per_lead_qc: Optional[List[Dict[str, Any]]] = None  # Per-lead quality control metrics
    report: DiagnosisEnhancedReport
    disclaimer: str = "本结果仅供参考，不作为临床诊断依据"


# ---------------------------------------------------------------------------
# Symptom database (PTB-XL superclasses)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Model service singleton
# ---------------------------------------------------------------------------

_model_service = None


def get_model_service():
    """Get or create CardioFormer service instance"""
    global _model_service
    if _model_service is None:
        from ml.cardioformer_service import CardioFormerService

        checkpoint_path = settings.get_model_checkpoint_path()

        if checkpoint_path is None:
            if settings.is_production:
                raise RuntimeError(
                    "Model checkpoint not found. "
                    "Set MODEL_CHECKPOINT_PATH or mount models/checkpoints/best.ckpt."
                )
            logger.warning("⚠️  No model checkpoint found in configured locations.")
            logger.warning("   Falling back to random initialization (for testing only).")
        else:
            logger.info("✅ Found checkpoint: %s", checkpoint_path)

        _model_service = CardioFormerService(
            checkpoint_path=str(checkpoint_path) if checkpoint_path else None,
            num_classes=5,
            signal_length=1000,
            input_channels=12,
            device=settings.DEVICE,
            temperature=settings.MODEL_TEMPERATURE,
            normal_bias=settings.MODEL_NORMAL_BIAS,
        )

    return _model_service


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


async def _create_diagnosis_response(
    *,
    file_reference: str,
    result: Dict[str, Any],
    input_mode: str,
    metadata: Optional[Dict[str, Any]] = None,
    user_id: int | None = None,
    per_lead_qc: Optional[List[Dict[str, Any]]] = None,
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
        detected_labels=result.get("detected_labels"),
        secondary_findings=result.get("secondary_findings"),
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
        per_lead_qc=per_lead_qc,
        report=report,
    )
    return response


# ---------------------------------------------------------------------------
# DiagnosisService
# ---------------------------------------------------------------------------


class DiagnosisService:
    """Orchestrates the full ECG diagnosis pipeline.

    Key collaborators are injected through the constructor so that the route
    layer can pass patchable callables (enabling existing test mocks to work
    without modification).
    """

    def __init__(
        self,
        get_model_service_fn: Callable,
        ecg_loader_cls: Type,
        decode_image_fn: Callable,
        semaphore: asyncio.Semaphore | None = None,
    ):
        self._get_model_service_fn = get_model_service_fn
        self._ecg_loader_cls = ecg_loader_cls
        self._decode_image_fn = decode_image_fn
        # Semaphore to limit concurrent CPU-intensive tasks and prevent
        # CPU oversubscription when using asyncio.to_thread.
        # Should be shared across all service instances (provided by caller).
        self._semaphore = semaphore

    @property
    def _model_service(self):
        """Lazy model service — only initialized when first needed."""
        return self._get_model_service_fn()

    async def _run_in_thread(self, fn, *args, **kwargs):
        """Run a synchronous function in a thread pool with optional concurrency limit.

        Uses a semaphore (if provided) to prevent CPU oversubscription when multiple
        concurrent requests try to run CPU-intensive tasks simultaneously.
        """
        if self._semaphore:
            async with self._semaphore:
                return await asyncio.to_thread(fn, *args, **kwargs)
        return await asyncio.to_thread(fn, *args, **kwargs)

    async def diagnose_image(
        self,
        file: UploadFile,
        safe_name: str,
        user_id: int | None = None,
    ) -> DiagnosisResponse:
        """Full image diagnosis pipeline."""
        t_total_start = time.perf_counter()
        settings.ensure_runtime_dirs()
        upload_dir = settings.upload_dir_path

        file_path = upload_dir / f"{_timestamp()}_{safe_name}"

        t0 = time.perf_counter()
        await self._run_in_thread(save_upload, file, file_path)
        t_upload = time.perf_counter() - t0

        try:
            # Safe image decoding (defends against compression bombs, corrupt images, etc.)
            try:
                t0 = time.perf_counter()
                decoded = await self._run_in_thread(
                    self._decode_image_fn,
                    str(file_path),
                    max_pixels=settings.IMAGE_MAX_PIXELS,
                    max_dimension=settings.IMAGE_MAX_DIMENSION,
                    processing_max_dimension=settings.IMAGE_PROCESSING_MAX_DIMENSION,
                )
                image_array = decoded.image_rgb
                t_decode = time.perf_counter() - t0
            except ImageDecodeError as e:
                logger.warning("Image decode error: %s", str(e))
                raise HTTPException(
                    status_code=400,
                    detail="图像文件无效或损坏",
                )
            except ImageProcessingError as e:
                logger.warning("Image processing error: %s", str(e))
                raise HTTPException(
                    status_code=500,
                    detail="图像处理失败",
                )

            logger.info("📸 Processing image: %s", file.filename)
            logger.info("   Image shape: %s", image_array.shape)

            # --- Signal extraction with QC ---
            t0 = time.perf_counter()
            extraction = await self._run_in_thread(self._model_service.image_converter.extract_with_result, image_array)
            signal_np = extraction.signals
            t_extract = time.perf_counter() - t0

            # --- Inter-lead collapse quality gate (P0) ---
            from ml.signal_quality import analyze_signal_quality

            t0 = time.perf_counter()
            quality_report = await self._run_in_thread(analyze_signal_quality, signal_np)
            t_quality = time.perf_counter() - t0

            # Collect pipeline warnings from extraction QC
            from ml.pipeline_types import ExtractionResult

            extraction_qc: ExtractionResult | None = extraction
            quality_warning = None
            pipeline_warnings: list[str] = []
            per_lead_qc_data: list[dict[str, Any]] | None = None

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
                per_lead_qc_data = [
                    {
                        "lead_index": qc.lead_index,
                        "quality": qc.quality,
                        "flatness": qc.flatness,
                        "coverage": qc.coverage,
                    }
                    for qc in extraction_qc.per_lead_qc
                ]

            # --- If collapsed, skip model inference ---
            if quality_report.is_collapsed:
                logger.warning("⚠️  Signal quality gate FAILED — skipping inference")
                if quality_report.warning:
                    logger.warning("   %s", quality_report.warning)

                pipeline_warnings.insert(0, quality_report.warning or "信号质量不足")

                # Build a minimal result without running the model
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
                    per_lead_qc=per_lead_qc_data,
                    report=report,
                )
                t_total = time.perf_counter() - t_total_start
                logger.info(
                    "⏱  Pipeline timing (collapsed): upload=%.1fms decode=%.1fms "
                    "extract=%.1fms quality=%.1fms total=%.1fms",
                    t_upload * 1000, t_decode * 1000, t_extract * 1000,
                    t_quality * 1000, t_total * 1000,
                )
                return response

            # --- Normal inference path ---
            logger.info("🔮 Running CardioFormer inference...")
            t0 = time.perf_counter()
            result = await self._run_in_thread(self._model_service.predict_from_signal, signal_np)
            t_inference = time.perf_counter() - t0
            result["extraction_qc"] = extraction

            logger.info("✅ Inference completed")
            logger.info("   Prediction: %s", result['prediction'])
            logger.info("   Confidence: %.2f%%", result['confidence'] * 100)

            t0 = time.perf_counter()
            response = await _create_diagnosis_response(
                file_reference=file.filename,
                result=result,
                input_mode="image",
                user_id=user_id,
                per_lead_qc=per_lead_qc_data,
            )
            t_report = time.perf_counter() - t0
            response.quality_warning = quality_warning
            response.pipeline_warnings = pipeline_warnings

            t_total = time.perf_counter() - t_total_start
            logger.info(
                "⏱  Pipeline timing: upload=%.1fms decode=%.1fms "
                "extract=%.1fms quality=%.1fms inference=%.1fms "
                "report=%.1fms total=%.1fms",
                t_upload * 1000, t_decode * 1000, t_extract * 1000,
                t_quality * 1000, t_inference * 1000, t_report * 1000,
                t_total * 1000,
            )
            return response

        except HTTPException:
            # Re-raise HTTP exceptions (including image decode 400s)
            raise
        except Exception as e:
            logger.exception("❌ Image diagnosis failed: %s", str(e))
            raise HTTPException(status_code=500, detail="诊断失败")
        finally:
            file_path.unlink(missing_ok=True)

    async def diagnose_signal(
        self,
        dat_path: Path,
        file_reference: str,
        user_id: int | None = None,
    ) -> DiagnosisResponse:
        """Diagnose from a .dat file that already has a matching .hea on disk."""
        t_total_start = time.perf_counter()
        logger.info("📁 Processing .dat file: %s", file_reference)

        # Load signal data
        loader = self._ecg_loader_cls(target_length=1000, target_leads=12, normalize=True)

        try:
            t0 = time.perf_counter()
            signal_data, metadata = await self._run_in_thread(loader.load_dat_file, str(dat_path))
            t_load = time.perf_counter() - t0
        except FileNotFoundError as e:
            logger.warning("Missing companion file: %s", str(e))
            raise HTTPException(
                status_code=400,
                detail="缺少配套文件。.dat文件需要同名的.hea头文件。",
            )

        # Validate signal format
        if not loader.validate_signal(signal_data):
            raise HTTPException(
                status_code=400, detail="信号数据格式无效，请检查数据完整性"
            )

        logger.info("✅ Signal loaded successfully")
        logger.info("   Shape: %s", signal_data.shape)
        logger.info("   Sample rate: %s Hz", metadata.get('fs', 'unknown'))

        # Model inference directly from signal
        logger.info("🔮 Running CardioFormer inference on signal data...")
        t0 = time.perf_counter()
        result = await self._run_in_thread(self._model_service.predict_from_signal, signal_data)
        t_inference = time.perf_counter() - t0

        logger.info("✅ Inference completed")
        logger.info("   Prediction: %s", result['prediction'])
        logger.info("   Confidence: %.2f%%", result['confidence'] * 100)

        t0 = time.perf_counter()
        response = await _create_diagnosis_response(
            file_reference=file_reference,
            result=result,
            input_mode="signal",
            metadata=metadata,
            user_id=user_id,
            per_lead_qc=None,  # DAT files don't have image extraction QC
        )
        t_report = time.perf_counter() - t0

        t_total = time.perf_counter() - t_total_start
        logger.info(
            "⏱  Pipeline timing (signal): load=%.1fms inference=%.1fms "
            "report=%.1fms total=%.1fms",
            t_load * 1000, t_inference * 1000, t_report * 1000,
            t_total * 1000,
        )
        return response

    async def diagnose_dat_pair(
        self,
        dat_file: UploadFile,
        hea_file: UploadFile,
        dat_safe: str,
        hea_safe: str,
        user_id: int | None = None,
    ) -> DiagnosisResponse:
        """Full dat+hea pair diagnosis pipeline."""
        t_total_start = time.perf_counter()
        settings.ensure_runtime_dirs()
        upload_dir = settings.upload_dir_path
        temp_dir = upload_dir / f"session_{_timestamp()}"
        temp_dir.mkdir(parents=True, exist_ok=True)

        dat_path = temp_dir / dat_safe
        hea_path = temp_dir / hea_safe

        try:
            t0 = time.perf_counter()
            await self._run_in_thread(save_upload, dat_file, dat_path)
            await self._run_in_thread(save_upload, hea_file, hea_path)
            t_upload = time.perf_counter() - t0

            logger.info("✅ Files saved (%.1fms):", t_upload * 1000)
            logger.info("   .dat: %s", dat_path)
            logger.info("   .hea: %s", hea_path)

            response = await self.diagnose_signal(
                dat_path=dat_path,
                file_reference=dat_file.filename,
                user_id=user_id,
            )
            t_total = time.perf_counter() - t_total_start
            logger.info(
                "⏱  Pipeline timing (dat-pair): upload=%.1fms total=%.1fms",
                t_upload * 1000, t_total * 1000,
            )
            return response

        except HTTPException:
            raise
        except Exception as e:
            logger.exception("❌ .dat diagnosis failed: %s", str(e))
            raise HTTPException(status_code=500, detail="诊断失败")
        finally:
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)
                logger.debug("🧹 Cleaned up temp directory: %s", temp_dir)
