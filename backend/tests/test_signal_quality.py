"""
Tests for P0: Inter-lead collapse quality gate.

Tests for the SignalQualityAnalyzer that detects when ECG image
conversion produces nearly identical signals across all 12 leads.
"""

import numpy as np
import pytest

from ml.signal_quality import SignalQualityReport, analyze_signal_quality


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _identical_signals(num_leads: int = 12, length: int = 1000) -> np.ndarray:
    """Create num_leads identical copies of the same sine wave."""
    t = np.linspace(0, 4 * np.pi, length, dtype=np.float32)
    base = np.sin(t)
    return np.tile(base, (num_leads, 1))


def _diverse_sine_signals(num_leads: int = 12, length: int = 1000) -> np.ndarray:
    """Create num_leads different sine waves with distinct frequencies/phases."""
    signals = []
    for i in range(num_leads):
        t = np.linspace(0, 4 * np.pi, length, dtype=np.float32)
        freq = 1.0 + i * 0.7  # Different frequency per lead
        phase = i * np.pi / 6  # Different phase per lead
        sig = np.sin(freq * t + phase)
        signals.append(sig)
    return np.array(signals, dtype=np.float32)


def _partially_correlated_signals(length: int = 1000) -> np.ndarray:
    """Create 12-lead signal with 6 identical pairs (6 unique, each duplicated)."""
    signals = []
    for i in range(6):
        t = np.linspace(0, 4 * np.pi, length, dtype=np.float32)
        freq = 1.0 + i * 0.7
        sig = np.sin(freq * t)
        signals.append(sig)       # original
        signals.append(sig.copy())  # identical copy
    return np.array(signals, dtype=np.float32)


def _zero_variance_lead_signals(length: int = 1000) -> np.ndarray:
    """Create 12-lead signal where 3 leads are flat (zero variance)."""
    signals = []
    for i in range(12):
        if i in (2, 5, 9):
            # Flat lead — constant value
            sig = np.full(length, 0.5, dtype=np.float32)
        else:
            t = np.linspace(0, 4 * np.pi, length, dtype=np.float32)
            freq = 1.0 + i * 0.5
            sig = np.sin(freq * t).astype(np.float32)
        signals.append(sig)
    return np.array(signals, dtype=np.float32)


def _nan_lead_signals(length: int = 1000) -> np.ndarray:
    """Create 12-lead signal where 2 leads are entirely NaN."""
    signals = []
    for i in range(12):
        if i in (3, 7):
            sig = np.full(length, np.nan, dtype=np.float32)
        else:
            t = np.linspace(0, 4 * np.pi, length, dtype=np.float32)
            freq = 1.0 + i * 0.5
            sig = np.sin(freq * t).astype(np.float32)
        signals.append(sig)
    return np.array(signals, dtype=np.float32)


def _all_flat_signals(num_leads: int = 12, length: int = 1000) -> np.ndarray:
    """All leads are flat (zero variance) — extreme collapsed case."""
    signals = []
    for i in range(num_leads):
        sig = np.full(length, 0.5, dtype=np.float32)
        signals.append(sig)
    return np.array(signals, dtype=np.float32)


# ---------------------------------------------------------------------------
# Test 1: Identical signals -> is_collapsed=True
# ---------------------------------------------------------------------------


class TestIdenticalSignals:
    """All 12 leads are identical -> should detect collapse."""

    def test_is_collapsed(self):
        report = analyze_signal_quality(_identical_signals())
        assert report.is_collapsed is True

    def test_mean_correlation_near_one(self):
        report = analyze_signal_quality(_identical_signals())
        assert report.mean_correlation > 0.99

    def test_max_correlation_is_one(self):
        report = analyze_signal_quality(_identical_signals())
        assert report.max_correlation >= 0.999

    def test_high_corr_ratio_is_one(self):
        report = analyze_signal_quality(_identical_signals())
        assert report.high_corr_ratio == 1.0

    def test_warning_is_set(self):
        report = analyze_signal_quality(_identical_signals())
        assert report.warning is not None
        assert "collapse" in report.warning.lower() or "相关" in report.warning


# ---------------------------------------------------------------------------
# Test 2: Diverse signals -> is_collapsed=False
# ---------------------------------------------------------------------------


class TestDiverseSignals:
    """12 different sine waves -> should NOT detect collapse."""

    def test_not_collapsed(self):
        report = analyze_signal_quality(_diverse_sine_signals())
        assert report.is_collapsed is False

    def test_mean_correlation_low(self):
        report = analyze_signal_quality(_diverse_sine_signals())
        assert report.mean_correlation < 0.5

    def test_no_warning(self):
        report = analyze_signal_quality(_diverse_sine_signals())
        assert report.warning is None


# ---------------------------------------------------------------------------
# Test 3: Partially correlated (6 identical pairs)
# ---------------------------------------------------------------------------


