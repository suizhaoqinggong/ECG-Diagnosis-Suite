"""
ECG Image to Signal Converter

Converts ECG images to 1D signal format for ResNet1D model
"""
import cv2
import numpy as np
import logging
from typing import Tuple, Optional
import torch

from ml.pipeline_types import ExtractionResult, LeadQC

logger = logging.getLogger(__name__)


class ECGImageToSignal:
    """
    Convert ECG image to 12-lead 1D signal

    This is a simplified converter that extracts signal from
    standard 12-lead ECG paper recordings.
    """

    def __init__(
        self,
        signal_length: int = 1000,
        num_leads: int = 12,
        sampling_rate: int = 500
    ):
        self.signal_length = signal_length
        self.num_leads = num_leads
        self.sampling_rate = sampling_rate

    def extract_lead_signals(
        self,
        image: np.ndarray,
        lead_positions: Optional[list] = None
    ) -> np.ndarray:
        """
        Extract 1D signals from ECG image

        Args:
            image: ECG image array [H, W, C] or [H, W]
            lead_positions: Positions of each lead in the image

        Returns:
            signals: Extracted signals [num_leads, signal_length]
        """
        result = self.extract_with_result(image, lead_positions)
        return result.signals

    def _suppress_grid_lines(self, image_rgb: np.ndarray) -> np.ndarray:
        """
        Suppress grid lines from an ECG image, preserving traces.

        Uses two strategies:
        1. Color-based suppression: If the image has colored grid lines
           (common on ECG paper: red/pink grid, black traces), detect and
           suppress them via HSV saturation analysis.
        2. Periodic-line suppression: Detect horizontal/vertical lines that
           are much denser than typical ECG traces and suppress them.

        Args:
            image_rgb: Input image, either [H, W, 3] (RGB) or [H, W] (grayscale).

        Returns:
            Grayscale image [H, W] with grid lines suppressed.
        """
        # Handle 2-D (grayscale) input directly
        if image_rgb.ndim == 2:
            return self._suppress_grid_lines_grayscale(image_rgb)

        h, w, c = image_rgb.shape
        assert c == 3, f"Expected 3-channel image, got {c}"

        # Check if the image actually has color information
        # If all channels are nearly identical, treat as grayscale
        r, g, b = image_rgb[:, :, 0], image_rgb[:, :, 1], image_rgb[:, :, 2]
        channel_diff = float(
            np.mean(np.abs(r.astype(np.int16) - g.astype(np.int16)))
            + np.mean(np.abs(r.astype(np.int16) - b.astype(np.int16)))
        ) / 2.0

        if channel_diff < 5.0:
            # Essentially grayscale — use conservative path
            gray = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2GRAY)
            return self._suppress_grid_lines_grayscale(gray)

        # --- Color-based suppression ---
        # Convert to HSV to separate saturation (color) from value (brightness)
        hsv = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2HSV)
        saturation = hsv[:, :, 1].astype(np.float32)
        value = hsv[:, :, 2].astype(np.float32)

        # Grid lines on ECG paper typically have noticeable saturation (colored),
        # while traces are dark and low-saturation (black ink).
        # Build a "trace likelihood" map:
        #   - Dark pixels (low value) -> high trace likelihood
        #   - Saturated pixels (high saturation) -> low trace likelihood (likely grid)
        #   - Dark + saturated -> could be either, but dark dominates

        # Trace score: higher for dark, low-saturation pixels
        # Normalize value to [0, 1] range for scoring
        value_norm = value / 255.0
        sat_norm = saturation / 255.0

        # Trace likelihood: dark pixels score high, bright saturated pixels score low
        # Using: trace_score = (1 - value_norm) * (1 - sat_norm * 0.5)
        # This means:
        #   - Very dark (value_norm~0) => high score regardless of saturation
        #   - Bright + saturated => low score (grid)
        #   - Bright + unsaturated => medium score (background)
        trace_score = (1.0 - value_norm) * (1.0 - sat_norm * 0.5)

        # Convert trace_score to grayscale image where traces are dark
        # Invert: high trace_score -> dark pixel (we want traces dark for downstream)
        # But we want the OUTPUT to be a grayscale image where:
        #   - traces are dark
        #   - grid lines are bright (suppressed)
        # So: output = (1 - trace_score) * 255
        result = ((1.0 - trace_score) * 255.0).astype(np.uint8)

        # --- Periodic line suppression ---
        result = self._suppress_periodic_lines(result)

        # --- Safety check: if suppression removed too much, fall back ---
        # Count dark pixels (potential content) in the result
        dark_ratio = float(np.mean(result < 80))
        if dark_ratio > 0.50:
            # Too much content would be lost — use standard grayscale instead
            logger.debug(
                "Grid suppression would remove %.0f%% of content (> 50%%), "
                "falling back to standard grayscale",
                dark_ratio * 100,
            )
            return cv2.cvtColor(image_rgb, cv2.COLOR_RGB2GRAY)

        return result

    def _suppress_grid_lines_grayscale(self, gray: np.ndarray) -> np.ndarray:
        """
        Conservative grid suppression for grayscale-only images.

        For grayscale images there is no color information to distinguish
        grid lines from traces, so we return the image unchanged to avoid
        removing real ECG content.  Grid suppression is only effective
        when colored grid lines (red/pink) can be detected via HSV analysis.
        """
        return gray

    def _suppress_periodic_lines(self, gray: np.ndarray) -> np.ndarray:
        """
        Detect and suppress periodic horizontal/vertical grid lines
        using row/column occupancy analysis.

        Args:
            gray: Grayscale image [H, W].

        Returns:
            Grayscale image with periodic grid lines suppressed.
        """
        h, w = gray.shape
        result = gray.copy()

        # Binarize for occupancy analysis: dark pixels are foreground
        # Use adaptive threshold to be robust across different brightness levels
        mean_val = float(np.mean(gray))
        _, binary = cv2.threshold(gray, int(mean_val * 0.7), 255, cv2.THRESH_BINARY_INV)

        # --- Horizontal grid lines ---
        row_occupancy = np.sum(binary > 0, axis=1).astype(np.float64) / w
        median_occupancy = float(np.median(row_occupancy))

        if median_occupancy > 0.001:
            # Grid lines have much higher occupancy than typical trace rows
            grid_threshold = median_occupancy * 3.0
            grid_rows = row_occupancy > grid_threshold

            # Also require periodicity: grid lines repeat at regular intervals
            # Find the dominant period via autocorrelation of the grid row signal
            grid_signal = grid_rows.astype(np.float64)
            if np.sum(grid_signal) > 2:
                # Check periodicity via FFT
                fft = np.fft.rfft(grid_signal - np.mean(grid_signal))
                magnitudes = np.abs(fft[1:])  # Skip DC component
                if len(magnitudes) > 0:
                    peak_idx = np.argmax(magnitudes) + 1
                    if peak_idx < len(fft):
                        # Only suppress if there's clear periodicity
                        peak_magnitude = magnitudes[peak_idx - 1]
                        mean_magnitude = float(np.mean(magnitudes))
                        if peak_magnitude > mean_magnitude * 3.0:
                            # Periodic grid detected — suppress those rows
                            for y in range(h):
                                if grid_rows[y]:
                                    # Replace with interpolated value from neighbors
                                    above = max(y - 1, 0)
                                    below = min(y + 1, h - 1)
                                    # Use the brighter neighbor (background) to fill
                                    result[y, :] = np.maximum(result[above, :], result[below, :])

        # --- Vertical grid lines (less aggressive) ---
        col_occupancy = np.sum(binary > 0, axis=0).astype(np.float64) / h
        median_col_occupancy = float(np.median(col_occupancy))

        if median_col_occupancy > 0.001:
            # Less aggressive threshold for columns since traces span horizontally
            grid_col_threshold = median_col_occupancy * 4.0
            grid_cols = col_occupancy > grid_col_threshold

            # Check periodicity for columns too
            col_signal = grid_cols.astype(np.float64)
            if np.sum(col_signal) > 2:
                fft = np.fft.rfft(col_signal - np.mean(col_signal))
                magnitudes = np.abs(fft[1:])
                if len(magnitudes) > 0:
                    peak_idx = np.argmax(magnitudes) + 1
                    if peak_idx < len(fft):
                        peak_magnitude = magnitudes[peak_idx - 1]
                        mean_magnitude = float(np.mean(magnitudes))
                        if peak_magnitude > mean_magnitude * 3.0:
                            for x in range(w):
                                if grid_cols[x]:
                                    left = max(x - 1, 0)
                                    right = min(x + 1, w - 1)
                                    result[:, x] = np.maximum(result[:, left], result[:, right])

        return result

    def _extract_trace_centroid(self, strip: np.ndarray) -> np.ndarray:
        """
        Extract a 1D trace signal from a binary strip using continuity-constrained
        vertical run tracking.

        For each column:
        1. Find vertical runs of dark pixels (foreground)
        2. Filter: reject runs shorter than 2px or taller than 40% of strip height
        3. Compute the center Y of each valid run
        4. Select the run closest to the previous column's center (continuity)
        5. Interpolate gaps from neighbors
        6. Invert so upward deflection = positive
        7. Light smoothing

        Args:
            strip: Binary image [H, W] where 0=background, 255=foreground.

        Returns:
            1D signal array of length W with NaN gaps interpolated.
        """
        h, w = strip.shape
        signal = np.full(w, np.nan, dtype=np.float64)

        min_run_len = 2
        max_run_len = int(h * 0.4)

        prev_center: float | None = None

        for col in range(w):
            column = strip[:, col]

            # Find vertical runs of foreground pixels
            runs = []
            in_run = False
            run_start = 0
            for row in range(h):
                if column[row] > 0:
                    if not in_run:
                        in_run = True
                        run_start = row
                else:
                    if in_run:
                        in_run = False
                        run_len = row - run_start
                        if min_run_len <= run_len <= max_run_len:
                            center = run_start + run_len / 2.0
                            runs.append(center)
            # Handle run that extends to the bottom edge
            if in_run:
                run_len = h - run_start
                if min_run_len <= run_len <= max_run_len:
                    center = run_start + run_len / 2.0
                    runs.append(center)

            if not runs:
                continue

            if prev_center is None:
                # First column: pick the run closest to the strip center
                best = min(runs, key=lambda c: abs(c - h / 2.0))
            else:
                # Continuity: pick the run closest to previous center
                best = min(runs, key=lambda c: abs(c - prev_center))

            signal[col] = best
            prev_center = best

        # Interpolate NaN gaps from neighbors
        nan_mask = np.isnan(signal)
        if np.any(nan_mask) and not np.all(nan_mask):
            valid_indices = np.where(~nan_mask)[0]
            signal[nan_mask] = np.interp(
                np.where(nan_mask)[0],
                valid_indices,
                signal[valid_indices],
            )

        # If all NaN (empty strip), return zeros
        if np.all(np.isnan(signal)):
            return np.zeros(w, dtype=np.float64)

        # Invert: upward deflection = positive (y=0 is top, so subtract from strip center)
        signal = (h / 2.0) - signal

        # Light Savitzky-Golay smoothing
        if len(signal) >= 7:
            try:
                from scipy.signal import savgol_filter
                signal = savgol_filter(signal, window_length=min(11, len(signal) if len(signal) % 2 == 1 else len(signal) - 1), polyorder=3)
            except ImportError:
                # Fallback: simple moving average
                kernel = np.ones(5) / 5.0
                signal = np.convolve(signal, kernel, mode='same')

        return signal

    def extract_with_result(
        self,
        image: np.ndarray,
        lead_positions: Optional[list] = None,
    ) -> ExtractionResult:
        """
        Extract signals with QC metadata.

        Same as extract_lead_signals() but returns ExtractionResult with
        per-lead quality metrics.

        Args:
            image: ECG image array [H, W, C] or [H, W]
            lead_positions: Positions of each lead in the image

        Returns:
            ExtractionResult with signals and QC metadata
        """
        # Grid suppression step: suppress grid lines before binarization
        gray = self._suppress_grid_lines(image)

        # Threshold to get ECG trace
        _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)

        height, width = binary.shape
        strip_height = height // self.num_leads

        signals = []
        per_lead_qc: list[LeadQC] = []
        total_interpolated = 0
        total_columns = 0
        fallback_used = False

        for i in range(self.num_leads):
            y_start = i * strip_height
            y_end = (i + 1) * strip_height
            strip = binary[y_start:y_end, :]

            # Compute per-strip QC before extraction
            col_has_content = np.mean(strip > 0, axis=0)
            coverage = float(np.mean(col_has_content > 0.02))
            valid_column_ratio = float(np.mean(col_has_content > 0.005))

            # Extract signal using continuity-constrained centroid tracking
            signal_1d = self._extract_trace_centroid(strip)

            # Count interpolated (near-zero variance) columns
            interpolated = int(np.sum(signal_1d < 1e-6))
            total_interpolated += interpolated
            total_columns += len(signal_1d)
            interpolated_ratio = interpolated / max(len(signal_1d), 1)

            # Signal flatness (std of the extracted signal)
            flatness = float(np.std(signal_1d))

            # Jump rate: fraction of columns where signal jumps > 20% of strip height
            if len(signal_1d) > 1:
                diffs = np.abs(np.diff(signal_1d))
                jump_threshold = strip_height * 0.20
                jump_rate = float(np.mean(diffs > jump_threshold))
            else:
                jump_rate = 0.0

            # Clipped ratio: fraction at min or max
            clipped_ratio = 0.0  # For mean-based extraction, clipping is rare

            # SNR estimate: signal std / noise floor
            if flatness > 0:
                noise_floor = float(np.median(signal_1d[signal_1d < np.median(signal_1d)])) if np.any(signal_1d < np.median(signal_1d)) else 0.0
                snr_estimate = flatness / max(noise_floor, 1e-8)
            else:
                snr_estimate = None

            # Quality classification
            if coverage < 0.02:
                quality = "fail"
            elif coverage < 0.10 or flatness < 1.0:
                quality = "poor"
            elif coverage < 0.30:
                quality = "warn"
            else:
                quality = "good"

            per_lead_qc.append(LeadQC(
                lead_index=i,
                flatness=flatness,
                coverage=coverage,
                valid_column_ratio=valid_column_ratio,
                interpolated_ratio=interpolated_ratio,
                jump_rate=jump_rate,
                clipped_ratio=clipped_ratio,
                snr_estimate=snr_estimate,
                quality=quality,
            ))

            # Normalize
            signal_1d = (signal_1d - signal_1d.min()) / (signal_1d.max() - signal_1d.min() + 1e-8)

            # Resize to desired length
            signal_1d = cv2.resize(signal_1d, (1, self.signal_length))
            signal_1d = signal_1d.flatten()

            signals.append(signal_1d)

        signals_array = np.array(signals, dtype=np.float32)

        # Overall quality
        failed_leads = sum(1 for qc in per_lead_qc if qc.quality == "fail")
        poor_leads = sum(1 for qc in per_lead_qc if qc.quality in ("fail", "poor"))

        if failed_leads > self.num_leads // 2:
            overall_quality = "fail"
        elif poor_leads > self.num_leads // 3:
            overall_quality = "warn"
        else:
            overall_quality = "pass"

        interpolated_ratio = total_interpolated / max(total_columns, 1)

        return ExtractionResult(
            signals=signals_array,
            layout_method="horizontal_strips",
            layout_score=1.0,
            fallback_used=fallback_used,
            interpolated_columns=total_interpolated,
            interpolated_ratio=interpolated_ratio,
            per_lead_qc=per_lead_qc,
            warnings=[],
            issues=[],
            overall_quality=overall_quality,
        )

    def __call__(self, image: np.ndarray) -> torch.Tensor:
        """
        Convert image to tensor

        Args:
            image: ECG image array

        Returns:
            tensor: Signal tensor [1, num_leads, signal_length]
        """
        signals = self.extract_lead_signals(image)
        tensor = torch.from_numpy(signals).float()
        tensor = tensor.unsqueeze(0)  # Add batch dimension

        return tensor


