"""
Signal Quality Analyzer — Inter-lead collapse quality gate.

Detects when ECG image conversion produces nearly identical signals
across all 12 leads (inter-lead collapse), which causes the model to
misclassify.  This module is called AFTER image-to-signal conversion
but BEFORE model inference.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray


@dataclass(slots=True)
class SignalQualityReport:
    """Quality report for an extracted multi-lead ECG signal."""

    mean_correlation: float       # mean off-diagonal Pearson correlation
    max_correlation: float        # max off-diagonal Pearson correlation
    high_corr_ratio: float        # fraction of pairs above threshold
    flat_lead_count: int          # leads with std < 0.005
    is_collapsed: bool            # True if signal quality is too poor
    warning: str | None           # human-readable warning


def _nan_safe_corrcoef(signals: NDArray[np.floating]) -> NDArray[np.floating]:
    """
    Compute pairwise Pearson correlation matrix, NaN-safe.

    For each pair of leads, compute correlation using only the samples
    where *both* leads are non-NaN.  If fewer than 10 shared samples
    remain, or either lead has zero variance, return NaN for that pair.
    """
    n_leads = signals.shape[0]
    corr = np.full((n_leads, n_leads), np.nan, dtype=np.float64)

    for i in range(n_leads):
        corr[i, i] = 1.0
        for j in range(i + 1, n_leads):
            # Mask where both leads have valid (non-NaN) values
            mask = np.isfinite(signals[i]) & np.isfinite(signals[j])
            count = int(mask.sum())

            if count < 10:
                # Not enough shared samples — leave as NaN
                continue

            x = signals[i][mask]
            y = signals[j][mask]

            vx = np.var(x)
            vy = np.var(y)

            if vx < 1e-30 or vy < 1e-30:
                # Zero variance — correlation undefined, leave as NaN
                continue

            r = float(np.corrcoef(x, y)[0, 1])
            if np.isnan(r):
                continue

            corr[i, j] = r
            corr[j, i] = r

    return corr


def analyze_signal_quality(
    signals: NDArray[np.floating],
    threshold: float = 0.9,
) -> SignalQualityReport:
    """
    Analyze inter-lead signal quality to detect collapsed outputs.

    A "collapsed" conversion happens when the image-to-signal pipeline
    produces nearly identical traces for all 12 leads, typically because
    it failed to segment the image correctly.

    Args:
        signals: Extracted ECG signals, shape [num_leads, signal_length].
        threshold: Correlation threshold above which a lead pair is
                   considered "highly correlated".  Default 0.9.

    Returns:
        SignalQualityReport with correlation metrics and collapse flag.
    """
    n_leads, _ = signals.shape

    # --- Flat lead detection ---
    flat_lead_count = 0
    for i in range(n_leads):
        lead = signals[i]
        valid = lead[np.isfinite(lead)]
        if len(valid) < 10:
            # Lead is mostly/entirely NaN — treat as flat
            flat_lead_count += 1
        else:
            std = float(np.std(valid))
            if std < 0.005:
                flat_lead_count += 1

    # --- Inter-lead correlation ---
    corr = _nan_safe_corrcoef(signals)

    # Extract upper-triangle off-diagonal values (skip NaN)
    upper_indices = np.triu_indices(n_leads, k=1)
    off_diag = corr[upper_indices]
    valid_corr = off_diag[np.isfinite(off_diag)]

    if len(valid_corr) > 0:
        mean_corr = float(np.mean(valid_corr))
        max_corr = float(np.max(valid_corr))
        high_count = int(np.sum(valid_corr >= threshold))
        total_pairs = len(valid_corr)
        high_corr_ratio = high_count / total_pairs
    else:
        # No valid correlation pairs (e.g. all NaN or all zero-variance)
        mean_corr = float("nan")
        max_corr = float("nan")
        high_corr_ratio = 0.0

    # --- Collapse detection ---
    collapsed_by_corr = (
        np.isfinite(mean_corr) and mean_corr > threshold
    )
    collapsed_by_flat = flat_lead_count > 6
    is_collapsed = collapsed_by_corr or collapsed_by_flat

    # --- Warning message ---
    warning: str | None = None
    if is_collapsed:
        parts: list[str] = []
        if collapsed_by_corr:
            parts.append(
                f"导联间平均相关性过高 ({mean_corr:.3f} > {threshold})"
            )
        if collapsed_by_flat:
            parts.append(
                f"平坦导联数过多 ({flat_lead_count}/12)"
            )
        warning = "信号质量不足: " + "; ".join(parts) + "。图像转换可能失败，请检查ECG图像质量。"

    return SignalQualityReport(
        mean_correlation=mean_corr if np.isfinite(mean_corr) else 0.0,
        max_correlation=max_corr if np.isfinite(max_corr) else 0.0,
        high_corr_ratio=high_corr_ratio,
        flat_lead_count=flat_lead_count,
        is_collapsed=is_collapsed,
        warning=warning,
    )