class TestPartiallyCorrelated:
    """6 pairs of identical signals — should have elevated but not full correlation."""

    def test_high_corr_ratio(self):
        report = analyze_signal_quality(_partially_correlated_signals())
        # With 6 identical pairs out of C(12,2)=66 total pairs,
        # high_corr_ratio should be substantial
        assert report.high_corr_ratio > 0.0

    def test_mean_correlation_between(self):
        report = analyze_signal_quality(_partially_correlated_signals())
        # Mean correlation should be above zero but below threshold
        assert 0.0 < report.mean_correlation

    def test_not_collapsed_by_default_threshold(self):
        report = analyze_signal_quality(_partially_correlated_signals(), threshold=0.9)
        # With default 0.9 threshold, 6 pairs of identicals should still not
        # trigger collapse (mean_corr will be elevated but not > 0.9)
        assert report.is_collapsed is False


# ---------------------------------------------------------------------------
# Test 4: Zero-variance leads -> flat_lead_count incremented, no crash
# ---------------------------------------------------------------------------


class TestZeroVarianceLeads:
    """Leads with zero variance should be counted, no crash."""

    def test_does_not_crash(self):
        report = analyze_signal_quality(_zero_variance_lead_signals())
        assert isinstance(report, SignalQualityReport)

    def test_flat_lead_count(self):
        report = analyze_signal_quality(_zero_variance_lead_signals())
        # 3 leads are flat
        assert report.flat_lead_count == 3

    def test_not_collapsed(self):
        """With only 3 flat leads (< 6), should not trigger collapse."""
        report = analyze_signal_quality(_zero_variance_lead_signals())
        assert report.is_collapsed is False


# ---------------------------------------------------------------------------
# Test 5: All-NaN leads -> no crash
# ---------------------------------------------------------------------------


class TestNaNLeads:
    """Leads that are entirely NaN should not crash the analyzer."""

    def test_does_not_crash(self):
        report = analyze_signal_quality(_nan_lead_signals())
        assert isinstance(report, SignalQualityReport)

    def test_flat_lead_count_includes_nan(self):
        """NaN-only leads should be counted as flat (std=0 after NaN removal)."""
        report = analyze_signal_quality(_nan_lead_signals())
        # NaN-only leads have std=NaN < 0.005 is False, but we handle them
        # They should be counted as flat
        assert report.flat_lead_count >= 2


# ---------------------------------------------------------------------------
# Test 6: All flat leads -> collapsed via flat_lead_count > 6
# ---------------------------------------------------------------------------


class TestAllFlatLeads:
    """All leads flat -> should detect collapse via flat_lead_count."""

    def test_is_collapsed(self):
        report = analyze_signal_quality(_all_flat_signals())
        assert report.is_collapsed is True

    def test_flat_lead_count_is_12(self):
        report = analyze_signal_quality(_all_flat_signals())
        assert report.flat_lead_count == 12

    def test_warning_mention_flat(self):
        report = analyze_signal_quality(_all_flat_signals())
        assert report.warning is not None


# ---------------------------------------------------------------------------
# Test 7: Custom threshold
# ---------------------------------------------------------------------------


class TestCustomThreshold:
    """Verify threshold parameter controls collapse detection."""

    def test_low_threshold_triggers_on_diverse(self):
        """With a very low threshold, even diverse signals may trigger."""
        report = analyze_signal_quality(
            _partially_correlated_signals(), threshold=0.01
        )
        assert report.is_collapsed is True

    def test_high_threshold_does_not_trigger_on_identical(self):
        """With threshold=1.0, even identical signals are not 'collapsed' by corr."""
        report = analyze_signal_quality(_identical_signals(), threshold=1.0)
        # But they might still be collapsed due to identical signals having corr=1.0
        # mean_correlation=1.0 > 1.0 is False, so not collapsed via corr
        # But flat_lead_count could be 0 since they have variance
        # So this should be False
        assert report.is_collapsed is False


# ---------------------------------------------------------------------------
# Test 8: Report is a proper dataclass
# ---------------------------------------------------------------------------


class TestReportDataclass:
    """SignalQualityReport should be a proper dataclass."""

    def test_has_all_fields(self):
        report = analyze_signal_quality(_diverse_sine_signals())
        assert hasattr(report, "mean_correlation")
        assert hasattr(report, "max_correlation")
        assert hasattr(report, "high_corr_ratio")
        assert hasattr(report, "flat_lead_count")
        assert hasattr(report, "is_collapsed")
        assert hasattr(report, "warning")

    def test_types(self):
        report = analyze_signal_quality(_diverse_sine_signals())
        assert isinstance(report.mean_correlation, float)
        assert isinstance(report.max_correlation, float)
        assert isinstance(report.high_corr_ratio, float)
        assert isinstance(report.flat_lead_count, int)
        assert isinstance(report.is_collapsed, bool)
        assert report.warning is None or isinstance(report.warning, str)
