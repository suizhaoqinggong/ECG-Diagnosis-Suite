import pytest
from app.services.health_pipeline.classifier import HealthAssetClassifier, AssetType

class TestHealthAssetClassifier:
    def test_classify_pdf_file(self):
        classifier = HealthAssetClassifier()
        result = classifier.classify("report.pdf", "application/pdf")
        assert result == AssetType.HEALTH_REPORT_PDF

    def test_classify_image_file(self):
        classifier = HealthAssetClassifier()
        # ECG image
        result = classifier.classify("ecg.jpg", "image/jpeg")
        assert result == AssetType.ECG_IMAGE

        # General health report image/screenshot
        result = classifier.classify("blood_test.png", "image/png")
        assert result == AssetType.HEALTH_REPORT_IMAGE

    def test_classify_ecg_signal_files(self):
        classifier = HealthAssetClassifier()
        result = classifier.classify("sample.dat", "application/octet-stream")
        assert result == AssetType.ECG_SIGNAL_DAT

        result = classifier.classify("sample.hea", "application/octet-stream")
        assert result == AssetType.ECG_SIGNAL_HEA

    def test_classify_text_file(self):
        classifier = HealthAssetClassifier()
        result = classifier.classify("report.txt", "text/plain")
        assert result == AssetType.HEALTH_REPORT_TEXT

    def test_unsupported_file_type(self):
        classifier = HealthAssetClassifier()
        with pytest.raises(ValueError, match="Unsupported file type"):
            classifier.classify("unknown.exe", "application/exe")
