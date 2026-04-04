"""Deterministic template report builder.

All methods are pure functions that produce a ``DiagnosisEnhancedReport``
without touching the network or external services.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.core.config import settings
from .schemas import DiagnosisEnhancedReport


class TemplateReportBuilder:
    """Build structured ECG reports from diagnosis parameters."""

    # ------------------------------------------------------------------
    # Phrase / section helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_confidence_phrase(confidence: float) -> str:
        if confidence >= 0.85:
            return "模型对当前主判断信号较强"
        if confidence >= 0.7:
            return "模型对当前主判断有中等偏高把握"
        if confidence >= 0.5:
            return "模型给出了倾向性判断，但不确定性仍然明显"
        return "模型输出不确定性较高，应谨慎解读"

    @staticmethod
    def _build_follow_up(severity: Optional[str]) -> List[str]:
        if severity == "严重":
            return [
                "建议尽快线下就医，由心内科医生结合症状、生命体征和辅助检查综合评估。",
                "如伴胸痛、晕厥、呼吸困难等急症表现，应优先急诊处理。",
            ]
        if severity == "中等":
            return [
                "建议在近期安排心内科随访，并结合既往病史进行复核。",
                "可根据医生建议补充动态心电图、超声心动图或实验室检查。",
            ]
        return [
            "建议结合常规体检或门诊复查，持续观察是否出现新的症状。",
            "如近期存在不适表现，仍建议由专业医生结合临床信息复核。",
        ]

    @staticmethod
    def _build_limitations(input_mode: str, confidence: float) -> List[str]:
        limitations = [
            "本报告基于算法输出自动生成，仅供研究和工程验证参考，不能替代医生诊断。",
            "模型结论依赖输入数据质量、采样条件和训练分布，异常噪声或非标准采集会影响结果。",
        ]

        if input_mode == "image":
            limitations.append(
                "图像上传路径包含图像转信号过程，纸质心电图拍摄角度、阴影和分辨率会降低解释可靠性。"
            )

        if confidence < settings.CONFIDENCE_THRESHOLD:
            limitations.append(
                "当前主分类置信度低于系统阈值，应重点参考备选类别并优先进行人工复核。"
            )

        return limitations

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def build_report(
        self,
        *,
        prediction: str,
        confidence: float,
        severity: Optional[str],
        icd_code: Optional[str],
        description: Optional[str],
        recommendations: Optional[List[str]],
        top3_predictions: Optional[List[Dict[str, Any]]],
        input_mode: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> DiagnosisEnhancedReport:
        """Build a deterministic structured report without external dependencies."""
        confidence_percent = f"{confidence * 100:.1f}%"
        confidence_phrase = self._build_confidence_phrase(confidence)

        summary = (
            f"本次 ECG 智能分析的主判断为“{prediction}”，"
            f"当前置信度约为 {confidence_percent}。{confidence_phrase}。"
        )

        interpretation_parts = [
            description or f"模型将该记录归入“{prediction}”类别。",
            f"综合风险分层为“{severity or '未分层'}”。",
        ]
        if icd_code:
            interpretation_parts.append(f"系统关联的 ICD 编码为 {icd_code}。")
        if metadata and metadata.get("fs"):
            interpretation_parts.append(f"本次信号采样率为 {metadata['fs']} Hz。")

        key_findings = [
            f"主分类结果：{prediction}（{confidence_percent}）。",
            f"严重程度：{severity or '未评估'}。",
        ]
        if icd_code:
            key_findings.append(f"关联 ICD 编码：{icd_code}。")
        if top3_predictions:
            alternatives = []
            for item in top3_predictions[1:3]:
                label = item.get("class") or item.get("class_en") or "未知类别"
                probability = item.get("probability")
                if isinstance(probability, (float, int)):
                    alternatives.append(f"{label}（{probability * 100:.1f}%）")
                else:
                    alternatives.append(label)
            if alternatives:
                key_findings.append(f"其他高置信类别包括：{'、'.join(alternatives)}。")

        report_recommendations = list(recommendations or [])
        if not report_recommendations:
            report_recommendations = [
                "建议结合既往病史、临床症状和常规检查结果进行综合判断。",
                "如存在明显不适，请尽快咨询专业医生。",
            ]

        return DiagnosisEnhancedReport(
            source="template",
            summary=summary,
            clinical_interpretation="".join(interpretation_parts),
            key_findings=key_findings,
            recommendations=report_recommendations,
            follow_up=self._build_follow_up(severity),
            limitations=self._build_limitations(input_mode, confidence),
        )
