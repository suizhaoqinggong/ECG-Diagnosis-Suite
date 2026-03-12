"""
ECG Image to Signal Converter

Converts ECG images to 1D signal format for ResNet1D model
"""
import cv2
import numpy as np
from typing import Tuple, Optional
import torch


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
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        # Threshold to get ECG trace
        _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)

        # Simple approach: divide image into 12 horizontal strips
        # Each strip represents one lead
        height, width = binary.shape
        strip_height = height // self.num_leads

        signals = []
        for i in range(self.num_leads):
            # Extract strip for this lead
            y_start = i * strip_height
            y_end = (i + 1) * strip_height
            strip = binary[y_start:y_end, :]

            # Find the ECG trace in this strip
            # Simple: take the column-wise average (or median)
            signal_1d = np.mean(strip, axis=0)

            # Normalize
            signal_1d = (signal_1d - signal_1d.min()) / (signal_1d.max() - signal_1d.min() + 1e-8)

            # Resize to desired length
            signal_1d = cv2.resize(signal_1d, (1, self.signal_length))
            signal_1d = signal_1d.flatten()

            signals.append(signal_1d)

        # Stack all leads
        signals = np.array(signals)  # [num_leads, signal_length]

        return signals

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
