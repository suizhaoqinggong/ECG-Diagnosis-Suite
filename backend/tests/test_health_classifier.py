import pytest
from app.services.health_pipeline.classifier import (
    HealthAssetClassifier,
    AssetType,
    classify_asset,
)


def test_classify_asset_marks_pdf_as_report_pdf():
    assert classify_asset("summary.pdf", "application/pdf") == "report_pdf"


def test_classify_asset_marks_dat_as_ecg_signal():
    assert classify_asset("record.dat", "application/octet-stream") == "ecg_signal"


def test_classify_asset_marks_hea_as_ecg_signal():
    assert classify_asset("record.hea", "text/plain") == "ecg_signal"


def test_classify_asset_marks_images_as_report_image():
    assert classify_asset("photo.png", "image/png") == "report_image"
    assert classify_asset("photo.jpg", "image/jpeg") == "report_image"
    assert classify_asset("photo.jpeg", "image/jpeg") == "report_image"


def test_classify_asset_marks_ecg_named_images_as_ecg_image():
    assert classify_asset("ecg-lead.png", "image/png") == "ecg_image"


def test_classify_asset_rejects_unsupported():
    with pytest.raises(ValueError, match="Unsupported upload"):
        classify_asset("data.csv", "text/csv")


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
