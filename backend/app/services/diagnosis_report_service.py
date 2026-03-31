"""
Diagnosis report generation service.

Builds a richer structured report from the base diagnosis output and can
optionally enhance it with an OpenAI model when configured.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Literal, Optional

import httpx
from pydantic import BaseModel, ConfigDict, Field

from app.core.config import settings

logger = logging.getLogger(__name__)


class DiagnosisEnhancedReport(BaseModel):
    """Structured narrative report returned to API clients."""

    source: Literal["template", "llm"]
    model: Optional[str] = None
    summary: str
    clinical_interpretation: str
    key_findings: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    follow_up: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)


class _LLMReportBody(BaseModel):
    """Schema enforced on LLM output."""

    model_config = ConfigDict(extra="forbid")

    summary: str
    clinical_interpretation: str
    key_findings: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    follow_up: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)


class DiagnosisReportService:
    """Generate fallback or LLM-enhanced reports for diagnosis results."""

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _strip_markdown_fences(text: str) -> str:
        """Remove surrounding ```json ... ``` fences that LLMs often add."""
        stripped = text.strip()
        if stripped.startswith("```"):
            # Drop the opening fence line (e.g. ```json or ```)
            stripped = stripped.split("\n", 1)[-1] if "\n" in stripped else stripped[3:]
            # Drop the closing fence
            if stripped.rstrip().endswith("```"):
                stripped = stripped.rstrip()[:-3]
        return stripped.strip()

    def _parse_llm_text(
        self,
        raw_text: str,
        model_name: str,
        fallback_report: DiagnosisEnhancedReport,
        provider_label: str,
    ) -> Optional[DiagnosisEnhancedReport]:
        """Parse raw LLM text into a DiagnosisEnhancedReport.

        Handles markdown fences, JSON validation, and field-level fallback.
        Returns None when the text cannot be parsed.
        """
        cleaned = self._strip_markdown_fences(raw_text)

        try:
            parsed = _LLMReportBody.model_validate_json(cleaned)
        except Exception as exc:
            logger.warning("%s report returned invalid JSON: %s", provider_label, exc)
            return None

        return DiagnosisEnhancedReport(
            source="llm",
            model=model_name,
            summary=parsed.summary,
            clinical_interpretation=parsed.clinical_interpretation,
            key_findings=parsed.key_findings or fallback_report.key_findings,
            recommendations=parsed.recommendations or fallback_report.recommendations,
            follow_up=parsed.follow_up or fallback_report.follow_up,
            limitations=parsed.limitations or fallback_report.limitations,
        )

    def _build_confidence_phrase(self, confidence: float) -> str:
        if confidence >= 0.85:
            return "模型对当前主判断信号较强"
        if confidence >= 0.7:
            return "模型对当前主判断有中等偏高把握"
        if confidence >= 0.5:
            return "模型给出了倾向性判断，但不确定性仍然明显"
        return "模型输出不确定性较高，应谨慎解读"

    def _build_follow_up(self, severity: Optional[str]) -> List[str]:
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

    def _build_limitations(self, input_mode: str, confidence: float) -> List[str]:
        limitations = [
            "本报告基于算法输出自动生成，仅供研究和工程验证参考，不能替代医生诊断。",
            "模型结论依赖输入数据质量、采样条件和训练分布，异常噪声或非标准采集会影响结果。",
        ]

        if input_mode == "image":
            limitations.append("图像上传路径包含图像转信号过程，纸质心电图拍摄角度、阴影和分辨率会降低解释可靠性。")

        if confidence < settings.CONFIDENCE_THRESHOLD:
            limitations.append("当前主分类置信度低于系统阈值，应重点参考备选类别并优先进行人工复核。")

        return limitations

    def build_template_report(
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

    async def _generate_with_openai(
        self,
        *,
        prompt_context: Dict[str, Any],
        fallback_report: DiagnosisEnhancedReport,
    ) -> Optional[DiagnosisEnhancedReport]:
        if not settings.OPENAI_API_KEY:
            return None

        schema = _LLMReportBody.model_json_schema()

        payload = {
            "model": settings.OPENAI_REPORT_MODEL,
            "input": [
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                "你是一名用于科研和工程验证场景的 ECG 报告撰写助手。"
                                "只能基于提供的结构化诊断结果写报告，不能虚构新的测量值、病史、"
                                "器械参数或临床结论。"
                                "请使用专业、克制、清晰的中文输出。"
                                "如果置信度有限，要明确表达不确定性；"
                                "所有建议必须保持医学上审慎，不能替代临床诊断。"
                            ),
                        }
                    ],
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": json.dumps(prompt_context, ensure_ascii=False),
                        }
                    ],
                },
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "ecg_diagnosis_report",
                    "strict": True,
                    "schema": schema,
                }
            },
        }

        headers = {
            "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(
            base_url=settings.OPENAI_BASE_URL.rstrip("/"),
            timeout=settings.OPENAI_TIMEOUT_SECONDS,
        ) as client:
            response = await client.post("/responses", headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

        raw_text: Optional[str] = None
        for output in data.get("output", []):
            for content in output.get("content", []):
                text_value = content.get("text")
                if isinstance(text_value, str) and text_value.strip():
                    raw_text = text_value
                    break
            if raw_text:
                break

        if not raw_text:
            logger.warning("OpenAI report generation returned no text output.")
            return None

        return self._parse_llm_text(
            raw_text,
            model_name=settings.OPENAI_REPORT_MODEL,
            fallback_report=fallback_report,
            provider_label="OpenAI",
        )

    async def _generate_with_anthropic_compatible(
        self,
        *,
        prompt_context: Dict[str, Any],
        fallback_report: DiagnosisEnhancedReport,
    ) -> Optional[DiagnosisEnhancedReport]:
        if not settings.ANTHROPIC_COMPAT_API_KEY:
            return None

        system_prompt = (
            "你是一名用于科研和工程验证场景的 ECG 报告撰写助手。"
            "只能基于提供的结构化诊断结果写报告，不能虚构新的测量值、病史、器械参数或临床结论。"
            "请使用专业、克制、清晰的中文输出。"
            "如果置信度有限，要明确表达不确定性；所有建议必须保持医学上审慎，不能替代临床诊断。"
            "你必须只输出一个 JSON 对象，不能包含 markdown、解释或额外文本。"
            "JSON 结构必须包含以下字段："
            "summary(string), clinical_interpretation(string), key_findings(string[]), "
            "recommendations(string[]), follow_up(string[]), limitations(string[])."
        )

        payload = {
            "model": settings.ANTHROPIC_COMPAT_MODEL,
            "max_tokens": settings.ANTHROPIC_COMPAT_MAX_TOKENS,
            "system": system_prompt,
            "messages": [
                {
                    "role": "user",
                    "content": json.dumps(prompt_context, ensure_ascii=False),
                }
            ],
        }

        headers = {
            "x-api-key": settings.ANTHROPIC_COMPAT_API_KEY,
            "content-type": "application/json",
        }

        async with httpx.AsyncClient(
            base_url=settings.ANTHROPIC_COMPAT_BASE_URL.rstrip("/"),
            timeout=settings.ANTHROPIC_COMPAT_TIMEOUT_SECONDS,
        ) as client:
            response = await client.post("/v1/messages", headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

        chunks = []
        for content in data.get("content", []):
            text_value = content.get("text")
            if isinstance(text_value, str) and text_value.strip():
                chunks.append(text_value)

        raw_text = "\n".join(chunks).strip()
        if not raw_text:
            logger.warning("Anthropic-compatible report generation returned no text output.")
            return None

        return self._parse_llm_text(
            raw_text,
            model_name=settings.ANTHROPIC_COMPAT_MODEL,
            fallback_report=fallback_report,
            provider_label="Anthropic-compatible",
        )

    async def generate_report(
        self,
        *,
        prediction: str,
        confidence: float,
        severity: Optional[str],
        icd_code: Optional[str],
        description: Optional[str],
        recommendations: Optional[List[str]],
        top3_predictions: Optional[List[Dict[str, Any]]],
        all_probabilities: Optional[Dict[str, float]],
        input_mode: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> DiagnosisEnhancedReport:
        fallback_report = self.build_template_report(
            prediction=prediction,
            confidence=confidence,
            severity=severity,
            icd_code=icd_code,
            description=description,
            recommendations=recommendations,
            top3_predictions=top3_predictions,
            input_mode=input_mode,
            metadata=metadata,
        )

        if not settings.LLM_REPORT_ENABLED:
            return fallback_report

        prompt_context = {
            "prediction": prediction,
            "confidence": confidence,
            "severity": severity,
            "icd_code": icd_code,
            "description": description,
            "recommendations": recommendations,
            "top3_predictions": top3_predictions,
            "all_probabilities": all_probabilities,
            "input_mode": input_mode,
            "metadata": metadata or {},
            "fallback_report": fallback_report.model_dump(mode="json"),
        }

        provider = settings.LLM_REPORT_PROVIDER.lower()

        # Warn early if the chosen provider has no API key configured
        if provider == "openai" and not settings.OPENAI_API_KEY:
            logger.warning(
                "LLM reports are enabled with provider 'openai', but OPENAI_API_KEY is not set. "
                "Falling back to template report."
            )
            return fallback_report
        if provider in {"anthropic", "anthropic_compatible", "zhipu_anthropic"} and not settings.ANTHROPIC_COMPAT_API_KEY:
            logger.warning(
                "LLM reports are enabled with provider '%s', but ANTHROPIC_COMPAT_API_KEY is not set. "
                "Falling back to template report.",
                provider,
            )
            return fallback_report

        try:
            if provider == "openai":
                enhanced_report = await self._generate_with_openai(
                    prompt_context=prompt_context,
                    fallback_report=fallback_report,
                )
            elif provider in {"anthropic", "anthropic_compatible", "zhipu_anthropic"}:
                enhanced_report = await self._generate_with_anthropic_compatible(
                    prompt_context=prompt_context,
                    fallback_report=fallback_report,
                )
            else:
                logger.warning(
                    "Unsupported LLM report provider '%s', falling back to template report.",
                    settings.LLM_REPORT_PROVIDER,
                )
                return fallback_report
        except Exception as exc:
            logger.warning("LLM report generation failed, using fallback report: %s", exc)
            return fallback_report

        return enhanced_report or fallback_report


_report_service = DiagnosisReportService()


def get_diagnosis_report_service() -> DiagnosisReportService:
    return _report_service
