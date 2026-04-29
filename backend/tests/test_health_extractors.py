import pytest
from pathlib import Path
from app.services.health_pipeline.extractors import PDFTextExtractor, ImageTextExtractor

# Test fixtures
FIXTURES_DIR = Path(__file__).parent / "fixtures"

class TestPDFTextExtractor:
    def test_extract_text_from_pdf(self):
        extractor = PDFTextExtractor()
        # Test with a sample PDF
        pdf_path = FIXTURES_DIR / "sample_health_report.pdf"
        if pdf_path.exists():
            text = extractor.extract(pdf_path)
            assert len(text) > 0
            assert "体检报告" in text or "health report" in text.lower()
        else:
            # Basic test if fixture doesn't exist
            pytest.skip("Sample PDF fixture not available")

class TestImageTextExtractor:
    def test_extract_text_from_image(self):
        extractor = ImageTextExtractor()
        # Test with a sample image
        image_path = FIXTURES_DIR / "sample_blood_test.png"
        if image_path.exists():
            text = extractor.extract(image_path)
            assert len(text) > 0
            assert any(keyword in text for keyword in ["血红蛋白", "白细胞", "Hb", "WBC"])
        else:
            # Basic test if fixture doesn't exist
            pytest.skip("Sample image fixture not available")
