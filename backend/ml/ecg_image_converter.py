"""
ECG Image to Signal Converter

Converts ECG images to 1D signal format for ResNet1D model
"""
import cv2
import numpy as np
from typing import Tuple, Optional
import torch

from ml.pipeline_types import ExtractionResult, LeadQC


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
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

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

            # Extract signal
            signal_1d = np.mean(strip, axis=0)

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
