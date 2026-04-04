"""
Business regression tests for upload utilities.

Covers sanitize_filename (path traversal), validate_extension (allowlist),
and save_upload (size enforcement).
"""

import io
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException, UploadFile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.core.upload import sanitize_filename, validate_extension, save_upload


# ===========================================================================
# sanitize_filename
# ===========================================================================


class TestSanitizeFilename:
    def test_normal_filename(self):
        assert sanitize_filename("ecg.png") == "ecg.png"

    def test_strips_directory_path(self):
        assert sanitize_filename("../../etc/passwd") == "passwd"

    def test_strips_windows_path(self):
        # On non-Windows, Path("C:\\Users\\test\\ecg.png").name keeps the full string
        # since backslashes aren't separators on Unix. This is acceptable — Windows
        # paths can't traverse Unix filesystems.
        result = sanitize_filename("C:\\Users\\test\\ecg.png")
        assert "ecg.png" in result

    def test_strips_forward_slash_path(self):
        assert sanitize_filename("/tmp/secret.dat") == "secret.dat"

    def test_rejects_none(self):
        with pytest.raises(HTTPException) as exc:
            sanitize_filename(None)
        assert exc.value.status_code == 400

    def test_rejects_empty_string(self):
        with pytest.raises(HTTPException) as exc:
            sanitize_filename("")
        assert exc.value.status_code == 400

    def test_rejects_dot(self):
        with pytest.raises(HTTPException) as exc:
            sanitize_filename(".")
        assert exc.value.status_code == 400

    def test_rejects_double_dot(self):
        with pytest.raises(HTTPException) as exc:
            sanitize_filename("..")
        assert exc.value.status_code == 400

    def test_rejects_null_bytes(self):
        with pytest.raises(HTTPException) as exc:
            sanitize_filename("file\x00.png")
        assert exc.value.status_code == 400

    def test_rejects_control_characters(self):
        with pytest.raises(HTTPException) as exc:
            sanitize_filename("file\x01.png")
        assert exc.value.status_code == 400

    def test_preserves_chinese_characters(self):
        assert sanitize_filename("心电图.png") == "心电图.png"

    def test_preserves_spaces(self):
        assert sanitize_filename("my ecg report.png") == "my ecg report.png"


# ===========================================================================
# validate_extension
# ===========================================================================


class TestValidateExtension:
    def test_accepts_png(self):
        validate_extension("image.png")  # should not raise

    def test_accepts_jpg(self):
        validate_extension("image.jpg")

    def test_accepts_jpeg(self):
        validate_extension("image.jpeg")

    def test_accepts_dat(self):
        validate_extension("signal.dat")

    def test_accepts_hea(self):
        validate_extension("signal.hea")

    def test_accepts_uppercase_extension(self):
        validate_extension("image.PNG")

    def test_rejects_txt(self):
        with pytest.raises(HTTPException) as exc:
            validate_extension("notes.txt")
        assert exc.value.status_code == 400

    def test_rejects_py(self):
        with pytest.raises(HTTPException) as exc:
            validate_extension("script.py")
        assert exc.value.status_code == 400

    def test_rejects_exe(self):
        with pytest.raises(HTTPException) as exc:
            validate_extension("malware.exe")
        assert exc.value.status_code == 400

    def test_rejects_no_extension(self):
        with pytest.raises(HTTPException) as exc:
            validate_extension("README")
        assert exc.value.status_code == 400


# ===========================================================================
# save_upload (size enforcement)
# ===========================================================================


class TestSaveUpload:
    def test_save_small_file(self, tmp_path):
        content = b"x" * 100
        file = MagicMock(spec=UploadFile)
        file.file = io.BytesIO(content)
        dest = tmp_path / "test.png"

        save_upload(file, dest)
        assert dest.exists()
        assert dest.read_bytes() == content

    def test_rejects_oversized_file(self, tmp_path):
        # Patch MAX_UPLOAD_SIZE to 100 bytes for this test
        big_content = b"x" * 200
        file = MagicMock(spec=UploadFile)
        file.file = io.BytesIO(big_content)
        dest = tmp_path / "big.png"

        with patch("app.core.upload.settings.MAX_UPLOAD_SIZE", 100):
            with pytest.raises(HTTPException) as exc:
                save_upload(file, dest)
        assert exc.value.status_code == 413
        # Partial file should be cleaned up
        assert not dest.exists()

    def test_creates_parent_directory(self, tmp_path):
        content = b"hello"
        file = MagicMock(spec=UploadFile)
        file.file = io.BytesIO(content)
        dest = tmp_path / "subdir" / "deep" / "test.png"

        save_upload(file, dest)
        assert dest.exists()
        assert dest.read_bytes() == content
