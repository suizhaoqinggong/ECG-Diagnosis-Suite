from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.diagnosis_service import (
    _build_upload_file_path,
    _build_upload_session_dir,
)


def test_image_upload_paths_remain_unique_with_same_timestamp():
    upload_dir = Path("/tmp/uploads")

    first = _build_upload_file_path(upload_dir, "ecg.png")
    second = _build_upload_file_path(upload_dir, "ecg.png")

    assert first != second
    assert first.parent == upload_dir
    assert second.parent == upload_dir
    assert first.name.endswith("_ecg.png")
    assert second.name.endswith("_ecg.png")


def test_dat_pair_session_dirs_remain_unique_with_same_timestamp():
    upload_dir = Path("/tmp/uploads")

    first = _build_upload_session_dir(upload_dir)
    second = _build_upload_session_dir(upload_dir)

    assert first != second
    assert first.parent == upload_dir
    assert second.parent == upload_dir
    assert first.name.startswith("session_")
    assert second.name.startswith("session_")