def create_dummy_ecg_signal(
    signal_length: int = 1000,
    num_leads: int = 12
) -> torch.Tensor:
    """
    Create dummy ECG signal for testing

    This generates realistic-looking ECG waveform

    Args:
        signal_length: Length of signal
        num_leads: Number of leads

    Returns:
        ECG signal tensor [1, num_leads, signal_length]
    """
    signals = []

    for lead in range(num_leads):
        # Create synthetic ECG-like waveform
        t = np.linspace(0, 10, signal_length)

        # Base signal
        signal = np.zeros(signal_length)

        # Add P-QRS-T waves periodically
        for beat in range(10):  # 10 beats in the signal
            # Position of this beat
            beat_start = int(beat * signal_length / 10)
            beat_end = int((beat + 0.8) * signal_length / 10)

            if beat_end > signal_length:
                beat_end = signal_length

            beat_len = beat_end - beat_start

            # Create P wave
            p_wave = 0.1 * np.sin(np.linspace(0, np.pi, beat_len // 4))

            # Create QRS complex
            qrs_len = beat_len // 6
            qrs = np.zeros(qrs_len)
            qrs[qrs_len//4:qrs_len//2] = -0.2  # Q wave
            qrs[qrs_len//2:3*qrs_len//4] = 1.0  # R wave
            qrs[3*qrs_len//4:] = -0.3  # S wave

            # Create T wave
            t_wave = 0.3 * np.sin(np.linspace(0, np.pi, beat_len // 3))

            # Combine waves
            beat_signal = np.zeros(beat_len)
            beat_signal[:len(p_wave)] = p_wave
            beat_signal[len(p_wave):len(p_wave)+len(qrs)] = qrs
            beat_signal[len(p_wave)+len(qrs):len(p_wave)+len(qrs)+len(t_wave)] = t_wave

            # Add some noise
            beat_signal += 0.02 * np.random.randn(beat_len)

            # Add to full signal
            signal[beat_start:beat_end] = beat_signal

        # Add baseline wander
        baseline = 0.1 * np.sin(2 * np.pi * t / signal_length * 10)
        signal += baseline

        signals.append(signal)

    # Stack and convert to tensor
    signals = np.array(signals)
    tensor = torch.from_numpy(signals).float()
    tensor = tensor.unsqueeze(0)  # Add batch dimension

    return tensor


if __name__ == "__main__":
    # Test the converter
    converter = ECGImageToSignal()

    # Create a dummy image
    dummy_image = np.random.randint(0, 255, (1200, 1000, 3), dtype=np.uint8)

    # Convert
    signal_tensor = converter(dummy_image)
    print(f"Signal tensor shape: {signal_tensor.shape}")

    # Create dummy signal
    dummy_signal = create_dummy_ecg_signal()
    print(f"Dummy signal shape: {dummy_signal.shape}")
