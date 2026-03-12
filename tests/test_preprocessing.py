"""
Test preprocessing module
"""
import pytest
import numpy as np
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent / "backend"))
from ml.preprocessing import ECGPreprocessor


def test_preprocessor_init():
    """Test preprocessor initialization"""
    preprocessor = ECGPreprocessor()
    assert preprocessor.target_size == (224, 224)
    assert preprocessor.normalize is True


def test_preprocessor_to_grayscale():
    """Test grayscale conversion"""
    preprocessor = ECGPreprocessor()

    # Create a test RGB image
    rgb_image = np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8)
    gray_image = preprocessor.to_grayscale(rgb_image)

    assert len(gray_image.shape) == 2  # Should be 2D
    assert gray_image.dtype == np.uint8


def test_preprocessor_normalize():
    """Test normalization"""
    preprocessor = ECGPreprocessor()

    # Create test image
    image = np.random.randint(0, 255, (224, 224), dtype=np.uint8)
    normalized = preprocessor.normalize_image(image)

    assert normalized.dtype == np.float32
    assert normalized.min() >= 0.0
    assert normalized.max() <= 1.0


# TODO: Add test with actual image file
# def test_preprocess_full_pipeline():
#     """Test full preprocessing pipeline"""
#     preprocessor = ECGPreprocessor()
#     result = preprocessor.preprocess("tests/fixtures/sample.png")
#
#     assert result.shape == (1, 224, 224, 1)
#     assert result.dtype == np.float32


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
