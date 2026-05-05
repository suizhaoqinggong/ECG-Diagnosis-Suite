from __future__ import annotations

import base64
import mimetypes
from pathlib import Path
from typing import Any, Optional, Protocol

import httpx
import pypdf

from app.core.config import settings

from .schemas import ExtractedText


class VisionExtractor(Protocol):
    async def extract(self, image_path: Path) -> str:
        ...


def extract_pdf_text(pdf_path: Path, password: Optional[str] = None) -> str:
    with pdf_path.open("rb") as handle:
        reader = pypdf.PdfReader(handle, password=password)
        return "\n".join(page.extract_text() or "" for page in reader.pages).strip()


async def extract_report_image_text(
    image_path: Path,
    provider: VisionExtractor | None,
) -> str:
    if provider is None:
        return ""
    return (await provider.extract(image_path)).strip()


def _normalize_vision_content(content: Any) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and item.get("type") == "text":
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "\n".join(part for part in parts if part).strip()
    return ""


class OpenAICompatibleVisionExtractor:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        timeout_seconds: int,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds

    async def extract(self, image_path: Path) -> str:
        mime_type = mimetypes.guess_type(image_path.name)[0] or "image/png"
        encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "Extract the clinically relevant text from this medical report image. "
                                "Return plain text only, preserving numbers, units, and category labels."
                            ),
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime_type};base64,{encoded}"},
                        },
                    ],
                }
            ],
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()

        data = response.json()
        message = data["choices"][0]["message"]["content"]
        return _normalize_vision_content(message)


def build_default_vision_extractor() -> OpenAICompatibleVisionExtractor | None:
    api_key = settings.OPENAI_HEALTH_VISION_API_KEY or settings.OPENAI_API_KEY
    model = settings.OPENAI_HEALTH_VISION_MODEL
    if not api_key or not model:
        return None

    base_url = settings.OPENAI_HEALTH_VISION_BASE_URL or settings.OPENAI_BASE_URL
    return OpenAICompatibleVisionExtractor(
        api_key=api_key,
        base_url=base_url,
        model=model,
        timeout_seconds=settings.OPENAI_HEALTH_VISION_TIMEOUT_SECONDS,
    )


class PDFTextExtractor:
    def extract(self, file_path: Path, password: Optional[str] = None) -> ExtractedText:
        return ExtractedText(
            text=extract_pdf_text(file_path, password=password),
            source_file=file_path,
            extraction_method="pypdf",
            confidence=0.9,
        )


class ImageTextExtractor:
    def __init__(self, provider: VisionExtractor | None = None):
        self.provider = provider

    async def extract(self, file_path: Path) -> ExtractedText:
        text = await extract_report_image_text(file_path, self.provider)
        return ExtractedText(
            text=text,
            source_file=file_path,
            extraction_method="vision_provider" if self.provider else "unconfigured",
            confidence=0.85 if text else 0.0,
        )
