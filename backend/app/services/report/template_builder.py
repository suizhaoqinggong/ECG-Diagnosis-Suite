"""Deterministic template report builder.

All methods are pure functions that produce a ``DiagnosisEnhancedReport``
without touching the network or external services.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.core.config import settings
from .schemas import DiagnosisEnhancedReport


# ---------------------------------------------------------------------------
# Diagnosis-specific content profiles
# ---------------------------------------------------------------------------
# Each profile provides per-diagnosis phrasing for summary, interpretation,
# follow-up, and additional key findings.  Templates are keyed by
# confidence tier: "high" (≥0.85), "medium" (≥0.60), "low" (<0.60).

_DIAGNOSIS_PROFILES: Dict[str, Dict[str, Any]] = {
    "正常": {
        "summary": {
            "high": (
                "本次ECG智能分析显示，心电波形在各导联上均呈现正常形态，"
                "P波、QRS波群、ST段及T波未见明显异常改变，属于典型正常心电图表现。"
            ),
            "medium": (
                "本次分析倾向于判断为正常心电图，"
                "各导联波形大致在正常参考范围内。"
                "不过部分波形特征不够十分典型，建议在常规体检中加以确认。"
            ),
            "low": (
                "本次分析初步判断为正常心电图，"
                "但由于当前信号特征不够明确，结合临床复查会更稳妥。"
            ),
        },
        "interpretation": {
            "high": (
                "各导联P波形态、时限正常，QRS波群时限和振幅在正常范围，"
                "ST段无抬高或压低，T波方向及形态未见病理性改变。"
                "未见异常Q波、传导延迟或心室肥厚的电压标准。"
            ),
            "medium": (
                "各导联主要波形基本在正常范围，但存在一些非特异性改变，"
                "尚不足以支持病理性诊断。"
            ),
            "low": (
                "波形整体未达到异常诊断标准，但受限于信号质量，"
                "部分细微异常可能无法完全排除。"
            ),
        },
        "key_finding_extras": [
            "未见ST段抬高或压低",
            "QT间期在正常参考范围内",
            "未见病理性Q波",
            "各导联QRS波群时限正常",
        ],
        "follow_up": [
            "保持健康的生活方式，包括均衡饮食、规律运动和充足睡眠。",
            "建议每年进行一次常规体检和心电图检查。",
            "如出现胸闷、心悸、气短等新发症状，应及时就医复查。",
        ],
    },
    "心肌梗死": {
        "summary": {
            "high": (
                "本次ECG智能分析检测到典型心肌梗死相关波形改变，"
                "包括ST段抬高或压低、病理性Q波等高危征象，"
                "需要引起高度重视。"
            ),
            "medium": (
                "本次分析检测到可能存在心肌梗死的波形改变，"
                "ST段及QRS波群存在异常，但征象不是特别显著，"
                "建议结合临床症状和心肌酶学检查综合评估。"
            ),
            "low": (
                "本次分析提示可能存在心肌梗死波形改变，"
                "但信号特征不够典型，应结合临床症状及时排查。"
            ),
        },
        "interpretation": {
            "high": (
                "心电图显示明确的ST段改变，可能伴随病理性Q波形成或T波倒置，"
                "符合心肌缺血或梗死的典型心电图演变特征。"
                "考虑冠状动脉急性阻塞的可能，需尽快进行冠脉评估。"
            ),
            "medium": (
                "ST段及T波存在异常改变，可能提示心肌缺血。"
                "建议进一步完善心肌损伤标志物检测（如肌钙蛋白）及冠脉影像学检查。"
            ),
            "low": (
                "心电图存在可疑异常改变，但缺乏典型心肌梗死的诊断标准。"
                "建议结合临床表现及实验室检查进行综合判断。"
            ),
        },
        "key_finding_extras": [
            "ST段存在异常抬高或压低",
            "可能出现病理性Q波",
            "T波改变提示心肌缺血可能",
        ],
        "follow_up": [
            "立即就医急诊科，进行紧急评估和处理。",
            "需要进行冠脉造影检查，评估血管堵塞情况。",
            "遵医嘱服用抗血小板药物及其他心血管保护药物。",
            "卧床休息，避免任何体力活动和情绪激动。",
            "严密监测生命体征及心电变化。",
        ],
    },
    "ST-T改变": {
        "summary": {
            "high": (
                "本次ECG智能分析检测到明确的ST段及T波异常改变，"
                "提示心肌复极化过程存在异常，可能与心肌缺血、"
                "电解质紊乱或其他心脏病变相关。"
            ),
            "medium": (
                "本次分析检测到ST段或T波存在异常改变，"
                "但改变幅度和范围有限，建议进一步排查潜在病因。"
            ),
            "low": (
                "本次分析提示可能存在ST-T改变，"
                "但信号特征不够典型，建议结合临床复查。"
            ),
        },
        "interpretation": {
            "high": (
                "ST段偏离基线、T波低平或倒置等改变，反映心室复极化异常。"
                "常见原因包括冠状动脉供血不足、电解质紊乱（如低钾）、"
                "药物影响或心肌病变。需要结合临床背景进一步鉴别。"
            ),
            "medium": (
                "存在非特异性的ST-T改变，可能由多种因素引起，"
                "包括心肌缺血、电解质失衡或自主神经调节异常等。"
            ),
            "low": (
                "可见轻微的ST-T异常，但缺乏明确的诊断指向性，"
                "建议复查或结合其他检查综合判断。"
            ),
        },
        "key_finding_extras": [
            "ST段偏离基线",
            "T波形态或方向异常",
            "心肌复极化异常征象",
        ],
        "follow_up": [
            "建议心内科专科就诊，完善心脏超声等检查。",
            "监测血压和心率，记录症状发作情况。",
            "完善电解质及心肌酶学检查。",
            "避免剧烈运动和情绪激动。",
            "定期复查心电图，观察动态变化。",
        ],
    },
    "传导障碍": {
        "summary": {
            "high": (
                "本次ECG智能分析检测到明确的心电传导异常，"
                "心脏电激动在传导系统中存在延迟或阻滞，"
                "可能影响心率和节律的稳定性。"
            ),
            "medium": (
                "本次分析检测到心电传导系统存在异常，"
                "可能表现为传导延迟或间歇性阻滞，"
                "建议进一步评估传导系统的功能状态。"
            ),
            "low": (
                "本次分析提示可能存在心电传导异常，"
                "但征象不够明确，建议结合临床复查确认。"
            ),
        },
        "interpretation": {
            "high": (
                "心电图提示PR间期延长或QRS波群增宽，"
                "反映房室传导或室内传导存在延迟。"
                "可能的病因包括传导系统退行性改变、"
                "心肌缺血、药物影响或电解质异常等。"
            ),
            "medium": (
                "存在传导系统的异常改变，但阻滞程度可能为轻度或间歇性。"
                "建议结合动态心电图评估传导异常的频率和严重程度。"
            ),
            "low": (
                "可见轻微的传导异常征象，但缺乏明确的诊断依据，"
                "建议进一步观察或复查确认。"
            ),
        },
        "key_finding_extras": [
            "PR间期或QRS时限延长",
            "心电传导系统存在延迟或阻滞",
            "可能影响心率的稳定性",
        ],
        "follow_up": [
            "建议心内科就诊，评估传导异常的类型和严重程度。",
            "必要时进行24小时动态心电图监测。",
            "评估是否存在起搏器植入的指征。",
            "避免使用可能影响房室传导的药物。",
            "定期复查心电图，监测传导功能的动态变化。",
        ],
    },
    "心室肥大": {
        "summary": {
            "high": (
                "本次ECG智能分析检测到明确的心室肥大相关心电图改变，"
                "QRS波群电压增高，符合心室壁增厚或心腔扩大的心电图特征。"
            ),
            "medium": (
                "本次分析提示可能存在心室肥大的心电图改变，"
                "QRS电压增高但未达到典型诊断标准，"
                "建议结合心脏超声进一步明确。"
            ),
            "low": (
                "本次分析提示可能存在心室肥厚趋势，"
                "但心电图改变不典型，需结合临床资料综合判断。"
            ),
        },
        "interpretation": {
            "high": (
                "心电图显示QRS波群电压增高，伴或不伴ST-T继发性改变，"
                "符合心室肥大的心电图诊断标准。"
                "常见原因包括高血压性心脏病、心脏瓣膜病或心肌病变等。"
            ),
            "medium": (
                "QRS电压存在增高趋势，但尚未达到典型心室肥大的电压标准。"
                "建议进行心脏超声检查评估心室壁厚度和心腔大小。"
            ),
            "low": (
                "可见轻微的电压增高改变，但特异性不足，"
                "建议结合临床及其他检查手段综合评估。"
            ),
        },
        "key_finding_extras": [
            "QRS波群电压增高",
            "可能存在ST-T继发性改变",
            "心室壁增厚或心腔扩大的心电图征象",
        ],
        "follow_up": [
            "建议心内科就诊，完善心脏超声检查。",
            "控制血压在正常范围（如为高血压患者）。",
            "评估心脏瓣膜功能，排除瓣膜性心脏病。",
            "限制钠盐摄入。",
            "定期随访心脏结构和功能。",
        ],
    },
}


class TemplateReportBuilder:
    """Build structured ECG reports from diagnosis parameters."""

    # ------------------------------------------------------------------
    # Template selection helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _confidence_tier(confidence: float) -> str:
        """Map confidence value to a tier key."""
        if confidence >= 0.85:
            return "high"
        if confidence >= 0.60:
            return "medium"
        return "low"

    @staticmethod
    def _build_confidence_phrase(confidence: float, prediction: str) -> str:
        """Build a context-aware confidence phrase that considers diagnosis type."""
        tier = TemplateReportBuilder._confidence_tier(confidence)

        # Diagnosis-specific confidence phrasing
        if prediction == "正常":
            if tier == "high":
                return "结果可信度较高，可以较为放心。"
            if tier == "medium":
                return "结果有一定参考价值，建议在常规体检中确认。"
            return "结果不确定性较高，建议结合临床复查。"
        if prediction == "心肌梗死":
            if tier == "high":
                return "结果高度可信，需要立即引起重视。"
            if tier == "medium":
                return "结果有一定提示意义，建议尽快进行进一步检查。"
            return "结果存在不确定性，但仍不宜忽视，建议及时排查。"
        # ST-T改变, 传导障碍, 心室肥大
        if tier == "high":
            return "结果较为明确，建议据此安排后续诊疗。"
        if tier == "medium":
            return "结果有参考价值，建议结合临床进一步评估。"
        return "结果存在一定不确定性，建议复查或结合其他检查手段确认。"

    @staticmethod
    def _build_follow_up(severity: Optional[str], prediction: str) -> List[str]:
        """Return personalized follow-up advice."""
        profile = _DIAGNOSIS_PROFILES.get(prediction)
        if profile:
            return list(profile["follow_up"])
        # Fallback for unknown diagnoses
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
        """Build limitations section."""
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
        detected_labels: Optional[List[str]] = None,
        secondary_findings: Optional[List[str]] = None,
    ) -> DiagnosisEnhancedReport:
        """Build a deterministic structured report without external dependencies."""
        profile = _DIAGNOSIS_PROFILES.get(prediction)

        # --- Summary ---
        tier = self._confidence_tier(confidence)
        confidence_percent = f"{confidence * 100:.1f}%"
        confidence_phrase = self._build_confidence_phrase(confidence, prediction)

        if profile:
            summary_parts = [profile["summary"].get(tier, "")]
        else:
            summary_parts = [
                f"本次 ECG 智能分析的主判断为《{prediction}》，"
                f"当前置信度约为 {confidence_percent}。"
            ]
        summary_parts.append(confidence_phrase)
        summary = " ".join(summary_parts)

        # --- Clinical interpretation ---
        interpretation_parts: list[str] = []
        if profile:
            interp = profile["interpretation"].get(tier, "")
            if interp:
                interpretation_parts.append(interp)
        else:
            interpretation_parts.append(
                description or f"模型将该记录归入《{prediction}》类别。"
            )
        # Add severity and ICD info
        interpretation_parts.append(f"综合风险分层为《{severity or '未分层'}》。")
        if icd_code:
            interpretation_parts.append(f"系统关联的 ICD 编码为 {icd_code}。")
        if metadata and metadata.get("fs"):
            interpretation_parts.append(f"本次信号采样率为 {metadata['fs']} Hz。")

        # --- Key findings ---
        key_findings: list[str] = [
            f"主分类结果：{prediction}（{confidence_percent}）。",
            f"严重程度：{severity or '未评估'}。",
        ]
        if icd_code:
            key_findings.append(f"关联 ICD 编码：{icd_code}。")

        # Add diagnosis-specific key findings
        if profile:
            for extra in profile["key_finding_extras"]:
                key_findings.append(extra)

        # Add top-3 alternatives
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

        # Add secondary findings as a key finding
        if secondary_findings:
            secondary_text = "、".join(secondary_findings)
            key_findings.append(
                f"同时检测到其他异常征象：{secondary_text}，建议综合评估。"
            )

        # --- Recommendations ---
        report_recommendations = list(recommendations or [])
        if not report_recommendations:
            report_recommendations = [
                "建议结合既往病史、临床症状和常规检查结果进行综合判断。",
                "如存在明显不适，请尽快咨询专业医生。",
            ]

        # --- Follow-up ---
        follow_up = self._build_follow_up(severity, prediction)

        # --- Limitations ---
        limitations = self._build_limitations(input_mode, confidence)

        return DiagnosisEnhancedReport(
            source="template",
            summary=summary,
            clinical_interpretation="".join(interpretation_parts),
            key_findings=key_findings,
            recommendations=report_recommendations,
            follow_up=follow_up,
            limitations=limitations,
        )
