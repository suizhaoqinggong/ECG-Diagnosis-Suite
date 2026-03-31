"""
Tests for sigmoid-based multilabel inference.

These tests verify the fix for the softmax→sigmoid bug where a multilabel
CardioFormer model was being decoded with softmax (forcing probabilities
to sum to 1), causing systematically low confidence scores.
"""
import sys
from pathlib import Path

import numpy as np
import pytest
import torch
import torch.nn.functional as F

# Ensure backend is importable
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from ml.cardioformer_service import CardioFormerService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_service(checkpoint_path: str | None = None) -> CardioFormerService:
    """Create a CardioFormerService for testing."""
    return CardioFormerService(
        checkpoint_path=checkpoint_path,
        num_classes=5,
        signal_length=1000,
        input_channels=12,
        device="cpu",
    )


def _dummy_signal(seed: int = 42) -> np.ndarray:
    """Create a reproducible dummy ECG signal [12, 1000]."""
    rng = np.random.RandomState(seed)
    signal = rng.randn(12, 1000).astype(np.float32)
    return signal


# ---------------------------------------------------------------------------
# Core sigmoid tests
# ---------------------------------------------------------------------------

class TestSigmoidInference:
    """Verify sigmoid decoding produces independent per-class probabilities."""

    def test_probabilities_are_independent(self):
        """Sigmoid probabilities should NOT sum to 1 (unlike softmax)."""
        service = _make_service()
        result = service.predict_from_signal(_dummy_signal())
        probs = result["all_probabilities"]

        total = sum(probs.values())
        assert total != pytest.approx(1.0, abs=0.05), (
            f"Probabilities sum to {total:.3f} — looks like softmax, not sigmoid"
        )

    def test_all_probabilities_in_range(self):
        """Each sigmoid probability must be in (0, 1)."""
        service = _make_service()
        result = service.predict_from_signal(_dummy_signal())
        for name, prob in result["all_probabilities"].items():
            assert 0.0 < prob < 1.0, f"{name} has invalid probability {prob}"

    def test_confidence_is_sigmoid_max(self):
        """The reported confidence should equal the max sigmoid probability."""
        service = _make_service()
        result = service.predict_from_signal(_dummy_signal())
        max_prob = max(result["all_probabilities"].values())
        assert result["confidence"] == pytest.approx(max_prob, rel=1e-5)

    def test_confidence_higher_than_softmax_baseline(self):
        """
        Sigmoid confidence should be >= softmax confidence for the same input.

        This is the core regression test: the old softmax decoding suppressed
        confidence because it forced probabilities to sum to 1.
        """
        service = _make_service()
        signal = _dummy_signal()

        # Get sigmoid result from service
        result = service.predict_from_signal(signal)
        sigmoid_confidence = result["confidence"]

        # Compute what softmax would give with the same model
        input_tensor = service.preprocess_signal(signal)
        with torch.no_grad():
            logits = service.model(input_tensor)
            softmax_probs = F.softmax(logits, dim=1)
            softmax_confidence = float(softmax_probs.max().item())

        assert sigmoid_confidence >= softmax_confidence, (
            f"Sigmoid confidence ({sigmoid_confidence:.4f}) should be >= "
            f"softmax confidence ({softmax_confidence:.4f})"
        )


class TestMultilabelOutput:
    """Verify multilabel-specific fields in the inference result."""

    def test_has_detected_labels(self):
        """Result should include detected_labels (classes above threshold)."""
        service = _make_service()
        result = service.predict_from_signal(_dummy_signal())
        assert "detected_labels" in result
        assert isinstance(result["detected_labels"], list)

    def test_has_secondary_findings(self):
        """Result should include secondary_findings."""
        service = _make_service()
        result = service.predict_from_signal(_dummy_signal())
        assert "secondary_findings" in result
        assert isinstance(result["secondary_findings"], list)

    def test_primary_not_in_secondary(self):
        """Primary prediction should not appear in secondary_findings."""
        service = _make_service()
        result = service.predict_from_signal(_dummy_signal())
        assert result["prediction"] not in result["secondary_findings"]

    def test_detected_labels_above_threshold(self):
        """All detected_labels should have sigmoid probability >= threshold."""
        service = _make_service()
        result = service.predict_from_signal(_dummy_signal())
        for label in result["detected_labels"]:
            prob = result["all_probabilities"][label]
            assert prob >= 0.5, (
                f"{label} is in detected_labels but probability ({prob:.4f}) < 0.5"
            )

    def test_result_has_top3(self):
        """Top-3 predictions should still be present."""
        service = _make_service()
        result = service.predict_from_signal(_dummy_signal())
        assert "top3_predictions" in result
        assert len(result["top3_predictions"]) == 3


class TestWithCheckpoint:
    """Tests that require the actual model checkpoint."""

    @pytest.fixture
    def checkpoint_path(self):
        path = Path(__file__).parent.parent / "models" / "checkpoints" / "best.ckpt"
        if not path.exists():
            pytest.skip("Model checkpoint not available")
        return str(path)

    def test_checkpoint_loads(self, checkpoint_path):
        """Checkpoint should load without error."""
        service = _make_service(checkpoint_path)
        assert service is not None

    def test_checkpoint_confidence_above_half(self, checkpoint_path):
        """
        With a trained model, dummy signal should give at least one class
        with sigmoid confidence > 0.5 (much better than the old softmax).
        """
        service = _make_service(checkpoint_path)
        result = service.predict_from_signal(_dummy_signal())
        assert result["confidence"] > 0.5, (
            f"With a trained model, confidence is only {result['confidence']:.4f}"
        )

    def test_sigmoid_vs_softmax_gap(self, checkpoint_path):
        """
        With the real checkpoint, sigmoid max should be significantly
        higher than softmax max (the bug we're fixing).
        """
        service = _make_service(checkpoint_path)
        signal = _dummy_signal()

        result = service.predict_from_signal(signal)
        sigmoid_max = result["confidence"]

        input_tensor = service.preprocess_signal(signal)
        with torch.no_grad():
            logits = service.model(input_tensor)
            softmax_max = float(F.softmax(logits, dim=1).max().item())

        gap = sigmoid_max - softmax_max
        assert gap > 0.05, (
            f"Expected sigmoid > softmax by at least 5%, got gap={gap:.4f} "
            f"(sigmoid={sigmoid_max:.4f}, softmax={softmax_max:.4f})"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
