import asyncio
from pathlib import Path

from reportlab.pdfgen import canvas

from app.services.health_pipeline.extractors import (
    extract_pdf_text,
    extract_report_image_text,
)


class StubVisionExtractor:
    async def extract(self, image_path: Path) -> str:
        return "甲状腺超声提示 TI-RADS 3 类结节"


def test_extract_pdf_text_returns_plain_text(tmp_path):
    pdf_path = tmp_path / "report.pdf"
    pdf = canvas.Canvas(str(pdf_path))
    pdf.drawString(72, 720, "LDL 4.9 mmol/L")
    pdf.save()

    text = extract_pdf_text(pdf_path)

    assert "LDL 4.9 mmol/L" in text


def test_extract_report_image_text_uses_provider(tmp_path):
    image_path = tmp_path / "report.jpg"
    image_path.write_bytes(b"fake-image")

    text = asyncio.run(extract_report_image_text(image_path, StubVisionExtractor()))

    assert "TI-RADS 3" in text
