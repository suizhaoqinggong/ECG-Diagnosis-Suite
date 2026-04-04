"""LLM provider implementations for report enhancement.

Each provider implements ``async generate(...)`` which returns either a
``DiagnosisEnhancedReport`` or ``None`` when generation fails or is not
configured.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

import httpx

from app.core.config import settings
from .parser import LLMReportBody, parse_llm_text
from .schemas import DiagnosisEnhancedReport

logger = logging.getLogger(__name__)


class OpenAIProvider:
    """Generate enhanced reports using the OpenAI Responses API."""

    async def generate(
        self,
        *,
        prompt_context: Dict[str, Any],
        fallback_report: DiagnosisEnhancedReport,
    ) -> Optional[DiagnosisEnhancedReport]:
        if not settings.OPENAI_API_KEY:
            return None

        schema = LLMReportBody.model_json_schema()

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

        return parse_llm_text(
            raw_text,
            model_name=settings.OPENAI_REPORT_MODEL,
            fallback_report=fallback_report,
            provider_label="OpenAI",
        )


class AnthropicCompatibleProvider:
    """Generate enhanced reports using an Anthropic-compatible Messages API."""

    async def generate(
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

        return parse_llm_text(
            raw_text,
            model_name=settings.ANTHROPIC_COMPAT_MODEL,
            fallback_report=fallback_report,
            provider_label="Anthropic-compatible",
        )
